"""
pdftotext and the archived snapshot, once. AGENT-EDITABLE (PLAN.md §7). Reads bytes it is
given and the archive; never fetches.

The same "write the bytes to a temp file, run pdftotext, fail on a non-zero exit" was
written out in each state parser as it was added. Four of the copies had no time limit,
and the parse steps in run.sh have none of their own, so one PDF that hung pdftotext
would have held the monthly job until the runner was killed. They also decoded strictly,
so one stray byte raised where the other copies replaced it. The -bbox-layout reader
(temp file, iterparse, lines merged into rows) was in four parsers the same way, and the
"newest snapshot, its manifest" block in all sixteen. What stays per state is the
tolerance and the time limit, which each state measured against its own books.
"""
import contextlib
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "{http://www.w3.org/1999/xhtml}"


def layout_text(pdf_bytes, timeout=900):
    """pdftotext -layout on raw bytes: the text, pages separated by form feeds."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True,
                           timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


@contextlib.contextmanager
def _bbox_file(pdf_bytes, timeout):
    """pdftotext -bbox-layout into a temp file, for as long as the caller reads it."""
    with tempfile.TemporaryDirectory() as d:
        p, x = os.path.join(d, "b.pdf"), os.path.join(d, "b.xml")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-bbox-layout", p, x], capture_output=True,
                           timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        yield x


def bbox_xml(pdf_bytes, timeout=900):
    """pdftotext -bbox-layout on raw bytes: the whole XHTML document as text."""
    with _bbox_file(pdf_bytes, timeout) as x, \
            open(x, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def bbox_pages(pdf_bytes, tol, rotate=False, timeout=900):
    """Yield page_rows() for each page of pdftotext -bbox-layout, streamed so a
    thousand-page book is never held whole as a tree."""
    with _bbox_file(pdf_bytes, timeout) as x:
        for _, el in ET.iterparse(x, events=("end",)):
            if el.tag == NS + "page":
                yield page_rows(el, tol, rotate)
                el.clear()


def page_rows(page, tol, rotate=False):
    """One -bbox-layout <page> as table rows: [top, bottom, [(left, right, word), ...]],
    rows top to bottom and words left to right.

    Poppler's lines are runs of adjacent words and NOT table rows: a figure, a name in a
    second script, a head of account each arrive as lines of their own. Two lines are one
    row when their tops agree to within `tol` points, which each state measures for its
    own books. With `rotate`, a page whose lines are mostly taller than they are wide is
    read as typeset sideways and its coordinates are turned upright (Kerala's Gender,
    Child and Elderly statements, mixed in among upright prose pages)."""
    raw = []
    for ln in page.iter(NS + "line"):
        ws = [(float(w.get("xMin")), float(w.get("xMax")),
               float(w.get("yMin")), float(w.get("yMax")), w.text or "")
              for w in ln.iter(NS + "word")]
        if ws:
            raw.append(ws)
    rot = rotate and bool(raw) and 2 * sum(
        1 for ws in raw if max(w[3] for w in ws) - min(w[2] for w in ws) >
        max(w[1] for w in ws) - min(w[0] for w in ws)) > len(raw)
    height = float(page.get("height"))
    lines = []
    for ws in raw:
        if rot:
            cells = [(height - w[3], height - w[2], w[4]) for w in ws]
            a, b = min(w[0] for w in ws), max(w[1] for w in ws)
        else:
            cells = [(w[0], w[1], w[4]) for w in ws]
            a, b = min(w[2] for w in ws), max(w[3] for w in ws)
        cells.sort(key=lambda c: c[0])
        lines.append([a, b, cells])
    lines.sort(key=lambda t: (t[0], t[2][0][0]))
    rows = []
    for a, b, cells in lines:
        if rows and abs(rows[-1][0] - a) <= tol:
            rows[-1][1] = max(rows[-1][1], b)
            rows[-1][2].extend(cells)
        else:
            rows.append([a, b, cells])
    for r in rows:
        r[2].sort(key=lambda c: c[0])
    return rows


def snapshot(state, date=None, root=ROOT):
    """The snapshot to parse: (date, its directory, its manifest).

    The newest dated directory under archive/<state>/, or `date`. The same block was in
    all sixteen state parsers, four of them reading a missing manifest as {} and
    publishing cycle: null; a snapshot with no manifest is an incomplete collection and is
    refused here."""
    base = os.path.join(root, "archive", state)
    dates = sorted(d for d in (os.listdir(base) if os.path.isdir(base) else ())
                   if os.path.isdir(os.path.join(base, d)))
    if not dates:
        raise SystemExit(f"no archive at archive/{state}/: run collect/{state}.py first")
    date = date or dates[-1]
    src = os.path.join(base, date)
    path = os.path.join(src, "_manifest.json")
    if not os.path.exists(path):
        raise SystemExit(f"archive/{state}/{date}/_manifest.json missing: the snapshot is "
                         "absent or its collection did not finish")
    with open(path, encoding="utf-8") as fh:
        return date, src, json.load(fh)


def require_books(src, man, name=lambda book: f"{book}.pdf.gz"):
    """Refuse a snapshot missing a book its own manifest expected.

    Nine parsers skipped a missing book with `continue` and published a shorter register,
    exit 0: the state deleting schemes, as far as anyone reading the output could tell.
    `name` maps a book in the manifest's books_expected to its archived file name."""
    missing = [b for b in man.get("books_expected") or []
               if not os.path.exists(os.path.join(src, name(b)))]
    if missing:
        raise SystemExit(f"{src}: {len(missing)} expected book(s) missing, first {missing[0]!r}; "
                         "a missing book is whole schemes silently absent")


