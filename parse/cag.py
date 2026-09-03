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
# Boilerplate that wraps every title and names no scheme. Stripped so that what remains is
# the subject, which is the only part a scheme name can be matched against. "Report of the
# Comptroller and Auditor General of India on Performance Audit on 'Implementation of Jal
# Jeevan Mission in Rajasthan'" is 84 characters of which 34 are the subject.
#
# Two things about this list that are not obvious and cost a rewrite to find.
#
# The catalogue misspells its own audit type. "Performace Audit of National Rural Health
# Mission" appears in HUNDREDS of titles, and an audit-type rule spelling it correctly left
# every one of them with "Performace Audit of" glued to the front of the scheme name. The
# patterns tolerate it, and tolerate "andd" in "Comptroller andd Auditor General" the same
# way. A source's typos are part of its shape.
#
# A report number is optional AND the year clause can stand alone. "Report No. 5 of 2017",
# "Report No.5 of 2017", "Report 5 of 2017" and plain "Report of 2013" all occur, and only
# the first three were handled: 641 subjects read "of 2013" or "of 2014 - Financial Audit
# on State Finance of", which is a filing reference published as if it were a scheme name.
BOILER = [
    # "Report No. 5 of 2017", "Report No.5 of 2017", "Report 5 of 2017", "Report of 2013".
    # The number is optional AND the whole "of YYYY" clause can stand alone, which is what
    # left 641 subjects reading "of 2013".
    r"^[\u2010-\u2015\-]+\s*",          # a leading dash, left when a prefix was stripped
    r"^cag\s+report\s+(?:on|of)?\s*",
    r"^report\s+",
    r"^\d{1,3}\s+(?=[A-Za-z])",                       # a leading serial number
    r"^audit\s+report\s*(?:\([a-z ]+\))?\s*",        # "Audit Report (Civil) ..."
    r"^the\s+",
    # "No. 24 Part 1 of 2015" as well as "No. 24 of 2015".
    r"^(?:no\.?\s*)?[\dIVXL]+(?:\s+part\s+[\dIVXL]+)?\s+of\s+(?:the\s+year\s+)?\d{4}"
    r"\s*[:\-]?\s*",
    r"^of\s+(?:the\s+year\s+)?\d{4}\s*[:\-]?\s*",
    # "andd" is the catalogue's own typo and it defeated the whole clause.
    # "andd" is the catalogue's own typo and "&" its own abbreviation; both defeated the
    # clause when it spelled out "and".
    r"^(?:of\s+)?(?:the\s+)?comptroller\s+(?:an[d]{1,3}|&)\s+auditor\s+general\s+of\s+india"
    r"(?:\s*[,\-]?\s*(?:on|for))?\s*",
    r"^(?:\(c\s*&\s*ag\)|c\s*&\s*ag)(?:\s+of\s+india)?\s*(?:on|for)?\s*",
    r"^(?:on|for|regarding|of)\s+",
    # Compound audit types: "Performance and Compliance Audit on", "Performance and
    # Financial Audit on". One type at a time left "Performance and Financial Audit on
    # Civil of" as a scheme name.
    r"^(?:(?:performan?ce|compl[ai]{2}nce|financial|thematic)\s*(?:,|and|&)?\s*)+audit\s+"
    r"(?:report\s+)?(?:on|of)?\s*",
    r"^(?:union|state)\s+government\s*[,\-]?\s*",
    # "Union Revenue Performance Audit Indirect Taxes Customs" puts the government and the
    # sector in front of the audit type, so neither anchored rule above reaches it.
    r"^(?:union|state)\s+\w+\s+(?:performan?ce|compl[ai]{2}nce|financial|thematic)\s+"
    r"audit\s*(?:report\s+)?(?:on|of)?\s*",
    r"\s*(?:for\s+)?the\s+(?:year|period)\s+ended\s+.*$",
    # A trailing report number is the catalogue's filing, never part of a subject.
    r"\s*[,\.]?\s*report\s+no\.?\s*[\dIVXL]+\s+of\s+\d{4}.*$",
    r"\s*[,\-]?\s*government\s+of\s+[a-z &]+$",
    r"\s+reports?\s+of\s+.*$",
    r"\s+union\s+government\s*.*$",
    # The audit type also comes LAST: "Public Debt Management Performance Audit".
    r"\s+(?:performan?ce|compl[ai]{2}nce|financial|thematic|social)\s+audit\s*$",
    # A dangling preposition is what is left when the government name after it was
    # stripped: "Ordnance Equipment Group of Factories of".
    r"\s+(?:of|on|for|in|and|the)\s*$",
    # An audit type can sit after a parenthetical or a dash rather than at the front:
    # "(Ministry of X), Performance Audit on Functioning of ...". Anchored to a separator
    # so it cannot eat the word Performance out of a scheme's own name.
    r"^.*?[\),\u2013\u2014\-]\s*(?:(?:performan?ce|compl[ai]{2}nce|financial|thematic)\s*"
    r"(?:,|and|&)?\s*)+audit\s+(?:report\s+)?(?:on|of)?\s*",
]
NOT_A_SUBJECT = re.compile(
    r"^(?:(?:general|social|economic|revenue|civil|commercial|financial|public\s+sector"
    r"|local\s+bodies?|state|union\s+government|panchayati\s+raj|urban\s+local"
    r"|autonomous\s+bodies?|psus?|performance|compliance|direct\s+taxes?"
    r"|indirect\s+taxes?|goods\s+and\s+services\s+tax|gst"
    r"|state\s+finances?|general\s+purpose\s+financial|railways?\s+finances?"
    r"|revenue\s+receipts?|appropriation|audit\s+report(?:\s*\([a-z ]+\))?"
    r"|state\s+finances?\s+audit\s+report[\s\d\-]*[a-z ]*)"
    r"(?:\s*(?:and|,|&)\s*)?)+"
    r"(?:\s*(?:sector|sectors|finances?|undertakings?|departments?|institutions?|"
    r"bodies|accounts?|audit|receipts?|expenditure)s?)*\s*$", re.I)

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
    # Two words minimum. A one-word subject is a sector or a department every time, and
    # offering it to a scheme matcher is how "Civil" becomes a finding.
    if len(s) < 6 or len(s.split()) < 2:
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
    # An explicit date that was never collected is an error, not an empty result. run.sh
    # passed it the myScheme snapshot date, the CAG archive is stamped with its own crawl
    # date, and this quietly wrote a catalogue of zero reports over a good one. A parser
    # that answers "nothing" when asked about a day it has no bytes for is indistinguishable
    # from a source that published nothing that day, which is exactly the confusion this
    # project exists to remove.
    if date and date not in dates:
        raise SystemExit(f"no CAG archive for {date}. Held: {', '.join(dates)}")
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
