"""
pdftotext, once. AGENT-EDITABLE (PLAN.md §7). Reads bytes it is given; never fetches.

The same "write the bytes to a temp file, run pdftotext, fail on a non-zero exit" was
written out in each state parser as it was added. Four of the copies had no time limit,
and the parse steps in run.sh have none of their own, so one PDF that hung pdftotext
would have held the monthly job until the runner was killed. They also decoded strictly,
so one stray byte raised where the other copies replaced it.
"""
import os
import subprocess
import tempfile


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
