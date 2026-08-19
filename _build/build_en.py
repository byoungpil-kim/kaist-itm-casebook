# -*- coding: utf-8 -*-
"""English mirror site builder: generates en/index.html and en/cases/{id}.html.

Same re-stitch model as build.py — en/cases/{id}.html IS the editable source for
its English body (between BODY:START/BODY:END). build_case() reads the body back
out and re-wraps it, so hand edits survive a rebuild. The seed for a case that has
no English page yet is _build/cases_en/{id}_body.html.

Korean strings come from assets/meta.json; English strings from assets/meta_en.json.
Full-text report links intentionally point at the KOREAN fulltext pages — the
reports themselves are not translated.
"""
import json, os, html, glob, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = ROOT
meta = json.load(open(f'{W}/assets/meta.json', encoding='utf-8'))
en = json.load(open(f'{W}/assets/meta_en.json', encoding='utf-8'))
by_id = {m['id']: m for m in meta}
EN = en['cases']
ISSUE_EN, CAT_EN, ADV_EN = en['issues'], en['cats'], en['advisors']
ISSUES = list(ISSUE_EN.values())
CATS = list(CAT_EN.values())

BODY_START = '<!-- BODY:START -->'
BODY_END = '<!-- BODY:END -->'


def pub_en(m):
    """'2024년 가을학기' → 'Fall 2024'."""
    season = 'Fall' if '가을' in m['semester'] or '가을' in m['pub'] else 'Spring'
    return f"{season} {m['year']}"


def name(ko, romanized):
    """Romanized name with the Korean form kept alongside."""
    if not ko:
        return '-'
    return f'{romanized} ({ko})' if romanized else ko


def issues_en(m):
    return [ISSUE_EN[i] for i in m['issues']]


def cats_en(m):
    return [CAT_EN[c] for c in m['categories']]


def load_body(cid):
    out_path = f'{W}/en/cases/{cid}.html'
    if os.path.exists(out_path):
        txt = open(out_path, encoding='utf-8').read()
        s, e = txt.find(BODY_START), txt.find(BODY_END)
        if s != -1 and e != -1 and e > s:
            return txt[s + len(BODY_START):e].strip('\n')
    frag = f'{ROOT}/_build/cases_en/{cid}_body.html'
    if os.path.exists(frag):
        return open(frag, encoding='utf-8').read().strip('\n')
    return None


def header(rel='', ko_href='../index.html'):
    return f'''<header class="site-header">
  <div class="wrap">
    <a class="logo" href="{rel}index.html">
      <span class="l1">ITM KAIST</span>
      <span class="l2">KAIST COLLEGE OF BUSINESS</span>
    </a>
    <nav class="gnb">
      <a href="{rel}index.html" class="on">Case Study Library</a>
      <a href="{ko_href}" class="lang">한국어</a>
      <a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener" class="ext">ITM website ↗</a>
    </nav>
  </div>
</header>'''


DISCLAIMER = '''<div class="ai-note">
  <b>Machine-translated page.</b> This English edition was produced automatically by AI from the
  Korean original. It has not been verified by the authors, and accuracy of terminology, figures,
  names and nuance is not guaranteed. The Korean edition is the authoritative version — please
  consult it for any citation or decision. Personal and organization names are romanized
  automatically and may differ from the form the individual uses.
</div>'''


def footer():
    return f'''{DISCLAIMER}
<footer class="site-footer">
  <div class="wrap">
    <div>
      <div class="f-logo">ITM KAIST <span class="f-sub">TECHNOLOGY &amp; INNOVATION MANAGEMENT</span></div>
      <p>KAIST Graduate School of Innovation &amp; Technology Management<br>
      291 Daehak-ro, Yuseong-gu, Daejeon, Republic of Korea<br>
      These case studies were selected from the master's thesis case studies of the KAIST ITM program.</p>
      <p class="copyright">Copyright in each case study belongs to its original author.
      Reproduction, redistribution or derivative use without prior written permission is prohibited.
      To cite or reuse this material, please obtain prior permission from the original author and
      the KAIST Graduate School of Innovation &amp; Technology Management.</p>
    </div>
    <div class="f-right">
      <p><a href="https://itm.kaist.ac.kr" target="_blank" rel="noopener">itm.kaist.ac.kr ↗</a><br>
      ⓒ Copyright by the original authors. All rights reserved.</p>
    </div>
  </div>
</footer>'''


