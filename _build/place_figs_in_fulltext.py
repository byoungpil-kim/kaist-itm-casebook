# -*- coding: utf-8 -*-
"""210203: 렌더된 그림(fig/cht/tbl*.webp)을 캡션·출처와 함께 본문 흐름에 재배치."""
import sys, io, re, os, json, fitz, html as H

CID = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '210203'
SP = os.environ.get('FIGTMP', '_build/_figtmp')
CAP = re.compile(r'^\[(그림|차트|표)\s*(\d+)\]\s*(.+)$')
DRY = '--dry' in sys.argv
despace = lambda s: re.sub(r'\s+', '', s)

man = json.load(io.open(f'{SP}/figman203.json', encoding='utf-8'))
key2fig = {(m['kind'], m['num']): m for m in man}

# --- PDF 읽기순서에서 각 캡션 직전 본문 텍스트(앵커) 추출 ---
d = fitz.open(f'pdf/{CID}.pdf')
anchors = {}
tail = ''
for pi in range(d.page_count):
    lines = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t:
                lines.append((l['bbox'][1], l['bbox'][0], l['spans'][0]['size'], t))
    for _y, _x, sz, t in sorted(lines):
        m = CAP.match(t)
        if m and sz <= 11.5:
            k = (m.group(1), int(m.group(2)))
            anchors.setdefault(k, despace(tail)[-45:])
        elif sz >= 11.5:
            tail = (tail + ' ' + t)[-600:]

# --- HTML 재구성 ---
path = f'fulltext/{CID}/index.html'
html = io.open(path, encoding='utf-8').read()
mm = re.search(r'(<main[^>]*>)(.*?)(</main>)', html, re.S)
body = mm.group(2)
body = re.sub(r'\n?<p class="ftcap">.*?</p>', '', body, flags=re.S)
body = re.sub(r'\n?<p class="ftsrc">.*?</p>', '', body, flags=re.S)
body = re.sub(r'\n?<figure class="ftfig">.*?</figure>', '', body, flags=re.S)
blocks = [b for b in body.split('\n') if b.strip()]
dplain = [despace(re.sub(r'<[^>]+>', '', b)) for b in blocks]

order = sorted(man, key=lambda m: (m['page'], m['y']))
ins, last, miss = {}, -1, []
for m in order:
    k = (m['kind'], m['num'])
    a = anchors.get(k, '')
    tgt = None
    for probe in (a[-40:], a[-30:], a[-22:], a[-15:], a[-11:]):
        if len(probe) < 8:
            break
        for i in range(max(last, 0), len(blocks)):
            if (blocks[i].startswith('<p>') or blocks[i].startswith('<h')) and probe in dplain[i]:
                tgt = i; break
        if tgt is not None:
            break
    if tgt is None:
        # 보조: 본문의 참조 표현([그림 5]에서 보듯 …) 뒤에 배치
        ref = despace(f"[{m['kind']}{m['num']}]")
        for i in range(max(last, 0), len(blocks)):
            if blocks[i].startswith('<p>') and ref in dplain[i]:
                tgt = i; break
    if tgt is None:
        miss.append(m['name']); tgt = last if last >= 0 else 0
    last = tgt
    cap = f'<p class="ftcap">{H.escape(m["cap"], quote=False)}</p>'
    src = f'<p class="ftsrc">{H.escape(m["src"], quote=False)}</p>' if m.get('src') else ''
    fig = f'<figure class="ftfig"><img src="img/{m["name"]}" alt=""></figure>'
    ins.setdefault(tgt, []).append('\n'.join(x for x in (cap, src, fig) if x))

out = []
for i, b in enumerate(blocks):
    out.append(b)
    out.extend(ins.get(i, []))
newbody = '\n' + '\n'.join(out) + '\n'

print(f"그림 {len(order)}개 배치 | 앵커 미매칭 {len(miss)}: {miss}")
if DRY:
    sys.exit()
io.open(path, 'w', encoding='utf-8').write(html[:mm.start(2)] + newbody + html[mm.end(2):])
print("HTML 갱신 완료")
