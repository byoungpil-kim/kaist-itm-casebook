# -*- coding: utf-8 -*-
"""230211(이윤주) 그림·표 위치 재확인 및 재렌더.

이 원고는 캡션이 그림/표 '아래'에 온다(캡션 9pt, 본문 10pt). 출처는 캡션 괄호 안에 들어 있다.
캡션 위쪽의 이미지·표 영역을 clip 렌더해 캡션과 1:1로 맞춘다.
본문 중의 "(그림 6 참조)" 같은 상호참조는 캡션이 아니므로 제외한다
 — 캡션은 줄 전체가 '그림 N.' / '표 N.'으로 시작하는 9pt 줄이다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '230211'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
DPI = 200
CAP = re.compile(r'^(그림|표)\s*(\d+)\s*[.．]\s*\S')
SENT_END = ('다.', '다', '음.', '함.', '까?', '?', '.', '음', '함')


def bodyish(ln):
    """본문 줄인가 — 그림 영역의 위 경계가 된다.
    문단 마지막의 짧은 줄("되어있다.")도 본문이므로 폭만으로 판정하면 안 된다."""
    if ln['sz'] < 9.5 or ln['x'] > 105:
        return False
    return (ln['x1'] - ln['x']) > 120 or ln['t'].rstrip().endswith(SENT_END)
d = fitz.open(f'pdf/{CID}.pdf')
IMGDIR = f'fulltext/{CID}/img'
PAGENO = re.compile(r'^\d{1,3}$')


def lines(pi):
    out = []
    PH = d[pi].rect.height
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if not t or (PAGENO.fullmatch(t) and l['bbox'][1] > PH - 100):
                continue
            out.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                            t=t, sz=l['spans'][0]['size']))
    out.sort(key=lambda a: (a['y'], a['x']))
    return out


def images(pi):
    return [fitz.Rect(b['bbox']) for b in d[pi].get_text('dict')['blocks'] if b.get('type') == 1]


def drawrects(pi):
    out = []
    for x in d[pi].get_drawings():
        r = fitz.Rect(x['rect'])
        if r.width > 40 and r.height > 3 and r.width < d[pi].rect.width - 20:
            out.append(r)
    return out


def region_above(pi, cap_y, cap_line=None):
    """캡션 위쪽의 그림/표 영역. 위 경계는 직전 본문 줄 아래."""
    L = lines(pi)
    top = 80
    for ln in L:                                  # 캡션 위의 마지막 '본문 줄' 아래를 시작점으로
        if ln['y1'] >= cap_y - 2 or (cap_line and ln is cap_line):
            continue
        if CAP.match(ln['t']) or bodyish(ln):
            top = max(top, ln['y1'] + 3)
    rects = [r for r in images(pi) + drawrects(pi) if top - 6 <= r.y0 and r.y1 <= cap_y + 2]
    txt = [ln for ln in L if top - 2 < ln['y'] and ln['y1'] <= cap_y - 1]
    if not rects and not txt:
        return None
    xs0 = [r.x0 for r in rects] + [t['x'] for t in txt]
    xs1 = [r.x1 for r in rects] + [t['x1'] for t in txt]
    ys0 = [r.y0 for r in rects] + [t['y'] for t in txt]
    r = (min(xs0) - 6, min(ys0) - 4, max(xs1) + 6, cap_y - 2)
    if r[2] - r[0] < 60 or r[3] - r[1] < 25:
        return None
    return r


def region_prev_page_bottom(pi):
    """캡션이 페이지 머리에 있을 때, 앞 페이지 하단의 그림 영역."""
    L = lines(pi)
    PH = d[pi].rect.height
    top = 80
    for ln in L:
        if bodyish(ln):
            top = max(top, ln['y1'] + 3)
    rects = [r for r in images(pi) + drawrects(pi) if r.y0 >= top - 6]
    if not rects:
        return None
    r = (min(x.x0 for x in rects) - 6, min(x.y0 for x in rects) - 4,
         max(x.x1 for x in rects) + 6, max(x.y1 for x in rects) + 4)
    if r[2] - r[0] < 60 or r[3] - r[1] < 25:
        return None
    return r


found, seen = [], set()
for pi in range(d.page_count):
    L = lines(pi)
    for ln in L:
        m = CAP.match(ln['t'])
        if not m or ln['sz'] > 10.5:              # 목차(16pt 등) 제외. 캡션은 본문과 같은 10pt
            continue
        key = (m.group(1), int(m.group(2)))
        if key in seen:
            continue
        r, page = region_above(pi, ln['y'], ln), pi
        if r is None and pi > 0:                  # 그림이 앞 페이지 하단에 있는 경우
            r, page = region_prev_page_bottom(pi - 1), pi - 1
        if r is None:
            print(f"  !! 영역 못 찾음 {key} p{pi+1}")
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
print(f"캡션 {len(found)}개 | 그림 {sorted(f['num'] for f in found if f['kind']=='그림')}")
print(f"              | 표 {sorted(f['num'] for f in found if f['kind']=='표')}")
