"""
Classify Maharashtra Annual Scheme rows: welfare scheme, or head of expenditure?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ only. Never fetches.

    data/maharashtra/labels.json         hand ground truth, the input
    data/maharashtra/classification.json the verdicts, the output

parse/maharashtra.py pulls 1,956 rows out of the ANNUAL SCHEME 2026-2027 (Departmentwise)
book, one per 10-digit state scheme code, and its own caveat already says the plain truth:
this is a superset of the schemes a citizen can apply to. "District and Other Roads",
"4705-Capital Outlay on Command Area Development", "Jail Department", "Works of Mechanical
Organisation" and three rows whose entire printed name is "Lumsum" are all in it. 450 of
the 1,956 sit on a capital outlay or loan major head and 524 name a body in their own
title. Set against myScheme's 85 Maharashtra records, essentially the whole 1,956 is absent
from the national citizen portal, and publishing that number as "schemes Maharashtra hides"
would be false. It would mean naming the jail department and the share capital of the
Vidarbha Irrigation Development Corporation as schemes a government hid.

WHAT IS DIFFERENT HERE. Karnataka's books print a purpose line, one sentence saying what
the money buys, and that was the strongest signal in parse/classify_karnataka.py at
P(scheme) 0.947. Maharashtra prints none. It prints no object head either, so Tamil Nadu's
substitute is not available: the 8-character BEAMS budget code is a 4-digit MAJOR head
followed by a 4-character serial within it, and there is no minor head and no object head
anywhere in the book. What Maharashtra prints instead is a LONG, DESCRIPTIVE ENGLISH NAME,
and the name is where almost all of the signal is. The single strongest thing in this file
is a preposition test, and it is the Andhra Pradesh finding arriving in a different form:

    a benefit word in a name that does NOT pay it TO a body    P(scheme) 0.828 over 29 rows
    a benefit word in a name that DOES pay it TO a body        P(scheme) 0.231 over 13 rows
    (base rate on the development half 0.240)

"Free power scheme for handloom weavers families upto 200 units per month" and "Grant in
Aid to Traditional Art & Art Groups" both carry a benefit word. Only the shape of the
sentence separates them, and in Maharashtra that shape is the head-word plus the
preposition: a name that BEGINS "Grant / Grants-in-aid / Assistance / Financial Assistance
/ Subsidy / Loan / Support ... to|for" is money for a body 89.7% of the time. Andhra
Pradesh needed the word THROUGH to rescue subsidies routed through welfare corporations;
Maharashtra does not, because the word appears in only 27 of 1,956 names and in exactly one
row of the development half. It is measured and rejected below rather than borrowed.

WHAT THE 10-DIGIT SCHEME CODE ENCODES, measured and not assumed, because it was worth
asking. It is not opaque and it is not a scheme type. Digits 1 and 2 are the cut of the
budget the row belongs to (11 GENERAL, 12 Scheduled Caste Component, 13 Tribal Component,
14 the four centrally sponsored codes that appear only in statement GN4, 15 and 16 two more
GENERAL blocks). Digits 3 and 4 are the SECTOR: 13 code groups against the 14 sector names
the book prints, and the mapping is one to one except for a handful of rows filed under a
block whose printed sector differs. Digits 5 and 6 are the SUB-SECTOR within that sector,
92 (sector, sub-sector) pairs of which 13 carry more than one printed sub-sector name.
Digits 7 to 10 are a serial. So the code carries the component, the sector and the
sub-sector, all three of which the book already prints as their own fields, and a serial.
The serial is the only part that could have carried anything the fields do not, and it does
not: codes with a serial under 50 are schemes 19.6% of the time against a base rate of
24.0%, a lift of -0.044. It is published in signals_rejected with that number.

There are two label sets and they answer different questions.
  stratified, 391 rows   A probability sample across department families and the allocation
                         range. This is what the threshold sweep runs on, because precision
                         and recall estimated on anything else would not generalise.
  audit, 240 rows        Every remaining row the classifier scores 5 or above. With the 60
                         stratified rows already there, the two sets are a CENSUS of the
                         published region and of the three bands below it, so the published
                         list's error count is counted, not estimated. The audit was made
                         after the weights were fixed and was deliberately not fed back into
                         them, which is why its findings are in known_errors rather than
                         patched.

WHY THE CENSUS STARTS AT 5. The corpus puts 300 rows at score 5 or above, 386 at 4 and 425
at 3. 300 rows, of which 240 needed a new label, is the largest set that can be read one by
one and labelled reliably by hand, and it covers the published region plus the three bands
below it, which is what the threshold argument needs. Below 5 the precision numbers in this
file are estimates from the stratified sample and are labelled as such.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan or its waiver, free power, free travel, a house, treatment
                for a named beneficiary class, or training in which the trainee is himself
                the beneficiary.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, buys the
                capacity of the delivery system rather than the benefit, discharges the
                state's obligation to its own serving or scheme staff, or is an accounting
                or adjustment head.

Two lines did most of the work and both are recorded in labels.json. First, A TRAINING HEAD
IS A SCHEME WHEN THE TRAINEE IS A CITIZEN and not when the trainee is the state's own staff:
"Residential Training for Competitive Examination for Dhangar Community student" is a
scheme, "Training to Government Employees" and "Organization of Training programmes,
workshops, seminars of Animal Husbandry extension for field staff" are not. Second, A
SATURATION MISSION IS NOT A SCHEME even when the habitation it saturates belongs to a named
community: Tanda Vasti Sudhar Yojana, Thakkar Bappa Adiwasi Vasti Improvement, PM JANMAN
and Dharti Aaba Janjatiya Gram Utkarsh Abhiyan build village infrastructure for a named
community, they carry a beneficiary class and a scheme marker in their names, and they are
the errors that survive publication. 96 of the 631 labels sat close enough to one of those
lines to be flagged borderline, and each carries the sentence that decided it.

WHAT ACTUALLY DISCRIMINATES. Measured on the 196 rows of the development half against a
base rate of 24.0%, which is itself the first finding: about one Maharashtra Annual Scheme
row in four is a welfare scheme, where 16% of Tamil Nadu's Demand Book sub-heads, 41% of
Andhra Pradesh's scheme-wise rows and 55% of Karnataka's were.

  what the name says, which is nearly all of it:
    a benefit word in a name that does not pay it TO a body   P(scheme) 0.828 over 29 rows
    a named beneficiary class in the name                     P(scheme) 0.568 over 44 rows
    a scheme marker word in the name                          P(scheme) 0.586 over 29 rows
    the name names a body                                     P(scheme) 0.020 over 51 rows
    the name is a grant or assistance paid TO a body          P(scheme) 0.103 over 29 rows
    an asset or works word in the name                        P(scheme) 0.091 over 44 rows
    an accounting or administration word in the name          P(scheme) 0.000 over 14 rows
    the name is share capital or a capital contribution       P(scheme) 0.100 over 10 rows
    the name begins with an establishment word                P(scheme) 0.000 over  7 rows

  the state's own accounting classification, which is only the major head:
    capital outlay or loan major head, 4xxx to 7xxx           P(scheme) 0.000 over 46 rows
    general or administrative services major head             P(scheme) 0.000 over 17 rows
    welfare function major head                               P(scheme) 0.571 over 42 rows

Two are worth pausing on. The FIRST is that the words "grant" and "aid" are NOT benefit
words in Maharashtra and are deliberately absent from the BENEFIT vocabulary: rows carrying
one of them are schemes 5.6% of the time over 18 development rows, because the book uses
"Grant in aid to ..." for a body 127 times. Karnataka and Tamil Nadu both counted "grant" as
a benefit word; here it is evidence in the other direction, and the measurement is published
in signals_rejected. The SECOND is that the capital major head is exact rather than weak.
All 46 development rows on a 4xxx to 7xxx head are not schemes, because in Maharashtra the
capital side of the budget is share capital into irrigation corporations, metro lines,
buildings and loans, and the housing schemes that would otherwise sit there are booked on
2216 instead.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py and
the other four state classifiers. F1 peaks at threshold 2, where the sample says precision
is 64.0% and one published name in three is not a scheme. Publishing runs at 8. The audit
census settles that number, because it counts errors rather than estimating them:

    threshold  5   300 rows published, 63 are not schemes   precision 79.0%
    threshold  6   211 rows published, 21 are not schemes   precision 90.0%
    threshold  7   149 rows published, 10 are not schemes   precision 93.3%
    threshold  8    96 rows published,  3 are not schemes   precision 96.9%
    threshold  9    70 rows published,  2 are not schemes   precision 97.1%
    threshold 11    12 rows published,  0 are not schemes   precision 100.0%

The break is between 7 and 8, and it is visible in the bands rather than the cumulative
column: the band at exactly 5 is 89 rows of which 42 are not schemes, a marginal precision
of 52.8%; the band at 6 is 62 rows with 11 errors, 82.3%; the band at 7 is 53 rows with 7
errors, 86.8%; and the band at 8 is 26 rows with 1 error, 96.2%. Adding the band at 7 would
take counted precision from 96.9% to 93.3%, which is below where the other four states
publish. Note that no row in the corpus scores exactly 10, so thresholds 10 and 11 name the
same 12 rows. Threshold 8 it is, and the three errors that survive are named in
known_errors rather than patched out.

The stratified sample alone would have said 100% at threshold 8, on the strength of 26
rows. The census counts 96.9%. Note the direction: here the probability sample was
flattering, as Karnataka's and Tamil Nadu's were and Andhra Pradesh's was not, which is the
same lesson either way. A sample of 391 rows leaves too few above the bar to state the
published list's precision to better than a few points, and which way it errs is luck.
Precision is counted. Recall is estimated, because the rows the classifier rejects are too
many to label exhaustively.

WHAT IT STILL GETS WRONG, and it is one failure mode plus two service facilities. The three
errors above the bar are the Aadhaar enrolment kits bought for anganwadi beneficiaries, the
181 women's helpline and the National Nutrition Mission: each names a beneficiary class,
each carries a benefit or marker word, and each buys equipment, a phone line or a
convergence programme rather than a benefit. Below the bar the same failure mode is
everywhere, and it is the saturation mission: PM JANMAN twice, Dharti Aaba Janjatiya Gram
Utkarsh Abhiyan, Tanda Vasti Sudhar Yojana and Pradhan Mantri Jan Vikas Karyakram all sit
at exactly 7 and are all village infrastructure wearing a beneficiary class in their names.
Adding a habitation-development penalty would fix six of the ten errors at threshold 7 and
would be principled, but the fix was found by reading the audit, and changing weights to
suit the audit would destroy the one measurement in this file that counts errors instead of
estimating them. It is named here instead.

WHAT THE MISSING PURPOSE LINE COSTS. Recall at threshold 8 is 28.3% on the stratified
sample and 35.6% on the held-out half, against Karnataka's 31.6%, Andhra Pradesh's 36.5%
and Tamil Nadu's 41.0% at their own published bars. It is the lowest of the five, and the
reason is visible in the bands: the band at exactly 7 is 53 rows of which 46 really are
schemes and the band at 6 is 62 rows of which 51 are, so the classifier can SEE about a
hundred more schemes than it publishes and cannot separate them from the eighteen
saturation missions and service facilities sitting beside them. A name is all Maharashtra
gives it. The published count is a floor on Maharashtra's schemes and never a total, and
the state could raise it tomorrow by printing the minor head and the object head it already
keeps in BEAMS beside each scheme code, which is what Tamil Nadu does.
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

PUBLISH_THRESHOLD = 8

# Every row at or above this score carries a hand label, from the stratified set or the
# audit set. Precision at or above it is counted; below it, it is estimated from the
# stratified sample only. See the docstring for why this is 5 and not lower.
CENSUS_FROM = 5


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written by reading the 1,889 distinct names in the
# corpus, before any of the numbers in the docstring were computed, so the weights
# are fitted and the word choices are not. Two choices are recorded honestly and
# both are measured in signals_rejected rather than argued: "grant" and "aid" are
# NOT in BENEFIT, and bare "share" and "capital" are NOT in ACCOUNTING.
# ---------------------------------------------------------------------------

# Major heads of the general and administrative services blocks, plus the three
# Secretariat heads and Statistics. 2011 State Legislature, 2014 Administration of
# Justice, 2029 Land Revenue, 2052 Secretariat-General Services, 2053 District
# Administration, 2055 Police, 2056 Jails, 2059 Public Works, 2070 Other Administrative
# Services, 2251 Secretariat-Social Services, 3451 Secretariat-Economic Services,
# 3454 Census, Surveys and Statistics.
ADMIN_MAJOR = {"2011", "2012", "2013", "2014", "2015", "2017", "2029", "2030", "2039",
               "2040", "2041", "2045", "2047", "2048", "2049", "2051", "2052", "2053",
               "2054", "2055", "2056", "2058", "2059", "2070", "2071", "2075", "2251",
               "3451", "3454", "3475"}

# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC, ST, OBC and Minorities, 2235 Social Security and Welfare,
# 2236 Nutrition, 2501 Special Programmes for Rural Development, 2505 Rural Employment.
# 2401 Crop Husbandry is deliberately absent even though it measures 0.632 over 19
# development rows, because that number is the farm missions and the loan waivers and
# those rows already clear the bar on their names; adding 2401 would also lift every
# research station and extension head in the department.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2501", "2505"}

# Words that name the BODY receiving the money, including the two tiers of local
# government Maharashtra devolves through, Zilla Parishad and Panchayat Samiti.
BODY = {
    "corporation", "corporations", "board", "boards", "authority", "directorate",
    "directorates", "commission", "committee", "council", "academy", "academies",
    "agency", "agencies", "department", "departments", "office", "offices",
    "headquarters", "society", "societies", "federation", "trust", "laboratory",
    "laboratories", "museum", "library", "libraries", "secretariat", "tribunal", "court",
    "courts", "bureau", "university", "universities", "institute", "institutes",
    "institution", "institutions", "company", "companies", "limited", "ltd",
    "undertaking", "undertakings", "mahamandal", "pradhikaran", "vidyapeeth", "parishad",
    "parishads", "samiti", "samitis", "municipal", "corporatoin", "mandal", "bank",
    "banks", "mills", "mill", "factory", "factories", "organisation", "organisations",
    "organization", "organizations", "cell", "wing", "commissioner", "engineer", "staff",
    "establishment", "establishments",
}

# Words that name an accounting, administration or publicity operation. Bare "share" and
# "capital" are deliberately NOT here: "(State Share)" and "(Central Share 100%)" are
# printed on hundreds of genuine centrally sponsored scheme rows. The share capital case
# is caught by a phrase instead, SHARE_CAPITAL below.
ACCOUNTING = {
    "lumsum", "lumpsum", "deduct", "recoveries", "recovery", "adjusted", "ways", "means",
    "computerisation", "computerization", "governance", "survey", "census", "monitoring",
    "evaluation", "audit", "publicity", "propaganda", "advertising", "investigation",
    "salary", "salaries", "honorarium", "administrative", "administration", "provision",
    "outlay", "expenditure", "reserved", "refund", "suspense", "contingency",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "constructions", "constrution", "construtiion", "building",
    "buildings", "bldg", "bldgs", "infrastructure", "infrastructural", "road", "roads",
    "works", "work", "maintenance", "repair", "repairs", "renovation", "upgradation",
    "upgrading", "gradation", "modernisation", "modernization", "equipment", "equipments",
    "machinery", "restoration", "dam", "dams", "reservoir", "reservoirs", "canal",
    "canals", "bridge", "bridges", "quarters", "acquisition", "land", "lands", "premises",
    "complex", "campus", "strengthening", "improvement", "improvements", "widening",
    "laying", "installation", "plantation", "afforestation", "electrification", "depot",
    "depos", "depots", "erection", "tanks", "tank",
}

# Words that name the thing a person receives. "grant", "grants" and "aid" are
# deliberately absent; see signals_rejected for the number that keeps them out.
BENEFIT = {
    "scholarship", "scholarships", "stipend", "stipends", "pension", "pensions",
    "subsidy", "subsidies", "free", "insurance", "bima", "compensation", "kit", "kits",
    "nutrition", "nutritious", "reimbursement", "allowance", "allowances", "relief",
    "meal", "meals", "gratia", "waiver", "rebate", "concession", "doles", "feeding",
    "marriage", "maternity", "vandana", "vandanam", "anudan", "vetan", "uniform",
    "uniforms", "sanman", "mahasanmaan", "awas", "gharkul", "treatment", "poshan",
    "exemption", "assistance", "incentive", "incentives", "spectacles", "food", "diet",
    "dole",
}

# Words that name who receives it. A row that names its beneficiary class is describing a
# transfer; a row that names none is usually describing an office, an asset or a mission.
BENEFICIARY = {
    "students", "student", "women", "woman", "girls", "girl", "farmers", "farmer",
    "weavers", "weaver", "fishermen", "fisherman", "beneficiaries", "beneficiary",
    "victims", "victim", "workers", "worker", "families", "family", "children", "child",
    "persons", "person", "youth", "widow", "widows", "disabled", "abled", "citizens",
    "households", "household", "artisans", "entrepreneurs", "mothers", "adolescent",
    "destitute", "orphan", "orphans", "poor", "aged", "senior", "tribal", "tribals",
    "tribes", "tribe", "scheduled", "backward", "minority", "minorities", "transgender",
    "labourers", "labour", "boys", "unemployed", "patients", "holders", "cultivators",
    "shetkari", "mahila", "ladaki", "ladki", "bahin", "vidyarthi", "adivasi", "castes",
    "caste", "navboudh", "vjnt", "sbc", "obc", "dnt", "ebc", "sebc", "nomadic",
    "landless", "growers", "needy", "janjati", "janjatiya", "lek",
}

# Scheme-name morphology. The word "scheme" itself is NOT here and is measured and
# rejected below: this is the Annual SCHEME book and the word appears in 485 of 1,956
# names, including "Schemes finanaced from receipts from Forest Development Tax".
MARKER = {"yojana", "yojna", "yojane", "abhiyan", "abhiyana", "mission", "karyakram",
          "nidhi", "samman", "sanman"}

# Maharashtra's capital side, in the state's own words. 97 rows.
SHARE_CAPITAL = re.compile(
    r"\bshare\s*capital\b|\bcapital\s+contribution\b|\bcapital\s+investment\b|"
    r"\bmargin\s+money\b", re.I)
# THE PREPOSITION TEST, and the strongest thing in this file. A name that BEGINS with a
# transfer head-word and then says "to" or "for" within the next few words is money for a
# body: "Grant in Aid to Urdu Ghar", "Financial Assistance to Shabri Tribal Development
# Corporation", "Loan to Rural /Urban Consumer Co-operative Societies". 216 rows.
RECIPIENT_BODY = re.compile(
    r"^\s*(grant|grants|grant\s*-?\s*in\s*-?\s*aid|grants\s*-?\s*in\s*-?\s*aid|"
    r"assistance|financial\s+assistance|f\.?\s*a\.?|loans?|subsidy|subsidies|support|aid)"
    r"\b[^,]{0,24}?\b(to|for)\b", re.I)
# Andhra Pradesh's preposition, measured here and dead: 27 names in 1,956 carry it and one
# of them is in the development half. See signals_rejected.
THROUGH = re.compile(r"\bthrough\b", re.I)
ESTAB_LEAD = re.compile(
    r"^\s*(directorate|director\b|estt\b|establishment of|office of|headquarters|"
    r"head office|regional office|jail department|strengthening of office)", re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def major_heads(budget_codes):
    """The 4-digit major head of every budget code on this scheme code, sorted.

    Maharashtra's 8-character BEAMS budget code is a 4-digit major head followed by a
    4-character serial. There is no minor head and no object head anywhere in the book,
    so the major head is the whole of the accounting evidence.
    """
    return sorted({(b or "")[:4] for b in (budget_codes or []) if b})


# The weights. Negative weights are larger than positive ones on purpose. A row that names
# a body and also carries benefit words, "Grants-in-aid for various Schemes being
# implemented by Jain Minority Development Economic Corporation", should have to work to
# clear the bar, because that is the row that would embarrass the published list.
WEIGHTS = {
    "capital": -4, "body": -3, "works": -3, "acct": -3, "recipient_body": -3, "admin": -3,
    "share_capital": -2, "estab_lead": -2,
    "benefit_direct": 4, "who": 3, "welfare": 2, "marker": 2,
}


def score_entry(name, majors):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic."""
    tk = tokens(name)
    maj = set(majors or ())
    to_a_body = bool(RECIPIENT_BODY.match(name or ""))
    ev = []
    total = 0

    def add(key, why):
        nonlocal total
        total += WEIGHTS[key]
        ev.append(["%+d" % WEIGHTS[key], why])

    # Structure first: the major head is all the accounting evidence there is.
    cap = sorted(m for m in maj if m[:1] in "4567")
    if cap:
        add("capital", "capital outlay or loan major head " + ", ".join(cap))
    adm = sorted(maj & ADMIN_MAJOR)
    if adm:
        add("admin", "general or administrative services major head " + ", ".join(adm))

    # What the name says it is.
    if SHARE_CAPITAL.search(name or ""):
        add("share_capital", "the name is share capital, a capital contribution, a "
                             "capital investment or margin money")
    if to_a_body:
        add("recipient_body", "the name is a grant, assistance, subsidy or loan paid TO "
                              "or FOR a named body")
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

    # Positive structure, then positive name evidence.
    wel = sorted(maj & WELFARE_MAJOR)
    if wel:
        add("welfare", "welfare function major head " + ", ".join(wel))
    ben = sorted(tk & BENEFIT)
    if ben and not to_a_body:
        add("benefit_direct", "benefit word in a name that does not pay it TO a body: "
            + ", ".join(ben[:3]))
    who = sorted(tk & BENEFICIARY)
    if who:
        add("who", "named beneficiary class in the name: " + ", ".join(who[:3]))
    mark = sorted(tk & MARKER)
    if mark:
        add("marker", "scheme marker word in the name: " + ", ".join(mark[:2]))

    return total, ev


