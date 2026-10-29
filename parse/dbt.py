"""
Derive per-state DBT scheme counts from archived DBT Bharat HTML.

AGENT-EDITABLE (PLAN.md §7). Reads only from archive/. Never fetches.

Writes data/dbt/states.json.

The count is server-rendered in `<span id="no_of_schemes">`, so no browser is needed.
Two patterns are tried: the id, which is precise, then the visible label, which is the
fallback if the markup is restyled. If both fail for a state that previously had a
count, that is a parser regression and should surface as a diff, not a silent zero —
so a state that cannot be read is recorded as null, never as 0.

Caveat carried in the output and repeated on every page that uses it: a state's DBT
count reflects how much that state has onboarded onto the DBT platform, not how many
schemes it runs.
"""

import argparse
import glob
import gzip
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, write_json, today  # noqa: E402

# LGD state code -> name. 25/26 retired on the Dadra & Nagar Haveli / Daman & Diu merger.
STATES = {
    1: "Jammu and Kashmir", 2: "Himachal Pradesh", 3: "Punjab", 4: "Chandigarh",
    5: "Uttarakhand", 6: "Haryana", 7: "Delhi", 8: "Rajasthan", 9: "Uttar Pradesh",
    10: "Bihar", 11: "Sikkim", 12: "Arunachal Pradesh", 13: "Nagaland", 14: "Manipur",
    15: "Mizoram", 16: "Tripura", 17: "Meghalaya", 18: "Assam", 19: "West Bengal",
    20: "Jharkhand", 21: "Odisha", 22: "Chhattisgarh", 23: "Madhya Pradesh",
    24: "Gujarat", 27: "Maharashtra", 28: "Andhra Pradesh", 29: "Karnataka",
    30: "Goa", 31: "Lakshadweep", 32: "Kerala", 33: "Tamil Nadu", 34: "Puducherry",
    35: "Andaman and Nicobar Islands", 36: "Telangana",
    37: "Dadra & Nagar Haveli and Daman & Diu", 38: "Ladakh",
}

BY_ID = re.compile(rb'id="no_of_schemes"[^>]*>\s*([\d,]+)', re.I)
BY_LABEL = re.compile(rb"NO\.\s*OF\s*SCHEMES.{0,300}?([\d,]+)", re.I | re.S)


def count_from(html):
    for rx in (BY_ID, BY_LABEL):
        m = rx.search(html)
        if m:
            try:
                return int(m.group(1).replace(b",", b""))
            except ValueError:
                continue
    return None


def central_names(html):
    """Scheme names on DBT Bharat's central list. The page is one <ol> per ministry, not
    a table: 56 lists, 320 <li>, which is the count DBT Bharat states for itself. It was
    counted as <tr> rows, of which it has none, so the count was always empty."""
    out = []
    for block in re.findall(r"<ol[^>]*>(.*?)</ol>", html, re.S | re.I):
        for li in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S | re.I):
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", li)).strip()
            if name:
                out.append(name)
    return out


def read(date):
    """One snapshot's scheme count per state (None where unreadable) and its central rows."""
    src = os.path.join(ROOT, "archive", "dbt", date)
    if not os.path.isdir(src):
        raise SystemExit(f"no archive at archive/dbt/{date}")

    states = {}
    for path in sorted(glob.glob(os.path.join(src, "state-*.html.gz"))):
        code = int(os.path.basename(path).split("-")[1].split(".")[0])
        with gzip.open(path, "rb") as fh:
            states[STATES.get(code, f"code {code}")] = count_from(fh.read())

    central = None
    cpath = os.path.join(src, "central-list.html.gz")
    if os.path.exists(cpath):
        with gzip.open(cpath, "rb") as fh:
            central = len(central_names(fh.read().decode("utf-8", "replace"))) or None
    return states, central


def parse(date):
    states, central = read(date)
    unreadable = [name for name, n in states.items() if n is None]
    out = {
        "snapshot": date,
        "states": states,
        "state_total": sum(v for v in states.values() if v is not None),
        "states_read": sum(1 for v in states.values() if v is not None),
        "states_unreadable": unreadable,
        "central_rows": central,
        "caveat": ("A state's DBT count reflects how much that state has onboarded onto "
                   "the DBT platform, not how many schemes it runs. These are not "
                   "comparable to myScheme's per-state figures without that context."),
    }
    write_json("data/dbt/states.json", out)
    return out


def selftest():
    page = ('<h3>Ministry A</h3><ol class="x"><li><a href="#">PM  Kisan</a></li>'
            '<li>Scheme <b>Two</b></li><li> </li></ol>'
            '<ol><li>Scheme Three</li></ol><table><tr><td>not a scheme</td></tr></table>')
    bad = 0
    for label, got, want in [
            ("names come from the <ol> lists, tags and spacing removed",
             central_names(page), ["PM Kisan", "Scheme Two", "Scheme Three"]),
            ("a page with no list has no names", central_names("<table></table>"), [])]:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": want {want} got {got}"))
    return bad


def main():
    ap = argparse.ArgumentParser(description="Parse archived DBT Bharat HTML.")
    ap.add_argument("--date", default=today())
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        print("dbt self-test")
        sys.exit(1 if selftest() else 0)
    out = parse(args.date)
    print(f"DBT {args.date}: {out['states_read']}/36 states read, "
          f"total {out['state_total']:,} state schemes")
    if out["states_unreadable"]:
        print(f"  unreadable: {', '.join(out['states_unreadable'])}")
    for k in ("Karnataka", "Gujarat", "Kerala", "Uttar Pradesh"):
        print(f"  {k:<16} {out['states'].get(k)}")


if __name__ == "__main__":
    main()
