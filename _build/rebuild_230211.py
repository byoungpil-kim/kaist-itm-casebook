# -*- coding: utf-8 -*-
"""230211(이윤주) 원문 전면 재구성.

기존 산출물은 그림·표 52개가 모두 문서 맨 앞에 몰려 있고 본문이 그 뒤에 따라오는 구조였다
(본문 중 "(그림 6 참조)" 같은 상호참조 3건도 캡션으로 잘못 잡혀 있었다).
PDF 읽기 순서를 그대로 따라가며 캡션을 만나는 지점에 그림을 배치한다.

이 원고의 구조
 - 본문 10pt, 문단 첫 줄 들여쓰기(x 77.2 → 101.2)
 - 캡션은 그림/표 '아래'에 오고 본문과 같은 10pt, "그림 N." / "표 N." 로 시작
 - 제목: 16pt 비볼드 = 제N 장(h2), 16pt 볼드 = N.N(h3), 14pt 볼드 = N.N.N(h4)
 - 그림 영역은 figs_230211.py가 캡션 좌표로 렌더해 둔 것을 그대로 쓴다
"""
import sys, io, re, os, json, fitz, html as H

CID = '230211'
SP = r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad'
BODY_START = 4                     # p5부터 본문
CAP = re.compile(r'^(그림|표)\s*(\d+)\s*[.．]\s*\S')
PAGENO = re.compile(r'^\d{1,3}$')
REFS = re.compile(r'^\s*(참고문헌|References?)\s*$')

d = fitz.open(f'pdf/{CID}.pdf')
FIG = {(f['kind'], f['num']): f for f in json.load(io.open(f'{SP}/figs_{CID}.json', encoding='utf-8'))}
# 캡션이 있는 쪽 → 그 그림이 실제로 그려진 영역(본문에서 제외해야 할 구간)
REGION = {}
for f in FIG.values():
    REGION.setdefault(f['page'] - 1, []).append(tuple(f['rect']))


def vlines(pi):
    """조각난 텍스트를 y 기준 한 줄로 병합."""
    PH = d[pi].rect.height
    frags = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            raw = ''.join(s['text'] for s in l['spans'])
            if not raw.strip():
                continue
            if PAGENO.fullmatch(raw.strip()) and l['bbox'][1] > PH - 100:
                continue
            sp = l['spans'][0]
            frags.append(dict(y=l['bbox'][1], y1=l['bbox'][3], x=l['bbox'][0], x1=l['bbox'][2],
                              raw=raw, sz=sp['size'],
                              bold=bool(sp['flags'] & 16) or 'Bold' in sp['font']))
    frags.sort(key=lambda f: (f['y'], f['x']))
    out = []
    for f in frags:
        if out and abs(f['y'] - out[-1]['y']) <= 3:
            p = out[-1]
            p['raw'] = p['raw'].rstrip() + ' ' + f['raw'].strip()
            p['x1'] = max(p['x1'], f['x1']); p['y1'] = max(p['y1'], f['y1'])
        else:
            out.append(dict(f))
    return out


blocks, para = [], []


def flush():
    global para
    if para:
        t = re.sub(r'\s{2,}', ' ', ''.join(para).strip())
        if len(t) > 1:
            blocks.append(('p', t))
        para = []


done = False
for pi in range(BODY_START, d.page_count):
    if done:
        break
    regs = REGION.get(pi, [])
    in_fig = lambda ln: any(r[1] - 2 <= (ln['y'] + ln['y1']) / 2 <= r[3] + 2 and
                            r[0] - 4 <= ln['x'] and ln['x1'] <= r[2] + 4 for r in regs)
    for ln in vlines(pi):
        t = ln['raw'].strip()
        if REFS.match(t):
            done = True; break
        m = CAP.match(t)
        if m:                                   # 캡션 → 그림 배치 지점
            key = (m.group(1), int(m.group(2)))
            if key in FIG:
                flush(); blocks.append(('fig', key))
            continue
        if in_fig(ln):                          # 그림/표 안의 글자는 이미지로 보여준다
            flush(); continue
        if ln['sz'] >= 15.5:
            flush(); blocks.append(('h3' if ln['bold'] else 'h2', t)); continue
        if ln['sz'] >= 13.5 and ln['bold']:
            flush(); blocks.append(('h4', t)); continue
        if 9.5 <= ln['sz'] < 12:
            if para and ln['x'] >= 95:          # 첫 줄 들여쓰기 = 새 문단
                flush()
            para.append(ln['raw'])
flush()

out = []
for kind, val in blocks:
    if kind in ('h2', 'h3', 'h4'):
        out.append(f'<{kind}>{H.escape(val, quote=False)}</{kind}>')
    elif kind == 'p':
        out.append(f'<p>{H.escape(val, quote=False)}</p>')
    else:
        f = FIG[val]
        out.append(f'<p class="ftcap">{H.escape(f["cap"], quote=False)}</p>')
        out.append(f'<figure class="ftfig"><img src="{f["img"]}" alt=""></figure>')
io.open(f'{SP}/body_{CID}.html', 'w', encoding='utf-8').write('\n'.join(out))

ps = [b for b in blocks if b[0] == 'p']
print(f"문단 {len(ps)}개(평균 {sum(len(b[1]) for b in ps)//max(1,len(ps))}자, 최대 {max(len(b[1]) for b in ps)}자)")
print(f"h2 {sum(1 for b in blocks if b[0]=='h2')} · h3 {sum(1 for b in blocks if b[0]=='h3')} · "
      f"h4 {sum(1 for b in blocks if b[0]=='h4')} | 그림·표 {sum(1 for b in blocks if b[0]=='fig')}개")
miss = [k for k in FIG if k not in [b[1] for b in blocks if b[0] == 'fig']]
print("배치 못한 그림:", miss or "없음")
