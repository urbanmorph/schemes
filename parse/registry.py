"""
Build the union registry — every scheme any source names, not just myScheme's list.

AGENT-EDITABLE (PLAN.md §7). Reads data/ and archive/. Never fetches.

    data/registry.json

The register was mirroring one portal. That was a mistake: myScheme is a source, not
the definition of what exists. Union across four sources: 5,201 entries against
myScheme's 4,771 — 343 added by the Budget statements, 75 by DBT Bharat, 12 by the
Outcome Budget.

Absences here are claimed only when parse/match.py's GENEROUS matcher finds nothing.
An earlier version reused the conservative matcher (now enrich/similarity.py) and inflated
every count: it reported 5,621 entries and 570 funded-but-unlisted lines worth
Rs 18.5 lakh cr, when the true figures are 5,201 and 311 worth Rs 10.4 lakh cr. The
difference was false absences — "Jal Jeevan Mission (JJM) / National Rural Drinking
Water Mission" scored 0.41 against myScheme's "Jal Jeevan Mission", and
"MGNREGA-Programme Component" scored 0.33 against "Mahatma Gandhi National Rural
Employment Guarantee Act". Both are listed. Claiming otherwise would have been a
false accusation, published.

Samagra Shiksha (Rs 42,100 cr) survives the generous matcher and is genuinely absent.

The CAG's setup facts (data/cag/facts.json) join last and by hand, not by this matcher: each
fact names the source its entry holds, and the schemes the register lacks come in as entries
of their own, many of them ended. See attach_cag().

Names are compared only against entries sharing a content word or acronym, via a token
index. Comparing every name against every entry took six minutes; this takes ten
seconds and makes the same comparisons.
"""

import argparse
import glob
import gzip
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT_DIR, "collect"))
from common import ROOT, read_json, utcnow, write_json  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_m = _load("scheme_match", os.path.join(HERE, "match.py"))
probably_same, m_index_keys = _m.probably_same, _m.index_keys
# By path: collect/dbt.py is the collector and comes first on sys.path.
_dbt = _load("parse_dbt", os.path.join(HERE, "dbt.py"))
m_similarity = _m.similarity

# Merging uses parse/match.py's GENEROUS matcher, not enrich/similarity.py's conservative
# one. The two answer different questions and the earlier code used the wrong one here:
# a name that fails to merge becomes a claim that myScheme omits the scheme, so a
# conservative matcher inflates every absence. It cost us "Jal Jeevan Mission" and
# "MGNREGA" as false absences before this was caught.


# Pairs the matcher accepts that were read and rejected: (source line, entry name), each
# with why. A line that money attaches to is published on that scheme's page, so a wrong
# merge puts another scheme's allocation there. Kept short and specific; a rule that
# would have to grow here is a matcher defect for parse/match.py.
REJECTED = {
    ("Startup India Fund of Funds 2.0", "Startup India Seed Fund Scheme- For Startups"):
        "a fund of funds for venture funds, not the seed fund for startups; containment "
        "of 'startup india fund' put Rs 900 cr on the seed fund's page",
    ("Startup India Fund of Funds 2.0", "Startup India Seed Fund Scheme- For Incubators"):
        "the same fund of funds, which moved to the seed fund's other page once the first "
        "pair was rejected",
}


def candidates(name, pool):
    """Every entry in `pool` the generous matcher accepts for `name`, as (-similarity,
    entry name, entry, reason), leaving out REJECTED pairs."""
    out = []
    for en in pool:
        if (name, en["name"]) in REJECTED:
            continue
        same, reason = probably_same(name, en["name"])
        if same:
            out.append((-m_similarity(name, en["name"]), en["name"], en, reason))
    return out


def line_key(name, detail):
    """A source line's identity: its name AND every field the source records about it. Two
    lines named alike in different demands are two lines: "Research and Development" is
    voted in demands 9, 21, 71 and 89, and comparing names alone kept demand 9's Rs 21 crore
    and dropped demand 21's Rs 17,250 crore."""
    return json.dumps([name, detail], sort_keys=True)


