"""
Static site generator. Reads data/, writes site/_out/. Never fetches.

Local only for now — `./serve.sh` builds and serves at 127.0.0.1:8788. Nothing here
deploys anywhere.

Every figure rendered comes from a file under data/, which is derived from bytes under
archive/, which carry the fetch that produced them. If a number cannot be traced back
that far it does not belong on a page.

Where a value is absent at source it renders as "..." — the nil-mark from Union Budget
Statements 4A/4B — and never as a blank or a zero. Absence is the subject here, so it
gets a notation rather than a gap.
"""

import argparse
import hashlib
import html
import json
import re
import os
import shutil
import subprocess
import urllib.parse
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_out")

# Set this when the site gets a home. Used only for sitemap and canonical URLs.
SITE_BASE = os.environ.get("SITE_BASE", "https://schemes.pages.dev").rstrip("/")

ISSUE_URL = "https://github.com/urbanmorph/schemes/issues/new"

FONTS = ("https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400"
         "&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap")

# The scheme index lives on "/" rather than behind its own route. The argument and the
# evidence for it are the same page: someone who reads that 99% of schemes carry no end
# date should be able to scroll straight into the list and check it, without treating
# "see the data" as a separate destination.
ROUTES = [("/", "index.html"), ("/divergence", "divergence.html"),
          ("/changes", "changes.html")]


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


# Stopwords for the search keyword extract. Kept deliberately blunt: the aim is to drop
# words that appear in almost every scheme description, not to do linguistics.
_KW_STOP = set("""a an the of for and or to in on at by with from as is are was were be
been being this that these those it its their they them he she his her which who whom
whose what when where why how all any both each few more most other some such no nor not
only own same so than too very can will just should now under over between into during
scheme schemes yojana yojna government state central india indian department ministry
provided provide provides shall may must also been being will benefit benefits
beneficiary beneficiaries applicant applicants eligible eligibility assistance amount
rs per year years annum through under given give given""".split())


def keywords(text, name, limit=8):
    """Distinctive words from a description, for search.

    The full description would be the better index and costs far too much: 242 characters
    on 4,767 rows is about 170 KB gzipped on a page that is already heavy. Words already
    in the scheme name are dropped too, since the name is indexed separately.

    Eight is where the curve flattens. Measured on the built page, against a baseline of
    346 KB with no description indexed at all:

        limit  6  ->  418 KB   "widow" finds 100
        limit  8  ->  444 KB   "widow" finds 109
        limit 10  ->  468 KB   "widow" finds 125
        limit 14  ->  516 KB   "widow" finds 134

    Eight buys 81% of the coverage for 58% of the weight.
    """
    have = set(re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).split())
    out, seen = [], set()
    for w in re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split():
        if len(w) < 4 or w in _KW_STOP or w in have or w in seen or w.isdigit():
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def md(src, limit=None):
    """A deliberately small markdown subset: paragraphs, lists, bold, italic, links.

    Escaped before any formatting is applied, because this text comes from an external
    API and is rendered verbatim on 4,700 pages. Only http and https links are emitted.
    """
    if not src:
        return ""
    t = src if limit is None else src[:limit]
    # The source mixes markdown with stray HTML line breaks; escaping first would render
    # them as visible "<br>" text on the page.
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    # Source text is reproduced as published, except for dash punctuation: 35 of the
    # 4,771 descriptions use an em-dash and the house rule is that none reach the page.
    # An en-dash rather than a comma, because where the author reached for a dash a dash
    # is what the sentence wants; swapping in a comma rewrites their punctuation instead
    # of restyling it. Declared on the page rather than done silently.
    t = re.sub(r"\u2014", "\u2013", t)
    t = e(t)
    t = re.sub(r"&amp;quot;", "&quot;", t)
    t = re.sub(r"\[([^\]]{1,120})\]\((https?://[^\s)]{1,300})\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"\*\*([^*]{1,300})\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]{1,300})\*(?![*\w])", r"<i>\1</i>", t)

    html_out, bullets = [], []

    def flush():
        if bullets:
            html_out.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for raw in t.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        m = re.match(r"^(?:[-*\u2022]|\d+\.)\s+(.*)$", line)
        if m:
            bullets.append(m.group(1))
        else:
            flush()
            html_out.append(f"<p>{line}</p>")
    flush()
    return "".join(html_out)


def inr(x):
    """Indian digit grouping: last three, then pairs. 1864350 -> 18,64,350.

    A register of Indian government spending should write rupee figures the way the
    Budget documents it draws from write them. It also stops the number reformatting
    when the browser recomputes it, since the client already uses en-IN.
    """
    try:
        n = int(round(float(x)))
    except (TypeError, ValueError):
        return None
    sign = "-" if n < 0 else ""
    d = str(abs(n))
    if len(d) <= 3:
        return sign + d
    head, tail = d[:-3], d[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts) + "," + tail


def num(x):
    return f"{x:,}" if isinstance(x, (int, float)) else '<span class="nil">...</span>'


def load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------- chrome

def shell(title, active, body, depth=0, desc="", canon=""):
    # Descriptions are built from source text that has not been through md(), so the
    # dash rule has to be applied here too or the build guard catches it later.
    desc = re.sub(r"\u2014", "\u2013", desc or "")
    up = "../" * depth
    st = shell.status or {}
    verdict = st.get("verdict")
    if verdict == "COMPLETE":
        dot, word = "", "COMPLETE"
    elif verdict:
        dot, word = " bad", verdict
    else:
        dot, word = " warn", "no run yet"

    days = "..."
    if st.get("last_complete_run"):
        try:
            t = datetime.fromisoformat(st["last_complete_run"].replace("Z", "+00:00"))
            d = (datetime.now(timezone.utc) - t).days
            days = "today" if d == 0 else f"{d} day{'s' if d != 1 else ''} ago"
        except Exception:
            pass

    # `href="{up}"` produced an empty href at depth 0, which resolves to the current
    # document — so "/" in the nav silently reloaded whatever page you were already on
    # instead of going home. `up or "./"` gives "./" at the root and "../" one level down.
    home = up or "./"
    nav = "".join(
        f'<a class="route{" on" if r == active else ""}" '
        f'href="{home if f == "index.html" else up + f}">{e(r)}</a>'
        for r, f in ROUTES)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} &middot; The Schemes Register</title>
<meta name="description" content="{e(desc[:158])}">
<meta property="og:title" content="{e(title)} &middot; The Schemes Register">
<meta property="og:description" content="{e(desc[:158])}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{up}theme.css?v={CSS_V}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='6' cy='21' r='3.4' fill='%23C26E0D'/%3E%3Ccircle cx='16' cy='21' r='3.4' fill='%23C26E0D'/%3E%3Ccircle cx='26' cy='21' r='3.4' fill='%23C26E0D'/%3E%3C/svg%3E">
</head><body>
<a class="skip" href="#main">Skip to the register</a>
<header class="mast"><div class="wrap mast-in">
  <a class="brand" href="{home}">
    <span class="nil" aria-hidden="true">...</span>
    <span><span class="brandname">The Schemes Register</span>
    <span class="sub">Indian government scheme data &middot; and what is missing from it</span></span>
  </a>
  <nav class="routes" aria-label="Sections">{nav}</nav>
  <button class="tbtn" id="themeBtn" type="button">&#9686; theme</button>
</div></header>
<div class="fresh"><div class="wrap">
  <span class="dot{dot}"></span>
  <span>Last complete collection <b>{days}</b></span>
  <span class="sep">&middot;</span><span>snapshot <b>{e(st.get('snapshot') or '...')}</b></span>
  <span class="sep">&middot;</span>
  <span>{num(st.get('records_parsed'))} of {num(st.get('expected_total'))} records
        &middot; {num(st.get('pages_written'))}/{num(st.get('pages_expected'))} pages</span>
  <span class="sep">&middot;</span><span>verdict <b>{e(word)}</b></span>
  <span class="sep">&middot;</span><span>{num(st.get('snapshots'))} snapshot(s) held</span>
</div></div>
<main id="main" tabindex="-1"><div class="wrap">{body}</div></main>
<footer><div class="wrap">
  <div class="srcs">
    <b>Every figure on this page comes from one of four government sources</b>
    <a href="https://www.myscheme.gov.in/" target="_blank" rel="noopener">myScheme</a>
    <span>scheme records, eligibility, benefits</span>
    <a href="https://www.indiabudget.gov.in/doc/eb/stat4a.pdf" target="_blank" rel="noopener">Union Budget, Statements 4A and 4B</a>
    <span>per-scheme allocations</span>
    <a href="https://www.indiabudget.gov.in/" target="_blank" rel="noopener">Outcome Budget, Output Outcome Monitoring Framework</a>
    <span>output and outcome targets</span>
    <a href="https://dbtbharat.gov.in/" target="_blank" rel="noopener">DBT Bharat</a>
    <span>direct benefit transfer listings</span>
    <p>Collected {e(st.get('snapshot') or '')} and archived byte for byte, so any figure
    here can be traced to the request that produced it. Nothing on this site is
    calculated from a source that is not named above.</p>
  </div>
  <div class="foot">
    <span>The Schemes Register &middot; local build, not deployed</span>
    <span><a href="{ISSUE_URL}?template=missing-figure.yml" target="_blank" rel="noopener">Report a wrong or missing figure</a>
      &middot; code MIT, data CC BY 4.0</span>
  </div>
