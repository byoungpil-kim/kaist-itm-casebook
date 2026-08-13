# -*- coding: utf-8 -*-
"""230107(금연욱) 원문 검토 — 절 제목 복원, 캡션↔이미지 교정, 캡션 잔재 정리.

발견된 결함
 1) 절 제목 19개(2.1~5.2)가 모두 본문 문단 안에 섞여 있어 목차가 장 제목 6개뿐이었다.
    (원문에서 절 제목이 본문과 같은 12pt·비볼드라 추출기가 구분하지 못함)
 2) Fig.1과 Table 1의 이미지가 서로 바뀌어 있었고, Table 5·8은 캡션이 잘린 버전을 쓰고 있었다.
 3) 본문 문장이 캡션으로 잡힌 3건이 정작 올바른 이미지를 물고 있었다.
 4) 그림 뒤에 캡션 텍스트가 본문으로 되풀이돼 있었다.
"""
import sys, io, re, os, glob, fitz, html as H

CID = '230107'
P = f'fulltext/{CID}/index.html'
d = fitz.open(f'pdf/{CID}.pdf')
h = io.open(P, encoding='utf-8').read()
log = []

# ── ① PDF에서 절 제목 목록을 뽑아 본문에서 분리
heads = []
for pi in range(5, d.page_count):
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if re.match(r'^\d+\.\d+(\.\d+)?\s+\S', t) and len(t) < 50 and t not in heads:
                heads.append(t)
heads.sort(key=len, reverse=True)          # 긴 제목부터 (3.1.1이 3.1보다 먼저)
n = 0
for t in heads:
    esc = re.escape(H.escape(t, quote=False))
    # 본문 문단 안의 제목을 <h3>로 떼어낸다
    pat = re.compile(r'<p>(.*?)\s*' + esc + r'\s*(.*?)</p>', re.S)
    def rep(m):
        global n
        before, after = m.group(1).strip(), m.group(2).strip()
        n += 1
        out = (f'<p>{before}</p>\n' if before else '') + f'<h3>{H.escape(t, quote=False)}</h3>\n'
        return out + (f'<p>{after}</p>' if after else '')
    h, k = pat.subn(rep, h, count=1)
log.append(f'절 제목 {n}개를 본문에서 분리해 h3로 복원')

# ── ② 캡션이 본문으로 되풀이된 것 제거
h, k = re.subn(r'(<figure class="ftfig">.*?</figure>\s*)<p>(Table \d+\.[^<]{0,90}|Fig\. \d+\.[^<]{0,90})</p>\s*',
               r'\1', h, flags=re.S)
log.append(f'그림 뒤 본문에 되풀이된 캡션 {k}건 제거')

# ── ③ 본문 문장이 캡션으로 잡힌 3건 — 본문으로 되돌리고, 물고 있던 이미지는 제 캡션으로 넘긴다
MOVE = {}          # 올바른 캡션 → 이미지
for bogus, owner in (('Table 1을 살펴보면', 'Table 1.'),
                     ('Table 5와 6을 살펴보면', 'Table 5.'),
                     ('Table 8의 결과에서', 'Table 8.')):
    m = re.search(r'<p class="ftcap">(' + re.escape(bogus) + r'[^<]*)</p>\s*'
                  r'<figure class="ftfig"><img src="(img/[^"]+)"[^>]*></figure>\s*', h)
    assert m, bogus
    MOVE[owner] = m.group(2)
    h = h[:m.start()] + f'<p>{m.group(1)}</p>\n' + h[m.end():]
    log.append(f'  캡션→본문 복원: {m.group(1)[:40]}… (이미지 {m.group(2)} 는 {owner} 로)')

# ── ④ 캡션별 올바른 이미지 지정 (각 이미지 내용을 직접 확인해 확정)
MOVE['Fig. 1.'] = 'img/f-013-000.webp'
for owner, img in MOVE.items():
    m = re.search(r'(<p class="ftcap">' + re.escape(owner) + r'[^<]*</p>\s*'
                  r'(?:<p class="ftsrc">[^<]*</p>\s*)?)<figure class="ftfig"><img src="(img/[^"]+)"[^>]*></figure>', h)
    assert m, owner
    if m.group(2) != img:
        log.append(f'  {owner:10} {m.group(2)} → {img}')
        h = h[:m.start()] + m.group(1) + f'<figure class="ftfig"><img src="{img}" alt=""></figure>' + h[m.end():]

io.open(P, 'w', encoding='utf-8').write(h)
used = set(re.findall(r'img/[^"]+', h))
files = {'img/' + os.path.basename(f) for f in glob.glob(f'fulltext/{CID}/img/*')}
log.append(f'없는 참조: {sorted(used - files)} | 미사용 삭제: {sorted(files - used)}')
for f in sorted(files - used):
    os.remove(f'fulltext/{CID}/' + f)
io.open(r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad/log230107.txt',
        'w', encoding='utf-8').write('\n'.join(log))