def state_page(en):
    """A state's or UT's myScheme record. None is an unrecorded level, not a state."""
    return (en["sources"].get("myscheme") or {}).get("level") not in (None, "Central")


def pick(cands):
    """The entry a national line merges into, from (-similarity, name, entry, reason)
    candidates: (entry, reason, state page it resembles).

    Every line merged here is a Union one (Budget, Outcome Budget, DBT's central list), and
    a state's myScheme page is that state's record, not the Union scheme. Letting them merge
    filed Nutrient Based Subsidy under Goa's "Internet Subsidy Scheme" and the National AIDS
    Control Programme under "... - Uttarakhand": 63 Union lines in all, each shown on a state
    page under a name that is not its own. So a Union line merges only into a national
    entry, and one that resembles only a state page gets its own entry with that page
    noted, because the resemblance is still the evidence that myScheme lists the scheme
    somewhere and must keep the line out of the absence count."""
    cands = sorted(cands, key=lambda c: (c[0], c[1]))
    national = [c for c in cands if not state_page(c[2])]
    if national:
        return national[0][2], national[0][3], None
    if cands:
        _, name, en, why = cands[0]
        return None, "", {"slug": en["sources"]["myscheme"]["slug"], "name": name,
                          "merge_reason": why}
    return None, "", None


def assign(lines, key):
    """Each (name, detail, candidates) line's entry, as (index, entry or None, reason, note).

    Exact names join first; every other line then takes its best candidate in the order
    the source lists them, each entry holding at most one line of a source. Line by line
    alone let the first plausible line take the slot: "National Career Services" (Rs 80 cr)
    took myScheme's National Service Scheme, and the exactly named National Service Scheme
    line (Rs 357 cr) was then published as funded and unlisted. Ranking every pair by
    similarity instead was tried and rejected: it moved 23 lines, among them PMAY-Urban
    (Rs 18,625 cr) off PMAY-U for the 2.0 line and the SC/ST post-doctoral fellowship onto
    the women's, because an acronym match scores low however right it is.

    A line left without an entry is noted with what it still resembles: a state's page
    (pick()) or a national myScheme record another line holds ("listed_as"). Either keeps
    it out of every absence claim (on_myscheme())."""
    taken = {id(c[2]) for _, _, cands in lines for c in cands if key in c[2]["sources"]}
    out = {}
    exact = sorted((name, c[1], i, j) for i, (name, _, cands) in enumerate(lines)
                   for j, c in enumerate(cands) if c[0] <= -1.0 and not state_page(c[2]))
    for _, _, i, j in exact:
        en = lines[i][2][j][2]
        if i not in out and id(en) not in taken:
            out[i] = (i, en, lines[i][2][j][3], {})
            taken.add(id(en))
    for i, (name, _, cands) in enumerate(lines):
        if i in out:
            continue
        hit, why, near = pick(cands)
        if hit is not None and id(hit) not in taken:
            out[i] = (i, hit, why, {})
            taken.add(id(hit))
            continue
        ms = hit if hit is not None and "myscheme" in hit["sources"] else None
        note = ({"state_page": near} if near else
                {"listed_as": {"slug": ms["sources"]["myscheme"]["slug"], "name": ms["name"],
                               "merge_reason": why}} if ms else {})
        out[i] = (i, None, "", note)
    return [out[i] for i in range(len(lines))]


def on_myscheme(en):
    """Does myScheme list this scheme, for every absence claim made from the register? Its
    own record, or a state's page its Union lines resemble (pick()): before pick() those
    lines merged into the state page and counted as listed, and keeping them on their own
    entry must not turn the resemblance into an accusation. Without this, classify.py
    newly called PM POSHAN and Saksham Anganwadi funded-but-unlisted."""
    return "myscheme" in en["sources"] or any(
        en["sources"].get(k, {}).keys() & {"state_page", "listed_as"} for k in ("budget", "outcome", "dbt"))


