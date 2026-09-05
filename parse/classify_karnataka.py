"""
Classify Karnataka budget rows: welfare scheme, or institution and establishment head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

    data/karnataka/labels.json          hand ground truth, the input
    data/karnataka/classification.json  the verdicts, the output

parse/karnataka.py pulls 969 rows out of the Gender, Child and SCSP/TSP books. Comparing
those against myScheme's Karnataka records says almost all of them are absent from the
national citizen portal, and publishing that number as "schemes Karnataka hides" would be
false, because a large share of the 969 are not schemes at all. "Chamarajanagar Government
Law College", "Commissionerate of School Education, Bengaluru", "Karnataka State Legal
Services Authority" and "Unspent SCSP-TSP Amount as per the SCSP-TSP Act 2013" are all in
that list. Naming an accounting head as a scheme the government hid is an accusation
against a government that did nothing of the kind.

WHY THERE IS A HAND LABEL SET AND NOT A BORROWED ONE. parse/classify.py can score itself
against myScheme membership because the Union Budget lines it reads are mostly national
schemes a portal would list. That proxy collapses here. Measured on the 108 rows of the
development half: a Karnataka row whose name matches any myScheme record anywhere in India
is a scheme 38.8% of the time, against 34.1% for rows that match nothing, a lift of +0.05.
The signal is worthless because the matches are cross-state coincidences. So the ground
truth is hand labels in data/karnataka/labels.json, where a human can read the reasoning on
each one and correct it. The labels are the project. Everything below is only as good as
they are.

There are two label sets and they answer different questions.
  stratified, 215 rows   A probability sample across the three books and the allocation
                         range. This is what the threshold sweep runs on, because
                         precision and recall estimated on anything else would not
                         generalise to rows the classifier has not seen.
  audit, 109 rows        Every remaining row the classifier calls a scheme at score 5 or
                         above. With the 40 stratified rows that already sat there, the
                         two sets are a CENSUS of the published region, so the published
                         list's error count is counted, not estimated. The audit was made
                         after the weights were fixed and was deliberately not fed back
                         into them, which is why two of its findings are still in the
                         output as errors rather than as patches.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan, free travel, a house, treatment for a named beneficiary
                class, or training given to people.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, or is an
                accounting or adjustment head.
62 of the 215 sat close enough to that line to be flagged borderline, and each carries the
sentence that decided it. A reader who disagrees can flip the label and rerun.

WHAT ACTUALLY DISCRIMINATES. Two families of signal, measured on the development half
against a base rate of 37.0%:

  the state's own accounting classification, which is not a guess:
    capital outlay or loan major head (4xxx to 7xxx)      P(scheme) 0.000 over 23 rows
    establishment or works minor head (001, 003 to 053)   P(scheme) 0.000 over  8 rows
    welfare function major head (2216, 2225, 2235, ...)   P(scheme) 0.690 over 29 rows

  what the book itself says the money is for:
    institution words in the name                         P(scheme) 0.000 over 23 rows
    asset or works words in the name                      P(scheme) 0.000 over 12 rows
    the purpose line names a benefit                      P(scheme) 0.947 over 19 rows
    the purpose line names who receives it                P(scheme) 0.909 over 22 rows

The purpose line result is worth pausing on. Whether a row HAS a purpose line does not
separate rows that match a myScheme record from rows that do not (43% against 37%), which
is why that test looked dead. Against hand labels the mere presence of a purpose line is
already worth +0.49, and what the purpose line SAYS is worth +0.70. The signal was there;
the myScheme proxy was hiding it.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py.
F1 peaks at threshold 1, where precision is 83% and one published name in six is wrong.
Publishing runs at 7 instead. The audit census is what settles that number, because it
counts errors rather than estimating them:

    threshold 5   149 rows published, 12 are not schemes   precision 91.9%
    threshold 6   106 rows published,  6 are not schemes   precision 94.3%
    threshold 7    74 rows published,  2 are not schemes   precision 97.3%
    threshold 8    50 rows published,  1 is not a scheme   precision 98.0%

The stratified sample alone would have said 97.5% at threshold 5, on the strength of 40
rows. The census says 91.9%. That gap is the reason the audit exists: a probability sample
of 215 rows leaves too few above the bar to state the published list's precision to better
than a few points, and the direction of the error was flattering. Being wrong about a name
is worse than leaving a true case out, because the first is an accusation and the second is
only an omission, so this runs at 7 and gives up recall for it.
"""

