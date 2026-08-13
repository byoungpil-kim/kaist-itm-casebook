# -*- coding: utf-8 -*-
"""260105(김진) 원문 캡션↔이미지 재정렬 + 끊긴 문단 복구.

이 원고는 "그림 N." 캡션이 그림 아래, "표 N." 캡션이 표 위에 온다. 구 추출기가 전부
캡션-위로 가정해, 본문 문장이 캡션으로 잡힌 4건이 이미지를 하나씩 흡수하면서
그림 15부터 짝이 한 칸씩 밀렸다. 각 이미지의 내용을 직접 확인해 짝을 확정했다.
"""
import sys, io, re, os, glob

P = 'fulltext/260105/index.html'
h = io.open(P, encoding='utf-8').read()
log = []

# ── ① 본문 문장이 캡션으로 잡힌 4건 — 문단 복구 (딸려 있던 이미지는 아래 ②에서 제자리로)
merges = [
    # (앞 문단 끝, 가짜 캡션, 사이 figure(없으면 ''), 뒤 문단 시작, 이음새 공백)
    ('<p>주: 본 그림은 실측 데이터가 아닌 trade-off 완화 구조를 설명하기 위한 개념도임 비비고 사례는 이러한 trade-off가 단순히 열처리 강도의 조정이 아니라 공정아키텍처의 재구성을 통해 완화될 수 있음을 보여준다. 이를 개념적으로 나타낸 것이</p>\n',
     '<p class="ftcap">그림 14로, 미생물 안전성과 관능적 품질 간의 정량적 균형점이나 최적 교차점을</p>\n',
     '<figure class="ftfig"><img src="img/f-023-025.webp" alt=""></figure>\n',
     '<p>제시하기 위한 실증 그래프라기보다, 누적 열처리 부담이 증가할수록 두 품질속성이 상반된 방향으로 변화하는 관계를 설명하기 위해 도식화한 개념도이다.</p>\n', ' '),
    ('', '<p class="ftcap">그림 19는 냉동블록 처리 여부에 따른 레토르트 후 육류·해산물의 경도 차이를</p>\n',
     '<figure class="ftfig"><img src="img/f-030-035.webp" alt=""></figure>\n',
     '<p>보여준다. 전처리 냉동블록을 적용한 조건은', ' '),
    ('', '<p class="ftcap">표 8은 마이크로파 전처리와 마일드 레토르트 병행 조건의 살균 효과를 보여</p>\n',
     '<figure class="ftfig"><img src="img/f-032-036.webp" alt=""></figure>\n',
     '<p>준다. 닭고기, 쇠고기, 새우 모두에서', ''),
    ('', '<p class="ftcap">표 9는 개선 공정 적용 전후의 관능적 품질 변화를 제시한다. 김치원료의 경우</p>\n',
     '', '<p>개선 공정 적용 후 전반맛, 김치 식감, 외관 항목의', ' '),
]
for prev, cap, fig, nxt, joiner in merges:
    block = prev + cap + fig + nxt
    assert block in h, f'블록 불일치: {cap[:44]}'
    captxt = re.sub(r'</?p[^>]*>', '', cap).strip()
    prevtxt = re.sub(r'</?p>', '', prev).strip()
    if prev:
        newp = '<p>' + prevtxt + ' ' + captxt + joiner + nxt[len('<p>'):]
    else:
        newp = '<p>' + captxt + joiner + nxt[len('<p>'):]
    h = h.replace(block, newp)
    log.append(f'문단 복구: {captxt[:42]}…')

# ── ② 캡션 번호 → 실제 이미지 (각 이미지 내용을 직접 확인해 확정)
FIX = {
    ('그림', 15): 'f-023-025', ('표', 4): 'f-024-026', ('그림', 16): 'f-024-027',
    ('표', 5): 'f-025-028', ('그림', 17): 'f-026-029', ('표', 6): 'f-027-030',
    ('표', 7): 'f-027-031', ('그림', 18): 'f-028-032', ('그림', 19): 'f-028-033',
    ('그림', 20): 'f-030-035', ('표', 8): 'f-030-034', ('그림', 21): 'f-032-036',
    ('표', 9): 'f-032-037', ('그림', 22): 'f-033-039',
}
CAP = re.compile(r'^\s*\[?\s*(그림|표)\s*(\d+)\s*[.．\]]')


def repl(m):
    cap = re.sub('<[^>]+>', '', m.group(1)).strip()
    mm = CAP.match(cap)
    if not mm:
        return m.group(0)
    key = (mm.group(1), int(mm.group(2)))
    if key not in FIX:
        return m.group(0)
    old = re.findall(r'<img src="img/([^"]+)"', m.group(3))
    new = FIX[key] + '.webp'
    if old != [new]:
        log.append(f'  {key[0]}{key[1]:2d}: {old} → [{new}]')
    return m.group(0)[:m.start(3) - m.start(0)] + f'<figure class="ftfig"><img src="img/{new}" alt=""></figure>\n'


h = re.sub(r'(<p class="ftcap">.*?</p>)\s*((?:<p class="ftsrc">.*?</p>\s*)?)((?:<figure class="ftfig">.*?</figure>\s*)+)',
           repl, h, flags=re.S)
io.open(P, 'w', encoding='utf-8').write(h)

used = set(re.findall(r'img/[^"]+', h))
files = {'img/' + os.path.basename(f) for f in glob.glob('fulltext/260105/img/*')}
log.append(f'없는 참조: {sorted(used - files)}')
for f in sorted(files - used):
    os.remove('fulltext/260105/' + f)
log.append(f'미사용 이미지 삭제: {sorted(files - used)}')
io.open(r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad/log260105.txt',
        'w', encoding='utf-8').write('\n'.join(log))