def source_keys(en):
    """Every source key an entry holds, in the form data/cag/facts.json names entries by."""
    src = en["sources"]
    if "myscheme" in src:
        yield {"myscheme": src["myscheme"]["slug"]}
    if "budget" in src:
        b = src["budget"]
        yield {"budget": [b["name"], b.get("statement"), b.get("demand_no")]}
    for k in ("outcome", "dbt"):
        if k in src:
            yield {k: src[k]["name"]}


def national_counts(entries):
    """(entries a national source names, {number of national sources: entries}). The CAG is
    not one of the four national lists, and a scheme only its reports name, many of them
    ended, must not be counted as one the four sources name."""
    n = {}
    for en in entries:
        k = len(en["sources"].keys() - {"cag"})
        if k:
            n[k] = n.get(k, 0) + 1
    return sum(n.values()), dict(sorted(n.items()))


def attach_cag(entries, cag):
    """Add the CAG's setup facts (data/cag/facts.json, local/cag/extraction/export.py): each
    attached fact to the entry holding its source, each draft as an entry of its own. Returns
    how many attached facts found no entry, which happens when a source leaves the register;
    they are counted in the output rather than dropped unseen.

    The facts are keyed by source rather than by entry name because names move when the merge
    changes: Nutrient Based Subsidy was filed under Goa's "Internet Subsidy Scheme" until pick()
    stopped Union lines merging into state pages."""
    # A key two entries hold names neither: the last one would win, silently.
    by_key, shared = {}, set()
    for en in entries:
        for k in map(json.dumps, source_keys(en)):
            if k in by_key and by_key[k] is not en:
                shared.add(k)
            by_key[k] = en
    for k in shared:
        del by_key[k]
    lost = 0
    for f in cag.get("attached", []):
        en = by_key.get(json.dumps(f["entry"]))
        if en is None:
            lost += 1
            continue
        en["sources"].setdefault("cag", {"facts": []})["facts"].append(
            {k: v for k, v in f.items() if k != "entry"})

    def name(link):
        en = by_key.get(json.dumps(link.get("entry")))
        return link.get("draft") or (en and en["name"])

    for d in cag.get("drafts", []):
        rec = {k: v for k, v in d.items() if k != "name"}
        for r in ("replaced_by", "part_of"):
            if r in rec:
                rec[r] = [n for n in map(name, rec[r]) if n]
        entries.append({"name": d["name"], "sources": {"cag": rec}})
    return lost


def dbt_central(date):
    """Scheme names from the archived DBT Bharat central list."""
    p = os.path.join(ROOT, "archive", "dbt", date, "central-list.html.gz")
    if not os.path.exists(p):
        return []
    with gzip.open(p, "rb") as fh:
        return _dbt.central_names(fh.read().decode("utf-8", "replace"))


