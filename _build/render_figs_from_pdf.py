# -*- coding: utf-8 -*-
"""fulltext 그림 재구성 (1/2): PDF에서 캡션 아래 '그래픽 bbox'를 clip 렌더링.

사용법(저장소 루트):
    python _build/render_figs_from_pdf.py <사례ID> [--dry]   # 그림 렌더 + 매니페스트
    python _build/place_figs_in_fulltext.py <사례ID> [--dry] # 캡션·출처와 함께 본문에 배치
    (--dry는 파일을 바꾸지 않고 결과만 보고. 중간 산출물은 _build/_figtmp/)

적용 대상: 본문과 그림이 한 줄에 나란히 놓여(2단 배치) 임베디드 이미지 추출이
실패하는 원고. 210203(강보배)에서 캡션↔그림 밀림·좌우 중 한쪽 누락·이미지 0장
문제를 이 방식으로 해결했다. 캡션 형식은 [그림 N]/[차트 N]/[표 N] 기준.

배경: 이 문서는 본문(좌)과 그림(우)이 같은 줄에 나란히 놓인 구간이 많아
      임베디드 이미지 추출/자동 크롭이 실패했다(캡션-그림 밀림, 누락).
      docx도 차트가 네이티브 객체·표가 실제 표라 이미지가 없다.
      → 캡션 아래의 벡터 도형+이미지 bbox를 합쳐 그 영역만 렌더한다.
캡션 규칙: 캡션이 그림 위, 출처는 그림 아래.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '210203'
SP = os.environ.get('FIGTMP', '_build/_figtmp')
os.makedirs(SP, exist_ok=True)
CAP = re.compile(r'^\[(그림|차트|표)\s*(\d+)\]\s*(.+)$')
SRC = re.compile(r'^\(?\s*출처\s*[:：]')
DPI = 200
DRY = '--dry' in sys.argv

d = fitz.open(f'pdf/{CID}.pdf')
records = []

for pi in range(d.page_count):
    pg = d[pi]
    PH, PW = pg.rect.height, pg.rect.width
    lines = []
    for b in pg.get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t:
                lines.append(dict(y0=l['bbox'][1], y1=l['bbox'][3], x0=l['bbox'][0],
                                  x1=l['bbox'][2], sz=l['spans'][0]['size'], t=t))
    lines.sort(key=lambda a: a['y0'])
    # 그래픽 후보(벡터 도형 + 이미지), 페이지 테두리/머리말 선 제외
    gfx = []
    for x in pg.get_drawings():
        r = fitz.Rect(x['rect'])
        if r.width > 3 and r.height > 3 and not (r.width > 480 and r.height > 600):
            gfx.append(r)
    for b in pg.get_text('dict')['blocks']:
        if b.get('type') == 1:
            gfx.append(fitz.Rect(b['bbox']))

    for ln in lines:
        m = CAP.match(ln['t'])
        if not m or ln['sz'] > 11.5:
            continue
        kind, num = m.group(1), int(m.group(2))
        cy, cx0, cx1 = ln['y1'], ln['x0'], ln['x1']
        # 캡션 아래 그래픽을 근접 클러스터로 묶기
        cands = sorted([r for r in gfx if r.y1 > cy + 1 and r.y0 < cy + 430],
                       key=lambda r: r.y0)
        def text_region():
            # 도형·이미지가 없는 텍스트 표(예: 표 7·8) → 캡션 아래 텍스트 영역으로 폴백
            bottom = PH - 60
            for l2 in lines:
                if l2['y0'] <= cy:
                    continue
                if SRC.match(l2['t']):
                    bottom = min(bottom, l2['y0'] - 2); break
                if l2['sz'] >= 11.5 and l2['x0'] < 110 and (l2['y0'] - cy) > 8:
                    bottom = min(bottom, l2['y0'] - 2); break
                if CAP.match(l2['t']) and l2['sz'] <= 11.5:
                    bottom = min(bottom, l2['y0'] - 2); break
            if bottom - cy < 40:
                return None
            inner = [l2 for l2 in lines if cy < l2['y0'] < bottom]
            if not inner:
                return None
            return fitz.Rect(min(l2['x0'] for l2 in inner) - 6, cy + 2,
                             max(l2['x1'] for l2 in inner) + 6, bottom)

        box = None
        for r in cands:
            if box is None:
                if r.y0 > cy + 60:      # 캡션과 너무 떨어진 첫 요소는 다른 그림
                    break
                box = fitz.Rect(r)
            elif r.y0 <= box.y1 + 22:   # 세로 간격이 작으면 같은 그림
                box |= r
            else:
                break
        if box is None or box.height < 30:
            box = text_region()
        if box is None or box.height < 30:
            continue
        # 출처 줄이 박스 안에 걸리면 그 위로 자르기
        for l2 in lines:
            if SRC.match(l2['t']) and box.y0 < l2['y0'] < box.y1:
                box.y1 = min(box.y1, l2['y0'] - 2)
        box = fitz.Rect(max(box.x0 - 4, 30), max(box.y0 - 3, cy + 2),
                        min(box.x1 + 4, PW - 30), min(box.y1 + 3, PH - 55))
        src = next((l2['t'] for l2 in lines
                    if SRC.match(l2['t']) and 0 < l2['y0'] - box.y1 < 60), None)
        records.append(dict(page=pi, kind=kind, num=num, cap=ln['t'], src=src, rect=tuple(box)))

# 같은 (종류,번호) 중복이면 면적이 큰 쪽 채택(목차·본문참조 방지)
best = {}
for r in records:
    k = (r['kind'], r['num'])
    area = (r['rect'][2] - r['rect'][0]) * (r['rect'][3] - r['rect'][1])
    if k not in best or area > best[k]['_a']:
        r['_a'] = area; best[k] = r
records = sorted(best.values(), key=lambda r: (r['page'], r['rect'][1]))

outdir = f'{SP}/figtest' if DRY else f'fulltext/{CID}/img'
os.makedirs(outdir, exist_ok=True)
manifest = []
for r in records:
    tag = 'fig' if r['kind'] == '그림' else ('cht' if r['kind'] == '차트' else 'tbl')
    name = f"{tag}{r['num']:02d}.webp"
    pix = d[r['page']].get_pixmap(clip=fitz.Rect(*r['rect']), dpi=DPI)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        os.path.join(outdir, name), 'WEBP', quality=90)
    manifest.append(dict(name=name, page=r['page'] + 1, kind=r['kind'], num=r['num'],
                         y=round(r['rect'][1]), cap=r['cap'], src=r['src'],
                         w=round(r['rect'][2] - r['rect'][0]), h=round(r['rect'][3] - r['rect'][1])))

io.open(f'{SP}/figman203.json', 'w', encoding='utf-8').write(json.dumps(manifest, ensure_ascii=False, indent=1))
with io.open(f'{SP}/figman203.txt', 'w', encoding='utf-8') as o:
    for m in manifest:
        o.write(f"{m['name']:11} p{m['page']:02d} {m['w']:3}x{m['h']:3} | {m['cap'][:56]} | {(m['src'] or '')[:30]}\n")
print(f"{'DRY ' if DRY else ''}렌더 {len(manifest)}개 -> {outdir}")
