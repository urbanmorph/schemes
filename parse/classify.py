"""
Classify Budget line items: citizen-facing scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ and archive/. Never fetches.

    data/classification.json

The union registry found 570 Budget lines with money and no myScheme entry. Presenting
that as "570 hidden welfare schemes" would be false: Statement 4B carries "Road Works",
"Rolling Stock", "Manufacturing Suspense" and "Aircraft and Aero Engines" — real
expenditure that no citizen applies to and that a scheme portal is right to omit. But
it also carries Samagra Shiksha and Crop Insurance, which are exactly what a scheme
portal is for. Something has to separate them, and it should not be a judgement call
made once by hand and never checked.

So: independent signals, each computable, combined by a transparent additive score with
the arithmetic published per line. Same rule as the quality checks — if a reader cannot
recompute the verdict from the evidence shown, it is not publishable.

VALIDATION, and its honest limit. The classifier is scored against myScheme membership
as ground truth for "citizen-facing". That proxy is imperfect in one direction and the
direction matters: myScheme omitting a scheme is the very thing this project documents,
so a line the classifier calls a scheme and myScheme lacks may well be the classifier
being right. Recall measured this way is therefore a floor, and PRECISION is the metric
worth reading — of the lines this calls schemes, how many does myScheme agree are
schemes.
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
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# Absence and membership questions use the generous matcher; see parse/match.py.
_m = _load("scheme_match", os.path.join(HERE, "match.py"))
probably_same = _m.probably_same

# Words that name a benefit delivered to a person.
SCHEME_WORDS = {
    "yojana", "yojna", "scheme", "mission", "abhiyan", "scholarship", "fellowship",
    "pension", "bima", "insurance", "awas", "poshan", "shiksha", "kalyan", "samman",
    "nidhi", "vikas", "welfare", "livelihood", "employment", "skill", "training",
    "stipend", "assistance", "grant", "subsidy", "beneficiaries", "empowerment",
    "swasthya", "arogya", "anganwadi", "midday", "nutrition", "housing", "sanitation",
}

# Words that name an asset, an input, or an accounting head rather than a benefit.
HEAD_WORDS = {
    "works", "rolling", "stock", "suspense", "manufacturing", "equipments", "equipment",
    "machinery", "plant", "track", "renewals", "doubling", "gauge", "electrification",
    "signalling", "workshops", "aircraft", "aero", "engines", "vessels", "fleet",
    "amenities", "buildings", "roads", "highways", "bridges", "acquisition",
    "depreciation", "reserve", "capital", "investment", "loans", "advances",
    "establishment", "secretariat", "administration", "census", "survey",
}

# Demands whose expenditure is overwhelmingly capital or establishment. Sourced from the
# Outcome Budget's own contents table rather than guessed.
INFRA_MINISTRY = re.compile(
    r"railway|defence|road transport|highway|shipping|ports|civil aviation|"
    r"telecommunication|atomic energy|space|earth science|external affairs|home affairs",
    re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def demand_ministry_map():
    """demand number -> ministry, from the Outcome Budget's contents table."""
    p = os.path.join(ROOT, "archive", "budget", "2026", "outcome.pdf.gz")
    if not os.path.exists(p):
        return {}
    import shutil, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "o.pdf")
        with gzip.open(p, "rb") as s, open(pdf, "wb") as d:
            shutil.copyfileobj(s, d)
        txt = os.path.join(td, "o.txt")
        subprocess.run(["pdftotext", "-layout", pdf, txt], check=True,
                       capture_output=True, timeout=300)
        t = open(txt, encoding="utf-8", errors="replace").read()
    out = {}
    for m, d, n in re.findall(
            r"^\s*(?:\d{1,3}\.)?\s*(M/o[^\n]{4,70}?)\s{2,}(.{2,60}?)\s{2,}(\d{1,3})\s+\d{1,3}\s*$",
            t, re.M):
        out[int(n)] = m.strip()
    for m, n in re.findall(r"^\s*(Ministry of [^\n]{4,70}?)\s{3,}Demand No\.\s*(\d{1,3})\s*$",
                           t, re.M | re.I):
        out.setdefault(int(n), m.strip())
    return out


def dbt_names(date):
    p = os.path.join(ROOT, "archive", "dbt", date, "central-list.html.gz")
    if not os.path.exists(p):
        return []
    h = gzip.open(p, "rb").read().decode("utf-8", "replace")
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", li)).strip()
            for ol in re.findall(r"<ol[^>]*>(.*?)</ol>", h, re.S | re.I)
            for li in re.findall(r"<li[^>]*>(.*?)</li>", ol, re.S | re.I)
            if re.sub(r"<[^>]+>", "", li).strip()]


def score_line(name, statement, demand_no, in_dbt, in_outcome, ministry):
    """Additive, auditable. Every component is returned so the total can be rechecked."""
    tk = tokens(name)
    ev = []
    total = 0

    if in_dbt:
        total += 3
        ev.append(("+3", "named in DBT Bharat's central list, so money reaches individuals"))
    if in_outcome:
        total += 1
        ev.append(("+1", "has an Output-Outcome framework"))
    if statement == "stat4a":
        total += 2
        ev.append(("+2", "Centrally Sponsored, delivered through states to citizens"))

    hits = sorted(tk & SCHEME_WORDS)
    if hits:
        total += 2
        ev.append(("+2", "benefit words in the name: " + ", ".join(hits[:4])))
    heads = sorted(tk & HEAD_WORDS)
    if heads:
        total -= 3
        ev.append(("-3", "asset or accounting words in the name: " + ", ".join(heads[:4])))
    if ministry and INFRA_MINISTRY.search(ministry):
        total -= 2
        ev.append(("-2", f"capital-heavy demand: {ministry}"))

    return total, ev