def build(snapshot, year):
    checks = json.load(open(os.path.join(ROOT, "data", "checks.json"),
                            encoding="utf-8"))["schemes"]

    entries = []
    for s in checks:
        entries.append({
            "name": s["name"] or s["slug"],
            "sources": {"myscheme": {"slug": s["slug"], "level": s.get("level"),
                                     "org": s.get("org"), "passed": s["passed"],
                                     "total": s["total"]}},
        })

    # Token index, so a name is only compared against entries that share a content word
    # or an acronym with it. Comparing every name against every entry was 5,600 x 6,000
    # and took six minutes; this makes the same comparisons on a few dozen candidates.
    index = {}

    keys_for = m_index_keys

    def register(en):
        for k in keys_for(en["name"]):
            index.setdefault(k, []).append(en)

    for en in entries:
        register(en)

    def add(names_with_detail, key):
        """Attach to the BEST matching entry if one plausibly matches, else create one.

        Every candidate is gathered and then ranked. Taking the first match instead made
        the join depend on set iteration order, which Python varies per process: three
        identical runs of this file returned 5,438, 5,428 and 5,417 entries, and pinning
        PYTHONHASHSEED returned 5,429 every time. Nothing upstream had changed.

        For a register whose value is a comparable monthly series, and whose change feed
        is `git log` over these files, that is worse than being wrong in a fixed way. A
        rebuild would show schemes merging and splitting with no government having done
        anything, which is the same failure this repository refuses INCOMPLETE snapshots
        to avoid. It also meant every count published here carried an undisclosed error
        bar of about twenty.

        Sorting the keys restores determinism. Ranking by similarity additionally makes
        the choice the best available one rather than whichever the hash offered first,
        with the name as tie-breaker so equal scores still resolve the same way.
        """
        lines, held = [], set()
        for name, detail in names_with_detail:
            # The same line read twice is one line.
            if line_key(name, detail) in held:
                continue
            held.add(line_key(name, detail))
            seen, pool = set(), []
            for k in sorted(keys_for(name)):
                for en in index.get(k, ()):
                    if id(en) not in seen:
                        seen.add(id(en))
                        pool.append(en)
            lines.append((name, detail, candidates(name, pool)))
        # setdefault silently discarded a second line matching the same entry, and umbrella
        # schemes routinely have several: 721 budget lines became 493 registry sources,
        # losing 228 of them including FAME. A line whose entry is taken by a closer line is
        # a distinct thing and gets its own entry.
        added = 0
        for i, hit, why, note in assign(lines, key):
            name, detail, _ = lines[i]
            if hit is not None:
                hit["sources"][key] = {**detail, "name": name, "merge_reason": why}
                continue
            en = {"name": name, "sources": {key: {**detail, "name": name, **note}}}
            entries.append(en)
            register(en)
            added += 1
        return added

    budget = []
    for stmt in ("stat4a", "stat4b"):
        p = os.path.join(ROOT, "data", "budget", str(year), f"{stmt}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        for it in d["items"]:
            budget.append((it["name"], {"statement": stmt, "demand_no": it.get("demand_no"),
                                        "be_cr": it.get("be_next_year"),
                                        "cycle": d.get("cycle")}))
    new_budget = add(budget, "budget")

    obp = os.path.join(ROOT, "data", "outcome", f"{year}.json")
    new_outcome = 0
    if os.path.exists(obp):
        ob = json.load(open(obp, encoding="utf-8"))
        new_outcome = add([(f["name"], {"page": f["page"], "outlay_cr": f.get("outlay_cr"),
                                        "classification": f["classification"],
                                        "targets": len(f["outputs"]) + len(f["outcomes"])})
                           for f in ob["schemes"]], "outcome")

    new_dbt = add([(n, {"list": "central"}) for n in dbt_central(snapshot)], "dbt")

    cag = read_json("data/cag/facts.json", {}) or {}
    cag_lost = attach_cag(entries, cag)

    # Funded but never announced: a Budget line with money and no myScheme entry.
    unlisted = sorted(
        ({"name": en["name"],
          "be_cr": en["sources"]["budget"].get("be_cr"),
          "statement": en["sources"]["budget"].get("statement"),
          "demand_no": en["sources"]["budget"].get("demand_no"),
          "also_in": [k for k in en["sources"] if k not in ("budget",)]}
         for en in entries
         if "budget" in en["sources"] and not on_myscheme(en)
         and isinstance(en["sources"]["budget"].get("be_cr"), (int, float))),
        key=lambda x: -(x["be_cr"] or 0))

    national, by_count = national_counts(entries)

    out = {
        "snapshot": snapshot, "cycle": f"{year}-{str(year+1)[2:]}", "built": utcnow(),
        "merge_rule": "parse/match.py probably_same, generous, for absence claims",
        "total_entries": len(entries),
        "myscheme_entries": len(checks),
        "added_by": {"budget": new_budget, "outcome": new_outcome, "dbt": new_dbt,
                     "cag": len(cag.get("drafts", []))},
        "cag_facts_unattached": cag_lost,
        "national_entries": national,
        "cag_only_entries": len(entries) - national,
        "in_n_sources": by_count,
        "unlisted_but_funded": unlisted[:400],
        "unlisted_but_funded_total": len(unlisted),
        "unlisted_but_funded_cr": round(sum(u["be_cr"] or 0 for u in unlisted), 2),
        "caveat": ("Clustered by name similarity at a deliberately high floor, so the "
                   "union under-merges: one scheme appearing twice is a visible and "
                   "fixable error, while two different schemes silently collapsed into "
                   "one is not. Counts here are a floor on how many schemes exist, "
                   "never a ceiling."),
        "entries": entries,
    }
    write_json("data/registry.json", out)
    return out


def latest_dbt():
    """The newest DBT snapshot that walked clean. run.sh called this module and
    classify.py with no --snapshot, and the default was a fixed 2026-08-30, so every
    monthly run built the DBT half of the registry from August's archive and labelled it
    that way."""
    dates = [os.path.basename(os.path.dirname(p))
             for p in glob.glob(os.path.join(ROOT, "archive", "dbt", "*", "_manifest.json"))
             if (read_json(p, {}) or {}).get("error_count") == 0]
    if not dates:
        raise SystemExit("no clean DBT snapshot under archive/dbt")
    return max(dates)


def selftest():
    def entry(name, slug, level):
        return {"name": name, "sources": {"myscheme": {"slug": slug, "level": level}}}
    goa = entry("Internet Subsidy Scheme", "internet-subsidy-scheme", "State/ UT")
    central = entry("Nutrient Based Subsidy Scheme", "nbs", "Central")
    picks = [
        ("a Union line never lands on a state's page, however alike the names",
         pick([(-0.9, goa["name"], goa, "transliteration variant")]),
         (None, "", {"slug": "internet-subsidy-scheme", "name": "Internet Subsidy Scheme",
                     "merge_reason": "transliteration variant"})),
        ("a national entry is chosen over a closer state page",
         pick([(-0.9, goa["name"], goa, "x"), (-0.5, central["name"], central, "y")]),
         (central, "y", None)),
        ("no candidate, no state page", pick([]), (None, "", None))]
    nss = {"name": "National Service Scheme", "sources": {"myscheme": {"slug": "nssc", "level": "Central"}}}
    career = ("National Career Services", {"be_cr": 80.0},
              [(-0.6, nss["name"], nss, "all 2 content words of the shorter name are present")])
    service = ("National Service Scheme", {"be_cr": 357.39}, [(-1.0, nss["name"], nss, "exact")])
    got = assign([career, service], "budget")
    picks += [
        ("the closest line takes an entry, whichever line arrives first",
         [(g[1] and g[1]["name"], g[2]) for g in got], [(None, ""), ("National Service Scheme", "exact")]),
        ("a line that loses the entry to a closer one still resembles that myScheme record",
         got[0][3], {"listed_as": {"slug": "nssc", "name": "National Service Scheme",
                                   "merge_reason": "all 2 content words of the shorter name are present"}}),
        ("an entry already holding this source takes no second line",
         assign([service], "myscheme")[0][1], None)]
    nbs = {"name": "Nutrient Based Subsidy", "sources": {"budget": {
        "name": "Nutrient Based Subsidy", "statement": "stat4b", "demand_no": 6}}}
    pm = {"name": "PM POSHAN", "sources": {"myscheme": {"slug": "pm-poshan", "level": "Central"}}}
    fact = {"field": "start", "value": "1992", "citation": "CAG, p. 1."}
    cag = {"attached": [{"entry": {"myscheme": "pm-poshan"}, "relation": "same", **fact},
                        {"entry": {"myscheme": "gone"}, "relation": "same", **fact}],
           "drafts": [{"name": "Concession Scheme", "government": "Central", "facts": [fact],
                       "replaced_by": [{"entry": {"budget": ["Nutrient Based Subsidy", "stat4b", 6]}},
                                       {"draft": "Later"}]}]}
    entries = [nbs, pm]
    lost = attach_cag(entries, cag)
    picks += [
        ("a CAG fact attaches to the entry holding its source",
         pm["sources"].get("cag"), {"facts": [{"relation": "same", **fact}]}),
        ("a fact whose source has gone is counted, not dropped silently", lost, 1),
        ("a pair read and rejected never merges, however the matcher scores it",
         [c[1] for c in candidates("Startup India Fund of Funds 2.0",
                                   [{"name": "Startup India Seed Fund Scheme- For Startups", "sources": {}},
                                    {"name": "Fund of Funds for Startups", "sources": {}}])],
         ["Fund of Funds for Startups"]),
        ("a fact keyed to a source two entries hold attaches to neither, and is counted",
         attach_cag([{"name": "A", "sources": {"outcome": {"name": "Fund of Funds"}}},
                     {"name": "B", "sources": {"outcome": {"name": "Fund of Funds"}}}],
                    {"attached": [{"entry": {"outcome": "Fund of Funds"}, **fact}]}), 1),
        ("the national counts leave out what only the CAG names, and the CAG as a source",
         national_counts(entries), (2, {1: 2})),
        ("a line resembling a state's page counts as on myScheme, so it is never called absent",
         on_myscheme({"sources": {"budget": {"state_page": {"slug": "x"}}}}), True),
        ("a line with no myScheme record or resemblance is not on it",
         on_myscheme({"sources": {"budget": {}}}), False),
        ("a draft is an entry of its own, its links named by the entries' current names",
         entries[2], {"name": "Concession Scheme", "sources": {"cag": {
             "government": "Central", "facts": [fact],
             "replaced_by": ["Nutrient Based Subsidy", "Later"]}}})]
    held = line_key("Research and Development", {"statement": "stat4b", "demand_no": 9, "be_cr": 21.0})
    bad = 0
    for label, got, want in [
            ("the same line read twice is one line",
             line_key("Research and Development",
                      {"be_cr": 21.0, "demand_no": 9, "statement": "stat4b"}) == held, True),
            ("the same name in another demand is another line",
             line_key("Research and Development",
                      {"statement": "stat4b", "demand_no": 21, "be_cr": 17250.25}) == held, False),
            ("a different name is another line",
             line_key("Research", {"statement": "stat4b", "demand_no": 9, "be_cr": 21.0}) == held, False)] + picks:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Build the union registry across sources.")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--snapshot", help="DBT snapshot date (default: the newest clean one)")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    if a.self_test:
        print("registry self-test")
        sys.exit(1 if selftest() else 0)
    o = build(a.snapshot or latest_dbt(), a.year)
    print(f"union registry: {o['total_entries']:,} entries "
          f"(myScheme alone: {o['myscheme_entries']:,})")
    for k, v in o["added_by"].items():
        print(f"    + {v:>4} from {k}")
    if o["cag_facts_unattached"]:
        print(f"    !! {o['cag_facts_unattached']} CAG facts name a source no longer in the register")
    print(f"\n  entries by number of national sources naming them: {o['in_n_sources']}")
    print(f"\n  funded in the Budget, absent from myScheme: "
          f"{o['unlisted_but_funded_total']} schemes, "
          f"Rs {o['unlisted_but_funded_cr']:,.0f} cr")
    for u in o["unlisted_but_funded"][:8]:
        print(f"      Rs {u['be_cr']:>11,.2f} cr  {u['name'][:58]}")


if __name__ == "__main__":
    main()
