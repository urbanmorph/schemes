"""
Turn the archived CAG index pages into a catalogue of audit reports.

AGENT-EDITABLE (PLAN.md §7). Reads archive/cag/, writes data/cag/reports.json. Never
fetches.

    data/cag/reports.json    one entry per tabled report

Scope, which is narrower than it looks and deliberately so. This register is about *the
data about* schemes and never about whether a scheme works, so nothing here reads, quotes
or characterises an audit FINDING. What is captured is that a report exists, on what
subject, tabled when, of what type, covering which government, and where to read it. The
CAG's conclusions are the CAG's to publish.

The one thing this adds that exists nowhere else: which schemes have been audited at all.
That list is not published as a list anywhere, and finding it today means paging through
2,798 entries by hand.

Every field is lifted from a class the site sets, not from position or from flattened
text: .dtn for the date, .reportType for the audit type, .reportIcon h5 for the
government, .sectorDetail for the sector, .pdfBottomReport for the PDF. A layout change
therefore empties a field rather than filling it with the wrong neighbour, which is the
failure mode worth having.
"""

import argparse
import glob
import gzip
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

BASE = "https://cag.gov.in"
BLOCK = re.compile(r'<div class="AuditReportlisting">(.*?)(?=<div class="AuditReportlisting">'
                   r'|<div class="pagination|</section)', re.S)

# Boilerplate that wraps every title and names no scheme. Stripped so that what remains is
# the subject, which is the only part a scheme name can be matched against. "Report of the
# Comptroller and Auditor General of India on Performance Audit on 'Implementation of Jal
# Jeevan Mission in Rajasthan'" is 84 characters of which 34 are the subject.
BOILER = [
    # "No." is optional: the catalogue writes "Report No. 5 of 2017", "Report No.5 of
    # 2017" and plain "Report 5 of 2017". Requiring it left 17 titles reduced to "5 of
    # 2017", a report number published as if it were a scheme name.
    r"^report\s+(?:(?:no\.?\s*)?[\dIVXL]+\s+of\s+(?:the\s+year\s+)?\d{4}\s*[:\-]?\s*)?",
    r"^(?:of\s+)?the\s+comptroller\s+and\s+auditor\s+general\s+of\s+india\s*",
    r"^(?:\(c\s*&\s*ag\)|c\s*&\s*ag)\s*",
    r"^(?:on|for|regarding)\s+",
    r"^(?:performance|compliance|financial|thematic)\s+audit\s+(?:report\s+)?(?:on|of)?\s*",
    r"^(?:union|state)\s+government\s*[,\-]?\s*",
    r"\s+for\s+the\s+year\s+ended\s+.*$",
    r"\s*[,\-]?\s*government\s+of\s+[a-z &]+$",
    # A trailing "Reports of the Department of X" is the series the report belongs to, not
    # part of the subject. Without this, "Disbursement of Defence Pension" arrives as
    # "Disbursement of Defence Pension Reports of Defence Services".
    r"\s+reports?\s+of\s+.*$",
    r"\s+union\s+government\s*.*$",
]

# Subjects that name a sector or a class of audit rather than a scheme. Any title reducing
# to one of these is reporting on a slice of government, not on a programme, and offering
# it to a scheme matcher would manufacture findings out of the CAG's own filing system.
NOT_A_SUBJECT = re.compile(
    r"^(?:(?:general|social|economic|revenue|civil|commercial|financial|public\s+sector"
    r"|local\s+bodies?|state|union\s+government|panchayati\s+raj|urban\s+local"
    r"|autonomous\s+bodies?|psus?)"
    r"(?:\s*(?:and|,|&)\s*)?)+"
    r"(?:\s*(?:sector|sectors|finances?|undertakings?|departments?|institutions?|"
    r"bodies|accounts?|audit))*\s*$", re.I)


def text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def pick(block, pattern, group=1):
    m = re.search(pattern, block, re.S | re.I)
    return text(m.group(group)) if m else None


def subject(title):
    """The title with its wrapper removed. Returns None when nothing survives.

    A CAG title is not a scheme name. Some contain one, "on Green India Mission", and some
    contain none at all, "on State Finances for the year 2024-25, Government of Jharkhand".
    Reporting the second kind as an unmatched scheme would be counting the register's own
    boilerplate as a finding, so a title that reduces to a general-purpose phrase returns
    nothing and is never offered to the matcher.
    """
    s = (title or "").strip().strip("“”\"'")
    prev = None
    while prev != s:
        prev = s
        for pat in BOILER:
            s = re.sub(pat, "", s, flags=re.I).strip().strip("“”\"'").strip(",-: ")
    s = re.sub(r"^implementation\s+of\s+", "", s, flags=re.I).strip()
    s = re.sub(r"\s+in\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?$", "", s).strip()
    if len(s) < 6:
        return None
    if NOT_A_SUBJECT.match(s):
        return None
    return s


