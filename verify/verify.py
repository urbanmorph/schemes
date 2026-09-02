"""
Verifier — decides whether a snapshot is fit to publish. Deterministic, no agent.

PLAN.md §8. The failure this exists to catch is not a missing file; it is a *present*
file with the wrong bytes. A 401 body, a Cloudflare interstitial, an empty facet array,
or page 34 of 48 are all valid writes. R2 or git give durability; nothing gives
completeness. This does.

It deliberately re-counts from the archive rather than trusting the collector's own
manifest — a collector that miscounts would otherwise certify itself.

Assertions, all fail-loud:
  1. details in the archive == summary.total from the census response
  2. list pages written == pages expected
  3. no archived body matches a known error shape
  4. (annual) parsed budget line items sum to the PDF's printed Grand Total

A failing run is still archived and is still committed — but marked INCOMPLETE, and
parse/ must refuse to build /changes against it. An incomplete snapshot does not merely
lose data, it manufactures false events: one dropped page reads as "100 schemes
removed this month", which is a headline-shaped artifact and entirely our own bug.

Exits non-zero when the snapshot is not COMPLETE, so GitHub Actions emails a human.
The alarm has to reach you without you going to look for it — see PLAN.md §9.
"""

import argparse
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, looks_like_error, read_json, utcnow, today, write_json  # noqa: E402

STALE_DAYS = 40      # monthly cadence + a week of slack


class Truncated(Exception):
    """The gzip stream ends without its end-of-stream marker."""


def _lines(path):
    """Yield raw lines from a .ndjson.gz, surviving a truncated stream.

    A collector killed mid-write leaves a gzip with no end-of-stream marker, and naive
    iteration raises EOFError partway through. That must not crash the verifier: a
    truncated archive is precisely the "present file holding the wrong bytes" case this
    module exists to catch, and it has to be reported as a failed assertion rather than a
    stack trace. So the readable prefix is yielded, then Truncated is raised so the caller
    can record how much survived and mark the snapshot INCOMPLETE.
    """
    with gzip.open(path, "rb") as fh:
        while True:
            try:
                line = fh.readline()
            except (EOFError, OSError) as exc:
                raise Truncated(str(exc)) from exc
            if not line:
                return
            line = line.strip()
            if line:
                yield line


def verify_myscheme(date):
    d = os.path.join(ROOT, "archive", "myscheme", date)
    checks, out = [], {"date": date, "source": "myscheme"}

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return ok

    if not os.path.isdir(d):
        check("archive present", False, f"no archive at archive/myscheme/{date}")
        return out, checks

    man = read_json(f"archive/myscheme/{date}/_manifest.json", {})
    out["key_event"] = man.get("key_event")
    out["api_version"] = man.get("api_version")

    # --- expected total, read from the census response itself, not the manifest
    census_path = os.path.join(d, "census.json.gz")
    expected = None
    if os.path.exists(census_path):
        with gzip.open(census_path, "rb") as fh:
            raw = fh.read()
        if looks_like_error(raw):
            check("census body is data", False, f"census matches an error shape: {looks_like_error(raw)}")
        else:
            try:
                expected = json.loads(raw)["data"]["summary"]["total"]
            except Exception as e:
                check("census parses", False, str(e)[:120])
    else:
        check("census present", False, "census.json.gz missing")

    out["expected_total"] = expected

    # --- independent recount from the archive
    details_path = os.path.join(d, "details.ndjson.gz")
    list_path = os.path.join(d, "list.ndjson.gz")

    n_details, bad_details, truncated = 0, 0, []
    if os.path.exists(details_path):
        try:
            for line in _lines(details_path):
                n_details += 1
                if looks_like_error(line):
                    bad_details += 1
        except Truncated as exc:
            truncated.append(f"details.ndjson.gz: {exc}")
    # Recount the list too: pages, the records inside them, and distinct slugs. The
    # completeness question is about *records* (does the crawl account for every row the
    # census promised); duplicate slugs are a separate fact, reported not failed.
    n_pages, bad_pages, n_records = 0, 0, 0
    slugs = set()
    if os.path.exists(list_path):
        try:
            for line in _lines(list_path):
                n_pages += 1
                if looks_like_error(line):
                    bad_pages += 1
                    continue
                try:
                    for it in json.loads(line)["data"]["hits"]["items"]:
                        n_records += 1
                        f_ = it.get("fields", it)
                        if f_.get("slug"):
                            slugs.add(f_["slug"])
                except Exception:
                    bad_pages += 1
        except Truncated as exc:
            truncated.append(f"list.ndjson.gz: {exc}")

    out["records_parsed"] = n_details
    out["list_records"] = n_records
    out["unique_slugs"] = len(slugs)
    out["duplicate_slugs"] = n_records - len(slugs)
    out["pages_written"] = n_pages
    out["pages_expected"] = man.get("pages_expected")
    out["sort"] = man.get("sort")

    # A smoke run is honestly incomplete — say so rather than pretending otherwise.
    limited = man.get("limited_to")
    if limited:
        out["limited_to"] = limited
        check("full census attempted", False,
              f"run was limited to {limited} details — smoke test, not a publishable snapshot")

    if expected is not None:
        # The list crawl must account for every record the census promised. This is the
        # assertion that catches paging drift: under an unstable sort it read 4,735
        # against 4,772 and would have let 37 schemes vanish from the archive unnoticed.
        check("list records == census total", n_records == expected,
              f"{n_records} records vs {expected} expected"
              + ("" if n_records == expected else
                 f"  ({expected - n_records} unaccounted — check the sort is stable)"))

    if not limited:
        check("a detail for every slug", n_details == len(slugs),
              f"{n_details} details vs {len(slugs)} distinct slugs"
              + ("" if n_details == len(slugs) else f"  ({len(slugs) - n_details} missing)"))

    if man.get("pages_expected"):
        check("all list pages written", n_pages == man["pages_expected"],
              f"{n_pages}/{man['pages_expected']} pages")

    # Reported, never fatal: one slug carrying two records is the register's business,
    # not a collection failure — but it does mean the published total counts records
    # rather than schemes, which anyone quoting 4,772 should know.
    if out["duplicate_slugs"]:
        print(f"  note: {out['duplicate_slugs']} duplicate slug(s) — "
              f"{expected} records describe {len(slugs)} distinct schemes")

    check("no error-shaped bodies", bad_details == 0 and bad_pages == 0,
          f"{bad_details} detail + {bad_pages} list bodies match a throttle/WAF shape")

    # A truncated stream means the collector died mid-write. The readable prefix is still
    # good data and is kept — but the snapshot is not a census and must not be published.
    check("archive streams are complete", not truncated,
          "; ".join(truncated) if truncated else "all streams end cleanly")
    out["truncated"] = truncated

    return out, checks


