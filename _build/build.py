# -*- coding: utf-8 -*-
"""Static site builder: generates index.html and wraps case body fragments into full pages."""
import json, os, html, glob, re

# repo layout: this script lives in _build/, site root is the parent directory
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = ROOT
meta = json.load(open(f'{W}/assets/meta.json'))
by_id = {m['id']: m for m in meta}
ISSUES = ['파괴적 혁신·신시장', '기술추격·흡수역량', '플랫폼·생태계', '강소기업·딥테크 성장',
          '디지털 전환·공정혁신', 'R&D·특허 전략', '제품혁신·아키텍처', '시장확산·캐즘 극복', '공공·기술사업화']
CATS = ['IT·플랫폼', '제조·중공업', '기계·장비·부품', '항공·방산', '바이오·헬스케어', '배터리·소재', '소비재·유통', '공공·기술사업화']

def header(rel=''):
    return f'''<header class="site-header">
  <div class="wrap">
    <a class="logo" href="{rel}index.html">
      <span class="l1">ITM KAIST</span>
      <span class="l2">KAIST COLLEGE OF BUSINESS</span>
    </a>
    <nav class="gnb">
      <a href="{rel}index.html" class="on">사례연구 라이브러리</a>
      <a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener" class="ext">ITM 홈페이지 ↗</a>
    </nav>
  </div>
</header>'''

def footer():
    return '''<footer class="site-footer">
  <div class="wrap">
    <div>
      <div class="f-logo">ITM KAIST <span class="f-sub">TECHNOLOGY &amp; INNOVATION MANAGEMENT</span></div>
      <p>KAIST 기술경영전문대학원 · Graduate School of Innovation &amp; Technology Management<br>
      대전광역시 유성구 대학로 291 KAIST 기술경영학부동(N22)<br>
      본 사례연구는 KAIST ITM 석사과정 졸업 사례연구 중 우수사례로 선정된 자료입니다.</p>
      <p class="copyright">본 사이트에 게시된 각 사례연구의 저작권은 해당 원저자(연구자)에게 귀속됩니다.
      사전 서면 허락 없는 무단 전재·복제·배포·2차적 저작물 작성을 금하며,
      인용 또는 활용을 원하시는 경우 반드시 원저자 및 KAIST 기술경영전문대학원의 사전 허락을 받으시기 바랍니다.</p>
    </div>
    <div class="f-right">
      <p><a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener">itm.kaist.ac.kr ↗</a><br>
      ⓒ Copyright by the original authors. All rights reserved.<br>무단 전재 및 재배포 금지</p>
    </div>
  </div>
</footer>'''

def facet_sidebar(rel='', current_issue=None, current_cat=None, interactive=True):
    # current_issue may be a list (multi-issue)
    """Sidebar facets. interactive=True → buttons (index JS). False → links back to index."""
    from collections import Counter
    cnt_issue = Counter(i for m in meta for i in m['issues'])
    cnt_cat = Counter(m['category'] for m in meta)

    def facet(title, items, counts, group, current):
        total = len(meta)
        lis = []
        if interactive:
            lis.append(f'<li><button class="on" data-g="{group}" data-v="전체">전체 <span class="n">{total}</span></button></li>')
            for it in items:
                lis.append(f'<li><button data-g="{group}" data-v="{html.escape(it)}">{html.escape(it)} <span class="n">{counts.get(it,0)}</span></button></li>')
        else:
            import urllib.parse
            lis.append(f'<li><a class="fbtn" href="{rel}index.html">전체 <span class="n">{total}</span></a></li>')
            for it in items:
                q = urllib.parse.quote(it)
                cur = current if isinstance(current, (list, tuple, set)) else [current]
                on = ' on' if it in cur else ''
                lis.append(f'<li><a class="fbtn{on}" href="{rel}index.html?{group}={q}">{html.escape(it)} <span class="n">{counts.get(it,0)}</span></a></li>')
        return f'''<div class="facet"><div class="f-hd">{title}</div><ul>{''.join(lis)}</ul></div>'''

    return (facet('기술경영 쟁점', ISSUES, cnt_issue, 'issue', current_issue)
            + facet('산업 분류', CATS, cnt_cat, 'cat', current_cat)
            + '<p class="facet-note">\'기술경영 쟁점\'과 \'산업 분류\'를 함께 선택하면 두 분류에 모두 해당하는 사례를 확인할 수 있습니다.</p>')