def run(snapshot, year, threshold):
    reg = json.load(open(os.path.join(ROOT, "data", "registry.json"), encoding="utf-8"))
    dbt = dbt_names(snapshot)
    dmap = demand_ministry_map()

    obp = os.path.join(ROOT, "data", "outcome", f"{year}.json")
    ob = json.load(open(obp, encoding="utf-8"))["schemes"] if os.path.exists(obp) else []
    ob_names = [f["name"] for f in ob]

    lines = []
    for en in reg["entries"]:
        b = en["sources"].get("budget")
        if not b:
            continue
        name = b.get("name") or en["name"]
        in_dbt = any(probably_same(name, d)[0] for d in dbt)
        in_ob = "outcome" in en["sources"] or any(probably_same(name, o)[0] for o in ob_names)
        ministry = dmap.get(b.get("demand_no"))
        total, ev = score_line(name, b.get("statement"), b.get("demand_no"),
                               in_dbt, in_ob, ministry)
        lines.append({
            "name": name, "statement": b.get("statement"), "demand_no": b.get("demand_no"),
            "ministry": ministry, "be_cr": b.get("be_cr"),
            "in_myscheme": "myscheme" in en["sources"],
            "in_dbt": in_dbt, "in_outcome": in_ob,
            "score": total, "evidence": ev,
            "verdict": "scheme" if total >= threshold else "budget head",
        })

    # Validation against myScheme membership. See the module docstring for why precision
    # is the metric that means something here and recall is only a floor.
    tp = sum(1 for x in lines if x["verdict"] == "scheme" and x["in_myscheme"])
    fp = sum(1 for x in lines if x["verdict"] == "scheme" and not x["in_myscheme"])
    fn = sum(1 for x in lines if x["verdict"] != "scheme" and x["in_myscheme"])
    tn = sum(1 for x in lines if x["verdict"] != "scheme" and not x["in_myscheme"])
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    # Threshold sweep, published so the operating point is a choice a reader can see
    # rather than a number chosen by feel.
    sweep = []
    for t in range(0, 7):
        a = sum(1 for x in lines if x["score"] >= t and x["in_myscheme"])
        b = sum(1 for x in lines if x["score"] >= t and not x["in_myscheme"])
        c = sum(1 for x in lines if x["score"] < t and x["in_myscheme"])
        pr = a / (a + b) if a + b else 0
        rc = a / (a + c) if a + c else 0
        sweep.append({"threshold": t, "precision": round(pr, 3),
                      "recall_floor": round(rc, 3),
                      "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0})

    schemes = [x for x in lines if x["verdict"] == "scheme"]
    # The PUBLISHED absence list uses a stricter bar than the general classification.
    # Naming a scheme as missing from a government portal is an accusation; being wrong
    # about it is worse than omitting a true case, so it runs at the high-precision end
    # of the sweep rather than the F1-optimal one.
    PUBLISH_AT = 4
    unlisted = sorted((x for x in lines
                       if x["score"] >= PUBLISH_AT and not x["in_myscheme"]
                       and isinstance(x["be_cr"], (int, float))),
                      key=lambda x: -(x["be_cr"] or 0))

    out = {
        "snapshot": snapshot, "cycle": f"{year}-{str(year+1)[2:]}", "built": utcnow(),
        "threshold": threshold,
        "lines": len(lines),
        "classified_scheme": len(schemes),
        "classified_head": len(lines) - len(schemes),
        "validation": {
            "ground_truth": "myScheme membership",
            "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "precision": round(precision, 3), "recall_floor": round(recall, 3),
            "note": ("Recall is a floor, not a measurement: a line called a scheme that "
                     "myScheme lacks may be the classifier being right and the portal "
                     "being incomplete, which is the thing this project documents. "
                     "Precision is the metric worth reading."),
        },
        "publish_threshold": 4,
        "threshold_sweep": sweep,
        "unlisted_schemes": unlisted[:300],
        "unlisted_schemes_total": len(unlisted),
        "unlisted_schemes_cr": round(sum(x["be_cr"] or 0 for x in unlisted), 2),
        "scoring": {
            "in DBT central list": 3, "Centrally Sponsored (4A)": 2,
            "benefit words in name": 2, "has outcome framework": 1,
            "asset/accounting words in name": -3, "capital-heavy demand": -2,
        },
        "all_lines": lines,
    }
    write_json("data/classification.json", out)
    return out


def main():
    ap = argparse.ArgumentParser(description="Classify budget lines as scheme or head.")
    ap.add_argument("--snapshot", default="2026-08-30")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--threshold", type=int, default=2)
    a = ap.parse_args()
    o = run(a.snapshot, a.year, a.threshold)
    v = o["validation"]
    print(f"budget lines classified: {o['lines']}")
    print(f"  scheme       {o['classified_scheme']:>5}")
    print(f"  budget head  {o['classified_head']:>5}\n")
    print(f"validated against myScheme membership (threshold {a.threshold}):")
    print(f"  precision      {v['precision']:.1%}   of lines called schemes, "
          f"myScheme agrees on {v['true_positive']}/{v['true_positive']+v['false_positive']}")
    print(f"  recall (floor) {v['recall_floor']:.1%}   {v['false_negative']} myScheme "
          f"schemes scored below threshold")
    print(f"\nfunded schemes absent from myScheme: {o['unlisted_schemes_total']}, "
          f"Rs {o['unlisted_schemes_cr']:,.0f} cr")
    for x in o["unlisted_schemes"][:10]:
        print(f"   Rs {x['be_cr']:>11,.0f} cr  score {x['score']:>2}  {x['name'][:52]}")


if __name__ == "__main__":
    main()
