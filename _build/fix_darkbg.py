# -*- coding: utf-8 -*-
"""검정 배경 이미지 수정.

원인: PDF 임베디드 이미지가 SMask(투명 마스크)를 가진 경우, pdfimages 추출은
base(투명영역=검정)와 마스크를 분리하는데 구 파이프라인이 base만 사용 → 검정 배경.

수정: 해당 이미지의 페이지 배치 rect를 PyMuPDF로 찾아 그 영역을 페이지째
clip 렌더(뷰어 표시 그대로 = 흰 배경 + SMask 적용)한 이미지로 교체.
매칭: 파일명 f-{page(1-based,pdfimages)}-{idx} 의 페이지에서 임베디드 이미지
크기(w×h)가 대상 파일과 같은 xref의 get_image_rects.

사용: python fix_darkbg.py <CID> [--dry]   (저장소 루트에서)
"""
import fitz, io, os, re, sys
from PIL import Image

def dark_frac(p):
    im = Image.open(p).convert('L'); w, h = im.size; px = im.load()
    b = []
    for x in range(0, w, max(1, w // 50)): b += [px[x, 0], px[x, h - 1]]
    for y in range(0, h, max(1, h // 50)): b += [px[0, y], px[w - 1, y]]
    return sum(1 for v in b if v < 40) / len(b)

def fix_case(CID, dry=False):
    doc = fitz.open(f'pdf/{CID}.pdf')
    # 임베디드 인벤토리: (0-based page) -> [(xref, w, h, smask)]
    inv = {}
    for pi in range(doc.page_count):
        for img in doc[pi].get_images(full=True):
            inv.setdefault(pi, []).append((img[0], img[2], img[3], img[1]))

    # 대상 수집: fulltext 참조 webp + assets png
    targets = []
    fp = f'fulltext/{CID}/index.html'
    if os.path.isfile(fp):
        h = io.open(fp, encoding='utf-8').read()
        for src in sorted(set(re.findall(r'<img src="(img/[^"]+)"', h))):
            p = f'fulltext/{CID}/{src}'
            if os.path.isfile(p): targets.append(p)
    ad = f'assets/img/{CID}'
    if os.path.isdir(ad):
        targets += [os.path.join(ad, f) for f in sorted(os.listdir(ad))]

    fixed, skipped = [], []
    for p in targets:
        try:
            if dark_frac(p) <= 0.5: continue
        except Exception: continue
        m = re.match(r'f-(\d+)-\d+', os.path.basename(p))
        if not m:
            skipped.append((p, 'name-pattern')); continue
        pg = int(m.group(1)) - 1          # pdfimages 1-based -> 0-based
        im = Image.open(p); tw, th = im.size
        cand = [x for x in inv.get(pg, []) if (x[1], x[2]) == (tw, th)]
        if not cand:
            skipped.append((p, f'no-match p{pg} {tw}x{th}')); continue
        xref = cand[0][0]
        rects = doc[pg].get_image_rects(xref)
        if not rects:
            skipped.append((p, f'no-rect xref{xref}')); continue
        r = rects[0]
        zoom = max(1.0, min(4.0, tw / r.width))   # 기존 해상도에 맞춤
        pix = doc[pg].get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=r, alpha=False)
        out = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        if not dry:
            if p.lower().endswith('.png'):
                out.save(p, 'PNG', optimize=True)
            else:
                out.save(p, 'WEBP', quality=87, method=6)
        fixed.append(os.path.basename(p))
    return fixed, skipped

if __name__ == '__main__':
    CID = sys.argv[1]; dry = '--dry' in sys.argv
    fixed, skipped = fix_case(CID, dry)
    print(f'{CID}: fixed={len(fixed)} skipped={len(skipped)}' + (' (dry)' if dry else ''))
    for s in skipped: print('   SKIP', s[0], '--', s[1])
