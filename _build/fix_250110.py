# -*- coding: utf-8 -*-
"""250110(이주영) 원문 수정 — 저자 검수 반영.

저자 지적: "표와 그림 깨진 부분, 제 7장 제목과 appendix가 삭제되어 수정 필요"

확인된 결함
 1) 제 6 장 결론·제 7 장 연구의 한계 및 향후 과제 제목이 14pt라 h2(16pt 기준)에서 누락.
    제7장 본문은 6.2 시사점 끝에 그대로 흡수돼 있었다.
 2) Appendix에 목차 줄("Appendix 1 …56 / Appendix 2 …57")만 남고 실제 표 2개가 없었다.
 3) 캡션 끝에 목차 쪽번호가 붙어 있었다("[표 1. …] 4").
 4) 본문 문장 3개가 캡션으로 잘못 잡혀 있었다.
"""
import sys, io, re, os, fitz, html as H
from PIL import Image

CID = '250110'
P = f'fulltext/{CID}/index.html'
d = fitz.open(f'pdf/{CID}.pdf')
h = io.open(P, encoding='utf-8').read()
log = []


def render(pi, rect, name):
    pix = d[pi].get_pixmap(clip=fitz.Rect(*rect), dpi=200)
    Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(
        f'fulltext/{CID}/img/{name}', 'WEBP', quality=90)
    return f'img/{name}'


def table_region(pi, cap_y):
    """캡션 아래 ~ 각주(6.5pt)/쪽번호 앞까지의 표 영역."""
    xs0, xs1, ys1 = [], [], []
    for b in d[pi].get_text('dict')['blocks']:
        if b.get('type') != 0:
            continue
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            sz = l['spans'][0]['size']
            if not t or l['bbox'][1] <= cap_y + 2 or sz < 8 or l['bbox'][1] > 700:
                continue
            xs0.append(l['bbox'][0]); xs1.append(l['bbox'][2]); ys1.append(l['bbox'][3])
    for x in d[pi].get_drawings():
        r = fitz.Rect(x['rect'])
        if r.width > 40 and r.y0 > cap_y and r.y1 < 700:
            xs0.append(r.x0); xs1.append(r.x1); ys1.append(r.y1)
    return (min(xs0) - 8, cap_y + 4, max(xs1) + 8, max(ys1) + 6)


# ── ① 제 6 장 제목 추가
old = '<h3>6.1 연구 결과</h3>'
assert old in h
h = h.replace(old, '<h2>제 6 장 결론</h2>\n' + old, 1)
log.append("제 6 장 결론 제목 추가")

# ── ② 제 7 장 제목 추가 (본문은 6.2 끝에 흡수돼 있었다)
mark = '<p>본 연구는 R&amp;D 기반 기술 전유성과 신시장형 파괴적 혁신 이론을 바탕으로, ㈜아이센스가 글로벌'
i = h.index(mark)
h = h[:i] + '<h2>제 7 장 연구의 한계 및 향후 과제</h2>\n' + h[i:]
log.append("제 7 장 연구의 한계 및 향후 과제 제목 추가 (본문 6문단은 이미 존재)")

# ── ③ Appendix 본문 복원 (표 2개를 PDF에서 렌더)
a1 = render(49, table_region(49, 160.0), 'appendix1.webp')
a2 = render(50, table_region(50, 130.0), 'appendix2.webp')
old_app = re.search(r'<h2>Appendix</h2>\n<p>Appendix 1\..*?</p>\n', h, re.S).group(0)
new_app = ('<h2>Appendix</h2>\n'
           '<p class="ftcap">Appendix 1. 한국 의료기기산업 8대 중점 분야'
           '<sup class="fnref" id="fnref-56"><a href="#fn-56">56</a></sup></p>\n'
           f'<figure class="ftfig"><img src="{a1}" alt=""></figure>\n'
           '<p class="ftcap">Appendix 2. 체외진단 의료기기의 기술적 분류'
           '<sup class="fnref" id="fnref-57"><a href="#fn-57">57</a></sup></p>\n'
           f'<figure class="ftfig"><img src="{a2}" alt=""></figure>\n')
h = h.replace(old_app, new_app)
log.append(f"Appendix 1·2 표 복원 ({a1}, {a2})")

# ── ④ 캡션 끝의 목차 쪽번호 제거
def strip_pageno(m):
    inner = m.group(1)
    new = re.sub(r'(\]|\))\s*\d{1,3}\s*$', r'\1', inner)
    if new != inner:
        log.append(f"  쪽번호 제거: {H.unescape(re.sub('<[^>]+>','',inner))[:44]}")
    return f'<p class="ftcap">{new}</p>'
h = re.sub(r'<p class="ftcap">(.*?)</p>', strip_pageno, h, flags=re.S)

# ── ⑤ 본문 문장이 캡션으로 잡힌 것 되돌리기
CAPOK = re.compile(r'^\s*[\[<]?\s*(그림|표|Appendix)\s*\d')
def uncap(m):
    inner = m.group(1)
    plain = H.unescape(re.sub('<[^>]+>', '', inner)).strip()
    if CAPOK.match(plain):
        return m.group(0)
    log.append(f"  캡션→본문: {plain[:50]}")
    return f'<p>{inner}</p>'
h = re.sub(r'<p class="ftcap">(.*?)</p>', uncap, h, flags=re.S)

io.open(P, 'w', encoding='utf-8').write(h)
io.open(r'C:/Users/bpkim/AppData/Local/Temp/claude/C--claude-kaist-itm-casebook/2ceb311a-0bdd-4832-9bbf-8fbf2318b7df/scratchpad/log250110.txt',
        'w', encoding='utf-8').write('\n'.join(log))