def build_index():
    cards = []
    for m in meta:
        chips = ''.join(f'<span class="chip">{html.escape(i)}</span>' for i in m['issues']) + f'<span class="chip" style="color:#5a6b80;background:#EEF1F5;">{html.escape(m["category"])}</span>'
        firm = html.escape(m['firm']) if m['firm'] else '&nbsp;'
        s = (m['title']+' '+m['firm']+' '+m['author']+' '+m['category']+' '+' '.join(m['issues'])).lower()
        cards.append(f'''<article class="card" data-cat="{html.escape(m['category'])}" data-issue="{html.escape('|'.join(m['issues']))}"
  data-s="{html.escape(s + ' ' + m['id'])}">
  <div class="top">{chips}<span class="caseno">[No. {m['id']}]</span></div>
  <h3><a href="cases/{m['id']}.html">{html.escape(m['title'])}</a></h3>
  <div class="firm">{firm}</div>
  <div class="meta">{html.escape(m['author'])} · {m['pub']}</div>
  <div class="foot"><span>지도교수 {html.escape(m['advisor']) if m['advisor'] else '-'}</span><span class="more">자세히 보기 →</span></div>
</article>''')

    n_total = len(meta)

    page = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KAIST ITM 사례연구 라이브러리 | Case Study Library</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="KAIST 기술경영전문대학원(ITM) 석사과정 졸업 사례연구 우수사례 모음">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
{header()}
<section class="hero hero-v3">
  <svg class="hero-art" viewBox="0 0 1200 230" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
    <g fill="none" stroke="#7FB0FF">
      <circle cx="1020" cy="118" r="52" stroke-opacity=".28" stroke-width="1.4"/>
      <circle cx="1020" cy="118" r="92" stroke-opacity=".18" stroke-width="1.2" stroke-dasharray="3 7"/>
      <circle cx="1020" cy="118" r="138" stroke-opacity=".12" stroke-width="1"/>
      <circle cx="1020" cy="118" r="186" stroke-opacity=".07" stroke-width="1"/>
      <path d="M 640 210 C 760 140 900 190 1010 120 S 1180 40 1240 70" stroke-opacity=".25" stroke-width="1.6"/>
      <path d="M 600 230 C 740 180 880 230 1000 160 S 1190 90 1260 120" stroke-opacity=".15" stroke-width="1.3"/>
      <path d="M 820 24 L 906 62 L 986 30 L 1088 74 L 1176 44" stroke-opacity=".3" stroke-width="1.4"/>
    </g>
    <g fill="#7FB0FF">
      <circle cx="906" cy="62" r="4" fill-opacity=".7"/>
      <circle cx="986" cy="30" r="3" fill-opacity=".5"/>
      <circle cx="1088" cy="74" r="4.5" fill-opacity=".8"/>
      <circle cx="820" cy="24" r="2.6" fill-opacity=".45"/>
      <circle cx="1176" cy="44" r="3" fill-opacity=".5"/>
      <circle cx="1020" cy="118" r="5.5" fill-opacity=".9"/>
    </g>
  </svg>
  <div class="wrap">
    <h1>기술과 경영의 접점에서 배우는 <span class="en">ITM Case Study</span> 라이브러리</h1>
    <p class="sub">KAIST 기술경영전문대학원(ITM) 석사과정의 기업 혁신 사례연구 가운데 우수사례를 선별해 소개합니다.</p>
    <p class="wip">⚠ 본 사이트는 현재 제작 중인 초안(Work in Progress)으로 최종본이 아니며, 내용은 예고 없이 수정될 수 있습니다. 수정 요청·문의: <a href="mailto:byoungpil.kim@kaist.ac.kr">byoungpil.kim@kaist.ac.kr</a></p>
  </div>
</section>
<section class="grid-area">
  <div class="wrap layout">
    <aside class="facets">
      {facet_sidebar(interactive=True)}
    </aside>
    <div>
      <div class="mfilters">
        <select id="msel-issue" aria-label="기술경영 쟁점">
          <option value="전체">기술경영 쟁점: 전체</option>
          {''.join(f'<option value="{html.escape(i)}">{html.escape(i)}</option>' for i in ISSUES)}
        </select>
        <select id="msel-cat" aria-label="산업 분류">
          <option value="전체">산업 분류: 전체</option>
          {''.join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in CATS)}
        </select>
      </div>
      <div class="toolbar">
        <div style="display:flex;align-items:center;gap:22px;">
          <span class="count">총 <b id="cnt">{n_total}</b>건</span>
        </div>
        <div class="searchbox">
          <input id="q" type="search" placeholder="기업명·키워드·제목 검색" aria-label="검색">
          <button onclick="apply()">검색</button>
        </div>
      </div>
      <div class="grid" id="grid">
        {''.join(cards)}
      </div>
    </div>
  </div>
