"""
Join central schemes to their Output-Outcome Monitoring Framework.

SECONDARY LAYER. Writes only data/enrichment/outcome.json, never into data/myscheme/,
and never counted by parse/checks.py.

What this surfaces is the sharpest thing the register can say about a scheme. The
Outcome Budget is where the government writes down what a scheme will deliver this year
— 9.5 crore beneficiaries, 95% of grievances redressed — and it is a 302-page PDF that
no citizen will ever open. myScheme, the portal built to explain these schemes to
citizens, publishes none of it.

It also makes the coverage claim concrete per scheme rather than in aggregate. 167 of
711 central schemes have a framework at all; the rest have no published target of any
kind, which is a statement about the Outcome Budget's scope and not about them.

Matching reuses enrich/budget.py's conservative similarity, for the same reason: a wrong
join here attributes one scheme's promise to another.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def _load(name, path):
    """Import by path. `collect/budget.py` and `enrich/budget.py` share a module name,
    and collect/ is on sys.path for common.py — so a plain `import budget` resolves to
    the collector, not the matcher."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_b = _load("enrich_budget", os.path.join(HERE, "budget.py"))
band, similarity = _b.band, _b.similarity


def run(year):
    schemes = json.load(open(os.path.join(ROOT, "data", "checks.json"),
                             encoding="utf-8"))["schemes"]
    central = [s for s in schemes if s.get("level_value") == "central"]

    ob_path = os.path.join(ROOT, "data", "outcome", f"{year}.json")
    if not os.path.exists(ob_path):
        raise SystemExit(f"no parsed Outcome Budget at {ob_path} — run parse/outcome.py")
    ob = json.load(open(ob_path, encoding="utf-8"))
    frames = ob["schemes"]

    matched, counts = {}, {"strong": 0, "likely": 0, "weak": 0, "none": 0}
    for s in central:
        best, score = None, 0.0
        for f in frames:
            sc = similarity(s["name"], f["name"])
            if sc > score:
                best, score = f, sc
        b = band(score)
        counts[b or "none"] += 1
        if b in ("strong", "likely") and (best["outputs"] or best["outcomes"]):
            matched[s["slug"]] = {
                "framework_name": best["name"],
                "scheme_name": s["name"],
                "match_score": round(score, 3),
                "confidence": b,
                "classification": best["classification"],
                "outlay_cr": best.get("outlay_cr"),
                "page": best["page"],
                "outputs": best["outputs"][:12],
                "outcomes": best["outcomes"][:12],
                "cycle": ob["cycle"],
                "source": f"Outcome Budget {ob['cycle']}, "
                          f"Output Outcome Monitoring Framework, p.{best['page']}",
            }

    write_json("data/enrichment/outcome.json", {
        "cycle": ob["cycle"],
        "built": utcnow(),
        "source": ob["source"],
        "central_schemes": len(central),
        "frameworks_in_document": len(frames),
        "counts": counts,
        "caveat": ("Targets only, never achievements. The framework states what each "
                   "scheme promises to deliver in the coming year; no source publishes "
                   "a delivered-versus-promised figure for any central scheme. A scheme "
                   "absent here has no published target of any kind, which is a fact about the "
                   "Outcome Budget's scope, not about the scheme."),
        "schemes": matched,
    })
    return counts, len(central), len(frames)


def main():
    ap = argparse.ArgumentParser(description="Join schemes to Outcome Budget targets.")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    counts, n, m = run(a.year)
    print(f"Outcome Budget join · {n} central schemes vs {m} frameworks")
    for k in ("strong", "likely", "weak", "none"):
        print(f"    {k:<8}{counts[k]:>5}   {100*counts[k]/n:>5.1f}%")
    carried = counts["strong"] + counts["likely"]
    print(f"\n  carried into the site: {carried}")
    print(f"  central schemes with no published framework at all: "
          f"{n - m} of {n} ({100*(n-m)/n:.0f}%)")


if __name__ == "__main__":
    main()
