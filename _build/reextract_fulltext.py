# -*- coding: utf-8 -*-
"""
원문 전문(fulltext) 본문 재추출 파이프라인  (2026-07 도입)

목적: 구 gen_fulltext2.py(pdftotext -layout)가 만든 fulltext 본문의 구조적 결함
      (줄바꿈 띄어쓰기 누락·문장 분리, 각주 본문 흡수, 표 텍스트 잔존, 미주 무링크)을
      원본 PDF에서 PyMuPDF로 재추출해 근본 수정한다.

핵심 원리:
  - PyMuPDF `get_text("dict")`는 PDF에 인코딩된 실제 공백을 보존한다. 한 문단의 줄들을
    **공백 추가 없이 그대로 이어붙이면**(trailing-space 규칙) 한글 띄어쓰기가 정확히 복원된다.
    (구 생성기는 `' '.join(ln.split())`로 줄끝 공백을 날린 게 버그였다.)
  - 폰트 크기로 역할 구분: 본문≈12, 소제목≈12 bold, 대제목≈16, 각주/캡션≈10, 미주마커≈6~8(위첨자).
  - 문단 시작 신호는 파일마다 다르다: 앞 공백(260113) 또는 x0 들여쓰기(260111). 둘 다 대응.
  - 표는 `find_tables()`로 영역을 감지해 텍스트를 제거(표는 이미지로 대체). 단 참고문헌·부록·초록
    페이지에서 오탐하므로 body 페이지에만 적용(CONFIG의 table_pages).
  - 그림/표 블록(캡션·출처·이미지)은 기존 `fulltext/{id}/index.html`에서 재사용하되,
    Pillow로 백지 이미지를 감지·제거하고, 그림이 백지뿐이면 같은 페이지의 다른 크롭으로 대체한다.
  - 미주 위첨자는 본문 링크(<sup>)로, 페이지 하단 각주는 목록으로 분리해 양방향 연결.
  - 참고문헌은 [N] 마커로 분리.

사용법 (반드시 저장소 루트에서 실행):
    python _build/reextract_fulltext.py <사례ID>          # fulltext/{id}/index.html 을 직접 갱신
    python _build/reextract_fulltext.py <사례ID> --dry     # 갱신 없이 통계만 출력(검토용)
    검증: python -m http.server 8000  →  브라우저에서 육안 확인  →  git diff 확인 후 커밋.

의존성: pip install PyMuPDF Pillow  /  pdf/{id}.pdf(저장소 내 사례별 분할 PDF)가 필요.
Windows: 파이썬 파일 IO는 utf-8 명시(본 스크립트는 io.open(...encoding='utf-8')로 처리).

새 사례 CONFIG 추가법:
  - body_start : 본문이 시작하는 PDF 페이지 인덱스(0-base). 첫 size≈16 장 제목 페이지.
      찾기: 아래 probe 스니펫으로 size>=15 헤딩의 페이지를 확인.
  - refs_head  : 참고문헌 대제목 텍스트('Reference' 또는 '참고문헌'). 이 h2에서 참고문헌 모드로 전환.
  - table_pages: 표영역 텍스트를 제거할 body 페이지 범위(초록·참고문헌·부록 제외). 보통 range(body_start, refs_page).
  캡션은 기존 HTML의 것을 재사용하므로 대개 추가 설정 불필요(캡션이 깨진 경우만 수동 보정).

probe 스니펫(페이지 구조 파악):
    import fitz; d=fitz.open('pdf/260111.pdf')
    for pi in range(d.page_count):
        for b in d[pi].get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                s=l['spans'][0]
                if s['size']>=15: print(pi, ''.join(x['text'] for x in l['spans'])[:40])
"""
import fitz, io, re, html, os, sys
from collections import Counter
from PIL import Image, ImageStat

# ---- 사례별 설정 (파일럿 완료: 260113, 260111) ----
CFG = {
    '260113': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 33))),
    '260111': dict(body_start=5, refs_head='참고문헌', table_pages=set(range(5, 43))),
    # 새 사례: dict(body_start=?, refs_head='참고문헌'|'Reference', table_pages=set(range(?, ?)))
}