import argparse
import glob
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT_DIR, "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# Absence claims use the generous matcher, per parse/match.py's own argument. It returns
# a TUPLE (bool, why) and a tuple is always truthy, so the [0] is load bearing: without it
# every comparison matches and the absence list empties out silently.
_m = _load("scheme_match", os.path.join(HERE, "match.py"))
probably_same = _m.probably_same

PUBLISH_THRESHOLD = 7


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written from the corpus before any of the numbers
# above were computed, so the weights are fitted but the word choices are not.
# ---------------------------------------------------------------------------

# Minor heads are standardised across Indian government accounts, so these mean the same
# thing in every department: 001 Direction and Administration, 003 Training, 004 Research,
# 005 Investigation, 051 Construction, 052 Machinery and Equipment, 053 Maintenance and
# Repairs. Not one of the 8 rows under these heads in the development half was a scheme.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053"}

# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC, ST, OBC and Minorities, 2235 Social Security and Welfare,
# 2236 Nutrition, 2408 Food, 2501 Rural Development Programmes, 2505 Rural Employment.
# 69.0% of the 29 development rows under these were schemes, against 25.3% elsewhere.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2408", "2501", "2505"}

# Words that name an organisation rather than a benefit. "Chamarajanagar Government Law
# College", "Directorate of Minorities", "Karnataka State Wakf Board".
INSTITUTION = {
    "university", "universities", "college", "colleges", "institute", "institutes",
    "institution", "institutions", "corporation", "corporations", "board", "authority",
    "directorate", "commissionerate", "commissioner", "director", "academy", "centre",
    "center", "centres", "centers", "department", "office", "bureau", "commission",
    "council", "nigam", "hospital", "hospitals", "laboratory", "exchanges",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "constuction", "building", "buildings", "maintenance",
    "infrastructure", "works", "road", "roads", "renovation", "procurement", "repair",
    "repairs", "equipment", "equipments", "machinery", "bridges", "jetties", "capital",
}

# Words that name an accounting or payroll head. "Unspent SCSP-TSP Amount" is the clearest
# case: 11 rows carry it and not one is a scheme.
ACCOUNTING = {
    "unspent", "devolution", "salary", "salaries", "honorarium", "administrative",
    "expenses", "expenditure", "fcg", "sfc",
}
# "Establishment" is two different words in this corpus. "District Forest Officers'
# Establishments" is a payroll head; "Subsidy for Establishment of SME Units under
# SCSP-TSP" is a loan scheme for SC and ST entrepreneurs. Matching the bare token charged
# the second one -2 for being the first, so the accounting sense is matched by phrase.
ACCOUNTING_PHRASE = re.compile(r"\bestablishments\b|\bestablishment (charges|expenses)\b",
                               re.I)

# Words that name the thing a person receives.
BENEFIT = {
    "scholarship", "scholarships", "stipend", "pension", "incentive", "incentives",
    "assistance", "subsidy", "subsidies", "free", "insurance", "compensation", "dbt",
    "loan", "loans", "kit", "kits", "nutrition", "bhagya", "reimbursement", "allowance",
    "relief", "concession", "concessional", "concessions", "samman", "nidhi",
}

# Words that name who receives it. A head that names its beneficiary class is describing a
# transfer; a head that names none is usually describing an office or an asset.
BENEFICIARY = {
    "students", "student", "women", "woman", "girls", "girl", "farmers", "farmer",
    "weavers", "beneficiaries", "beneficiary", "victims", "victim", "workers", "worker",
    "families", "family", "children", "child", "persons", "person", "youth", "youths",
    "widows", "disabled", "handicapped", "blind", "citizens", "households", "household",
    "fishermen", "artisans", "entrepreneurs", "graduates", "mothers", "adolescent",
}

# Scheme-name morphology. Weak on its own and weighted accordingly: "Namma Grama Namma
# Raste Scheme" is a rural road renewal head, so the word Scheme in a name proves nothing.
SCHEME_MARKER = {
    "yojana", "yojane", "yojna", "abhiyan", "abhiyana", "mission", "scheme", "schemes",
    "bhagya", "nidhi", "samman",
}

# A purpose line that describes putting up a building is describing an asset, whatever the
# name above it says. This is what separates "CSS-Central Share-National Ayush Mission",
# whose stated purpose is upgradation of hospitals, from a mission that treats patients.
PURPOSE_ASSET = re.compile(
    r"\b(construction|maintenance|upgradation|building|infrastructure|renovation|"
    r"establishment of)", re.I)

