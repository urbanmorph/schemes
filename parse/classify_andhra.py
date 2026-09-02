"""
Classify Andhra Pradesh budget rows: welfare scheme, or institution and establishment head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

    data/andhra/labels.json          hand ground truth, the input
    data/andhra/classification.json  the verdicts, the output

parse/andhra.py pulls 552 rows out of six scheme-wise books, and its own caveat already
says the plain truth: some of those rows are establishment heads the books list alongside
schemes. "Headquarters Office" appears 18 times, "District Offices" 14, "Buildings" 6, and
"District and Other Roads", "Extension" and "Hospitals and Dispensaries" once each. Set
against myScheme's 52 Andhra Pradesh records, almost the whole 552 is absent from the
national citizen portal, and publishing that number as "schemes Andhra Pradesh hides" would
be false. Naming a district office as a scheme a government hid is an accusation against a
government that did nothing of the kind.

WHAT IS DIFFERENT HERE, AND IT IS THE WHOLE PROBLEM. Karnataka's books print a purpose
line, one sentence saying what the money buys, and that line was the strongest signal in
parse/classify_karnataka.py: P(scheme) 0.947 where the line named a benefit. Andhra
Pradesh prints no purpose line anywhere in the six books. What it prints instead, on 402 of
the 552 rows, is the head of account, and the head of account carries three usable fields:
the major head says which function of government the money belongs to, the minor head says
whether it is direction and administration or construction, and the object head says
whether the money is a salary, an office expense, a major work, a grant-in-aid, a subsidy
or a scholarship. That is a weaker instrument than a sentence of English, and the recall
number below says so. The other 150 rows, from the Gender and Child books, carry no head of
account at all and are read on their name alone.

THE KEY IS (department, name), NOT A HEAD OF ACCOUNT. The same scheme run by five
departments is five rows, because "Subsidy on Domestic LPG Scheme" under Backward Classes
Welfare and under Tribal Welfare are separate provisions. 552 rows collapse to 484 distinct
names. Every count in this file is on the 552-row basis unless it says otherwise, and the
output carries both.

There are two label sets and they answer different questions.
  stratified, 203 rows   A probability sample across the books and the allocation range.
                         This is what the threshold sweep runs on, because precision and
                         recall estimated on anything else would not generalise to rows the
                         classifier has not seen.
  audit, 99 rows         Every remaining row the classifier scores 3 or above. With the 48
                         stratified rows already there, the two sets are a CENSUS of the
                         published region, so the published list's error count is counted,
                         not estimated. The audit was made after the weights were fixed and
                         was deliberately not fed back into them, which is why its findings
                         are in the output as errors rather than as patches.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan, free travel, free power, a house, treatment for a named
                beneficiary class, or training in which the trainee is himself the
                beneficiary class.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, pays for the
                capacity of the delivery system rather than the benefit, or is an
                accounting or adjustment head.
The line between the last two clauses is the one that did most of the work here. Adult
literacy and skilling are schemes because the learner is the beneficiary; the agricultural
extension sub-mission and the livestock mission's seminars and trainings are not, because
they buy the delivery system's capacity. 75 of the 302 labels sat close enough to that line
to be flagged borderline, and each carries the sentence that decided it. A reader who
disagrees can flip the label and rerun.

WHAT ACTUALLY DISCRIMINATES. Measured on the 102 rows of the development half against a
base rate of 41.2%:

  the state's own accounting classification, which is not a guess:
    capital outlay or loan major head (4xxx to 7xxx)      P(scheme) 0.150 over 20 rows
    a running cost or major works object head             P(scheme) 0.147 over 34 rows
    establishment or works minor head (001 to 053)        P(scheme) 0.200 over  5 rows
    every object head on the row is a transfer head       P(scheme) 0.667 over 27 rows
    welfare function major head (2225, 2235, ...)         P(scheme) 0.526 over 19 rows

  what the name says:
    accounting or administration word in the name         P(scheme) 0.000 over  5 rows
    the name is assistance or support paid TO a body      P(scheme) 0.000 over  5 rows
    asset or works word in the name                       P(scheme) 0.091 over 22 rows
    institution word in the name                          P(scheme) 0.133 over 30 rows
    benefit word in the name                              P(scheme) 0.783 over 23 rows
    named beneficiary class in the name                   P(scheme) 0.692 over 13 rows
    scheme-name marker in the name                        P(scheme) 0.667 over 27 rows

Two of those are worth pausing on. The object head is the closest thing this corpus has to
Karnataka's purpose line: it is the state saying, in its own chart of accounts, whether the
money is a salary or a scholarship, and it separates 0.147 from 0.667. And the word
"through" is a real signal in Andhra Pradesh specifically, because the state routes benefits
through its welfare corporations: "Economic Support Schemes through BC-A Corporation" is a
subsidy to individuals and "Assistance to A.P. Women Co-operative Finance Corporation" is
money for a body. Both carry the token "Corporation". The preposition is what tells them
apart, so the institution penalty is suppressed when the name says "through" and a point is
added instead.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py and
parse/classify_karnataka.py. F1 peaks at threshold 0, where precision is 81.5% and nearly
one published name in five is wrong. Publishing runs at 4. The audit census settles that
number, because it counts errors rather than estimating them:

    threshold 3   147 rows published, 18 are not schemes   precision 87.8%
    threshold 4    92 rows published,  4 are not schemes   precision 95.7%
    threshold 5    70 rows published,  3 are not schemes   precision 95.7%
    threshold 6    50 rows published,  2 are not schemes   precision 96.0%
    threshold 7    16 rows published,  0 are not schemes   precision 100.0%

The break is between 3 and 4, not further up: of the 55 rows that sit at exactly 3, 14 are
not schemes, a marginal precision of 74.5%, while the 22 rows between 4 and 5 contain one
error. Precision is flat from 4 to 6, so buying 0.3 points of it by dropping 42 rows would
not be a trade, it would be a loss. Threshold 4 it is, and the four errors that survive are
named in known_errors rather than patched out.

The stratified sample alone would have said 93.9% at threshold 4, on the strength of 33
rows. The census says 95.7%. Note the direction: here the probability sample was
pessimistic, where Karnataka's was flattering, which is the same lesson either way. A
sample of 203 rows leaves too few above the bar to state the published list's precision to
better than a few points, and which way it errs is luck. Precision is counted. Recall is
estimated, because the rows the classifier rejects are too many to label exhaustively.

WHAT THE MISSING PURPOSE LINE COSTS. Recall at threshold 4 is 36.5% on the stratified
sample, against Karnataka's 31.6% at its own published bar, so the two states are not
far apart on that number; but Karnataka reached it with a sentence of English on 40% of its
rows and Andhra Pradesh reaches it on the chart of accounts alone. The rows this loses are
named in known_errors and they are the state's own brands: Thallikivandanam, Annadata
Sukhibhava, Gruha Vasathi, Aadarana, NTR Jalasiri. A Telugu scheme name says nothing to a
vocabulary of English benefit words, and no head of account rescues it when the Gender
Budget prints none. The published count is a floor on Andhra Pradesh's schemes and never a
total, and it is a lower floor than Karnataka's for a reason that is the state's to fix:
print the purpose line.
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

PUBLISH_THRESHOLD = 4

# Every row at or above this score carries a hand label, from the stratified set or the
# audit set. Precision at or above it is counted; below it, it is estimated from the
# stratified sample only.
CENSUS_FROM = 3


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written by reading the 484 distinct names in the
# corpus, before any of the numbers above were computed, so the weights are
# fitted and the word choices are not.
# ---------------------------------------------------------------------------

# Minor heads are standardised across Indian government accounts, so these mean the same
# thing in every department: 001 Direction and Administration, 003 Training, 004 Research,
# 005 Investigation, 051 Construction, 052 Machinery and Equipment, 053 Maintenance and
# Repairs. Note that Andhra Pradesh's SC and ST volumes book most rows under minor heads
# 789 and 796, the sub-plan heads, which say who the money is for and not what it buys, so
# the minor head fires on far fewer rows here than it does in Karnataka.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053"}

# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC, ST, OBC and Minorities, 2235 Social Security and Welfare,
# 2236 Nutrition, 2501 Rural Development Programmes, 2505 Rural Employment. 2408 Food is
# left out deliberately: in this corpus it carries fertiliser buffer storage costs.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2501", "2505"}

# Object heads, the sixth field of a head of account, are the state saying what kind of
# spending this is. The three groups below are the standard chart of accounts groups.
#   transfers, money that leaves government and reaches someone:
#     310 Grants-in-aid, 330 Subsidies, 340 Scholarships and Stipends, 350 Grants for
#     creation of capital assets. 900 is Andhra Pradesh's own lump sum scheme block, used
#     for the pension heads and the welfare corporation heads. 320 Contributions is a
#     transfer too and is deliberately absent: it fires on two rows in the whole corpus,
#     it was not in the set measured on the development half, and adding it afterwards
#     would mean the published numbers describe a configuration nobody measured.
TRANSFER_OBJ = {"310", "330", "340", "350", "900"}
#   running the office and building the asset:
#     010 Salaries, 020 Wages, 030 Overtime, 040 Pensionary charges, 060 Medical
#     reimbursement, 110 and 120 Travel, 130 Office Expenses, 140 Rents Rates and Taxes,
#     160 Publications, 200 Other Administrative Expenses, 260 Advertising, 280
#     Professional Services, 290 and 300 Other Contractual Services, 500 Other Charges,
#     510 Motor Vehicles, 520 Machinery and Equipment, 530 Major Works.
RUNNING_OBJ = {"010", "020", "030", "040", "060", "070", "100", "110", "120", "130",
               "140", "160", "170", "200", "260", "280", "290", "300", "500", "510",
               "520", "530"}
# The supplies group, 210 Supplies and Materials through 270 Minor Works, is measured and
# then left out on purpose; see REJECTED_SIGNALS for the number and the argument.

# Words that name an organisation rather than a benefit. "Andhra Pradesh Study Circle",
# "Assistance to Urdu Academy", "Government Junior Colleges", "State Commission for Women".
INSTITUTION = {
    "university", "universities", "college", "colleges", "school", "schools", "institute",
    "institutes", "institution", "institutions", "institutional", "corporation",
    "corporations", "board", "authority", "directorate", "commission", "committee",
    "council", "academy", "academies", "centre", "centres", "center", "centers", "agency",
    "agencies", "department", "office", "offices", "headquarters", "hospital", "hospitals",
    "dispensaries", "society", "societies", "federation", "trust", "laboratory",
    "laboratories", "labs", "kendralu", "itda", "itdas", "canteens", "polytechnics",
    "cell", "circle", "circles", "units", "municipalities", "municipal", "niwas", "sadan",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "contsruction", "constuction", "building", "buildings",
    "infrastructure", "infrastructural", "infrastcture", "road", "roads", "works",
    "maintenance", "maintanence", "repair", "repairs", "renovation", "upgradation",
    "upgrading", "modernisation", "modernization", "equipment", "equipments", "machinery",
    "erection", "statues", "plantation", "harbors", "jetties", "stadia", "restoration",
    "capital", "assets", "sites", "electrification", "facilities", "facility", "hostels",
    "hostel", "homes", "home", "lands", "land",
}

# Words that name an accounting, payroll or administration head. "Deduct - Recoveries",
# "Administrative Support for implementation of TSP", "Livestock Census".
ACCOUNTING = {
    "deduct", "recoveries", "administrative", "admin", "salary", "salaries", "honorarium",
    "management", "monitoring", "evaluation", "audit", "census", "charges", "decretal",
    "establishments", "computerisation", "survey", "investigation",
}

# Words that name the thing a person receives.
BENEFIT = {
    "scholarship", "scholarships", "stipend", "pension", "pensions", "incentive",
    "incentives", "assistance", "subsidy", "subsidies", "free", "insurance",
    "compensation", "loan", "loans", "kit", "kits", "nutrition", "nutritious",
    "reimbursement", "allowance", "relief", "meal", "meals", "bhojanam", "gratia",
    "bhima", "thrift", "vandanam", "bharosa", "nidhi", "pellikanuka", "aids",
    "sponsorship", "waiver",
}

# Words that name who receives it. A head that names its beneficiary class is describing a
# transfer; a head that names none is usually describing an office or an asset.
BENEFICIARY = {
    "students", "student", "women", "woman", "womens", "girls", "girl", "farmers",
    "farmer", "weavers", "weaver", "fishermen", "beneficiaries", "victim", "victims",
    "workers", "worker", "families", "family", "children", "child", "persons", "person",
    "youth", "widow", "widows", "disabled", "abled", "citizens", "households", "household",
    "artisans", "entrepreneurs", "graduates", "mothers", "adolescent", "barbers",
    "drivers", "imams", "mouzans", "pastors", "piligrims", "pilgrims", "apprenticeship",
    "labour", "tribals", "boys", "saloons", "vidyardhi", "senior", "aged", "poor", "kisan",
}

# Scheme-name morphology. Weak on its own and weighted accordingly: "Green India Mission"
# is an afforestation head and "Mission Vatsalya - Child Helpline" is a helpline, so the
# word Mission in a name proves nothing.
MARKER = {
    "yojana", "yojna", "yojane", "abhiyan", "abhiyana", "mission", "scheme", "schemes",
    "karyakram", "pariyojana", "samman", "nidhi", "bharosa",
}

# The Andhra Pradesh preposition test. The state pays most of its individual subsidies and
# loans out THROUGH a welfare corporation, so the corporation's name sits inside the
# scheme's name. "Economic Support Schemes through BC-A Corporation" is a transfer to
# individuals; "Assistance to A.P. Women Co-operative Finance Corporation" is money for the
# body itself. Both carry the token Corporation and only the preposition separates them.
THROUGH = re.compile(r"\bthrough\b", re.I)
RECIPIENT_BODY = re.compile(r"^\s*(assistance|support|loans?|grants?)\s+(to|for)\b", re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def hoa_fields(hoas):
    """Major, minor and object head sets across all heads of account on one row.

    A row is a (department, name) pair and the annexure books list it under several heads,
    a general head plus the -789 SC head plus the -796 ST head, revenue plus capital. All
    of them are evidence about the same provision, so all of them are read. Sets, never
    lists, and every use below sorts before printing, because parse/registry.py once
    returned a different entry count on every run by iterating a set.
    """
    major, minor, obj = set(), set(), set()
    for h in hoas or []:
        p = (h or "").split("-")
        if len(p) > 0 and p[0]:
            major.add(p[0])
        if len(p) > 2:
            minor.add(p[2])
        if len(p) > 5:
            obj.add(p[5])
    return major, minor, obj


def score_entry(name, hoas):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic.

    Negative weights are larger than positive ones on purpose. A row that looks like an
    institution and also carries benefit words, "Assistance to Andhra Pradesh Study
    Circle", should have to work to clear the bar, because that is the row that would
    embarrass the published list.
    """
    tk = tokens(name)
    major, minor, obj = hoa_fields(hoas)
    ev = []
    total = 0

    def add(points, why):
        nonlocal total
        total += points
        ev.append(["%+d" % points, why])

    # Structure first: what the state's own accounting classification says this is.
    cap = sorted(m for m in major if m[:1] in "4567")
    if cap:
        add(-3, "capital outlay or loan major head " + ", ".join(cap))

    est = sorted(minor & ESTAB_MINOR)
    if est:
        add(-3, "establishment or works minor head " + ", ".join(est))

    run = sorted(obj & RUNNING_OBJ)
    if run:
        add(-3, "running cost or major works object head " + ", ".join(run[:4]))
    elif obj and obj <= TRANSFER_OBJ:
        add(2, "every object head on this row is a transfer head " +
            ", ".join(sorted(obj)))

    inst = sorted(tk & INSTITUTION)
    if inst and not THROUGH.search(name or ""):
        add(-4, "institution words in the name: " + ", ".join(inst[:4]))

    if RECIPIENT_BODY.match(name or ""):
        add(-3, "the name is assistance or support paid TO a named body")

    works = sorted(tk & WORKS)
    if works:
        add(-3, "asset or works words in the name: " + ", ".join(works[:4]))

    acct = sorted(tk & ACCOUNTING)
    if acct:
        add(-3, "accounting, payroll or administration words in the name: " +
            ", ".join(acct[:4]))

    wel = sorted(major & WELFARE_MAJOR)
    if wel:
        add(1, "welfare function major head " + ", ".join(wel))

    ben = sorted(tk & BENEFIT)
    if ben:
        add(3, "benefit words in the name: " + ", ".join(ben[:4]))

    who = sorted(tk & BENEFICIARY)
    if who:
        add(2, "named beneficiary class in the name: " + ", ".join(who[:4]))

    if THROUGH.search(name or ""):
        add(2, "the name says the benefit is delivered THROUGH a body, not paid to it")

    mark = sorted(tk & MARKER)
    if mark:
        add(1, "scheme-name marker in the name: " + ", ".join(mark[:3]))

    return total, ev