</section>
{footer()}
<script>
const sel = {{ issue: '전체', cat: '전체' }};
function setFacet(g, v) {{
  let found = false;
  document.querySelectorAll(`.facet button[data-g="${{g}}"]`).forEach(x => {{
    const on = (x.dataset.v === v);
    x.classList.toggle('on', on);
    if (on) found = true;
  }});
  if (found) sel[g] = v;
}}
document.querySelectorAll('.facet button').forEach(b => b.addEventListener('click', () => {{
  const g = b.dataset.g;
  document.querySelectorAll(`.facet button[data-g="${{g}}"]`).forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  sel[g] = b.dataset.v;
  syncSelects();
  apply();
}}));
function syncSelects() {{
  const si = document.getElementById('msel-issue'), sc = document.getElementById('msel-cat');
  if (si) si.value = sel.issue; if (sc) sc.value = sel.cat;
}}
['issue','cat'].forEach(g => {{
  const el = document.getElementById('msel-' + g);
  if (el) el.addEventListener('change', () => {{ sel[g] = el.value; setFacet(g, el.value); apply(); }});
}});
document.getElementById('q').addEventListener('input', apply);
function apply() {{
  const q = document.getElementById('q').value.trim().toLowerCase();
  let n = 0;
  document.querySelectorAll('#grid .card').forEach(c => {{
    const okI = (sel.issue === '전체' || c.dataset.issue.split('|').includes(sel.issue));
    const okC = (sel.cat === '전체' || c.dataset.cat === sel.cat);
    const okQ = (!q || c.dataset.s.includes(q));
    const show = okI && okC && okQ;
    c.style.display = show ? '' : 'none';
    if (show) n++;
  }});
  document.getElementById('cnt').textContent = n;
}}
// apply URL params (?issue=...&cat=...) from case-page sidebar links
const usp = new URLSearchParams(location.search);
if (usp.get('issue')) setFacet('issue', usp.get('issue'));
if (usp.get('cat')) setFacet('cat', usp.get('cat'));
if (usp.get('issue') || usp.get('cat')) apply();
syncSelects();
</script>
</body>
</html>'''
    open(f'{W}/index.html', 'w').write(page)
    print('index.html written,', len(cards), 'cards')

def build_case(cid):
    m = by_id[cid]
    frag_path = f'{ROOT}/_build/cases_src/{cid}_body.html'
    if not os.path.exists(frag_path):
        return False
    body = open(frag_path).read()
    ids = [x['id'] for x in meta]  # newest first
    i = ids.index(cid)
    prv = by_id[ids[i+1]] if i+1 < len(ids) else None   # older
    nxt = by_id[ids[i-1]] if i-1 >= 0 else None         # newer
    pn = '<div class="prevnext" style="padding:0;">'
    if prv:
        pn += f'<a class="pn" href="{prv["id"]}.html"><div class="dir">← 이전 사례</div><div class="ttl">{html.escape(prv["title"])}</div></a>'
    if nxt:
        pn += f'<a class="pn next" href="{nxt["id"]}.html"><div class="dir">다음 사례 →</div><div class="ttl">{html.escape(nxt["title"])}</div></a>'
    pn += '</div>'
    chips = ''.join(f'<span class="chip">{html.escape(i)}</span>' for i in m['issues']) + f'<span class="chip">{html.escape(m["category"])}</span>'
    dl = f'''<div class="dlbar-inner"><div class="dlcard">
  <div><div class="t">사례연구 원문 보고서</div>
  <div class="s">{html.escape(m['title'])} — {html.escape(m['author'])} ({m['pub']})</div></div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;"><a class="btn" href="../fulltext/{cid}/index.html" target="_blank" rel="noopener">원문 전체 보기 →</a></div>
</div></div>'''
    page = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(m['title'])} | KAIST ITM 사례연구</title>
<meta name="robots" content="noindex, nofollow">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
{header('../')}
<section class="art-hero">
  <div class="wrap">
    <div class="crumb"><a href="../index.html">사례연구 라이브러리</a> &nbsp;›&nbsp; {html.escape(m['issue'])} &nbsp;›&nbsp; {html.escape(m['category'])}</div>
    <div class="chips">{chips}<span class="caseno caseno-hero">[No. {cid}]</span></div>
    <h1>{html.escape(m['title'])}</h1>
    <div class="byline">
      <span><span class="lbl">연구자</span><b>{html.escape(m['author'])}</b></span>
      <span><span class="lbl">지도교수</span><b>{html.escape(m['advisor']) if m['advisor'] else '-'}</b></span>
      <span><span class="lbl">발표</span><b>{m['pub']}</b></span>
      {f'<span><span class="lbl">대상 기업</span><b>{html.escape(m["firm"])}</b></span>' if m['firm'] else ''}
    </div>
  </div>
</section>
<div class="wrap layout case-layout">
  <aside class="facets">
    {facet_sidebar(rel='../', current_issue=m['issues'], current_cat=m['category'], interactive=False)}
  </aside>
  <div class="mfilters mfilters-case">
    <select aria-label="기술경영 쟁점으로 찾기" onchange="if(this.value)location.href='../index.html?issue='+encodeURIComponent(this.value)">
      <option value="">기술경영 쟁점으로 찾기…</option>
      {''.join(f'<option value="{html.escape(i)}">{html.escape(i)}</option>' for i in ISSUES)}
    </select>
    <select aria-label="산업 분류로 찾기" onchange="if(this.value)location.href='../index.html?cat='+encodeURIComponent(this.value)">
      <option value="">산업 분류로 찾기…</option>
      {''.join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in CATS)}
    </select>
  </div>
  <div>
    <main class="art-body case-art">
{body}
    </main>
    {dl}
    {pn}
  </div>
</div>
{footer()}
</body>
</html>'''
    open(f'{W}/cases/{cid}.html', 'w').write(page)
    return True

if __name__ == '__main__':
    build_index()
    done = [cid for cid in by_id if build_case(cid)]
    print('case pages built:', len(done))
