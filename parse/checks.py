"""
Tier-1 documentation checks — deterministic, network-free, per scheme.

AGENT-EDITABLE (PLAN.md §7). Reads data/, writes data/checks.json. Never fetches.

These are the checks that need no network and therefore have no false-positive rate:
either the field is there or it is not. PLAN.md §5 ships these before anything
network-dependent, because /quality is a page we have to defend and every network flag
enlarges its surface. Link reachability (Tier 2) and cross-source joins (Tier 3) come
later, with their own error bars.

Every check is phrased as a statement about the *record*, never about the scheme. The
distinction has to survive being screenshotted without its caption (PLAN.md §1) — which
is also why there is no letter grade here, only a count of checks passed.

URLs are read from the structured fields only — `references[].url` and
`applicationProcess[].url`. Harvesting URLs out of rich-text or markdown produces
phantom defects: a link followed by a full stop in prose reads as a malformed URL when
it is nothing of the kind.
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import date as _date
from urllib.parse import urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, write_json  # noqa: E402

RUPEE = "₹"


def _md(x):
    return x if isinstance(x, str) else ""


def structured_urls(en):
    """Only fields whose declared purpose is to hold a URL."""
    out = []
    for r in en.get("schemeContent", {}).get("references", []) or []:
        if isinstance(r, dict) and r.get("url") is not None:
            out.append(("reference", r.get("title") or "", r["url"]))
    for a in en.get("applicationProcess", []) or []:
        if isinstance(a, dict) and a.get("url") is not None:
            out.append(("application", a.get("mode") or "", a["url"]))
    return out


def url_defect(u):
    """Why this stored value is not a usable URL. None if it is fine."""
    if not isinstance(u, str) or not u.strip():
        return "empty"
    if u != u.strip():
        return "leading or trailing whitespace"
    if "**" in u or "\n" in u or "\t" in u:
        return "markup characters in the field"
    if " " in u:
        return "unencoded space"
    try:
        p = urlsplit(u)
    except Exception:
        return "does not parse as a URL"
    if p.scheme not in ("http", "https"):
        return f"scheme is {p.scheme or 'missing'}"
    if not p.netloc or "." not in p.netloc:
        return "no valid host"
    return None


def check_scheme(rec):
    en = rec.get("en", {}) or {}
    basic = en.get("basicDetails", {}) or {}
    content = en.get("schemeContent", {}) or {}
    elig = en.get("eligibilityCriteria", {}) or {}

    name = basic.get("schemeName") or ""
    brief = _md(content.get("briefDescription"))
    benefits = _md(content.get("benefits_md"))
    eligibility = _md(elig.get("eligibilityDescription_md"))
    agency = basic.get("implementingAgency")
    open_date = basic.get("schemeOpenDate")
    close_date = basic.get("schemeCloseDate")
    urls = structured_urls(en)
    modes = [(a.get("mode") or "").lower()
             for a in en.get("applicationProcess", []) or [] if isinstance(a, dict)]

    bad_urls = [(kind, label, u, why) for kind, label, u in urls
                if (why := url_defect(u)) is not None]

    expired = None
    if close_date:
        try:
            expired = _date.fromisoformat(str(close_date)[:10]) < _date.today()
        except ValueError:
            expired = None

    checks = [
        ("eligibility_documented", len(eligibility) >= 80,
         f"{len(eligibility)} characters" if eligibility else "field empty"),

        ("benefit_quantified",
         bool(benefits) and (any(c.isdigit() for c in benefits) or RUPEE in benefits),
         "amount or quantity stated" if benefits else "field empty"),

        ("description_substantive",
         len(brief) >= 120 and brief.strip().lower() != name.strip().lower(),
         f"{len(brief)} characters" if brief else "field empty"),

        ("implementing_agency_named", bool(agency and str(agency).strip()),
         "named" if agency else "field absent from the record"),

        ("application_path_published",
         any(u for _, _, u in urls if _ == "application") or
         any("offline" in m for m in modes),
         "URL published" if urls else "no URL and no offline mode declared"),

        ("start_date_recorded", bool(open_date), open_date or "not published"),

        ("end_date_recorded", bool(close_date),
         close_date or "no end date — indefinite by omission"),

        ("stored_urls_well_formed", not bad_urls,
         "all parse" if not bad_urls else
         f"{len(bad_urls)} of {len(urls)}: " + "; ".join(f"{w}" for *_, w in bad_urls[:3])),

        ("not_expired_while_listed", expired is not True,
         "closed but still listed" if expired else (close_date or "no end date")),
    ]

    passed = sum(1 for _, ok, _ in checks if ok)
    return {
        "slug": rec.get("slug") or rec.get("_slug"),
        "name": name,
        "short": basic.get("schemeShortTitle") or "",
        "level": (basic.get("level") or {}).get("label"),
        "type": (basic.get("schemeType") or {}).get("label"),
        "ministry": (basic.get("nodalMinistryName") or {}).get("label"),
        "state": basic.get("beneficiaryState"),
        "dbt": basic.get("dbtScheme"),
        "open_date": open_date,
        "close_date": close_date,
        "url_count": len(urls),
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": i, "ok": ok, "detail": d} for i, ok, d in checks],
        "bad_urls": [{"field": k, "label": l, "url": u, "why": w} for k, l, u, w in bad_urls],
    }


def run(snapshot=None):
    files = sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")))
    if not files:
        raise SystemExit("no data/myscheme/schemes — run parse/explode.py first")

    results, tally = [], {}
    for path in files:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        r = check_scheme(rec)
        results.append(r)
        for c in r["checks"]:
            t = tally.setdefault(c["id"], {"pass": 0, "fail": 0})
            t["pass" if c["ok"] else "fail"] += 1

    n = len(results)
    summary = {
        "snapshot": snapshot,
        "schemes": n,
        "checks_per_scheme": results[0]["total"] if results else 0,
        "distribution": {str(k): sum(1 for r in results if r["passed"] == k)
                         for k in range(0, (results[0]["total"] if results else 0) + 1)},
        "by_check": {k: {**v, "fail_pct": round(100 * v["fail"] / n, 1)}
                     for k, v in sorted(tally.items())},
    }
    write_json("data/checks.json", {"summary": summary, "schemes": results})
    return summary


def main():
    ap = argparse.ArgumentParser(description="Run Tier-1 documentation checks.")
    ap.add_argument("--snapshot")
    args = ap.parse_args()
    s = run(args.snapshot)
    print(f"{s['schemes']:,} schemes · {s['checks_per_scheme']} checks each\n")
    print(f"  {'check':<30}{'fails':>8}{'of total':>11}")
    for k, v in s["by_check"].items():
        print(f"  {k:<30}{v['fail']:>8}{v['fail_pct']:>10}%")


if __name__ == "__main__":
    main()
