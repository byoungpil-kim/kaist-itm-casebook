# -*- coding: utf-8 -*-
"""230205(진기호) 그림·표 위치 재확인 및 재렌더.

이 원고는 캡션이 그림/표 '위'에 오고, 캡션이 페이지 끝이면 그림은 다음 쪽 머리에 온다.
캡션 바로 아래(또는 다음 쪽 머리)의 이미지·표 영역을 clip 렌더해 캡션과 1:1로 맞춘다.
목차(그림 차례/표 차례) 페이지의 캡션 목록은 건너뛴다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '230205'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
BODY_START = 3                      # p4 하단(제1장 서론)부터 본문 — p3·p4 상단은 차례
DPI = 200
CAP = re.compile(r'^\s*<\s*(그림|표)\s*(\d+)\s*>')
SRC = re.compile(r'^\s*<\s*출처\s*>|^\s*출처\s*[:：]')
d = fitz.open(f'pdf/{CID}.pdf')
IMGDIR = f'fulltext/{CID}/img'


def lines(pi):
    out = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans'])
            if not t.strip():
                continue
            if re.fullmatch(r'\d{1,3}', t.strip()) and l['bbox'][1] > d[pi].rect.height - 100:
                continue                      # 쪽번호
            out.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                            t=t.strip(), sz=l['spans'][0]['size']))
    out.sort(key=lambda a: (a['y'], a['x']))
    return out


def images(pi):
    return [fitz.Rect(b['bbox']) for b in d[pi].get_text('dict')['blocks'] if b.get('type') == 1]


def drawrects(pi):
    out = []
    for x in d[pi].get_drawings():
        r = fitz.Rect(x['rect'])
        if r.width > 40 and r.height > 3 and r.width < d[pi].rect.width:
            out.append(r)
    return out


def region(pi, top):
    """top(캡션 아래 또는 페이지 머리)부터 그림/표 영역. 없으면 None."""
    PH = d[pi].rect.height
    L = lines(pi)
    imgs = [r for r in images(pi) if top - 2 <= r.y0]
    inside = lambda y: any(r.y0 - 2 <= y <= r.y1 - 2 for r in imgs)   # 그림 위에 얹힌 출처 줄
    bottom = PH - 105
    for ln in L:                                  # 본문/출처/다음 캡션 앞에서 끊는다
        if ln['y'] <= top + 1 or inside(ln['y']):
            continue
        if CAP.match(ln['t']) or SRC.match(ln['t']) or (ln['sz'] >= 11.5 and ln['x'] < 120):
            bottom = min(bottom, ln['y'] - 4); break
    rects = [r for r in images(pi) + drawrects(pi) if top - 2 <= r.y0 <= bottom + 6]
    # 표는 이미지가 아니라 텍스트+선으로 그려지므로 작은 글씨 줄도 영역에 포함
    txt = [ln for ln in L if top + 1 < ln['y'] and (ln['y1'] <= bottom + 3 or inside(ln['y']))]
    if not rects and not txt:
        return None
    xs0 = [r.x0 for r in rects] + [t['x'] for t in txt]
    xs1 = [r.x1 for r in rects] + [t['x1'] for t in txt]
    ys1 = [r.y1 for r in rects] + [t['y1'] for t in txt]
    r = (min(xs0) - 6, top + 2, max(xs1) + 6, max(ys1) + 4)
    if r[2] - r[0] < 60 or r[3] - r[1] < 25:
        return None
    return r


found, seen = [], set()
for pi in range(BODY_START, d.page_count):
    L = lines(pi)
    for i, ln in enumerate(L):
        m = CAP.match(ln['t'])
        if not m or (pi == 3 and ln['y'] < 500):        # p4 상단은 그림 차례 목록
            continue
        key = (m.group(1), int(m.group(2)))
        if key in seen:
            continue
        r, page = region(pi, ln['y1']), pi
        if r is None and pi + 1 < d.page_count:          # 캡션이 페이지 끝 → 다음 쪽 머리
            r, page = region(pi + 1, 80), pi + 1
        if r is None:
            print(f"  !! 영역 못 찾음 {key}")
            continue
        seen.add(key)
        found.append(dict(kind=key[0], num=key[1], cap=ln['t'], cap_page=pi + 1, page=page + 1,
                          rect=[round(v, 1) for v in r]))

os.makedirs(IMGDIR, exist_ok=True)
for f in found:
    name = ('fig%02d' if f['kind'] == '그림' else 'tab%02d') % f['num'] + '.webp'
    pix = d[f['page'] - 1].get_pixmap(clip=fitz.Rect(*f['rect']), dpi=DPI)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        os.path.join(IMGDIR, name), 'WEBP', quality=90)
    f['img'] = 'img/' + name

io.open(f'{SP}/figs_{CID}.json', 'w', encoding='utf-8').write(
    json.dumps(found, ensure_ascii=False, indent=1))
figs = [f['num'] for f in found if f['kind'] == '그림']
tabs = [f['num'] for f in found if f['kind'] == '표']
print(f"캡션 {len(found)}개 | 그림 {sorted(figs)}")
print(f"                | 표 {sorted(tabs)}")
