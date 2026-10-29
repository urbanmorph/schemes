"""
Build the union registry — every scheme any source names, not just myScheme's list.

AGENT-EDITABLE (PLAN.md §7). Reads data/ and archive/. Never fetches.

    data/registry.json

The register was mirroring one portal. That was a mistake: myScheme is a source, not
the definition of what exists. Union across four sources: 5,201 entries against
myScheme's 4,771 — 343 added by the Budget statements, 75 by DBT Bharat, 12 by the
Outcome Budget.

Absences here are claimed only when parse/match.py's GENEROUS matcher finds nothing.
An earlier version reused the conservative matcher from enrich/budget.py and inflated
every count: it reported 5,621 entries and 570 funded-but-unlisted lines worth
Rs 18.5 lakh cr, when the true figures are 5,201 and 311 worth Rs 10.4 lakh cr. The
difference was false absences — "Jal Jeevan Mission (JJM) / National Rural Drinking
Water Mission" scored 0.41 against myScheme's "Jal Jeevan Mission", and
"MGNREGA-Programme Component" scored 0.33 against "Mahatma Gandhi National Rural
Employment Guarantee Act". Both are listed. Claiming otherwise would have been a
false accusation, published.

Samagra Shiksha (Rs 42,100 cr) survives the generous matcher and is genuinely absent.

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
probably_same, m_tokens, m_acronyms = _m.probably_same, _m.tokens, _m.acronyms
# By path: collect/dbt.py is the collector and comes first on sys.path.
_dbt = _load("parse_dbt", os.path.join(HERE, "dbt.py"))
m_skeleton, m_similarity = _m.skeleton, _m.similarity

# Merging uses parse/match.py's GENEROUS matcher, not enrich/budget.py's conservative
# one. The two answer different questions and the earlier code used the wrong one here:
# a name that fails to merge becomes a claim that myScheme omits the scheme, so a
# conservative matcher inflates every absence. It cost us "Jal Jeevan Mission" and
# "MGNREGA" as false absences before this was caught.


def same_line(held, name, detail):
    """Is (name, detail) the source line an entry already holds? Name AND every field the
    source records about it. Two lines named alike in different demands are two lines:
    "Research and Development" is voted in demands 9, 21, 71 and 89, and comparing names
    alone kept demand 9's Rs 21 crore and dropped demand 21's Rs 17,250 crore."""
    return held.get("name") == name and all(held.get(k) == v for k, v in detail.items())


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

    def keys_for(name):
        # Skeletons as well as raw tokens, or the index silently cancels the matcher's
        # transliteration rule: probably_same knows Gruha and Griha are the same word,
        # but they are different index keys, so the pair is never made a candidate and
        # the match never gets the chance to happen. An index that under-retrieves does
        # not merely slow the join down, it decides it — every pair it fails to offer is
        # reported as an absence, which here is an accusation. Measured on the Karnataka
        # join: a skeleton-only index retrieved 504 matches where exhaustive comparison
        # found 564.
        t = set(m_tokens(name))
        return (t | {m_skeleton(x) for x in t}
                | {a for a in m_acronyms(name) if len(a) >= 5})

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
        added = 0
        for name, detail in names_with_detail:
            seen, cands = set(), []
            for k in sorted(keys_for(name)):
                for en in index.get(k, ()):
                    if id(en) in seen:
                        continue
                    seen.add(id(en))
                    same, reason = probably_same(name, en["name"])
                    if same:
                        cands.append((-m_similarity(name, en["name"]), en["name"],
                                      en, reason))
            hit, why = None, ""
            if cands:
                cands.sort(key=lambda c: (c[0], c[1]))
                hit, why = cands[0][2], cands[0][3]
            # setdefault silently discarded a second line matching the same entry, and
            # umbrella schemes routinely have several: 721 budget lines became 493
            # registry sources, losing 228 of them including FAME. If the slot is taken
            # by a DIFFERENT line, this is a distinct thing and gets its own entry.
            if hit is not None and key not in hit["sources"]:
                hit["sources"][key] = {**detail, "name": name, "merge_reason": why}
            elif hit is not None and same_line(hit["sources"][key], name, detail):
                pass
            else:
                en = {"name": name, "sources": {key: {**detail, "name": name}}}
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

    # Funded but never announced: a Budget line with money and no myScheme entry.
    unlisted = sorted(
        ({"name": en["name"],
          "be_cr": en["sources"]["budget"].get("be_cr"),
          "statement": en["sources"]["budget"].get("statement"),
          "demand_no": en["sources"]["budget"].get("demand_no"),
          "also_in": [k for k in en["sources"] if k not in ("budget",)]}
         for en in entries
         if "budget" in en["sources"] and "myscheme" not in en["sources"]
         and isinstance(en["sources"]["budget"].get("be_cr"), (int, float))),
        key=lambda x: -(x["be_cr"] or 0))

    by_count = {}
    for en in entries:
        by_count[len(en["sources"])] = by_count.get(len(en["sources"]), 0) + 1

    out = {
        "snapshot": snapshot, "cycle": f"{year}-{str(year+1)[2:]}", "built": utcnow(),
        "merge_rule": "parse/match.py probably_same, generous, for absence claims",
        "total_entries": len(entries),
        "myscheme_entries": len(checks),
        "added_by": {"budget": new_budget, "outcome": new_outcome, "dbt": new_dbt},
        "in_n_sources": dict(sorted(by_count.items())),
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
    held = {"name": "Research and Development", "statement": "stat4b", "demand_no": 9,
            "be_cr": 21.0, "merge_reason": "exact"}
    bad = 0
    for label, got, want in [
            ("the same line read twice is one line",
             same_line(held, "Research and Development",
                       {"statement": "stat4b", "demand_no": 9, "be_cr": 21.0}), True),
            ("the same name in another demand is another line",
             same_line(held, "Research and Development",
                       {"statement": "stat4b", "demand_no": 21, "be_cr": 17250.25}), False),
            ("a different name is another line",
             same_line(held, "Research", {"statement": "stat4b", "demand_no": 9}), False)]:
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
    print(f"\n  entries by number of sources naming them: {o['in_n_sources']}")
    print(f"\n  funded in the Budget, absent from myScheme: "
          f"{o['unlisted_but_funded_total']} schemes, "
          f"Rs {o['unlisted_but_funded_cr']:,.0f} cr")
    for u in o["unlisted_but_funded"][:8]:
        print(f"      Rs {u['be_cr']:>11,.2f} cr  {u['name'][:58]}")


if __name__ == "__main__":
    main()
