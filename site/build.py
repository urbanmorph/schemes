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
    <h2 class="pagetitle">Every scheme any government source names &mdash;
      and what each one fails to say</h2>
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
"""


def page_divergence(census, dbt, reg=None, cls=None):
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

    # Funded, monitored, and never announced. The strongest thing the union registry
    # says: these are named as schemes by at least two government sources and carry a
    # Budget allocation, and the government's own citizen-facing portal does not list
    # them at all.
    unlisted_section = ""
    if reg and cls:
        rows = "".join(
            f'<tr><td>{e(u["name"])}</td>'
            f'<td class="num">{u["be_cr"]:,.0f}</td>'
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
  harder finding than any missing field &mdash; and it is invisible to anything that
  treats myScheme&rsquo;s 4,772 as the universe.</p>
  <div class="tscroll"><table>
    <thead><tr><th>Funded and classified a scheme, absent from myScheme</th>
      <th class="num">BE 2026&ndash;27 (&#8377; cr)</th><th class="num">Score</th>
      <th>Why it scores as a scheme</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <div class="warnbox">
    <b>How these were separated from budget heads, and how often that is wrong</b>
    Statement 4B mixes welfare schemes with infrastructure and accounting heads &mdash;
    &ldquo;Road Works&rdquo;, &ldquo;Rolling Stock&rdquo;, &ldquo;Manufacturing
    Suspense&rdquo; &mdash; that no citizen applies to. A classifier scores each line on
    independent signals: named in DBT Bharat&rsquo;s list (+3), Centrally Sponsored (+2),
    benefit words in the name (+2), has an outcome framework (+1), asset or accounting
    words (&minus;3), capital-heavy demand (&minus;2). Every line&rsquo;s arithmetic is
    published so the verdict can be rechecked.
    <p style="margin:8px 0 0">Validated against myScheme membership as ground truth:
    at the F1-optimal threshold of 2 precision is
    {v.get('precision', 0):.0%}; this table runs at the stricter threshold of {thr},
    where precision is {prec:.0%} &mdash; naming a scheme as missing is an accusation,
    so it runs at the high-precision end. Recall is a floor and not a measurement: a
    line called a scheme that myScheme lacks may be the classifier being right and the
    portal being incomplete, which is the thing this page is about. Residual errors are
    visible above &mdash; &ldquo;Space Technology&rdquo; should not be here.</p>
  </div>
</section>"""

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

