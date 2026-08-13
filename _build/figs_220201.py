# -*- coding: utf-8 -*-
"""220201(공다영) 그림·표 캡션↔이미지 재정렬.

캡션은 그림·표 **위**에 온다. 문제는 본문에 "[표 2]와 같이 …", "[그림 9]와 같이 …" 처럼
대괄호 상호참조로 시작하는 문장이 5개 있어 캡션으로 잡히고, 그것들이 이미지를 하나씩
가로채면서 뒤쪽 캡션이 줄줄이 밀린 것이다.
진짜 캡션은 "]" 다음이 조사가 아니라 제목으로 이어진다.
"""
import sys, io, re, os, json, fitz
from PIL import Image

CID = '220201'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
DPI = 200
CAP = re.compile(r'^\s*\[\s*(그림|표)\s*(\d+)\s*\]\s*(.*)$')
# 진짜 캡션은 "] " 뒤에 제목이 온다. 상호참조는 "]와 같이"처럼 조사가 바로 붙는다.
BOGUS = re.compile(r'^\s*\[\s*(?:그림|표)\s*\d+\s*\](?=[^\s])')
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
           if b.get('type') == 1 and b['bbox'][3] - b['bbox'][1] > 20]
    if not out:                      # 임베디드 이미지가 없으면 벡터 도형(차트)으로 영역을 잡는다
        W = d[pi].rect.width
        dr = [fitz.Rect(x['rect']) for x in d[pi].get_drawings()
              if fitz.Rect(x['rect']).width > 30 and fitz.Rect(x['rect']).height > 10
              and fitz.Rect(x['rect']).width < W - 20]
        if dr:
            out = [fitz.Rect(min(r.x0 for r in dr), min(r.y0 for r in dr),
                             max(r.x1 for r in dr), max(r.y1 for r in dr))]
    return sorted(out, key=lambda r: r.y0)


def is_caption(t):
    return bool(CAP.match(t)) and not BOGUS.match(t)


found = []
for pi in range(4, d.page_count):
    L = lines(pi)
    R = rects(pi)
    caps = [ln for ln in L if is_caption(ln['t'])]
    for k, ln in enumerate(caps):
        m = CAP.match(ln['t'])
        # 아래 경계: 다음 캡션 또는 본문 재개
        bottom = d[pi].rect.height - 60
        for o in L:
            if o['y'] <= ln['y1'] + 1:
                continue
            if is_caption(o['t']) or (o['sz'] >= 11 and o['x'] < 110 and (o['x1'] - o['x']) > 300):
                bottom = min(bottom, o['y'] - 4)
                break
        sel = [r for r in R if r.y0 >= ln['y1'] - 2 and r.y1 <= bottom + 10]
        page = pi
        if not sel and pi + 1 < d.page_count:      # 그림이 다음 쪽 머리에 있는 경우
            Rn = rects(pi + 1)
            Ln = lines(pi + 1)
            if Rn and not any(is_caption(o['t']) and o['y'] < Rn[0].y0 for o in Ln):
                sel = [Rn[0]]
                page = pi + 1
        if not sel:
            print(f'  !! 이미지 없음 {m.group(1)}{m.group(2)} p{pi+1}')
            continue
        rect = (min(r.x0 for r in sel) - 5, min(r.y0 for r in sel) - 5,
                max(r.x1 for r in sel) + 5, max(r.y1 for r in sel) + 5)
        found.append(dict(kind=m.group(1), num=int(m.group(2)), page=page + 1, cap=ln['t'],
                          rect=[round(v, 1) for v in rect], y=ln['y']))

os.makedirs(IMGDIR, exist_ok=True)
seq = {}
for f in found:
    seq.setdefault((f['kind'], f['num']), 0)
    seq[(f['kind'], f['num'])] += 1
    suffix = '' if seq[(f['kind'], f['num'])] == 1 else chr(96 + seq[(f['kind'], f['num'])])
    name = ('fig%02d' if f['kind'] == '그림' else 'tab%02d') % f['num'] + suffix + '.webp'
    pix = d[f['page'] - 1].get_pixmap(clip=fitz.Rect(*f['rect']), dpi=DPI)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        os.path.join(IMGDIR, name), 'WEBP', quality=90)
    f['img'] = 'img/' + name

io.open(f'{SP}/figs_{CID}.json', 'w', encoding='utf-8').write(
    json.dumps(found, ensure_ascii=False, indent=1))
print(f"캡션 {len(found)}개")
for kind, rng in (('그림', 17), ('표', 12)):
    nums = sorted(f['num'] for f in found if f['kind'] == kind)
    dup = [n for n in set(nums) if nums.count(n) > 1]
    print(f"  {kind} {nums}" + (f"  중복 {dup}" if dup else ''))