SIGNALS = [
    {"points": -4, "signal": "institution word in the name, unless the name says through",
     "measured": "P(scheme) 0.133 over 30 development rows, base rate 0.412"},
    {"points": -3, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": "P(scheme) 0.150 over 20 development rows"},
    {"points": -3, "signal": ("a running cost or major works object head, 010 to 300, "
                              "510, 520, 530"),
     "measured": "P(scheme) 0.147 over 34 development rows"},
    {"points": -3, "signal": "establishment or works minor head, 001 003 004 005 051 052 053",
     "measured": ("P(scheme) 0.200 over 5 development rows. Thin, because the SC and ST "
                  "volumes book most rows under the sub-plan minor heads 789 and 796 "
                  "instead, so the functional minor head is invisible on those rows.")},
    {"points": -3, "signal": "asset or works word in the name",
     "measured": "P(scheme) 0.091 over 22 development rows"},
    {"points": -3, "signal": "accounting, payroll or administration word in the name",
     "measured": "P(scheme) 0.000 over 5 development rows"},
    {"points": -3, "signal": "the name is assistance or support paid TO a named body",
     "measured": "P(scheme) 0.000 over 5 development rows"},
    {"points": 3, "signal": "benefit word in the name",
     "measured": "P(scheme) 0.783 over 23 development rows, the strongest positive"},
    {"points": 2, "signal": "every object head on the row is a transfer head",
     "measured": "P(scheme) 0.667 over 27 development rows"},
    {"points": 2, "signal": "named beneficiary class in the name",
     "measured": "P(scheme) 0.692 over 13 development rows"},
    {"points": 2, "signal": "the name says the benefit is delivered THROUGH a body",
     "measured": ("P(scheme) 1.000 over 2 development rows, and all 9 rows in the "
                  "corpus that carry the word are labelled schemes. Two development rows is too few "
                  "to fit a weight on, so the weight is set from the argument rather than "
                  "the count: the preposition is the only thing separating a subsidy paid "
                  "out through a corporation from a grant paid to one.")},
    {"points": 1, "signal": "welfare function major head, 2216 2225 2235 2236 2501 2505",
     "measured": ("P(scheme) 0.526 over 19 development rows, lift +0.141. Weak here where "
                  "it was worth +0.34 in Karnataka, because 2225 in Andhra Pradesh carries "
                  "the residential schools and the hostels as well as the pensions.")},
    {"points": 1, "signal": "scheme-name marker in the name",
     "measured": "P(scheme) 0.667 over 27 development rows, the weakest positive"},
]

REJECTED_SIGNALS = [
    {"signal": "the name matches a myScheme record tagged Andhra Pradesh",
     "measured": ("5 of the 552 rows join at all, and reading the five, only one join is "
                  "real. It cannot be measured as a signal because it barely fires."),
     "why": ("This is the borrowed ground truth the hand labels replace, and here it is "
             "not merely weak, it is circular. The question the register asks is which "
             "budget rows are ABSENT from myScheme, so scoring a row higher for being "
             "present on myScheme would systematically push down exactly the rows the "
             "answer is made of.")},
    {"signal": "the name matches a myScheme record from any state",
     "measured": "P(scheme) 0.542 with, 0.296 without, lift +0.245 over 102 development rows",
     "why": ("Real lift, and still rejected, for the circularity above and because the "
             "matcher is generous by design: it fires on 48 of 102 development rows, most "
             "of them on shared words rather than shared schemes.")},
    {"signal": "a supplies object head, 210 to 270",
     "measured": "P(scheme) 0.154 over 13 development rows, lift -0.296",
     "why": ("A genuine negative, left out anyway. 210 Supplies and Materials, 230 and 250 "
             "Clothing, Tentage and Stores are the heads under which an in-kind benefit is "
             "actually bought: the mid day meal menu and the baby kit are booked there. "
             "Charging a row for the accounting of the transfer it makes would penalise "
             "the clearest transfers in the corpus. Including it changed published "
             "precision by nothing and cost recall, and the measurement is here so a "
             "reader can disagree.")},
    {"signal": "the row carries no head of account at all",
     "measured": "P(scheme) 0.531 with, 0.357 without, lift +0.174 over 102 development rows",
     "why": ("Real but not a fact about the row, only about which book printed it: the "
             "Gender and Child budgets print no head of account and they list more "
             "brand-name schemes than the annexures do. Scoring it would be scoring the "
             "book, and the same row appears in both.")},
    {"signal": "the word Programme or Development in the name",
     "measured": ("P(scheme) 0.333 with, 0.417 without for Programme, and the identical "
                  "pair for Development, over 102 development rows"),
     "why": "Too weak to carry a point in either direction."},
    {"signal": "the name ends in a place, or hangs a place off the word at",
     "measured": "fires on 0 of the 102 development rows",
     "why": ("Karnataka's rule, carried over and dead here: Andhra Pradesh's books do not "
             "append the district to an institution's name the way Karnataka's do. Kept "
             "out rather than kept in as a rule that never fires.")},
]

KNOWN_ERRORS = [
    {"name": "MISSION VATSALYA (Child Protection Services and Child Welfare Services) "
             "[AP353]", "score": 6,
     "kind": "false positive, published at threshold 4",
     "why": ("The highest scoring of the four errors that survive the publishing bar. It "
             "scores 6 from a welfare major head, a transfer object head, the word Child "
             "and the word Mission. It is labelled not_scheme because this head runs the "
             "child care institutions and the protection service, while the transfer it "
             "makes has its own separate row, Mission Vatsalya - Non-Institutional care "
             "Sponsorship, which is labelled a scheme. This is the classifier's 'Space "
             "Technology': a row in the published list a careful reader would object to, "
             "named here rather than quietly patched out. Flip this label and precision at "
             "threshold 4 reads 96.7% rather than 95.7%.")},
    {"name": "Mission Shakti - SAMARTHYA - NATIONAL HUB FOR WOMEN EMPOWERMENT [AP359]",
     "score": 6,
     "kind": "false positive, published at threshold 4",
     "why": ("The clearest of the four. A national hub is a technical support unit and no "
             "benefit passes from this head to any woman. It scores 6 because it names a "
             "beneficiary class, sits on a welfare major head with a grant-in-aid object "
             "head, and carries the word Mission. Adding hub to the institution vocabulary "
             "would fix it and would be principled, but the fix was found by reading the "
             "audit, and changing weights to suit the audit would destroy the one "
             "measurement in this file that counts errors instead of estimating them.")},
    {"name": "Pradhan Mantri Poshan Shakti Nirman (PM POSHAN) - Transportation Assistance "
             "[AP75]", "score": 5,
     "kind": "false positive, published at threshold 4",
     "why": ("The word Assistance is worth 3 and the money is a carrier's freight bill for "
             "moving foodgrains to schools. The label could reasonably be flipped, since "
             "the freight is part of a meal a child does receive; if it were, precision at "
             "threshold 4 would read 96.7%.")},
    {"name": "Pradhan Mantri Jan Vikas Karyakram (PMJVK) [AP238]", "score": 4,
     "kind": "false positive, published at threshold 4",
     "why": ("PMJVK builds schools, health centres and hostels in minority concentration "
             "areas. It scores exactly at the bar, on a welfare major head, a transfer "
             "object head and the scheme marker Karyakram, and nothing in its name says "
             "building.")},
    {"name": "PM RKVY - Digital Agriculture Mission [AP314], and 13 other rows at score 3",
     "score": 3,
     "kind": "false positive, excluded at threshold 4",
     "why": ("The reason the bar is 4 and not 3. The band at exactly 3 is 55 rows of which "
             "14 are not schemes, a marginal precision of 74.5%: the digital agriculture "
             "mission, the agricultural extension sub-mission, the livestock mission's "
             "seminars and trainings, the drug demand reduction plan, the smart cities "
             "mission, an afforestation programme, two helplines and the atrocities act's "
             "special courts. Every one of them is a central scheme name attached to "
             "spending that builds the delivery system rather than a benefit.")},
    {"name": "Thallikivandanam, Annadata Sukhibhava, Gruha Vasathi, Aadarana, NTR Jalasiri, "
             "Badikostha, Mahaprasthanam, Yuva Kiranalu", "score": "-3 to 3",
     "kind": "false negative, the recall cost, and it is the state's own brands",
     "why": ("Large, structural, and the direct consequence of there being no purpose "
             "line. These are Telugu scheme names carrying no English benefit word and no "
             "beneficiary noun. Six of their twelve rows print no head of account either, "
             "so on those the classifier has literally nothing to read: all five "
             "Thallikivandanam rows and Gruha Vasathi score 0 on an empty hand. "
             "Thallikivandanam is Rs 4,098 crore of support to mothers for keeping "
             "children in school, in the Backward Classes row alone. Aadarana, which buys "
             "tool kits for Backward Class artisans, scores 3 and misses the bar by one. "
             "Recall at the published bar is 36.5% on the stratified sample, so a "
             "published count from this classifier is a floor on Andhra Pradesh's schemes "
             "and never a total.")},
    {"name": "Krishionnati Yojana and PM RKVY rows booked under capital major head 4401",
     "score": "-5",
     "kind": "false negative, excluded at threshold 4",
     "why": ("The National Food Security Mission, the pulses mission and the agriculture "
             "mechanisation sub-mission each appear twice, once on the revenue side where "
             "they score 3 to 6 and once on the capital side under 4401 with a major works "
             "object head, where the same scheme scores -5. The capital slice really is "
             "buying works, so the classifier is not wrong about the row; it is the "
             "(department, name) key putting one provision's two halves in one row and "
             "letting the negative half decide. Both halves are printed in all_entries.")},
    {"name": "Mid-Day Meal programme in Government Junior colleges", "score": -1,
     "kind": "false negative, the cost of the institution rule",
     "why": ("A meal served to students, penalised 4 for the word colleges. The same shape "
             "catches Best Available Schools, which pays the fees of Scheduled Caste "
             "children in private schools and scores -1 for the word Schools. Any Andhra "
             "Pradesh scheme whose name says where the benefit is delivered pays the "
             "institution penalty for saying so.")},
]

# Absence is a matching question, and reading all five joins this corpus produced found
# four of them wrong. They are kept here as the record of a fix, not of a live defect:
# every one was a hole in parse/match.py's acronym rules, and all four are now closed by
# NOT_ACRONYMS there, with self-tests taken from these exact pairs. The count moved from
# 90 to 92 as a result, which is the figure this file used to have to state by hand.
#
# They stay in the output because a reader should be able to see what the join used to get
# wrong and check that it no longer does, and because the next state's corpus will find the
# next hole the same way: by someone reading every join rather than trusting the count.
KNOWN_FALSE_MATCHES = [
    {"andhra": "PMAY-URBAN-BLC Scheme [AP345]",
     "myscheme": ("INDIRAMMA Disabled Pension (Urban), and the Old Age, Weavers and Widow "
                  "pensions with the same suffix"),
     "why": ("The matcher's acronym rule fires on the shared bare word urban. Four "
             "separate false joins from one token. PMAY-URBAN-BLC is beneficiary led house "
             "construction and the INDIRAMMA rows are pensions.")},
    {"andhra": "Mission Shakti - SAMARTHYA - NATIONAL HUB FOR WOMEN EMPOWERMENT [AP359]",
     "myscheme": "National Mission on Edible Oils- Oil Palm",
     "why": "The same rule, on the shared bare word national."},
    {"andhra": "Livestock Census and Integrated Sample Survey - INTEGRATED SAMPLE SURVEY "
               "OTHER COMPONENTS [AP407], and the salary component row",
     "myscheme": ("Providing Artificial Limbs and Other Appliances to Disabled BOC "
                  "Workers, and Sanctioning Spectacles to Senior Citizens"),
     "why": ("Acronym containment: the initials of the long Andhra Pradesh name happen to "
             "contain the initials of the myScheme name. Two more false joins.")},
    {"andhra": "PM RKVY - National Mission on Edible Oils - Oil Palm [AP405]",
     "myscheme": "National Mission on Edible Oils- Oil Palm",
     "why": ("The one join that is real, at similarity 0.78. It is here so the reader can "
             "see that the count of true joins across 552 rows and 52 records is one.")},
]


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

def entry_key(r):
    """The key of an Andhra Pradesh row. Not a head of account: see the docstring."""
    return r["department"] + " | " + r["name"]


def book(r):
    """One book per row for stratification, in priority order.

    Six books overlap on the same row, so a single label is needed. SC and ST first
    because those two volumes are the deepest, then Backward Classes and Minorities, then
    Child, then Gender. The first two groups are the annexure layout that prints heads of
    account; the last two are the layout that does not, which is the split that matters.
    """
    b = set(r.get("books") or [])
    if "Scheduled Castes Component" in b or "Scheduled Tribes Component" in b:
        return "SCST"
    if "Backward Classes Component" in b or "Minorities Component" in b:
        return "BCMIN"
    if "Child Budget" in b:
        return "CB"
    return "GB"


def stratify(entries, target=200):
    """Deterministic stratified sample: book crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by key and picked at even
    spacing, so this returns the same rows on every machine and every run.
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

    cells = {}
    for r in entries:
        cells.setdefault((book(r), band(r)), []).append(r)

    out = []
    for k in sorted(cells):
        rows = sorted(cells[k], key=entry_key)
        # Proportional allocation with a floor of 4, so the sample is close to self
        # weighting and every stratum still gets enough rows to say anything about.
        n = min(len(rows), max(4, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda x: entry_key(x[0]))


def myscheme_andhra():
    """Scheme names myScheme lists for Andhra Pradesh. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("andhra" in (s or "").lower() for s in states):
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
    ap = json.load(open(os.path.join(ROOT, "data", "andhra", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(ap["entries"], key=entry_key)

    lp = os.path.join(ROOT, "data", "andhra", "labels.json")
    labels = json.load(open(lp, encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_andhra()

    rows = []
    for r in entries:
        total, ev = score_entry(r["name"], r.get("hoas"))
        k = entry_key(r)
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in listed if probably_same(r["name"], n)[0]]
        rows.append({
            "key": k,
            "department": r["department"],
            "name": r["name"],
            "be_lakh": r.get("be_lakh"),
            "books": sorted(r.get("books") or []),
            "hoas": sorted(r.get("hoas") or []),
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_andhra": bool(hit),
            "myscheme_match": sorted(hit) or None,
            "hand_label": by_key[k]["label"] if k in by_key else None,
        })

    # Validation on the probability sample. The audit set is a census of the published
    # region, so mixing it in would inflate precision at exactly the thresholds that
    # matter; it gets its own count below.
    scored = [{"key": x["key"], "name": x["name"], "score": x["score"],
               "label": by_key[x["key"]]["label"]}
              for x in rows
              if x["key"] in by_key and by_key[x["key"]].get("sample") != "audit"]
    scored.sort(key=lambda x: x["key"])
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

    # The audited census. Every row scoring CENSUS_FROM or more carries a hand label, from
    # one set or the other, so at those thresholds these are counts and not estimates.
    audited = sorted((x for x in rows if x["key"] in by_key), key=lambda x: x["key"])
    census = []
    top = max(x["score"] for x in rows)
    for t in range(CENSUS_FROM, top + 1):
        pub = [x for x in audited if x["score"] >= t]
        corpus = [x for x in rows if x["score"] >= t]
        bad = [x for x in pub if by_key[x["key"]]["label"] != "scheme"]
        census.append({
            "threshold": t,
            "rows_in_corpus": len(corpus),
            "rows_hand_labelled": len(pub),
            "published": len(pub),
            "not_schemes": len(bad),
            "precision": round((len(pub) - len(bad)) / len(pub), 3) if pub else 0.0,
            "the_errors": sorted(x["name"] for x in bad),
        })
    at_census = next(x for x in census if x["threshold"] == threshold)

    schemes = [x for x in rows if x["verdict"] == "scheme"]
    absent_all = [x for x in rows if not x["in_myscheme_andhra"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_andhra"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per SCHEME, not per departmental share of one. Andhra Pradesh funds a scheme
    # separately out of each social-category department, so NTR Bharosa Pension appears six
    # times, once for Backward Classes, once for Scheduled Castes and so on. Publishing the
    # rows would print that scheme six times down a page and read as six findings.
    #
    # The departments are distinct within every name here, checked rather than assumed, so
    # the shares add: NTR Bharosa is Rs 27,719 cr across six departments and not the
    # Rs 11,913 cr of its largest one. This is the opposite of the rule for BOOKS, where the
    # six publications report overlapping slices of the same provision and the largest is
    # taken, and the two rules are different because the underlying facts are.
    #
    # The score is the best any share achieved, because the evidence for a scheme being a
    # scheme does not weaken by being funded twice.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"])
        if e is None:
            e = by_name[x["name"]] = {"name": x["name"], "departments": [],
                                      "be_lakh": 0.0, "score": x["score"],
                                      "evidence": x["evidence"], "books": set()}
        if x.get("department") and x["department"] not in e["departments"]:
            e["departments"].append(x["department"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
        e["books"] |= set(x.get("books") or ())
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["departments"] = sorted(r["departments"])
        r["books"] = sorted(r["books"])
        r["be_lakh"] = round(r["be_lakh"], 2)

    out = {
        "built": utcnow(),
        "snapshot": ap.get("snapshot"),
        "state": "Andhra Pradesh",
        "cycle": ap.get("cycle"),
        "source": "data/andhra/schemes.json",
        "question": ("Which of Andhra Pradesh's 552 scheme-wise budget rows are welfare "
                     "schemes, and which are institutions, establishment heads, asset "
                     "heads or accounting heads?"),
        "entries": len(rows),
        "distinct_names": len({x["name"] for x in rows}),
        "counting_basis": ("Every count here is on the 552-row basis, one row per "
                           "(department, scheme name), unless the field says distinct. "
                           "552 rows carry 484 distinct names, because a scheme run by "
                           "five departments is five provisions and collapsing them would "
                           "erase four."),
        "publish_threshold": threshold,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"] for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "rows_without_head_of_account": sum(1 for x in rows if not x["hoas"]),
        "ground_truth": {
            "file": "data/andhra/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "why_not_myscheme": ("myScheme membership cannot be the ground truth here, and "
                                 "not because it is weak. Only 5 of the 552 rows join an "
                                 "Andhra Pradesh myScheme record at all, and reading those "
                                 "five, one join is real. Worse, the signal is circular: "
                                 "the question is which rows are absent from myScheme, so "
                                 "scoring presence would push down exactly the rows the "
                                 "answer is made of."),
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
            # rather than an estimate: every row scoring 3 or more carries a hand label,
            # so the errors in the published list are enumerated, not inferred. The
            # stratified sample alone would have claimed 93.9% precision at threshold 4 on
            # the strength of 33 rows; the census says 95.7%. It erred pessimistically
            # here and flatteringly in Karnataka, which is the same lesson either way: a
            # probability sample is the right tool for recall, which cannot be censused,
            # and the wrong one for counting mistakes in a list short enough to read.
            "census_note": ("Every row at or above score 3 is hand labelled, so precision "
                            "at these thresholds is counted rather than estimated. Recall "
                            "still comes from the stratified sample, because the rows the "
                            "classifier rejects are too many to label exhaustively."),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": ("F1 peaks at threshold 0, where nearly one published name in "
                           "five is not a scheme. Naming a scheme as hidden by a "
                           "government is an accusation, so this runs at the "
                           "high-precision end and accepts the recall loss. The break in "
                           "the census is between 3 and 4: the band at exactly 3 is 74.5% "
                           "precise on its own, and everything from 4 up is about 96%."),
            "what_the_missing_purpose_line_costs": (
                "Karnataka's books print a purpose line and it was that classifier's "
                "strongest signal at P(scheme) 0.947. Andhra Pradesh prints none, on any "
                "of the 552 rows, and 150 of them carry no head of account either. On "
                "those 150 the classifier reads a name and nothing else, which is why the "
                "state's own Telugu-named brands, Thallikivandanam at Rs 4,098 crore "
                "among them, score 0 and are excluded. Recall at the published bar is "
                "36.5%."),
        },
        "known_errors": KNOWN_ERRORS,
        "known_false_matches": KNOWN_FALSE_MATCHES,
        "myscheme_andhra_records": len(listed),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        # Now equal to the line above, because the four false joins these two numbers used
        # to disagree over have been fixed in parse/match.py. Kept as a separate field so
        # that a future divergence between them is visible rather than silently absorbed:
        # if these two ever differ again, the matcher has grown a new hole.
        "absent_and_classified_scheme_after_reading_the_joins": len(schemes),
        "absent_distinct_names": len({x["name"] for x in absent}),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": ("Absence is decided by parse/match.py's generous matcher against "
                        "the myScheme records tagged Andhra Pradesh, because claiming "
                        "absence should require that even a generous matcher finds "
                        "nothing. Here the matcher is too generous rather than too strict: "
                        "5 of 552 rows join and four of the five joins are wrong, listed "
                        "in known_false_matches. Two of those false joins sit inside the "
                        "published list, so the count above says 90 where reading the "
                        "joins says 92, and the one real join, an oil palm mission row, "
                        "scores 3 and is not published anyway. The surviving list is a "
                        "floor: no book "
                        "prints a purpose line, 150 of the 552 rows print no head of "
                        "account either, and a real scheme with a Telugu name and neither "
                        "cannot clear a high bar on the evidence the books print. "
                        "be_lakh is itself a floor, the largest single-book slice of the "
                        "provision, so absent_cr understates too."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/andhra/classification.json", out)
    return out


def check_sample():
    """Report which sampled rows have no hand label yet, so the set can be extended."""
    ap = json.load(open(os.path.join(ROOT, "data", "andhra", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "andhra", "labels.json"),
                            encoding="utf-8"))
    have = {x["key"] for x in labels["labels"]}
    frame = stratify(sorted(ap["entries"], key=entry_key))
    missing = [(entry_key(r), st, r["name"]) for r, st, _, _ in frame
               if entry_key(r) not in have]
    print(f"sampling frame {len(frame)} rows, labelled {len(have)}, "
          f"unlabelled {len(missing)}")
    for k, st, name in missing:
        print(f"  [{st}]  {k[:100]}")
    # The census half of the contract: nothing at or above CENSUS_FROM may be unlabelled.
    uncovered = [entry_key(r) for r in sorted(ap["entries"], key=entry_key)
                 if score_entry(r["name"], r.get("hoas"))[0] >= CENSUS_FROM
                 and entry_key(r) not in have]
    print(f"census at score >= {CENSUS_FROM}: {len(uncovered)} rows unlabelled")
    for k in uncovered:
        print(f"  {k[:100]}")
    return missing, uncovered


def main():
    a = argparse.ArgumentParser(
        description="Classify Andhra Pradesh budget rows as welfare scheme or budget head.")
    a.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    a.add_argument("--check-sample", action="store_true",
                   help="list sampled or census rows that carry no hand label yet")
    args = a.parse_args()
    if args.check_sample:
        check_sample()
        return
    o = run(args.threshold)
    v = o["validation"]
    print(f"andhra rows classified: {o['entries']} "
          f"({o['distinct_names']} distinct names)")
    print(f"  scheme         {o['classified_scheme']:>5}  "
          f"({o['classified_scheme_distinct_names']} distinct names)")
    print(f"  not a scheme   {o['classified_not_scheme']:>5}\n")
    g = o["ground_truth"]
    print(f"ground truth: {g['labelled']} hand labels, {g['scheme']} scheme / "
          f"{g['not_scheme']} not_scheme, {g['borderline']} borderline\n")
    print(f"threshold sweep (precision, recall on the {v['n_labelled']} stratified labels):")
    for s in o["threshold_sweep"]:
        mark = "  <- published" if s["threshold"] == o["publish_threshold"] else ""
        print(f"   {s['threshold']:>3}  called {s['called_scheme']:>4}  "
              f"precision {s['precision']:.3f}  recall {s['recall']:.3f}  "
              f"f1 {s['f1']:.3f}{mark}")
    print(f"\naudit census (every row at or above {CENSUS_FROM} is hand labelled, "
          f"so these are counts):")
    for s in o["threshold_sweep_census"]:
        mark = "  <- published" if s["threshold"] == o["publish_threshold"] else ""
        print(f"   {s['threshold']:>3}  published {s['published']:>4}  "
              f"not schemes {s['not_schemes']:>3}  "
              f"precision {s['precision']:.3f}{mark}")
    p = v["at_publish_threshold"]
    h = v["at_publish_threshold_held_out"]
    c = v["at_publish_threshold_census"]
    print(f"\npublished at threshold {o['publish_threshold']}, not the F1 optimum "
          f"{v['f1_optimal_threshold']}:")
    print(f"  census precision  {c['precision']:.1%}  "
          f"({c['published'] - c['not_schemes']}/{c['published']} published rows really "
          f"are schemes, counted)")
    print(f"  sample precision  {p['precision']:.1%}  on {v['n_labelled']} stratified rows")
    print(f"  recall            {p['recall']:.1%}  ({p['false_negative']} real schemes "
          f"scored below the bar)")
    print(f"  held out          {h['precision']:.1%} precision on the {v['n_held_out']} "
          f"rows no weight was fitted to\n")
    print(f"absent from myScheme Andhra Pradesh and classified a scheme: "
          f"{o['absent_from_myscheme_and_classified_scheme']} of "
          f"{o['absent_from_myscheme_all_rows']} absent rows, "
          f"{o['absent_distinct_names']} distinct names, Rs {o['absent_cr']:,.0f} cr")
    for x in o["absent_schemes"][:10]:
        print(f"   Rs {(x['be_lakh'] or 0) / 100:>10,.0f} cr  score {x['score']:>3}  "
              f"{x['name'][:56]}")


if __name__ == "__main__":
    main()