CSS = '''.fnref { font-size: 11px; line-height: 0; }
.fnref a { color: var(--blue); text-decoration: none; padding: 0 1px; }
.ftnotes, .ftrefs { max-width: 820px; font-size: 13.5px; color: var(--gray-5); line-height: 1.7; padding-left: 24px; margin: 10px 0 26px; }
.ftnotes li, .ftrefs li { margin-bottom: 7px; }
.ftnotes { border-top: 1px solid var(--gray-2); padding-top: 16px; margin-top: 30px; }
.fnback { text-decoration: none; margin-left: 5px; color: var(--gray-4); }
'''


def build_body(CID, cfg):
    d = fitz.open(f'pdf/{CID}.pdf')

    # 표 영역(body 페이지만; find_tables는 밀집 텍스트에서 오탐)
    table_rects = {}
    for pi in cfg['table_pages']:
        if pi >= d.page_count:
            continue
        try:
            table_rects[pi] = [fitz.Rect(t.bbox) for t in d[pi].find_tables().tables]
        except Exception:
            table_rects[pi] = []

    def in_table(pi, y0, y1):
        cy = (y0 + y1) / 2
        return any(r.y0 - 2 <= cy <= r.y1 + 2 for r in table_rects.get(pi, []))

    # 문단 시작 판정용: 본문(size≈12) 줄들의 최빈 좌측 x(=이어짐 마진). 문단 시작은 더 들여씀.
    xc = Counter()
    for pi in range(cfg['body_start'], d.page_count):
        for b in d[pi].get_text('dict')['blocks']:
            if b.get('type', 0) != 0:
                continue
            for l in b.get('lines', []):
                if 11 <= l['spans'][0]['size'] < 13 and ''.join(x['text'] for x in l['spans']).strip():
                    xc[round(l['bbox'][0])] += 1
    body_left = xc.most_common(1)[0][0] if xc else 77

    def is_para_start(raw, x0):
        return raw[:1] == ' ' or x0 >= body_left + 6

    def spans_to_text(spans):
        out = []
        for s in spans:
            tx = s['text']
            if (s['flags'] & 1) and s['size'] < 10 and re.fullmatch(r'\d+', tx.strip()):
                out.append('{{FN' + tx.strip() + '}}')   # 미주 위첨자 -> 플레이스홀더
            else:
                out.append(tx)
        return ''.join(out)

    blocks, footnotes, refs_raw, para = [], {}, [], []
    fn_cur, mode = None, 'body'

    def flush():
        if para:
            t = ''.join(para).strip()
            if t:
                blocks.append(['p', t])
            para.clear()

    for pi in range(cfg['body_start'], d.page_count):
        for b in d[pi].get_text('dict')['blocks']:
            if b.get('type', 0) != 0:
                continue  # 이미지 블록은 문단을 끊지 않음(그림은 정렬로 배치)
            for l in b.get('lines', []):
                spans = l['spans']
                raw = ''.join(s['text'] for s in spans)
                if not raw.strip():
                    continue
                size = spans[0]['size']
                bold = bool(spans[0]['flags'] & 16) or 'Bold' in spans[0]['font']
                x0, y0, y1 = l['bbox'][0], l['bbox'][1], l['bbox'][3]
                rr = raw.rstrip()
                if size < 11 and x0 > 500 and y0 > 760 and re.fullmatch(r'\d+', rr.strip()):
                    continue  # 페이지 번호
                if 'CASE STUDY' in raw and 'KAIST' in raw:
                    continue  # 러닝 헤더
                if size < 11 and y0 > 665 and mode != 'ref':      # 페이지 하단 각주
                    m = re.match(r'\s*(\d+)\s+(.*)', raw)
                    if size <= 7 and m:
                        fn_cur = int(m.group(1)); footnotes[fn_cur] = m.group(2)
                    elif fn_cur is not None:
                        footnotes[fn_cur] += raw
                    continue
                fn_cur = None
                if mode == 'body' and in_table(pi, y0, y1) and size < 13:
                    continue  # 표 영역 텍스트 제거
                txt = spans_to_text(spans).rstrip()
                if size >= 15:                                     # 대제목
                    flush()
                    mode = 'ref' if cfg['refs_head'] in txt else 'body'
                    blocks.append(['h2', txt]); continue
                if mode == 'ref':
                    refs_raw.append((round(x0), raw)); continue
                if 11.5 < size < 13 and bold and re.match(r'^\d+(\.\d+)*\.?\s', txt):
                    flush(); blocks.append(['h3', txt.rstrip('.')]); continue   # 소제목
                if re.match(r'^<\s*(그림|표)\s*\d', txt) or (re.match(r'^(그림|표)\s*\d+[\.\s]', txt) and size < 11.5):
                    flush(); continue                              # 캡션 라인 제거(그림 블록은 재사용)
                if re.match(r'^\s*출처\s*[:：]', txt):
                    continue                                       # 출처 라인 제거
                if 11 <= size < 13:                                # 본문
                    if is_para_start(raw, x0):
                        flush()
                    para.append(spans_to_text(spans))
    flush()
    return blocks, footnotes, refs_raw


