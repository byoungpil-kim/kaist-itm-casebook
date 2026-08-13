# -*- coding: utf-8 -*-
"""240204(박아령) 그림·표 캡션↔이미지 재정렬.

이 원고는 캡션이 그림·표 **아래**에 오고, 나란히 놓인 그림들이 한 줄 캡션을 공유한다
(예: "<그림3. 제조업 내 기계산업 비중>  <그림4. 기계산업 분류>").
구 추출이 캡션-위로 가정하고 묶음 캡션도 한 장만 물려, 그림 2·4·6·8·9·11·13·17·28·30과
표 3·14가 사실상 사라져 있었다.

캡션 줄의 각 조각을 x좌표로, 그 위 이미지들을 x좌표로 정렬해 열끼리 짝짓는다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '240204'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
DPI = 200
ONE = re.compile(r'<\s*(그림|표)\s*(\d+)\s*\.')
d = fitz.open(f'pdf/{CID}.pdf')
IMGDIR = f'fulltext/{CID}/img'


def frags(pi):
    """병합하지 않은 줄 조각(묶음 캡션을 열별로 나누기 위해)."""
    out = []
    PH = d[pi].rect.height
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if not t or (re.fullmatch(r'\d{1,3}', t) and l['bbox'][1] > PH * 0.87):
                continue
            out.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                            t=t, sz=max(s['size'] for s in l['spans'])))
    return sorted(out, key=lambda a: (a['y'], a['x']))


def rects(pi):
    out = [fitz.Rect(b['bbox']) for b in d[pi].get_text('dict')['blocks']
           if b.get('type') == 1 and b['bbox'][3] - b['bbox'][1] > 15]
    for x in d[pi].get_drawings():
        r = fitz.Rect(x['rect'])
        if r.width > 40 and r.height > 10 and r.width < d[pi].rect.width - 20:
            out.append(r)
    return out


found = []
for pi in range(6, d.page_count):
    F = frags(pi)
    R = rects(pi)
    # 같은 y의 캡션 조각들을 한 묶음으로
    caps = [f for f in F if ONE.match(f['t'])]
    groups, cur = [], []
    for f in caps:
        if cur and abs(f['y'] - cur[-1]['y']) <= 4:
            cur.append(f)
        else:
            if cur:
                groups.append(cur)
            cur = [f]
    if cur:
        groups.append(cur)

    for g in groups:
        g.sort(key=lambda a: a['x'])
        ytop_cap = min(f['y'] for f in g)
        # 위 경계: 캡션 위의 본문 줄 아래
        top = 80.0
        for o in F:
            if o['y1'] >= ytop_cap - 2:
                continue
            if o['sz'] >= 11 and o['x'] < 110 and (o['x1'] - o['x']) > 300:
                top = max(top, o['y1'] + 4)
            elif ONE.match(o['t']):
                top = max(top, o['y1'] + 4)
        sel = sorted([r for r in R if r.y0 >= top - 8 and r.y1 <= ytop_cap - 1], key=lambda r: r.x0)
        if not sel and pi > 0:                      # 그림이 앞 쪽 하단에 있는 경우
            Rp = sorted(rects(pi - 1), key=lambda r: r.x0)
            Fp = frags(pi - 1)
            ytopp = max([o['y1'] for o in Fp if o['sz'] >= 11 and o['x'] < 110
                         and (o['x1'] - o['x']) > 300] or [80.0]) + 4
            sel = [r for r in Rp if r.y0 >= ytopp - 8]
            page = pi - 1
        else:
            page = pi
        if not sel:
            print(f"  !! 이미지 없음 p{pi+1} {[x['t'][:20] for x in g]}")
            continue
        # 캡션 조각 수와 이미지 수가 같으면 x순으로 1:1, 아니면 전체를 한 장으로
        if len(sel) == len(g):
            pairs = [([f], [r]) for f, r in zip(g, sel)]
        elif len(g) == 1:
            pairs = [(g, sel)]
        else:
            # 각 캡션 조각의 x중심에 가장 가까운 이미지들로 나눈다
            pairs = []
            for k, f in enumerate(g):
                cx = (f['x'] + f['x1']) / 2
                mine = [r for r in sel if r.x0 - 12 <= cx <= r.x1 + 12]
                if not mine:
                    mine = [min(sel, key=lambda r: abs((r.x0 + r.x1) / 2 - cx))]
                pairs.append(([f], mine))
        for fs, rs in pairs:
            m = ONE.match(fs[0]['t'])
            rect = (min(r.x0 for r in rs) - 5, min(r.y0 for r in rs) - 5,
                    max(r.x1 for r in rs) + 5, max(r.y1 for r in rs) + 5)
            found.append(dict(kind=m.group(1), num=int(m.group(2)), page=page + 1,
                              cap=fs[0]['t'], rect=[round(v, 1) for v in rect]))

os.makedirs(IMGDIR, exist_ok=True)
seen = set()
for f in found:
    key = (f['kind'], f['num'])
    if key in seen:
        continue
    seen.add(key)
    name = ('fig%02d' if f['kind'] == '그림' else 'tab%02d') % f['num'] + '.webp'
    pix = d[f['page'] - 1].get_pixmap(clip=fitz.Rect(*f['rect']), dpi=DPI)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        os.path.join(IMGDIR, name), 'WEBP', quality=90)
    f['img'] = 'img/' + name

found = [f for f in found if 'img' in f]
io.open(f'{SP}/figs_{CID}.json', 'w', encoding='utf-8').write(
    json.dumps(found, ensure_ascii=False, indent=1))
g = sorted(f['num'] for f in found if f['kind'] == '그림')
t = sorted(f['num'] for f in found if f['kind'] == '표')
print(f"그림 {g}\n표   {t}")
print("그림 누락:", sorted(set(range(1, 31)) - set(g)), "| 표 누락:", sorted(set(range(1, 16)) - set(t)))
