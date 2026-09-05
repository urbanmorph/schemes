"""
Classify Odisha Demand for Grants scheme codes: welfare scheme, or head of expenditure?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ only. Never fetches.

    data/odisha/labels.json          hand ground truth, the input
    data/odisha/classification.json  the verdicts, the output

READ THIS FIRST. Of the five states classified so far, ODISHA IS THE ONE WHOSE BOOKS DO NOT
SUPPORT THE PRECISION THE OTHER FOUR REACH. The counted precision at the publishing bar is
90.3%, against Karnataka's 91.9%, Andhra Pradesh's 95.7%, Tamil Nadu's 96.3% and Kerala's
97.4%, and it is counted on 31 published codes of which 3 are not schemes. That number is
published rather than engineered away, and the reason it cannot be raised is in
signals_rejected: the one instrument that carried Tamil Nadu is measured here and fails.
A reader who needs better than nine in ten should read the band at 12 and above, which is
two rows and not a register. See can_this_state_support_a_high_precision_classifier below.

parse/odisha.py pulls 1,628 four-digit scheme codes out of 44 Demand for Grants books, and
its own caveat already says the plain truth: the books file establishment and generic heads
at the same level as schemes, so "District Establishment", "Tahasil Establishment",
"Information, Education and Communication", "Stationery Offices" and "Emoluments of
Governor" sit alongside "Mukhya Mantri Kalakara Sahayata Yojana". 496 of the 1,628 codes
carry a Salaries detailed head, 569 name a body in their own title and 90 carry a CHARGED
provision. Set against myScheme's 85 Odisha records, essentially the whole 1,628 is absent
from the national citizen portal, and publishing that number as "schemes Odisha hides"
would be false. It would mean naming the High Court establishment and the Governor's
emoluments as schemes a government hid.

WHAT ODISHA PRINTS AND WHAT IT IS WORTH. Karnataka prints a purpose line and it was that
classifier's strongest signal at P(scheme) 0.947. Odisha prints no purpose line. It prints
something that looks like Tamil Nadu's substitute and is not: beneath each 4-digit scheme
code it prints the 5-digit SUB-SCHEME codes, 8,562 of them, and the first two digits of a
sub-scheme code are the standard object head class. 01 is Salaries, 08 Office Expenses, 21
Maintenance, 37 Major Works, 40 Scholarship and Stipend, 43 Subsidy. In Tamil Nadu the
equivalent field was the strongest signal in the file: rows where every object head was a
benefit transfer head were schemes 89.5% of the time. HERE THAT RULE MEASURES 0.125 OVER 8
DEVELOPMENT ROWS, below the base rate of 0.092 plus nothing, and it fails for a reason
worth stating: in Odisha the benefit-type classes are the small standing lines inside an
establishment block. Class 15 Clothing fires on the jails and the police, 24 Diet on the
hospitals and the correctional homes, 25 Medicine on the dispensaries, 38 Pension on the
state's own retired servants, 17 Rewards on "Reward to Police / Public". The chart of
accounts is there and it says almost nothing about whether the row is a scheme.

WHAT DOES WORK is the negative half of the same field, and it is exact rather than weak:

    every detailed head under the code is an establishment,      P(scheme) 0.000 over 44
      works or accounting head                                     development rows
    a Salaries detailed head under the code                      P(scheme) 0.000 over 61
    the name names a body                                        P(scheme) 0.000 over 79
    a general or administrative services major head              P(scheme) 0.000 over 47
    an asset or works word in the name                           P(scheme) 0.000 over 33
    the provision is CHARGED on the Consolidated Fund            P(scheme) 0.000 over 11

The classifier is therefore built the other way up from the other four: it is very good at
saying what is NOT a scheme and poor at saying what is. Its positives are weak, the
strongest being a benefit word in the name at 0.389 over 18 development rows, against a
base rate of 0.092. Karnataka's purpose line was 0.947 and Tamil Nadu's object head 0.895.
Nothing in Odisha comes near.

THE CHARGED COLUMN, which parse/odisha.py already separates and which was worth checking:
90 of the 1,628 codes carry a charged provision, expenditure charged on the Consolidated
Fund rather than voted by the Assembly. All 27 in the stratified sample are labelled
not_scheme, and all 11 in the development half. That is what the constitutional category
means: charged expenditure is debt service, the Governor's emoluments, judges' salaries and
decreed sums. It is a small, exact negative and it is used.

WHAT THE 4-DIGIT SCHEME CODE ENCODES, measured. The code is a serial and the serial is
morphology: the low block was assigned to the legacy establishment heads in something close
to alphabetical order and new schemes are appended at the top. It is monotone on the
development half, which is why it is used and why it is worth one point in each direction
and no more:

    code under 1000        P(scheme) 0.000 over 45 development rows
    code 1000 to 1999      P(scheme) 0.000 over 35
    code 2000 to 2999      P(scheme) 0.061 over 33
    code 3000 to 3499      P(scheme) 0.172 over 29
    code 3500 and above    P(scheme) 0.208 over 53

This is the same kind of signal as Tamil Nadu's sub-head letter block, it is a fact about
when the head was created rather than about what it buys, and it is weighted accordingly.

There are two label sets and they answer different questions.
  stratified, 390 rows   A probability sample across department families and the allocation
                         range. This is what the threshold sweep runs on.
  audit, 141 rows        Every remaining row the classifier scores 4 or above. With the 58
                         stratified rows already there, the two sets are a CENSUS of the
                         published region and of the five bands below it, so the published
                         list's error count is counted, not estimated. The audit was made
                         after the weights were fixed and was deliberately not fed back into
                         them, which is why its findings are in known_errors rather than
                         patched.

WHY THE CENSUS STARTS AT 4. The corpus puts 199 rows at score 4 or above, 273 at 3 and 349
at 2. 199 rows, of which 141 needed a new label, is comfortably readable one by one, and it
covers the published region plus the five bands below it. The census is small because the
score distribution is compressed at the top: only 46 rows score 8 or more and only 20 score
10 or more.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan or its waiver, free travel, a house, treatment for a named
                beneficiary class, or training in which the trainee is himself the
                beneficiary.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, buys the
                capacity of the delivery system rather than the benefit, discharges the
                state's obligation to its own serving or retired staff, or is an accounting
                or adjustment head.

Two lines did most of the work. First, THE PRINTED DETAILED HEAD DECIDES when the row's own
name does not: "Welfare of Fishermen" is not_scheme because the only detailed head printed
under it is "Development of Fisheries in collaboration with International Institutions",
and "Advertising, Sales and Publicity" is a scheme because the only detailed head under it
is "Providing Free Mobile Phones to farmers". Second, A MISSION IS NOT A SCHEME unless what
it hands over is printed somewhere. 100 of the 531 labels sat close enough to one of those
lines to be flagged borderline, and each carries the sentence that decided it.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. F1 peaks at threshold 4, where the
sample says precision is 44.8% and more than half the published names are not schemes.
Publishing runs at 9. The audit census settles that number:

    threshold  4   199 rows published, 105 are not schemes   precision 47.2%
    threshold  5   148 rows published,  70 are not schemes   precision 52.7%
    threshold  6    93 rows published,  36 are not schemes   precision 61.3%
    threshold  7    70 rows published,  22 are not schemes   precision 68.6%
    threshold  8    46 rows published,   7 are not schemes   precision 84.8%
    threshold  9    31 rows published,   3 are not schemes   precision 90.3%
    threshold 10    20 rows published,   3 are not schemes   precision 85.0%
    threshold 11    11 rows published,   1 is not a scheme   precision 90.9%
    threshold 12     2 rows published,   0 are not schemes   precision 100.0%

The break is between 8 and 9. Read the bands: the band at exactly 7 is 24 rows of which 15
are not schemes, a marginal precision of 37.5%; the band at 8 is 15 rows with 4 errors,
73.3%; the band at 9 is 11 rows with NO errors, 100%; and the band at 10 is 9 rows with 2
errors, 77.8%. That last figure is the honest headline of this file: THE SCORE DOES NOT
ORDER THE TOP OF THE LIST. Cumulative precision falls from 90.3% at threshold 9 to 85.0% at
10 and rises again to 90.9% at 11, because two of the three surviving errors score 10 and
one scores 11, higher than most of the real schemes. Raising the bar past 9 buys nothing
and costs eleven true positives.

The stratified sample alone would have said 83.3% at threshold 9, on the strength of 12
rows. The census counts 90.3%. Note the direction: here the probability sample was
pessimistic, as Andhra Pradesh's was and Karnataka's, Tamil Nadu's and Kerala's were not.
Precision is counted. Recall is estimated.

WHAT IT STILL GETS WRONG. All three surviving errors are the same failure mode and it is
the one Maharashtra has too: a MISSION named for a beneficiary class that buys convergence
or a service facility rather than a benefit. Dharti Aaba Janjatiya Gram Utkarsh Abhiyan at
11 is village saturation for tribal habitations; the State Hub for Empowerment of Women at
10 is an office; Mission Vatsalya's Child Helpline at 10 is a telephone line. Four more sit
at exactly 8 and are excluded only because they score lower: Mission Vatsalya itself, the
Aadhaar enrolment kit under POSHAN 2.0, Development of PVTGs and the Odisha Pusti Mission.
A penalty on the words Mission, Abhiyan, Hub and Helpline would fix all three published
errors at a stroke; it is not applied, because the fix was found by reading the audit and
refitting on the audit would destroy the one measurement in this file that counts errors
rather than estimating them.

WHAT THE MISSING PURPOSE LINE COSTS. Recall at threshold 9 is 25.0% on the stratified
sample and 22.7% on the held-out half, the lowest of the five states, and the two biggest
misses are the two biggest schemes in the state. Subhadra Yojana, Rs 10,145 crore of cash
paid to women, scores 7: a welfare major head, a sub-plan minor head, a code above 3000 and
the word Yojana, and nothing else, because "Subhadra" is a name and the only detailed heads
printed under it are Other Charges and a support line for self help groups. Samrudha
Krushaka Yojana, Rs 6,088 crore of price assistance to paddy growers, scores 5 for the same
reason. AAHAAR scores 6, Ayushman Bharat PMJAY 6, Biju Kanya Ratna 7 and PMAY's affordable
housing head 1. 504 of the 8,562 detailed heads in the books are literally called "Other
Charges", 596 sit in that class altogether, and 1,549 more sit in the state's 78-block where
a department may write whatever it likes. The published count is a floor on Odisha's schemes
and never a total, and the published rupee figure is a small fraction of what Odisha
actually transfers.
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

PUBLISH_THRESHOLD = 9

# Every row at or above this score carries a hand label, from the stratified set or the
# audit set. Precision at or above it is counted; below it, it is estimated from the
# stratified sample only. See the docstring for why this is 4.
CENSUS_FROM = 4


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written by reading the 1,627 distinct names and the
# 1,826 distinct sub-scheme names in the corpus, before any of the numbers in the
# docstring were computed, so the weights are fitted and the word choices are not.
# ---------------------------------------------------------------------------

# The first two digits of Odisha's 5-digit sub-scheme code are the standard object head
# class, and the classes below were read off the books themselves rather than assumed:
#   01 Salaries, 02 Wages, 03 Work Charged Salaries, 04 NMR and DLR Salaries, 06 Travel,
#   07 Leave Travel Concession, 08 Office Expenses and Electricity, 09 Rent Rates and
#   Taxes, 10 Hospitality, 11 Advertising and Publications, 12 Legal and Professional
#   Services, 13 Election charges, 14 Decretal Dues, 16 Arms and Ammunition, 18 Purchases,
#   19 Secret Service, 26 Sumptuary, 30 Motor Vehicles, 31 Tools and Plant, 32 Machinery
#   and Equipment, 33 Materials and Supplies, 34 Stationery.
ESTAB_OBJ = {"01", "02", "03", "04", "06", "07", "08", "09", "10", "11", "12", "13", "14",
             "16", "18", "19", "26", "30", "31", "32", "33", "34"}
#   21 Maintenance, 22 Project works, 28 Construction, 36 Minor Works, 37 Major Works.
WORKS_OBJ = {"21", "22", "28", "36", "37"}
#   23 Interest, 35 Share Capital Investment, 45 Disaster fund contributions, 48 Advances
#   and Loans, 49 Deduct-Recoveries and Inter-Account Transfers, 80 Devolution and Lump
#   Provisions, 91 amounts met from a Reserve Fund.
ACCOUNT_OBJ = {"23", "35", "45", "48", "49", "80", "91"}
#   15 Clothing and Bedding, 17 Rewards and Incentives, 24 Diet and Feeding, 25 Medicine,
#   29 Compensation and Ex-gratia, 38 Pension and Retirement Benefits, 39 Ex-gratia,
#   40 Scholarship and Stipend, 43 Subsidy, 47 Food grains. THIS GROUP IS MEASURED AND NOT
#   USED; see signals_rejected. It is the Tamil Nadu instrument and it does not transfer.
BENEFIT_OBJ = {"15", "17", "24", "25", "29", "38", "39", "40", "43", "47"}
#   41 Grants-in-aid, 42 Contributions. Transfers to bodies, and as uninformative here as
#   object head 309 was in Tamil Nadu: 502 of the 8,562 detailed heads are in class 41.
GRANT_OBJ = {"41", "42"}
#   20 Other Charges, 27 miscellaneous, and 78, the block in which a department writes its
#   own activity names. A code whose detailed heads are ALL in this group is a programme
#   rather than an establishment, which is the only thing this group says.
NEUTRAL_OBJ = {"20", "27", "78"}

# Minor heads are standardised across Indian government accounts: 001 Direction and
# Administration, 003 Training, 004 Research, 005 Investigation, 051 Construction,
# 052 Machinery and Equipment, 053 Maintenance and Repairs, 090 to 095 Secretariat and
# other establishments.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053", "090", "091", "092", "094",
               "095"}
# 911 Deduct - Recoveries of Overpayments, 902 Deduct - Amount met from a fund. 28 codes.
RECOVERY_MINOR = {"911", "902"}
# 789 Special Component Plan for Scheduled Castes, 793 and 794 the tribal sub-plans,
# 796 Tribal Area Sub-Plan. Odisha books 511 of its 1,628 codes on one of these.
SUBPLAN_MINOR = {"789", "793", "794", "796"}
# 2216 Housing, 2225 Welfare of SC ST and OBC, 2235 Social Security and Welfare,
# 2236 Nutrition, 2501 Special Programmes for Rural Development, 2505 Rural Employment.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2501", "2505"}
# The Organs of State, Fiscal Services and Administrative Services block, plus the three
# Secretariat heads 2052, 2251 and 3451 and the statistics head 3454.
ADMIN_MAJOR = {"2011", "2012", "2013", "2014", "2015", "2029", "2030", "2039", "2040",
               "2041", "2045", "2047", "2048", "2049", "2051", "2052", "2054", "2055",
               "2056", "2058", "2059", "2062", "2070", "2071", "2075", "2251", "3451",
               "3454", "3475"}

# Words that name the BODY receiving the money or the office spending it. Unlike Tamil
# Nadu, "school", "college", "hospital", "centre", "institute" and "institution" are KEPT
# here, and the measurement says they belong: the 22 development rows that carry one of
# those six words and none of the others are schemes 0.000 of the time, because in Odisha
# they name the institution ("Government Upper Primary School", "Medical College", "Police
# Hospital") and not the place a benefit is delivered.
BODY = {
    "university", "universities", "college", "colleges", "school", "schools", "institute",
    "institutes", "institution", "institutions", "corporation", "corporations", "board",
    "authority", "commission", "committee", "council", "academy", "agency", "society",
    "societies", "federation", "trust", "laboratory", "laboratories", "museum", "library",
    "libraries", "tribunal", "court", "courts", "bureau", "company", "ltd", "hospital",
    "hospitals", "dispensaries", "centre", "centres", "center", "panchayat", "panchayats",
    "parisad", "parishad", "samiti", "samities", "municipal", "nigam", "nigama", "bhawan",
    "bhavan", "sadan", "association", "associations", "organisation", "organisations",
    "directorate", "secretariat", "commissioner", "engineer", "department", "deptt",
    "office", "offices", "headquarters", "establishment", "estt", "cell", "wing", "staff",
}

# Words that name an accounting, administration or publicity operation. "grant" and
# "grants" are here rather than in BENEFIT, for the same reason as in Maharashtra.
ACCOUNTING = {
    "charges", "expenses", "expenditure", "interest", "loan", "loans", "deduct",
    "recoveries", "recovery", "fund", "funds", "computerisation", "computerization",
    "survey", "census", "audit", "monitoring", "evaluation", "publicity", "iec", "lump",
    "provision", "reserve", "administration", "administrative", "salaries", "salary",
    "governance", "statistics", "miscellaneous", "grants", "grant",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "buildings", "building", "works", "work", "maintenance", "repair",
    "repairs", "renovation", "rejuvenation", "improvement", "infrastructure", "road",
    "roads", "bridges", "canal", "canals", "dam", "drainage", "sewerage", "embankment",
    "irrigation", "land", "acquisition", "quarters", "modernisation", "upgradation",
    "installation", "installations", "equipment", "equipments", "machinery",
    "electrification", "depot", "depots", "furniture", "fixtures", "plantation",
}

# Words that name the thing a person receives.
BENEFIT = {
    "pension", "pensions", "scholarship", "scholarships", "stipend", "subsidy",
    "subsidies", "assistance", "incentive", "incentives", "insurance", "compensation",
    "relief", "allowance", "allowances", "free", "rebate", "waiver", "reimbursement",
    "kit", "kits", "nutrition", "food", "feeding", "diet", "meal", "uniform", "paridhan",
    "gruha", "awas", "sahayata", "protsahana", "bima", "aahaar", "laptops",
}

# Words that name who receives it.
BENEFICIARY = {
    "students", "student", "women", "woman", "girls", "girl", "farmers", "farmer",
    "fishermen", "fisherman", "artisans", "weavers", "weaver", "workers", "worker",
    "families", "family", "children", "child", "persons", "person", "youth", "widow",
    "disabled", "handicapped", "citizens", "households", "household", "destitute",
    "orphan", "poor", "poors", "aged", "senior", "tribal", "tribals", "tribe", "tribes",
    "scheduled", "backward", "minority", "minorities", "obc", "ebc", "dnt", "pvtgs",
    "beneficiaries", "kanya", "bunakar", "karigara", "janajati", "janjatiya", "drivers",
    "labour", "unemployed", "patients", "apprentices", "sportsperson", "refugees",
    "extermists", "impaired", "visually",
}

# Scheme-name morphology. The word "scheme" is deliberately absent: it appears in only 32
# of 1,628 names here and half of those are "Other Plan Schemes for ...".
MARKER = {"yojana", "yojna", "abhiyan", "abhijan", "mission", "karyakrama", "nidhi",
          "samarthya"}

ESTAB_LEAD = re.compile(
    r"^\s*(directorate|director\b|chief\s+engineer|superintending\s+engineer|"
    r"executive\s+engineer|estt\b|establishment of|office of|head\s*quarters?|headquarters|"
    r"district\s+establishment|field\s+establishment|administration of|commissioner)", re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def heads(entry):
    """(major heads, minor heads, object head classes) for one scheme code, as sets.

    A head of account in this corpus is printed MAJOR-SUBMAJOR-MINOR, and the object head
    class is the first two digits of the 5-digit sub-scheme code beneath the row. Sets,
    never lists, and every use below sorts before printing, because parse/registry.py once
    returned a different entry count on every run by iterating a set.
    """
    major, minor = set(), set()
    for h in entry.get("hoas") or []:
        p = (h or "").split("-")
        if p and p[0]:
            major.add(p[0])
        if len(p) > 2 and p[2]:
            minor.add(p[2])
    obj = {(s.get("code") or "")[:2] for s in entry.get("sub_schemes") or []}
    obj.discard("")
    return major, minor, obj


# The weights. Negative weights are larger than positive ones on purpose, and in Odisha
# they carry nearly all of the work: the file is good at saying what is not a scheme and
# poor at saying what is.
WEIGHTS = {
    "body": -3, "salaries": -3, "all_estab_obj": -3, "admin": -3, "works": -3,
    "recovery": -3, "charged": -2, "estab_lead": -2, "estab_minor": -2, "acct": -2,
    "capital": -2, "old_code": -1,
    "ben": 4, "marker": 3, "who": 3, "welfare": 2, "neutral_obj": 1, "subplan": 1,
    "new_code": 1,
}


def score_entry(name, major, minor, obj, charged, code):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic."""
    tk = tokens(name)
    major, minor, obj = set(major or ()), set(minor or ()), set(obj or ())
    ev = []
    total = 0

    def add(key, why):
        nonlocal total
        total += WEIGHTS[key]
        ev.append(["%+d" % WEIGHTS[key], why])

    # Structure first: what the state's own accounting classification says this is.
    if obj and obj <= (ESTAB_OBJ | WORKS_OBJ | ACCOUNT_OBJ):
        add("all_estab_obj", "every detailed head under this code is an establishment, "
                             "works or accounting head: " + ", ".join(sorted(obj)))
    if "01" in obj:
        add("salaries", "a Salaries detailed head under this code")
    rec = sorted(minor & RECOVERY_MINOR)
    if rec:
        add("recovery", "recovery or adjustment minor head " + ", ".join(rec))
    adm = sorted(major & ADMIN_MAJOR)
    if adm:
        add("admin", "general or administrative services major head " + ", ".join(adm))
    cap = sorted(m for m in major if m[:1] in "4567")
    if cap:
        add("capital", "capital outlay or loan major head " + ", ".join(cap))
    est = sorted(minor & ESTAB_MINOR)
    if est:
        add("estab_minor", "establishment or works minor head " + ", ".join(est))
    if charged:
        add("charged", "the provision is CHARGED on the Consolidated Fund, not voted")

    # What the name says it is.
    if ESTAB_LEAD.match(name or ""):
        add("estab_lead", "the name begins with an establishment word")
    acct = sorted(tk & ACCOUNTING)
    if acct:
        add("acct", "accounting or administration word in the name: " + ", ".join(acct[:3]))
    works = sorted(tk & WORKS)
    if works:
        add("works", "asset or works word in the name: " + ", ".join(works[:3]))
    body = sorted(tk & BODY)
    if body:
        add("body", "the name names a body: " + ", ".join(body[:3]))
    if code.isdigit() and int(code) < 2000:
        add("old_code", "scheme code " + code + ", in the legacy block below 2000")

    # Positive structure, then positive name evidence.
    wel = sorted(major & WELFARE_MAJOR)
    if wel:
        add("welfare", "welfare function major head " + ", ".join(wel))
    if obj and obj <= NEUTRAL_OBJ:
        add("neutral_obj", "every detailed head under this code is a programme head rather "
                           "than an establishment head: " + ", ".join(sorted(obj)))
    sub = sorted(minor & SUBPLAN_MINOR)
    if sub:
        add("subplan", "sub-plan minor head " + ", ".join(sub))
    if code.isdigit() and int(code) >= 3000:
        add("new_code", "scheme code " + code + ", in the block above 3000")
    ben = sorted(tk & BENEFIT)
    if ben:
        add("ben", "benefit word in the name: " + ", ".join(ben[:3]))
    who = sorted(tk & BENEFICIARY)
    if who:
        add("who", "named beneficiary class in the name: " + ", ".join(who[:3]))
    mark = sorted(tk & MARKER)
    if mark:
        add("marker", "scheme marker word in the name: " + ", ".join(mark[:2]))

    return total, ev