def facet_sidebar(rel='', current_issue=None, current_cat=None, interactive=True):
    from collections import Counter
    cnt_issue = Counter(i for m in meta for i in issues_en(m))
    cnt_cat = Counter(c for m in meta for c in cats_en(m))

    def facet(title, items, counts, group, current):
        total = len(meta)
        lis = []
        if interactive:
            lis.append(f'<li><button class="on" data-g="{group}" data-v="All">All <span class="n">{total}</span></button></li>')
            for it in items:
                lis.append(f'<li><button data-g="{group}" data-v="{html.escape(it)}">{html.escape(it)} <span class="n">{counts.get(it,0)}</span></button></li>')
        else:
            import urllib.parse
            lis.append(f'<li><a class="fbtn" href="{rel}index.html">All <span class="n">{total}</span></a></li>')
            for it in items:
                q = urllib.parse.quote(it)
                cur = current if isinstance(current, (list, tuple, set)) else [current]
                on = ' on' if it in cur else ''
                lis.append(f'<li><a class="fbtn{on}" href="{rel}index.html?{group}={q}">{html.escape(it)} <span class="n">{counts.get(it,0)}</span></a></li>')
        return f'''<div class="facet"><div class="f-hd">{title}</div><ul>{''.join(lis)}</ul></div>'''

    return (facet('Management of technology', ISSUES, cnt_issue, 'issue', current_issue)
            + facet('Industry', CATS, cnt_cat, 'cat', current_cat)
            + '<p class="facet-note">Combine a management-of-technology theme with an industry to see cases that match both.</p>')


def build_index():
    cards = []
    for m in meta:
        e = EN[m['id']]
        chips = (''.join(f'<span class="chip">{html.escape(i)}</span>' for i in issues_en(m))
                 + ''.join(f'<span class="chip" style="color:#5a6b80;background:#EEF1F5;">{html.escape(c)}</span>' for c in cats_en(m)))
        firm = html.escape(e['firm']) if e['firm'] else '&nbsp;'
        s = (e['title'] + ' ' + e['firm'] + ' ' + e['author'] + ' ' + m['author'] + ' '
             + ' '.join(cats_en(m)) + ' ' + ' '.join(issues_en(m))).lower()
        cards.append(f'''<article class="card" data-cat="{html.escape('|'.join(cats_en(m)))}" data-issue="{html.escape('|'.join(issues_en(m)))}"
  data-s="{html.escape(s + ' ' + m['id'])}">
  <div class="top">{chips}<span class="caseno">[No. {m['id']}]</span></div>
  <h3><a href="cases/{m['id']}.html">{html.escape(e['title'])}</a></h3>
  <div class="firm">{firm}</div>
  <div class="meta"><span>{html.escape(name(m['author'], e['author']))}</span><span>{pub_en(m)}</span></div>
</article>''')
    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KAIST ITM Case Study Library</title>
<meta name="robots" content="noindex, nofollow">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
{header('', ko_href='../index.html')}
<section class="hero hero-v3">
  <svg class="hero-art" viewBox="0 0 1200 240" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <g fill="none" stroke="rgba(255,255,255,.16)" stroke-width="1.2">
      <path d="M-40 190 L180 120 L360 168 L560 86 L760 140 L960 70 L1240 118"/>
      <path d="M-40 216 L180 150 L360 196 L560 120 L760 172 L960 104 L1240 150"/>
    </g>
    <g fill="rgba(255,255,255,.5)">
      <circle cx="180" cy="120" r="5.5"/><circle cx="560" cy="86" r="5.5"/>
      <circle cx="960" cy="70" r="5.5"/><circle cx="1020" cy="118" r="5.5" fill-opacity=".9"/>
    </g>
  </svg>
  <div class="wrap">
    <h1>Learning at the intersection of technology and management<br><span class="en">ITM Case Study Library</span></h1>
    <p class="sub">Selected corporate innovation case studies from the master's program of the KAIST Graduate School of Innovation &amp; Technology Management (ITM).</p>
  </div>
</section>
<section class="grid-area">
  <div class="wrap layout">
    <aside class="facets">
      {facet_sidebar()}
    </aside>
    <div>
      <div class="toolbar">
        <input id="q" type="search" placeholder="Search by title, company, author or case number">
        <div class="count"><b id="cnt">{len(cards)}</b> cases</div>
      </div>
      <div class="mfilters">
        <select id="msel-issue" aria-label="Filter by management-of-technology theme">
          <option value="All">All themes</option>
          {''.join(f'<option value="{html.escape(i)}">{html.escape(i)}</option>' for i in ISSUES)}
        </select>
        <select id="msel-cat" aria-label="Filter by industry">
          <option value="All">All industries</option>
          {''.join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in CATS)}
        </select>
      </div>
      <div class="grid" id="grid">
{''.join(cards)}
      </div>
    </div>
  </div>
