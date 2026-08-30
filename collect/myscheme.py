"""
myScheme collector — raw bytes only, no field extraction.

FROZEN CODE. Read PLAN.md §7 before editing. The repair agent may not touch this file.

Writes, for run date D:

    archive/myscheme/D/census.json.gz     the size=1 response: summary.total + all facets
    archive/myscheme/D/list.ndjson.gz     48 list-page bodies, one JSON object per line
    archive/myscheme/D/details.ndjson.gz  one detail body per scheme, one per line
    archive/myscheme/D/_manifest.json     what was attempted, what arrived, and hashes

Nothing downstream of this file may run before all of the above is on disk. The
manifest is the only thing this collector *interprets*, and only to count.

Two facts about the API, both measured on 2026-08-30, that this file exists to respect:

  size caps at 100. 200, 500 and 1000 all return `data: null`. A full list is 48 pages.

  401 means rate-limited, not rotated. The key in the JS bundle is byte-identical
  before and after a 401, and the original key works again about three minutes later.
  So a 401 is never on its own evidence of rotation — resolve_key() has to compare.
"""

import argparse
import gzip
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (ROOT, fetch, looks_like_error, utcnow, today,  # noqa: E402
                    write_json)

API = "https://api.myscheme.gov.in"
SITE = "https://www.myscheme.gov.in/"
PAGE = 100                      # hard API cap, not a tuning knob
KEY_FALLBACK = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"

# Paging over 48 requests is not atomic, and the API's default sort is relevance
# (`multiple_sort`), which is not stable between requests. Measured 2026-08-30 with the
# default sort: 4,772 records returned but only 4,735 distinct slugs — 37 duplicates, 36
# of them straddling a page boundary. Items shifting across boundaries are returned
# twice, which means an equal number are never returned at all. Re-running under
# `schemename-asc` cut it to 1. A stable sort key is the difference between a census and
# an approximation, so this is not a preference.
SORT = "schemename-asc"


def headers(key):
    return {"x-api-key": key, "Referer": SITE, "Accept": "application/json"}


# ------------------------------------------------------------------ resume support

def _readable_slugs(path):
    """Slugs already archived, reading only as far as the stream is intact.

    A process killed mid-write leaves a gzip with no end-of-stream marker. The prefix is
    still valid data — it was fetched and written before the kill — so it is kept and
    resumed from, not discarded. Only whole, parseable lines count.
    """
    if not os.path.exists(path):
        return set()
    seen = set()
    try:
        with gzip.open(path, "rb") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.add(json.loads(line)["slug"])
                except Exception:
                    continue          # a half-written final line; stop counting it
    except (EOFError, OSError):
        pass                          # truncated stream: keep whatever parsed
    return seen


def _rewrite_clean(path, keep):
    """Rewrite the archive containing only whole records, so it can be appended to.

    Appending to a truncated gzip would produce a file no reader can get past. Rewriting
    the intact prefix first is what makes resume safe.
    """
    rows = []
    try:
        with gzip.open(path, "rb") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    if json.loads(line)["slug"] in keep:
                        rows.append(line)
                except Exception:
                    continue
    except (EOFError, OSError):
        pass
    with gzip.open(path, "wb") as fh:
        for r in rows:
            fh.write(r + b"\n")


# ------------------------------------------------------------------ key handling

def extract_key_from_bundle():
    """Pull the client key out of the site's own JS. Returns (key, api_versions)."""
    home = fetch(SITE, timeout=40)
    if not home.ok:
        return None, {}
    html = home.body.decode("utf-8", "replace")
    chunks = re.findall(r"https://cdn\.myscheme\.in/_next/static/chunks/[^\"']+\.js", html)
    key, versions = None, set()
    for url in dict.fromkeys(chunks):
        js = fetch(url, timeout=30)
        if not js.ok:
            continue
        if key is None:
            m = re.search(rb'x-api-key"\s*:\s*"([A-Za-z0-9]{20,})"', js.body)
            if m:
                key = m.group(1).decode()
        versions.update(v.decode() for v in
                        re.findall(rb"api\.myscheme\.gov\.in/([a-z]+/v\d+)", js.body))
    return key, sorted(versions)