SIGNALS = [
    {"points": -4, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": ("P(scheme) 0.000 over 46 development rows, base rate 0.240. Exact rather "
                  "than weak: 450 of the 1,956 rows sit on a capital or loan head and in "
                  "Maharashtra that side of the budget is share capital into irrigation "
                  "corporations, metro lines, buildings and loans to companies. The housing "
                  "schemes that would otherwise sit there are booked on 2216 instead.")},
    {"points": -3, "signal": "the name names a body",
     "measured": ("P(scheme) 0.020 over 51 development rows, the strongest name signal in "
                  "either direction. Fires on 524 of 1,956 rows. Zilla Parishad and "
                  "Panchayat Samiti are in this vocabulary deliberately: money to them is "
                  "devolution to another tier of government, and it costs the classifier "
                  "the handful of scheme rows Maharashtra pays out through them.")},
    {"points": -3, "signal": "an asset or works word in the name",
     "measured": "P(scheme) 0.091 over 44 development rows, fires on 402 of 1,956 rows"},
    {"points": -3, "signal": "an accounting or administration word in the name",
     "measured": "P(scheme) 0.000 over 14 development rows, fires on 171 of 1,956 rows"},
    {"points": -3, "signal": "the name is a grant, assistance, subsidy or loan paid TO or "
                             "FOR a named body",
     "measured": ("P(scheme) 0.103 over 29 development rows, fires on 216 of 1,956 rows. "
                  "This is the preposition test in its negative half. Where the same rows "
                  "also carry a benefit word they measure 0.231, against 0.828 for benefit "
                  "words in a name that does not begin this way.")},
    {"points": -3, "signal": "general or administrative services major head",
     "measured": ("P(scheme) 0.000 over 17 development rows, fires on 160 of 1,956 rows. "
                  "The block runs 2011 to 2075 plus the three Secretariat heads 2052, 2251 "
                  "and 3451 and the statistics head 3454.")},
    {"points": -2, "signal": "the name is share capital, a capital contribution, a capital "
                             "investment or margin money",
     "measured": ("P(scheme) 0.100 over 10 development rows, fires on 97 of 1,956 rows. "
                  "Weighted at -2 and not lower because 95 of those 97 also sit on a "
                  "capital major head and have already paid -4 for it.")},
    {"points": -2, "signal": "the name begins with an establishment word",
     "measured": "P(scheme) 0.000 over 7 development rows, fires on 54 of 1,956 rows"},
    {"points": 4, "signal": "a benefit word in a name that does not pay it TO a body",
     "measured": ("P(scheme) 0.828 over 29 development rows, the strongest signal in the "
                  "file and the substitute for the purpose line Maharashtra does not print. "
                  "The same benefit words inside a name that DOES begin 'Grant / Assistance "
                  "/ Subsidy ... to' measure 0.231 over 13 rows, and the two together, "
                  "which is a plain benefit-word signal, measure 0.643 over 42. The "
                  "preposition is worth 0.185 of P(scheme) on its own.")},
    {"points": 3, "signal": "a named beneficiary class in the name",
     "measured": "P(scheme) 0.568 over 44 development rows, fires on 406 of 1,956 rows"},
    {"points": 2, "signal": "welfare function major head, 2216 2225 2235 2236 2501 2505",
     "measured": ("P(scheme) 0.571 over 42 development rows, lift +0.331. Stronger than in "
                  "Andhra Pradesh (+0.141) and Tamil Nadu (+0.231) because Maharashtra books "
                  "its hostels and residential schools on 2225 alongside the scholarships "
                  "but books most of its institutions on 2202, 2205 and 2210 instead.")},
    {"points": 2, "signal": "a scheme marker word in the name",
     "measured": ("P(scheme) 0.586 over 29 development rows. Stronger than the same signal "
                  "in Tamil Nadu (0.286) and Karnataka, because Maharashtra brands its "
                  "transfers in Marathi and Hindi: Yojana, Abhiyan, Nidhi and Sanman. The "
                  "word 'scheme' is NOT in this vocabulary; see signals_rejected.")},
]

