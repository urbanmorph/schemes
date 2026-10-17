"""
What the monthly run has already done, read from the archive's own manifests.

ORCHESTRATION (PLAN.md §7): reads archive/ and run.json, never fetches, never writes the
archive. run.sh asks it before each collector so that a second run does no work the first
one finished, and so that a run stopped at its time limit continues where it stopped.

    python3 progress.py month-date            the snapshot date this month's run uses
    python3 progress.py finished SOURCE DATE  exit 0 if SOURCE is finished for DATE
    python3 progress.py held STATE CYCLE      exit 0 if STATE's budget book for CYCLE is archived
    python3 progress.py run-ok DATE           exit 0 if the whole run for DATE finished clean
    python3 progress.py --self-test

A run that stops part way through the month must not start a second snapshot the next
day. That would leave two half-collected dates, neither of which verifies. So the month's
snapshot date is the one already started this month, if any, and today otherwise.
"""

import glob
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def month_date(root=ROOT, today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    started = sorted(os.path.basename(p) for p in
                     glob.glob(os.path.join(root, "archive", "myscheme", today[:7] + "-*"))
                     if os.path.isdir(p) and os.path.basename(p) <= today)
    return started[-1] if started else today


def finished(source, date, root=ROOT):
    """True when re-running SOURCE for DATE would fetch nothing new."""
    if source == "myscheme":
        # The collector rewrites its manifest while it runs, so existing is not finishing.
        m = _read(os.path.join(root, "archive", "myscheme", date, "_manifest.json")) or {}
        return bool(m.get("finished") and not m.get("in_progress") and not m.get("fatal")
                    and m.get("details_expected")
                    and m.get("details_written") == m.get("details_expected")
                    and m.get("pages_written") == m.get("pages_expected"))
    if source == "dbt":
        # Written only at the end, so its presence is a finished walk; errors mean re-walk.
        m = _read(os.path.join(root, "archive", "dbt", date, "_manifest.json"))
        return bool(m) and m.get("error_count") == 0
    if source == "cag":
        # Collected on its own date, once a month. Any complete walk this month will do.
        for p in glob.glob(os.path.join(root, "archive", "cag", date[:7] + "-*", "_manifest.json")):
            if (_read(p) or {}).get("complete"):
                return True
        return False
    raise SystemExit(f"unknown source {source!r}")


def _cycle(s):
    """'2026-2027' and '2026-27' are one cycle; the collectors write both."""
    m = re.fullmatch(r"(\d{4})-(?:\d{2})?(\d{2})", (s or "").strip())
    return f"{m.group(1)}-{m.group(2)}" if m else None


def held(state, cycle, root=ROOT):
    """Is a state's budget book for CYCLE already archived?

    The question run.sh asks before re-fetching a state, and it used to ask it of one
    field, `cycle`, spelled exactly "2026-27". Nine of sixteen state collectors do not
    write that: Maharashtra and West Bengal write "2026-2027", four record the cycle they
    asked for as `cycle_wanted`, and Odisha and Jharkhand record none, because their cycle
    is not in any URL and is read off each book. So every month re-downloaded those nine
    states' books, an hour or more of PDFs that had not changed, to commit them again.

    In order: a recorded cycle decides; then the cycle a clean walk asked for; and only a
    manifest with neither field is read for the cycle printed in its books' titles.
    """
    want = _cycle(cycle)
    for p in glob.glob(os.path.join(root, "archive", state, "*", "_manifest.json")):
        m = _read(p) or {}
        if m.get("cycle"):
            ok = _cycle(m["cycle"]) == want
        elif m.get("cycle_wanted"):
            ok = _cycle(m["cycle_wanted"]) == want and not m.get("errors")
        else:
            y = want[:4]
            # URLs carry it percent-encoded ("Budget%202026-27.pdf"), where the %20 puts
            # a digit right before the year, so decode first and bound on digits.
            text = urllib.parse.unquote(json.dumps(m))
            ok = re.search(rf"(?<!\d){y}-(?:{y[:2]})?{want[5:]}(?!\d)", text) is not None
        if ok:
            return True
    return False


def run_ok(date, root=ROOT):
    r = _read(os.path.join(root, "run.json")) or {}
    return r.get("date") == date and r.get("ok") is True


def selftest():
    import tempfile
    bad = 0

    def check(label, got, want):
        nonlocal bad
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f"  (want {want!r}, got {got!r})"))

    def put(root, rel, obj):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)

    r = tempfile.mkdtemp()
    check("no snapshot this month: today", month_date(r, "2026-10-03"), "2026-10-03")
    put(r, "archive/myscheme/2026-09-03/_manifest.json", {})
    check("last month's snapshot is not reused", month_date(r, "2026-10-03"), "2026-10-03")
    put(r, "archive/myscheme/2026-10-03/_manifest.json", {"in_progress": True})
    check("a snapshot started this month is continued", month_date(r, "2026-10-05"), "2026-10-03")

    full = {"finished": "x", "in_progress": False, "details_expected": 3, "details_written": 3,
            "pages_expected": 1, "pages_written": 1}
    check("myScheme mid-run is not done", finished("myscheme", "2026-10-03", r), False)
    put(r, "archive/myscheme/2026-10-03/_manifest.json", dict(full, details_written=2))
    check("myScheme finished short is not done", finished("myscheme", "2026-10-03", r), False)
    put(r, "archive/myscheme/2026-10-03/_manifest.json", full)
    check("myScheme with every detail is done", finished("myscheme", "2026-10-03", r), True)

    check("DBT with no manifest is not done", finished("dbt", "2026-10-03", r), False)
    put(r, "archive/dbt/2026-10-03/_manifest.json", {"error_count": 1})
    check("DBT with errors is not done", finished("dbt", "2026-10-03", r), False)
    put(r, "archive/dbt/2026-10-03/_manifest.json", {"error_count": 0})
    check("DBT clean is done", finished("dbt", "2026-10-03", r), True)

    put(r, "archive/cag/2026-09-02/_manifest.json", {"complete": True})
    check("last month's CAG walk does not count", finished("cag", "2026-10-03", r), False)
    os.makedirs(os.path.join(r, "archive/cag/2026-10-03"))
    check("a CAG walk with no manifest is not done", finished("cag", "2026-10-03", r), False)
    put(r, "archive/cag/2026-10-04/_manifest.json", {"complete": True})
    check("any complete CAG walk this month is done", finished("cag", "2026-10-03", r), True)

    check("a state never collected is not held", held("kerala", "2026-27", r), False)
    put(r, "archive/kerala/2026-09-02/_manifest.json", {"cycle": "2026-27"})
    check("cycle recorded as 2026-27 is held", held("kerala", "2026-27", r), True)
    check("last cycle's book does not hold the next one", held("kerala", "2027-28", r), False)
    put(r, "archive/maharashtra/2026-09-02/_manifest.json", {"cycle": "2026-2027"})
    check("cycle spelled 2026-2027 is the same cycle", held("maharashtra", "2026-27", r), True)
    put(r, "archive/delhi/2026-09-03/_manifest.json", {"cycle_wanted": "2026-27", "errors": []})
    check("a clean walk for the cycle it wanted is held", held("delhi", "2026-27", r), True)
    put(r, "archive/tripura/2026-09-03/_manifest.json", {"cycle_wanted": "2026-27", "errors": [{"x": 1}]})
    check("a walk with errors is not", held("tripura", "2026-27", r), False)
    put(r, "archive/odisha/2026-09-02/_manifest.json",
        {"books": {"a": {"what": "Demand for Grants 2026-27, Agriculture"}}, "errors": []})
    check("no cycle field, but the books name it", held("odisha", "2026-27", r), True)
    check("...and only that cycle", held("odisha", "2027-28", r), False)
    put(r, "archive/jharkhand/2026-09-03/_manifest.json",
        {"books": {"a": {"url": "https://x/Child%20Budget%202026-27.pdf"}}})
    check("a cycle inside a percent-encoded URL counts", held("jharkhand", "2026-27", r), True)
    put(r, "archive/punjab/2026-09-03/_manifest.json", {"cycle": "2025-26", "note": "2026-27 RE"})
    check("a recorded cycle is not overridden by a mention", held("punjab", "2026-27", r), False)

    check("no run.json: run needed", run_ok("2026-10-03", r), False)
    put(r, "run.json", {"date": "2026-10-03", "ok": False})
    check("a run that stopped is run again", run_ok("2026-10-03", r), False)
    put(r, "run.json", {"date": "2026-10-03", "ok": True})
    check("a clean run is not repeated", run_ok("2026-10-03", r), True)
    check("a clean run last month does not cover this one", run_ok("2026-11-03", r), False)
    return bad


def main(argv):
    if argv[:1] == ["--self-test"]:
        print("progress self-test")
        return 1 if selftest() else 0
    if argv[:1] == ["month-date"]:
        print(month_date())
        return 0
    if argv[:1] == ["finished"] and len(argv) == 3:
        return 0 if finished(argv[1], argv[2]) else 1
    if argv[:1] == ["held"] and len(argv) == 3:
        return 0 if held(argv[1], argv[2]) else 1
    if argv[:1] == ["run-ok"] and len(argv) == 2:
        return 0 if run_ok(argv[1]) else 1
    print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