# "Bidar Institute of Medical Sciences, Bidar", "Construction of Law College at Haveri".
# A name that ends in a place, or hangs a place off "at", is naming a building or a body.
NAME_PLACE = re.compile(r",\s*[A-Z][a-z]+\s*$|\bat [A-Z][a-z]+")


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def score_entry(hoa, name, purpose):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic.

    Negative weights are larger than positive ones on purpose. A row that looks like an
    institution and also carries benefit words, "Government Schools for the Deaf and
    Blind", should have to work to clear the bar, because that is the row that would
    embarrass the published list.
    """
    tk = tokens(name)
    tp = tokens(purpose)
    ev = []
    total = 0

    def add(points, why):
        nonlocal total
        total += points
        ev.append(["%+d" % points, why])

    # Structure first: what the state's own accounting classification says this is.
    if hoa[0] in "4567":
        add(-4, "capital outlay or loan major head " + hoa[:4])
    if hoa[8:11] in ESTAB_MINOR:
        add(-3, "establishment or works minor head " + hoa[8:11])

    inst = sorted(tk & INSTITUTION)
    if inst:
        add(-4, "institution words in the name: " + ", ".join(inst[:4]))
    elif NAME_PLACE.search(name or ""):
        add(-4, "the name ends in a place, which is the shape of an institution's name")

    works = sorted(tk & WORKS)
    if works:
        add(-3, "asset or works words in the name: " + ", ".join(works[:4]))

    acct = sorted(tk & ACCOUNTING)
    if acct or ACCOUNTING_PHRASE.search(name or ""):
        add(-2, "accounting or payroll words in the name: " +
            (", ".join(acct[:4]) or "establishments"))

    if PURPOSE_ASSET.search(purpose or ""):
        add(-2, "the book's purpose line describes building or upkeep, not a transfer")

    if hoa[:4] in WELFARE_MAJOR:
        add(2, "welfare function major head " + hoa[:4])

    pben = sorted(tp & BENEFIT)
    if pben:
        add(3, "the purpose line names a benefit: " + ", ".join(pben[:4]))
    pwho = sorted(tp & BENEFICIARY)
    if pwho:
        add(2, "the purpose line names who receives it: " + ", ".join(pwho[:4]))

    ben = sorted(tk & BENEFIT)
    if ben:
        add(2, "benefit words in the name: " + ", ".join(ben[:4]))
    who = sorted(tk & BENEFICIARY)
    if who:
        add(2, "named beneficiary class in the name: " + ", ".join(who[:4]))
    mark = sorted(tk & SCHEME_MARKER)
    if mark:
        add(1, "scheme-name marker in the name: " + ", ".join(mark[:3]))

    return total, ev


SIGNALS = [
    {"points": -4, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": "P(scheme) 0.000 over 23 development rows, base rate 0.370"},
    {"points": -4, "signal": "institution word in the name, or a name ending in a place",
     "measured": "P(scheme) 0.000 over 23 development rows"},
    {"points": -3, "signal": "establishment or works minor head, 001 003 004 005 051 052 053",
     "measured": "P(scheme) 0.000 over 8 development rows"},
    {"points": -3, "signal": "asset or works word in the name",
     "measured": "P(scheme) 0.000 over 12 development rows"},
    {"points": -2, "signal": "accounting or payroll word in the name",
     "measured": "P(scheme) 0.077 over 13 development rows"},
    {"points": -2, "signal": "the purpose line describes building or upkeep",
     "measured": "P(scheme) 0.167 over 6 development rows, the weakest line here"},
    {"points": 3, "signal": "the purpose line names a benefit",
     "measured": "P(scheme) 0.947 over 19 development rows"},
    {"points": 2, "signal": "welfare function major head, 2216 2225 2235 2236 2408 2501 2505",
     "measured": "P(scheme) 0.690 over 29 development rows"},
    {"points": 2, "signal": "the purpose line names who receives it",
     "measured": "P(scheme) 0.909 over 22 development rows"},
    {"points": 2, "signal": "benefit word in the name",
     "measured": "P(scheme) 0.789 over 19 development rows"},
    {"points": 2, "signal": "named beneficiary class in the name",
     "measured": "P(scheme) 0.800 over 15 development rows"},
    {"points": 1, "signal": "scheme-name marker in the name",
     "measured": "P(scheme) 0.625 over 32 development rows, the weakest positive"},
]

REJECTED_SIGNALS = [
    {"signal": "the name matches a myScheme record from any state",
     "measured": "P(scheme) 0.388 with, 0.341 without, lift +0.047 over 108 rows",
     "why": ("The cross-state matches are coincidences of wording, so membership of the "
             "national portal says almost nothing about whether a Karnataka budget row is "
             "a scheme. This is the borrowed ground truth the labels replace.")},
    {"signal": "the row has a purpose line at all",
     "measured": "P(scheme) 0.667 with, 0.182 without, lift +0.485 over 108 rows",
     "why": ("Real, but subsumed: what the purpose line says is worth +0.70 and this only "
             "+0.49, and scoring both would count one piece of evidence twice.")},
    {"signal": "the name starts with CSS-Central Share or CSS-State Share",
     "measured": "P(scheme) 0.455 with, 0.333 without, lift +0.121 over 108 rows",
     "why": ("Centrally sponsored funding says nothing on its own: AMRUT, Samagra Shiksha "
             "infrastructure and PM-ABHIM are all CSS rows that build things.")},
    {"signal": "the word Programme or Program in the name",
     "measured": "P(scheme) 0.444 with, 0.364 without, lift +0.080 over all 215 rows",
     "why": "Too weak to carry a point in either direction."},
]

KNOWN_ERRORS = [
    {"name": "Government Schools for the Deaf and Blind", "score": 9,
     "kind": "false positive, published at threshold 7",
     "why": ("The higher-scoring of the two errors that survive the publishing bar. It is "
             "a real welfare provision, free accommodation, meals and education for deaf "
             "and blind children, so its purpose line reads exactly like a scheme's. It "
             "is labelled not_scheme because the head funds institutions, the schools "
             "themselves. This is the classifier's 'Space Technology': a row in the "
             "published list a careful reader would object to, named here rather than "
             "quietly patched out.")},
    {"name": "Placement Cell of the Different Abled", "score": 7,
     "kind": "false positive, published at threshold 7",
     "why": ("The other one. Its name is an office, a placement cell, and the labelling "
             "rule says an office is not a scheme, but its purpose line says unemployment "
             "allowance to differently abled persons, which is a transfer. This label "
             "could reasonably be flipped, and if it were, precision at threshold 7 would "
             "read 98.6% rather than 97.3%.")},
    {"name": "CSS-Salary-Integrated Child Protection Scheme", "score": 5,
     "kind": "false positive, excluded at threshold 7",
     "why": ("A salary head that says so in its own name. It gets -2 for the word salary "
             "and then +7 from a welfare major head, a child beneficiary and the word "
             "Scheme. Making a CSS-Salary prefix disqualifying would fix it and would be "
             "principled, but the fix was found by reading the audit, and changing weights "
             "to suit the audit would destroy the one measurement in this file that counts "
             "errors instead of estimating them.")},
    {"name": "CSS-Central Share-Training of Anganwadi Workers & Helpers, and its state "
             "share", "score": 6,
     "kind": "false positive, excluded at threshold 7",
     "why": ("Departmental staff training reads as a benefit because the trainees are "
             "people. Two rows, both excluded at 7.")},
    {"name": "Assistance to KHDC", "score": 5,
     "kind": "false positive, excluded at threshold 7",
     "why": ("Assistance to the Karnataka Handloom Development Corporation. The "
             "institution test never fired because the institution is an acronym. Any row "
             "that names a body only by its initials is invisible to this classifier.")},
    {"name": "rows with no purpose line and a plain name", "score": "0 to 2",
     "kind": "false negative, the recall cost",
     "why": ("Large, and structural. Gruha Lakshmi, Palna, Ashadeep, CSS-State Share-NRLM "
             "and CSS-State Share-ICDS-(SNP) are all genuine schemes scoring 0 to 2 "
             "because the book prints no purpose line for them and their names carry no "
             "benefit word. 580 of the 969 rows have no purpose line at all. A published "
             "count from this classifier is a floor on Karnataka's schemes and never a "
             "total.")},
]

# Absence is a matching question, and parse/match.py misses a specific shape: a Karnataka
# name of one or two words against a myScheme name of one word, where the containment rule
# needs two shared content words and the skeleton rule needs two shared skeletons. Found by
# reading all 149 published names against all 60 myScheme Karnataka records by hand.
KNOWN_FALSE_ABSENCES = [
    {"karnataka": "Bhagya Lakshmi", "myscheme": "Bhagyalaxmi Scheme",
     "why": ("The Karnataka name is two words and the myScheme name is one, so neither "
             "containment nor the skeleton rule has two tokens to line up.")},
    {"karnataka": "Udyogini - Women Development Corporation", "myscheme": "Udyogini Scheme",
     "why": "Same shape: Udyogini alone on the myScheme side, one content word."},
    {"karnataka": "Food and Accomodation Assistance-Vidyasiri",
     "myscheme": "Vidyasiri food And Accommodation Scholarship Scheme",
     "why": ("Same scheme, words reordered and Accommodation spelled with one m on the "
             "Karnataka side.")},
    {"karnataka": "Interest Subsidy for Crop Loan, Pledge Loan, SHGs",
     "myscheme": "Interest Subvention Scheme",
     "why": ("Uncertain rather than confirmed: myScheme's record is thin enough that it "
             "may or may not be this line. Listed so a reader can check it.")},
]


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

def stratify(entries, target=210):
    """Deterministic stratified sample: book crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by head of account and
    picked at even spacing, so this returns the same rows on every machine and every run.
    parse/registry.py once returned a different answer each run because it iterated a set,
    and that manufactured false change events; nothing here iterates an unsorted anything.
    """
    alloc = sorted(r["be_lakh"] for r in entries if r.get("be_lakh"))
    cuts = [alloc[int(len(alloc) * f)] for f in (0.25, 0.5, 0.75)] if alloc else [0, 0, 0]

    def band(r):
        v = r.get("be_lakh")
        if not v:
            return "none"
        return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"

    def book(r):
        b = r.get("books") or []
        if "SCSP/TSP Allocations" in b:
            return "SCSPTSP"
        return "CB" if "Child Budget" in b else "GB"

    cells = {}
    for r in entries:
        cells.setdefault((book(r), band(r)), []).append(r)

    out = []
    for key in sorted(cells):
        rows = sorted(cells[key], key=lambda r: r["hoa"])
        # Proportional allocation with a floor of 4, so the sample is close to self
        # weighting and every stratum still gets enough rows to say anything about.
        n = min(len(rows), max(4, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % key, len(rows), len(idx)))
    return sorted(out, key=lambda x: x[0]["hoa"])


def myscheme_karnataka():
    """Scheme names myScheme lists for Karnataka. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("karnataka" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def sweep(rows, lo, hi):
    """Precision and recall at every threshold, so the operating point is visible."""
    out = []
    for t in range(lo, hi + 1):
        tp = sum(1 for x in rows if x["score"] >= t and x["label"] == "scheme")
        fp = sum(1 for x in rows if x["score"] >= t and x["label"] != "scheme")
        fn = sum(1 for x in rows if x["score"] < t and x["label"] == "scheme")
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        out.append({"threshold": t, "called_scheme": tp + fp,
                    "true_positive": tp, "false_positive": fp, "false_negative": fn,
                    "precision": round(pr, 3), "recall": round(rc, 3),
                    "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0})
    return out


def run(threshold=PUBLISH_THRESHOLD):
    ka = json.load(open(os.path.join(ROOT, "data", "karnataka", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(ka["entries"], key=lambda r: r["hoa"])

    lp = os.path.join(ROOT, "data", "karnataka", "labels.json")
    labels = json.load(open(lp, encoding="utf-8"))
    by_hoa = {x["hoa"]: x for x in labels["labels"]}

    listed = myscheme_karnataka()

    rows = []
    for r in entries:
        total, ev = score_entry(r["hoa"], r["name"], r.get("purpose"))
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        in_ms = any(probably_same(r["name"], k)[0] for k in listed)
        rows.append({
            "hoa": r["hoa"], "name": r["name"], "purpose": r.get("purpose"),
            "be_lakh": r.get("be_lakh"), "books": sorted(r.get("books") or []),
            "score": total, "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_karnataka": in_ms,
            "hand_label": by_hoa[r["hoa"]]["label"] if r["hoa"] in by_hoa else None,
        })

    # Validation on the probability sample. The audit set is a census of the published
    # region, so mixing it in would inflate precision at exactly the thresholds that
    # matter; it gets its own count below.
    scored = [{"hoa": x["hoa"], "name": x["name"], "score": x["score"],
               "label": by_hoa[x["hoa"]]["label"]}
              for x in rows
              if x["hoa"] in by_hoa and by_hoa[x["hoa"]].get("sample") != "audit"]
    scored.sort(key=lambda x: x["hoa"])
    lo = min(x["score"] for x in scored)
    hi = max(x["score"] for x in scored)

    # The held-out half. Labels were made before any weight was chosen, and the weights
    # were then fitted looking only at the even-indexed half, so the odd-indexed half is
    # the honest estimate. Reporting only the full-set number would flatter the classifier.
    dev = [x for i, x in enumerate(scored) if i % 2 == 0]
    held = [x for i, x in enumerate(scored) if i % 2 == 1]

    full_sweep = sweep(scored, max(lo, -8), hi)
    held_sweep = sweep(held, max(lo, -8), hi)
    at = next(x for x in full_sweep if x["threshold"] == threshold)
    at_held = next(x for x in held_sweep if x["threshold"] == threshold)

    # The audited census. Every row scoring 5 or more carries a hand label, from one set or
    # the other, so at those thresholds these are counts and not estimates.
    audited = sorted((x for x in rows if x["hoa"] in by_hoa),
                     key=lambda x: x["hoa"])
    covered_from = 5
    census = []
    for t in range(covered_from, hi + 1):
        pub = [x for x in audited if x["score"] >= t]
        bad = [x for x in pub if by_hoa[x["hoa"]]["label"] != "scheme"]
        census.append({
            "threshold": t, "published": len(pub), "not_schemes": len(bad),
            "precision": round((len(pub) - len(bad)) / len(pub), 3) if pub else 0.0,
            "the_errors": sorted(x["name"] for x in bad),
        })
    at_census = next(x for x in census if x["threshold"] == threshold)

    schemes = [x for x in rows if x["verdict"] == "scheme"]
    absent_all = [x for x in rows if not x["in_myscheme_karnataka"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_karnataka"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["hoa"]))

    out = {
        "built": utcnow(),
        "snapshot": ka.get("snapshot"),
        "state": "Karnataka",
        "cycle": ka.get("cycle"),
        "source": "data/karnataka/schemes.json",
        "question": ("Which of Karnataka's 969 scheme-wise budget rows are welfare "
                     "schemes, and which are institutions, establishment heads, asset "
                     "heads or accounting heads?"),
        "entries": len(rows),
        "publish_threshold": threshold,
        "classified_scheme": len(schemes),
        "classified_not_scheme": len(rows) - len(schemes),
        "ground_truth": {
            "file": "data/karnataka/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "why_not_myscheme": ("myScheme membership cannot be the ground truth here. A "
                                 "Karnataka row that matches a myScheme record from any "
                                 "state is a scheme 38.8% of the time against 34.1% for "
                                 "rows that match nothing, a lift of +0.047. The matches "
                                 "are coincidences of wording."),
            "labels": sorted(labels["labels"], key=lambda x: x["hoa"]),
        },
        "signals": SIGNALS,
        "signals_rejected": REJECTED_SIGNALS,
        "threshold_sweep": full_sweep,
        "threshold_sweep_held_out": held_sweep,
        "threshold_sweep_census": census,
        "validation": {
            "n_labelled": len(scored),
            "n_development": len(dev),
            "n_held_out": len(held),
            "at_publish_threshold": {
                "threshold": threshold,
                "precision": at["precision"],
                "recall": at["recall"],
                "true_positive": at["true_positive"],
                "false_positive": at["false_positive"],
                "false_negative": at["false_negative"],
            },
            "at_publish_threshold_held_out": {
                "threshold": threshold,
                "precision": at_held["precision"],
                "recall": at_held["recall"],
                "true_positive": at_held["true_positive"],
                "false_positive": at_held["false_positive"],
            },
            # The census is the number that decides the threshold, and it is a count
            # rather than an estimate: every row scoring 5 or more carries a hand label,
            # so the errors in the published list are enumerated, not inferred. The
            # stratified sample alone would have claimed 97.5% precision at threshold 5
            # on the strength of 40 rows; the census says 91.9%. A probability sample is
            # the right tool for recall, which cannot be censused, and the wrong one for
            # counting mistakes in a list short enough to read.
            "census_note": ("Every row at or above score 5 is hand labelled, so precision "
                            "at these thresholds is counted rather than estimated. Recall "
                            "still comes from the stratified sample, because the rows the "
                            "classifier rejects are too many to label exhaustively."),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": ("F1 peaks lower down the sweep, where roughly one published "
                           "name in six is not a scheme. Naming a scheme as hidden by a "
                           "government is an accusation, so this runs at the "
                           "high-precision end and accepts the recall loss."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_karnataka_records": len(listed),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": ("Absence is decided by parse/match.py's generous matcher against "
                        "the myScheme records tagged Karnataka, because claiming absence "
                        "should require that even a generous matcher finds nothing. The "
                        "surviving list is a floor: 580 of the 969 rows carry no purpose "
                        "line, and a real scheme with a plain name and no purpose line "
                        "cannot clear a high bar on the evidence the books print."),
        "absent_schemes": absent,
        # absent_distinct is the key every other state publishes and the one the site reads.
        # This file predates it and emitted only absent_schemes, so the site counted
        # Karnataka's absence claim as zero while still rendering its table from the other
        # key: the register's own headline was missing a state it was publishing on the
        # page below it. Karnataka's 72 rows carry 72 distinct names, so the de-duplicated
        # view and the full list are the same list, and it is written out under both names
        # rather than left for a reader of the JSON to work out.
        "absent_distinct": absent,
        "all_entries": rows,
    }
    write_json("data/karnataka/classification.json", out)
    return out


def check_sample():
    """Report which sampled rows have no hand label yet, so the set can be extended."""
    ka = json.load(open(os.path.join(ROOT, "data", "karnataka", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "karnataka", "labels.json"),
                            encoding="utf-8"))
    have = {x["hoa"] for x in labels["labels"]}
    frame = stratify(sorted(ka["entries"], key=lambda r: r["hoa"]))
    missing = [(r["hoa"], st, r["name"]) for r, st, _, _ in frame if r["hoa"] not in have]
    print(f"sampling frame {len(frame)} rows, labelled {len(have)}, "
          f"unlabelled {len(missing)}")
    for hoa, st, name in missing:
        print(f"  {hoa}  [{st}]  {name[:80]}")
    return missing


def main():
    ap = argparse.ArgumentParser(
        description="Classify Karnataka budget rows as welfare scheme or budget head.")
    ap.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    ap.add_argument("--check-sample", action="store_true",
                    help="list sampled rows that carry no hand label yet")
    a = ap.parse_args()
    if a.check_sample:
        check_sample()
        return
    o = run(a.threshold)
    v = o["validation"]
    print(f"karnataka rows classified: {o['entries']}")
    print(f"  scheme         {o['classified_scheme']:>5}")
    print(f"  not a scheme   {o['classified_not_scheme']:>5}\n")
    g = o["ground_truth"]
    print(f"ground truth: {g['labelled']} hand labels, {g['scheme']} scheme / "
          f"{g['not_scheme']} not_scheme, {g['borderline']} borderline\n")
    print(f"threshold sweep (precision, recall on all {v['n_labelled']} labels):")
    for s in o["threshold_sweep"]:
        mark = "  <- published" if s["threshold"] == o["publish_threshold"] else ""
        print(f"   {s['threshold']:>3}  called {s['called_scheme']:>4}  "
              f"precision {s['precision']:.3f}  recall {s['recall']:.3f}  "
              f"f1 {s['f1']:.3f}{mark}")
    p = v["at_publish_threshold"]
    h = v["at_publish_threshold_held_out"]
    print(f"\npublished at threshold {o['publish_threshold']}, not the F1 optimum "
          f"{v['f1_optimal_threshold']}:")
    print(f"  precision  {p['precision']:.1%}  ({p['true_positive']}/"
          f"{p['true_positive'] + p['false_positive']} labelled rows called scheme "
          f"really are)")
    print(f"  recall     {p['recall']:.1%}  ({p['false_negative']} real schemes scored "
          f"below the bar)")
    print(f"  held out   {h['precision']:.1%} precision on the {v['n_held_out']} rows no "
          f"weight was fitted to\n")
    print(f"absent from myScheme Karnataka and classified a scheme: "
          f"{o['absent_from_myscheme_and_classified_scheme']} of "
          f"{o['absent_from_myscheme_all_rows']} absent rows, "
          f"Rs {o['absent_cr']:,.0f} cr")
    for x in o["absent_schemes"][:10]:
        print(f"   Rs {(x['be_lakh'] or 0) / 100:>10,.0f} cr  score {x['score']:>3}  "
              f"{x['name'][:56]}")


if __name__ == "__main__":
    main()