</section>
{footer()}
<script>
const sel = {{issue: 'All', cat: 'All'}};
function setFacet(g, v) {{
  document.querySelectorAll(`.facet button[data-g="${{g}}"]`).forEach(x => {{
    x.classList.toggle('on', x.dataset.v === v);
  }});
  sel[g] = v; syncSelects();
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
    const okI = (sel.issue === 'All' || c.dataset.issue.split('|').includes(sel.issue));
    const okC = (sel.cat === 'All' || c.dataset.cat.split('|').includes(sel.cat));
    const okQ = (!q || c.dataset.s.includes(q));
    const show = okI && okC && okQ;
    c.style.display = show ? '' : 'none';
    if (show) n++;
  }});
  document.getElementById('cnt').textContent = n;
}}
const usp = new URLSearchParams(location.search);
if (usp.get('issue')) setFacet('issue', usp.get('issue'));
if (usp.get('cat')) setFacet('cat', usp.get('cat'));
if (usp.get('issue') || usp.get('cat')) apply();
syncSelects();
</script>
</body>
</html>'''
    os.makedirs(f'{W}/en', exist_ok=True)
    open(f'{W}/en/index.html', 'w', encoding='utf-8').write(page)
    print('en/index.html written,', len(cards), 'cards')


def build_case(cid):
    m = by_id[cid]
    e = EN[cid]
    body = load_body(cid)
    if body is None:
        return False
    ids = [x['id'] for x in meta]
    i = ids.index(cid)
    prv = by_id[ids[i + 1]] if i + 1 < len(ids) else None
    nxt = by_id[ids[i - 1]] if i - 1 >= 0 else None
    pn = '<div class="prevnext" style="padding:0;">'
    if prv:
        pn += f'<a class="pn" href="{prv["id"]}.html"><div class="dir">← Previous case</div><div class="ttl">{html.escape(EN[prv["id"]]["title"])}</div></a>'
    if nxt:
        pn += f'<a class="pn next" href="{nxt["id"]}.html"><div class="dir">Next case →</div><div class="ttl">{html.escape(EN[nxt["id"]]["title"])}</div></a>'
    pn += '</div>'
    chips = (''.join(f'<span class="chip">{html.escape(i)}</span>' for i in issues_en(m))
             + ''.join(f'<span class="chip">{html.escape(c)}</span>' for c in cats_en(m)))
    dl = f'''<div class="dlbar-inner"><div class="dlcard">
  <div><div class="t">Full case study report</div>
  <div class="s">{html.escape(e['title'])} — {html.escape(name(m['author'], e['author']))} ({pub_en(m)})<br>
  <span style="color:var(--gray-4);">The full report is available in Korean only.</span></div></div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;"><a class="btn" href="../../fulltext/{cid}/index.html">Read full report (Korean) →</a></div>
</div></div>'''
    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(e['title'])} | KAIST ITM Case Study</title>
<meta name="robots" content="noindex, nofollow">
<link rel="stylesheet" href="../../assets/style.css">
</head>
<body>
{header('../', ko_href=f'../../cases/{cid}.html')}
<section class="art-hero">
  <div class="wrap">
    <div class="crumb"><a href="../index.html">Case Study Library</a> &nbsp;›&nbsp; {html.escape(ISSUE_EN[m['issue']])} &nbsp;›&nbsp; {html.escape(CAT_EN[m['category']])}</div>
    <div class="chips">{chips}<span class="caseno caseno-hero">[No. {cid}]</span></div>
    <h1>{html.escape(e['title'])}</h1>
    <div class="byline">
      <span><span class="lbl">Author</span><b>{html.escape(name(m['author'], e['author']))}</b></span>
      <span><span class="lbl">Advisor</span><b>{html.escape(name(m['advisor'], ADV_EN.get(m['advisor'], '')))}</b></span>
      <span><span class="lbl">Presented</span><b>{pub_en(m)}</b></span>
      {f'<span><span class="lbl">Company</span><b>{html.escape(e["firm"])}</b></span>' if e['firm'] else ''}
    </div>
  </div>
</section>
<div class="wrap layout case-layout">
  <aside class="facets">
    {facet_sidebar(rel='../', current_issue=issues_en(m), current_cat=cats_en(m), interactive=False)}
  </aside>
  <div class="mfilters mfilters-case">
    <select aria-label="Filter by management-of-technology theme" onchange="if(this.value)location.href='../index.html?issue='+encodeURIComponent(this.value)">
      <option value="">Browse by theme…</option>
      {''.join(f'<option value="{html.escape(i)}">{html.escape(i)}</option>' for i in ISSUES)}
    </select>
    <select aria-label="Filter by industry" onchange="if(this.value)location.href='../index.html?cat='+encodeURIComponent(this.value)">
      <option value="">Browse by industry…</option>
      {''.join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in CATS)}
    </select>
  </div>
  <div>
    <main class="art-body case-art">
{BODY_START}
{body}
{BODY_END}
    </main>
    {dl}
    {pn}
  </div>
</div>
{footer()}
</body>
</html>'''
    os.makedirs(f'{W}/en/cases', exist_ok=True)
    open(f'{W}/en/cases/{cid}.html', 'w', encoding='utf-8').write(page)
    return True


if __name__ == '__main__':
    build_index()
    done = [cid for cid in by_id if build_case(cid)]
    missing = [cid for cid in by_id if cid not in done]
    print('en case pages built:', len(done))
    if missing:
        print('  not translated yet:', ' '.join(sorted(missing)))
