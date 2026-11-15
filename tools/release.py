#!/usr/bin/env python3
"""Cut this month's release of the register, and publish every release into the site.

A release is the month's schemes.csv under a code that never changes or gets reused:
schemes-register-<year>.<month>, from the snapshot's date. It lives in releases/<code>/, is
committed with the snapshot, and is served unchanged at /releases/<code>/ ever after, so a
code someone cited still fetches the bytes they used. The SHA-256 in its manifest proves it.

    python3 tools/release.py           # after site/build.py; run.sh does this

Idempotent: the same CSV under an existing code does nothing. A different CSV under an
existing code is refused (exit 1), because a release that changes is not a release. Only a
COMPLETE snapshot is released; an INCOMPLETE one would publish a false month.

No Zenodo (deferred) and no DOI: the code, the checksum and this site are the citation. The
manifest names the w3id.org address the code would resolve through once it is registered.
"""
import csv
import hashlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "schemes-register-"
SITE = "https://india-schemes.pages.dev"
W3ID = "https://w3id.org/india-schemes/register/"     # proposed; not registered yet


class ReleaseChanged(Exception):
    """A release's CSV differs from what was cut under that code."""


def release_code(snapshot):
    """The code for a snapshot date: 2026-11-03 -> schemes-register-2026.11."""
    year, month = snapshot.split("-")[:2]
    return f"{PREFIX}{year}.{month}"


def _ids(text):
    return {r["slug"] for r in csv.DictReader(io.StringIO(text))}


def _codes(root):
    d = os.path.join(root, "releases")
    if not os.path.isdir(d):
        return []
    return sorted((c for c in os.listdir(d) if c.startswith(PREFIX)
                   and os.path.isfile(os.path.join(d, c, "manifest.json"))), reverse=True)


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def make_release(root=ROOT):
    """Cut the release for status.json's snapshot from site/_out/schemes.csv.

    Returns (code, made): (None, False) for a snapshot that is not COMPLETE, (code, False)
    when that release already holds these bytes. Raises ReleaseChanged when it holds others."""
    with open(os.path.join(root, "status.json"), encoding="utf-8") as fh:
        status = json.load(fh)
    if status.get("verdict") != "COMPLETE" or not status.get("snapshot"):
        return None, False
    code = release_code(status["snapshot"])
    with open(os.path.join(root, "site", "_out", "schemes.csv"), encoding="utf-8", newline="") as fh:
        text = fh.read()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    folder = os.path.join(root, "releases", code)
    if os.path.isfile(os.path.join(folder, "manifest.json")):
        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as fh:
            held = json.load(fh)["sha256"]
        if held == digest:
            return code, False
        raise ReleaseChanged(
            f"{code} is already released with SHA-256 {held}, and this build's schemes.csv is "
            f"{digest}. A release never changes: if the data needs correcting, say so in the next "
            "month's release.")

    earlier = [c for c in _codes(root) if c < code]
    previous = earlier[0] if earlier else None
    ids = _ids(text)
    manifest = {
        "code": code,
        "snapshot": status["snapshot"],
        "file": "schemes.csv",
        "sha256": digest,
        "bytes": len(text.encode("utf-8")),
        "rows": len(ids),
        "licence": "CC BY 4.0 (the derived data); each source keeps its own terms",
        "attribution": "The Schemes Register (github.com/urbanmorph/schemes), from myScheme, DBT Bharat, "
                       "the Union Budget and Outcome Budget, CAG audit reports and state budget books",
        "url": f"{SITE}/releases#{code}",
        "w3id_proposed": W3ID + code[len(PREFIX):],
        "id_note": "Ids are the slug in each scheme's page URL. A scheme keeps its id while it stays in the "
                   "register; a state budget row whose duplicate disappears can lose its suffix.",
        "previous": previous,
    }
    if previous:
        with open(os.path.join(root, "releases", previous, "schemes.csv"), encoding="utf-8", newline="") as fh:
            before = _ids(fh.read())
        manifest["ids_added"] = len(ids - before)
        manifest["ids_removed"] = len(before - ids)
        n_add, n_rem = manifest["ids_added"], manifest["ids_removed"]
        change = (f"{n_add} id{'s' if n_add != 1 else ''} added and {n_rem} "
                  f"id{'s' if n_rem != 1 else ''} removed since {previous}.")
    else:
        change = "The first release under a release code."

    os.makedirs(folder, exist_ok=True)
    _write(os.path.join(folder, "schemes.csv"), text)
    _write(os.path.join(folder, "manifest.json"), json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    _write(os.path.join(folder, "CHANGES.md"),
           f"# {code}\n\nThe register as of the {status['snapshot']} snapshot: {len(ids):,} schemes.\n\n"
           f"{change}\n\nSHA-256 of schemes.csv: `{digest}`\n\n"
           "What changed in each scheme's record is in the repository's history "
           "(`git log -p data/`) and on the site's /changes page.\n")
    return code, True


def publish(root, out):
    """Copy every release into the built site and write releases/index.json, newest first."""
    dest = os.path.join(out, "releases")
    os.makedirs(dest, exist_ok=True)
    listing = []
    for code in _codes(root):
        src = os.path.join(root, "releases", code)
        shutil.copytree(src, os.path.join(dest, code), dirs_exist_ok=True)
        with open(os.path.join(src, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        listing.append({k: m.get(k) for k in ("code", "snapshot", "sha256", "rows", "url", "w3id_proposed")}
                       | {"csv": f"/releases/{code}/schemes.csv"})
    with open(os.path.join(dest, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"latest": listing[0]["code"] if listing else None, "releases": listing},
                  fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def main():
    try:
        code, made = make_release(ROOT)
    except ReleaseChanged as e:
        print(f"release refused: {e}", file=sys.stderr, flush=True)
        return 1
    if code is None:
        print("no release: this snapshot is not COMPLETE", flush=True)
    else:
        print(f"{code}: {'released' if made else 'already released, unchanged'}", flush=True)
    publish(ROOT, os.path.join(ROOT, "site", "_out"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