def parse_page(body):
    out = []
    for b in BLOCK.findall(body):
        m = re.search(r'href="(/en/audit-report/details/(\d+))"', b)
        if not m:
            continue
        title = pick(b, r'href="/en/audit-report/details/\d+"[^>]*>(.*?)</a>')
        pdf = re.search(r'<div class="pdfBottomReport">.*?href="([^"]+\.pdf[^"]*)"', b, re.S | re.I)
        size = re.search(r"<sub>\(\s*<b>PDF</b>\s*&nbsp;([\d.]+)&nbsp;(\w+)", b)
        rno = re.search(r"Report\s+No\.?\s*([\dIVXL]+)\s+of\s+(?:the\s+year\s+)?(\d{4})",
                        text(b), re.I)
        out.append({
            "id": int(m.group(2)),
            "title": title,
            "subject": subject(title),
            "tabled": pick(b, r'<span class="dtn">(.*?)</span>'),
            "audit_type": pick(b, r'<div class="reportType">\s*<span>(.*?)</span>'),
            "government": pick(b, r'<div class="reportIcon">.*?<h5>(.*?)</h5>') or "Union",
            "sector": pick(b, r'<div class="sectorDetail">\s*<div>Sector:?</div>\s*<div>(.*?)</div>'),
            "report_no": rno.group(1) if rno else None,
            "report_year": int(rno.group(2)) if rno else None,
            "detail_url": BASE + m.group(1),
            "pdf_url": (BASE + pdf.group(1)) if pdf else None,
            "pdf_size": f"{size.group(1)} {size.group(2)}" if size else None,
        })
    return out


def run(date=None):
    dates = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "archive", "cag", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/cag/: run collect/cag.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "cag", date)
    # A manifest is written when the crawl finishes, so a crawl still running or killed
    # part way has none. Parsing anyway is useful for looking at what arrived, but it must
    # not then claim the catalogue is complete: without the manifest there is no recorded
    # total to check the row count against, and reconciles stays false rather than absent.
    mp = os.path.join(src, "_manifest.json")
    man = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}

    by_id, pages = {}, 0
    for p in sorted(glob.glob(os.path.join(src, "page-*.html.gz"))):
        with gzip.open(p, "rb") as fh:
            body = fh.read().decode("utf-8", "replace")
        pages += 1
        for r in parse_page(body):
            by_id.setdefault(r["id"], r)
    reports = [by_id[k] for k in sorted(by_id)]

    def tally(field):
        t = {}
        for r in reports:
            t[str(r.get(field) or "not stated")] = t.get(str(r.get(field) or "not stated"), 0) + 1
        return dict(sorted(t.items(), key=lambda kv: (-kv[1], kv[0])))

    claimed = man.get("total_claimed")
    write_json("data/cag/reports.json", {
        "snapshot": date,
        "built": utcnow(),
        "source": "Comptroller and Auditor General of India, audit report index",
        "source_url": man.get("index"),
        "pages_read": pages,
        "reports": len(reports),
        "site_claimed_total": claimed,
        # The site prints its own total on every page, so the parse has a checksum it did
        # not compute itself. A silent layout change that drops one listing per page would
        # otherwise be invisible: the crawl would still look complete and every page would
        # still yield rows.
        "reconciles": (claimed is not None and len(reports) == claimed),
        "with_a_subject": sum(1 for r in reports if r["subject"]),
        "with_a_pdf": sum(1 for r in reports if r["pdf_url"]),
        "by_audit_type": tally("audit_type"),
        "by_government": tally("government"),
        "scope_note": ("A catalogue, not findings. This records that a report exists, on "
                       "what, when, of what type, for which government, and where to read "
                       "it. Nothing here reads or characterises an audit conclusion: those "
                       "are the CAG's to publish. What this adds is the list of what has "
                       "been audited, which is not published as a list anywhere."),
        "subject_note": ("A CAG title is not a scheme name. Some contain one, 'on Green "
                         "India Mission'; many name a function of government instead, 'on "
                         "State Finances, Government of Jharkhand'. `subject` is the title "
                         "with its boilerplate stripped, and is null where nothing "
                         "survives, so only titles that could name a scheme are ever "
                         "offered to a matcher."),
        "entries": reports,
    })
    return reports, pages, claimed


def main():
    ap = argparse.ArgumentParser(description="Parse the archived CAG report catalogue.")
    ap.add_argument("--date")
    a = ap.parse_args()
    reports, pages, claimed = run(a.date)
    ok = claimed is not None and len(reports) == claimed
    print(f"CAG catalogue: {len(reports):,} reports from {pages} pages")
    if claimed is None:
        print("  no manifest yet, so completeness is unverified: crawl still running or "
              "interrupted")
    else:
        print(f"  site's own total {claimed:,} -> {'reconciles' if ok else 'MISMATCH'}")
    print(f"  with a subject that could name a scheme {sum(1 for r in reports if r['subject']):,}")
    d = json.load(open(os.path.join(ROOT, "data", "cag", "reports.json"), encoding="utf-8"))
    for k, v in list(d["by_audit_type"].items())[:6]:
        print(f"     {k:<28}{v:>6}")


if __name__ == "__main__":
    main()
