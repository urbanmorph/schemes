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
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_out")

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


def num(x):
    return f"{x:,}" if isinstance(x, (int, float)) else '<span class="nil">...</span>'


def load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------- chrome

def shell(title, active, body, depth=0):
    up = "../" * depth
    st = shell.status or {}
    verdict = st.get("verdict")
    if verdict == "COMPLETE":
        dot, word = "", "COMPLETE"
    elif verdict:
        dot, word = " bad", verdict
    else:
        dot, word = " warn", "no run yet"

    days = "&mdash;"
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{up}theme.css?v={CSS_V}">
</head><body>
<header class="mast"><div class="wrap mast-in">
  <a class="brand" href="{home}">
    <span class="nil" aria-hidden="true">...</span>
    <span><h1>The Schemes Register</h1>
    <span class="sub">Indian government scheme data &middot; and what is missing from it</span></span>
  </a>
  <button class="tbtn" id="themeBtn" type="button">&#9686; theme</button>
</div></header>
<nav class="routes"><div class="wrap">{nav}</div></nav>
<div class="fresh"><div class="wrap">
  <span class="dot{dot}"></span>
  <span>Last complete collection <b>{days}</b></span>
  <span class="sep">&middot;</span><span>snapshot <b>{e(st.get('snapshot') or '—')}</b></span>
  <span class="sep">&middot;</span>
  <span>{num(st.get('records_parsed'))} of {num(st.get('expected_total'))} records
        &middot; {num(st.get('pages_written'))}/{num(st.get('pages_expected'))} pages</span>
  <span class="sep">&middot;</span><span>verdict <b>{e(word)}</b></span>
  <span class="sep">&middot;</span><span>{num(st.get('snapshots'))} snapshot(s) held</span>