REJECTED_SIGNALS = [
    {"signal": "the serial part of the 10-digit scheme code",
     "measured": ("Codes whose last four digits are under 50 are schemes 19.6% of the time "
                  "over 102 development rows, against a base rate of 24.0%: a lift of "
                  "-0.044. Codes with a serial of 1,000 or more measure 0.500, on six "
                  "development rows, which is not a measurement."),
     "why": ("The code was worth taking apart and it turned out to carry nothing the book "
             "does not already print as a field. Digits 1 and 2 are the cut of the budget "
             "(11 GENERAL, 12 Scheduled Caste Component, 13 Tribal Component, 14 the four "
             "GN4-only codes, 15 and 16 two further GENERAL blocks). Digits 3 and 4 are the "
             "sector: 13 code groups against the book's 14 printed sector names, one to one "
             "apart from a handful of rows filed under a block whose printed sector differs. "
             "Digits 5 and 6 are the sub-sector, 92 (sector, sub-sector) pairs of which 13 "
             "carry more than one printed name. Digits 7 to 10 are a serial, and the serial "
             "is the only part that could have said something the component, sector and "
             "sub-sector fields do not. It does not. Tamil Nadu's sub-head letter block WAS "
             "a real signal at 0.377 against 0.076; Maharashtra's serial is not.")},
    {"signal": "the component of the budget the row belongs to, GENERAL, SCCS or TCS",
     "measured": ("On all 391 stratified rows: Tribal Component 0.457 over 35 rows, "
                  "Scheduled Caste Component 0.275 over 40, GENERAL 0.201 over 314. On the "
                  "development half the two sub-plan cuts disagree: TCS 0.706 over 17 rows "
                  "and SCCS 0.200 over 20."),
     "why": ("The two halves of the same idea point opposite ways on the development half, "
             "which is what a signal fitted on 37 rows looks like. It would also score the "
             "CUT OF THE BUDGET rather than the provision, and the sub-plan cuts are full of "
             "establishment: 'Construction of Hostels (OTSP)', 'Maintenance-Repairs Of Office "
             "Buildings (State Level Scheme)' and 'Opening and Maintenanace of Govt Hostels "
             "for sc Boys' are all in them. It is also close to the stratification axis, so "
             "scoring it would make the sample and the classifier agree with each other "
             "rather than with the book.")},
    {"signal": "the word 'scheme' in the name",
     "measured": ("P(scheme) 0.326 over 46 development rows against a base rate of 0.240, a "
                  "lift of +0.086. On all 391 stratified rows, 0.309 over 97."),
     "why": ("This is the ANNUAL SCHEME book and the word appears in 485 of the 1,956 names. "
             "The book prints '(Scheme)' as a suffix on hundreds of rows as a typesetting "
             "habit, and 'Schemes finanaced from receipts from Forest Development Tax' and "
             "'Scheme of Award to the Best Institutions under Social Justice Department' are "
             "both in the set. A word that fires on a quarter of the corpus for a lift of "
             "0.086 is noise with a large n.")},
    {"signal": "the words 'grant', 'grants' and 'aid' as benefit words",
     "measured": ("P(scheme) 0.056 over 18 development rows, against 0.240 base and 0.828 "
                  "for the benefit words that are kept."),
     "why": ("Karnataka and Tamil Nadu both counted 'grant' as a benefit word. In "
             "Maharashtra it is evidence in the other direction: the word 'grant' "
             "appears in 127 of the 1,956 names and 'aid' in 107, almost always in the "
             "shape 'Grant in aid to <body>'. Keeping them would have made the preposition test "
             "fight itself, since the same rows fire RECIPIENT_BODY.")},
    {"signal": "the name says the benefit is delivered THROUGH a body",
     "measured": ("27 of 1,956 names carry the word and exactly one of them is in the 196 "
                  "development rows, which is not a measurement."),
     "why": ("This is the signal that mattered in Andhra Pradesh, where the state routes "
             "individual subsidies through its welfare corporations and 'Economic Support "
             "Schemes through BC-A Corporation' had to be told apart from 'Assistance to "
             "A.P. Women Corporation'. Maharashtra does not write its budget that way: it "
             "names the corporation as the recipient and stops. Borrowing a weight from "
             "another state's corpus because the argument sounds right is exactly what this "
             "method exists to prevent, so it is measured and left out.")},
    {"signal": "the source of fund is a centrally sponsored scheme, or the name carries the "
               "book's '(Others 67)' or '(Umbrella NN)' tag",
     "measured": ("Source of fund CSS: P(scheme) 0.356 over 45 development rows, lift "
                  "+0.116; 0.333 over 93 on all 391 stratified rows. The '(Others 67)' tag: "
                  "0.359 over 39 development rows, lift +0.119. The '(Umbrella NN)' tag: "
                  "0.286 over 7 rows."),
     "why": ("Real but small, and it is the same fact three times: all three mark a "
             "centrally sponsored scheme. A centrally sponsored scheme is as often a mission "
             "funding the delivery system as a transfer to a household. The National Health "
             "Mission, Samagra Shiksha, AMRUT, Jal Jeevan Mission, PM JANMAN and Project "
             "Tiger all carry the tag. At a lift of 0.116 it would have added a point to "
             "nearly a quarter of the corpus and moved the wrong rows.")},
    {"signal": "the size of the allocation",
     "measured": ("The four allocation quartiles run 0.213, 0.182, 0.255 and 0.278 on all "
                  "391 stratified rows against a base of 0.235, and the nil band runs "
                  "0.267."),
     "why": ("Non-monotone and nearly flat: the nil band is higher than two of the four "
             "quartiles. A scheme is not larger or smaller than a head of expenditure in "
             "Maharashtra. Mukhyamantri Mazi Ladaki Bahin is Rs 21,000 crore and the "
             "grazing subsidy to shepherd families is Rs 5 crore, while Mumbai Metro Line "
             "4 and 4A is Rs 1,208 crore and 'Numismatic Society' is Rs 1 lakh.")},
    {"signal": "the department family the row belongs to",
     "measured": ("On all 391 stratified rows: WELFARE 0.423 over 97 rows, ECONOMY 0.270 "
                  "over 89, SERVICE 0.188 over 101, INFRA 0.094 over 64, GOVERNANCE 0.050 "
                  "over 40, against a base rate of 0.235."),
     "why": ("Real, an eightfold spread, and deliberately unused. It would score the "
             "department rather than the provision, and it would guarantee that a welfare "
             "scheme run by an infrastructure department could never clear the bar: PMAY "
             "Urban is run by Housing, Jal Jeevan Mission by Water Supply and the solar "
             "agricultural pump subsidy by Energy. It is also the stratification axis, so "
             "scoring it would make the sample and the classifier agree with each other "
             "rather than with the book.")},
    {"signal": "the row is funded at nil",
     "measured": "P(scheme) 0.273 over 11 development rows against a base of 0.240",
     "why": ("99 of the 1,956 codes carry no provision this year and the state means "
             "something by that: the scheme code exists and is funded at nil. It is not "
             "evidence that the row is not a scheme, and a register of what a government "
             "does not publish should surface a parked scheme rather than hide it.")},
    {"signal": "the name matches a myScheme record tagged Maharashtra",
     "measured": ("parse/maharashtra.py already measured this and recorded the result in "
                  "myscheme_join_defects: 167 joins produced, 131 wrong on inspection. Of "
                  "myScheme's 84 Maharashtra records only 17 have a sound join at all, and "
                  "125 of the 131 wrong joins come from one hole, the community abbreviation "
                  "VJNT being read as a scheme acronym, which fanned six myScheme records "
                  "out to every one of the 21 register rows whose name contains it."),
     "why": ("This is the borrowed ground truth the hand labels replace, and here it is both "
             "bad and circular. Bad, because a matcher that joins 'Tanda Vasti Sudhar Yojana "
             "For VJNT And SBC' to 'Training Of Motor Driving To VJNT, SBS & OBC' 125 times "
             "is measuring its own acronym rule and not the schemes. Circular, because the "
             "question the register asks is which budget rows are ABSENT from myScheme, so "
             "scoring a row higher for being present would systematically push down exactly "
             "the rows the answer is made of. Read myscheme_join_defects as evidence about "
             "parse/match.py, not about schemes.")},
]

