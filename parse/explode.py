"""
Derive the browsable current-state tree from an archived snapshot.

AGENT-EDITABLE. This is the half of the pipeline the repair agent may change
(PLAN.md §7), because everything it does is replayable: point it at any archived date
and it rebuilds that month from bytes that are already on disk. If the upstream shape
changes and this file has to be rewritten, the entire history can be re-derived under
the new rules, and old-parse vs new-parse diffed to see exactly what moved.

Nothing here may fetch. If this file needs the network, the split has been broken.

Writes:
    data/myscheme/census.json           totals and facets
    data/myscheme/schemes/<slug>.json   one record per scheme, overwritten each month

One file per scheme, overwritten rather than date-keyed, is what makes /changes free:
git already stores the history, so `git log -p data/myscheme/schemes/pm-kisan.json` is
the change feed for that scheme and `git show <sha>:<path>` is any past snapshot. Keys
are sorted and the JSON is indented so those diffs are line-wise and readable.
"""

import argparse
import gzip
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, read_json, write_json, today  # noqa: E402

SAFE = set("abcdefghijklmnopqrstuvwxyz0123456789-_")


def safe_name(slug):
    """Slugs come from an external system; keep them from escaping the directory."""
    s = "".join(c if c in SAFE else "-" for c in slug.lower())[:120]
    return s or "unnamed"


def record_of(body):
    """Pull the scheme record out of an API envelope, tolerating shape drift."""
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict):
            # Some responses nest the record under an `en` language key.
            if len(data) == 1 and isinstance(next(iter(data.values())), dict):
                only = next(iter(data.values()))
                if "schemeName" in only or "schemeShortTitle" in only:
                    return only
            return data
    return body


def explode(date):
    src = os.path.join(ROOT, "archive", "myscheme", date)
    if not os.path.isdir(src):
        raise SystemExit(f"no archive at archive/myscheme/{date}")

    status = read_json("status.json", {})
    if status.get("snapshot") == date and status.get("verdict") != "COMPLETE":
        raise SystemExit(
            f"snapshot {date} is {status.get('verdict')} — refusing to build from it.\n"
            "An incomplete snapshot does not just lose records, it manufactures false\n"
            "change events downstream. See PLAN.md §8."
        )

    # --- census
    census_path = os.path.join(src, "census.json.gz")
    if os.path.exists(census_path):
        with gzip.open(census_path, "rb") as fh:
            doc = json.loads(fh.read())
        d = doc["data"]
        write_json("data/myscheme/census.json", {
            "snapshot": date,
            "total": d["summary"]["total"],
            "facets": {f["identifier"]: {e["label"]: e["count"] for e in f["entries"]}
                       for f in d.get("facets", [])},
        })

    # --- list-only fields. beneficiaryState is returned by the search endpoint and NOT
    # by the per-scheme detail endpoint, so building records from details alone dropped
    # the state dimension entirely — a register of Indian schemes with no idea which
    # state each belongs to. Merge it back in from the same snapshot's list pages.
    listed = {}
    lp = os.path.join(src, "list.ndjson.gz")
    if os.path.exists(lp):
        with gzip.open(lp, "rb") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    items = json.loads(line)["data"]["hits"]["items"]
                except Exception:
                    continue
                for it in items:
                    f = it.get("fields", it)
                    if f.get("slug"):
                        listed[f["slug"]] = f

    # --- schemes. Rebuild the directory so a scheme that vanished upstream disappears
    # from the tree, and shows up as a deletion in the diff rather than lingering.
    out_dir = os.path.join(ROOT, "data", "myscheme", "schemes")
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    n, skipped = 0, 0
    details = os.path.join(src, "details.ndjson.gz")
    with gzip.open(details, "rb") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                rec = record_of(row.get("body"))
            except Exception:
                skipped += 1
                continue
            if not isinstance(rec, dict):
                skipped += 1
                continue
            rec["_slug"] = row.get("slug")
            rec["_snapshot"] = date
            lf = listed.get(row.get("slug"))
            if lf:
                rec["_list"] = {k: lf[k] for k in
                                ("beneficiaryState", "schemeCategory", "tags",
                                 "schemeFor", "level", "nodalMinistryName")
                                if k in lf}
            write_json(f"data/myscheme/schemes/{safe_name(row['slug'])}.json", rec)
            n += 1

    return n, skipped


def main():
    ap = argparse.ArgumentParser(description="Rebuild data/ from an archived snapshot.")
    ap.add_argument("--date", default=today())
    args = ap.parse_args()
    n, skipped = explode(args.date)
    print(f"built data/myscheme from snapshot {args.date}: {n} schemes"
          + (f", {skipped} unparseable" if skipped else ""))


if __name__ == "__main__":
    main()
