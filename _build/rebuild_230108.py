# -*- coding: utf-8 -*-
"""230108(김기윤) 원문 전면 재구성.

발견된 문제
 1) 절 제목(1.1~3.3.2)이 볼드가 아니고 본문과 같은 12pt → 전부 본문으로 흡수, 목차 없음
 2) 표 17개가 통째로 누락(캡션·이미지 모두 없음)
 3) find_tables() 오탐(페이지 60% 높이)으로 12페이지 등 본문이 통째로 삭제됨
 4) 그림 1·2가 좌우로 나란히 배치돼(캡션 한 줄, 이미지 2개, 출처 좌우) 하나로 뭉침

구조: 캡션이 그림/표 '위', 출처는 아래. 문단은 첫 줄 들여쓰기(x 77→89) 또는 선행 공백.
표 셀은 10pt라 본문(12pt) 필터로 자동 배제되므로 find_tables()는 쓰지 않는다.
그림/표 영역의 하단은 '도형·이미지의 아래끝'으로 잡는다 — 텍스트 규칙으로 잡으면
표 안의 괄호 셀("(STP 등)")과 표 아래 출처 줄을 구분할 수 없다.
"""
import sys, io, re, os, fitz, html as H
from PIL import Image

CID = '230108'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
BODY_START = 4
DPI = 200
SEC = re.compile(r'^\d+\.\d+(\.\d+)?\s*[가-힣A-Za-z(]')
FIGCAP = re.compile(r'^\s*<\s*그림\s*(\d+)\s*>')
TABCAP = re.compile(r'^\s*\[\s*표\s*-?\s*(\d+)\s*\]')
SRCPFX = re.compile(r'^\s*(출처|자료)\s*[:：]')
IMGDIR = f'fulltext/{CID}/img'
d = fitz.open(f'pdf/{CID}.pdf')
os.makedirs(IMGDIR, exist_ok=True)


SRC_KW = re.compile(r'출처|자료|저자|참조|보고서|홈페이지|공시|조사|http|\d{4}')


def is_src(t, x, sz):
    """출처 줄: '출처:/자료:' 또는 출처 성격의 낱말·연도를 담은 괄호·꺾쇠 한 줄.
    괄호만 보고 판정하면 표 안의 숫자 셀("(409.2)")까지 출처로 잡힌다."""
    t = t.strip()
    if SRCPFX.match(t):
        return True
    return (bool(re.match(r'^[(（<]', t)) and len(t) < 90 and bool(SRC_KW.search(t))
            and (x >= 120 or sz <= 11.5 or t.endswith((')', '）', '>'))))


def collect_src(lines, y0, y1, hard, xlo=None, xhi=None):
    """[y0, y1] 구간의 출처 줄. 첫 출처 줄 이후 이어지는 작은 글씨는 같은 출처의 둘째 줄로 본다."""
    got, send, started = [], y0, False
    for ln in sorted(lines, key=lambda a: (a['y'], a['x'])):
        if not (y0 <= ln['y'] <= y1) or ln['y'] >= hard - 1:
            continue
        if xlo is not None and not (xlo <= ln['x'] < xhi):
            continue
        t = ln['raw'].strip()
        if is_break(t, ln['x'], ln['x1'], ln['sz']):
            break
        if is_src(t, ln['x'], ln['sz']):
            got.append(t); send = max(send, ln['y1']); started = True
        elif started and ln['sz'] <= 11.5 and len(t) < 60:
            got.append(t); send = max(send, ln['y1'])
        elif started:
            break
    return ' '.join(got), send


def is_break(t, x, x1, sz):
    """그림/표 영역을 끝내는 줄(다음 캡션·소제목·장제목·본문 재개)."""
    t = t.strip()
    if is_src(t, x, sz):
        return False
    return (bool(FIGCAP.match(t)) or bool(TABCAP.match(t)) or sz >= 15
            or bool(SEC.match(t) and len(t) < 60)
            or (sz >= 11.5 and x < 115 and (x1 - x) > 300))


def vlines(pi):
    """양쪽정렬로 쪼개진 조각을 y 기준 한 줄로 병합."""
    frags = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            raw = ''.join(s['text'] for s in l['spans'])
            if raw.strip():
                sp0 = l['spans'][0]
                frags.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                                  raw=raw, sz=sp0['size'],
                                  bold=bool(sp0['flags'] & 16) or 'Bold' in sp0['font']))
    foot = d[pi].rect.height - 90          # 쪽번호는 페이지 하단 우측에만 있다
    frags = [f for f in frags
             if not (re.fullmatch(r'\d{1,3}\s*', f['raw']) and f['x'] > 400 and f['y'] > foot)]
    frags.sort(key=lambda f: (f['y'], f['x']))
    merged = []
    for f in frags:
        if merged and abs(f['y'] - merged[-1]['y']) <= 3:
            prev = merged[-1]
            prev['raw'] = prev['raw'].rstrip() + ' ' + f['raw'].strip()
            prev['x1'] = max(prev['x1'], f['x1']); prev['y1'] = max(prev['y1'], f['y1'])
        else:
            merged.append(dict(f))
    return merged