def figure_blocks(CID):
    """기존 HTML에서 그림/표 블록(캡션·출처·이미지) 재사용 + 백지 이미지 제거/대체."""
    _blank = {}

    def is_blank(p):
        if p not in _blank:
            try:
                st = ImageStat.Stat(Image.open(p).convert('L'))
                _blank[p] = (st.mean[0] > 252 and st.stddev[0] < 3)
            except Exception:
                _blank[p] = False
        return _blank[p]

    cur = io.open(f'fulltext/{CID}/index.html', encoding='utf-8').read()
    main = re.search(r'<main[^>]*>(.*?)</main>', cur, re.S).group(1)
    items = re.findall(
        r'<p class="ftcap">(.*?)</p>|<p class="ftsrc">(.*?)</p>|<figure class="ftfig"><img src="([^"]+)"[^>]*></figure>|<p>(.*?)</p>',
        main, re.S)
    despace = lambda s: re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', s))
    figs, sig, g = [], None, None
    for cap, src, img, body in items:
        if img:
            g = g or {'cap': None, 'src': None, 'imgs': [], 'sig': sig}
            g['imgs'].append(img)
        elif cap:
            if g and g['imgs']:
                figs.append(g); g = None
            g = g or {'cap': None, 'src': None, 'imgs': [], 'sig': sig}
            g['cap'] = html.unescape(re.sub(r'<[^>]+>', '', cap)).strip()
        elif src:
            g = g or {'cap': None, 'src': None, 'imgs': [], 'sig': sig}
            g['src'] = html.unescape(re.sub(r'<[^>]+>', '', src)).strip()
        elif body:
            b2 = re.sub(r'<[^>]+>', '', body).strip()
            if not re.match(r'^[<\[]?\s*(그림|표)\s*\d', b2):
                sig = despace(b2)[-30:]
    if g and g['imgs']:
        figs.append(g)

    imgdir = f'fulltext/{CID}/img'
    allcrops = sorted(os.listdir(imgdir))
    used = set()
    for f in figs:
        good = [im for im in f['imgs'] if not is_blank(f'fulltext/{CID}/' + im)]
        if not good:  # 백지뿐 -> 같은 페이지 다른 크롭 탐색
            for im in f['imgs']:
                m = re.match(r'img/(f-\d+)', im)
                page = m.group(1) if m else None
                for c in allcrops:
                    cp = f'img/{c}'
                    if page and c.startswith(page) and cp not in used and not is_blank(f'{imgdir}/{c}'):
                        good = [cp]; break
                if good:
                    break
        for im in good:
            used.add(im)
        f['imgs'] = good
    return [f for f in figs if f['imgs']]