SIGNALS = [
    {"points": -3, "signal": "every detailed head under the code is an establishment, works "
                             "or accounting head",
     "measured": ("P(scheme) 0.000 over 44 development rows, base rate 0.092. Fires on 356 "
                  "of 1,628 codes. This is the negative half of the object head and it is "
                  "the only half that works in Odisha.")},
    {"points": -3, "signal": "a Salaries detailed head under the code",
     "measured": ("P(scheme) 0.000 over 61 development rows, fires on 496 of 1,628 codes. "
                  "Measured separately from the clause above and separately exact: the 47 "
                  "development rows that carry Salaries but are NOT wholly establishment "
                  "heads are also 0.000.")},
    {"points": -3, "signal": "the name names a body",
     "measured": ("P(scheme) 0.000 over 79 development rows, fires on 569 of 1,628 codes, "
                  "the largest exact negative in the file. School, college, hospital, "
                  "centre, institute and institution are in this vocabulary, where Tamil "
                  "Nadu pruned them out: the 22 development rows carrying one of those six "
                  "and none of the others measure 0.000, because in Odisha they name the "
                  "institution rather than where a benefit is delivered.")},
    {"points": -3, "signal": "a general or administrative services major head",
     "measured": "P(scheme) 0.000 over 47 development rows, fires on 357 of 1,628 codes"},
    {"points": -3, "signal": "an asset or works word in the name",
     "measured": "P(scheme) 0.000 over 33 development rows, fires on 272 of 1,628 codes"},
    {"points": -3, "signal": "recovery or adjustment minor head, 911 and 902",
     "measured": ("P(scheme) 0.000 over 5 development rows, fires on 28 of 1,628 codes. "
                  "Thin in the sample and exact in kind: these are accounting mirrors that "
                  "repeat the scheme's own name.")},
    {"points": -2, "signal": "the provision is CHARGED on the Consolidated Fund, not voted",
     "measured": ("P(scheme) 0.000 over 11 development rows and 0.000 over all 27 in the "
                  "stratified sample; 90 of the 1,628 codes carry a charged provision. "
                  "Charged expenditure is a constitutional category, not a budget habit: "
                  "debt service, the Governor's emoluments, judges' salaries and decreed "
                  "sums are charged and nothing a citizen applies for is.")},
    {"points": -2, "signal": "the name begins with an establishment word",
     "measured": "P(scheme) 0.000 over 16 development rows, fires on 110 of 1,628 codes"},
    {"points": -2, "signal": "establishment or works minor head, 001 003 004 005 051 052 "
                             "053 090 091 092 094 095",
     "measured": "P(scheme) 0.018 over 55 development rows, fires on 428 of 1,628 codes"},
    {"points": -2, "signal": "an accounting or administration word in the name",
     "measured": "P(scheme) 0.032 over 31 development rows, fires on 246 of 1,628 codes"},
    {"points": -2, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": "P(scheme) 0.033 over 30 development rows, fires on 253 of 1,628 codes"},
    {"points": -1, "signal": "scheme code below 2000",
     "measured": ("P(scheme) 0.000 over 80 development rows, fires on 657 of 1,628 codes. "
                  "Morphology and not meaning: the low block was assigned to the legacy "
                  "establishment heads in something close to alphabetical order. One point "
                  "and no more, for the same reason Tamil Nadu gave one point to its "
                  "sub-head letter block.")},
    {"points": 4, "signal": "a benefit word in the name",
     "measured": ("P(scheme) 0.389 over 18 development rows, the strongest positive in the "
                  "file, and it is worth saying how weak that is: Karnataka's purpose line "
                  "measured 0.947 and Tamil Nadu's object head 0.895. Fires on 113 of 1,628 "
                  "codes.")},
    {"points": 3, "signal": "a scheme marker word in the name",
     "measured": ("P(scheme) 0.364 over 22 development rows, fires on 120 of 1,628 codes. "
                  "0.381 over the 21 rows that do not also name a body. This is also the "
                  "signal that produces every surviving error, because Odisha calls its "
                  "convergence programmes Missions and Abhiyans too.")},
    {"points": 3, "signal": "a named beneficiary class in the name",
     "measured": ("P(scheme) 0.333 over 15 development rows, 0.455 over the 11 that do not "
                  "also name a body. Fires on 125 of 1,628 codes.")},
    {"points": 2, "signal": "welfare function major head, 2216 2225 2235 2236 2501 2505",
     "measured": ("P(scheme) 0.233 over 30 development rows, lift +0.141, and 0.333 over "
                  "the 21 that do not also name a body. Fires on 235 of 1,628 codes.")},
    {"points": 1, "signal": "every detailed head under the code is a programme head, 20 "
                            "Other Charges, 27 or the 78 block",
     "measured": ("P(scheme) 0.214 over 42 development rows, lift +0.122, and 0.265 over "
                  "the 34 that do not also name a body. Fires on 360 of 1,628 codes. It "
                  "says only that the code is a programme rather than an establishment, "
                  "which is why it is worth one point.")},
    {"points": 1, "signal": "sub-plan minor head, 789 793 794 796",
     "measured": ("P(scheme) 0.145 over 62 development rows, lift +0.053. Weak, and much "
                  "weaker than the same signal in Tamil Nadu (0.526), because Odisha books "
                  "511 of its 1,628 codes on a sub-plan head including its irrigation "
                  "projects, its office buildings and its road works.")},
    {"points": 1, "signal": "scheme code 3000 or above",
     "measured": ("P(scheme) 0.195 over 82 development rows, lift +0.103. Fires on 681 of "
                  "1,628 codes. The positive half of the same morphology signal, and "
                  "monotone with it: under 1000 measures 0.000 over 45 rows, 1000 to 1999 "
                  "0.000 over 35, 2000 to 2999 0.061 over 33, 3000 to 3499 0.172 over 29 "
                  "and 3500 and above 0.208 over 53.")},
]

REJECTED_SIGNALS = [
    {"signal": "every detailed head under the code is a BENEFIT TRANSFER head, the rule "
               "that was the strongest signal in Tamil Nadu",
     "measured": ("P(scheme) 0.125 over 8 development rows, against a base rate of 0.092. "
                  "The weaker form, ANY benefit transfer head under the code, measures 0.200 "
                  "over 15 development rows, a lift of +0.108. Tamil Nadu's equivalent "
                  "measured 0.895 over 19 rows."),
     "why": ("This is the most important rejection in the file and it is why Odisha cannot "
             "reach the precision the other states do. The state's chart of accounts is "
             "present and detailed, 8,562 sub-scheme codes under 1,628 scheme codes, and "
             "the benefit-type classes in it are the small standing lines inside an "
             "establishment block rather than a transfer to a citizen. Class 15 Clothing "
             "fires on the jails, the police and the correctional homes; 24 Diet on the "
             "hospitals and the homes; 25 Medicine on the dispensaries and the police "
             "hospital; 38 Pension on the state's own retired servants and the judges' "
             "family pensioners; 17 Rewards on 'Reward to Police / Public'. Fifty codes in "
             "the corpus have nothing but benefit classes under them and most of them are "
             "'Central Home', 'Police Hospital' and 'Pension to Govt. servants'. Tamil "
             "Nadu's object head separated 0.895 from 0.000; Odisha's separates nothing.")},
    {"signal": "the benefit words in the printed SUB-SCHEME names, read as a purpose line",
     "measured": ("A benefit word anywhere in a code's sub-scheme names measures P(scheme) "
                  "0.200 over 25 development rows. Restricted to the codes whose OWN name "
                  "carries no benefit word, which is the only case where it could add "
                  "anything, it measures 0.154 over 13 rows against a base of 0.092, a lift "
                  "of +0.062."),
     "why": ("Odisha prints 1,826 distinct sub-scheme names and reading a few of them makes "
             "them look like Karnataka's purpose line: 'Free Laptops to visually impaired "
             "students', 'Providing Free Mobile Phones to farmers', 'Financial Benefits for "
             "Implementation of the Revised Surrendered and Rehabilitation Scheme'. Measured "
             "as a signal they are not one, because 504 of the 8,562 are literally called "
             "'Other Charges', 517 'Office Expenses' and 489 'Salaries', 596 sit in the "
             "Other Charges class 20 altogether, and the informative ones sit on codes "
             "whose own name already says the same thing. They are used in the LABELLING rule, where a human reads them "
             "one at a time, and not in the scoring, where a vocabulary would have to read "
             "all 8,562.")},
    {"signal": "the name is a grant, assistance or subsidy paid TO a named body, the "
               "preposition test that carried Maharashtra",
     "measured": ("P(scheme) 0.500 over 4 development rows and 0.375 over all 8 in the "
                  "stratified sample, against a base rate of 0.103."),
     "why": ("It fires on 8 rows in a 390-row sample and points the WRONG WAY, which is what "
             "a signal fitted on four rows looks like. Odisha's terse naming does not put "
             "the recipient in the head-word: it writes 'Berhampur University', 'Utkal "
             "University' and 'Madrasa Education' where Maharashtra would write 'Grant in "
             "aid to ...'. The body vocabulary catches those rows directly, at 0.000 over 79 "
             "development rows, so nothing is lost.")},
    {"signal": "the name matches a myScheme record tagged Odisha",
     "measured": ("parse/odisha.py already measured this and recorded the result in "
                  "myscheme_join_defects: 37 joins produced, 22 wrong on inspection."),
     "why": ("This is the borrowed ground truth the hand labels replace, and here it is both "
             "bad and circular. Bad, because three fifths of the joins are wrong on a corpus "
             "this small. Circular, because the question the register asks is which budget "
             "rows are ABSENT from myScheme, so scoring a row higher for being present would "
             "systematically push down exactly the rows the answer is made of. Read "
             "myscheme_join_defects as evidence about parse/match.py, not about schemes.")},
    {"signal": "the department family the row belongs to",
     "measured": ("On all 390 stratified rows: WELFARE 0.212 over 52 rows, ECONOMY 0.133 "
                  "over 75, INFRA 0.103 over 97, SERVICE 0.063 over 79, GOVERNANCE 0.046 "
                  "over 87, against a base rate of 0.103."),
     "why": ("Real, a fivefold spread, and deliberately unused. It would score the demand "
             "book rather than the provision, and it would guarantee that a welfare scheme "
             "run by an infrastructure department could never clear the bar: PMAY Gramin is "
             "run by Panchayati Raj and the Odisha Transport Drivers Welfare Scheme by "
             "Transport. It is also the stratification axis, so scoring it would make the "
             "sample and the classifier agree with each other rather than with the books.")},
    {"signal": "the size of the allocation",
     "measured": ("The four allocation quartiles run 0.102, 0.068, 0.080 and 0.180 on all "
                  "390 stratified rows against a base of 0.103, and the nil band runs "
                  "0.054."),
     "why": ("Non-monotone: the first quartile is higher than the second and the third. A "
             "scheme is not larger or smaller than a head of expenditure in Odisha. Subhadra "
             "is thousands of crore and the pension to indigent sportsmen is a few lakh, "
             "while 'Major Irrigation Project' and 'Pension to Govt. servants' are larger "
             "than both.")},
    {"signal": "the row is funded at nil",
     "measured": "P(scheme) 0.056 over 18 development rows against a base of 0.092",
     "why": ("125 of the 1,628 codes carry no provision this year and the state means "
             "something by that: the code exists and is funded at nil. It is not evidence "
             "that the row is not a scheme, and a register of what a government does not "
             "publish should surface a parked scheme rather than hide it.")},
]

KNOWN_ERRORS = [
    {"name": "Dharti Aaba Janjatiya Gram Utkarsh Abhiyan (DA-JGUA) [3891]",
     "score": 11,
     "kind": "false positive, published at threshold 9, and the highest scoring row in the "
             "published list",
     "why": ("Worth saying plainly: score is not confidence, and here the single highest "
             "scoring error outranks almost every real scheme. DA-JGUA is village "
             "saturation for tribal habitations, roads and drains and community halls in "
             "villages with a tribal majority. It scores 11 because it sits on 2202 and 2225 "
             "with sub-plan minor heads, has a code above 3000, names a beneficiary class "
             "twice and carries the marker Abhiyan, and its only printed detailed heads are "
             "Central Share of CSS, State Share of CSS and Other Charges, which say "
             "nothing. Maharashtra's classifier makes exactly the same error on exactly the "
             "same programme.")},
    {"name": "State Hub for Empowerment of Women (SAMARTHYA) [3668] and Mission Vatsalya - "
             "Child Helpline [3742]",
     "score": 10,
     "kind": "false positive, published at threshold 9",
     "why": ("An office and a telephone line. Both sit on 2235 Social Security and Welfare "
             "with codes above 3000, both name a beneficiary class, and 'Hub' and 'Helpline' "
             "are in no vocabulary in this file. The word Mission earns the second one three "
             "points. Adding Hub, Helpline, Cell and Mission to a penalty list would remove "
             "all three published errors and would be principled, and it is not done because "
             "the fix was found by reading the audit.")},
    {"name": "The band at exactly 10: 9 rows of which 2 are not schemes",
     "score": 10,
     "kind": "the reason the bar is at 9 and not higher",
     "why": ("Cumulative precision is NOT monotone here and the reason is that the score "
             "does not order the top of the list: 90.3% at threshold 9, 85.0% at 10, 90.9% "
             "at 11. The band at exactly 9 is 11 rows with no errors at all; the band at 10 "
             "is 9 rows with 2. Raising the bar past 9 discards a clean band and keeps the "
             "errors above it. This is the clearest single piece of evidence that the "
             "Odisha books do not carry enough to rank as well as the other four states.")},
    {"name": "Mission VATSALYA [3519], Adhaar enrolment kit under Saksham Anganwadi and "
             "POSHAN 2.0 [3555], Development of PVTGs [3612], Odisha Pusti Mission [3941]",
     "score": 8,
     "kind": "false positive, excluded at threshold 9",
     "why": ("The same failure mode one band down, and the reason the bar is not at 8: the "
             "band at exactly 8 is 15 rows of which 4 are not schemes, a marginal precision "
             "of 73.3%, against 100% for the band at 9. Every one of the four is a mission "
             "or a purchase named for a beneficiary class. The Aadhaar enrolment kit is the "
             "same error Maharashtra publishes at score 9.")},
    {"name": "Subhadra Yojana [3862] at score 7, Rs 10,145 crore, and Samrudha Krushaka "
             "Yojana [3851] at score 5, Rs 6,088 crore",
     "score": "5 and 7",
     "kind": "false negative, and these are the two largest schemes in the Odisha budget",
     "why": ("The plainest measure of what the missing purpose line costs. Subhadra pays "
             "Rs 10,000 a year into a woman's account and scores 7: +2 for the welfare major "
             "head 2235, +1 for the sub-plan minor heads, +1 for a code above 3000 and +3 "
             "for the word Yojana. Nothing else fires, because Subhadra is a name and the "
             "only detailed heads printed under it are Other Charges and a support line for "
             "self help groups. Samrudha Krushaka pays a price assistance to paddy growers "
             "and scores 5, missing even the welfare major head because it sits on 2401 Crop "
             "Husbandry. Between them they are more money than everything this file "
             "publishes, so the published rupee figure is a small fraction of what Odisha "
             "transfers and must not be read as a total.")},
    {"name": "AAHAAR [3922] at score 6, Ayusman Bharat PMJAY [3844] at 6, Biju Kanya Ratna "
             "[3105] at 7, PMAY Affordable Housing and In-Situ Slum Redevelopment [3782] "
             "at 1, Supply of subsidised Rice [3448] at 4",
     "score": "1 to 7",
     "kind": "false negative, the rest of the recall cost",
     "why": ("Odisha's subsidised cooked meal, its health insurance, its girl child benefit "
             "and its urban housing are all excluded. AAHAAR and Biju Kanya Ratna are Odia "
             "brand names that say nothing to an English vocabulary and print only 'Other "
             "Charges' beneath them. PMJAY is caught by nothing but the word Yojana. The "
             "PMAY housing head is actively penalised, -2 for minor head 051 Construction, "
             "which is the accounting of the transfer it makes and not the transfer: the "
             "same defect parse/classify_tamilnadu.py recorded against its own object head "
             "309. Recall at the bar is 25.0%.")},
    {"name": "Mukhyamantri Kanya Vibaha Yojana [3948] at score 10 is a true positive that "
             "sits in the same band as two errors",
     "score": 10,
     "kind": "context for the band at 10",
     "why": ("Named here so the band at 10 is not read as uniformly bad. Seven of its nine "
             "rows are real schemes, including the marriage assistance for girls, the "
             "pre-matric scholarship for minority students and the old age pension to "
             "destitutes. The two errors in it are the two service facilities named above.")},
]


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

# Five department families, a fixed partition of the 44 demand books by their printed
# two-digit department number. The books cannot each be a stratum: 44 crossed with 5
# allocation bands is 220 cells and a sample large enough to fill them could not be
# labelled by hand. The families come out at 218 to 415 codes each.
FAMILIES = [
    ("WELFARE", ["11", "14", "36", "41", "44"]),
    ("SERVICE", ["09", "10", "12", "15", "25", "38", "39", "43"]),
    ("ECONOMY", ["06", "19", "22", "23", "24", "27", "31", "32", "33", "34", "40"]),
    ("INFRA", ["07", "13", "17", "20", "21", "28", "30", "37"]),
]


def family(entry):
    """The family of the lowest-numbered department funding this code.

    83 of the 1,628 codes are funded in more than one department. The lowest-numbered one
    is used so the stratum is a function of the row and not of dictionary order.
    """
    ds = sorted(entry.get("departments") or [])
    n = ds[0][:2] if ds else "00"
    for name, nums in FAMILIES:
        if n in nums:
            return name
    return "GOVERNANCE"


def stratify(entries, target=380):
    """Deterministic stratified sample: department family crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by scheme code and picked at
    even spacing, so this returns the same rows on every machine and every run.
    """
    alloc = sorted(r["be_lakh"] for r in entries if r.get("be_lakh"))
    cuts = [alloc[int(len(alloc) * f)] for f in (0.25, 0.5, 0.75)] if alloc else [0, 0, 0]

    def band(r):
        v = r.get("be_lakh")
        if not v:
            return "nil"
        return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"

    cells = {}
    for r in entries:
        cells.setdefault((family(r), band(r)), []).append(r)
    out = []
    for k in sorted(cells):
        rows = sorted(cells[k], key=lambda x: x["code"])
        n = min(len(rows), max(6, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda t: t[0]["code"])


def myscheme_odisha():
    """Scheme names myScheme lists for Odisha. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("odisha" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    An EXACT superset of probably_same rather than a speed-for-accuracy trade: every branch
    in probably_same that can return True requires the pair to share a content token, share
    a transliteration skeleton, or stand in an acronym relation, so a pair that shares none
    of the three cannot match.
    """
    tok, skel, acro = {}, {}, {}
    facts = {}
    for n in listed:
        t = set(_m.tokens(n))
        s = set(_m.skeletons(n))
        a = set(_m.acronyms(n))
        facts[n] = (t, s, a)
        for k in t:
            tok.setdefault(k, set()).add(n)
        for k in s:
            skel.setdefault(k, set()).add(n)
        for k in a:
            acro.setdefault(k, set()).add(n)
    return {"tok": tok, "skel": skel, "acro": acro, "facts": facts,
            "acronyms": sorted(acro)}


def myscheme_candidates(name, idx):
    """Every myScheme name that could possibly match this one, sorted."""
    t = set(_m.tokens(name))
    s = set(_m.skeletons(name))
    a = set(_m.acronyms(name))
    out = set()
    for k in t:
        out |= idx["tok"].get(k, set())
        out |= idx["acro"].get(k, set())
    for k in s:
        out |= idx["skel"].get(k, set())
    for k in a:
        out |= idx["tok"].get(k, set())
        for other in idx["acronyms"]:
            if k in other or other in k:
                out |= idx["acro"][other]
    return sorted(out)


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


def run(threshold=PUBLISH_THRESHOLD, verbose=False):
    od = json.load(open(os.path.join(ROOT, "data", "odisha", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(od["entries"], key=lambda x: x["code"])

    labels = json.load(open(os.path.join(ROOT, "data", "odisha", "labels.json"),
                            encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_odisha()
    idx = myscheme_index(listed)

    rows = []
    for r in entries:
        major, minor, obj = heads(r)
        total, ev = score_entry(r["name"], major, minor, obj, r.get("be_charged_lakh"),
                                r["code"])
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in myscheme_candidates(r["name"], idx)
               if probably_same(r["name"], n)[0]]
        rows.append({
            "key": r["code"],
            "code": r["code"],
            "name": r["name"],
            "departments": sorted(r.get("departments") or []),
            "hoas": sorted(r.get("hoas") or []),
            "major_heads": sorted(major),
            "minor_heads": sorted(minor),
            "object_heads": sorted(obj),
            "sub_schemes": sorted(s["name"] for s in (r.get("sub_schemes") or [])),
            "be_lakh": r.get("be_lakh"),
            "be_charged_lakh": r.get("be_charged_lakh"),
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_odisha": bool(hit),
            "myscheme_match": sorted(hit) or None,
            "hand_label": by_key[r["code"]]["label"] if r["code"] in by_key else None,
        })

    # Validation on the probability sample. The audit set is a census of the published
    # region, so mixing it in would inflate precision at exactly the thresholds that
    # matter; it gets its own count below.
    scored = [{"key": x["key"], "name": x["name"], "score": x["score"],
               "label": by_key[x["key"]]["label"]}
              for x in rows
              if x["key"] in by_key and by_key[x["key"]].get("sample") == "stratified"]
    scored.sort(key=lambda x: x["key"])
    lo = min(x["score"] for x in scored)
    hi = max(x["score"] for x in scored)

    # The held-out half. Labels were made before any weight was chosen, and the weights
    # were then fitted looking only at the even-indexed half, so the odd-indexed half is
    # the honest estimate.
    dev = [x for i, x in enumerate(scored) if i % 2 == 0]
    held = [x for i, x in enumerate(scored) if i % 2 == 1]

    full_sweep = sweep(scored, lo, hi)
    held_sweep = sweep(held, lo, hi)
    at = next(x for x in full_sweep if x["threshold"] == threshold)
    at_held = next(x for x in held_sweep if x["threshold"] == threshold)

    # The audited census. Every row scoring CENSUS_FROM or more carries a hand label, from
    # one set or the other, so at those thresholds these are counts and not estimates.
    audited = sorted((x for x in rows if x["key"] in by_key), key=lambda x: x["key"])
    census = []
    top = max(x["score"] for x in rows)
    for t in range(CENSUS_FROM, top + 1):
        pub = [x for x in audited if x["score"] >= t]
        corpus = [x for x in rows if x["score"] >= t]
        bad = [x for x in pub if by_key[x["key"]]["label"] != "scheme"]
        band = [x for x in pub if x["score"] == t]
        band_bad = [x for x in band if by_key[x["key"]]["label"] != "scheme"]
        census.append({
            "threshold": t,
            "rows_in_corpus": len(corpus),
            "rows_hand_labelled": len(pub),
            "published": len(pub),
            "not_schemes": len(bad),
            "precision": round((len(pub) - len(bad)) / len(pub), 3) if pub else 0.0,
            "band_at_exactly_this_score": len(band),
            "band_not_schemes": len(band_bad),
            "band_precision": round((len(band) - len(band_bad)) / len(band), 3)
            if band else 0.0,
            "the_errors": sorted("%s [%s]" % (x["name"], x["code"]) for x in bad),
        })
    at_census = next(x for x in census if x["threshold"] == threshold)

    schemes = [x for x in rows if x["verdict"] == "scheme"]
    absent_all = [x for x in rows if not x["in_myscheme_odisha"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_odisha"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per NAME as well as per scheme code. Odisha's codes are very nearly unique on
    # name already, 1,627 distinct names over 1,628 codes, so this view exists for
    # comparability with the other states rather than because it collapses much. The
    # allocations add, because two codes are two provisions.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"])
        if e is None:
            e = by_name[x["name"]] = {"name": x["name"], "departments": [], "codes": [],
                                      "be_lakh": 0.0, "score": x["score"],
                                      "evidence": x["evidence"]}
        for d in x["departments"]:
            if d not in e["departments"]:
                e["departments"].append(d)
        e["codes"].append(x["code"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["departments"] = sorted(r["departments"])
        r["codes"] = sorted(r["codes"])
        r["be_lakh"] = round(r["be_lakh"], 2)

    out = {
        "built": utcnow(),
        "snapshot": od.get("snapshot"),
        "state": "Odisha",
        "cycle": od.get("cycle"),
        "variant": od.get("variant"),
        "source": "data/odisha/schemes.json",
        "question": ("Which of Odisha's 1,628 Demand for Grants scheme codes are welfare "
                     "schemes a citizen can apply to, and which are establishment heads, "
                     "institutions, works, debt heads or accounting heads?"),
        "entries": len(rows),
        "distinct_names": len({x["name"].lower() for x in rows}),
        "counting_basis": (
            "EVERY COUNT HERE IS ON THE 1,628 SCHEME CODE BASIS unless the field name says "
            "distinct. The 4-digit code is Odisha's own identifier for a provision and it is "
            "the code the state's Gender Budget prints beside each scheme name; where the "
            "same code recurs under several demands parse/odisha.py has already added the "
            "provisions and named every department. The 1,628 codes carry 1,627 distinct "
            "names, so unlike Tamil Nadu and Maharashtra the two bases are almost the same "
            "list; absent_distinct is published anyway for comparability."),
        "publish_threshold": threshold,
        # The F1 optimum, the bar for the WEAKER claim: "this state's budget names
        # this as a scheme". It lived only in site/build.py, so the data could not
        # say which rows the site lists and anything else reading this file had to
        # guess. parse/cag_join.py guessed by skipping this state entirely.
        "listing_threshold": 4,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"].lower() for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "funded_at_nil": sum(1 for x in rows if not x.get("be_lakh")),
        "funded_at_nil_and_classified_scheme": sum(
            1 for x in schemes if not x.get("be_lakh")),
        "charged_rows": sum(1 for x in rows if x.get("be_charged_lakh")),
        "charged_and_classified_scheme": sum(
            1 for x in schemes if x.get("be_charged_lakh")),
        "salary_head_rows": sum(1 for x in rows if "01" in x["object_heads"]),
        "sub_schemes_read": sum(len(x["sub_schemes"]) for x in rows),
        "can_this_state_support_a_high_precision_classifier": (
            "Not to the standard the other four reach, and the honest answer is published "
            "rather than engineered around. Counted precision at the publishing bar is "
            "90.3% on 31 codes, against Karnataka's 91.9%, Andhra Pradesh's 95.7%, Tamil "
            "Nadu's 96.3% and Kerala's 97.4%. Three of the 31 published codes are not "
            "schemes and all three are named in known_errors. The cause is measured and not "
            "guessed: Odisha prints no purpose line, and the chart of accounts that "
            "substituted for one in Tamil Nadu is present here but says nothing, because its "
            "benefit-type classes are the standing lines inside jails, hospitals and homes "
            "rather than transfers to citizens (0.125 over 8 development rows, against Tamil "
            "Nadu's 0.895 over 19). What is left is short English names over a base rate of "
            "10%, and the strongest positive signal in the file measures 0.389. Cumulative "
            "precision is also not monotone above the bar, which is direct evidence that the "
            "score does not rank the top of the list. A reader who requires better than nine "
            "in ten should read the band at 12 and above, which is two rows and not a "
            "register. The published 31 are a floor and a weak one."),
        "ground_truth": {
            "file": "data/odisha/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "sets": labels["sets"],
            "why_not_myscheme": (
                "myScheme membership cannot be the ground truth here. parse/odisha.py "
                "produced 37 joins between these 1,628 codes and the Odisha myScheme records "
                "and read every one by eye: 22 are wrong. The defects are reproduced in "
                "myscheme_join_defects below. They are evidence about the matcher, not "
                "ground truth about schemes. Worse, the signal is circular: the question is "
                "which rows are absent from myScheme, so scoring presence would push down "
                "exactly the rows the answer is made of."),
            "labels": sorted(labels["labels"], key=lambda x: x["key"]),
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
            "base_rate_stratified": round(
                sum(1 for x in scored if x["label"] == "scheme") / len(scored), 3),
            "base_rate_development_half": round(
                sum(1 for x in dev if x["label"] == "scheme") / len(dev), 3),
            "base_rate_note": (
                "About one Odisha scheme code in ten is a welfare scheme, the lowest base "
                "rate of the five states: 16% of Tamil Nadu's Demand Book sub-heads, 24% of "
                "Maharashtra's Annual Scheme rows, 41% of Andhra Pradesh's scheme-wise rows "
                "and 55% of Karnataka's. That is a fact about the document before it is a "
                "fact about the state: Odisha files establishment and generic heads at the "
                "same level as schemes, so 'District Establishment', 'Stationery Offices' "
                "and 'Emoluments of Governor' each occupy a scheme code."),
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
            "census_note": (
                "Every row at or above score %d is hand labelled, so precision at these "
                "thresholds is counted rather than estimated. The census starts at %d "
                "because the corpus puts 199 rows there, 273 at score 3 and 349 at 2; 199 "
                "rows, of which 141 needed a new label, is comfortably readable and covers "
                "the published region plus the five bands below it. Recall still comes from "
                "the stratified sample, because the rows the classifier rejects are too many "
                "to label exhaustively." % (CENSUS_FROM, CENSUS_FROM)),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": (
                "F1 peaks at threshold 4, where the sample says precision is 44.8% and more "
                "than half the published names are not schemes. Naming a scheme as hidden by "
                "a government is an accusation, so this runs at the high-precision end and "
                "accepts the recall loss. The break in the census is between 8 and 9: the "
                "band at exactly 7 is 37.5% precise, the band at 8 is 73.3% and the band at "
                "9 is 100%. Cumulative precision is NOT monotone above the bar, 90.3% at 9, "
                "85.0% at 10 and 90.9% at 11, because two of the three surviving errors "
                "score higher than most of the real schemes. Raising the bar past 9 discards "
                "a clean band of eleven rows and keeps the errors above it."),
            "sample_versus_census": (
                "The stratified sample alone would have claimed 83.3% precision at threshold "
                "9, on the strength of 12 rows above the bar. The census counts 90.3%. It "
                "erred pessimistically here, as Andhra Pradesh's did, where Karnataka's, "
                "Tamil Nadu's and Kerala's flattered, which is the same lesson either way: a "
                "probability sample is the right tool for recall, which cannot be censused, "
                "and the wrong one for counting mistakes in a list short enough to read."),
            "what_the_missing_purpose_line_costs": (
                "Karnataka's books print a purpose line and it was that classifier's "
                "strongest signal at P(scheme) 0.947. Tamil Nadu prints none but prints the "
                "object head, worth 0.895. Odisha prints the object head too, in the first "
                "two digits of its 5-digit sub-scheme code, and it is worth 0.125. Recall at "
                "the published bar is 25.0% on the stratified sample and 22.7% on the "
                "held-out half, the lowest of the five states, and precision is the lowest "
                "too. The rows it loses are the two biggest schemes in the state: "
                "Subhadra Yojana, Rs 10,145 crore of cash to women, scores 7 and Samrudha "
                "Krushaka Yojana, Rs 6,088 crore of price assistance to paddy growers, "
                "scores 5. AAHAAR scores 6, Ayushman Bharat PMJAY 6 and Biju Kanya Ratna 7. "
                "504 of the 8,562 detailed heads Odisha prints are called 'Other "
                "Charges' and 1,549 more sit in the block where a department writes its own "
                "names."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_odisha_records": len(listed),
        "myscheme_record_count_note": (
            "This is counted live off data/myscheme/schemes/, every record whose "
            "beneficiaryState list mentions Odisha. parse/odisha.py's myscheme_join_summary "
            "below says 83 and that figure is hard coded there from an earlier count of the "
            "same directory. The two are reported side by side rather than reconciled, "
            "because a silently moving denominator is exactly the kind of thing a register "
            "should show rather than smooth over."),
        "myscheme_join_defects": od.get("myscheme_join_defects"),
        "myscheme_join_summary": od.get("myscheme_join_summary"),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_distinct_names": len({x["name"].lower() for x in absent}),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": (
            "Absence is decided by parse/match.py's generous matcher against the myScheme "
            "records tagged Odisha, because claiming absence should require that even a "
            "generous matcher finds nothing. Read that number against myscheme_join_summary: "
            "the matcher produced 37 joins over the whole corpus and 22 of them are wrong, so "
            "a row counted present may not be. The surviving list is a floor and a weak one: "
            "counted precision at the bar is 90.3%, the lowest of the five states, and recall "
            "is 25.0%. Read can_this_state_support_a_high_precision_classifier before "
            "quoting any number from this file."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/odisha/classification.json", out)
    return out


def check_sample():
    """Report which sampled or census rows have no hand label yet."""
    od = json.load(open(os.path.join(ROOT, "data", "odisha", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "odisha", "labels.json"),
                            encoding="utf-8"))
    have = {x["key"] for x in labels["labels"]}
    entries = sorted(od["entries"], key=lambda x: x["code"])
    frame = stratify(entries)
    missing = [(r["code"], st, r["name"]) for r, st, _, _ in frame if r["code"] not in have]
    print("sampling frame %d rows, labelled %d, unlabelled %d"
          % (len(frame), len(have), len(missing)))
    for k, st, name in missing:
        print("  [%s]  %s  %s" % (st, k, name[:80]))
    uncovered = []
    for r in entries:
        major, minor, obj = heads(r)
        if (score_entry(r["name"], major, minor, obj, r.get("be_charged_lakh"),
                        r["code"])[0] >= CENSUS_FROM and r["code"] not in have):
            uncovered.append(r["code"])
    print("census at score >= %d: %d rows unlabelled" % (CENSUS_FROM, len(uncovered)))
    for k in uncovered:
        print("  %s" % k)
    return missing, uncovered


def main():
    a = argparse.ArgumentParser(
        description="Classify Odisha Demand for Grants scheme codes as welfare scheme or "
                    "head of expenditure.")
    a.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    a.add_argument("--check-sample", action="store_true",
                   help="list sampled or census rows that carry no hand label yet")
    a.add_argument("--verbose", action="store_true")
    args = a.parse_args()
    if args.check_sample:
        check_sample()
        return
    o = run(args.threshold, verbose=args.verbose)
    v = o["validation"]
    print("odisha scheme codes classified: %d (%d distinct names)"
          % (o["entries"], o["distinct_names"]))
    print("  scheme         %5d  (%d distinct names)"
          % (o["classified_scheme"], o["classified_scheme_distinct_names"]))
    print("  not a scheme   %5d" % o["classified_not_scheme"])
    print("  of which carry a Salaries detailed head: %d, charged: %d\n"
          % (o["salary_head_rows"], o["charged_rows"]))
    g = o["ground_truth"]
    print("ground truth: %d hand labels, %d scheme / %d not_scheme, %d borderline"
          % (g["labelled"], g["scheme"], g["not_scheme"], g["borderline"]))
    print("              %d stratified, %d audit census\n"
          % (g["sets"]["stratified"]["n"], g["sets"]["audit"]["n"]))
    print("threshold sweep (precision, recall on the %d stratified labels, base rate %.3f):"
          % (v["n_labelled"], v["base_rate_stratified"]))
    for s in o["threshold_sweep"]:
        if s["threshold"] < 0:
            continue
        mark = "  <- published" if s["threshold"] == o["publish_threshold"] else ""
        print("   %3d  called %4d  precision %.3f  recall %.3f  f1 %.3f%s"
              % (s["threshold"], s["called_scheme"], s["precision"], s["recall"],
                 s["f1"], mark))
    print("\naudit census (every row at or above %d is hand labelled, so these are counts):"
          % CENSUS_FROM)
    print("   %3s  %8s %11s %10s | %8s %11s %10s"
          % ("t", "published", "not schemes", "precision", "band", "not schemes",
             "precision"))
    for s in o["threshold_sweep_census"]:
        mark = "  <- published" if s["threshold"] == o["publish_threshold"] else ""
        print("   %3d  %8d %11d %10.3f | %8d %11d %10.3f%s"
              % (s["threshold"], s["published"], s["not_schemes"], s["precision"],
                 s["band_at_exactly_this_score"], s["band_not_schemes"],
                 s["band_precision"], mark))
    p = v["at_publish_threshold"]
    h = v["at_publish_threshold_held_out"]
    c = v["at_publish_threshold_census"]
    print("\npublished at threshold %d, not the F1 optimum %d:"
          % (o["publish_threshold"], v["f1_optimal_threshold"]))
    print("  census precision  %.1f%%  (%d/%d published codes really are schemes, counted)"
          % (c["precision"] * 100, c["published"] - c["not_schemes"], c["published"]))
    print("  sample precision  %.1f%%  on %d stratified rows"
          % (p["precision"] * 100, v["n_labelled"]))
    print("  recall            %.1f%%  (%d real schemes scored below the bar)"
          % (p["recall"] * 100, p["false_negative"]))
    print("  held out          %.1f%% precision, %.1f%% recall on the %d rows no weight "
          "was fitted to" % (h["precision"] * 100, h["recall"] * 100, v["n_held_out"]))
    print("\n  THIS IS THE WEAKEST OF THE FIVE STATES. Read")
    print("  can_this_state_support_a_high_precision_classifier in the output before")
    print("  quoting any number from it.\n")
    print("absent from myScheme Odisha and classified a scheme: %d of %d absent codes, "
          "%d distinct names, Rs %s cr"
          % (o["absent_from_myscheme_and_classified_scheme"],
             o["absent_from_myscheme_all_rows"], o["absent_distinct_names"],
             format(o["absent_cr"], ",.0f")))
    for x in o["absent_distinct"][:12]:
        print("   Rs %10s cr  score %3d  %s"
              % (format((x["be_lakh"] or 0) / 100, ",.0f"), x["score"], x["name"][:58]))


if __name__ == "__main__":
    main()