KNOWN_ERRORS = [
    {"name": "Procurement of Adhar Enrolment Kits for enrollment of Anganwadi "
             "Beneficiaries(Others 67) [1111170093]",
     "score": 9,
     "kind": "false positive, published at threshold 8",
     "why": ("The highest scoring error in the published list, which is worth saying plainly: "
             "score is not confidence. It sits on 2236 Nutrition (+2), names a beneficiary "
             "class (+3), carries the benefit word 'kits' in a name that does not pay it to a "
             "body (+4), and buys enrolment hardware. The word 'procurement' is not in the "
             "ACCOUNTING vocabulary and 'kit' is in BENEFIT because a Baby Care Kit and a "
             "science kit really are benefits. This is the cost of that word and it is one "
             "row.")},
    {"name": "Toll free \"181 Womens Helpline\" to provide urgent information and assistance "
             "to distressed women in the state [1111170108]",
     "score": 9,
     "kind": "false positive, published at threshold 8",
     "why": ("A telephone service, not a benefit. It scores 9 because it is on 2235 Social "
             "Security and Welfare, names women twice, and says 'assistance to distressed "
             "women' without ever naming a body, so the preposition test does not fire: "
             "RECIPIENT_BODY looks at the START of the name and this name starts with 'Toll "
             "free'. The Child Helpline under Mission Vatsalya fails the same way at 7 and "
             "is excluded only because it scores lower.")},
    {"name": "National Nutrition Mission(Others 67) [1111170094]",
     "score": 8,
     "kind": "false positive, published at threshold 8, and the row that sets the bar",
     "why": ("POSHAN Abhiyaan buys convergence, technology and behaviour change, not food; "
             "the food is the ICDS diet expenses row beside it, which is labelled a scheme. "
             "It scores exactly 8 on a welfare major head (+2), the benefit word 'nutrition' "
             "(+4) and the marker 'mission' (+2), with no penalty at all, because its name is "
             "three words long and none of them names a body or a work. A three-word name is "
             "the hardest case for a classifier that reads names.")},
    {"name": "Pradhan Mantri Janjati Adivasi Nyaya Maha Abhiyan (PM JANMAN) [1302100003 and "
             "1311270102], Dharti Aaba Janjatiya Gram Utakrsh Abhiyan (DA-JGUA) [1311270105], "
             "Tanda Vasti Sudhar Yojana For VJNT And SBC [1111120008], Pradhan Mantri Jan "
             "Vikas Karyakram for Minority Concentrated Areas [1111190026]",
     "score": 7,
     "kind": "false positive, excluded at threshold 8, and the reason the bar is where it is",
     "why": ("The single failure mode that produces most of the errors below the bar, and it "
             "is structural rather than a slip. Every one of these is a SATURATION MISSION: "
             "it names a community, carries a scheme marker, sits on a welfare major head, "
             "and spends on roads, drains, houses and community halls inside that community's "
             "habitations. Nothing in a Maharashtra budget row distinguishes 'Thakkar Bappa "
             "Adiwasi Vasti Improvement Programme', which is not a scheme, from 'Shabari "
             "Tribal Housing Scheme', which is, except the word 'improvement' that one of "
             "them happens to print. Adding a habitation-development penalty on Vasti, Gram, "
             "Tanda, Basti and Area would fix six of the ten errors at threshold 7 and would "
             "be principled. It is not done, because the fix was found by reading the audit "
             "and refitting on the audit would destroy the one measurement in this file that "
             "counts errors rather than estimating them.")},
    {"name": "The band at exactly 7: 53 rows of which 7 are not schemes",
     "score": 7,
     "kind": "the recall the bar costs",
     "why": ("46 of the 53 rows at exactly 7 really are schemes, and so are 51 of the 62 at "
             "exactly 6. The classifier can see about a hundred more schemes than it "
             "publishes and cannot separate them from the eighteen saturation missions and "
             "service facilities sitting beside them, which is why recall at the bar is 28.3% "
             "and the lowest of the five states. Publishing at 7 instead would take counted "
             "precision from 96.9% to 93.3%.")},
    {"name": "Mukhyamantri Mazi Ladaki Bahin [1111170117] at score 5, Lek Ladaki [1111170111] "
             "at score 5, Asmita Yojana [1102010050] at score 4, Aam Aadmi Bima Yojana "
             "[1111210081] at score 4",
     "score": "4 and 5",
     "kind": "false negative, and it is the state's own brands",
     "why": ("Maharashtra's largest single scheme, Rs 21,000 crore of cash paid monthly to "
             "women, is excluded. Its name is four Marathi words and an English vocabulary "
             "reads only 'ladaki' and 'bahin' from BENEFICIARY and 'mazi' from nothing; there "
             "is no benefit word, no marker, and 2235 gives it +2. Lek Ladaki, Asmita Yojana "
             "and Aam Aadmi Bima Yojana fail the same way. A Marathi scheme name says almost "
             "nothing to a vocabulary of English benefit words, and unlike Tamil Nadu there "
             "is no object head to rescue it. This is the single largest cost of the missing "
             "purpose line and it is worth more rupees than everything the file publishes.")},
    {"name": "Free Supply of a benefit booked as a grant to a Zilla Parishad: 'Grant to Zilla "
             "Parishad for Free Uniform and Writing Material in 103 Development Blocks for "
             "the Students of Standard Ist to IVth' [1111010086]",
     "score": 3,
     "kind": "false negative, and it is the price of the preposition test",
     "why": ("An unambiguous in-kind benefit to a named beneficiary class, penalised twice "
             "for the route it takes: -3 for beginning 'Grant to' and -3 for naming Zilla "
             "Parishad. Both penalties are right on average and both are wrong here. This is "
             "the same defect parse/classify_tamilnadu.py recorded against its own object "
             "head 309: charging a row for the accounting of the transfer it makes.")},
]


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