</div></div>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">
  <span>The Schemes Register &middot; local build, not deployed</span>
  <span>Built {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; data CC BY 4.0</span>
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

def page_index(census, checks, dbt):
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
<section class="hero">
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
    <p>This is not a list of schemes you can apply to &mdash; myScheme already does that.
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
    deliberately not here yet &mdash; both carry real error bars and belong behind a
    methodology page. These do not.</div>
</section>

{index_section(checks)}
"""


def page_divergence(census, dbt):
    ms = (census or {}).get("facets", {}).get("beneficiaryState", {})
    ds = (dbt or {}).get("states", {})
    names = sorted(set(ms) | set(ds))
    rows = ""
    for n in names:
        if n == "All":
            continue
        a, b = ms.get(n), ds.get(n)
        ratio = f"{b / a:.1f}&times;" if a and b else '<span class="nil">...</span>'
        direction = ("DBT higher" if a and b and b > a
                     else "myScheme higher" if a and b and a > b else "&mdash;")
        rows += (f'<tr><td>{e(n)}</td><td class="num">{num(a)}</td>'
                 f'<td class="num">{num(b)}</td><td class="num">{ratio}</td>'
                 f'<td class="muted">{direction}</td></tr>')

    kar_ms, kar_dbt = ms.get("Karnataka"), ds.get("Karnataka")
    return f"""
<div class="eyebrow">Route &middot; /divergence</div>
<h2 class="pagetitle">Three sources, one question, different answers</h2>
<p class="standfirst">How many welfare schemes does a given state have? Every central
government portal that answers this question answers it differently, and no portal
acknowledges the others exist.</p>

<div class="callout">
  <div class="big">Karnataka is {num(kar_ms)} schemes or {num(kar_dbt)}, depending on which
  government portal you ask.</div>
  <div class="cite">myScheme beneficiaryState facet &middot; DBT Bharat state dashboard
  scode=Mjk &middot; both from the same snapshot</div>
</div>

<div class="tscroll"><table>
  <thead><tr><th>State</th><th class="num">myScheme</th><th class="num">DBT Bharat</th>
    <th class="num">Ratio</th><th>Direction</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>

<div class="warnbox">
  <b>These are different units &mdash; do not read the ratio as error</b>
  {e((dbt or {}).get('caveat', ''))}
  And myScheme's per-state number is a <em>beneficiary</em> tag spanning both central and
  state schemes, which is why the facet does not sum to the published total. Neither
  number is wrong. The finding is that both are published as &ldquo;schemes&rdquo; with
  nothing saying they count different things.
</div>
"""


def index_section(checks):
    rows = ""
    for s in (checks or {}).get("schemes", []):
        slug = s["slug"]
        failed = [c["id"] for c in s["checks"] if not c["ok"]]
        # The haystack is name + acronym + slug. In the development sector these schemes
        # are almost always referred to by acronym — nobody searches "Mahatma Gandhi
        # National Rural Employment Guarantee Scheme" — and the slug is frequently the
        # acronym too, so it costs nothing to include.
        short = s.get("short") or ""
        hay = " ".join(x for x in ((s["name"] or ""), short, slug) if x).lower()
        acr = f'<span class="acr">{e(short)}</span>' if short and short != s["name"] else ""
        rows += (
            f'<tr data-n="{e(hay)}" data-p="{s["passed"]}">'
            f'<td><a href="scheme/{e(slug)}.html">{e(s["name"] or slug)}</a>{acr}</td>'
            f'<td class="muted">{e(s.get("level") or "")}</td>'
            f'<td class="muted">{e((s.get("ministry") or "")[:44])}</td>'
            f'<td class="num"><b>{s["passed"]}</b>/{s["total"]}</td>'
            f'<td class="muted" style="font-size:12px">{e(", ".join(failed[:3]))}</td></tr>')
    n = len((checks or {}).get("schemes", []))
    if not n:
        return ('<section class="sec"><h2>Every scheme</h2>'
                '<div class="empty"><span class="big">...</span>'
                '<b>No scheme data built yet.</b><br>'
                'Run parse/explode.py, then parse/checks.py.</div></section>')
    return f"""
<section class="sec">
<h2>Every scheme, and how completely it is documented</h2>
<div class="sec-note">Sorted by checks passed, never by a grade &mdash; a count can be
  recomputed from the rows, and a letter is what gets screenshotted without its caption</div>
<div class="filters">
  <input id="q" type="search" placeholder="Filter by name or acronym&hellip;" aria-label="Filter schemes by name, acronym or slug">
  <select id="minp" aria-label="Minimum checks passed">
    <option value="">any score</option>
    {''.join(f'<option value="{i}">{i} or fewer passed</option>' for i in range(0, 10))}
  </select>
  <span class="count" id="count">{n:,} schemes</span>
</div>
<div class="tscroll"><table id="tbl">
  <thead><tr><th class="sortable" data-k="n">Scheme</th><th>Level</th><th>Ministry</th>
    <th class="num sortable" data-k="p">Passed</th><th>Failing</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
<script>
(function(){{
  var tb=document.querySelector('#tbl tbody'),rows=[].slice.call(tb.rows),
      q=document.getElementById('q'),mp=document.getElementById('minp'),
      c=document.getElementById('count'),asc=false;
  function apply(){{
    var t=q.value.toLowerCase(),m=mp.value===''?null:+mp.value,shown=0;
    rows.forEach(function(r){{
      var ok=(!t||r.dataset.n.indexOf(t)>-1)&&(m===null||+r.dataset.p<=m);
      r.hidden=!ok; if(ok)shown++;
    }});
    c.textContent=shown.toLocaleString()+' of {n:,} schemes';
  }}
  q.addEventListener('input',apply); mp.addEventListener('change',apply);
  document.querySelectorAll('th.sortable').forEach(function(th){{
    th.addEventListener('click',function(){{
      var k=th.dataset.k; asc=!asc;
      rows.sort(function(a,b){{
        var x=k==='p'?+a.dataset.p:a.dataset.n, y=k==='p'?+b.dataset.p:b.dataset.n;
        return (x<y?-1:x>y?1:0)*(asc?1:-1);
      }});
      rows.forEach(function(r){{tb.appendChild(r);}});
    }});
  }});
}})();
</script>
</section>
"""


def page_changes(log):
    if not log:
        return """
<div class="eyebrow">Route &middot; /changes</div>
<h2 class="pagetitle">What the government changed without saying</h2>
<p class="standfirst">A diff between consecutive monthly snapshots. Nothing here is an
opinion &mdash; each row is two archived payloads and the field that differs between them.</p>
<div class="empty">
  <span class="big">...</span>
  <b>One snapshot held.</b><br>
  A change feed needs two. The next monthly collection makes this page real; nothing can
  be backfilled to fill it in, which is the entire reason collection started before the
  site did.
</div>"""

    rows = ""
    for c in log:
        rows += (f'<div class="ch"><div class="ctype edit">{e(c["date"])}</div>'
                 f'<div><div class="name">{e(c["subject"])}</div>'
                 f'<div class="det">{c["files"]} file(s) changed</div></div></div>')
    return f"""
<div class="eyebrow">Route &middot; /changes</div>
<h2 class="pagetitle">What the government changed without saying</h2>
<div class="tscroll"><table><thead><tr><th>Snapshot</th><th>Commit</th>
<th class="num">Files changed</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(c["date"])}</td><td>{e(c["subject"])}</td>'
         f'<td class="num">{c["files"]}</td></tr>' for c in log)}