def rawlines(pi):
    """병합하지 않은 줄 조각(좌우 2단 배치에서 열별 분리에 필요)."""
    out = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            raw = ''.join(s['text'] for s in l['spans'])
            if raw.strip():
                out.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                                raw=raw, sz=l['spans'][0]['size']))
    return out


def graphics(pi):
    """페이지의 이미지 사각형. get_drawings()는 이 원고에선 줄마다 깔린 흰 배경
    사각형뿐이라 그림·표 경계 신호로 쓸 수 없다."""
    return [fitz.Rect(b['bbox']) for b in d[pi].get_text('dict')['blocks'] if b.get('type') == 1]


def render(pi, rect, name):
    pix = d[pi].get_pixmap(clip=fitz.Rect(*rect), dpi=DPI)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        os.path.join(IMGDIR, name), 'WEBP', quality=90)
    return f'img/{name}'


def region_below(pi, cap_y1, lines, gr):
    """캡션 아래 그림/표 영역과 그 아래 출처 줄을 함께 돌려준다."""
    PH = d[pi].rect.height
    limit, hard = PH - 55, PH        # limit=영역 탐색 한계, hard=절대 넘으면 안 되는 다음 캡션/제목 y
    for ln in lines:
        if ln['y'] <= cap_y1 + 1:
            continue
        if is_break(ln['raw'], ln['x'], ln['x1'], ln['sz']):
            limit, hard = min(limit, ln['y'] - 4), ln['y']; break
        if SRCPFX.match(ln['raw'].strip()):
            limit = min(limit, ln['y'] - 3); break

    # 영역 하단 = 이미지 아래끝과 표 본문(출처 줄 전) 아래끝 중 큰 값
    gb = [r.y1 for r in gr if cap_y1 - 2 <= r.y0 and r.y1 <= limit + 4]
    inner = [ln for ln in lines if cap_y1 + 1 < ln['y'] < limit]
    srcys = [ln['y'] for ln in inner if is_src(ln['raw'], ln['x'], ln['sz'])]
    first_src = min(srcys) if srcys else None
    body = [ln['y1'] for ln in inner if ln['sz'] <= 11.2
            and not is_src(ln['raw'], ln['x'], ln['sz']) and (first_src is None or ln['y'] < first_src)]
    cands = [v for v in (max(gb) if gb else None, max(body) if body else None) if v is not None]
    # 표 테두리는 마지막 글자보다 조금 더 내려오므로 여유를 두되, 출처 줄은 물지 않게 자른다
    media_bottom = (max(cands) + 14) if cands else limit
    media_bottom = min(media_bottom, (first_src + 1) if first_src is not None else limit)

    xs0, xs1 = [], []
    for r in gr:
        if cap_y1 - 2 <= r.y0 and r.y1 <= media_bottom + 4:
            xs0.append(r.x0); xs1.append(r.x1)
    for ln in lines:
        if cap_y1 + 1 < ln['y'] and ln['y1'] <= media_bottom + 3:
            xs0.append(ln['x']); xs1.append(ln['x1'])
    if not xs0 or media_bottom - cap_y1 < 22:
        return None, '', cap_y1, hard

    rect = (min(xs0) - 6, cap_y1 + 2, max(xs1) + 6, media_bottom + 1)
    srctext, send = collect_src(lines, media_bottom - 2, media_bottom + 52, hard)
    return rect, srctext, max(send, rect[3]), hard


blocks, para = [], []


def flush():
    global para
    if para:
        t = re.sub(r'\s{2,}', ' ', ''.join(para).strip())
        if len(t) > 1:
            blocks.append(('p', t))
        para = []


carry = {}          # 앞 페이지 캡션의 그림/표가 이어지는 페이지 → 그 아래까지 본문에서 제외

