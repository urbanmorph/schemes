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
import gzip
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT_DIR, "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_m = _load("scheme_match", os.path.join(HERE, "match.py"))
probably_same, m_tokens, m_acronyms = _m.probably_same, _m.tokens, _m.acronyms

# Merging uses parse/match.py's GENEROUS matcher, not enrich/budget.py's conservative
# one. The two answer different questions and the earlier code used the wrong one here:
# a name that fails to merge becomes a claim that myScheme omits the scheme, so a
# conservative matcher inflates every absence. It cost us "Jal Jeevan Mission" and
# "MGNREGA" as false absences before this was caught.


def dbt_central(date):
    """Scheme names from the archived DBT Bharat central list.

    The page is 56 <ol> blocks, one per ministry, not a table — 320 <li> in total,
    which is the count DBT Bharat states for itself.
    """
    p = os.path.join(ROOT, "archive", "dbt", date, "central-list.html.gz")
    if not os.path.exists(p):
        return []
    html = gzip.open(p, "rb").read().decode("utf-8", "replace")
    out = []
    for block in re.findall(r"<ol[^>]*>(.*?)</ol>", html, re.S | re.I):
        for li in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S | re.I):
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", li)).strip()
            if name:
                out.append(name)
    return out


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
        return set(m_tokens(name)) | {a for a in m_acronyms(name) if len(a) >= 5}

    def register(en):
        for k in keys_for(en["name"]):
            index.setdefault(k, []).append(en)

    for en in entries:
        register(en)

    def add(names_with_detail, key):
        """Attach to an existing entry if one plausibly matches, else create a new one."""
        added = 0
        for name, detail in names_with_detail:
            seen, hit, why = set(), None, ""
            for k in keys_for(name):
                for en in index.get(k, ()):
                    if id(en) in seen:
                        continue
                    seen.add(id(en))
                    same, reason = probably_same(name, en["name"])
                    if same:
                        hit, why = en, reason
                        break
                if hit:
                    break
            if hit is not None:
                hit["sources"].setdefault(key, {**detail, "name": name,
                                                "merge_reason": why})
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


def main():
    ap = argparse.ArgumentParser(description="Build the union registry across sources.")
    ap.add_argument("--snapshot", default="2026-08-30")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    o = build(a.snapshot, a.year)
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
