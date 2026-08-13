# -*- coding: utf-8 -*-
"""250215(이진용) 본문에 섞여 들어간 쪽번호 제거 + 쪽 경계에서 끊긴 문단 병합.

이 원고의 쪽번호는 하단 '가운데'(x≈300)에 있어 우측 정렬을 전제한 필터에 걸리지 않았고,
그대로 본문에 흡수됐다(예: "…기여하는 핵심 12 메커니즘을", "정부 기술의 44 상용화에").
쪽 경계의 앞뒤 문구를 PDF에서 뽑아 그 사이에 낀 번호만 정확히 지운다.
"""
import sys, io, re, fitz, html as H

CID = '250215'
P = f'fulltext/{CID}/index.html'
d = fitz.open(f'pdf/{CID}.pdf')
h = io.open(P, encoding='utf-8').read()
log = []


def page_lines(pi):
    """쪽번호를 뺀 본문 줄(위→아래)."""
    PH = d[pi].rect.height
    out = []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if not t:
                continue
            if re.fullmatch(r'\d{1,3}', t) and l['bbox'][1] > PH - 90:
                continue
            out.append((l['bbox'][1], t))
    return [t for _, t in sorted(out)]


def norm(s):
    return re.sub(r'\s+', '', s)


plain_map = []           # (정규화 위치, 원문 위치)
buf = []
for m in re.finditer(r'>([^<]+)<', h):
    for k, ch in enumerate(m.group(1)):
        if not ch.isspace():
            buf.append((ch, m.start(1) + k))
plainH = ''.join(c for c, _ in buf)
pos = [p for _, p in buf]

removed = 0
for pi in range(1, d.page_count):
    # 쪽번호 블록이 그 쪽 본문보다 먼저 읽혀, [앞 쪽 마지막 줄][이 쪽 번호][이 쪽 첫 줄] 순으로 섞인다
    pn = str(pi)                                   # 인쇄된 쪽번호 = 0-based 인덱스
    cur, nxt = page_lines(pi - 1), page_lines(pi)
    if not cur or not nxt:
        continue
    tail = norm(H.unescape(cur[-1]))[-14:]
    head = norm(H.unescape(nxt[0]))[:14]
    if len(tail) < 8 or len(head) < 8:
        continue
    key = tail + pn + head
    i = plainH.find(key)
    if i < 0:
        continue
    # 원문에서 쪽번호 문자들의 위치를 찾아 지운다
    s = pos[i + len(tail)]
    e = pos[i + len(tail) + len(pn) - 1] + 1
    assert h[s:e] == pn, (h[s - 20:e + 20], pn)
    h = h[:s] + h[e:]
    removed += 1
    log.append(f'  p{pi} → p{pi+1} 사이 쪽번호 {pn} 제거: …{H.unescape(cur[-1])[-24:]} | {H.unescape(nxt[0])[:24]}…')
    # 위치 인덱스 갱신
    buf = []
    for m in re.finditer(r'>([^<]+)<', h):
        for k, ch in enumerate(m.group(1)):
            if not ch.isspace():
                buf.append((ch, m.start(1) + k))
    plainH = ''.join(c for c, _ in buf)
    pos = [p for _, p in buf]

log.insert(0, f'본문에 섞인 쪽번호 {removed}개 제거')

# ── 쪽 경계에서 끊긴 문단 병합 (앞 문단이 문장으로 끝나지 않은 경우)
merged = 0
def merge(m):
    global merged
    a, b = m.group(1), m.group(2)
    if re.search(r'(다|요|음|함|임)[.\"\'”’)\]]?\s*$', a) or a.rstrip().endswith(('.', '?', '!', ':')):
        return m.group(0)
    merged += 1
    return f'<p>{a} {b}</p>'
h = re.sub(r'<p>([^<]{25,}?)</p>\s*<p>([^<]{10,}?)</p>', merge, h)
log.append(f'쪽 경계에서 끊긴 문단 {merged}건 병합')

io.open(P, 'w', encoding='utf-8').write(h)
io.open(r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad/log250215.txt',
        'w', encoding='utf-8').write('\n'.join(log))
