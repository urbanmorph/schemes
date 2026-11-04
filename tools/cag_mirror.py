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
    python3 tools/cag_mirror.py --verify        re-hash every held file first

Each file is written whole or not at all (.part, then rename) and recorded in
local/cag/manifest.json with its SHA-256, which is saved every 25 files and on any exit.
A rerun skips every file whose size still matches the manifest, so a stopped run
continues where it stopped and a finished one fetches nothing. --verify compares every
held file's SHA-256 instead, which reads all of them (some 30 GB). It stops by itself when
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
import signal
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


# What the CAG serves in place of a report: one page saying the report is not tabled, or to
# see the printed copy, or nothing at all (the 2012-13 coal block allocation audit, 1837).
PLACEHOLDER = re.compile(r"not tabled|printed version of the relevant report", re.I)


def is_placeholder(body):
    """A one-page stand-in rather than a report. Held as a file, counted as missing."""
    import fitz
    try:
        doc = fitz.open(stream=body, filetype="pdf")
    except (fitz.FileDataError, RuntimeError):
        return False  # unreadable here is not evidence of a stand-in page
    with doc:
        if doc.page_count != 1:
            return False
        text = " ".join(doc[0].get_text().split())
    return len(text) < 300 and (not text or bool(PLACEHOLDER.search(text)))


def merged(bodies):
    """Several PDFs as one, in the order given."""
    import fitz
    out = fitz.open()
    for b in bodies:
        with fitz.open(stream=b, filetype="pdf") as part:
            out.insert_pdf(part)
    return out.tobytes(garbage=3, deflate=True)


PART_NO = re.compile(r"^(\d+)\.?[-_ ]")


def reading_order(urls):
    """Chapter files in reading order. The report page lists them in no fixed order
    ("3-Preface", "5-Chapter-1", "1-Inner-Cover" on 118335), but the files are numbered;
    where every one carries a number it decides, and otherwise the page's order stands."""
    nos = [PART_NO.match(urllib.parse.unquote(u.rsplit("/", 1)[-1])) for u in urls]
    if not all(nos):
        return list(urls)
    return [u for _, u in sorted(zip((int(n[1]) for n in nos), urls), key=lambda x: x[0])]


def all_parts(urls, fetch, sleep, pace, tried):
    """Every one of `urls` as a PDF, or None if any part cannot be had: a report missing a
    chapter is not saved as though it were whole."""
    parts = []
    for u in urls:
        body, final = first_pdf([u], fetch, sleep, pace, tried)
        if not body:
            return None
        parts.append((final, body))
    return parts


def held(rec, path, verify):
    """True when the file on disk is the one the manifest recorded. A size check catches the
    truncated and half-written files a stopped run leaves; only `verify` reads the bytes. A
    placeholder is not held: it is asked for again, like a report with no file."""
    if not rec.get("sha256") or rec.get("placeholder") or not os.path.exists(path):
        return False
    if verify:
        return sha(path) == rec["sha256"]
    return os.path.getsize(path) == rec.get("bytes")


def first_pdf(urls, fetch, sleep, pace, tried):
    """The first of `urls` that answers with a PDF, as (body, final url), or (b"", None)."""
    for u in urls:
        sleep(pace)
        code, body, final = fetch(u)
        tried.append([u, code])
        if code == 200 and body[:5] == b"%PDF-":
            return body, final
    return b"", None


RETRY_DAYS = 30