def resolve_key(key):
    """Confirm `key` works. On 401, decide rate-limit vs rotation by COMPARING.

    Returns (key, event) where event is None, 'throttled' or 'rotated'. Only 'rotated'
    is worth alerting a human about; 'throttled' is ordinary and must not page anyone.
    """
    probe = f"{API}/search/v6/schemes?lang=en&q=%5B%5D&keyword=&sort=&from=0&size=1"
    r = fetch(probe, headers=headers(key), retries=3)
    if r.ok and not looks_like_error(r.body):
        return key, None

    found, versions = extract_key_from_bundle()
    if found and found != key:
        print(f"  key rotated: {key[:8]}… -> {found[:8]}…  (versions: {versions})")
        return found, "rotated"

    # Same key, or the bundle could not be read. Either way this is a throttle, not a
    # rotation. Wait it out rather than reporting a key event that did not happen.
    print("  401 with an unchanged key — throttled, backing off 180s")
    time.sleep(180)
    return key, "throttled"


# ------------------------------------------------------------------ collection

def collect(out_dir, key, pace, limit=None, rel_manifest=None):
    os.makedirs(out_dir, exist_ok=True)
    man = {
        "source": "myscheme",
        "started": utcnow(),
        "api_base": API,
        "api_version": "search/v6 + schemes/v6",
        "page_size": PAGE,
        "key_fingerprint": f"{key[:4]}…{key[-4:]}",
        "key_event": None,
        "status_histogram": {},
        "errors": [],
    }

    def note(status):
        k = str(status)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    # ---- 1. census. summary.total is the checksum every later assertion leans on.
    census = fetch(f"{API}/search/v6/schemes?lang=en&q=%5B%5D&keyword=&sort=&from=0&size=1",
                   headers=headers(key), pace=pace)
    note(census.status)
    if not census.ok or looks_like_error(census.body):
        man.update(finished=utcnow(), fatal="census fetch failed")
        write_json(os.path.join(out_dir, "_manifest.json").replace(ROOT + os.sep, ""), man)
        raise SystemExit("census fetch failed — nothing else can be trusted, aborting")

    with gzip.open(os.path.join(out_dir, "census.json.gz"), "wb") as fh:
        fh.write(census.body)

    doc = census.json()
    total = doc["data"]["summary"]["total"]
    man["expected_total"] = total
    man["census_sha256"] = census.sha256
    pages = (total + PAGE - 1) // PAGE
    man["pages_expected"] = pages
    print(f"  census: {total} schemes, {pages} pages of {PAGE}")

    # ---- 2. list pages -> slugs
    slugs, pages_written, list_records = [], 0, 0
    with gzip.open(os.path.join(out_dir, "list.ndjson.gz"), "wb") as fh:
        for i in range(pages):
            frm = i * PAGE
            r = fetch(f"{API}/search/v6/schemes?lang=en&q=%5B%5D&keyword=&sort={SORT}"
                      f"&from={frm}&size={PAGE}", headers=headers(key), pace=pace)
            note(r.status)
            bad = looks_like_error(r.body) if r.ok else f"http {r.status}"
            if bad:
                man["errors"].append({"stage": "list", "from": frm, "why": str(bad)})
                continue
            fh.write(r.body + b"\n")
            pages_written += 1
            try:
                items = r.json()["data"]["hits"]["items"]
            except Exception as e:
                man["errors"].append({"stage": "list-shape", "from": frm, "why": str(e)[:120]})
                continue
            for it in items:
                list_records += 1
                f_ = it.get("fields", it)
                if f_.get("slug"):
                    slugs.append(f_["slug"])
            if i % 10 == 0:
                print(f"    list {i + 1}/{pages}  records={list_records}")

    man["pages_written"] = pages_written
    man["list_records"] = list_records
    man["slugs_missing"] = list_records - len(slugs)
    # Duplicates are reported, never silently collapsed. Under a stable sort a residual
    # duplicate is a fact about the register (one slug, two records), not a paging
    # artifact — and it means the published total counts more records than schemes.
    seen = {}
    for s in slugs:
        seen[s] = seen.get(s, 0) + 1
    man["duplicate_slugs"] = sorted(s for s, c in seen.items() if c > 1)
    slugs = list(dict.fromkeys(slugs))
    man["unique_slugs"] = len(slugs)
    man["sort"] = SORT
    print(f"  list complete: {pages_written}/{pages} pages, {list_records} records, "
          f"{len(slugs)} unique slugs, {len(man['duplicate_slugs'])} duplicated")

    if limit:
        slugs = slugs[:limit]
        man["limited_to"] = limit

    # ---- 3. details. The rubric's fields live only here — the list endpoint carries
    #         12 fields and none of eligibility/benefits/applicationProcess/references.
    #
    # Resumable, because a full census is ~4,800 paced requests and a process that dies at
    # request 2,883 should not send the first 2,883 again. Resuming reuses the slug list
    # from this run's own list pages and re-fetches nothing already on disk.
    #
    # It does mean a resumed snapshot's fetches span a longer wall-clock window, so the
    # manifest records each segment. That is a real caveat and it is written down rather
    # than hidden — but it does not change collection *semantics*: same endpoint, same
    # stable sort, same slug set. What a record means is identical either way.
    total_slugs = len(slugs)
    details_path = os.path.join(out_dir, "details.ndjson.gz")
    done = _readable_slugs(details_path)
    if done:
        _rewrite_clean(details_path, done)
        man["resumed_from"] = len(done)
        man.setdefault("segments", []).append({"resumed_at": utcnow(), "had": len(done)})
        slugs = [s for s in slugs if s not in done]
        print(f"  resuming: {len(done)} details already archived, {len(slugs)} to go")

    got = len(done)
    with gzip.open(details_path, "ab") as fh:
        for n, slug in enumerate(slugs, 1):
            r = fetch(f"{API}/schemes/v6/public/schemes?slug={slug}&lang=en",
                      headers=headers(key), pace=pace)
            note(r.status)
            bad = looks_like_error(r.body) if r.ok else f"http {r.status}"
            if bad:
                man["errors"].append({"stage": "detail", "slug": slug, "why": str(bad)})
                continue
            # One line per record, slug carried alongside so the parser never has to
            # guess which response belongs to which scheme.
            fh.write(json.dumps({"slug": slug, "body": r.json()},
                                ensure_ascii=False, sort_keys=True).encode() + b"\n")
            got += 1
            if n % 200 == 0:
                print(f"    detail {n}/{len(slugs)}  ok={got}/{total_slugs}")
                # Flush a progress manifest. A run killed at request 2,883 previously
                # left the manifest describing an entirely different earlier run, so the
                # verifier compared new bytes against stale bookkeeping. The manifest
                # must never be further behind than the archive it describes.
                fh.flush()
                man.update(details_expected=total_slugs, details_written=got,
                           finished=None, in_progress=True,
                           error_count=len(man["errors"]))
                write_json(rel_manifest, dict(man, errors=man["errors"][:50]))

    man["details_expected"] = total_slugs
    man["details_written"] = got
    man["finished"] = utcnow()
    man["in_progress"] = False
    man["error_count"] = len(man["errors"])
    man["errors"] = man["errors"][:50]      # keep the manifest diffable
    return man


