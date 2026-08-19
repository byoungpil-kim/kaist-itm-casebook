# -*- coding: utf-8 -*-
"""docx 변경추적을 cases/{id}.html 본문에 반영.

문단 단위로 OLD(변경 거부본)를 HTML 요소의 평문과 대조해 위치를 찾고,
OLD→NEW 문자 단위 diff를 HTML 문자열 위치로 옮겨 적용한다.
이렇게 하면 <b>·<a> 같은 인라인 태그가 보존된다.
"""
import sys, io, os, re, glob, zipfile, html as H, difflib
from xml.etree import ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
DOCDIR = r'C:/claude/itm-cases/사례_수정_조항정'
REPO = r'C:/claude/kaist-itm-casebook'


def walk(el, ctx, acc):
    for ch in el:
        t = ch.tag
        if t == W + 'ins':
            walk(ch, 'ins', acc)
        elif t == W + 'del':
            walk(ch, 'del', acc)
        elif t == W + 't':
            acc.append((ctx, ch.text or ''))
        elif t == W + 'delText':
            acc.append(('del', ch.text or ''))
        elif t == W + 'tab':
            acc.append((ctx, ' '))
        elif t == W + 'br':
            acc.append((ctx, ' '))
        else:
            walk(ch, ctx, acc)


def changed_paras(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    out = []
    for p in root.find(W + 'body').iter(W + 'p'):
        acc = []
        walk(p, 'plain', acc)
        if not any(c in ('ins', 'del') for c, _ in acc):
            continue
        old = ''.join(s for c, s in acc if c != 'ins')
        new = ''.join(s for c, s in acc if c != 'del')
        if old.strip() == new.strip():
            continue
        out.append((old.strip(), new.strip()))
    return out


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def plain_map(h):
    """HTML 문자열의 평문과, 평문 각 문자 → 원문 인덱스 대응."""
    chars, pos = [], []
    i = 0
    n = len(h)
    while i < n:
        if h[i] == '<':
            j = h.find('>', i)
            i = n if j < 0 else j + 1
            continue
        if h[i] == '&':
            m = re.match(r'&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);', h[i:])
            if m:
                chars.append(H.unescape(m.group(0)))
                pos.append(i)
                i += len(m.group(0))
                continue
        chars.append(h[i])
        pos.append(i)
        i += 1
    return ''.join(chars), pos


def apply_one(body, old, new, log):
    """body(HTML 조각 문자열)에 old→new 반영. 성공 시 새 body, 실패 시 None."""
    plain, pos = plain_map(body)
    # 공백 정규화한 상태로 위치를 찾는다
    def squash(s):
        out, idx = [], []
        prev_sp = True
        for k, c in enumerate(s):
            if c.isspace():
                if prev_sp:
                    continue
                out.append(' ')
                idx.append(k)
                prev_sp = True
            else:
                out.append(c)
                idx.append(k)
                prev_sp = False
        return ''.join(out).strip(), idx
    sq, sqidx = squash(plain)
    tgt = norm(old)
    k = sq.find(tgt)
    if k < 0:
        return None
    if sq.find(tgt, k + 1) >= 0:
        log.append(f'    !! OLD가 본문에 2곳 이상 등장 — 건너뜀: {tgt[:40]}…')
        return None
    # squash 인덱스 → plain 인덱스
    # sq는 strip 되었으므로 앞쪽 공백만큼 보정
    lead = len(plain) - len(plain.lstrip())
    off = 0
    while off < len(sqidx) and sqidx[off] < lead:
        off += 1
    s2p = sqidx[off:]
    seg_plain_s = s2p[k]
    seg_plain_e = s2p[k + len(tgt) - 1] + 1
    seg_html_s = pos[seg_plain_s]
    seg_html_e = pos[seg_plain_e - 1] + 1
    seg_html = body[seg_html_s:seg_html_e]

    # 조각 안에서 old→new 문자 diff를 적용
    sp, spos = plain_map(seg_html)
    sm = difflib.SequenceMatcher(None, norm(sp), norm(new), autojunk=False)
    # sp(정규화 전) 인덱스를 쓰기 위해 정규화 없이 비교 (조각은 이미 old와 동일 평문)
    sm = difflib.SequenceMatcher(None, sp, new, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    out = seg_html
    lost = 0
    for tag, i1, i2, j1, j2 in reversed(ops):
        hs = spos[i1] if i1 < len(spos) else len(seg_html)
        he = (spos[i2 - 1] + 1) if i2 > i1 else hs
        if '<' in seg_html[hs:he]:
            lost += 1
        out = out[:hs] + H.escape(new[j1:j2], quote=False) + out[he:]
    if lost:
        log.append(f'    ※ 태그를 걸친 수정 {lost}건 (해당 구간 태그 소실 가능): {tgt[:30]}…')
    return body[:seg_html_s] + out + body[seg_html_e:]


def main():
    total_ok = total_fail = 0
    for path in sorted(glob.glob(os.path.join(DOCDIR, '*.docx'))):
        cid = os.path.basename(path).split('_')[0]
        hp = os.path.join(REPO, 'cases', cid + '.html')
        h = io.open(hp, encoding='utf-8').read()
        m = re.search(r'(<!-- BODY:START -->)(.*?)(<!-- BODY:END -->)', h, re.S)
        body = m.group(2)
        log = [f'===== {cid} =====']
        ok = fail = 0
        misses = []
        for old, new in changed_paras(path):
            r = apply_one(body, old, new, log)
            if r is None:
                fail += 1
                misses.append((old, new))
            else:
                body = r
                ok += 1
        log.append(f'  반영 {ok} / 실패 {fail}')
        for old, new in misses:
            log.append(f'  ✗ OLD: {old[:110]}')
            log.append(f'    NEW: {new[:110]}')
        print('\n'.join(log))
        total_ok += ok
        total_fail += fail
        if not DRY:
            io.open(hp, 'w', encoding='utf-8').write(h[:m.start(2)] + body + h[m.end(2):])
    print(f'\n@@ 전체 반영 {total_ok} / 실패 {total_fail}')


DRY = '--dry' in sys.argv
if __name__ == '__main__':
    main()
