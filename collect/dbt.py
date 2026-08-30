"""
DBT Bharat collector — raw HTML only, no field extraction.

FROZEN CODE. Read PLAN.md §7 before editing.

37 requests: one central scheme list, 36 state/UT dashboards. Cheap enough that there is
no reason to defer it — and the counts here cannot be backfilled any more than
myScheme's can, which is the whole argument for collecting before you need it.

    archive/dbt/D/central-list.html.gz
    archive/dbt/D/state-<code>.html.gz
    archive/dbt/D/_manifest.json

State codes are LGD codes, base64-encoded in the `scode` query parameter. 1–24 and
27–38: 25 and 26 were retired when Dadra & Nagar Haveli and Daman & Diu merged.

The per-state count is server-rendered in `<span id="no_of_schemes">`, so it is present
in the HTML and needs no browser. Extracting it is parse/'s job, not this file's.

A caveat that must travel with every number this collects: a state's DBT count reflects
how much that state has onboarded onto the DBT platform, not how many schemes it runs.
Kerala 73 against Karnataka 501 is an onboarding artefact, not a policy fact.
"""

import argparse
import base64
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://dbtbharat.gov.in"
STATE_CODES = list(range(1, 25)) + list(range(27, 39))   # 25/26 retired on the DNHDD merger


def scode(n):
    return base64.b64encode(str(n).encode()).decode()


def collect(date, pace=1.0):
    out_dir = os.path.join(ROOT, "archive", "dbt", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "dbt", "started": utcnow(), "base": BASE,
           "status_histogram": {}, "errors": [], "states_expected": len(STATE_CODES)}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    def save(name, body):
        with gzip.open(os.path.join(out_dir, name), "wb") as fh:
            fh.write(body)

    central = fetch(f"{BASE}/central-scheme/list", pace=pace)
    note(central.status)
    bad = looks_like_error(central.body) if central.ok else f"http {central.status}"
    if bad:
        man["errors"].append({"stage": "central", "why": str(bad)})
    else:
        save("central-list.html.gz", central.body)
        man["central_bytes"] = len(central.body)
    print(f"  central list: {central.status} ({len(central.body):,} bytes)")

    got = 0
    for code in STATE_CODES:
        r = fetch(f"{BASE}/state-ut/dashboard?scode={scode(code)}", pace=pace)
        note(r.status)
        bad = looks_like_error(r.body) if r.ok else f"http {r.status}"
        if bad:
            man["errors"].append({"stage": "state", "code": code, "why": str(bad)})
            continue
        save(f"state-{code:02d}.html.gz", r.body)
        got += 1

    man.update(states_written=got, finished=utcnow(), error_count=len(man["errors"]))
    print(f"  states: {got}/{len(STATE_CODES)}")
    write_json(f"archive/dbt/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(description="Collect a DBT Bharat snapshot (raw HTML).")
    ap.add_argument("--date", default=today())
    ap.add_argument("--pace", type=float, default=1.0)
    args = ap.parse_args()
    print(f"DBT Bharat snapshot {args.date}")
    collect(args.date, args.pace)


if __name__ == "__main__":
    main()