def _selftest_snapshot():
    bad = 0
    with tempfile.TemporaryDirectory() as root:
        try:
            snapshot("nowhere", root=root)
            bad += 1
        except SystemExit:
            pass
        for day, man in (("2026-01-01", '{"cycle": "old"}'), ("2026-02-01", '{"cycle": "new"}')):
            os.makedirs(os.path.join(root, "archive", "st", day))
            with open(os.path.join(root, "archive", "st", day, "_manifest.json"), "w") as fh:
                fh.write(man)
        open(os.path.join(root, "archive", "st", "notes.txt"), "w").close()
        date, src, man = snapshot("st", root=root)
        bad += (date, man) != ("2026-02-01", {"cycle": "new"})
        bad += src != os.path.join(root, "archive", "st", "2026-02-01")
        bad += snapshot("st", "2026-01-01", root=root)[2] != {"cycle": "old"}
        for wanted in ("2025-12-31", None):
            if wanted is None:
                os.makedirs(os.path.join(root, "archive", "st", "2026-03-01"))
            try:
                snapshot("st", wanted, root=root)
                bad += 1
            except SystemExit:
                pass
    print(f"  {'FAIL' if bad else 'ok  '} the newest snapshot or --date is read, and one "
          "without a manifest is refused")
    return bad


def _selftest_rows():
    bad = 0

    def page(lines, height=100):
        body = "".join("<line>" + "".join(
            f'<word xMin="{a}" xMax="{b}" yMin="{c}" yMax="{d}">{t}</word>'
            for a, b, c, d, t in ln) + "</line>" for ln in lines)
        return ET.fromstring(f'<page xmlns="http://www.w3.org/1999/xhtml" width="80" '
                             f'height="{height}"><flow><block>{body}</block></flow></page>')

    # A name and its figure 3 points apart are one row at tol 4 and two at tol 2.5.
    upright = page([[(10, 30, 50, 58, "Total"), (32, 40, 50, 58, "04")],
                    [(60, 70, 53, 61, "4,37")],
                    [(10, 30, 70, 78, "Next")]])
    got = page_rows(upright, 4.0)
    bad += got != [[50.0, 61.0, [(10.0, 30.0, "Total"), (32.0, 40.0, "04"),
                                 (60.0, 70.0, "4,37")]],
                   [70.0, 78.0, [(10.0, 30.0, "Next")]]]
    bad += len(page_rows(upright, 2.5)) != 3
    # Rotation is off unless asked for, and asked for, decided per page from line shape.
    bad += page_rows(upright, 4.0, rotate=True) != got
    sideways = page([[(20, 28, 10, 30, "A"), (20, 28, 32, 40, "B")],
                     [(40, 48, 10, 30, "C")]])
    bad += page_rows(sideways, 2.5, rotate=True) != [
        [20.0, 28.0, [(60.0, 68.0, "B"), (70.0, 90.0, "A")]],
        [40.0, 48.0, [(70.0, 90.0, "C")]]]
    bad += len(page_rows(sideways, 2.5)) != 1
    print(f"  {'FAIL' if bad else 'ok  '} -bbox-layout lines merge into rows within the "
          "tolerance, sideways pages turned upright only when asked")
    return bad


def selftest():
    bad = _selftest_snapshot() + _selftest_rows()
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.pdf.gz"), "wb").close()
        require_books(d, {"books_expected": ["a"]})
        try:
            require_books(d, {"books_expected": ["a", "b"]})
            bad += 1
        except SystemExit as e:
            bad += "'b'" not in str(e)
        open(os.path.join(d, "demand-07.pdf.gz"), "wb").close()
        require_books(d, {"books_expected": [7]}, lambda b: f"demand-{b:02d}.pdf.gz")
    print(f"  {'FAIL' if bad else 'ok  '} a book the manifest expected and the archive lacks is refused")
    return bad


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(1 if selftest() else 0)
    sys.exit("usage: python3 parse/pdf.py --self-test")