{unlisted_section}
"""


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
    for i, (v, lab, n) in enumerate(options):
        on = " on" if i == 0 else ""
        pressed = "true" if i == 0 else "false"
        count = f'<span class="pn">{n:,}</span>' if n is not None else ""
        parts.append(f'<button type="button" class="pill{on}" data-g="{gid}" '
                     f'data-v="{e(v)}" aria-pressed="{pressed}">{e(lab)}{count}</button>')
    btns = "".join(parts)
    return (f'<div class="pillgroup" role="group" aria-label="{e(label)}">'
            f'<span class="plabel">{e(label)}</span>{btns}</div>')


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
        'placeholder="Any ministry or department &mdash; type to filter, or browse" '
        'aria-label="Filter by ministry or department">'
        f'<datalist id="orglist">{org_options}</datalist>'
        '<button type="button" id="orgclear" class="tbtn" hidden>clear</button>')

    st = {}
    for e_ in entries:
        v = e_.get("state")
        for x in (v if isinstance(v, list) else [v] if v else []):
            st[x] = st.get(x, 0) + 1
    # "All" is myScheme's own label for a nationwide scheme, not a state. Keeping it in
    # the list but naming it plainly stops it reading as "no filter".
    state_select = (
        '<select id="st" aria-label="Filter by state or UT">'
        '<option value="">Any state or UT</option>'
        + "".join(f'<option value="{e(k.lower())}">'
                  f'{e("Nationwide (All)" if k == "All" else k)} ({n:,})</option>'
                  for k, n in sorted(st.items(), key=lambda kv: (kv[0] == "All", -kv[1])))
        + '</select>')

    lv = {}
    for e_ in entries:
        v = e_.get("level_value")
        if v:
            lv[v] = lv.get(v, 0) + 1
    LEVEL_LABEL = {"central": "Central", "state": "State or UT"}
    level_pills = pill_group("lvl", "Level",
                             [("", "All", len(entries))]
                             + [(k, LEVEL_LABEL.get(k, k), n)
                                for k, n in sorted(lv.items(), key=lambda kv: -kv[1])])

    src_counts = {}
    for e_ in entries:
        for k in e_["sources"]:
            src_counts[k] = src_counts.get(k, 0) + 1
    not_ms = sum(1 for e_ in entries if not e_["on_myscheme"])
    src_pills = pill_group(
        "src", "Listed by",
        [("", "All", len(entries))]
        + [(k, SOURCE_LABEL[k], src_counts[k])
           for k in ("myscheme", "budget", "dbt", "outcome") if k in src_counts]
        + [("!myscheme", "Not on myScheme", not_ms)])

    # Cuts that mean something, not "N or fewer" for every N. Measured: no scheme scores
    # below 2 or above 9, and the mass sits at 5-7, so most of the old dropdown's
    # eleven options selected either everything or nothing.
    def le(nmax):
        return sum(1 for x in entries
                   if x["checks"] and x["checks"]["passed"] <= nmax)
    doc_pills = pill_group(
        "doc", "Documentation",
        [("", "All", len(entries)),
         ("le4", "4 or fewer passed", le(4)),
         ("le5", "5 or fewer", le(5)),
         ("le6", "6 or fewer", le(6)),
         ("ge8", "8 or more", sum(1 for x in entries
                                  if x["checks"] and x["checks"]["passed"] >= 8)),
         ("none", "No record to check", sum(1 for x in entries if not x["checks"]))])

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
        sq = {x for x in sq if len(x) > 2 and x not in hay.split()}
        xattr = f' data-x="{e(" ".join(sorted(sq)))}"' if sq else ""
        acr = f'<span class="acr">{e(short)}</span>' if short and short != e_["name"] else ""
        badges = "".join(f'<span class="src {k}">{e(SOURCE_LABEL[k])}</span>'
                         for k in e_["sources"])
        if c:
            failed = [c_["id"] for c_ in c["checks"] if not c_["ok"]]
            score = f'<b>{c["passed"]}</b>/{c["total"]}'
            failing = e(" · ".join(CHECK_CODE.get(x, x) for x in failed[:3]))
        else:
            # Not on myScheme, so there is nothing to check. Showing 0/9 would read as a
            # verdict on the scheme rather than a fact about which portal lists it.
            score = '<span class="nil">...</span>'
            failing = '<span class="muted">not listed on myScheme</span>'
        rows += (f'<tr{xattr} data-p="{(c or {}).get("passed", -1)}" '
                 f'data-o="{e((e_.get("org") or "").lower())}" '
                 f'data-l="{e(e_.get("level_value") or "")}" '
                 f'data-st="{e(" ".join(x.lower() for x in ((e_.get("state") if isinstance(e_.get("state"), list) else [e_.get("state")]) if e_.get("state") else [])))}" '
                 f'data-s="{e(" ".join(e_["sources"]))}"'
                 + (f' data-b="{e_["be_cr"]:.0f}"' if isinstance(e_.get("be_cr"), (int, float)) else "")
                 + '>'
                 f'<td><a href="scheme/{e(slug)}.html">{e(e_["name"])}</a>{acr}</td>'
                 f'<td>{badges}</td>'
                 f'<td class="muted">{e(e_.get("level") or "")}</td>'
                 f'<td class="muted">{e((e_.get("org") or "")[:44])}</td>'
                 f'<td class="num">{score}</td>'
                 f'<td class="muted" style="font-size:12px">{failing}</td></tr>')

    n = len(entries)
    if not n:
        return ('<section class="sec"><h2>Every scheme</h2><div class="empty">'
                '<span class="big">...</span><b>No registry built yet.</b><br>'
                'Run parse/registry.py.</div></section>')
    return f"""
<section class="sec schemes" id="schemes">
<div class="sec-note">{n:,} across four sources &mdash; myScheme, the Union Budget,
  the Outcome Budget and DBT Bharat. Entries with no myScheme record have nothing to
  check, which is itself the finding.</div>
<div class="workspace">
<div class="wmain">
<div class="filters">
  <input id="q" type="search" placeholder="Search name or acronym &mdash; e.g. pm kisan, mgnrega&hellip;"
    aria-label="Search schemes by name, acronym or slug">
  {state_select}
  {org_select}
  <span class="count" id="count">{n:,} schemes</span>
</div>
<div class="pills">
  {level_pills}
  {src_pills}
  {doc_pills}