</tbody></table></div>
<div class="warnbox"><b>Why this page can be trusted more than the rest of the site</b>
A diff is not a judgment. Every row is derived from two archived payloads anyone can
re-fetch and compare. A snapshot that fails its completeness assertion is archived but
marked INCOMPLETE, and this page refuses to diff against it &mdash; otherwise a dropped
page of results would appear here as dozens of schemes being &ldquo;removed&rdquo;.</div>
"""


def page_scheme(s, status):
    checks = "".join(
        f'<div class="chk"><span class="mark {"p" if c["ok"] else "f"}">'
        f'{"&#10003;" if c["ok"] else "&#10007;"}</span>'
        f'<div>{e(c["id"].replace("_", " ").capitalize())}'
        f'<span class="why">{e(c["detail"])}</span></div></div>'
        for c in s["checks"])
    segs = "".join(f'<span class="seg {"p" if c["ok"] else "f"}"></span>' for c in s["checks"])

    chips = ""
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
            f'<span class="muted">{e(u["field"])} field &mdash; {e(u["why"])}</span></div>'
            for u in s["bad_urls"][:4]) + "</div>"

    def prov(field, value, source):
        v = e(value) if value else '<span class="nil">...</span>'
        return f'<tr><td>{e(field)}</td><td>{v}</td><td class="ts">{e(source)}</td></tr>'

    snap = status.get("snapshot", "")
    return f"""
<div class="eyebrow">Route &middot; /scheme/{e(s["slug"])}</div>
<div class="shead">
  <h2>{e(s["short"] or s["name"])}</h2>
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

def git_log():
    try:
        out = subprocess.run(
            ["git", "log", "--format=%H|%ad|%s", "--date=short", "--", "data/myscheme/schemes"],
            cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return []
    entries = []
    for line in out.splitlines():
        sha, d, subj = (line.split("|", 2) + ["", ""])[:3]
        n = subprocess.run(["git", "show", "--stat", "--format=", "--name-only", sha],
                           cwd=ROOT, capture_output=True, text=True).stdout
        entries.append({"date": d, "subject": subj,
                        "files": len([x for x in n.splitlines() if x.strip()])})
    return entries[:60]


# --------------------------------------------------------------------- build

def build():
    status = load("status.json", {}) or {}
    shell.status = status
    census = load("data/myscheme/census.json", {})
    checks = load("data/checks.json", {})
    dbt = load("data/dbt/states.json", {})

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "scheme"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "theme.css"), os.path.join(OUT, "theme.css"))

    def w(rel, s):
        with open(os.path.join(OUT, rel), "w", encoding="utf-8") as fh:
            fh.write(s)

    w("index.html", shell("The census and the argument", "/", page_index(census, checks, dbt)))
    w("divergence.html", shell("Divergence", "/divergence", page_divergence(census, dbt)))
    w("changes.html", shell("Changes", "/changes", page_changes(git_log())))

    n = 0
    for s in (checks or {}).get("schemes", []):
        w(os.path.join("scheme", f"{s['slug']}.html"),
          shell(s["short"] or s["name"], "/", page_scheme(s, status), depth=1))
        n += 1

    return n


def main():
    ap = argparse.ArgumentParser(description="Build the static site into site/_out.")
    ap.parse_args()
    n = build()
    print(f"built site/_out — 4 pages + {n:,} scheme pages")
    if n == 0:
        print("  (no scheme pages: run parse/explode.py then parse/checks.py first)")


if __name__ == "__main__":
    main()