def recently_missing(rec, now, days=RETRY_DAYS):
    """A report checked within `days` and found to have no PDF anywhere. About 49 of the
    newest reports have been taken down; asked again on every run, they came first in
    newest-first order and spent a whole --limit while the run fetched nothing."""
    if (rec.get("sha256") and not rec.get("placeholder")) or not rec.get("checked"):
        return False
    when = datetime.strptime(rec["checked"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (now - when).days < days


def mirror(reports, out, host, fetch=fetch, sleep=time.sleep, free_gb=None, min_free_gb=20,
           pace=1.0, limit=None, deadline=None, verify=False, retry_missing=False):
    os.makedirs(out, exist_ok=True)
    free_gb = free_gb or (lambda p: shutil.disk_usage(p).free / 2 ** 30)
    mp = os.path.join(out, "manifest.json")
    man = {}
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            man = json.load(fh)
    now = datetime.now(timezone.utc)
    todo = [r for r in sorted(reports, key=lambda r: -r["id"])
            if not held(man.get(str(r["id"])) or {}, os.path.join(out, f"{r['id']}.pdf"), verify)]
    have = len(reports) - len(todo)
    if not retry_missing:
        todo = [r for r in todo if not recently_missing(man.get(str(r["id"])) or {}, now)]
    if limit:
        todo = todo[:limit]
    log(f"cag mirror: {len(reports):,} reports, {have:,} held, {len(todo):,} to fetch -> {out}")

    got = bytes_ = 0
    stopped = None
    t0 = saved = time.time()
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
            tried = []
            body, final = first_pdf(candidates(r.get("pdf_url"), host), fetch, sleep, pace, tried)
            if not body and r.get("detail_url"):
                # The report page links whichever file is current, under whatever host.
                sleep(pace)
                code, page, _ = fetch(r["detail_url"])
                rec["detail_status"] = code
                links = list(dict.fromkeys(
                    html.unescape(u) for u in PDF_LINK.findall(page.decode("utf-8", "replace"))
                )) if code == 200 else []
                # Some reports are published a chapter to a file. Only the first was saved,
                # so ten reports were held as a contents page, a preface or a chapter.
                parts = (all_parts(reading_order(links), fetch, sleep, pace, tried)
                         if len(links) > 1 else None)
                if parts:
                    body, final = merged([b for _, b in parts]), parts[0][0]
                    rec["parts"] = [{"url": u, "bytes": len(b),
                                     "sha256": hashlib.sha256(b).hexdigest()} for u, b in parts]
                elif len(links) == 1:
                    body, final = first_pdf(links, fetch, sleep, pace, tried)
            rec["tried"], rec["checked"] = tried, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if body:
                rec["url"] = final
                path = os.path.join(out, f"{r['id']}.pdf")
                with open(path + ".part", "wb") as fh:
                    fh.write(body)
                os.replace(path + ".part", path)
                rec.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                           placeholder=is_placeholder(body))
                got += 1
                bytes_ += len(body)
            man[str(r["id"])] = rec
            # Every 25 files or ten minutes, whichever comes first: large PDFs can take far
            # longer than ten minutes for 25.
            if n % 25 == 0 or time.time() - saved > 600:
                save_manifest(out, man)
                saved = time.time()
            if n % 10 == 0 or n == len(todo):
                rate = n / max(time.time() - t0, 1)
                log(f"  {n:,}/{len(todo):,}  saved {got:,} ({bytes_ / 2 ** 30:.2f} GB)  "
                    f"{rate * 60:.0f}/min  eta {(len(todo) - n) / rate / 60:.0f} min  "
                    f"free {free_gb(out):.0f} GB")
    finally:
        save_manifest(out, man)
    missing = sum(1 for v in man.values() if not v.get("sha256") or v.get("placeholder"))
    log(f"done: saved {got:,} this run; manifest holds {len(man) - missing:,} files and "
        f"{missing:,} reports with no fetchable PDF")
    return {"saved": got, "bytes": bytes_, "stopped": stopped, "missing": missing}


def latest_reports():
    """Every report in the newest complete CAG crawl, read with parse/cag.py."""
    spec = importlib.util.spec_from_file_location("parse_changes",
                                                  os.path.join(ROOT, "parse", "changes.py"))
    changes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(changes)
    crawl = changes.complete("cag", lambda m: m.get("complete"))[-1]
    return changes.cag_parse.read(crawl)[0], crawl


def main():
    ap = argparse.ArgumentParser(description="Keep a local copy of every CAG audit report PDF.")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--pace", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--min-free-gb", type=float, default=20)
    ap.add_argument("--deadline-min", type=float)
    ap.add_argument("--verify", action="store_true", help="re-hash every held file")
    ap.add_argument("--retry-missing", action="store_true",
                    help=f"ask again for reports found to have no PDF in the last {RETRY_DAYS} days")
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
    # A kill (timeout, Ctrl-C from another shell) becomes SystemExit, so mirror()'s finally
    # saves the manifest; without it a SIGTERM skipped finally and orphaned up to 24 files.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    # Every report, not only those the index links a PDF for: 26 in the November crawl link
    # none, and a report's own page can link a file the index does not.
    r = mirror(reports, OUT, host, pace=a.pace, limit=a.limit, deadline=deadline,
               min_free_gb=a.min_free_gb, verify=a.verify, retry_missing=a.retry_missing)
    sys.exit(75 if r["stopped"] else 0)


if __name__ == "__main__":
    main()
