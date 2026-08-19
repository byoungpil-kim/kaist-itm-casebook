# -*- coding: utf-8 -*-
"""조항정 교수 수정의 유형 분석 — OLD/NEW 문단쌍에서 치환 패턴을 뽑는다."""
import sys, io, os, glob, re, difflib, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad')
from apply_trk import changed_paras
DOCDIR = r'C:/claude/itm-cases/사례_수정_조항정'

pairs = []
for path in sorted(glob.glob(DOCDIR + '/*.docx')):
    cid = os.path.basename(path).split('_')[0]
    for old, new in changed_paras(path):
        sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal': continue
            a, b = old[i1:i2], new[j1:j2]
            # 앞뒤 문맥 조금
            la, ra = old[max(0,i1-12):i1], old[i2:i2+12]
            pairs.append((cid, tag, a, b, la, ra))
print(f'치환 단위 {len(pairs)}건\n')

# 자주 나오는 삭제/삽입 어휘
delc = collections.Counter(a.strip() for _,t,a,b,_,_ in pairs if a.strip())
insc = collections.Counter(b.strip() for _,t,a,b,_,_ in pairs if b.strip())
print('== 자주 지운 표현 ==')
for k,v in delc.most_common(30): print(f'  {v:>3}  {k!r}')
print('\n== 자주 넣은 표현 ==')
for k,v in insc.most_common(30): print(f'  {v:>3}  {k!r}')
io.open(r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad/pairs.txt','w',encoding='utf-8').write(
    '\n'.join(f'{c}\t{t}\t{a!r}\t->\t{b!r}\t|{la}…{ra}|' for c,t,a,b,la,ra in pairs))