# Five department families, a fixed partition of the 56 departments the book names. The
# departments cannot each be a stratum: 56 crossed with 5 allocation bands is 280 cells,
# and a sample large enough to fill them could not be labelled by hand. The partition is
# by what the department does, written before the labels were made, and the five families
# come out at 179 to 513 rows each.
FAMILIES = [
    ("WELFARE", ["Social Justice", "Other Backward Bahujan Welfare", "Tribal Development",
                 "Persons with Disabilities Welfare Department", "Minorities Development",
                 "Women and Child Development", "Labour", "Relief and Rehabilitation",
                 "Housing"]),
    ("SERVICE", ["Public Health", "Medical Education and Drug", "School Education",
                 "Higher Education", "Technical Education",
                 "Skill, Employment, Entrepreneurship and Innovation Department",
                 "Sports", "Cultural Affairs", "Marathi Language", "Food and Civil Supply",
                 "Food & Drug Administration", "Water Supply and Sanitation"]),
    ("ECONOMY", ["Agriculture", "Animal Husbandry", "Fisheries", "Horticulture",
                 "Dairy Development", "Forest", "Co-operation", "Marketing", "Textile",
                 "Industry", "Tourism", "Soil & Water Conservation", "Kharland",
                 "Environment & Climate Change"]),
    ("INFRA", ["Water Resources", "Command Area Development Authority",
               "Public Works - Roads (Excluding Public Undertakings)",
               "Public Works - Roads (Public Undertakings)", "Public Works - Building",
               "Urban Development", "Rural Development", "Energy", "Home - Transport",
               "Home - Ports", "Information Technology"]),
]


