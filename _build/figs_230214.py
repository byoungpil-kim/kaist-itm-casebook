# -*- coding: utf-8 -*-
"""230214(장영준) 그림·표 재렌더.

이 원고는 캡션이 그림/표 '위'에 온다. 캡션은 10pt 가운데 정렬이고,
본문(12pt, x=76.6)에 섞인 "[그림 13]" 같은 상호참조는 캡션이 아니다.
그림 1·2는 한 캡션 줄에 나란히 있고 이미지가 좌우 두 장이므로 열별로 분리한다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '230214'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
DPI = 200
CAP = re.compile(r'^(그림|표)\s*(\d+)\s*[.．]\s*\S')
PAGENO = re.compile(r'^\d{1,3}$')
d = fitz.open(f'pdf/{CID}.pdf')
IMGDIR = f'fulltext/{CID}/img'


def lines(pi):
    out, PH = [], d[pi].rect.height
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if not t or (PAGENO.fullmatch(t) and l['bbox'][1] > PH - 120):
                continue
            out.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                            t=t, sz=l['spans'][0]['size']))
    out.sort(key=lambda a: (a['y'], a['x']))
    return out


def images(pi):
    return [fitz.Rect(b['bbox']) for b in d[pi].get_text('dict')['blocks'] if b.get('type') == 1]


def region(pi, top):
    """캡션 아래 그림/표 영역. 다음 본문 줄/캡션 앞에서 끊는다."""
    PH = d[pi].rect.height
    bottom = PH - 105
    for ln in lines(pi):
        if ln['y'] <= top + 1:
            continue
        body = ln['sz'] >= 15 or (ln['sz'] >= 11.5 and ln['x'] < 90 and (ln['x1'] - ln['x']) > 250)
        if CAP.match(ln['t']) or body:            # 본문은 x≈76.6에서 시작해 폭이 넓다(표 셀은 x≥97)
            bottom = min(bottom, ln['y'] - 5); break
    rects = [r for r in images(pi) if top - 2 <= r.y0 and r.y1 <= bottom + 8]
    if not rects:                       # 표 2처럼 이미지가 아니라 글자+선으로 그린 표
        cells = [ln for ln in lines(pi) if top + 1 < ln['y'] and ln['y1'] <= bottom + 3]
        draws = [fitz.Rect(x['rect']) for x in d[pi].get_drawings()
                 if fitz.Rect(x['rect']).width > 40 and top - 4 <= fitz.Rect(x['rect']).y0
                 and fitz.Rect(x['rect']).y1 <= bottom + 6]
        if not cells and not draws:
            return None, []
        xs0 = [c['x'] for c in cells] + [r.x0 for r in draws]
        xs1 = [c['x1'] for c in cells] + [r.x1 for r in draws]
        ys1 = [c['y1'] for c in cells] + [r.y1 for r in draws]
        return (min(xs0) - 8, top + 3, max(xs1) + 8, max(ys1) + 5), []
    r = (min(x.x0 for x in rects) - 5, top + 3,
         max(x.x1 for x in rects) + 5, max(x.y1 for x in rects) + 4)
    if r[2] - r[0] < 60 or r[3] - r[1] < 25:
        return None, []
    return r, rects


found, seen = [], set()
for pi in range(d.page_count):
    for ln in lines(pi):
        if ln['sz'] > 10.6:                    # 캡션은 10pt. 본문(12pt)의 "[그림 13]"은 제외
            continue
        nums = [(k, int(n)) for k, n in re.findall(r'(그림|표)\s*(\d+)\s*[.．]', ln['t'])]
        if not nums or not CAP.match(ln['t']):
            continue
        r, rects = region(pi, ln['y1'])
        if r is None:
            print(f"  !! 영역 못 찾음 {nums} p{pi+1}")
            continue
        if len(nums) == 2 and len(rects) >= 2:  # 좌우 2단 배치(그림 1·2)
            cols = sorted(rects, key=lambda a: a.x0)
            parts = re.split(r'(?=%s\s*%d\s*[.．])' % nums[1], ln['t'])
            for k, (kind, num) in enumerate(nums):
                if (kind, num) in seen:
                    continue
                seen.add((kind, num))
                rr = (cols[k].x0 - 4, top_ := r[1], cols[k].x1 + 4, cols[k].y1 + 4)
                found.append(dict(kind=kind, num=num, page=pi + 1, rect=[round(v, 1) for v in rr],
                                  cap=(parts[k].strip() if k < len(parts) else f'{kind} {num}.')))
            continue
        kind, num = nums[0]
        if (kind, num) in seen:
            continue
        seen.add((kind, num))
        found.append(dict(kind=kind, num=num, page=pi + 1, rect=[round(v, 1) for v in r], cap=ln['t']))

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
