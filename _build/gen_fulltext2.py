# -*- coding: utf-8 -*-
"""Generate flowing-body fulltext HTML from pdftotext -layout extracts.
Body only (from 서론 to end), no TOC, figures inserted near captions.
"""
import os, re, sys, json, glob, html
from collections import Counter
from PIL import Image

# repo layout: this script lives in _build/, site root is the parent directory.
# NOTE: regeneration needs the original figure-image pool (imgpool/) and extract texts,
# which are NOT in this repo (see CLAUDE.md > 원문 전문(fulltext) 재생성).
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
W = ROOT
meta = {m['id']: m for m in json.load(open(f'{W}/assets/meta.json'))}

HEAD_H2 = [
    re.compile(r'^제\s*\d+\s*장\b'),
    re.compile(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*[\.、]?\s+\S'),
    re.compile(r'^(?:[IVX]{1,4})\.\s+\S'),
    re.compile(r'^\d+\.\s+\S.{0,40}$'),
    re.compile(r'^\d+\s*장\b'),
]
HEAD_H3 = [
    re.compile(r'^\d+\.\d+(\.\d+)*\.?\s+\S'),
    re.compile(r'^\d+-\d+\.?\s+\S'),
]
CAP = re.compile(r'^[<\[(]?\s*(그림|표|차트|Figure|Table|Fig)\s*\.?\s*\d+', re.I)
SRC = re.compile(r'^\*?\s*[\[(]?\s*(출처|자료|source)\s*[:：\]]', re.I)
BULLET = re.compile(r'^[ㆍ•·▪‣○●◦-]\s+')
PAGENUM = re.compile(r'^[\s\-–—]*\d+[\s\-–—]*$')
DROP_PAT = [
    re.compile(r'사례연구\s*모음집'),
    re.compile(r'CASE\s*STUDY', re.I),
    re.compile(r'^C\s*$|^A\s*$|^S\s*$|^E\s*$|^T\s*$|^U\s*$|^D\s*$|^Y\s*$'),  # vertical sidebar letters
    re.compile(r'I\s*&\s*T\s*M\s+KAIST', re.I),
]
REF_HEAD = re.compile(r'^(Reference|References|참고\s*문헌|참고자료)\b', re.I)

def hangul(ch):
    return '가' <= ch <= '힣'

def find_body_start(pages):
    # find page index & line index of first 서론/제1장-like heading, after any TOC page
    toc_seen = -1
    for i, p in enumerate(pages[:12]):
        if re.search(r'차\s*례|목\s*차|contents', p, re.I):
            toc_seen = i
    for i, p in enumerate(pages):
        if i < toc_seen:  # don't start before TOC
            continue
        lines = p.split('\n')
        for j, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            # TOC lines have dot leaders — skip pages full of them
            if s.count('·') > 10 or '····' in s:
                continue
            if re.match(r'^(제\s*1\s*장|Ⅰ\s*[\.、]?|I\.|1\.|1\s*장)\s*.{0,6}서\s*론', s) or \
               re.match(r'^(제\s*1\s*장|Ⅰ[\.、]?|1\.)\s+\S', s) and ('서론' in s or '연구 배경' in s or '들어가' in s):
                return i, j
    # fallback: first page after toc_seen+1
    return (toc_seen + 1 if toc_seen >= 0 else 2), 0

def classify(s):
    if CAP.match(s): return 'cap'
    if SRC.match(s): return 'src'
    if REF_HEAD.match(s): return 'h2'
    for r in HEAD_H3:
        if r.match(s) and len(s) < 70: return 'h3'
    for r in HEAD_H2:
        if r.match(s) and len(s) < 60: return 'h2'
    if BULLET.match(s): return 'li'
    return 'p'

def gen(cid):
    txt_path = f'{ROOT}/_build/extract/{cid}.txt'
    raw = open(txt_path).read()
    pages = raw.split('\f')
    si, sj = find_body_start(pages)

    # frequency of short lines for header/footer removal
    freq = Counter()
    for p in pages:
        for ln in p.split('\n'):
            s = ' '.join(ln.split())
            if s and len(s) < 70:
                freq[s] += 1
    n_pages = len(pages)
    common = {s for s, c in freq.items() if c >= max(4, n_pages // 4)}

    # images by page
    imgs_by_page = {}
    for f in sorted(glob.glob(f'{ROOT}/_build/imgpool/{cid}/f-*.png')):
        m = re.match(r'f-(\d+)-\d+', os.path.basename(f))
        if m:
            imgs_by_page.setdefault(int(m.group(1)), []).append(f)

    out_dir = f'{W}/fulltext/{cid}'
    img_dir = f'{out_dir}/img'
    os.makedirs(img_dir, exist_ok=True)

    def img_block(path):
        base = os.path.basename(path)[:-4]
        dst = f'{img_dir}/{base}.webp'
        if not os.path.exists(dst):
            try:
                im = Image.open(path)
                if im.mode in ('RGBA', 'LA', 'P'):
                    im = im.convert('RGBA')
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                else:
                    im = im.convert('RGB')
                if im.width > 1500:
                    im = im.resize((1500, int(im.height * 1500 / im.width)), Image.LANCZOS)
                im.save(dst, 'WEBP', quality=82)
            except Exception:
                return None
        return f'<figure class="ftfig"><img src="img/{base}.webp" alt=""></figure>'

    parts = []          # html blocks
    para = []           # current paragraph fragments
    typical = []
    for p in pages:
        for ln in p.split('\n'):
            L = len(ln.rstrip())
            if L > 20: typical.append(L)
    maxw = sorted(typical)[int(len(typical)*0.9)] if typical else 80
    short_cut = maxw * 0.72

    def flush():
        nonlocal para
        if para:
            text = para[0]
            for frag in para[1:]:
                if text and frag and hangul(text[-1]) and hangul(frag[0]):
                    text += frag
                else:
                    text += ' ' + frag
            text = ' '.join(text.split())
            if text:
                parts.append('<p>' + html.escape(text) + '</p>')
            para = []

    in_list = False
    def close_list():
        nonlocal in_list
        if in_list:
            parts.append('</ul>')
            in_list = False

    open_caps = []  # indices in `parts` of captions not yet paired with an image (carried across pages)

    for i in range(si, len(pages)):
        lines = pages[i].split('\n')
        start_j = sj if i == si else 0
        page_imgs = list(imgs_by_page.get(i + 1, []))
        for j in range(start_j, len(lines)):
            ln = lines[j]
            s = ' '.join(ln.split())
            if not s:
                continue
            if PAGENUM.match(s) or s in common:
                continue
            if any(r.search(s) for r in DROP_PAT) and len(s) < 80:
                continue
            kind = classify(s)
            raw_line = ln.rstrip('\n')
            if kind == 'p':
                if in_list and BULLET.match(s) is None and para == []:
                    close_list()
                # paragraph-boundary heuristics
                prev_short = bool(para) and len(para[-1]) < short_cut and para[-1].rstrip()[-1:] in '.다」."\')%]'
                indented = bool(re.match(r'^\s{1,6}\S', raw_line)) and not re.match(r'^\s{7,}', raw_line)
                if para and (prev_short or (indented and len(para[-1]) < short_cut)):
                    flush()
                para.append(s)
            else:
                flush(); close_list()
                if kind == 'h2':
                    parts.append('<h2>' + html.escape(s) + '</h2>')
                elif kind == 'h3':
                    parts.append('<h3>' + html.escape(s) + '</h3>')
                elif kind == 'cap':
                    parts.append('<p class="ftcap">' + html.escape(s) + '</p>')
                    open_caps.append(len(parts) - 1)
                elif kind == 'src':
                    parts.append('<p class="ftsrc">' + html.escape(s) + '</p>')
                    # keep source line attached to its caption: if last open cap is just before, move anchor after src
                    if open_caps and open_caps[-1] == len(parts) - 2:
                        open_caps[-1] = len(parts) - 1
                elif kind == 'li':
                    if not in_list:
                        parts.append('<ul class="ftul">'); in_list = True
                    parts.append('<li>' + html.escape(BULLET.sub('', s)) + '</li>')
        # end of page: pair this page's images with oldest unpaired captions (this or earlier page)
        if page_imgs:
            flush(); close_list()
            for f in page_imgs:
                blk = img_block(f)
                if blk is None:
                    continue
                if open_caps:
                    idx = open_caps.pop(0)
                    parts.insert(idx + 1, blk)
                    open_caps = [(c + 1 if c > idx else c) for c in open_caps]
                else:
                    parts.append(blk)
        # captions only stay open for one extra page
        open_caps = [c for c in open_caps if c >= 0][-4:]
    flush(); close_list()

    m = meta[cid]
    body = '\n'.join(parts)
    page = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[원문] {html.escape(m['title'])} | KAIST ITM 사례연구</title>
<link rel="stylesheet" href="../../assets/style.css">
<style>
.ft-body {{ max-width: 820px; margin: 0 auto; padding: 48px 24px 80px; }}
.ft-body p {{ font-size: 16.5px; color: #2A2E35; margin-bottom: 18px; line-height: 1.8; }}
.ft-body h2 {{ font-size: 23px; font-weight: 800; margin: 46px 0 18px; padding-left: 14px; border-left: 4px solid var(--blue); }}
.ft-body h3 {{ font-size: 18px; font-weight: 700; margin: 30px 0 12px; color: var(--blue-deep); }}
.ftcap {{ text-align: center; font-size: 14px !important; color: var(--gray-5) !important; font-weight: 700; margin: 26px 0 6px !important; }}
.ftsrc {{ text-align: center; font-size: 12.5px !important; color: var(--gray-4) !important; margin: 4px 0 22px !important; }}
.ftfig {{ margin: 10px 0 26px; }}
.ftfig img {{ border: 1px solid var(--gray-2); border-radius: 8px; margin: 0 auto; max-width: 100%; }}
.ftul {{ margin: 0 0 18px 22px; }}
.ftul li {{ font-size: 16px; color: #2A2E35; margin-bottom: 6px; }}
.ft-note {{ max-width: 820px; margin: 0 auto; padding: 0 24px; }}
</style>
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="logo" href="../../index.html">
      <span class="l1">ITM KAIST</span>
      <span class="l2">KAIST COLLEGE OF BUSINESS</span>
    </a>
    <nav class="gnb">
      <a href="../../index.html" class="on">사례연구 라이브러리</a>
      <a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener" class="ext">ITM 홈페이지 ↗</a>
    </nav>
  </div>
</header>
<section class="art-hero">
  <div class="wrap" style="padding:52px 24px 44px;">
    <div class="crumb"><a href="../../index.html">사례연구 라이브러리</a> &nbsp;›&nbsp; <a href="../../cases/{cid}.html">기사 보기</a> &nbsp;›&nbsp; 원문 전체</div>
    <div class="chips"><span class="chip">원문 전체</span></div>
    <h1 style="font-size:27px;">{html.escape(m['title'])}</h1>
    <div class="byline">
      <span><span class="lbl">연구자</span><b>{html.escape(m['author'])}</b></span>
      <span><span class="lbl">지도교수</span><b>{html.escape(m['advisor']) if m['advisor'] else '-'}</b></span>
      <span><span class="lbl">발표</span><b>{m['pub']}</b></span>
    </div>
  </div>
</section>
<div class="ft-note"><div class="notice">본 페이지는 원문 보고서 본문을 웹 열람용으로 변환한 것입니다. 표·수식 등 일부 요소는 원문과 차이가 있을 수 있습니다.</div></div>
<main class="ft-body">
{body}
</main>
<div class="dlbar"><div class="dlcard">
  <div><div class="t">기사로 돌아가기</div><div class="s">{html.escape(m['title'])}</div></div>
  <a class="btn" href="../../cases/{cid}.html">← 기사 보기</a>
</div></div>
<footer class="site-footer">
  <div class="wrap">
    <div>
      <div class="f-logo">ITM KAIST <span class="f-sub">TECHNOLOGY &amp; INNOVATION MANAGEMENT</span></div>
      <p>KAIST 기술경영전문대학원 · Graduate School of Innovation &amp; Technology Management</p>
    </div>
    <div class="f-right"><p>ⓒ Copyright by the original author. All rights reserved.<br>본 사례연구의 저작권은 원저자에게 귀속됩니다.<br>사전 허락 없는 무단 전재·복제·배포를 금합니다.</p></div>
  </div>
</footer>
</body>
</html>'''
    open(f'{out_dir}/index.html', 'w').write(page)
    return len(parts)

def wrap_page(cid, body):
    m = meta[cid]
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[원문] {html.escape(m['title'])} | KAIST ITM 사례연구</title>
<link rel="stylesheet" href="../../assets/style.css">
<style>
.ft-body {{ max-width: 820px; margin: 0 auto; padding: 48px 24px 80px; }}
.ft-body p {{ font-size: 16.5px; color: #2A2E35; margin-bottom: 18px; line-height: 1.8; }}
.ft-body h2 {{ font-size: 23px; font-weight: 800; margin: 46px 0 18px; padding-left: 14px; border-left: 4px solid var(--blue); }}
.ft-body h3 {{ font-size: 18px; font-weight: 700; margin: 30px 0 12px; color: var(--blue-deep); }}
.ftcap {{ text-align: center; font-size: 14px !important; color: var(--gray-5) !important; font-weight: 700; margin: 26px 0 6px !important; }}
.ftsrc {{ text-align: center; font-size: 12.5px !important; color: var(--gray-4) !important; margin: 4px 0 22px !important; }}
.ftfig {{ margin: 10px 0 26px; }}
.ftfig img {{ border: 1px solid var(--gray-2); border-radius: 8px; margin: 0 auto; max-width: 100%; }}
.ftul {{ margin: 0 0 18px 22px; }}
.ftul li {{ font-size: 16px; color: #2A2E35; margin-bottom: 6px; }}
.footnote {{ font-size: 13px !important; color: var(--gray-4) !important; }}
.ft-note {{ max-width: 820px; margin: 0 auto; padding: 0 24px; }}
</style>
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="logo" href="../../index.html">
      <span class="l1">ITM KAIST</span>
      <span class="l2">KAIST COLLEGE OF BUSINESS</span>
    </a>
    <nav class="gnb">
      <a href="../../index.html" class="on">사례연구 라이브러리</a>
      <a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener" class="ext">ITM 홈페이지 ↗</a>
    </nav>
  </div>
</header>
<section class="art-hero">
  <div class="wrap" style="padding:52px 24px 44px;">
    <div class="crumb"><a href="../../index.html">사례연구 라이브러리</a> &nbsp;›&nbsp; <a href="../../cases/{cid}.html">기사 보기</a> &nbsp;›&nbsp; 원문 전체</div>
    <div class="chips"><span class="chip">원문 전체</span></div>
    <h1 style="font-size:27px;">{html.escape(m['title'])}</h1>
    <div class="byline">
      <span><span class="lbl">연구자</span><b>{html.escape(m['author'])}</b></span>
      <span><span class="lbl">지도교수</span><b>{html.escape(m['advisor']) if m['advisor'] else '-'}</b></span>
      <span><span class="lbl">발표</span><b>{m['pub']}</b></span>
    </div>
  </div>
</section>
<div class="ft-note"><div class="notice">본 페이지는 원문 보고서 본문을 웹 열람용으로 변환한 것입니다. 표·수식 등 일부 요소는 원문과 차이가 있을 수 있습니다.</div></div>
<main class="ft-body">
{body}
</main>
<div class="dlbar"><div class="dlcard">
  <div><div class="t">기사로 돌아가기</div><div class="s">{html.escape(m['title'])}</div></div>
  <a class="btn" href="../../cases/{cid}.html">← 기사 보기</a>
</div></div>
<footer class="site-footer">
  <div class="wrap">
    <div>
      <div class="f-logo">ITM KAIST <span class="f-sub">TECHNOLOGY &amp; INNOVATION MANAGEMENT</span></div>
      <p>KAIST 기술경영전문대학원 · Graduate School of Innovation &amp; Technology Management</p>
    </div>
    <div class="f-right"><p>ⓒ Copyright by the original author. All rights reserved.<br>본 사례연구의 저작권은 원저자에게 귀속됩니다.<br>사전 허락 없는 무단 전재·복제·배포를 금합니다.</p></div>
  </div>
</footer>
</body>
</html>'''

def gen_scanned(cid):
    """Wrap the vision-transcribed fragment, inserting images sequentially after captions."""
    frag = open(f'{ROOT}/_build/{cid}_full.html').read()
    out_dir = f'{W}/fulltext/{cid}'
    img_dir = f'{out_dir}/img'
    os.makedirs(img_dir, exist_ok=True)
    imgs = sorted(glob.glob(f'{ROOT}/_build/imgpool/{cid}/f-*.png'))
    blocks = []
    for f in imgs:
        base = os.path.basename(f)[:-4]
        dst = f'{img_dir}/{base}.webp'
        try:
            im = Image.open(f)
            if im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA')
                bg = Image.new('RGB', im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert('RGB')
            if im.width > 1500:
                im = im.resize((1500, int(im.height * 1500 / im.width)), Image.LANCZOS)
            im.save(dst, 'WEBP', quality=82)
            blocks.append(f'<figure class="ftfig"><img src="img/{base}.webp" alt=""></figure>')
        except Exception:
            pass
    # insert images after each ftcap (or its following ftsrc), sequentially, only for [그림...] captions
    out_parts = []
    qi = 0
    lines = re.split(r'(?<=</p>)\s*', frag)
    k = 0
    while k < len(lines):
        seg = lines[k]
        out_parts.append(seg)
        if 'class="ftcap"' in seg and '그림' in seg and qi < len(blocks):
            # if next seg is source, keep it before image
            if k + 1 < len(lines) and 'class="ftsrc"' in lines[k+1]:
                out_parts.append(lines[k+1]); k += 1
            out_parts.append(blocks[qi]); qi += 1
        k += 1
    open(f'{out_dir}/index.html', 'w').write(wrap_page(cid, '\n'.join(out_parts)))
    return len(blocks)

if __name__ == '__main__':
    ids = sys.argv[1:] or [m for m in meta]
    for cid in ids:
        if cid == '210107':
            n = gen_scanned(cid)
        else:
            n = gen(cid)
        print(cid, n, 'blocks')
