"""
Enrichment from the archived Union Budget statements — money myScheme never publishes.

SECONDARY LAYER (see enrich/wikidata.py for the rule). Writes only to
data/enrichment/, never into data/myscheme/, and is never counted by parse/checks.py.

Why this source rather than the open web: the point of the register is to surface what
is *not* easily available. Wikidata was tried and measured first — on a random sample of
40 central schemes it matched 0. It carries the dozen flagship schemes everyone can
already name and nothing else, which is precisely the easily-available information.

The Budget statements are the opposite. They are a government source, already archived
here, and they carry a per-scheme allocation that myScheme publishes nowhere at all:
myScheme has no budget field of any kind. A reader who wants to know what PM-KISAN costs
this year cannot get it from the portal that exists to explain PM-KISAN.

    data/enrichment/budget.json      matched schemes, with a confidence band each

On the match rate. Only ~8% of central schemes join a budget line at 0.75 or better.
That is not a shortfall in the matcher — it is the same finding as the headline
divergence, seen per scheme. myScheme lists citizen-facing schemes; the statements list
budget lines, which are often umbrella heads or sub-components. The two lists do not
correspond, and 543-vs-637 is what that looks like in aggregate. So the unmatched
majority is published as a fact about the sources, not hidden as a failure.

Every match ships its score and both names, so any join can be checked by eye and
disputed. Nothing below the floor is presented as a match.
"""

import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

# Words that carry no distinguishing signal in Indian scheme names — almost every scheme
# is a "yojana" or a "mission", so matching on them manufactures similarity.
STOP = {"scheme", "yojana", "yojna", "programme", "program", "mission", "abhiyan",
        "the", "of", "for", "and", "a", "an", "in", "to"}

STRONG, LIKELY, WEAK = 0.85, 0.75, 0.55


def norm(s):
    s = re.sub(r"\(.*?\)", " ", (s or "").lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 2}


def similarity(a, b):
    """Lower of sequence ratio and a ratio/overlap blend — the conservative reading.

    Ratio alone rewards two long names sharing boilerplate; token overlap alone rewards
    one shared word. A wrong join here publishes a rupee figure under the wrong scheme's
    name, so the bias is deliberately toward under-matching.
    """
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = tokens(a), tokens(b)
    overlap = len(ta & tb) / max(len(ta | tb), 1) if (ta and tb) else 0.0
    return min(ratio, (overlap + ratio) / 2)


def band(score):
    if score >= STRONG:
        return "strong"
    if score >= LIKELY:
        return "likely"
    if score >= WEAK:
        return "weak"
    return None


def load_budget(year):
    lines = []
    for stmt, kind in (("stat4a", "Centrally Sponsored"), ("stat4b", "Central Sector")):
        p = os.path.join(ROOT, "data", "budget", str(year), f"{stmt}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        for it in d["items"]:
            lines.append({**it, "statement": stmt, "kind": kind,
                          "cycle": d.get("cycle")})
    return lines


def run(year):
    schemes = json.load(open(os.path.join(ROOT, "data", "checks.json"),
                             encoding="utf-8"))["schemes"]
    central = [s for s in schemes if s.get("level_value") == "central"]
    lines = load_budget(year)
    if not lines:
        raise SystemExit(f"no parsed budget at data/budget/{year} — run parse/budget.py")

    matched, counts = {}, {"strong": 0, "likely": 0, "weak": 0, "none": 0}
    for s in central:
        best, score = None, 0.0
        for ln in lines:
            sc = similarity(s["name"], ln["name"])
            if sc > score:
                best, score = ln, sc
        b = band(score)
        counts[b or "none"] += 1
        if b in ("strong", "likely"):
            matched[s["slug"]] = {
                "budget_line": best["name"],
                "scheme_name": s["name"],
                "match_score": round(score, 3),
                "confidence": b,
                "be_next_year_cr": best.get("be_next_year"),
                "demand_no": best.get("demand_no"),
                "statement": best["statement"],
                "classification": best["kind"],
                "cycle": best.get("cycle"),
                "source": "Union Budget, Expenditure Profile "
                          f"Statement {best['statement'][-2:].upper()}",
            }

    write_json("data/enrichment/budget.json", {
        "cycle": f"{year}-{str(year + 1)[2:]}",
        "built": utcnow(),
        "source": "Union Budget Expenditure Profile, Statements 4A and 4B",
        "central_schemes": len(central),
        "budget_lines": len(lines),
        "counts": counts,
        "thresholds": {"strong": STRONG, "likely": LIKELY, "weak": WEAK},
        "caveat": ("Fuzzy name join, published with its score so it can be disputed. "
                   "Only strong and likely matches are carried. The large unmatched "
                   "majority is a fact about the sources: myScheme lists citizen-facing "
                   "schemes and the statements list budget lines, not a gap in this "
                   "register."),
        "schemes": matched,
    })
    return counts, len(central), len(lines)


def main():
    ap = argparse.ArgumentParser(description="Join central schemes to Budget lines.")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    counts, n, m = run(a.year)
    print(f"Budget {a.year}-{str(a.year+1)[2:]} · {n} central schemes vs {m} budget lines")
    for k in ("strong", "likely", "weak", "none"):
        print(f"    {k:<8}{counts[k]:>5}   {100*counts[k]/n:>5.1f}%")
    carried = counts["strong"] + counts["likely"]
    print(f"\n  carried into the site: {carried} ({100*carried/n:.1f}%) — "
          f"each with its score, disputable by eye")


if __name__ == "__main__":
    main()
