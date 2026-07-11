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

# ---- 사례별 설정 ----
# body_start: 본문 첫 장(章) 페이지(0-base). refs_head: 참고문헌 대제목(공백 무시 매칭).
# table_pages: 표영역 텍스트 제거 범위(초록·목차·부록·참고문헌 제외).
CFG = {
    '260113': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 33))),
    '260111': dict(body_start=5, refs_head='참고문헌', table_pages=set(range(5, 43))),
    '200104': dict(body_start=4, refs_head='참고문헌', table_pages=set(range(4, 29))),
    '210203': dict(body_start=4, refs_head='참고자료', table_pages=set(range(4, 50))),
    '210204': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 29))),
    '220201': dict(body_start=4, refs_head='Reference', table_pages=set(range(4, 42))),
    '220210': dict(body_start=4, refs_head='Reference', table_pages=set(range(4, 37))),
    '230101': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 24))),
    '230104': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 57))),
    '230107': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 23))),
    '230108': dict(body_start=4, refs_head='Reference', table_pages=set(range(4, 36))),
    '230113': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 35))),
    '230205': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 41))),
    '230213': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 50))),
    '230214': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 25))),
    '230216': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 41))),
    '230217': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 30))),
    '240102': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 31))),
    '240105': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 29))),
    '240109': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 27))),
    '240204': dict(body_start=7, refs_head='Reference', table_pages=set(range(7, 47))),
    '240205': dict(body_start=6, refs_head='Reference', table_pages=set(range(6, 48))),
    '240207': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 32))),
    '240210': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 33))),
    '250103': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 35))),
    '250108': dict(body_start=2, refs_head='Reference', table_pages=set(range(2, 76))),
    '250110': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 49))),
    '250111': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 45))),
    '250205': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 48))),
    '250215': dict(body_start=5, refs_head='Reference', table_pages=set(range(5, 49))),
    '260108': dict(body_start=6, refs_head='Reference', table_pages=set(range(6, 81))),
    # 250210: 제1장 서론 헤딩이 size10 소자체라 서론이 p4에서 시작(제2장부터 size16).
    '250210': dict(body_start=4, refs_head='Reference', table_pages=set(range(4, 37))),
    # 230211: 본문·참고문헌 헤딩이 모두 size10 소자체 → body_size 지정 필요.
    '230211': dict(body_start=4, refs_head='Reference', body_size=10, table_pages=set(range(4, 38))),
    # 재추출 부적합(복잡 레이아웃·삽화 텍스트 다수로 PyMuPDF가 본문을 조각으로 읽어 문단 폭발) →
    # 기존 gen_fulltext2 산출물 유지. CFG는 참고용(수동 실행해도 품질 미달):
    #   '240209': dict(body_start=4, refs_head='Reference', table_pages=set(range(4, 62))),
    #   '260105': dict(body_start=3, refs_head='Reference', table_pages=set(range(3, 37))),
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
    # 페이지 전체를 표로 오탐(높이>70%)하면 본문이 통째로 제거되므로 그런 rect는 무시한다.
    table_rects = {}
    for pi in cfg['table_pages']:
        if pi >= d.page_count:
            continue
        ph = d[pi].rect.height
        try:
            table_rects[pi] = [fitz.Rect(t.bbox) for t in d[pi].find_tables().tables
                               if fitz.Rect(t.bbox).height <= 0.7 * ph]
        except Exception:
            table_rects[pi] = []

    def in_table(pi, y0, y1):
        cy = (y0 + y1) / 2
        return any(r.y0 - 2 <= cy <= r.y1 + 2 for r in table_rects.get(pi, []))

    bs = cfg.get('body_size', 12)          # 본문 폰트 크기(기본 12; 소자체 문서는 CFG로 지정)
    BLO, BHI = bs - 1, bs + 1               # 본문 크기 하/상한

    # 문단 시작 판정용: 본문 줄들의 최빈 좌측 x(=이어짐 마진). 문단 시작은 더 들여씀.
    xc = Counter()
    for pi in range(cfg['body_start'], d.page_count):
        for b in d[pi].get_text('dict')['blocks']:
            if b.get('type', 0) != 0:
                continue
            for l in b.get('lines', []):
                if BLO <= l['spans'][0]['size'] < BHI and ''.join(x['text'] for x in l['spans']).strip():
                    xc[round(l['bbox'][0])] += 1
    body_left = xc.most_common(1)[0][0] if xc else 77
    ns = lambda s: re.sub(r'\s+', '', s)   # 공백 무시 비교(참  고  문  헌 등)

    def is_para_start(raw, x0):
        return raw[:1] == ' ' or x0 >= body_left + 6

    # 직전 문단이 문장 종결로 끝났는지(페이지 넘김 지점의 오분할 방지).
    _SENT_END = tuple('.?!’”」』）)') + ('다', '요', '함', '음', '임', '됨', '것', '라', '까')
    def sentence_ended(buf):
        t = ''.join(buf).rstrip()
        return (not t) or t.endswith(_SENT_END)

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
            # 숫자·절번호만 남은 문단(미주 마커·분리된 소제목 번호 등)은 버림
            if t and not re.fullmatch(r'[\d\s.\-–)]+', t):
                blocks.append(['p', t])
            para.clear()

    stop = False
    for pi in range(cfg['body_start'], d.page_count):
        if stop:
            break
        for b in d[pi].get_text('dict')['blocks']:
            if stop:
                break
            if b.get('type', 0) != 0:
                continue  # 이미지 블록은 문단을 끊지 않음(그림은 정렬로 배치)
            for l in b.get('lines', []):
                spans = l['spans']
                raw = ''.join(s['text'] for s in spans)
                if not raw.strip():
                    continue
                if '사례연구 모음집' in raw:
                    stop = True; break   # 본문 뒤에 남은 학기 모음집 표지 → 이후 전부 무시
                size = spans[0]['size']
                bold = bool(spans[0]['flags'] & 16) or 'Bold' in spans[0]['font']
                x0, y0, y1 = l['bbox'][0], l['bbox'][1], l['bbox'][3]
                rr = raw.rstrip()
                if size < 11 and x0 > 500 and y0 > 760 and re.fullmatch(r'\d+', rr.strip()):
                    continue  # 페이지 번호
                if 'CASE STUDY' in raw and 'KAIST' in raw:
                    continue  # 러닝 헤더
                if size < BLO and y0 > 665 and mode != 'ref':     # 페이지 하단 각주
                    m = re.match(r'\s*(\d+)\s+(.*)', raw)
                    if size <= 7 and m:
                        fn_cur = int(m.group(1)); footnotes[fn_cur] = m.group(2)
                    elif fn_cur is not None:
                        footnotes[fn_cur] += raw
                    continue
                fn_cur = None
                if mode == 'body' and in_table(pi, y0, y1) and size < BHI:
                    continue  # 표 영역 텍스트 제거
                txt = spans_to_text(spans).rstrip()
                if size >= 15:                                     # 대제목
                    if mode == 'ref':
                        continue   # 참고문헌 진입 후의 대형 텍스트(표지 잔여 등)는 본문 복귀 없이 무시
                    is_ref = ns(cfg['refs_head']) in ns(txt)
                    # 제목이 문자단위로 분리된 파일(240209·260105 등) 방어:
                    #   장 번호(숫자)만 떨어져 나온 조각은 앞 h2에 흡수, 문장부호 조각은 버림.
                    frag = txt.strip()
                    if not is_ref and mode != 'ref' and blocks and blocks[-1][0] == 'h2':
                        if re.fullmatch(r'\d+', frag):
                            blocks[-1][1] = (blocks[-1][1] + ' ' + frag).strip()
                            continue
                        if re.fullmatch(r'[.\-·:／/]+', frag):
                            continue
                    flush()
                    if is_ref:
                        mode = 'ref'; continue   # 참고문헌 대제목은 assemble()이 별도로 붙임(중복 방지)
                    mode = 'body'
                    blocks.append(['h2', txt]); continue
                # 참고문헌 헤딩이 본문과 같은 소자체(size<15)인 문서(230211 등) 대응
                if mode != 'ref' and len(txt.strip()) <= 15 and ns(txt) == ns(cfg['refs_head']):
                    flush(); mode = 'ref'; continue
                if mode == 'ref':
                    refs_raw.append((round(x0), raw)); continue
                # 소제목: 본문보다 크거나 같고 대제목(15)보다 작은 볼드 번호 제목.
                # (본문=소제목 동일 크기인 일반 문서와, 소제목이 더 큰 소자체 문서(230211 size14) 모두 대응)
                if bs - 0.5 <= size < 15 and bold and re.match(r'^\d+(\.\d+)*\.?\s', txt):
                    flush(); blocks.append(['h3', txt.rstrip('.')]); continue   # 소제목
                if re.match(r'^\s*[\[<]\s*(그림|표)\s*\d', txt) or (re.match(r'^\s*(그림|표)\s*\d+[\.\s]', txt) and size < 11.5):
                    flush(); continue                              # 캡션 라인 제거(그림 블록은 재사용, 앞공백·[·< 접두 포함)
                if re.match(r'^[\(（]?\s*출처\s*[:：]', txt):
                    continue                                       # 출처 라인 제거((출처: 포함)
                if BLO <= size < BHI:                              # 본문
                    tc = txt.strip()
                    if re.match(r'^[\(（]?\s*단위\s*[:：]', tc):
                        continue                                   # (단위: …) 표/차트 라벨 제거
                    if len(tc) < 45 and re.search(r'(작성|재인용)\s*[)）]\s*$', tc):
                        continue                                   # 캡션 출처 꼬리(…참고하여 본인 작성)) 잔재 제거
                    kor = len(re.findall(r'[가-힣]', tc))
                    if len(tc) >= 8 and kor < 4 and \
                       len(re.findall(r'[\d—\-.,%/\s]', tc)) / len(tc) > 0.75:
                        continue                                   # 수치·대시 위주 표 잔존 라인 제거
                    if is_para_start(raw, x0) and sentence_ended(para):
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