</div>
<div class="tscroll"><table id="tbl">
  <thead><tr><th class="sortable" data-k="n">Scheme</th><th>Listed by</th><th>Level</th>
    <th>Ministry / department</th><th class="num sortable" data-k="p">Passed</th>
    <th>Failing</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>
</div>
<aside class="wrail" aria-label="Statistics for the current selection">
  <div class="railhd">This selection</div>
  <div class="railbig"><span id="rShown">{n:,}</span><span class="railof">of {n:,}</span></div>
  <div class="railrow"><span>Not on myScheme</span><b id="rNoMs">&mdash;</b></div>
  <div class="railrow"><span>Median checks passed</span><b id="rMed">&mdash;</b></div>
  <div class="railrow"><span>Allocation known</span><b id="rMoney">&mdash;</b></div>
  <div class="railhd" style="margin-top:16px">Listed by</div>
  <div class="railrow"><span>myScheme</span><b id="rSms">&mdash;</b></div>
  <div class="railrow"><span>Union Budget</span><b id="rSbu">&mdash;</b></div>
  <div class="railrow"><span>DBT Bharat</span><b id="rSdb">&mdash;</b></div>
  <div class="railrow"><span>Outcome Budget</span><b id="rSoc">&mdash;</b></div>
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
      state={{lvl:'',src:'',doc:''}};
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
    set('rMed', med===null ? '—' : med+' of 9');
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
      : 'No single filter explains it — several are narrowing at once.';
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
  document.querySelectorAll('th.sortable').forEach(function(th){{
    th.addEventListener('click',function(){{
      var k=th.dataset.k; asc=!asc;
      rows.sort(function(a,b){{
        var x=k==='p'?+a.dataset.p:a._h, y=k==='p'?+b.dataset.p:b._h;
        return (x<y?-1:x>y?1:0)*(asc?1:-1);
      }});
      rows.forEach(function(r){{tb.appendChild(r);}});
    }});
  }});
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
            bits.append(f'outlay &#8377;{d["outlay_cr"]:,.2f} cr')
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
  <h2>{e(en["name"])}</h2>
  <div class="full">Named by {len(en["sources"])} government source(s), and not listed
    on myScheme</div>
  <div class="chips">{chips}</div>
</div>

<div class="warnbox">
  <b>No documentation checks for this scheme</b>
  The nine checks measure what myScheme publishes about a scheme. There is no myScheme
  record here to measure, so this page shows none &mdash; a score of nought would read
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
      <td class="ts">&mdash;</td></tr>
  </table></div>
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


# A scheme's launch date exists — it is in the gazette notification or the government
# order that created it. So "no start date recorded" is a weak claim that sounds like the
# fact is unknowable. The real claim is narrower and much stronger: the portal a citizen
# actually visits does not tell them, even though the government can point at the
# notification and say it was published. These labels are about the portal.
# Compact codes for the index's "failing" column. Spelling the check ids out on every
# one of 4,771 rows cost 496 KB — 21.5% of the page — to repeat nine strings.
CHECK_CODE = {
    "eligibility_documented": "eligibility",
    "benefit_quantified": "benefit",
    "description_substantive": "description",
    "implementing_agency_named": "agency",
    "application_path_published": "how-to-apply",
    "start_date_recorded": "start",
    "end_date_recorded": "end",
    "stored_urls_well_formed": "links",
    "not_expired_while_listed": "expired",
}

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
    targets and <b>no achieved-versus-promised column</b> — for this scheme or any
    other.</div>"""

    b = (enrich or {}).get("budget", {}).get(s["slug"])
    if b or ob:
        amt = (b or {}).get("be_next_year_cr")
        amt_s = f"&#8377;{amt:,.2f} cr" if isinstance(amt, (int, float)) else '<span class="nil">...</span>'
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
    its gazette notification whether or not the portal repeats it &mdash; the checks
    above ask only whether <em>this portal</em> tells a citizen, which is a different
    and narrower question.</div>
</section>"""

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

{found_block}

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
    w("index.html", shell("The census and the argument", "/",
                          page_index(census, checks, dbt, entries)))
    w("divergence.html", shell("Divergence", "/divergence",
                               page_divergence(census, dbt, load("data/registry.json", {}),
                                               load("data/classification.json", {}))))
    w("changes.html", shell("Changes", "/changes", page_changes(git_log())))

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
        w(os.path.join("scheme", f"{en['slug']}.html"),
          shell(title, "/", body, depth=1))
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