def verify_budget():
    """Carry forward the Budget reconciliation as a standing check.

    parse/budget.py does the reconciling and fails on its own when a statement does not
    add up — it runs annually, so it cannot be part of the monthly sequence. This
    surfaces its last verdict so a broken Budget parse stays visible on every monthly
    status instead of being forgotten between Februaries.

    The check catches silent row loss. Measured 2026-08-30: pdftotext drops items 28 and
    31 from Statement 4A entirely — 84 rows where the document numbers 86 — with no
    error raised. The printed Grand Total is the only independent witness the document
    offers, so the parse is held to it.
    """
    summary = read_json("data/budget/_totals.json")
    if not summary:
        return []
    checks = []
    for stmt, v in summary.items():
        parsed, printed = v.get("parsed_sum"), v.get("printed_grand_total")
        if parsed is not None and printed is not None:
            checks.append({
                "check": f"budget {stmt} money", "gating": False,
                "ok": abs(parsed - printed) < 0.02,   # crore, two decimals in the source
                "detail": f"parsed {parsed:,.2f} vs printed {printed:,.2f} cr"})
        if v.get("highest_index"):
            missing = v.get("missing_indices") or []
            checks.append({
                "check": f"budget {stmt} rows", "gating": False, "ok": not missing,
                "detail": f"{v.get('rows')} of {v['highest_index']} numbered rows"
                          + (f" — extraction lost {missing}" if missing else "")})
    return checks


def main():
    ap = argparse.ArgumentParser(description="Verify a snapshot and write status.json.")
    ap.add_argument("--date", default=today())
    args = ap.parse_args()

    prev = read_json("status.json", {})
    ms, checks = verify_myscheme(args.date)
    checks += verify_budget()

    # Only gating checks decide whether *this month's* snapshot is publishable. The
    # Budget statements are parsed annually and their defects are long-lived: a known row
    # gap in Statement 4A must stay visible every month without marking an otherwise
    # sound myScheme snapshot INCOMPLETE and blocking the change feed for a year.
    failed = [c for c in checks if not c["ok"]]
    gating_failed = [c for c in failed if c.get("gating", True)]
    advisory = [c for c in failed if not c.get("gating", True)]
    verdict = "COMPLETE" if not gating_failed else "INCOMPLETE"

    snapshots = len(glob.glob(os.path.join(ROOT, "archive", "myscheme", "*", "_manifest.json")))

    # When the BYTES were fetched, read from the snapshot's own manifest, not when this
    # verification ran. The site labels it "Last complete collection" and was showing the
    # verify time, which is the same day on a normal run and days out whenever an archived
    # snapshot is re-verified. A register whose subject is stale government data should not
    # be careless about the age of its own.
    collected = None
    try:
        mp = os.path.join(ROOT, "archive", "myscheme", args.date, "_manifest.json")
        collected = json.load(open(mp, encoding="utf-8")).get("finished")
    except Exception:
        pass

    status = {
        "last_run": utcnow(),
        "collection_finished": collected,
        "last_complete_run": utcnow() if verdict == "COMPLETE" else prev.get("last_complete_run"),
        "verdict": verdict,
        "snapshot": args.date,
        "snapshots": snapshots,
        "expected_total": ms.get("expected_total"),
        "records_parsed": ms.get("records_parsed"),
        "pages_expected": ms.get("pages_expected"),
        "pages_written": ms.get("pages_written"),
        "api_version": ms.get("api_version"),
        "key_event": ms.get("key_event"),
        "checks": checks,
        "standing_issues": [c["check"] for c in advisory],
        # ops-dashboard reads this directly; each entry is (what, where, why)
        "attention": [[c["check"], args.date, c["detail"]] for c in failed],
    }
    write_json("status.json", status)

    print(f"snapshot {args.date} — {verdict}")
    for c in checks:
        tag = "PASS" if c["ok"] else ("FAIL" if c.get("gating", True) else "warn")
        print(f"  {tag}  {c['check']:<28} {c['detail']}")

    if advisory:
        print(f"\n{len(advisory)} standing issue(s) carried forward — real defects, but "
              f"in annually-parsed sources, so they do not gate this month's snapshot.")

    if gating_failed:
        print(f"\n{len(gating_failed)} gating assertion(s) failed. Snapshot archived and "
              f"marked INCOMPLETE; parse/ must not diff against it.")
        raise SystemExit(1)
    print("\nsnapshot is complete and fit to publish.")


if __name__ == "__main__":
    main()