def main():
    ap = argparse.ArgumentParser(description="Collect a myScheme snapshot (raw bytes only).")
    ap.add_argument("--date", default=today(), help="archive date key (default: today UTC)")
    ap.add_argument("--pace", type=float, default=0.7,
                    help="seconds between requests (default 0.7; the API 401s under ~15 rapid calls)")
    ap.add_argument("--limit", type=int, help="cap detail fetches — smoke tests only, never in CI")
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, "archive", "myscheme", args.date)
    rel = os.path.join("archive", "myscheme", args.date, "_manifest.json")

    key = os.environ.get("MYSCHEME_KEY") or KEY_FALLBACK
    print(f"myScheme snapshot {args.date}")
    key, event = resolve_key(key)

    started = time.time()
    man = collect(out_dir, key, args.pace, args.limit, rel)
    man["key_event"] = event
    man["duration_s"] = round(time.time() - started)
    write_json(rel, man)

    print(f"  wrote {rel}  ({man['duration_s']}s)")
    print(f"  details {man['details_written']}/{man['details_expected']} · "
          f"pages {man['pages_written']}/{man['pages_expected']} · "
          f"errors {man['error_count']}")
    # Deliberately exits 0 even on a partial run: the archive write succeeded, and it is
    # verify/verify.py that decides whether this snapshot is fit to publish.


if __name__ == "__main__":
    main()