</div></footer>
<script>
document.getElementById('themeBtn').addEventListener('click',function(){{
  var r=document.documentElement,c=r.getAttribute('data-theme');
  if(!c)c=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  r.setAttribute('data-theme',c==='dark'?'light':'dark');
}});
</script>
</body></html>"""


shell.status = {}

# Content hash in the stylesheet URL. Without it a browser happily pairs freshly built
# HTML with a cached stylesheet, which is not a cosmetic problem: the hero markup and
# the hero CSS changed together, and the old grid applied to the new markup laid the
# title and standfirst out as two columns. Versioning the URL makes that pairing
# impossible instead of relying on anyone remembering to hard-refresh.
def _css_version():
    try:
        with open(os.path.join(HERE, "theme.css"), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:8]
    except OSError:
        return "0"


CSS_V = _css_version()


# --------------------------------------------------------------------- pages

def page_index(census, checks, dbt, entries):
    facets = (census or {}).get("facets", {})
    lvl = facets.get("level", {})
    stype = facets.get("schemeType", {})
    summ = (checks or {}).get("summary", {})
    by = summ.get("by_check", {})

    def failpct(k):
        v = by.get(k)
        return f'{v["fail_pct"]}%' if v else '<span class="nil">...</span>'

    dbt_total = (dbt or {}).get("state_total")
    ms_state = lvl.get("State")

    cells = [
        ("myScheme total", num((census or {}).get("total")), "api/search/v6"),
        ("Central", num(lvl.get("Central")), "level facet"),
        ("State", num(ms_state), "level facet"),
        ("DBT state schemes", num(dbt_total), "36 dashboards"),
        ("Outcome framework", '<span class="nil">...</span>', "not yet parsed"),
    ]
    strip = "".join(f'<div class="cell"><div class="k">{e(k)}</div>'
                    f'<div class="v">{v}</div><div class="n">{e(n)}</div></div>'
                    for k, v, n in cells)

    kar_ms = facets.get("beneficiaryState", {}).get("Karnataka")
    kar_dbt = (dbt or {}).get("states", {}).get("Karnataka")

    qrows = ""
    for k, label in [("implementing_agency_named", "Implementing agency named"),
                     ("end_date_recorded", "End date recorded"),
                     ("stored_urls_well_formed", "Stored URLs well-formed"),
                     ("eligibility_documented", "Eligibility documented"),
                     ("benefit_quantified", "Benefit quantified")]:
        v = by.get(k)
        if not v:
            continue
        qrows += (f'<tr><td>{e(label)}</td><td class="num">{num(v["fail"])}</td>'
                  f'<td class="num gap">{v["fail_pct"]}%</td></tr>')

    return f"""
<div class="topline">
  <div>
    <div class="eyebrow">The census</div>
    <h1 class="pagetitle">Every scheme any government source names,
      and what each one fails to say</h1>
  </div>
  <a class="jump" href="#argument">Why this exists &darr;</a>
</div>

{index_section(entries)}

<section class="hero" id="argument">
  <div class="bignil" aria-hidden="true">...</div>
  <div class="eyebrow">The argument</div>
  <h2>Karnataka runs {num(kar_ms)} welfare schemes. Or {num(kar_dbt)}. It depends which government portal you <em>ask</em>.</h2>
  <p class="standfirst muted">Three central government sources publish counts of India's
  welfare schemes. None of them agree, none reconciles to the others, and none keeps a
  record of what it said last month. This register keeps that record, and publishes
  what is missing as carefully as what is there.</p>
</section>

<div class="census">{strip}</div>

<section class="sec">
  <h2>What this is</h2>
  <div class="sec-note">And, more to the point, what it is not</div>
  <div class="measure">
    <p>This is not a list of schemes you can apply to. myScheme already does that.
    This is a record of <em>the data about</em> those schemes: how completely each one is
    documented, whether the sources contradict one another, and what changed since last
    month.</p>
    <p>Every claim here is about government publishing practice, never about whether a
    scheme works. &ldquo;No end date recorded&rdquo; is a fact about a database field. It
    is not a judgment on the scheme.</p>
  </div>
</section>

<section class="sec">
  <h2>What the records are missing</h2>
  <div class="sec-note">Tier-1 checks &middot; deterministic, no network, no false positives
    &middot; {num(summ.get('schemes'))} schemes</div>
  <div class="tscroll"><table>
    <thead><tr><th>Check</th><th class="num">Schemes failing</th><th class="num">Share</th></tr></thead>
    <tbody>{qrows or '<tr><td colspan="3" class="muted">run parse/checks.py</td></tr>'}</tbody>
  </table></div>
  <div class="sec-note" style="margin-top:9px">Link reachability and cross-source joins are
    deliberately not here yet. Both carry real error bars and belong behind a
    methodology page. These do not.</div>
</section>
"""


def page_divergence(census, dbt, reg=None, cls=None, entries=None, ka=None, ap=None):
    """Two questions, kept apart: how many schemes a state has, and which are unlisted.

    The per-state table and the unlisted-schemes table were both built into a local named
    `rows`, and the second assignment won. For every build until this was caught, the
    table headed "State | myScheme | DBT Bharat" rendered 69 Union Budget lines: PM-KISAN
    appeared under a column headed State. The page's own thesis was the thing missing
    from it. Both tables now carry distinct names.
    """
    ds = (dbt or {}).get("states", {})

    # Count state schemes, not state TAGS. The census facet is a beneficiary tag and all
    # 711 central schemes carry one, so reading it as a per-state scheme count folds
    # central schemes into every state's number. Almost all are tagged "All" and drop out
    # here, but a few are pinned to named states: Karnataka's facet of 60 is 56 state
    # schemes plus 4 central ones. Comparing a mixed number against DBT's state-scheme
    # count compares different things while claiming to expose exactly that error.
    ms = {}
    for en in (entries or []):
        if en.get("level_value") == "central" or not en.get("on_myscheme"):
            continue
        st = en.get("state")
        for n in (st if isinstance(st, list) else [st] if st else []):
            if n and n != "All":
                ms[n] = ms.get(n, 0) + 1
    if not ms:   # no unified entries passed; fall back to the facet rather than blank
        ms = {k: v for k, v in
              (census or {}).get("facets", {}).get("beneficiaryState", {}).items()}

    state_rows = ""
    for n in sorted(set(ms) | set(ds)):
        if n == "All":
            continue
        a, b = ms.get(n), ds.get(n)
        gap = f"{b - a:+,}" if a is not None and b is not None else '<span class="nil">...</span>'
        direction = ("DBT higher" if a and b and b > a
                     else "myScheme higher" if a and b and a > b else "not comparable")
        state_rows += (f'<tr><td>{e(n)}</td><td class="num">{num(a)}</td>'
                       f'<td class="num">{num(b)}</td><td class="num">{gap}</td>'
                       f'<td class="muted">{e(direction)}</td></tr>')

    # The variance finding. A count gap between two portals can always be argued away as
    # different units. A gap WITHIN one portal cannot: these are all myScheme's own
    # numbers, counted the same way on the same day.
    def pair(a, b):
        x, y = ms.get(a, 0), ms.get(b, 0)
        return (a, x, b, y, x / y) if y else (a, x, b, y, None)
    pairs = [pair(*p) for p in (("Gujarat", "Karnataka"),
                                ("Uttarakhand", "Uttar Pradesh"),
                                ("Goa", "Telangana"),
                                ("Haryana", "Punjab"))]
    pair_rows = "".join(
        f'<tr><td>{e(a)}</td><td class="num">{num(x)}</td><td>{e(b)}</td>'
        f'<td class="num">{num(y)}</td>'
        f'<td class="num">{f"{r:.1f}&times;" if r else "..."}</td></tr>'
        for a, x, b, y, r in pairs)
    total_ms, total_ds = sum(ms.values()), sum(v for v in ds.values() if v)
    higher = sum(1 for n in ms if ds.get(n) and ds[n] > ms[n])

    kar_ms, kar_dbt = ms.get("Karnataka"), ds.get("Karnataka")

    # A state's own budget against the national portal. The central sections of this page
    # answer "which funded schemes is the Union not telling citizens about". This answers
    # the same question one level down, where until now the page could only report a count.
    ka_section = ""
    if ka and ka.get("absent_schemes"):
        v = ka.get("validation", {})
        cen = v.get("at_publish_threshold_census", {})
        rows_ka = "".join(
            f'<tr><td>{e(r["name"])}'
            + (f'<div class="sub2">{e(r["purpose"])}</div>' if r.get("purpose") else "")
            + f'</td><td class="num">{inr(round((r["be_lakh"] or 0) / 100))}</td>'
            f'<td class="num">{r["score"]}</td>'
            f'<td class="muted" style="font-size:12px">{e("; ".join(w for _, w in r.get("evidence", [])[:2]))}</td></tr>'
            for r in ka["absent_schemes"])
        ka_section = f"""