def assemble(CID, cfg, blocks, footnotes, refs_raw, figs):
    esc = lambda t: html.escape(t, quote=False)
    fn_sup = lambda t: re.sub(
        r'\{\{FN(\d+)\}\}',
        lambda m: f'<sup class="fnref" id="fnref-{m.group(1)}"><a href="#fn-{m.group(1)}">{m.group(1)}</a></sup>', t)
    despace = lambda s: re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', s))

    # 그림 배치: 문서 순서(단조) 시그니처 정렬
    para_idx = [(i, despace(b[1])) for i, b in enumerate(blocks) if b[0] == 'p']
    fig_after, last = {}, -1
    for f in figs:
        tgt, s = None, f['sig']
        if s:
            for i, dp in para_idx:
                if i < last:
                    continue
                if s in dp or (len(s) >= 15 and s[-15:] in dp):
                    tgt = i; break
        if tgt is None:
            tgt = last if last >= 0 else (para_idx[0][0] if para_idx else 0)
        last = tgt
        fig_after.setdefault(tgt, []).append(f)

    out = []
    for idx, (kind, text) in enumerate(blocks):
        if kind == 'h2':
            out.append(f'<h2>{esc(text)}</h2>')
        elif kind == 'h3':
            out.append(f'<h3>{esc(text)}</h3>')
        else:
            out.append(f'<p>{fn_sup(esc(text))}</p>')
        for f in fig_after.get(idx, []):
            if f['cap']:
                out.append(f'<p class="ftcap">{esc(f["cap"])}</p>')
            if f['src']:
                out.append(f'<p class="ftsrc">{esc(f["src"])}</p>')
            for im in f['imgs']:
                out.append(f'<figure class="ftfig"><img src="{im}" alt=""></figure>')
    if footnotes:
        out.append('<h2>각주</h2>'); out.append('<ol class="ftnotes">')
        for n in sorted(footnotes):
            body = esc(re.sub(r'\s+', ' ', footnotes[n]).strip())
            out.append(f'<li id="fn-{n}">{body} <a class="fnback" href="#fnref-{n}">↩</a></li>')
        out.append('</ol>')
    if refs_raw:
        out.append(f'<h2>{esc(cfg["refs_head"])}</h2>')
        blob = re.sub(r'\s+', ' ', ' '.join(raw.strip() for _x, raw in refs_raw))
        parts = re.split(r'\[(\d+)\]', blob)
        if len(parts) > 2:
            out.append('<ol class="ftrefs">')
            it = iter(parts[1:])
            for _num, txt in zip(it, it):
                out.append(f'<li>{esc(txt.strip())}</li>')
            out.append('</ol>')
        else:
            out.append(f'<p class="ftsrc" style="text-align:left">{esc(blob.strip())}</p>')
    return '\n'.join(out)


def apply_to_file(CID, body):
    path = f'fulltext/{CID}/index.html'
    cur = io.open(path, encoding='utf-8').read()
    if '.ftnotes' not in cur:
        cur = cur.replace('</style>', CSS + '</style>', 1)
    cur = re.sub(r'(<main[^>]*>).*?(</main>)',
                 lambda m: m.group(1) + '\n' + body + '\n' + m.group(2), cur, flags=re.S)
    io.open(path, 'w', encoding='utf-8').write(cur)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CFG:
        print("usage: python _build/reextract_fulltext.py <CID> [--dry]")
        print("known CIDs:", ', '.join(CFG)); sys.exit(1)
    CID = sys.argv[1]
    dry = '--dry' in sys.argv
    cfg = CFG[CID]
    blocks, footnotes, refs_raw = build_body(CID, cfg)
    figs = figure_blocks(CID)
    body = assemble(CID, cfg, blocks, footnotes, refs_raw, figs)
    print(f"CID {CID}: blocks={len(blocks)} figs={len(figs)} footnotes={len(footnotes)} ref_lines={len(refs_raw)}")
    if dry:
        print("(--dry: 파일 미갱신)")
    else:
        apply_to_file(CID, body)
        print(f"applied -> fulltext/{CID}/index.html")


if __name__ == '__main__':
    main()
