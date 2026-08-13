# -*- coding: utf-8 -*-
"""250108(여진환) 그림·표 캡션↔이미지 재정렬.

이 원고는 "그림 N." / "표 N." 캡션이 모두 그림·표 **아래**에 온다. 구 추출이 캡션-위로
가정해 각 캡션이 '다음' 이미지를 물고 있었다(그림 29가 그림 30의 이미지를 표시하는 식).
캡션 바로 위 영역(이미지·도형·표 텍스트)을 clip 렌더해 1:1로 맞춘다.
표 6·7·9처럼 네이티브 표는 이미지가 없으므로 글자+괘선 영역을 렌더한다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '250108'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
DPI = 200
CAP = re.compile(r'^\s*(그림|표)\s*(\d+)\s*\.\s*\S')
SRC = re.compile(r'^\s*(출처|자료)\s*[:：]|^\s*\*')
d = fitz.open(f'pdf/{CID}.pdf')
IMGDIR = f'fulltext/{CID}/img'


def lines(pi):
    PH = d[pi].rect.height
    out = []
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
        if r.width > 30 and r.height > 3 and r.width < d[pi].rect.width - 20:
            out.append(r)
    return out


found = []
for pi in range(4, d.page_count):
    L = lines(pi)
    R = rects(pi)
    for i, ln in enumerate(L):
        m = CAP.match(ln['t'])
        if not m or ln['sz'] > 13:
            continue
        # 위 경계: 캡션 바로 위의 '본문 줄'(넓고 왼쪽에서 시작) 아래
        top = 80.0
        for o in L:
            if o['y1'] >= ln['y'] - 2:
                continue
            body = o['sz'] >= 11 and o['x'] < 110 and (o['x1'] - o['x']) > 260
            if body or CAP.match(o['t']) or SRC.match(o['t']):
                top = max(top, o['y1'] + 4)
        sel = [r for r in R if r.y0 >= top - 8 and r.y1 <= ln['y'] - 1]
        txt = [o for o in L if top - 2 < o['y'] and o['y1'] <= ln['y'] - 2]
        if not sel and not txt:
            print(f'  !! 영역 없음 {m.group(1)}{m.group(2)} p{pi+1}')
            continue
        xs0 = [r.x0 for r in sel] + [o['x'] for o in txt]
        xs1 = [r.x1 for r in sel] + [o['x1'] for o in txt]
        ys0 = [r.y0 for r in sel] + [o['y'] for o in txt]
        rect = (min(xs0) - 6, min(ys0) - 5, max(xs1) + 6, ln['y'] - 3)
        if rect[2] - rect[0] < 60 or rect[3] - rect[1] < 30:
            print(f'  !! 영역 작음 {m.group(1)}{m.group(2)} p{pi+1}')
            continue
        parts = [(pi, [round(v, 1) for v in rect])]
        # 캡션이 없는 앞 쪽들은 이 캡션에 딸린 내용이 이어진 것으로 본다(여러 쪽에 걸친 표·도표)
        if i == 0 or all(not CAP.match(o['t']) for o in L[:i]):
            q = pi - 1
            while q > 4 and len(parts) < 5:
                Lq, Rq = lines(q), rects(q)
                if any(CAP.match(o['t']) for o in Lq):
                    break
                # 본문 문단이 있는 쪽이면, 그 아래 남은 부분만 표/도표의 앞부분으로 본다
                bodys = [o for o in Lq if o['sz'] >= 11 and o['x'] < 110 and (o['x1'] - o['x']) > 260]
                if bodys:
                    # 문단 마지막 짧은 줄('미친다.')까지 포함해 경계를 잡는다
                    ylast = max(o['y1'] for o in bodys)
                    ytop = max([o['y1'] for o in Lq if o['sz'] >= 11 and o['x'] < 110
                                and o['y'] <= ylast + 30] or [ylast]) + 6
                    Rq = [r for r in Rq if r.y0 >= ytop - 4]
                    Lq = [o for o in Lq if o['y'] >= ytop - 2]
                    if Rq or Lq:
                        xs0 = [r.x0 for r in Rq] + [o['x'] for o in Lq]
                        xs1 = [r.x1 for r in Rq] + [o['x1'] for o in Lq]
                        ys0 = [r.y0 for r in Rq] + [o['y'] for o in Lq]
                        ys1 = [r.y1 for r in Rq] + [o['y1'] for o in Lq]
                        if max(ys1) - min(ys0) > 40:
                            parts.insert(0, (q, [round(min(xs0) - 6, 1), round(min(ys0) - 5, 1),
                                                 round(max(xs1) + 6, 1), round(max(ys1) + 5, 1)]))
                    break
                if not Rq and not Lq:
                    break
                xs0 = [r.x0 for r in Rq] + [o['x'] for o in Lq]
                xs1 = [r.x1 for r in Rq] + [o['x1'] for o in Lq]
                ys0 = [r.y0 for r in Rq] + [o['y'] for o in Lq]
                ys1 = [r.y1 for r in Rq] + [o['y1'] for o in Lq]
                parts.insert(0, (q, [round(min(xs0) - 6, 1), round(min(ys0) - 5, 1),
                                     round(max(xs1) + 6, 1), round(max(ys1) + 5, 1)]))
                q -= 1
        found.append(dict(kind=m.group(1), num=int(m.group(2)), page=pi + 1, cap=ln['t'],
                          rect=[round(v, 1) for v in rect], parts=parts))

os.makedirs(IMGDIR, exist_ok=True)
for f in found:
    base = ('fig%02d' if f['kind'] == '그림' else 'tab%02d') % f['num']
    imgs = []
    for k, (pg, rect) in enumerate(f['parts']):
        name = base + (chr(97 + k) if len(f['parts']) > 1 else '') + '.webp'
        pix = d[pg].get_pixmap(clip=fitz.Rect(*rect), dpi=DPI)
        Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
            os.path.join(IMGDIR, name), 'WEBP', quality=90)
        imgs.append('img/' + name)
    f['imgs'] = imgs

io.open(f'{SP}/figs_{CID}.json', 'w', encoding='utf-8').write(
    json.dumps(found, ensure_ascii=False, indent=1))
g = sorted(f['num'] for f in found if f['kind'] == '그림')
t = sorted(f['num'] for f in found if f['kind'] == '표')
print(f"그림 {g}\n표   {t}")
print("그림 누락:", sorted(set(range(1, 34)) - set(g)), "| 표 누락:", sorted(set(range(1, 18)) - set(t)))
