# -*- coding: utf-8 -*-
"""200104 <표 2> IPC 별 DJI 특허 현황(상위 5개) 재제작.

저자(김혜주) 원문 수정 요청: 빈도수 칸에 단위 '개'를 붙여달라(152 → 152개 등).
기존 t2.webp는 원문 PDF를 잘라낸 이미지라 글자를 고칠 수 없어, 같은 표를 다시 그린다.
표 5(t5.webp)를 저자 정정본으로 재제작할 때 쓴 것과 같은 시각 언어를 따른다.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = 'fulltext/200104/img/t2.webp'
FONT = 'C:/Windows/Fonts/malgun.ttf'
FONT_B = 'C:/Windows/Fonts/malgunbd.ttf'
S = 2                                    # 2배로 그린 뒤 축소(안티에일리어싱)

HEAD = ['순위', 'IPC 코드', '내용', '빈도수', '비율']
ROWS = [
    ['1', 'B64C', '비행기; 헬리콥터', '152개', '13.1%'],
    ['2', 'H04N', '화상통신', '148개', '12.7%'],
    ['3', 'G05D', '비전기적 변량의 제어 또는 조정계', '135개', '11.6%'],
    ['4', 'B64D', '항공기의 장비; 비행복; 패러슈트; 동력\n장치 또는 추진전달 기구의 설비 또는 장치', '86개', '7.4%'],
    ['',  'G03B', '사진을 촬영하기 위하여 또는 사진을\n투영하여 직시하기 위한 장치 또는 배치', '86개', '7.4%'],
    ['5', 'F16M', '엔진, 기계 장치에서의 프레임, 스탠드\n또는 지지대', '47개', '4%'],
]
COLW = [70, 110, 430, 105, 95]           # 합 810
PAD_X, PAD_Y = 12, 10
LINE_H = 30
HEAD_BG = (233, 236, 240)
BORDER = (60, 66, 74)
INK = (24, 28, 34)


def main():
    fb = ImageFont.truetype(FONT_B, 15 * S)
    fr = ImageFont.truetype(FONT, 15 * S)
    heights = [LINE_H + PAD_Y]
    for r in ROWS:
        n = max(c.count('\n') + 1 for c in r)
        heights.append(n * LINE_H + PAD_Y)
    W = sum(COLW) + 2
    H = sum(heights) + 2
    im = Image.new('RGB', (W * S, H * S), 'white')
    d = ImageDraw.Draw(im)

    def cell(x, y, w, h, text, font, bg=None, align='center'):
        if bg:
            d.rectangle([x * S, y * S, (x + w) * S, (y + h) * S], fill=bg)
        d.rectangle([x * S, y * S, (x + w) * S, (y + h) * S], outline=BORDER, width=1 * S)
        lines = text.split('\n')
        ty = y + (h - len(lines) * LINE_H) / 2
        for ln in lines:
            tw = d.textlength(ln, font=font) / S
            tx = x + (w - tw) / 2 if align == 'center' else x + PAD_X
            d.text((tx * S, ty * S + 4), ln, font=font, fill=INK)
            ty += LINE_H

    y = 1
    x = 1
    for i, htxt in enumerate(HEAD):
        cell(x, y, COLW[i], heights[0], htxt, fb, HEAD_BG)
        x += COLW[i]
    y += heights[0]
    for ri, r in enumerate(ROWS):
        x = 1
        for ci, c in enumerate(r):
            cell(x, y, COLW[ci], heights[ri + 1], c, fr,
                 align='left' if ci == 2 else 'center')
            x += COLW[ci]
        y += heights[ri + 1]

    im = im.resize((W, H), Image.LANCZOS)
    im.save(OUT, 'WEBP', quality=95)
    print(f'{OUT} 생성 ({W}x{H})')


if __name__ == '__main__':
    main()