for pi in range(BODY_START, d.page_count):
    lines = vlines(pi)
    gr = graphics(pi)
    skip_until = carry.get(pi, -1)
    for ln in lines:
        t = ln['raw'].strip()
        if not t or ln['y'] < skip_until:
            continue
        if t.startswith('참고문헌') or (t.startswith('Reference') and ln['sz'] >= 14):
            break
        if ln['sz'] >= 15:
            flush(); blocks.append(('h2', t)); continue

        fm, tm = FIGCAP.match(t), TABCAP.match(t)
        if fm or tm:
            flush()
            nums = [int(n) for n in re.findall(r'<\s*그림\s*(\d+)\s*>', t)] if fm else [int(tm.group(1))]
            tag = 'fig' if fm else 'tbl'
            rect, srctext, send, hard = region_below(pi, ln['y1'], lines, gr)
            if os.environ.get('DBG'):
                sys.stderr.write("p%d y%.0f %r rect=%s send=%.0f hard=%.0f\n" % (
                    pi + 1, ln['y'], t[:26], None if rect is None else tuple(round(v) for v in rect), send, hard))
            # 캡션이 페이지 끝이거나 그림/표가 페이지 밑단까지 차면 다음 페이지로 이어진다
            def ok(r):
                return r and (r[2] - r[0]) >= 60 and (r[3] - r[1]) >= 25
            parts = [(pi, rect)] if ok(rect) else []
            if (not parts or (rect[3] >= d[pi].rect.height - 100 and not srctext)) and pi + 1 < d.page_count:
                l2, g2 = vlines(pi + 1), graphics(pi + 1)
                r2, s2, e2, _ = region_below(pi + 1, 84, l2, g2)
                if ok(r2):
                    parts.append((pi + 1, r2))
                    srctext = (srctext + ' ' + s2).strip()
                    carry[pi + 1] = e2 + 2
            if not parts:
                continue
            if fm and len(nums) == 2:          # 좌우 2단 배치: 캡션·이미지·출처를 열별로 분리
                imgs = sorted([b['bbox'] for b in d[pi].get_text('dict')['blocks']
                               if b.get('type') == 1 and ln['y1'] < b['bbox'][1] < rect[3] + 8],
                              key=lambda r: r[0])
                capparts = re.split(r'(?=<\s*그림\s*%d\s*>)' % nums[1], t)
                mid = (imgs[0][2] + imgs[1][0]) / 2 if len(imgs) >= 2 else (rect[0] + rect[2]) / 2
                srcs = {}
                for k in (0, 1):
                    lo, hi = (0, mid) if k == 0 else (mid, 10_000)
                    srcs[k], s2 = collect_src(rawlines(pi), rect[3] - 8, rect[3] + 56, hard, lo, hi)
                    send = max(send, s2)
                for k, num in enumerate(nums):
                    r2 = (imgs[k][0] - 3, imgs[k][1] - 3, imgs[k][2] + 3, imgs[k][3] + 3) if len(imgs) > k else rect
                    blocks.append(('media', dict(
                        cap=capparts[k].strip() if k < len(capparts) else f'<그림 {num}>',
                        src=srcs[k],
                        imgs=[render(pi, r2, f'{tag}{num:02d}.webp')])))
                skip_until = min(send + 2, hard - 1)
                continue
            imgs = [render(p2, r2, f'{tag}{nums[0]:02d}{chr(97+i) if len(parts) > 1 else ""}.webp')
                    for i, (p2, r2) in enumerate(parts)]
            blocks.append(('media', dict(cap=t, src=srctext, imgs=imgs)))
            skip_until = min(send + 2, hard - 1)
            continue

        if SEC.match(t) and len(t) < 60:
            flush(); blocks.append(('h3', t)); continue
        if is_src(t, ln['x'], ln['sz']):
            continue
        if 10.8 <= ln['sz'] < 13:
            if ln.get('bold') and len(t) < 50:          # 굵은 소제목은 독립 문단
                flush(); blocks.append(('p', t)); continue
            if para and (ln['x'] >= 85 or ln['raw'][:1] == ' '):
                flush()
            para.append(ln['raw'])
flush()

out = []
for kind, val in blocks:
    if kind == 'h2':
        out.append(f'<h2>{H.escape(val, quote=False)}</h2>')
    elif kind == 'h3':
        out.append(f'<h3>{H.escape(val, quote=False)}</h3>')
    elif kind == 'p':
        out.append(f'<p>{H.escape(val, quote=False)}</p>')
    else:
        out.append(f'<p class="ftcap">{H.escape(val["cap"], quote=False)}</p>')
        if val['src']:
            out.append(f'<p class="ftsrc">{H.escape(val["src"], quote=False)}</p>')
        for im in val['imgs']:
            out.append(f'<figure class="ftfig"><img src="{im}" alt=""></figure>')
io.open(f'{SP}/body_{CID}.html', 'w', encoding='utf-8').write('\n'.join(out))
ps = [b for b in blocks if b[0] == 'p']
med = [b for b in blocks if b[0] == 'media']
print(f"문단 {len(ps)}개(평균 {sum(len(b[1]) for b in ps)//max(1,len(ps))}자) | "
      f"h2 {sum(1 for b in blocks if b[0]=='h2')} · h3 {sum(1 for b in blocks if b[0]=='h3')} | 그림·표 {len(med)}개")