def family(dept):
    for name, depts in FAMILIES:
        if dept in depts:
            return name
    return "GOVERNANCE"


def stratify(entries, target=380):
    """Deterministic stratified sample: department family crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by scheme code and picked
    at even spacing, so this returns the same rows on every machine and every run.
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
        cells.setdefault((family(r["department"]), band(r)), []).append(r)
    out = []
    for k in sorted(cells):
        rows = sorted(cells[k], key=lambda x: x["code"])
        # Proportional allocation with a floor of 6, so the sample is close to self
        # weighting and every stratum still gets enough rows to say anything about.
        n = min(len(rows), max(6, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda t: t[0]["code"])


def myscheme_maharashtra():
    """Scheme names myScheme lists for Maharashtra. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("maharashtra" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    An EXACT superset of probably_same rather than a speed-for-accuracy trade: every
    branch in probably_same that can return True requires the pair to share a content
    token, share a transliteration skeleton, or stand in an acronym relation, so a pair
    that shares none of the three cannot match. The one branch this does not index
    exactly is the prefix rule for a name made entirely of stop words, which cannot occur
    in a scheme name.
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
    mh = json.load(open(os.path.join(ROOT, "data", "maharashtra", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(mh["entries"], key=lambda x: x["code"])

    labels = json.load(open(os.path.join(ROOT, "data", "maharashtra", "labels.json"),
                            encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_maharashtra()
    idx = myscheme_index(listed)

    rows = []
    for r in entries:
        maj = major_heads(r.get("budget_codes"))
        total, ev = score_entry(r["name"], maj)
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in myscheme_candidates(r["name"], idx)
               if probably_same(r["name"], n)[0]]
        rows.append({
            "key": r["code"],
            "code": r["code"],
            "name": r["name"],
            "department": r["department"],
            "sector": r["sector"],
            "sub_sector": r["sub_sector"],
            "component": r["component"],
            "statement": r["statement"],
            "sources": sorted(r.get("sources") or []),
            "budget_codes": sorted(r.get("budget_codes") or []),
            "major_heads": maj,
            "be_lakh": r.get("be_lakh"),
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_maharashtra": bool(hit),
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
    # the honest estimate. Reporting only the full-set number would flatter the classifier.
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
    absent_all = [x for x in rows if not x["in_myscheme_maharashtra"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_maharashtra"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per NAME as well as per scheme code, because Maharashtra votes the same
    # scheme separately in the GENERAL, Scheduled Caste Component and Tribal Component
    # cuts under three different scheme codes: Pradhan Mantri Matru Vandana Yojana appears
    # four times. Publishing the codes would print it four times down a page and read as
    # four findings. The allocations add, because the three cuts are disjoint scheme codes
    # and separate provisions rather than overlapping views of one figure, which is
    # parse/maharashtra.py's own finding. The score is the best any code achieved.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"])
        if e is None:
            e = by_name[x["name"]] = {"name": x["name"], "departments": [], "codes": [],
                                      "components": [], "be_lakh": 0.0, "score": x["score"],
                                      "evidence": x["evidence"]}
        if x["department"] not in e["departments"]:
            e["departments"].append(x["department"])
        if x["component"] not in e["components"]:
            e["components"].append(x["component"])
        e["codes"].append(x["code"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["departments"] = sorted(r["departments"])
        r["components"] = sorted(r["components"])
        r["codes"] = sorted(r["codes"])
        r["be_lakh"] = round(r["be_lakh"], 2)

    out = {
        "built": utcnow(),
        "snapshot": mh.get("snapshot"),
        "state": "Maharashtra",
        "cycle": mh.get("cycle"),
        "variant": mh.get("variant"),
        "source": "data/maharashtra/schemes.json",
        "question": ("Which of Maharashtra's 1,956 Annual Scheme rows are welfare schemes a "
                     "citizen can apply to, and which are heads of expenditure, "
                     "institutions, share capital, works or accounting heads?"),
        "entries": len(rows),
        "distinct_names": len({x["name"].lower() for x in rows}),
        "counting_basis": (
            "EVERY COUNT HERE IS ON THE 1,956 SCHEME CODE BASIS unless the field name says "
            "distinct. The 10-digit scheme code is Maharashtra's own identifier for a "
            "provision and it is what the Planning Department numbers: the GENERAL, "
            "Scheduled Caste Component and Tribal Component cuts use DISJOINT scheme codes "
            "on this snapshot, so Pradhan Mantri Matru Vandana Yojana is four codes and four "
            "provisions rather than one counted four times, which is parse/maharashtra.py's "
            "own finding. The 1,956 codes carry 1,889 distinct names. absent_distinct is the "
            "de-duplicated view of the same list and its allocations add."),
        "publish_threshold": threshold,
        # The F1 optimum, the bar for the WEAKER claim: "this state's budget names
        # this as a scheme". It lived only in site/build.py, so the data could not
        # say which rows the site lists and anything else reading this file had to
        # guess. parse/cag_join.py guessed by skipping this state entirely.
        "listing_threshold": 2,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"].lower() for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "funded_at_nil": sum(1 for x in rows if not x.get("be_lakh")),
        "funded_at_nil_and_classified_scheme": sum(
            1 for x in schemes if not x.get("be_lakh")),
        "capital_or_loan_head_rows": sum(
            1 for x in rows if any(m[:1] in "4567" for m in x["major_heads"])),
        "ground_truth": {
            "file": "data/maharashtra/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "sets": labels["sets"],
            "why_not_myscheme": (
                "myScheme membership cannot be the ground truth here, and it was not a close "
                "call. parse/maharashtra.py produced 167 joins between these 1,956 codes and "
                "the Maharashtra myScheme records and read every one by eye: 131 are wrong. "
                "125 of them come from a single defect, the community abbreviation VJNT being "
                "read as a scheme acronym, which fanned six myScheme records out to every one "
                "of the 21 register rows whose name contains it. The defects are reproduced "
                "in myscheme_join_defects below. They are evidence about the matcher, not "
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
                "About one Maharashtra Annual Scheme row in four is a welfare scheme, "
                "against 16% of Tamil Nadu's Demand Book sub-heads, 41% of Andhra Pradesh's "
                "scheme-wise rows and 55% of Karnataka's. That is a fact about the document "
                "before it is a fact about the state: this is the SCHEME budget, so it is "
                "cleaner than Tamil Nadu's full detailed estimates and dirtier than "
                "Karnataka's Gender and Child annexures, which are already filtered to "
                "beneficiary-facing rows."),
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
                "thresholds is counted rather than estimated. The census starts at %d and not "
                "lower because of the scale: the corpus puts 300 rows at score 5 or above, "
                "386 at 4 and 425 at 3, and 300 rows, of which 240 needed a new label, is the "
                "largest set that can be read one by one and labelled reliably. Recall still "
                "comes from the stratified sample, because the rows the classifier rejects "
                "are too many to label exhaustively." % (CENSUS_FROM, CENSUS_FROM)),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": (
                "F1 peaks at threshold 2, where the sample says precision is 64.0% and one "
                "published name in three is not a scheme. Naming a scheme as hidden by a "
                "government is an accusation, so this runs at the high-precision end and "
                "accepts the recall loss. The break in the census is between 7 and 8, and it "
                "is visible in the bands rather than the cumulative column: the band at "
                "exactly 5 is 52.8% precise, the band at 6 is 82.3%, the band at 7 is 86.8% "
                "and the band at 8 is 96.2%. No row in the corpus scores exactly 10, so "
                "thresholds 10 and 11 name the same 12 rows."),
            "sample_versus_census": (
                "The stratified sample alone would have claimed 100% precision at threshold "
                "8, on the strength of 26 rows above the bar. The census counts 96.9%. It "
                "erred flatteringly here, as Karnataka's and Tamil Nadu's did and Andhra "
                "Pradesh's did not, which is the same lesson either way: a probability sample "
                "is the right tool for recall, which cannot be censused, and the wrong one "
                "for counting mistakes in a list short enough to read."),
            "what_the_missing_purpose_line_costs": (
                "Karnataka's books print a purpose line and it was that classifier's "
                "strongest signal at P(scheme) 0.947. Tamil Nadu prints none but prints the "
                "object head, worth 0.895. Maharashtra prints neither: its 8-character budget "
                "code is a major head and a serial, with no minor head and no object head "
                "anywhere in the book, so the name is nearly all there is. Recall at the "
                "published bar is 28.3% on the stratified sample and 35.6% on the held-out "
                "half, the lowest of the five states. The rows it loses are the state's own "
                "brands: Mukhyamantri Mazi Ladaki Bahin at Rs 21,000 crore scores 5, Lek "
                "Ladaki 5, Asmita Yojana 4 and Aam Aadmi Bima Yojana 4. A Marathi scheme name "
                "says almost nothing to a vocabulary of English benefit words."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_maharashtra_records": len(listed),
        "myscheme_record_count_note": (
            "This is counted live off data/myscheme/schemes/, every record whose "
            "beneficiaryState list mentions Maharashtra. parse/maharashtra.py's "
            "myscheme_join_summary below says 84 and that figure is hard coded there from an "
            "earlier count of the same directory. The two are reported side by side rather "
            "than reconciled, because a silently moving denominator is exactly the kind of "
            "thing a register should show rather than smooth over."),
        "myscheme_join_defects": mh.get("myscheme_join_defects"),
        "myscheme_join_summary": mh.get("myscheme_join_summary"),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_distinct_names": len({x["name"].lower() for x in absent}),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": (
            "Absence is decided by parse/match.py's generous matcher against the myScheme "
            "records tagged Maharashtra, because claiming absence should require that even a "
            "generous matcher finds nothing. Read that number against myscheme_join_summary: "
            "the matcher produced 167 joins over the whole corpus and 131 of them are wrong, "
            "so a row counted present may not be, and the absent count here is if anything an "
            "understatement. The surviving list is a floor for the opposite reason too: no "
            "purpose line and no object head is printed anywhere in the book, recall at the "
            "published bar is 28.3%, and the state's largest cash transfer does not clear "
            "it."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/maharashtra/classification.json", out)
    return out


def check_sample():
    """Report which sampled or census rows have no hand label yet."""
    mh = json.load(open(os.path.join(ROOT, "data", "maharashtra", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "maharashtra", "labels.json"),
                            encoding="utf-8"))
    have = {x["key"] for x in labels["labels"]}
    entries = sorted(mh["entries"], key=lambda x: x["code"])
    frame = stratify(entries)
    missing = [(r["code"], st, r["name"]) for r, st, _, _ in frame if r["code"] not in have]
    print("sampling frame %d rows, labelled %d, unlabelled %d"
          % (len(frame), len(have), len(missing)))
    for k, st, name in missing:
        print("  [%s]  %s  %s" % (st, k, name[:80]))
    uncovered = [r["code"] for r in entries
                 if score_entry(r["name"], major_heads(r["budget_codes"]))[0] >= CENSUS_FROM
                 and r["code"] not in have]
    print("census at score >= %d: %d rows unlabelled" % (CENSUS_FROM, len(uncovered)))
    for k in uncovered:
        print("  %s" % k)
    return missing, uncovered


def main():
    a = argparse.ArgumentParser(
        description="Classify Maharashtra Annual Scheme rows as welfare scheme or head of "
                    "expenditure.")
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
    print("maharashtra scheme codes classified: %d (%d distinct names)"
          % (o["entries"], o["distinct_names"]))
    print("  scheme         %5d  (%d distinct names)"
          % (o["classified_scheme"], o["classified_scheme_distinct_names"]))
    print("  not a scheme   %5d" % o["classified_not_scheme"])
    print("  of which on a capital outlay or loan major head: %d\n"
          % o["capital_or_loan_head_rows"])
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
          "was fitted to\n" % (h["precision"] * 100, h["recall"] * 100, v["n_held_out"]))
    print("absent from myScheme Maharashtra and classified a scheme: %d of %d absent codes, "
          "%d distinct names, Rs %s cr"
          % (o["absent_from_myscheme_and_classified_scheme"],
             o["absent_from_myscheme_all_rows"], o["absent_distinct_names"],
             format(o["absent_cr"], ",.0f")))
    for x in o["absent_distinct"][:12]:
        print("   Rs %10s cr  score %3d  %s"
              % (format((x["be_lakh"] or 0) / 100, ",.0f"), x["score"], x["name"][:58]))


if __name__ == "__main__":
    main()