<section class="sec">
  <h2>Karnataka&rsquo;s own budget names schemes its citizens cannot look up</h2>
  <div class="sec-note">Karnataka Budget {e(str(ka.get('cycle') or ''))}, scheme-wise books
    &middot; {num(ka.get('classified_scheme'))} of {num(ka.get('classified_scheme', 0) + ka.get('classified_not_scheme', 0))}
    rows survive classification as schemes</div>
  <p class="standfirst">The state publishes its Gender, Child and SCSP/TSP budgets, and
  between them they name {num((ka.get('classified_scheme') or 0) + (ka.get('classified_not_scheme') or 0))}
  budget heads. myScheme lists {num(ka.get('myscheme_karnataka_records'))} schemes for
  Karnataka. These {num(len(ka['absent_schemes']))} are on the state&rsquo;s books, carry
  money, read as schemes, and are on the national portal nowhere.</p>
  <div class="tscroll"><table>
    <thead><tr><th>In Karnataka&rsquo;s budget, absent from myScheme</th>
      <th class="num">2026&ndash;27 (&#8377; cr)</th><th class="num">Score</th>
      <th>Why it scores as a scheme</th></tr></thead>
    <tbody>{rows_ka}</tbody>
  </table></div>
  <div class="warnbox">
    <b>This is a floor, and the errors in it are counted rather than estimated</b>
    A budget book lists colleges, commissionerates and building heads beside schemes, and
    calling one of those a hidden scheme would be a false accusation. Every row is scored
    on signals published with the arithmetic, validated against
    {num((ka.get('ground_truth') or {}).get('labelled'))} hand labels.
    <p style="margin:8px 0 0">Precision at the published bar is
    {cen.get('precision', 0):.1%}, and that is a count: every row scoring at or above the
    coverage threshold carries a hand label, so the errors in this table are
    {num(cen.get('not_schemes'))} named ones rather than an estimate. Recall is
    {v.get('at_publish_threshold', {}).get('recall', 0):.0%}, so the table is a floor and
    never a total. Gruha Lakshmi, Karnataka&rsquo;s largest welfare scheme, is missing from
    it: 580 of the {num((ka.get('classified_scheme') or 0) + (ka.get('classified_not_scheme') or 0))}
    rows carry no purpose line, and a real scheme with a plain name and no stated purpose
    cannot clear a high bar on the evidence the books print.</p>
  </div>
</section>"""

    # Andhra Pradesh. Written parallel to the Karnataka block above rather than sharing a
    # helper with it, because the two states publish different evidence: Karnataka prints a
    # purpose line and Andhra Pradesh prints a head of account and a department. When a
    # third state lands, the chrome is worth factoring out and the row builders are not.
    ap_section = ""
    if ap and ap.get("absent_distinct"):
        v2 = ap.get("validation", {})
        cen2 = v2.get("at_publish_threshold_census", {})
        rows_ap = "".join(
            f'<tr><td>{e(r["name"])}'
            + (f'<div class="sub2">funded by {num(len(r["departments"]))} departments: '
               f'{e(", ".join(d.replace(" Department", "") for d in r["departments"]))}</div>'
               if len(r["departments"]) > 1 else "")
            + f'</td><td class="num">{inr(round((r["be_lakh"] or 0) / 100))}</td>'
            f'<td class="num">{r["score"]}</td>'
            f'<td class="muted" style="font-size:12px">{e("; ".join(w for _, w in r.get("evidence", [])[:2]))}</td></tr>'
            for r in ap["absent_distinct"])
        tot_ap = sum(r["be_lakh"] or 0 for r in ap["absent_distinct"]) / 100
        # Read from the data, never typed in. A hardcoded 69 on this page had already
        # drifted once while the number behind it moved.
        top_ap = max(ap["absent_distinct"], key=lambda r: r["be_lakh"] or 0)
        miss_ap = max((x for x in (ap.get("all_entries") or [])
                       if x.get("verdict") != "scheme"),
                      key=lambda x: x.get("be_lakh") or 0, default=None)
        ap_section = f"""
<section class="sec">
  <h2>Andhra Pradesh, where the portal and the budget describe different countries</h2>
  <div class="sec-note">Andhra Pradesh Budget {e(str(ap.get('cycle') or ''))}, six
    scheme-wise books &middot; {num(len(ap['absent_distinct']))} schemes,
    {inr(round(tot_ap))} crore</div>
  <p class="standfirst">myScheme lists {num(ap.get('myscheme_andhra_records'))} schemes for
  Andhra Pradesh: corporation and welfare-board items, tricycles, spectacles, pensions. The
  state&rsquo;s own budget names its largest programmes, and not one of them reaches the
  portal. {e(top_ap["name"])} alone is {inr(round((top_ap["be_lakh"] or 0) / 100))}
  crore.</p>
  <div class="tscroll"><table>
    <thead><tr><th>In Andhra Pradesh&rsquo;s budget, absent from myScheme</th>
      <th class="num">2026&ndash;27 (&#8377; cr)</th><th class="num">Score</th>
      <th>Why it scores as a scheme</th></tr></thead>
    <tbody>{rows_ap}</tbody>
  </table></div>
  <div class="warnbox">
    <b>One row per scheme, not per departmental share, and a floor again</b>
    Andhra Pradesh funds a scheme separately out of each social-category department, so NTR
    Bharosa Pension is six budget lines. They are added rather than listed six times,
    because the departments are distinct and the shares are of one provision. That is the
    opposite of the rule used across the six books, where the publications report
    overlapping slices and the largest is taken.
    <p style="margin:8px 0 0">Precision at the published bar is
    {cen2.get('precision', 0):.1%}, counted over {num(cen2.get('published'))} hand-labelled
    rows rather than estimated, with {num(cen2.get('not_schemes'))} errors named in the
    data. Recall is {v2.get('at_publish_threshold', {}).get('recall', 0):.0%}, lower than it
    should be for a reason that belongs to the state: no Andhra Pradesh book prints a
    purpose line, and 150 rows print no head of account either, so the classifier reads a
    name and nothing else. The largest thing this classifier rejects is
    {e((miss_ap or {}).get("name", ""))} at
    {inr(round(((miss_ap or {}).get("be_lakh") or 0) / 100))} crore, on a score of
    {(miss_ap or {}).get("score", 0)}.</p>
  </div>
</section>"""

    # Funded, monitored, and never announced. The strongest thing the union registry
    # says: these are named as schemes by at least two government sources and carry a
    # Budget allocation, and the government's own citizen-facing portal does not list
    # them at all.
    unlisted_section = ""
    if reg and cls:
        unlisted_rows = "".join(
            f'<tr><td>{e(u["name"])}</td>'
            f'<td class="num">{inr(u["be_cr"])}</td>'
            f'<td class="num">{u["score"]}</td>'
            f'<td class="muted" style="font-size:12px">'
            f'{e("; ".join(w for _, w in u.get("evidence", []) if not _.startswith("-"))[:96])}</td></tr>'
            for u in cls.get("unlisted_schemes", []))
        v = cls.get("validation", {})
        thr = cls.get("publish_threshold", 4)
        prec = next((r["precision"] for r in cls.get("threshold_sweep", [])
                     if r["threshold"] == thr), None)
        unlisted_section = f"""
<section class="sec">
  <h2>Funded, monitored, and never announced</h2>
  <div class="sec-note">Union registry across four government sources &middot;
    {num(reg.get('total_entries'))} entries against myScheme's
    {num(reg.get('myscheme_entries'))}</div>
  <p class="standfirst">A scheme the state funds but never tells citizens about is a
  harder finding than any missing field, and it is invisible to anything that
  treats myScheme&rsquo;s 4,772 as the universe.</p>
  <div class="tscroll"><table>
    <thead><tr><th>Funded and classified a scheme, absent from myScheme</th>
      <th class="num">BE 2026&ndash;27 (&#8377; cr)</th><th class="num">Score</th>
      <th>Why it scores as a scheme</th></tr></thead>
    <tbody>{unlisted_rows}</tbody>
  </table></div>
  <div class="warnbox">
    <b>How these were separated from budget heads, and how often that is wrong</b>
    Statement 4B mixes welfare schemes with infrastructure and accounting heads like
    &ldquo;Road Works&rdquo;, &ldquo;Rolling Stock&rdquo;, &ldquo;Manufacturing
    Suspense&rdquo;, none of which a citizen applies to. A classifier scores each line on
    independent signals: named in DBT Bharat&rsquo;s list (+3), Centrally Sponsored (+2),
    benefit words in the name (+2), has an outcome framework (+1), asset or accounting
    words (&minus;3), capital-heavy demand (&minus;2). Every line&rsquo;s arithmetic is
    published so the verdict can be rechecked.
    <p style="margin:8px 0 0">Validated against myScheme membership as ground truth:
    at the F1-optimal threshold of 2 precision is
    {v.get('precision', 0):.0%}; this table runs at the stricter threshold of {thr},
    where precision is {prec:.0%}. Naming a scheme as missing is an accusation,
    so it runs at the high-precision end. Recall is a floor and not a measurement: a
    line called a scheme that myScheme lacks may be the classifier being right and the
    portal being incomplete, which is the thing this page is about. Residual errors are
    visible above: &ldquo;Space Technology&rdquo; should not be here.</p>
  </div>
</section>"""

    return f"""
<div class="eyebrow">Route &middot; /divergence</div>
<h1 class="pagetitle">Three sources, one question, different answers</h1>
<p class="standfirst">How many welfare schemes does a given state have? Every central
government portal that answers this question answers it differently, and no portal
acknowledges the others exist.</p>

<div class="callout">
  <div class="big">Karnataka lists {num(ms.get("Karnataka"))} state schemes on one
  government portal and {num(ds.get("Karnataka"))} on another.</div>
  <div class="cite">myScheme state-level records tagged Karnataka &middot; DBT Bharat
  state dashboard scode=Mjk &middot; both from the same snapshot</div>
</div>

<p>Across {num(len([n for n in ms if ds.get(n)]))} states and union territories, DBT
Bharat names more schemes than myScheme in {num(higher)} of them, and myScheme names
more in the rest. Neither portal is a superset of the other, so a reader cannot pick one
and be done.</p>

<div class="tscroll"><table>
  <thead><tr><th>State or UT</th><th class="num">myScheme</th><th class="num">DBT Bharat</th>
    <th class="num">Gap</th><th>Direction</th></tr></thead>
  <tbody>{state_rows}</tbody>
  <tfoot><tr><td>All states and UTs</td><td class="num">{num(total_ms)}</td>
    <td class="num">{num(total_ds)}</td>
    <td class="num">{total_ds - total_ms:+,}</td><td class="muted"></td></tr></tfoot>
</table></div>

<div class="warnbox">
  <b>These are different units, so do not read the gap as error</b>
  {e((dbt or {}).get('caveat', ''))}
  Neither number is wrong. The finding is that both are published as
  &ldquo;schemes&rdquo; with nothing saying they count different things.
</div>

<section class="sec">
  <h2>The same portal, counted the same way, disagreeing with itself</h2>
  <div class="sec-note">myScheme state-level records only &middot; one snapshot</div>
  <p class="standfirst">A gap between two portals can always be explained away as
  different units. A gap <em>inside</em> one portal cannot. Every number below is
  myScheme&rsquo;s own, counted the same way on the same day.</p>
  <div class="tscroll"><table>
    <thead><tr><th>State</th><th class="num">Schemes</th><th>Compared with</th>
      <th class="num">Schemes</th><th class="num">Ratio</th></tr></thead>
    <tbody>{pair_rows}</tbody>
  </table></div>
  <p>Uttarakhand is a tenth of Uttar Pradesh by population. Goa is smaller than most
  Indian cities. These ratios are not descriptions of how much welfare a state
  administers, because no plausible policy difference runs an order of magnitude in that
  direction. They describe how much of it each state has loaded onto a central portal.</p>
  <div class="warnbox">
    <b>What this register can and cannot itemise</b>
    For central schemes the Union Budget supplies an independent list of names, so a
    scheme missing from myScheme can be named, and
    {num(len((cls or {}).get("unlisted_schemes", [])))} of them are named on this page.
    DBT Bharat publishes a per-state <em>count</em> and no state scheme list, so nothing
    central can itemise the shortfall of
    {num(sum(max(0, (ds.get(n) or 0) - v) for n, v in ms.items() if ds.get(n)))} schemes
    across the {num(higher)} states where DBT counts more.
    <p style="margin:8px 0 0">The way to name them is to read each state&rsquo;s own
    budget, which has to be done state by state: there is no common format and no
    guarantee a state publishes a readable one. Karnataka is done and is below. Andhra
    Pradesh is collected. Gujarat was attempted and its budget cannot be read by machine,
    which is a finding about Gujarat rather than a gap here. The survey of what each state
    publishes, including the failures, is in the repository.</p>
  </div>
</section>

{ka_section}
{ap_section}
{unlisted_section}
"""


# Only true connectives. "National", "Mission" and "Scheme" stay in, because real
# acronyms include them: MGNREGA is Mahatma Gandhi NATIONAL Rural Employment...
_ACR_SKIP = {"of", "and", "for", "the", "a", "an", "in", "to", "&"}


def acronym_keys(name):
    """Searchable acronym forms for a scheme name.

    Bracketed asides are stripped first, which is the whole trick for FAME: the official
    title is "...Manufacturing of (Hybrid and) Electric Vehicle", and keeping the bracket
    yields FAMHEV, which nobody types. Initials are then taken from the first few word
    offsets, because a leading "Scheme"/"National" often is not in the acronym, and every
    prefix of four or more characters is indexed, because these names are routinely
    shortened further than their own initials go.
    """
    n = re.sub(r"\(.*?\)", " ", name or "")
    n = re.sub(r"[^A-Za-z0-9\s]", " ", n).lower()
    words = [w for w in n.split() if w not in _ACR_SKIP and len(w) > 1]
    # Two offsets and short prefixes only. The full sweep (three offsets, prefixes to
    # ten characters) added 90 KB gzipped, a third of the page, for coverage nobody had
    # asked for; acronyms people actually type are four to six letters.
    keys = set()
    for start in (0, 1):
        ini = "".join(w[0] for w in words[start:])
        for k in range(4, min(len(ini), 6) + 1):
            keys.add(ini[:k])
    return keys


def where(entry):
    """Where a scheme applies, as a place rather than a tier.

    "State or UT" tells a reader nothing they wanted to know. The state is recorded on
    every myScheme entry and was being thrown away in favour of its level. Central
    schemes are nationwide except for 21 that name particular states, and 14 entries
    name several, so both cases are shown rather than flattened.
    """
    st = entry.get("state")
    names = [x for x in (st if isinstance(st, list) else [st] if st else []) if x]
    named = [x for x in names if x != "All"]
    lvl = entry.get("level_value")

    if lvl == "central":
        if not named:
            return "Central", "nationwide"
        head = named[0] if len(named) == 1 else f"{len(named)} states"
        return "Central", head
    if named:
        head = named[0] if len(named) == 1 else f"{named[0]} +{len(named)-1}"
        return head, "state or UT"
    # Two different silences, and they must not read the same. The Budget and DBT name a
    # scheme and its money and never where it applies, so those entries have nowhere to
    # get a state from. Three myScheme records carry no level either, which is a gap in
    # the portal rather than an absence of a record, and saying "no myScheme record"
    # about them would have been false.
    if entry.get("checks"):
        return entry.get("level") or "not stated", "not recorded on myScheme"
    return "not stated", "no myScheme record"


def where_full(entry):
    """Every state named, for the scheme page where there is room to list them."""
    st = entry.get("state")
    names = [x for x in (st if isinstance(st, list) else [st] if st else []) if x]
    named = [x for x in names if x != "All"]
    if not named:
        return "Nationwide" if entry.get("level_value") == "central" else ""
    return ", ".join(named)


SOURCE_LABEL = {"myscheme": "myScheme", "budget": "Union Budget",
                "outcome": "Outcome Budget", "dbt": "DBT Bharat"}


def slug_for(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:80] or "unnamed"


def unify(checks, registry, classification):
    """One row per scheme across every source, not one per myScheme record.

    A scheme present only in the Budget or the DBT list still exists; treating myScheme
    as the universe was the register mirroring a portal rather than describing a country.
    Entries with no myScheme record carry no documentation checks, and must not be shown
    as 0 of 9 — that reads as a verdict on the scheme when it is a statement about which
    portal lists it.
    """
    by_slug = {c["slug"]: c for c in (checks or {}).get("schemes", [])}
    cls = {c["name"]: c for c in (classification or {}).get("all_lines", [])}
    out, used = [], set()
    for en in (registry or {}).get("entries", []):
        srcs = en.get("sources", {})
        ms = srcs.get("myscheme")
        base = by_slug.get((ms or {}).get("slug")) if ms else None
        bud = srcs.get("budget") or {}
        verdict = (cls.get(bud.get("name")) or {}).get("verdict")
        # Slugs must be unique or one page silently overwrites another. Collisions are
        # rare and usually mean a missed merge, so the suffix is a visible marker.
        sl = base["slug"] if base else slug_for(en["name"])
        if sl in used:
            i = 2
            while f"{sl}-{i}" in used:
                i += 1
            sl = f"{sl}-{i}"
        used.add(sl)
        out.append({
            "name": en["name"],
            "slug": sl,
            "on_myscheme": bool(base),
            "checks": base,
            "sources": sorted(srcs.keys()),
            "level": (base or {}).get("level") or ((ms or {}).get("level")),
            "org": (base or {}).get("org"),
            "level_value": (base or {}).get("level_value"),
            "state": (base or {}).get("state"),
            "audience": (base or {}).get("audience"),
            "beneficiaries": (base or {}).get("beneficiaries") or [],
            "be_cr": bud.get("be_cr"),
            "demand_no": bud.get("demand_no"),
            "statement": bud.get("statement"),
            "classified": verdict,
            "detail": {k: v for k, v in srcs.items()},
        })
    return out


def pill_group(gid, label, options):
    """A single-choice filter as pills.

    Pills rather than a <select> wherever the axis has a handful of values: the options
    are the information — how many schemes each source lists, how many are badly
    documented — and a closed dropdown hides exactly that. Only the
    ministry/department filter stays a select, because 386 options is a list, not a set
    of choices.
    """
    parts = []
    for i, opt in enumerate(options):
        v, lab, n = opt[0], opt[1], opt[-1]
        short = opt[2] if len(opt) == 4 else lab
        on = " on" if i == 0 else ""
        pressed = "true" if i == 0 else "false"
        # "All" always selects everything, and the total is already in the count beside
        # the search box. Repeating it on four pills is width spent saying nothing.
        count = f'<span class="pn">{n:,}</span>' if n is not None and v != "" else ""
        text = (f'<span class="lg">{e(lab)}</span><span class="sm">{e(short)}</span>'
                if short != lab else e(lab))
        parts.append(f'<button type="button" class="pill{on}" data-g="{gid}" '
                     f'data-v="{e(v)}" aria-pressed="{pressed}">{text}{count}</button>')
    btns = "".join(parts)
    # The buttons get their own wrapper so the label can sit on a line of its own when
    # the row scrolls. It used to be position:sticky inside the scroller, which put it
    # on top of the pills as they slid underneath it.
    return (f'<div class="pillgroup" role="group" aria-label="{e(label)}">'
            f'<span class="plabel">{e(label)}</span>'
            f'<div class="pillrow">{btns}</div></div>')


def index_section(entries):
    orgs = {}
    for e_ in entries:
        o = e_.get("org")
        if o:
            k = orgs.setdefault(o, {"n": 0, "kind": "ministry" if str(o).lower().startswith(("ministry", "m/o")) else "department"})
            k["n"] += 1
    order = sorted(orgs.items(), key=lambda kv: (-kv[1]["n"], kv[0]))
    org_ix = {name: i for i, (name, _) in enumerate(order)}

    # A combobox, not a select. 386 options is too many to scroll and too many to know
    # by heart, so it has to be both browsable and searchable: <datalist> shows the whole
    # list on focus like a dropdown, narrows as you type, and typing a partial word that
    # matches no option still filters the table by substring. Native, so it keeps
    # keyboard and screen-reader behaviour rather than reimplementing it.
    org_options = "".join(
        f'<option value="{e(nm)}">{e("central ministry" if v["kind"] == "ministry" else "state / UT department")} &middot; {v["n"]:,} schemes</option>'
        for nm, v in order)
    org_select = (
        '<input id="org" list="orglist" autocomplete="off" '
        'placeholder="Any ministry or department: type to filter, or browse" '
        'aria-label="Filter by ministry or department">'
        f'<datalist id="orglist">{org_options}</datalist>'
        '<button type="button" id="orgclear" class="tbtn" hidden>clear</button>')

    st = {}
    for e_ in entries:
        v = e_.get("state")
        for x in (v if isinstance(v, list) else [v] if v else []):
            st[x] = st.get(x, 0) + 1
    # Alphabetical, with the nationwide bucket pinned last because it is not a state.
    #
    # This list was ordered by descending scheme count, which was wrong three times over.
    # A reader arrives knowing which state they want, so frequency order makes them read
    # 31 entries to reach Telangana. Ties had no name tie-break, so Assam and Kerala at 87
    # each, and Jammu and Kashmir and Uttar Pradesh at 47, fell in whatever order the
    # counting dict happened to hold, the same latent non-determinism that made the union
    # registry return a different answer on every run.
    #
    # The third reason is the real one. Putting Gujarat at the top asserts that Gujarat
    # has the most schemes. It has the most myScheme RECORDS, and /divergence exists to
    # argue that this is an artefact of what each state has loaded onto a central portal
    # rather than a fact about the state: Gujarat lists 641 and Karnataka 56, which no
    # policy difference explains. The control was quietly making the claim the rest of the
    # site spends a page disproving. The counts stay in the labels, where they are a
    # figure the reader can weigh, instead of an unlabelled ranking.
    #
    # "All" is myScheme's own label for a nationwide scheme, not a state, so it is named
    # plainly here to stop it reading as "no filter".
    state_select = (
        '<select id="st" aria-label="Filter by state or UT">'
        '<option value="">Any state or UT</option>'
        + "".join(f'<option value="{e(k.lower())}">'
                  f'{e("Nationwide" if k == "All" else k)} ({n:,})</option>'
                  for k, n in sorted(st.items(), key=lambda kv: (kv[0] == "All", kv[0])))
        + '</select>')

    lv = {}
    for e_ in entries:
        v = e_.get("level_value")
        if v:
            lv[v] = lv.get(v, 0) + 1
    LEVEL_LABEL = {"central": "Central", "state": "State or UT"}
    LEVEL_SHORT = {"central": "Central", "state": "State"}
    level_pills = pill_group("lvl", "Level",
                             [("", "All", None)]
                             + [(k, LEVEL_LABEL.get(k, k), LEVEL_SHORT.get(k, k), n)
                                for k, n in sorted(lv.items(), key=lambda kv: -kv[1])])

    src_counts = {}
    for e_ in entries:
        for k in e_["sources"]:
            src_counts[k] = src_counts.get(k, 0) + 1
    not_ms = sum(1 for e_ in entries if not e_["on_myscheme"])
    SRC_SHORT = {"myscheme": "myScheme", "budget": "Budget", "dbt": "DBT",
                 "outcome": "Outcome"}
    src_pills = pill_group(
        "src", "Listed by",
        [("", "All", None)]
        + [(k, SOURCE_LABEL[k], SRC_SHORT[k], src_counts[k])
           for k in ("myscheme", "budget", "dbt", "outcome") if k in src_counts]
        + [("!myscheme", "Not on myScheme", "Not listed", not_ms)])

    AUD = {"person": "People and families", "institution": "Firms and institutions",
           "mixed": "Both", "unstated": "Not stated"}
    aud = {}
    for e_ in entries:
        a = e_.get("audience")
        if a:
            aud[a] = aud.get(a, 0) + 1
    AUD_SHORT = {"person": "People", "institution": "Firms", "mixed": "Both",
                 "unstated": "Unstated"}
    aud_pills = pill_group(
        "aud", "Who it is for",
        [("", "All", None)]
        + [(k, AUD.get(k, k), AUD_SHORT.get(k, k), aud[k])
           for k in ("person", "institution", "mixed", "unstated") if k in aud])

    # Cuts that mean something, not "N or fewer" for every N. Measured: no scheme scores
    # below 2 or above 9, and the mass sits at 5-7, so most of the old dropdown's
    # eleven options selected either everything or nothing.
    def le(nmax):
        return sum(1 for x in entries
                   if x["checks"] and x["checks"]["passed"] <= nmax)
    doc_pills = pill_group(
        "doc", "Documentation",
        [("", "All", None),
         ("le4", "4 or fewer passed", "4 or fewer", le(4)),
         ("le5", "5 or fewer", "5 or fewer", le(5)),
         ("le6", "6 or fewer", "6 or fewer", le(6)),
         ("ge8", "8 or more", "8 or more",
          sum(1 for x in entries if x["checks"] and x["checks"]["passed"] >= 8)),
         ("none", "No record to check", "No record",
          sum(1 for x in entries if not x["checks"]))])

    # Initial rail values, rendered server-side. The rail used to ship "..." for every
    # figure and only fill in when a filter was touched, so the first thing a reader saw
    # was a panel of blanks. It is also what a reader without JS sees, and those numbers
    # are true for the unfiltered page.
    # Round per row, exactly as data-b does, so the server figure and the one the
    # browser recomputes on load are identical and the number does not visibly jump.
    r0_money = sum(round(x["be_cr"]) for x in entries
                   if isinstance(x.get("be_cr"), (int, float)))
    r0_scores = sorted(x["checks"]["passed"] for x in entries if x["checks"])
    r0_med = r0_scores[len(r0_scores) // 2] if r0_scores else None
    r0_src = {k: sum(1 for x in entries if k in x["sources"])
              for k in ("myscheme", "budget", "dbt", "outcome")}
    r0 = {
        "shown": f"{len(entries):,}",
        "noms": f"{len(entries) - r0_src['myscheme']:,}",
        "med": f"{r0_med} of 9" if r0_med is not None else "...",
        "money": f"&#8377;{inr(r0_money)} cr" if r0_money else "...",
        "sms": f"{r0_src['myscheme']:,}", "sbu": f"{r0_src['budget']:,}",
        "sdb": f"{r0_src['dbt']:,}", "soc": f"{r0_src['outcome']:,}",
    }

    rows = ""
    for e_ in entries:
        slug = e_["slug"]
        c = e_["checks"]
        short = (c or {}).get("short") or ""
        hay = re.sub(r"[^a-z0-9]+", " ",
                     " ".join(x for x in (e_["name"], short, slug) if x).lower()).strip()
        name_n = re.sub(r"[^a-z0-9]+", " ", (e_["name"] or "").lower()).strip()
        sq = {re.sub(r"[^a-z0-9]", "", x.lower())
              for x in ([short, slug] + ([e_["name"]] if len(name_n) <= 30 else [])) if x}
        sq |= acronym_keys(e_["name"])
        if c and c.get("brief"):
            sq |= set(keywords(c["brief"], e_["name"]))
        sq = {x for x in sq if len(x) > 2 and x not in hay.split()}
        xattr = f' data-x="{e(" ".join(sorted(sq)))}"' if sq else ""
        acr = f'<span class="acr">{e(short)}</span>' if short and short != e_["name"] else ""
        badges = "".join(f'<span class="src {k}">{e(SOURCE_LABEL[k])}</span>'
                         for k in e_["sources"])
        # Which checks failed lives on the scheme page, where each one has room to say
        # why. Three abbreviated codes in a narrow cell told a reader less than the count
        # already does, and cost the scheme name a seventh of the table.
        score = (f'<b>{c["passed"]}</b>/{c["total"]}' if c
                 else '<span class="nil">...</span>')
        # Allocation, blank where none is joined. Showing the gap is the point: a reader
        # who knows a figure exists can then tell us where it is.
        alloc = (f'&#8377;{inr(e_["be_cr"])}' if isinstance(e_.get("be_cr"), (int, float))
                 else '<span class="nil">...</span>')
        w_head, w_sub = where(e_)
        where_cell = (f'<td>{e(w_head)}'
                      + (f'<span class="sub2">{e(w_sub)}</span>' if w_sub else "")
                      + '</td>')
        rows += (f'<tr{xattr} data-p="{(c or {}).get("passed", -1)}" '
                 f'data-o="{e((e_.get("org") or "").lower())}" '
                 f'data-l="{e(e_.get("level_value") or "")}" '
                 f'data-st="{e(" ".join(x.lower() for x in ((e_.get("state") if isinstance(e_.get("state"), list) else [e_.get("state")]) if e_.get("state") else [])))}" '
                 f'data-a="{e(e_.get("audience") or "")}" '
                 f'data-s="{e(" ".join(e_["sources"]))}"'
                 + (f' data-b="{e_["be_cr"]:.0f}"' if isinstance(e_.get("be_cr"), (int, float)) else "")
                 + '>'
                 f'<td><a href="scheme/{e(slug)}.html">{e(e_["name"])}</a>{acr}</td>'
                 f'<td>{badges}</td>'
                 + where_cell
                 + f'<td class="muted">{e(e_.get("org") or "")}</td>'
                 f'<td class="num alloc">{alloc}</td>'
                 f'<td class="num">{score}</td></tr>')

    n = len(entries)
    if not n:
        return ('<section class="sec"><h2>Every scheme</h2><div class="empty">'
                '<span class="big">...</span><b>No registry built yet.</b><br>'
                'Run parse/registry.py.</div></section>')
    return f"""
<section class="sec schemes" id="schemes">
<div class="sec-note">{n:,} across four sources: myScheme, the Union Budget,
  the Outcome Budget and DBT Bharat. Open a scheme to see which checks it fails and why.
  Entries with no myScheme record have nothing to check, which is itself the finding.</div>
<div class="filters">
  <input id="q" type="search" placeholder="Search name or acronym, e.g. pm kisan or mgnrega&hellip;"
    aria-label="Search schemes by name, acronym or slug">
  {state_select}
  {org_select}
  <span class="count" id="count">{n:,} schemes</span>
</div>
<div class="pills">
  {level_pills}
  {aud_pills}
  {src_pills}
  {doc_pills}
</div>
<div class="workspace">
<div class="wmain">
<div class="tscroll"><table id="tbl">
  <thead><tr><th class="sortable" data-k="n">Scheme</th><th>Listed by</th><th>Where it applies</th>
    <th>Ministry / department</th>
    <th class="num sortable" data-k="b">Allocation</th>
    <th class="num sortable" data-k="p">Passed</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
</div>
<aside class="wrail" aria-label="Statistics for the current selection">
  <div class="railhd">This selection</div>
  <div class="railbig"><span id="rShown">{n:,}</span><span class="railof">of {n:,}</span></div>
  <div class="railrow"><span><span class="lg">Not on myScheme</span><span class="sm">off-portal</span></span><b id="rNoMs">{r0["noms"]}</b></div>
  <div class="railrow"><span><span class="lg">Median checks passed</span><span class="sm">median</span></span><b id="rMed">{r0["med"]}</b></div>
  <div class="railrow"><span><span class="lg">Allocation known</span><span class="sm">allocated</span></span><b id="rMoney">{r0["money"]}</b></div>
  <div class="railgroup">
    <div class="railhd" style="margin-top:16px">Listed by</div>
    <div class="railrow"><span>myScheme</span><b id="rSms">{r0["sms"]}</b></div>
    <div class="railrow"><span>Union Budget</span><b id="rSbu">{r0["sbu"]}</b></div>
    <div class="railrow"><span>DBT Bharat</span><b id="rSdb">{r0["sdb"]}</b></div>
    <div class="railrow"><span>Outcome Budget</span><b id="rSoc">{r0["soc"]}</b></div>
  </div>
  <a class="railtop" id="toTop" href="#schemes" hidden>&uarr; Back to top</a>
  <a class="railtop" href="{ISSUE_URL}?template=missing-figure.yml"
     target="_blank" rel="noopener">Report a missing or wrong figure</a>
  <div class="railnote">Every figure here follows the filters. Allocation is the
    Budget line for the visible schemes where one is joined; most schemes have none
    published anywhere.</div>
</aside>
</div>
<div class="empty" id="nomatch" hidden>
  <span class="big">...</span>
  <b>Nothing matches those filters.</b>
  <div id="whyempty" style="margin:10px 0 6px"></div>
  <span class="muted">Search ignores punctuation, so <code>pm kisan</code> and
  <code>PM-KISAN</code> are the same.</span>
</div>
<script>
(function(){{
  var tb=document.querySelector('#tbl tbody'),rows=[].slice.call(tb.rows),
      empty=document.getElementById('nomatch'),
      q=document.getElementById('q'),og=document.getElementById('org'),
      c=document.getElementById('count'),asc=false,
      state={{lvl:'',src:'',doc:'',aud:''}};
  var norm=function(v){{return v.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}};
  rows.forEach(function(r){{ r._h = norm(r.cells[0].textContent+' '+(r.dataset.x||'')); }});
  function terms(v){{ return norm(v).split(' ').filter(Boolean); }}

  function docOk(r,v){{
    if(!v) return true;
    var p=+r.dataset.p;              // -1 means no myScheme record, nothing to check
    if(v==='none') return p<0;
    if(p<0) return false;
    if(v==='ge8') return p>=8;
    return p<=+v.slice(2);
  }}
  function apply(){{
    var ts=terms(q.value),o=og.value.trim().toLowerCase(),
        stv=document.getElementById('st').value,shown=0;
    document.getElementById('orgclear').hidden = !o;
    rows.forEach(function(r){{
      var ok=(!o||r.dataset.o.indexOf(o)>-1)
             &&(!stv||(r.dataset.st||'').indexOf(stv)>-1)
             &&(!state.lvl||r.dataset.l===state.lvl)
             &&(!state.aud||r.dataset.a===state.aud)
             &&docOk(r,state.doc);
      if(ok&&state.src){{
        var have=(r.dataset.s||'').split(' ');
        ok = state.src.charAt(0)==='!' ? have.indexOf(state.src.slice(1))<0
                                       : have.indexOf(state.src)>-1;
      }}
      if(ok) for(var i=0;i<ts.length;i++) if(r._h.indexOf(ts[i])<0){{ok=false;break;}}
      r.hidden=!ok; if(ok)shown++;
    }});
    c.textContent=shown.toLocaleString()+' of {n:,} schemes';
    empty.hidden = shown>0;
    rail(shown);
    recount(ts,o);
    if(!shown) explain(ts,o);
    keepInView();
  }}

  // Filtering 5,395 rows down to 50 collapses the page, and the browser clamps the
  // scroll position to the new maximum. Choosing a state from a few screens down
  // therefore dumped the reader at the footer, looking at the source list, with the
  // results they had just asked for somewhere above them. Nothing scrolled: the page
  // shrank underneath them, which is worse, because there is no movement to explain it.
  //
  // Only correct it when the reader is actually past the results, so this never fires
  // while they are reading rows, and never on every keystroke in the search box, which
  // sits in the sticky bar and is usable from anywhere down the page.
  function keepInView(){{
    var tb=document.getElementById('schemes');
    if(!tb) return;
    var last=null,vis=rows.filter(function(r){{return !r.hidden;}});
    if(vis.length) last=vis[vis.length-1];
    var bottom=(last||tb).getBoundingClientRect().bottom;
    if(bottom>0) return;                 // still something to look at on screen
    var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    tb.scrollIntoView({{block:'start',behavior:reduce?'auto':'smooth'}});
  }}

  function rail(shown){{
    var vis=rows.filter(function(r){{return !r.hidden;}});
    var src={{myscheme:0,budget:0,dbt:0,outcome:0}},money=0,scores=[];
    vis.forEach(function(r){{
      (r.dataset.s||'').split(' ').forEach(function(k){{ if(k in src) src[k]++; }});
      if(r.dataset.b) money+=+r.dataset.b;
      if(+r.dataset.p>=0) scores.push(+r.dataset.p);
    }});
    scores.sort(function(a,b){{return a-b;}});
    var med = scores.length ? scores[Math.floor(scores.length/2)] : null;
    function set(id,v){{ document.getElementById(id).textContent=v; }}
    set('rShown',shown.toLocaleString());
    set('rNoMs',(shown-src.myscheme).toLocaleString());
    set('rMed', med===null ? '...' : med+' of 9');
    set('rMoney', money ? '₹'+Math.round(money).toLocaleString('en-IN')+' cr' : '—');
    set('rSms',src.myscheme.toLocaleString()); set('rSbu',src.budget.toLocaleString());
    set('rSdb',src.dbt.toLocaleString()); set('rSoc',src.outcome.toLocaleString());
  }}

  // Every pill shows how many rows it would select GIVEN the other filters, so a
  // combination that cannot match reads 0 before it is clicked rather than after.
  // "Central" plus a state department is empty by construction — central schemes carry
  // ministries, state schemes carry departments — and the old static counts hid that.
  function passes(r,ts,o,skip){{
    if(o && skip!=='org' && r.dataset.o.indexOf(o)<0) return false;
    var sv2=document.getElementById('st').value;
    if(sv2 && skip!=='st' && (r.dataset.st||'').indexOf(sv2)<0) return false;
    if(skip!=='lvl' && state.lvl && r.dataset.l!==state.lvl) return false;
    if(skip!=='aud' && state.aud && r.dataset.a!==state.aud) return false;
    if(skip!=='doc' && !docOk(r,state.doc)) return false;
    if(skip!=='src' && state.src){{
      var have=(r.dataset.s||'').split(' ');
      if(state.src.charAt(0)==='!' ? have.indexOf(state.src.slice(1))>-1
                                   : have.indexOf(state.src)<0) return false;
    }}
    for(var i=0;i<ts.length;i++) if(r._h.indexOf(ts[i])<0) return false;
    return true;
  }}
  function matchOne(r,g,v){{
    if(g==='lvl') return !v||r.dataset.l===v;
    if(g==='aud') return !v||r.dataset.a===v;
    if(g==='doc') return docOk(r,v);
    if(!v) return true;
    var have=(r.dataset.s||'').split(' ');
    return v.charAt(0)==='!' ? have.indexOf(v.slice(1))<0 : have.indexOf(v)>-1;
  }}
  function recount(ts,o){{
    document.querySelectorAll('.pill').forEach(function(b){{
      var g=b.dataset.g,v=b.dataset.v,k=0;
      for(var i=0;i<rows.length;i++){{
        var r=rows[i];
        if(passes(r,ts,o,g)&&matchOne(r,g,v)) k++;
      }}
      var pn=b.querySelector('.pn');
      if(pn) pn.textContent=k.toLocaleString();
      b.classList.toggle('zero',k===0);
    }});
  }}

  // When nothing matches, name the filter that emptied it rather than leaving the
  // reader to guess which of five controls is responsible.
  function explain(ts,o){{
    var bits=[],tries=[];
    if(o) tries.push(['org','ministry or department “'+og.value.trim()+'”']);
    var stEl=document.getElementById('st');
    if(stEl.value) tries.push(['st','state '+stEl.options[stEl.selectedIndex].text]);
    if(state.lvl) tries.push(['lvl','level']);
    if(state.aud) tries.push(['aud','who it is for']);
    if(state.src) tries.push(['src','listed by']);
    if(state.doc) tries.push(['doc','documentation']);
    if(ts.length) tries.push(['q','the search “'+q.value.trim()+'”']);
    tries.forEach(function(t){{
      var n=0;
      for(var i=0;i<rows.length;i++){{
        var r=rows[i];
        var ok = t[0]==='q' ? passes(r,[],o,null) : passes(r,ts,t[0]==='org'?'':o,t[0]);
        if(ok) n++;
      }}
      if(n>0) bits.push('drop '+t[1]+' and '+n.toLocaleString()+' match');
    }});
    var el=document.getElementById('whyempty');
    el.innerHTML = bits.length
      ? 'Try one of these: '+bits.join('; ')+'.'
      : 'No single filter explains it. Several are narrowing at once.';
  }}

  document.querySelectorAll('.pill').forEach(function(b){{
    b.addEventListener('click',function(){{
      var g=b.dataset.g;
      document.querySelectorAll('.pill[data-g="'+g+'"]').forEach(function(o){{
        var on = o===b;
        o.classList.toggle('on',on);
        o.setAttribute('aria-pressed',on?'true':'false');
      }});
      state[g]=b.dataset.v; apply();
    }});
  }});
  q.addEventListener('input',apply);
  og.addEventListener('input',apply); og.addEventListener('change',apply);
  document.getElementById('st').addEventListener('change',apply);
  document.getElementById('orgclear').addEventListener('click',function(){{
    og.value=''; apply(); og.focus();
  }});
  var sortedBy=null;
  document.querySelectorAll('th.sortable').forEach(function(th){{
    th.setAttribute('aria-sort','none');
    th.addEventListener('click',function(){{
      var k=th.dataset.k;
      // Clicking a new column starts ascending rather than inheriting the last
      // column's direction, which is what a reader expects and what the arrow claims.
      asc = (sortedBy===k) ? !asc : true;
      sortedBy=k;
      rows.sort(function(a,b){{
        var g=function(r){{return k==='p'?+r.dataset.p
                              :k==='b'?(r.dataset.b?+r.dataset.b:-Infinity)
                              :r._h;}};
        var x=g(a), y=g(b);
        return (x<y?-1:x>y?1:0)*(asc?1:-1);
      }});
      rows.forEach(function(r){{tb.appendChild(r);}});
      document.querySelectorAll('th.sortable').forEach(function(o){{
        var on = o===th;
        o.classList.toggle('sorted',on);
        o.classList.toggle('desc',on&&!asc);
        o.setAttribute('aria-sort', on ? (asc?'ascending':'descending') : 'none');
      }});
    }});
  }});
  // Publish the sticky filter bar's real height so the table header can sit exactly
  // beneath it at any width, including when the controls wrap.
  var bar=document.querySelector('.filters');
  function measure(){{
    document.documentElement.style.setProperty(
      '--filters-h', Math.ceil(bar.getBoundingClientRect().height)+'px');
  }}
  if(bar){{
    measure();
    if(window.ResizeObserver) new ResizeObserver(measure).observe(bar);
    else window.addEventListener('resize',measure);
  }}

  // Back to top. Hidden until there is something to go back up from, and it returns
  // focus to the search box, because wanting the top of a 5,438-row table almost always
  // means wanting to search again.
  var top=document.getElementById('toTop');
  if(top){{
    var onScroll=function(){{ top.hidden = window.scrollY < 500; }};
    window.addEventListener('scroll',onScroll,{{passive:true}});
    onScroll();
    top.addEventListener('click',function(ev){{
      ev.preventDefault();
      var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({{top:0,behavior:reduce?'auto':'smooth'}});
      q.focus({{preventScroll:true}});
    }});
  }}

  apply();          // rail and pill counts must be live from the first paint
}})();
</script>
</section>
"""


def page_unlisted(en, status):
    """A scheme other government sources name and myScheme does not list.

    There are no documentation checks here because there is no myScheme record to check.
    That absence is the subject of the page, and it is stated as a fact about the portal
    rather than rendered as a failing score against the scheme.
    """
    rows = ""
    for k in ("budget", "outcome", "dbt"):
        d = en["detail"].get(k)
        if not d:
            continue
        bits = []
        if d.get("be_cr") is not None:
            bits.append(f'<b>&#8377;{d["be_cr"]:,.2f} cr</b> for {e(d.get("cycle") or "")}')
        if d.get("demand_no"):
            bits.append(f'Demand No. {e(d["demand_no"])}')
        if d.get("statement"):
            bits.append(f'Statement {e(d["statement"][-2:].upper())}')
        if d.get("outlay_cr") is not None:
            bits.append(f'outlay &#8377;{inr(d["outlay_cr"])} cr')
        if d.get("targets"):
            bits.append(f'{d["targets"]} published targets')
        if d.get("page"):
            bits.append(f'p.{d["page"]}')
        if d.get("classification"):
            bits.append(e(d["classification"]))
        if d.get("list"):
            bits.append(f'{e(d["list"])} list')
        why = d.get("merge_reason")
        rows += (f'<tr><td>{e(SOURCE_LABEL[k])}</td>'
                 f'<td>{" &middot; ".join(bits) or "named"}'
                 + (f'<div class="muted" style="margin-top:3px">listed there as '
                    f'&ldquo;{e(d.get("name") or "")}&rdquo;'
                    + (f' &middot; matched: {e(why)}' if why else "") + '</div>'
                    if d.get("name") and d.get("name") != en["name"] else "")
                 + '</td></tr>')

    chips = "".join(f'<span class="chip">{e(SOURCE_LABEL[k])}</span>' for k in en["sources"])
    chips += '<span class="chip flag">Not on myScheme</span>'
    verdict = en.get("classified")
    return f"""
<div class="eyebrow">Route &middot; /scheme/{e(en["slug"])}</div>
<div class="shead">
  <h1>{e(en["name"])}</h1>
  <div class="full">Named by {len(en["sources"])} government source(s), and not listed
    on myScheme</div>
  <div class="chips">{chips}</div>
</div>

<div class="warnbox">
  <b>No documentation checks for this scheme</b>
  The nine checks measure what myScheme publishes about a scheme. There is no myScheme
  record here to measure, so this page shows none. A score of nought would read
  as a verdict on the scheme when it is a fact about the portal.
  {"This line is classified as a citizen-facing scheme rather than a budget head; the arithmetic is on /divergence." if verdict == "scheme" else "This line was classified as a budget head rather than a citizen-facing scheme, so its absence from a scheme portal may be correct."}
</div>

<section class="sec">
  <h2>What each source says</h2>
  <div class="sec-note">Every figure below is from a government document, named and dated</div>
  <div class="tscroll"><table class="prov">{rows}</table></div>
</section>

<section class="sec">
  <h2>What myScheme says</h2>
  <div class="tscroll"><table class="prov">
    <tr><td>myScheme record</td>
      <td><span class="nil">...</span> <span class="muted">no entry found in the
        {e(status.get('snapshot') or '')} snapshot, under a generous name match</span></td>
      <td class="ts">...</td></tr>
  </table></div>
</section>
"""


def page_changes(ch):
    """What differs between two snapshots of the same source.

    Never the repository's own history. This page previously rendered `git log` over
    data/, so with one snapshot collected it listed commit subjects from this project
    under the heading "What the government changed without saying". A page that points
    at government has to be evidenced by government bytes.
    """
    ch = ch or {}
    if not ch.get("comparable"):
        held = ch.get("snapshots_held", 0)
        return f"""
<div class="eyebrow">Route &middot; /changes</div>
<h1 class="pagetitle">What the government changed without saying</h1>
<p class="standfirst">A diff between consecutive monthly snapshots. Nothing here is an
opinion: each row is two archived payloads and the field that differs between them.</p>
<div class="empty">
  <span class="big">...</span>
  <b>{held} snapshot held.</b><br>
  A change feed needs two, and it cannot be back-filled. Wayback does not capture API
  responses and myScheme versions nothing, so the only record of what it said last month
  is the one collected last month. That is why collection started before this site did.
</div>"""

    def rows_for(items, kind):
        out = ""
        for it in items:
            deltas = "".join(
                f'<div class="delta"><span class="dfield">{e(d["field"])}</span>'
                f'<span class="dold">{e(d["from"]) if d["from"] else "not set"}</span>'
                f'<span class="dnew">{e(d["to"]) if d["to"] else "not set"}</span></div>'
                for d in it.get("changes", []))
            out += (f'<div class="ch"><div class="ctype {kind}">{e(kind)}</div>'
                    f'<div><a class="chname" href="scheme/{e(it["slug"])}.html">'
                    f'{e(it.get("name") or it["slug"])}</a>{deltas}</div></div>')
        return out

    byf = "".join(f'<tr><td>{e(k)}</td><td class="num">{v:,}</td></tr>'
                  for k, v in (ch.get("by_field") or {}).items())
    return f"""
<div class="eyebrow">Route &middot; /changes</div>
<h1 class="pagetitle">What the government changed without saying</h1>
<p class="standfirst">{e(ch["older"])} to {e(ch["newer"])}. Each row is two archived
payloads and the field that differs between them, so nothing here is an opinion.</p>

<div class="census">
  <div class="cell"><div class="k">Schemes added</div><div class="v">{ch["added_total"]:,}</div>
    <div class="n">not in the previous snapshot</div></div>
  <div class="cell"><div class="k">Schemes removed</div><div class="v">{ch["removed_total"]:,}</div>
    <div class="n">present before, gone now</div></div>
  <div class="cell"><div class="k">Records edited</div><div class="v">{ch["changed_total"]:,}</div>
    <div class="n">same scheme, different field</div></div>
</div>

<section class="sec">
  <h2>Which fields moved</h2>
  <div class="tscroll"><table>
    <thead><tr><th>Field</th><th class="num">Records</th></tr></thead>
    <tbody>{byf or '<tr><td colspan="2" class="muted">none</td></tr>'}</tbody>
  </table></div>
</section>

<section class="sec">
  <h2>Every difference</h2>
  <div class="sec-note">Edited first, then added and removed</div>
  {rows_for(ch.get("changed", []), "edited")}
  {rows_for(ch.get("added", []), "added")}
  {rows_for(ch.get("removed", []), "removed")}
</section>

<div class="warnbox"><b>Why this page can be trusted more than the rest of the site</b>
A diff is not a judgment. Every row is derived from two archived payloads anyone can
re-fetch from this repository and compare. A snapshot that fails its completeness
assertion is archived but marked INCOMPLETE, and this page refuses to diff against it,
because one dropped page of results would otherwise appear here as dozens of schemes
being removed.</div>
"""


# A scheme's launch date exists: it is in the gazette notification or the government
# order that created it. So "no start date recorded" is a weak claim that sounds like the
# fact is unknowable. The real claim is narrower and much stronger: the portal a citizen
# actually visits does not tell them, even though the government can point at the
# notification and say it was published. These labels are about the portal.
CHECK_LABEL = {
    "eligibility_documented":     "Eligibility published here",
    "benefit_quantified":         "Benefit amount published here",
    "description_substantive":    "Description more than a name",
    "implementing_agency_named":  "Implementing agency published here",
    "application_path_published": "How to apply published here",
    "start_date_recorded":        "Start date published here",
    "end_date_recorded":          "End date published here",
    "stored_urls_well_formed":    "Stored links well-formed",
    "not_expired_while_listed":   "Not expired while still listed",
}


def page_scheme(s, status, enrich=None, entry=None):
    checks = "".join(
        f'<div class="chk"><span class="mark {"p" if c["ok"] else "f"}">'
        f'{"&#10003;" if c["ok"] else "&#10007;"}</span>'
        f'<div>{e(CHECK_LABEL.get(c["id"], c["id"].replace("_", " ").capitalize()))}'
        f'<span class="why">{e(c["detail"])}</span></div></div>'
        for c in s["checks"])
    segs = "".join(f'<span class="seg {"p" if c["ok"] else "f"}"></span>' for c in s["checks"])

    chips = ""
    # Where it applies, named. The level alone ("State/ UT") is the one fact a reader
    # already knows from having found the scheme; the state is the one they want.
    places = where_full(s)
    if places:
        chips += f'<span class="chip place">{e(places)}</span>'
    for bnf in (s.get("beneficiaries") or [])[:4]:
        chips += f'<span class="chip">{e(bnf)}</span>'
    if s.get("level"):
        chips += f'<span class="chip">{e(s["level"])}</span>'
    if s.get("type"):
        chips += f'<span class="chip">{e(s["type"])}</span>'
    if s.get("ministry"):
        chips += f'<span class="chip">{e(s["ministry"])}</span>'
    chips += (f'<span class="chip live">Open since {e(s["open_date"])}</span>'
              if s.get("open_date") else '<span class="chip flag">No start date</span>')

    bad = ""
    if s.get("bad_urls"):
        bad = '<div class="warnbox"><b>Malformed URL in a stored field</b>' + "".join(
            f'<div style="margin-top:6px"><code>{e(u["url"][:110])}</code><br>'
            f'<span class="muted">{e(u["field"])} field: {e(u["why"])}</span></div>'
            for u in s["bad_urls"][:4]) + "</div>"

    def prov(field, value, source):
        v = e(value) if value else '<span class="nil">...</span>'
        return f'<tr><td>{e(field)}</td><td>{v}</td><td class="ts">{e(source)}</td></tr>'

    snap = status.get("snapshot", "")
    rep_title = urllib.parse.quote(f"Missing or wrong: {s.get('name') or s['slug']}"[:90])

    # What the scheme actually is. The register was reporting how completely a record
    # was documented without ever showing the documentation, which made every page a
    # verdict with no subject.
    def block(title, body_md, note="", limit=6000):
        h = md(body_md, limit)
        if not h:
            return ""
        return (f'<section class="sec"><h2>{e(title)}</h2>'
                + (f'<div class="sec-note">{e(note)}</div>' if note else "")
                + f'<div class="prose">{h}</div></section>')

    about = "".join([
        block("What this is", s.get("brief")),
        block("In detail", s.get("detail_md")),
        block("Who qualifies", s.get("eligibility_md")),
        block("What you get", s.get("benefits_md")),
        block("Who is excluded", s.get("exclusions_md")),
    ])
    if about:
        about = ('<div class="sec-note" style="margin-top:34px">myScheme&rsquo;s own '
                 'wording. Where it is thin, that is the finding.</div>' + about)

    # Found elsewhere. Deliberately separate from the checks above and never counted in
    # them: this is what a *different* government document says, not what this portal
    # publishes. Showing both together is the point — it turns "the portal omits this"
    # from a shrug into evidence that the omission was avoidable.
    found_block = ""
    ob = (enrich or {}).get("outcome", {}).get(s["slug"])
    targets_html = ""
    if ob:
        def rows(items, kind):
            return "".join(
                f'<tr><td>{e(kind)} {e(i["ref"])}</td>'
                f'<td>{e(i["indicator"])}</td>'
                f'<td class="num"><b>{i["target"]:,.2f}</b></td></tr>'
                if isinstance(i.get("target"), (int, float)) else
                f'<tr><td>{e(kind)} {e(i["ref"])}</td><td>{e(i["indicator"])}</td>'
                f'<td class="num"><span class="nil">...</span></td></tr>'
                for i in items)
        body = rows(ob.get("outputs", []), "output") + rows(ob.get("outcomes", []), "outcome")
        targets_html = f"""
  <h3 style="font-size:17px;margin:26px 0 4px">What it promises to deliver this year</h3>
  <div class="sec-note">{e(ob.get('source') or '')} &middot; matched at
    {ob.get('match_score')} ({e(ob.get('confidence') or '')})</div>
  <div class="tscroll"><table>
    <thead><tr><th>Indicator</th><th>Measure</th><th class="num">Target {e(ob.get('cycle') or '')}</th></tr></thead>
    <tbody>{body}</tbody>
  </table></div>
  <div class="sec-note" style="margin-top:8px">Indicator wording is the first line of a
    wrapped cell in the source PDF; target values are complete. The framework carries
    targets and <b>no achieved-versus-promised column</b>, for this scheme or any
    other.</div>"""

    b = (enrich or {}).get("budget", {}).get(s["slug"])
    if b or ob:
        amt = (b or {}).get("be_next_year_cr")
        amt_s = (f"&#8377;{inr(amt)} cr" if isinstance(amt, (int, float))
                 else '<span class="nil">...</span>')
        money_row = f"""
    <tr><td>Budget allocation</td>
      <td><b>{amt_s}</b> for {e((b or {}).get('cycle') or '')}
        <div class="muted" style="margin-top:3px">{e((b or {}).get('classification') or '')}
          &middot; Demand No. {e((b or {}).get('demand_no'))}
          &middot; matched to budget line &ldquo;{e((b or {}).get('budget_line') or '')}&rdquo;
          at {(b or {}).get('match_score')} ({e((b or {}).get('confidence') or '')})</div></td>
      <td class="ts">{e((b or {}).get('source') or '')}</td></tr>""" if b else ""
        found_block = f"""
<section class="sec">
  <h2>Found elsewhere in government</h2>
  <div class="sec-note">Not published on myScheme &middot; carried from another
    government source, with the join score shown so it can be disputed</div>
  <div class="tscroll"><table class="prov">{money_row}</table></div>
  {targets_html}
  <div class="warnbox"><b>Why this is here and not above</b>
    myScheme publishes no budget figure for any scheme. This one comes from the Union
    Budget Expenditure Profile and is joined by name, so it is shown apart from the
    checks and never counted in them. A scheme&rsquo;s launch date, likewise, exists in
    its gazette notification whether or not the portal repeats it. The checks
    above ask only whether <em>this portal</em> tells a citizen, which is a different
    and narrower question.</div>
</section>"""

    return f"""
<div class="eyebrow">Route &middot; /scheme/{e(s["slug"])}</div>
<div class="shead">
  <h1>{e(s["short"] or s["name"])}</h1>
  <div class="full">{e(s["name"])}</div>
  <div class="chips">{chips}</div>
</div>

<div class="meter">
  <div class="meter-top">
    <div>
      <div class="lbl">Documentation completeness</div>
      <div class="score"><b>{s["passed"]}</b> of {s["total"]} checks passed</div>
      <div class="bar">{segs}</div>
    </div>
    <div class="lbl" style="text-align:right;line-height:1.7">
      Checks are about the record,<br>not about the scheme.
    </div>
  </div>
  <div class="checks">{checks}</div>
</div>
{bad}

{about}
{found_block}

<div class="report">
  <b>Something missing or wrong on this page?</b>
  This register only knows what four government sources publish. If you know where the
  real figure lives, a link to the notification or order is what lets us publish it.
  <a href="{ISSUE_URL}?template=missing-figure.yml&title={rep_title}"
     target="_blank" rel="noopener">Tell us on GitHub</a>
</div>

<section class="sec">
  <h2>Provenance</h2>
  <div class="sec-note">Every field above, and where it came from</div>
  <div class="tscroll"><table class="prov">
    {prov("schemeName", s["name"], f"myScheme &middot; {snap}")}
    {prov("schemeOpenDate", s.get("open_date"), f"myScheme &middot; {snap}" if s.get("open_date") else "not published at source")}
    {prov("schemeCloseDate", s.get("close_date"), f"myScheme &middot; {snap}" if s.get("close_date") else "not published at source")}
    {prov("nodalMinistryName", s.get("ministry"), f"myScheme &middot; {snap}")}
    {prov("dbtScheme", str(s.get("dbt")) if s.get("dbt") is not None else None, f"myScheme &middot; {snap}")}
    {prov("achievement data", None, "no source publishes this for any central scheme")}
  </table></div>
</section>
"""


# --------------------------------------------------------------------- git log

# --------------------------------------------------------------------- build

def build():
    status = load("status.json", {}) or {}
    shell.status = status
    census = load("data/myscheme/census.json", {})
    checks = load("data/checks.json", {})
    dbt = load("data/dbt/states.json", {})
    enrich = {"budget": (load("data/enrichment/budget.json", {}) or {}).get("schemes", {}),
              "outcome": (load("data/enrichment/outcome.json", {}) or {}).get("schemes", {})}

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "scheme"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "theme.css"), os.path.join(OUT, "theme.css"))

    def w(rel, s):
        with open(os.path.join(OUT, rel), "w", encoding="utf-8") as fh:
            fh.write(s)

    registry = load("data/registry.json", {})
    classification = load("data/classification.json", {})
    entries = unify(checks, registry, classification)
    w("index.html", shell(
        "The census and the argument", "/", page_index(census, checks, dbt, entries),
        desc=(f"{len(entries):,} Indian government schemes across four official sources, "
              "with what each source publishes and what it leaves out.")))
    w("divergence.html", shell(
        "Divergence", "/divergence",
        page_divergence(census, dbt, load("data/registry.json", {}),
                        load("data/classification.json", {}), entries=entries,
                        ka=load("data/karnataka/classification.json", {}),
                        ap=load("data/andhra/classification.json", {})),
        desc=("Karnataka runs 60 welfare schemes, or 501, depending which government "
              "portal you ask. Three official sources, counted side by side.")))
    w("changes.html", shell(
        "Changes", "/changes", page_changes(load("data/changes.json", {})),
        desc="What Indian government scheme records changed between monthly snapshots."))

    n = 0
    seen = set()
    for en in entries:
        if en["slug"] in seen:
            continue
        seen.add(en["slug"])
        c = en["checks"]
        title = (c or {}).get("short") or en["name"]
        body = (page_scheme(c, status, enrich, en) if c
                else page_unlisted(en, status))
        # The description is the scheme's own words where it has any, because that is
        # what a reader searching the scheme's name is looking for. Where there is no
        # myScheme record, say which sources do name it: that is the finding.
        if c and c.get("brief"):
            d = " ".join(c["brief"].split())
        elif c:
            d = (f"{en['name']}: {c['passed']} of {c['total']} documentation checks "
                 f"passed on myScheme.")
        else:
            d = (f"{en['name']} is named by "
                 f"{', '.join(SOURCE_LABEL[k] for k in en['sources'])} and is not "
                 f"listed on myScheme.")
        w(os.path.join("scheme", f"{en['slug']}.html"),
          shell(title, "/", body, depth=1, desc=d))
        n += 1

    # A sitemap because 5,438 pages are reachable only through a JS-filtered table, and
    # a crawler that does not run the filter will never see most of them.
    urls = ["", "divergence.html", "changes.html"] + [
        f"scheme/{en['slug']}.html" for en in entries]
    stamp = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            fh.write(f"<url><loc>{SITE_BASE}/{u}</loc>"
                     f"<lastmod>{stamp}</lastmod></url>\n")
        fh.write("</urlset>\n")
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\n"
                 f"Sitemap: {SITE_BASE}/sitemap.xml\n")

    return n


def audit_text(out_dir):
    """Reject em-dashes in anything a reader sees. En-dashes are fine.

    Checked at build time rather than trusted to discipline: page copy is written in a
    dozen f-strings across this file, and a house rule that is not enforced is a rule
    that comes back. Script and style bodies are excluded because they are not prose.
    """
    bad = []
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if not fn.endswith((".html", ".md")):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                t = fh.read()
            t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
            t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
            t = html.unescape(t)
            if "\u2014" in t:
                n = t.count("\u2014")
                snippet = t[max(0, t.index("\u2014") - 45): t.index("\u2014") + 45]
                bad.append((os.path.relpath(path, out_dir), n,
                            " ".join(snippet.split())))
    return bad


def main():
    ap = argparse.ArgumentParser(description="Build the static site into site/_out.")
    ap.parse_args()
    n = build()
    print(f"built site/_out: 4 pages + {n:,} scheme pages")
    bad = audit_text(OUT)
    if bad:
        print(f"\nem-dashes in reader-facing text ({len(bad)} file(s)):")
        for f, k, snip in bad[:8]:
            print(f"  {f}  x{k}   ...{snip}...")
        raise SystemExit(1)
    if n == 0:
        print("  (no scheme pages: run parse/explode.py then parse/checks.py first)")


if __name__ == "__main__":
    main()
