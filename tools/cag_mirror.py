"""
Keep a local copy of every CAG audit report PDF, newest first.

LOCAL ONLY. Writes local/cag/, which is in .gitignore, and feeds nothing that is
published. It is not a collector: collect/cag.py and the archive are unchanged.

Why it exists. Between the 2026-09-02 and 2026-10-17 crawls the CAG took down 63
reports, 49 of them tabled that year; their pages answer 404, and nine of the PDFs had
gone from every host by the time anyone looked. The index tells this register that a
report existed. Only a copy of the file keeps what it said.

    python3 tools/cag_mirror.py                 every report in the latest complete crawl
    python3 tools/cag_mirror.py --limit 50      the 50 newest not yet held
    python3 tools/cag_mirror.py --deadline-min 120

Each file is written whole or not at all (.part, then rename) and recorded in
local/cag/manifest.json with its SHA-256, which is saved every 25 files and on any exit.
A rerun skips every file whose bytes still match their checksum, so a stopped run
continues where it stopped and a finished one fetches nothing. It stops by itself when
the disk has less than --min-free-gb left.
"""
import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "local", "cag")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PDF_LINK = re.compile(r'href="(https://[^"]+/download_audit_report/[^"]+?\.pdf)"', re.I)


def log(*a):
    print(*a, flush=True)


def fetch(url):
    """GET only: government hosts answer HEAD with errors (docs/MAINTAINING.md)."""
    url = urllib.parse.quote(html.unescape(url), safe=":/%?=&")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as ex:
        return ex.code, b"", url
    except Exception as ex:  # noqa: BLE001  a network error is a result to record, not a crash
        return f"error: {ex.__class__.__name__}", b"", url


def candidates(archived, host):
    """The archived file's path on the CAG's current CDN host. The CAG moves its files
    between hosts and keeps the path from /uploads/ on, so this is one request where
    asking the report page first would be two."""
    if not archived:
        return []
    path = urllib.parse.urlsplit(archived).path
    return [host + path[path.index("/uploads/"):]] if "/uploads/" in path else []


def current_host(report_page):
    m = PDF_LINK.search(report_page)
    if not m:
        return None
    u = urllib.parse.urlsplit(html.unescape(m.group(1)))
    return f"{u.scheme}://{u.netloc}"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_manifest(out, man):
    p = os.path.join(out, "manifest.json")
    with open(p + ".part", "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False, sort_keys=True)
    os.replace(p + ".part", p)


def mirror(reports, out, host, fetch=fetch, sleep=time.sleep, free_gb=None, min_free_gb=20,
           pace=1.0, limit=None, deadline=None):
    os.makedirs(out, exist_ok=True)
    free_gb = free_gb or (lambda p: shutil.disk_usage(p).free / 2 ** 30)
    mp = os.path.join(out, "manifest.json")
    man = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    todo = []
    for r in sorted(reports, key=lambda r: -r["id"]):
        rec, path = man.get(str(r["id"])) or {}, os.path.join(out, f"{r['id']}.pdf")
        if rec.get("sha256") and os.path.exists(path) and sha(path) == rec["sha256"]:
            continue
        todo.append(r)
    held = len(reports) - len(todo)
    if limit:
        todo = todo[:limit]
    log(f"cag mirror: {len(reports):,} reports, {held:,} held, {len(todo):,} to fetch -> {out}")

    got = bytes_ = 0
    stopped = None
    t0 = time.time()
    try:
        for n, r in enumerate(todo, 1):
            if free_gb(out) < min_free_gb:
                stopped = "disk"
                log(f"stopping: less than {min_free_gb} GB free")
                break
            if deadline and time.time() > deadline:
                stopped = "deadline"
                log("stopping: time limit reached")
                break
            rec = {"id": r["id"], "title": r.get("title"), "government": r.get("government"),
                   "tabled": r.get("tabled"), "detail_url": r.get("detail_url"),
                   "archived_url": r.get("pdf_url")}
            urls = candidates(r.get("pdf_url"), host)
            body, tried = b"", []
            for attempt in range(2):
                for u in urls:
                    sleep(pace)
                    code, body, final = fetch(u)
                    tried.append([u, code])
                    if code == 200 and body[:5] == b"%PDF-":
                        rec["url"] = final
                        break
                    body = b""
                if body or attempt or not r.get("detail_url"):
                    break
                # The report page links whichever file is current, under whatever host.
                sleep(pace)
                code, page, _ = fetch(r["detail_url"])
                rec["detail_status"] = code
                m = PDF_LINK.search(page.decode("utf-8", "replace")) if code == 200 else None
                urls = [html.unescape(m.group(1))] if m else []
            rec["tried"], rec["checked"] = tried, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if body:
                path = os.path.join(out, f"{r['id']}.pdf")
                with open(path + ".part", "wb") as fh:
                    fh.write(body)
                os.replace(path + ".part", path)
                rec.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                got += 1
                bytes_ += len(body)
            man[str(r["id"])] = rec
            if n % 25 == 0:
                save_manifest(out, man)
            if n % 10 == 0 or n == len(todo):
                rate = n / max(time.time() - t0, 1)
                log(f"  {n:,}/{len(todo):,}  saved {got:,} ({bytes_ / 2 ** 30:.2f} GB)  "
                    f"{rate * 60:.0f}/min  eta {(len(todo) - n) / rate / 60:.0f} min  "
                    f"free {free_gb(out):.0f} GB")
    finally:
        save_manifest(out, man)
    missing = sum(1 for v in man.values() if not v.get("sha256"))
    log(f"done: saved {got:,} this run; manifest holds {len(man) - missing:,} files and "
        f"{missing:,} reports with no fetchable PDF")
    return {"saved": got, "bytes": bytes_, "stopped": stopped, "missing": missing}


def latest_reports():
    """Every report in the newest complete CAG crawl, read with parse/cag.py."""
    sys.path.insert(0, os.path.join(ROOT, "collect"))
    spec = importlib.util.spec_from_file_location("parse_cag", os.path.join(ROOT, "parse", "cag.py"))
    cag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cag)
    dates = []
    for d in sorted(os.listdir(os.path.join(ROOT, "archive", "cag"))):
        mp = os.path.join(ROOT, "archive", "cag", d, "_manifest.json")
        if os.path.exists(mp) and json.load(open(mp)).get("complete"):
            dates.append(d)
    return cag.read(dates[-1])[0], dates[-1]


def main():
    ap = argparse.ArgumentParser(description="Keep a local copy of every CAG audit report PDF.")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--pace", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--min-free-gb", type=float, default=20)
    ap.add_argument("--deadline-min", type=float)
    a = ap.parse_args()
    reports, crawl = latest_reports()
    with_pdf = [r for r in reports if r.get("pdf_url")]
    log(f"crawl {crawl}: {len(with_pdf):,} of {len(reports):,} reports link a PDF")
    # The current host, read off the newest report's page rather than written here: the
    # CAG has already changed it once since the October crawl.
    newest = max(with_pdf, key=lambda r: r["id"])
    code, page, _ = fetch(newest["detail_url"])
    host = current_host(page.decode("utf-8", "replace")) if code == 200 else None
    if not host:
        sys.exit(f"could not read the current PDF host from {newest['detail_url']} ({code})")
    log(f"current PDF host {host}")
    deadline = time.time() + a.deadline_min * 60 if a.deadline_min else None
    r = mirror(with_pdf, OUT, host, pace=a.pace, limit=a.limit, deadline=deadline,
               min_free_gb=a.min_free_gb)
    sys.exit(75 if r["stopped"] else 0)


if __name__ == "__main__":
    main()
