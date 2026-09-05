"""
Classify Kerala Annual Plan rows: welfare scheme, or institution, works or accounting head?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ only. Never fetches.

    data/kerala/labels.json          hand ground truth, the input
    data/kerala/classification.json  the verdicts, the output

parse/kerala.py pulls 2,629 rows out of the Annual Plan Statements and the Gender & Child
and Elderly budgets, and every one of them is absent from myScheme, which lists 87 records
tagged Kerala. Publishing 2,629 as "schemes Kerala hides" would be false, and the reason is
on the face of the document: the Annual Plan lists INSTITUTIONS beside schemes. "State
Institute of Languages", "Kerala Sahitya Academy", "Bharat Bhavan", "Kerala State
Chalachitra Academy", "Kerala Agricultural University", "Medical College, Kozhikode" and
the 76 rows naming a wildlife sanctuary, a national park, a tiger reserve or a biosphere
reserve are all plan provisions, and not one of them is a scheme a citizen can apply for.
699 of the 2,629 names carry an institution word, 553 carry an asset or works word, and 925
sit on a capital or loan major head.

Nothing here fetches, and nothing here needs parse/kerala.py either. Unlike Tamil Nadu,
where the classifier has to rebuild the object heads out of the archive because the parser
drops them, data/kerala/schemes.json already carries every field this file reads: the code,
the name, the objectives sentence, the heads of account, the allocation, the books and the
earmarks. There is nothing to reimport and nothing to reimplement.

WHAT KERALA PRINTS THAT THE OTHER THREE DO NOT, AND WHAT IT IS WORTH. Two things, and the
honest answer on both is smaller than it looks.

The FIRST is the objectives sentence. 357 of the 2,629 rows carry one, and Karnataka's
purpose line was that classifier's strongest signal at P(scheme) 0.947. Here the bare
presence of an objectives line measures P(scheme) 0.250 over 16 development rows against a
base rate of 0.174, which is nothing. The reason is where the sentence comes from. It is
not a purpose line at all: it is the Gender & Child and Elderly budgets' note on the row's
WOMEN, CHILD or ELDERLY COMPONENT, and it describes that component rather than the row.
"Kerala Agricultural University" carries one, and it reads: the women components supported
under the scheme are Youth and women empowerment, and Renovation of ladies hostel. 83 of
the 357 end with the literal string "Gender Budget 2026-27" and those measure P(scheme)
0.000 over the 5 that fall in the development half. Worse, the sentence is sometimes
attached to the wrong row: "Weavers/Allied Workers Motivation Programme" carries a sentence
about the Department of Sainik Welfare and ex-servicemen, and "Vanitha Samrudhi - Women
Empowerment Programme" carries the landless housing scheme's sentence. What survives is a
narrow reading of it, the sentence naming a TRANSFER rather than an activity, and that is
worth two points and fires on 85 rows.

The SECOND is the scheme CODE PREFIX. Kerala allots 50 of them, ATC, SWE, AGR, FOR, MPS,
and unlike the printed `sector` string they are present and well formed on all 2,629 rows.
They discriminate enormously: on all 322 stratified rows RDT is 0.875 over 8 rows, WBC
0.517 over 29, LLW 0.455 over 11 and AGR 0.429 over 14, against 0.000 for every one of SES,
FOR, ATC, GEN, MLI, MMI, FSH, RAB and TEN. It is REJECTED anyway and for the reason Tamil
Nadu rejected its department family: it scores the sector rather than the provision, it
would guarantee that a welfare scheme run by the forest department could never clear the
bar, and it is the stratification axis, so scoring it would make the sample and the
classifier agree with each other rather than with the books. The measurement is published
in signals_rejected rather than argued away.

So what does the work is the head of account and the name, as in Andhra Pradesh. Measured
on the 161 rows of the development half against a base rate of 17.4%:

  the state's own accounting classification:
    minor head 800, Other Expenditure                     P(scheme) 0.040 over  25 rows
    capital outlay or loan major head, 4xxx to 7xxx       P(scheme) 0.106 over  66 rows
    establishment or works minor head                     P(scheme) 0.111 over  18 rows
    minor head 190 or 195, money that stops at a body     P(scheme) 0.133 over  15 rows
    a Special Component or Tribal Sub-Plan provision      P(scheme) 0.500 over  10 rows
    welfare function major head                           P(scheme) 0.542 over  24 rows
    minor head 277 or 283, education and housing          P(scheme) 0.714 over   7 rows

  what the name says:
    an accounting or establishment word in the name       P(scheme) 0.000 over  15 rows
    the name ends in a place                              P(scheme) 0.000 over   4 rows
    an institution word in the name                       P(scheme) 0.049 over  41 rows
    an asset or works word in the name                    P(scheme) 0.077 over  39 rows
    a centrally sponsored share-of-cost marker            P(scheme) 0.282 over  39 rows
    a scheme marker word in the name                      P(scheme) 0.400 over  30 rows
    a transliterated scheme brand in the name             P(scheme) 0.571 over  14 rows
    a named beneficiary class in the name                 P(scheme) 0.600 over  15 rows
    a benefit word in the name                            P(scheme) 0.857 over   7 rows

Two of those are worth pausing on. The FIRST is minor head 800, Other Expenditure. It is
the residual head in every Indian major head, and in Kerala it is where a department parks
its own buildings, its one-off projects and its unclassifiable works: 348 rows sit under it
and they are schemes 4% of the time. It is the closest thing this corpus has to Tamil
Nadu's recovery head, and it is not a word in a name but the state's own filing decision.
The SECOND is the transliterated scheme brand. 28 of the 50 schemes in the stratified
sample carry NO benefit word and NO beneficiary word in the name, because they are named
Deendayal Antyodaya Yojana, Pradhan Mantri Awas Yojana, Mahila Kisan Sashaktikaran
Pariyojana or PM KUSUM. A vocabulary of English benefit words is blind to all of them, and
the brand token is what rescues them. It is also the single biggest source of the errors
that survive, because a transliterated brand names a central mission and a central mission
can be a delivery system: Rashtriya Gram Swaraj Abhiyan is panchayat capacity building,
Rashtriya Uchchatar Shiksha Abhiyan is grants to colleges, and POSHAN Abhiyaan buys growth
monitoring devices and software rather than food.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys an identifiable benefit received by a person or household:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan, free supply, a house, land, treatment for a named
                beneficiary class, or training in which the trainee is the beneficiary.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, pays for the
                capacity of the delivery system rather than the benefit, discharges the
                state's obligation to its own serving or engaged staff, or is an accounting
                or adjustment head.

The line that cost the labelling time is not the institution line, which is easy. It is
this: A DEPARTMENTAL DEVELOPMENT PROGRAMME IS NOT A SCHEME UNLESS THE STATE'S OWN WORDS SAY
THE MONEY REACHES A PERSON. Kerala's plan is full of rows called Hi-Tech Agriculture, Soil
Health Management and Productivity Improvement, Extension Forestry, Mariculture Activities
and Development of Crops through Integrated Farming System Approach. Every one of them
probably does pay a subsidy to some cultivator, and none of them says so. They are labelled
not_scheme and flagged borderline. A centrally sponsored mission with published
per-beneficiary assistance norms counts as a scheme under that rule and a state programme
with no stated recipient does not, which is why the National Food Security Mission rows are
schemes and Hi-Tech Agriculture is not. 153 of the 584 labels sat close enough to that line
or to the employment line to be flagged borderline, and each carries the sentence that
decided it.

There are two label sets and they answer different questions.
  stratified, 322 rows   A probability sample across sector families and the allocation
                         range. This is what the threshold sweep runs on, because precision
                         and recall estimated on anything else would not generalise.
  audit, 262 rows        Every remaining row the classifier scores 4 or above. With the 27
                         stratified rows already there, the two sets are a CENSUS of the
                         published region and of the five bands below it, so the published
                         list's error count is counted, not estimated. The audit was made
                         after the weights were fixed and was deliberately not fed back into
                         them, which is why its findings are in known_errors rather than
                         patched.

WHY THE CENSUS STARTS AT 4. Kerala is small enough that the census could have gone lower,
and the cut is set by what the argument needs rather than by what the hand can bear: 289
rows score 4 or more, 409 score 3 or more, and 289 covers the published band and the five
bands beneath it, which is every band a reader could reasonably argue for. Below 4 the
precision numbers here are estimates from the stratified sample and are labelled as such.

BASE RATE, and it is the first finding. 50 of the 322 stratified rows are welfare schemes,
15.5%, against 41% of Andhra Pradesh's scheme-wise rows and 55% of Karnataka's. About one
Kerala Annual Plan row in six is a scheme a citizen could apply for. That is not a fact
about Kerala's welfare state, it is a fact about the document: the Annual Plan is the
state's PLAN provision list and it votes a wildlife sanctuary, a hydro-electric station and
a post-matric scholarship in the same series.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py,
parse/classify_karnataka.py, parse/classify_andhra.py and parse/classify_tamilnadu.py. F1
peaks at threshold 3, where the sample says precision is 74.5% and one published name in
four is not a scheme. Publishing runs at 9. The audit census settles that number, because
it counts errors rather than estimating them:

    threshold 4   289 rows published, 73 are not schemes   precision 74.7%
    threshold 5   213 rows published, 40 are not schemes   precision 81.2%
    threshold 6   148 rows published, 18 are not schemes   precision 87.8%
    threshold 7   102 rows published,  9 are not schemes   precision 91.2%
    threshold 8    55 rows published,  4 are not schemes   precision 92.7%
    threshold 9    38 rows published,  1 is not a scheme   precision 97.4%
    threshold 10   23 rows published,  0 are not schemes   precision 100.0%

Read the bands rather than the cumulative column: the band at exactly 4 is 76 rows of which
33 are not schemes, a marginal precision of 56.6%; the band at 5 is 66.2%; at 6, 80.4%; at
7, 89.4%; at 8, 82.4%; at 9, 93.3%; and everything from 10 up is 100%. Note that the band
at 8 is WORSE than the band at 7, which is what a 17-row band does, and it is why the bar
is not at 8: the three errors in that band are a tribal hostel, a women's helpline and the
insurance premium the state pays for its own anganwadi workers. Threshold 9 is the only bar
on this corpus that reaches the 95% to 97% counted precision the other three states publish
at, and naming a scheme as hidden by a government is an accusation, so that is where it
runs.

THE PRICE IS RECALL, AND IT IS STEEP. 38 rows out of 2,629. Recall at the published bar is
12.0% on the stratified sample and 9.1% on the held-out half, against Karnataka's 31.6%,
Andhra Pradesh's 36.5% and Tamil Nadu's 41.0% at their own bars. Kerala does worse than any
of the three and the reason is measurable rather than mysterious: it prints no object head,
its objectives sentence is about the gender component rather than the purpose, and its
scheme names are the Government of India's transliterated brands, which say nothing to a
vocabulary of English benefit words until the brand list catches them. The published 38 is
a floor on Kerala's schemes and is nowhere near a total. The full census sweep is published
so a reader who will accept 91.2% can read the 102-row list at threshold 7 instead, and the
nine errors in it are named.

The stratified sample alone would have claimed 100% precision at threshold 9, on the
strength of 6 rows above the bar. The census counts 97.4%. It erred flatteringly here, as
Karnataka's and Tamil Nadu's did and as Andhra Pradesh's did not, which is the same lesson
either way: a probability sample is the right tool for recall, which cannot be censused, and
the wrong one for counting mistakes in a list short enough to read.

WHAT IT STILL GETS WRONG. One error survives publication and it is the brand signal firing
on a system: National Nutrition Mission, POSHAN Abhiyaan, at score 9. Below the bar the
same failure mode accounts for most of the misses in both directions, and the largest single
loss is that the National Old Age Pension, Pradhan Mantri Awas Yojana Gramin, the Pradhan
Mantri Matru Vandana Yojana and Deen Dayal Upadhyaya Grameen Kaushalya Yojana all score 7
and are excluded. They are named in known_errors rather than patched out, because the fix
was found by reading the audit and refitting on the audit would destroy the one measurement
in this file that counts errors instead of estimating them.
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
# audit set. Precision at or above it is COUNTED; below it, it is estimated from the
# stratified sample only. See the docstring for why this is 4.
CENSUS_FROM = 4


# ---------------------------------------------------------------------------
# Vocabularies, written by reading the 2,629 names before any number was computed.
# ---------------------------------------------------------------------------

INSTITUTION = {
    "university", "universities", "college", "colleges", "institute", "institutes",
    "institution", "institutions", "corporation", "corporations", "board", "boards",
    "authority", "directorate", "commission", "commissionerate", "academy", "academies",
    "department", "departments", "office", "offices", "bureau", "council", "laboratory",
    "laboratories", "museum", "museums", "library", "libraries", "society", "societies",
    "federation", "trust", "ltd", "limited", "polytechnic", "polytechnics", "cell",
    "cells", "wing", "wings", "sanctuary", "sanctuaries", "park", "parks", "gallery",
    "secretariat", "tribunal", "headquarters", "bhavan", "kendra", "kendram", "academy",
    "undertaking", "undertakings", "mill", "mills", "factory", "press", "kseb", "ksebl",
    "company", "companies", "agency", "agencies", "zoo", "theatre", "auditorium",
    "observatory", "planetarium", "chalachitra", "sahitya", "akademi",
}

WORKS = {
    "construction", "constuction", "contsruction", "building", "buildings",
    "infrastructure", "infrastructural", "infrastruc", "works", "work", "road", "roads",
    "bridge", "bridges", "maintenance", "renovation", "repair", "repairs", "upgradation",
    "upgrading", "modernisation", "modernization", "modernaisation", "equipment",
    "equipments", "machinery", "acquisition", "aquisition", "land", "lands", "quarters",
    "canal", "canals", "dam", "dams", "jetty", "jetties", "harbour", "harbours",
    "stadium", "purchase", "vehicles", "campus", "installation", "electrification",
    "plant", "plants", "erection", "restoration", "desilting", "dredging", "widening",
    "laying", "complex", "premises", "flats", "slipway", "penstock", "anicut",
    "reservoir", "reservoirs", "workshop", "yard", "godown", "godowns", "annexe",
}

ACCOUNTING = {
    "spark", "administrative", "establishment", "establishments", "charges", "expenses",
    "expenditure", "computerisation", "computerization", "egovernance", "survey",
    "surveys", "investigation", "investigations", "studies", "study", "census",
    "monitoring", "evaluation", "audit", "publicity", "documentation", "deduct",
    "recoveries", "recovery", "suspense", "adjustment", "refund", "refunds",
    "feasibility", "dpr", "preparation", "formulation", "planning", "statistics",
    "consultancy", "outsourcing", "salary", "salaries", "honararium", "wages",
    "secretarial", "cadre", "posts", "staff", "manpower", "recruitment",
}

BENEFIT = {
    "scholarship", "scholarships", "scholorships", "stipend", "stipends", "pension",
    "pensions", "incentive", "incentives", "subsidy", "subsidies", "subvention", "free",
    "insurance", "kit", "kits", "nutrition", "nutritious", "reimbursement", "allowance",
    "relief", "concession", "meal", "meals", "waiver", "sponsorship", "honorarium",
    "marriage", "maternity", "uniform", "uniforms", "laptop", "textbooks", "ration",
    "treatment", "gratia", "doles", "dole", "feeding", "annuity", "bhima", "bheema",
}

BENEFICIARY = {
    "students", "student", "women", "woman", "womens", "girls", "girl", "farmers",
    "farmer", "weavers", "weaver", "fishermen", "fisherfolk", "fisherwomen",
    "beneficiaries", "victims", "victim", "workers", "worker", "families", "family",
    "children", "child", "youth", "widow", "widows", "widowed", "divorcees", "disabled",
    "abled", "citizens", "households", "household", "artisans", "entrepreneurs",
    "graduates", "mothers", "adolescent", "orphans", "destitutes", "destitute",
    "unemployed", "homeless", "landless", "tribals", "aged", "elderly", "patients",
    "vendors", "trainees", "transgender", "minorities", "minority", "pensioners",
    "labourers", "unwed", "deserted", "survivors", "inmates", "differently",
}

MARKER = {
    "yojana", "yojna", "yojan", "abhiyan", "abhiyaan", "scheme", "schemes", "pariyojana",
    "nidhi", "samman", "vandana", "vandanam", "mission", "programme", "thittam",
}


BRAND = {
    "pradhan", "mantri", "manthri", "yojana", "yojna", "yojan", "abhiyan", "abhiyaan",
    "antyodaya", "deendayal", "deen", "dayal", "upadhyaya", "kaushalya", "awas", "kisan",
    "samagra", "poshan", "mahila", "gramin", "grameen", "jan", "janjati", "adivasi",
    "vandana", "vandanam", "matru", "mathru", "sashaktikaran", "pariyojana", "swaraj",
    "nyaya", "utkarsh", "jyoti", "suraksha", "samman", "bima", "bheema", "shiksha",
    "ayushman", "swasthya", "swastya", "karyakram", "urja", "kusum", "annapurna",
    "vatsalya", "shakti", "saksham", "unnati", "nidhi", "sinchai", "krishi", "yasasvi",
    "ambedkar", "gandhi", "ayyankali", "narayan",
}

# The share-of-cost marker Kerala prints on every centrally sponsored scheme row:
# "(60% CSS)", "- 40% State Share", "Central Share", "(100% CSS)".
CSS_MARK = re.compile(r"\d+\s*%|\bcss\b|\bstate share\b|\bcentral share\b", re.I)
# The Special Component Plan and Tribal Sub-Plan, written in the name as well as booked
# under minor heads 789 and 796.
SUBPLAN_MARK = re.compile(r"\b(scp|tsp|scsp)\b", re.I)
# "Medical College, Kozhikode", "Kerala Folklore Academy, Thrissur". An institution is
# named by where it stands; a benefit is not.
PLACE_TAIL = re.compile(r",\s*[A-Z][a-z]+\s*$")
# The objectives sentence naming a transfer rather than an activity. See the docstring:
# the bare presence of an objectives line is worth nothing in Kerala and this narrow
# reading of it is worth a little.
OBJ_TRANSFER = re.compile(
    r"\b(financial assistance|assistance (is|for|to)|subsid|scholarship|stipend|"
    r"pension|incentive|free of cost|provided to|given to|reimburse|grant of|paid to|"
    r"loan)", re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def hoa_fields(hoas):
    """Major heads and minor heads of every head of account on the row, sorted."""
    major, minor = set(), set()
    for h in hoas or []:
        p = (h or "").split("-")
        if p and p[0]:
            major.add(p[0])
        if len(p) > 2 and p[2]:
            minor.add(p[2])
    return major, minor


def code_prefix(code):
    m = re.match(r"^\s*([A-Za-z]+)", code or "")
    return m.group(1).upper() if m else ""


# Minor heads are standardised across Indian government accounts, which is what makes
# them readable without knowing the major head: 001 Direction and Administration,
# 003 Training, 004 Research, 005 Investigation, 051 Construction, 052 Machinery and
# Equipment, 053 Maintenance and Repairs.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053"}
# 190 Assistance to Public Sector and Other Undertakings, 195 Assistance to Co-operatives.
# The money stops at a body.
BODY_MINOR = {"190", "195"}
# 800 Other Expenditure, the residual minor head. In Kerala it is where the department
# parks its own projects, buildings and one-off works.
OTHER_MINOR = {"800"}
# 789 Special Component Plan for Scheduled Castes, 793 and 794 the tribal sub-plans,
# 796 Tribal Area Sub-Plan.
SUBPLAN_MINOR = {"789", "793", "794", "796"}
# 277 Education and 283 Housing, the two minor heads Kerala books scholarships, hostels
# and house-building assistance under.
TRANSFER_MINOR = {"277", "283"}
# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC ST and OBC, 2235 Social Security and Welfare, 2236 Nutrition,
# 2501 Special Programmes for Rural Development, 2505 Rural Employment.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2501", "2505"}

# The weights. Negatives are larger than positives on purpose: a row that looks like an
# institution and also carries benefit words, "Post Matric Hostels for Tribals", should
# have to work to clear the bar, because that is the row that would embarrass the list.
WEIGHTS = {
    "inst": -4, "works": -3, "acct": -3, "other_minor": -2, "capital": -2,
    "estab_minor": -2, "body_minor": -2, "place": -2,
    "ben": 3, "who": 2, "welfare": 2, "transfer_minor": 2, "brand": 2, "obj": 2,
    "subplan": 1, "css": 1, "marker": 1,
}


def score_entry(r):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic."""
    name = r.get("name") or ""
    tk = tokens(name)
    obj = r.get("objectives") or ""
    major, minor = hoa_fields(r.get("hoas"))
    ev = []
    total = 0

    def add(key, why):
        nonlocal total
        total += WEIGHTS[key]
        ev.append(["%+d" % WEIGHTS[key], why])

    # What the name says it is.
    inst = sorted(tk & INSTITUTION)
    if inst:
        add("inst", "institution word in the name: " + ", ".join(inst[:3]))
    works = sorted(tk & WORKS)
    if works:
        add("works", "asset or works word in the name: " + ", ".join(works[:3]))
    acct = sorted(tk & ACCOUNTING)
    if acct:
        add("acct", "accounting or establishment word in the name: " + ", ".join(acct[:3]))
    if PLACE_TAIL.search(name):
        add("place", "the name ends in a place, which is how an institution is named")

    # What the state's own chart of accounts says this is.
    cap = sorted(m for m in major if m[:1] in "4567")
    if cap:
        add("capital", "capital outlay or loan major head " + ", ".join(cap[:3]))
    om = sorted(minor & OTHER_MINOR)
    if om:
        add("other_minor", "minor head 800, Other Expenditure")
    em = sorted(minor & ESTAB_MINOR)
    if em:
        add("estab_minor", "establishment or works minor head " + ", ".join(em))
    bm = sorted(minor & BODY_MINOR)
    if bm:
        add("body_minor", "minor head " + ", ".join(bm)
            + ", assistance to an undertaking or a co-operative")

    # Positive structure.
    wel = sorted(major & WELFARE_MAJOR)
    if wel:
        add("welfare", "welfare function major head " + ", ".join(wel[:3]))
    tm = sorted(minor & TRANSFER_MINOR)
    if tm:
        add("transfer_minor", "minor head " + ", ".join(tm)
            + ", where Kerala books scholarships, hostels and house-building assistance")
    if (minor & SUBPLAN_MINOR) or SUBPLAN_MARK.search(name):
        add("subplan", "a Special Component Plan or Tribal Sub-Plan provision")
    if CSS_MARK.search(name):
        add("css", "a centrally sponsored share-of-cost marker in the name")

    # Positive name evidence.
    ben = sorted(tk & BENEFIT)
    if ben:
        add("ben", "benefit word in the name: " + ", ".join(ben[:3]))
    who = sorted(tk & BENEFICIARY)
    if who:
        add("who", "named beneficiary class in the name: " + ", ".join(who[:3]))
    brand = sorted(tk & BRAND)
    if brand:
        add("brand", "a transliterated scheme brand in the name: " + ", ".join(brand[:3]))
    mark = sorted(tk & MARKER)
    if mark:
        add("marker", "scheme marker word in the name: " + ", ".join(mark[:2]))

    # The objectives sentence, and only where it names a transfer.
    if OBJ_TRANSFER.search(obj):
        add("obj", "the objectives line names a transfer, not an activity")

    return total, ev

SIGNALS = [
    {"points": -4, "signal": "an institution word in the name",
     "measured": ("P(scheme) 0.049 over 41 development rows, base rate 0.174, and it fires "
                  "on 699 of the 2,629 rows. This is the signal the whole file exists for: "
                  "the Annual Plan votes the Kerala Agricultural University, the State "
                  "Institute of Languages and 76 wildlife sanctuaries, national parks "
                  "and reserves in the same series as the post-matric scholarship.")},
    {"points": -3, "signal": "an asset or works word in the name",
     "measured": "P(scheme) 0.077 over 39 development rows, fires on 553 rows"},
    {"points": -3, "signal": "an accounting or establishment word in the name",
     "measured": ("P(scheme) 0.000 over 15 development rows, fires on 236 rows. Kerala's "
                  "accounting rows are wordier than Tamil Nadu's Deduct-Recoveries heads and "
                  "read as prose: Establishment Charges Transferred on Percentage Basis from "
                  "2059 - Public Works, Tools and Plant Charges Transferred on Percentage "
                  "Basis, Salary Claims Processed through SPARK.")},
    {"points": -2, "signal": "minor head 800, Other Expenditure",
     "measured": ("P(scheme) 0.040 over 25 development rows, fires on 348 rows. The residual "
                  "minor head of every major head, and in Kerala it is where a department "
                  "parks its own buildings, one-off projects and unclassifiable works. It is "
                  "the state's own filing decision rather than a word in a name, which is "
                  "why it is here and not in the vocabulary.")},
    {"points": -2, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": ("P(scheme) 0.106 over 66 development rows, fires on 925 rows. Weaker than "
                  "in Tamil Nadu, where it measured 0.000, because Kerala books the capital "
                  "side of a housing scheme under 4225 beside the revenue side under 2225.")},
    {"points": -2, "signal": "establishment or works minor head, 001 003 004 005 051 052 053",
     "measured": "P(scheme) 0.111 over 18 development rows, fires on 234 rows"},
    {"points": -2, "signal": "minor head 190 or 195, assistance to an undertaking or a "
                             "co-operative",
     "measured": ("P(scheme) 0.133 over 15 development rows, fires on 158 rows. The state "
                  "saying in its own chart of accounts that the money stops at a body: "
                  "Autokast, Travancore Titanium Products, the Kerala State Co-operative "
                  "Bank.")},
    {"points": -2, "signal": "the name ends in a place",
     "measured": ("P(scheme) 0.000 over 4 development rows, fires on 76 rows. Karnataka's "
                  "rule, dead in Andhra Pradesh, alive here: Medical College, Kozhikode.")},
    {"points": 3, "signal": "a benefit word in the name",
     "measured": ("P(scheme) 0.857 over 7 development rows and 0.923 over the 13 in the full "
                  "stratified sample, the strongest signal in the file. It fires on only 122 "
                  "of the 2,629 rows, which is the whole problem: an English benefit word is "
                  "nearly conclusive in Kerala and nearly absent from it.")},
    {"points": 2, "signal": "a named beneficiary class in the name",
     "measured": "P(scheme) 0.600 over 15 development rows, fires on 204 rows"},
    {"points": 2, "signal": "welfare function major head, 2216 2225 2235 2236 2501 2505",
     "measured": "P(scheme) 0.542 over 24 development rows, lift +0.368, fires on 377 rows"},
    {"points": 2, "signal": "minor head 277 or 283, where Kerala books scholarships, hostels "
                            "and house-building assistance",
     "measured": ("P(scheme) 0.714 over 7 development rows, the highest P of any structural "
                  "signal here, on too few rows to weight more heavily. Fires on 90 rows.")},
    {"points": 2, "signal": "a transliterated scheme brand in the name",
     "measured": ("P(scheme) 0.571 over 14 development rows and 0.520 over the 25 in the "
                  "full stratified sample. Fires on 210 rows. This is what a vocabulary of "
                  "English benefit words cannot do: 28 of the 50 schemes in the stratified "
                  "sample carry no benefit word and no beneficiary word at all, because they "
                  "are named Deendayal Antyodaya Yojana, Pradhan Mantri Awas Yojana or PM "
                  "KUSUM. It is also the largest single source of the errors below the bar, "
                  "because a transliterated brand names a central mission and a central "
                  "mission can be a delivery system.")},
    {"points": 2, "signal": "the objectives line names a transfer rather than an activity",
     "measured": ("P(scheme) 0.250 over 4 development rows, 0.583 over the 12 in the full "
                  "stratified sample. Fires on 85 rows. The development half carries too few "
                  "of these to justify the weight on its own margin and that is stated "
                  "rather than hidden: the weight rests on the full-sample figure and on the "
                  "fact that the bare presence of an objectives line, measured beside it at "
                  "0.250 over 16 rows, is rejected outright. Setting this weight to 0 takes "
                  "the published list from 38 rows to 27 with the same single counted "
                  "error, so all 11 rows it adds are genuine schemes.")},
    {"points": 1, "signal": "a Special Component Plan or Tribal Sub-Plan provision, by minor "
                            "head 789 793 794 796 or by the letters SCP, TSP or SCSP in the "
                            "name",
     "measured": ("P(scheme) 0.500 over 10 development rows, fires on 195 rows. Kerala books "
                  "scheme provisions in the sub-plans and establishment rarely, and it "
                  "writes the sub-plan into the name as often as into the head of account, "
                  "which is why both readings are taken.")},
    {"points": 1, "signal": "a centrally sponsored share-of-cost marker in the name",
     "measured": ("P(scheme) 0.282 over 39 development rows against a base of 0.174, a lift "
                  "of +0.108 and the weakest thing in the table that is kept. It fires on "
                  "613 rows, which is why it is worth one point and no more: Kerala prints "
                  "(60% CSS), 40% State Share and Central Share on road works and watershed "
                  "projects as readily as on the maternity benefit.")},
    {"points": 1, "signal": "a scheme marker word in the name",
     "measured": ("P(scheme) 0.400 over 30 development rows, fires on 562 rows. Weak for the "
                  "reason it is weak everywhere: Green Energy Hub is a Mission and Poshan "
                  "Pakhwada is an Abhiyan.")},
]

REJECTED_SIGNALS = [
    {"signal": "the scheme code prefix, or the sector family it belongs to",
     "measured": ("On all 322 stratified rows the individual prefixes run RDT 0.875 over 8 "
                  "rows, WBC 0.517 over 29, LLW 0.455 over 11 and AGR 0.429 over 14, against "
                  "0.000 for every one of SES over 17 rows, FOR over 15, ATC over 12, GEN "
                  "over 12, MLI over 7, MMI over 7, FSH over 6, RAB over 6 and TEN over 6. "
                  "Grouped into the five families it is WELFARE 0.403 over 67 rows, ECONOMY "
                  "0.186 over 97, INFRA 0.041 over 73, SERVICE 0.032 over 63 and GOVERNANCE "
                  "0.000 over 22, against a base rate of 0.155."),
     "why": ("The task asked for this to be measured rather than assumed, and it is real: a "
             "twelvefold spread between the families and an absolute one between the "
             "prefixes. It is deliberately unused, for the reason Tamil Nadu rejected its "
             "department family. It would score the sector rather than the provision, so a "
             "welfare scheme run by the forest department could never clear the bar and a "
             "wildlife sanctuary paid out of the welfare department would be pushed towards "
             "it. It is also the stratification axis, so scoring it would make the sample "
             "and the classifier agree with each other rather than with the books. The one "
             "thing the prefix IS used for is the sampling frame, where being a clean and "
             "complete sector code on all 2,629 rows is exactly what a stratification axis "
             "needs.")},
    {"signal": "the row carries an objectives line",
     "measured": ("P(scheme) 0.250 over 16 development rows against a base rate of 0.174, "
                  "and 0.268 over the 41 in the full stratified sample against 0.155. The 83 "
                  "rows whose objectives sentence ends with the literal string 'Gender "
                  "Budget 2026-27' measure 0.000 over the 5 of them in the development "
                  "half."),
     "why": ("This is the signal Kerala was supposed to have and it is not there. 357 rows "
             "carry an objectives sentence and Karnataka's purpose line was that "
             "classifier's strongest signal at 0.947, so the expectation was reasonable and "
             "the measurement kills it. The sentence is not a purpose line: it comes from "
             "the Gender & Child and Elderly budgets and it describes the row's WOMEN, CHILD "
             "or ELDERLY COMPONENT rather than the row. 'Kerala Agricultural University' "
             "carries one and it is about youth and women empowerment and the renovation of "
             "a ladies hostel. It is also sometimes attached to the wrong row: "
             "'Weavers/Allied Workers Motivation Programme' carries a sentence about the "
             "Department of Sainik Welfare. What is kept is the narrow reading in SIGNALS, "
             "the sentence naming a transfer, and nothing else.")},
    {"signal": "the row is funded at nil",
     "measured": "P(scheme) 0.227 over 44 development rows against a base rate of 0.174",
     "why": ("733 of the 2,629 rows are funded at nil and the state means something by that: "
             "the scheme exists and carries no provision this year. parse/kerala.py keeps "
             "that apart from having no figure at all, which 3 rows have, and this file "
             "keeps them apart in the sampling frame for the same reason. The measurement "
             "says nil is very slightly MORE likely to be a scheme than the corpus average, "
             "which is noise, and scoring it either way would be wrong: penalising it would "
             "hide exactly the fact a register of hidden schemes should surface, a scheme "
             "the state has parked at zero. 8 of the 38 published rows are funded at nil.")},
    {"signal": "the size of the allocation",
     "measured": ("The four allocation quartiles run 0.227 for nil, 0.265, 0.074, 0.030 and "
                  "0.261 on the development half against a base of 0.174."),
     "why": ("Non-monotone, which is another way of saying it is noise: the first quartile "
             "is the highest, the third is the lowest and the fourth climbs back. A scheme "
             "is not larger or smaller than an institution in Kerala. The National Health "
             "Mission flexible pool is Rs 465 crore and the Kerala Agricultural University "
             "is Rs 78 crore, while the immediate relief fund for survivors of violence is "
             "Rs 3 crore and a wildlife sanctuary can be Rs 7.5 lakh.")},
    {"signal": "the name matches a myScheme record tagged Kerala",
     "measured": ("87 myScheme records carry Kerala in beneficiaryState. The generous "
                  "matcher joins 21 of the 2,629 rows to one of them, and 8 of those 21 are "
                  "wrong on inspection: four rows of the Kerala State Council for Science, "
                  "Technology and Environment join three KSCSTE fellowships on the shared "
                  "acronym, 'Financial Assistance to SI-MET' joins 'Financial Assistance To "
                  "Ex-Convicts', and one garbled row joins five cardamom schemes. "
                  "parse/kerala.py records one of these in known_bad_joins and the rest are "
                  "reproduced in myscheme_join_defects below."),
     "why": ("Measured and rejected for Karnataka at a lift of 0.047, and worse here. 21 "
             "joins over 2,629 rows cannot be ground truth for anything: 99.2% of the corpus "
             "would carry the same value. It is also circular, because the question the "
             "register asks is which rows are ABSENT from myScheme, so scoring a row higher "
             "for being present would systematically push down exactly the rows the answer "
             "is made of.")},
    {"signal": "the row carries no head of account at all",
     "measured": "P(scheme) 0.167 over 6 development rows against a base rate of 0.174",
     "why": ("139 rows carry no head of account and 131 of them are Kerala State "
             "Electricity Board rows: the Board's capital programme is printed as a project "
             "list with no accounts classification, and only 16 of its 147 rows carry a head. It "
             "looked like a free negative signal and it measures at exactly the base rate, "
             "because the KSEB rows are already caught by their names, which are 'Marmala', "
             "'Soura', 'Poringalkuthu Left Bank HE Extn. Scheme' and 'Distbn. Line "
             "Extension'. Scoring the absence of a head of account would penalise a real "
             "scheme the parser failed to attach a head to, which is a cost with no "
             "matching benefit.")},
    {"signal": "the row carries a Gender, Child or Elderly earmark",
     "measured": "P(scheme) 0.200 over 15 development rows against a base rate of 0.174",
     "why": ("351 rows carry an earmark and 333 of them are women or children. It is the "
             "Gender & Child budget saying how much of this provision benefits women and "
             "children, which is a statement about a COMPONENT and not about the row, in "
             "exactly the way the objectives sentence is. The Kerala Agricultural University "
             "carries a women and children earmark of Rs 19.5 lakh and is still a "
             "university.")},
]

KNOWN_ERRORS = [
    {"name": "National Nutrition Mission (POSHAN Abhiyaan) (20% state share) [NUT 020]",
     "score": 9,
     "kind": "false positive, published at threshold 9, and the only one",
     "why": ("The single error that survives publication, and it is the brand signal firing "
             "on a delivery system. POSHAN Abhiyaan scores 9 out of a welfare major head, a "
             "transliterated brand, a scheme marker, a share-of-cost marker and the word "
             "nutrition, which is in the benefit vocabulary. The nutrition it buys is growth "
             "monitoring devices, the ICDS software and behaviour change communication; the "
             "food itself is voted separately under the Supplementary Nutrition Programme "
             "heads, which score 8 to 10 and are correctly published. Two sibling rows, NUT "
             "019 (2) at 7 and NUT 020 (2) at 6, fail the same way below the bar. Adding the "
             "word nutrition to a negative list, or excluding Abhiyaan from the brand set, "
             "would fix all three and would be principled. It is not done, because the fix "
             "was found by reading the audit and refitting on the audit would destroy the "
             "one measurement in this file that counts errors rather than estimating them.")},
    {"name": "Post Matric Hostels for Tribals [WBC 077], Women Helpline under Mission "
             "Shakti-Sambal Scheme [SWE 238 (1)], Insurance coverage for Anganwadi workers "
             "and helpers [SWE 239]",
     "score": 8,
     "kind": "false positive, excluded at threshold 9, and the reason the bar is not at 8",
     "why": ("Three errors in a band of 17 rows, a marginal precision of 82.4%, which is "
             "worse than the band at 7 and is why the bar sits at 9 rather than 8. Each is a "
             "different way of being wrong and each is flagged borderline in the labels. The "
             "hostel head runs and maintains hostels, and its own objectives line says it "
             "provides free boarding and lodging to tribal students, which is the reading "
             "that competes. The helpline is a service the state operates. The insurance "
             "premium is the state insuring its own anganwadi workers and helpers, the same "
             "employment line Tamil Nadu drew against its 2071 pension heads, and its two "
             "child rows at score 6 carry the names Pradhan Mantri Jeevan Jyoti Bima Yojana "
             "and Pradhan Mantri Suraksha Bima Yojana, which is as scheme-like as a name "
             "gets. A reader who thinks free boarding in a tribal hostel IS a welfare scheme "
             "should flip that label in data/kerala/labels.json and rerun.")},
    {"name": "National Social Assistance Programme - National Old Age Pension Scheme, both "
             "shares [SJP 001 (1) and (2)], Pradhan Mantri Awas Yojana Gramin under the "
             "Special Component and Tribal Sub-Plans [WBC 358 and WBC 362 and their share "
             "rows], Pradhan Manthri Mathru Vandana Yojna, both shares [SWE 179 (1) and (2)], "
             "Deen Dayal Upadhyaya Grameen Kaushalya Yojana [WBC 359 and WBC 363 and their "
             "share rows], Supply of Laptop to Students [WBC 290 (6)], Group Insurance "
             "Scheme for Handloom Weavers [VSI 051], Imbichi Bawa Housing Scheme for "
             "Divorcees, Widows and Abandoned Women from the Minority Communities [WBC 277]",
     "score": 7,
     "kind": "false negative, and the price of the bar",
     "why": ("The band at exactly 7 is 47 rows of which 42 are schemes, and losing them is "
             "what threshold 9 costs. The old age pension is the clearest case and its "
             "arithmetic is worth reading: +2 for the welfare major head 2235, +3 for the "
             "benefit word pension, +1 for the share-of-cost marker and +1 for the marker "
             "words Programme and Scheme is 7, and there is nothing else in the row to "
             "find. It names no beneficiary class, because 'Old Age' is two words this "
             "vocabulary does not hold; it carries no transliterated brand, because the "
             "scheme is named in English; and it sits on minor heads 191, 192 and 198, "
             "assistance to municipal corporations, municipalities and panchayats, which "
             "are neither rewarded nor penalised. Two points short. Every one of these rows "
             "is a real scheme and every one is excluded, which is why the published 38 is "
             "a floor and not a total.")},
    {"name": "The band at exactly 4 and 5: Rashtriya Gram Swaraj Abhiyan (six rows), "
             "Rashtriya Uchchatar Shiksha Abhiyaan (two rows), Umbrella Scheme on Krishi "
             "Unnathi Yojana NMAET-SMAE (four rows), Pradhan Mantri Krishi Sinchai Yojana "
             "Watershed Component (two rows), Poshan Pakhwada, Child Helpline Kerala, Hub "
             "for Empowerment of Women, Dr. Ambedkar Village Development Scheme, "
             "Implementation of the Forest Rights Act",
     "score": "4 and 5",
     "kind": "false positive, excluded at threshold 9, and the shape of the failure mode",
     "why": ("The band at 4 is 56.6% precise and the band at 5 is 66.2%, and almost all of "
             "the error is one thing: a transliterated central-mission brand on a row that "
             "funds a system, a village, a college or a watershed rather than a person. "
             "Rashtriya Gram Swaraj Abhiyan is panchayat capacity building, Rashtriya "
             "Uchchatar Shiksha Abhiyan is grants to colleges, NMAET-SMAE is the "
             "agricultural extension machinery, and PM-AJAY, Adi Adarsh Gram and Dharti Aaba "
             "Janjatiya Gram Utkarsh Abhiyan are all tribal and Scheduled Caste VILLAGE "
             "development. The brand signal cannot tell them from Pradhan Mantri Awas "
             "Yojana, and nothing else in the row can either.")},
    {"name": "Vocabulary defects that produce specific errors: 'Procurement of AAdhar "
             "Enrolment Kit', both shares [SWE 213], scores 6 on the word kit; 'Honorarium to "
             "Counselors Engaged in the Hostels and MRS' [WBC 288 (4)] scores 5 on the word "
             "honorarium; 'Barrier Free Kerala Scheme' [SWE 148] scores on the word free",
     "score": "5 and 6",
     "kind": "false positive, excluded at threshold 9",
     "why": ("Three words in the BENEFIT vocabulary that name the thing a person receives in "
             "most contexts and do not here. A kit is a benefit when it is a school kit and "
             "equipment when it is an enrolment kit; an honorarium is a benefit when it is "
             "paid to a trainee and a salary when it is paid to a counsellor the department "
             "engaged; free is a benefit in Free Supply of School Uniforms and an adjective "
             "in Barrier Free. All three are left in, because pruning a vocabulary against "
             "the audit is refitting on the audit.")},
    {"name": "Rows whose printed name merges two provisions: 'Barrier Free Kerala Scheme "
             "State support for National Social Assistance Programme - National Old Age "
             "Scheme (State)' [SJP 004], 'Speciality Health Care Clinic Transgenders "
             "(Homeopathy) Deendayal Antyodaya Yojana - National Urban Livelihood Mission' "
             "[UDT 184], 'Mahila Kisan Sashaktikaran Pariyojana (MKSP) SCSP (40% Share) "
             "Pradhan Manthri Awas Yojana - Gramin' [WBC 358]",
     "score": "4 to 8",
     "kind": "an extraction artefact the classifier inherits",
     "why": ("The Annual Plan's two-column and nine-column table pages sometimes run one "
             "row's name into the next, and parse/kerala.py's extraction_stats record 420 "
             "orphan cells in the Gender & Child book and 84 in the Elderly book. The "
             "classifier scores the merged string as one row and the hand label reads the "
             "provision the head of account belongs to, which is recorded in the reason on "
             "each of those labels. It is named here rather than repaired because repairing "
             "it belongs in parse/kerala.py, not in a classifier.")},
    {"name": "Kerala's own Malayalam-named schemes, and the 733 rows funded at nil",
     "score": "below the bar",
     "kind": "false negative, the recall cost",
     "why": ("Recall at the published bar is 12.0% on the stratified sample and 9.1% on the "
             "held-out half, the worst of the four states. 'Snehapoorvam', 'Thalolam', "
             "'Kedavilakku', 'Margadeepam', 'Vidhyavahini', 'Saayam Prabha' and 'Vanitha "
             "Samrudhi' are Kerala's own brands and a vocabulary of English benefit words "
             "and Hindi scheme brands sees nothing in them; only the head of account can "
             "rescue such a row, and only if it happens to sit under 2225 or 2235. Kerala "
             "could raise this number tomorrow by printing one sentence per scheme saying "
             "what the money is for and who receives it, which is what Karnataka does, and "
             "by printing that sentence against the scheme rather than against its gender "
             "component.")},
]



# ---------------------------------------------------------------------------
# The sampling frame.
# ---------------------------------------------------------------------------

# The 50 code prefixes Kerala itself allots, grouped into five families. The prefix is
# the state's own sector code and it is complete and clean on all 2,629 rows, where the
# printed `sector` string is neither: it carries 79 distinct values including "TOTAL",
# "(KILA)", "(100% CSS)" and "(60% - Mission (Urban) 2.0 2217-05-191-48", which are page
# artefacts rather than sectors. The 50 prefixes cannot each be a stratum: 50 crossed
# with 6 allocation bands is 300 cells and a sample large enough to fill them could not
# be labelled by hand.
FAMILIES = [
    ("WELFARE", ["WBC", "SWE", "SJP", "NUT", "LLW", "HSG"]),
    ("SERVICE", ["MPS", "GEN", "TEN", "ATC", "SYS", "CS", "IAP"]),
    ("ECONOMY", ["AGR", "AHY", "DDT", "FSH", "FOR", "COP", "VSI", "MLI", "MSW", "MNG",
                 "SAD", "OGE", "RDT", "CDT", "EAE", "SSR", "IT", "TRM"]),
    ("INFRA", ["POW", "MMI", "MIN", "RAB", "PWS", "SWS", "UDT", "OTS", "PLS", "RPT",
               "WRT", "NRE", "FC", "SWC", "CAD"]),
    ("GOVERNANCE", ["SES", "EAS", "SAP", "OGS"]),
]
FAMILY_OF = {p: n for n, ps in FAMILIES for p in ps}


def family(code):
    return FAMILY_OF.get(code_prefix(code), "GOVERNANCE")


def band(r, cuts):
    """Allocation band. nil and nofig are kept apart because the source keeps them apart.

    733 rows are funded at nil, which is Kerala saying the scheme exists and carries no
    provision this year. 3 rows carry no figure at all. Collapsing the two would erase a
    distinction the Annual Plan prints.
    """
    v = r.get("be_lakh")
    if v is None:
        return "nofig"
    if v == 0:
        return "nil"
    return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"


def stratify(entries, target=320):
    """Deterministic stratified sample: sector family crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by key and picked at even
    spacing, so this returns the same rows on every machine and every run.
    """
    alloc = sorted(r["be_lakh"] for r in entries if (r.get("be_lakh") or 0) > 0)
    cuts = [alloc[int(len(alloc) * f)] for f in (0.25, 0.5, 0.75)] if alloc else [0, 0, 0]
    cells = {}
    for r in entries:
        cells.setdefault((family(r["code"]), band(r, cuts)), []).append(r)
    out = []
    for k in sorted(cells):
        rows = sorted(cells[k], key=lambda r: r["key"])
        n = min(len(rows), max(4, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda t: t[0]["key"])


def myscheme_kerala():
    """Scheme names myScheme lists for Kerala. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("kerala" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    2,629 rows against 87 records is only 229,000 calls to probably_same, so this is not
    the speed problem Tamil Nadu had. It is kept for the same reason it is right there:
    every branch in probably_same that can return True requires the pair to share a
    content token, share a transliteration skeleton, or stand in an acronym relation, so
    the index is an EXACT superset of the pairs that can match rather than a
    speed-for-accuracy trade.
    """
    tok, skel, acro = {}, {}, {}
    for n in listed:
        for k in set(_m.tokens(n)):
            tok.setdefault(k, set()).add(n)
        for k in set(_m.skeletons(n)):
            skel.setdefault(k, set()).add(n)
        for k in set(_m.acronyms(n)):
            acro.setdefault(k, set()).add(n)
    return {"tok": tok, "skel": skel, "acro": acro, "acronyms": sorted(acro)}


def myscheme_candidates(name, idx):
    """Every myScheme name that could possibly match this one, sorted."""
    out = set()
    for k in set(_m.tokens(name)):
        out |= idx["tok"].get(k, set())
        out |= idx["acro"].get(k, set())
    for k in set(_m.skeletons(name)):
        out |= idx["skel"].get(k, set())
    for k in set(_m.acronyms(name)):
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


def run(threshold=PUBLISH_THRESHOLD):
    ke = json.load(open(os.path.join(ROOT, "data", "kerala", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(ke["entries"], key=lambda r: r["key"])

    labels = json.load(open(os.path.join(ROOT, "data", "kerala", "labels.json"),
                            encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_kerala()
    idx = myscheme_index(listed)

    rows = []
    for r in entries:
        total, ev = score_entry(r)
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in myscheme_candidates(r["name"], idx)
               if probably_same(r["name"], n)[0]]
        major, minor = hoa_fields(r.get("hoas"))
        rows.append({
            "key": r["key"],
            "code": r["code"],
            "name": r["name"],
            "sector": r.get("sector"),
            "code_prefix": code_prefix(r["code"]),
            "family": family(r["code"]),
            "hoas": sorted(r.get("hoas") or []),
            "major_heads": sorted(major),
            "minor_heads": sorted(minor),
            "be_lakh": r.get("be_lakh"),
            "books": sorted(r.get("books") or []),
            "earmarks": r.get("earmarks") or None,
            "has_objectives": bool((r.get("objectives") or "").strip()),
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_kerala": bool(hit),
            "myscheme_match": sorted(hit) or None,
            "hand_label": by_key[r["key"]]["label"] if r["key"] in by_key else None,
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
    absent_all = [x for x in rows if not x["in_myscheme_kerala"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_kerala"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per NAME as well as per scheme code, because Kerala votes the central share
    # and the state share of one scheme as two codes, and its Special Component and Tribal
    # Sub-Plan provisions as two more. Publishing the codes would print Post-Matric
    # Scholarship four times down a page and read as four findings. The allocations add,
    # because these are separate provisions and not overlapping cuts of one figure.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"].lower())
        if e is None:
            e = by_name[x["name"].lower()] = {
                "name": x["name"], "codes": [], "hoas": [], "be_lakh": 0.0,
                "score": x["score"], "evidence": x["evidence"]}
        e["codes"].append(x["code"])
        e["hoas"].extend(x["hoas"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["codes"] = sorted(r["codes"])
        r["hoas"] = sorted(set(r["hoas"]))
        r["be_lakh"] = round(r["be_lakh"], 2)

    joined = sorted((x for x in rows if x["in_myscheme_kerala"]), key=lambda x: x["key"])

    out = {
        "built": utcnow(),
        "snapshot": ke.get("snapshot"),
        "state": "Kerala",
        "cycle": ke.get("cycle"),
        "source": "data/kerala/schemes.json",
        "question": ("Which of Kerala's 2,629 Annual Plan rows are welfare schemes, and "
                     "which are institutions, works heads, departmental programmes or "
                     "accounting heads?"),
        "entries": len(rows),
        "distinct_names": len({x["name"].lower() for x in rows}),
        "counting_basis": (
            "EVERY COUNT HERE IS ON THE 2,629 SCHEME CODE BASIS unless the field name says "
            "distinct. The code is Kerala's own identifier for the provision, it is present "
            "and well formed on every row, and it is what the Annual Plan votes: a scheme's "
            "central share and its state share are separate codes, and its Special Component "
            "Plan and Tribal Sub-Plan provisions are separate codes again. The 2,629 codes "
            "carry 2,611 distinct names. The head of account could not be the key here as it "
            "is in Tamil Nadu, because 139 rows carry none at all and 419 rows carry more "
            "than one. absent_distinct is the de-duplicated view of the same list."),
        "publish_threshold": threshold,
        # The F1 optimum, the bar for the WEAKER claim: "this state's budget names
        # this as a scheme". It lived only in site/build.py, so the data could not
        # say which rows the site lists and anything else reading this file had to
        # guess. parse/cag_join.py guessed by skipping this state entirely.
        "listing_threshold": 3,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"].lower() for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "funded_at_nil": sum(1 for x in rows if x.get("be_lakh") == 0),
        "funded_at_nil_and_classified_scheme": sum(
            1 for x in schemes if x.get("be_lakh") == 0),
        "no_figure_at_all": sum(1 for x in rows if x.get("be_lakh") is None),
        "funded_at_nil_note": (
            "733 rows are printed with a figure of zero and 3 with no figure at all, and "
            "parse/kerala.py keeps those apart because the source does. A nil figure is the "
            "state saying the scheme exists and carries no provision this year, which is a "
            "fact a register of hidden schemes should surface rather than filter out. 8 of "
            "the published rows are funded at nil."),
        "rows_with_objectives": sum(1 for x in rows if x["has_objectives"]),
        "rows_with_no_head_of_account": sum(1 for x in rows if not x["hoas"]),
        "ground_truth": {
            "file": "data/kerala/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "sets": labels["sets"],
            "why_not_myscheme": (
                "myScheme membership cannot be the ground truth here and it was not a close "
                "call. 87 myScheme records carry Kerala in beneficiaryState and the generous "
                "matcher joins 21 of the 2,629 rows to one of them, so 99.2% of the corpus "
                "would carry the same value; 8 of the 21 joins are wrong on inspection and "
                "are listed in myscheme_join_defects. It was measured and rejected for "
                "Karnataka at a lift of 0.047 and it is worse here. It is also circular: the "
                "question is which rows are absent from myScheme, so scoring presence would "
                "push down exactly the rows the answer is made of."),
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
            "base_rate_development": round(
                sum(1 for x in dev if x["label"] == "scheme") / len(dev), 3),
            "base_rate_held_out": round(
                sum(1 for x in held if x["label"] == "scheme") / len(held), 3),
            "base_rate_note": (
                "About one Kerala Annual Plan row in six is a welfare scheme, against 41% of "
                "Andhra Pradesh's scheme-wise rows and 55% of Karnataka's, and close to Tamil "
                "Nadu's 16%. That is a fact about the document rather than about Kerala's "
                "welfare state: the Annual Plan is the state's plan PROVISION list and it "
                "votes a wildlife sanctuary, a hydro-electric station and a post-matric "
                "scholarship in the same series."),
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
                "because 289 rows score 4 or more and that covers the published band and the "
                "five bands beneath it, which is every band a reader could reasonably argue "
                "for. Recall still comes from the stratified sample, because the rows the "
                "classifier rejects are too many to label exhaustively."
                % (CENSUS_FROM, CENSUS_FROM)),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": (
                "F1 peaks at threshold 3, where the sample says precision is 74.5% and one "
                "published name in four is not a scheme. Naming a scheme as hidden by a "
                "government is an accusation, so this runs at the high-precision end and "
                "accepts the recall loss. Read the bands rather than the cumulative column: "
                "the band at exactly 4 is 56.6% precise, at 5 it is 66.2%, at 6 it is 80.4%, "
                "at 7 it is 89.4%, at 8 it FALLS to 82.4% on 17 rows, at 9 it is 93.3% and "
                "from 10 up it is 100%. Threshold 9 is the only bar on this corpus that "
                "reaches the 95% to 97% counted precision Karnataka, Andhra Pradesh and "
                "Tamil Nadu publish at."),
            "sample_versus_census": (
                "The stratified sample alone would have claimed 100% precision at threshold "
                "9, on the strength of 6 rows above the bar, and the held-out half would "
                "have claimed 100% on 2. The census counts 97.4% on 38. It erred "
                "flatteringly here, as Karnataka's and Tamil Nadu's did and as Andhra "
                "Pradesh's did not, which is the same lesson either way: a probability "
                "sample is the right tool for recall, which cannot be censused, and the "
                "wrong one for counting mistakes in a list short enough to read."),
            "what_the_objectives_line_cost": (
                "Kerala was expected to do better than Andhra Pradesh and Tamil Nadu because "
                "357 of its rows carry an objectives sentence, and Karnataka's purpose line "
                "was that classifier's strongest signal at P(scheme) 0.947. It does worse "
                "than all three. The sentence is not a purpose line: it is the Gender & "
                "Child and Elderly budgets' note on the row's women, child or elderly "
                "COMPONENT, its bare presence measures P(scheme) 0.250 against a base of "
                "0.174, and the 83 rows whose sentence ends 'Gender Budget 2026-27' measure "
                "0.000 on the development half. What carries this corpus instead is the "
                "minor head and the transliterated scheme brand. Recall at the published bar "
                "is 12.0% on the stratified sample and 9.1% on the held-out half, against "
                "Karnataka's 31.6%, Andhra Pradesh's 36.5% and Tamil Nadu's 41.0%."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_kerala_records": len(listed),
        "myscheme_record_count_note": (
            "Counted live off data/myscheme/schemes/, every record whose beneficiaryState "
            "list mentions Kerala. parse/kerala.py's own run over the same directory found "
            "eleven joins where this one finds %d, because the myScheme snapshot has grown "
            "since. Both numbers are reported rather than reconciled, because a silently "
            "moving denominator is exactly the kind of thing a register should show rather "
            "than smooth over." % len(joined)),
        "myscheme_joins": len(joined),
        "myscheme_join_defects": [
            {"kerala": x["name"], "code": x["code"], "myscheme": x["myscheme_match"]}
            for x in joined
        ],
        "myscheme_join_defects_note": (
            "All %d joins, listed so a reader can check them rather than take the absence "
            "count on trust. Eight are wrong: the four Kerala State Council for Science, "
            "Technology and Environment rows join three KSCSTE fellowships on the shared "
            "acronym, 'Financial Assistance to SI-MET' joins 'Financial Assistance To "
            "Ex-Convicts' on two content words, and the garbled row 'Kerala (Training to "
            "Kudumbashree workers) MINERALS & SMALL I...' joins five cardamom schemes. "
            "parse/kerala.py records one of these in its own known_bad_joins and argues "
            "there, correctly, that the direction of the error is the safe one: a false "
            "match means a Kerala scheme is treated as PRESENT on myScheme and is therefore "
            "not claimed absent, so it costs an under-reported absence rather than a false "
            "accusation." % len(joined)),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_distinct_names": len({x["name"].lower() for x in absent}),
        "absent_lakh": round(sum(x["be_lakh"] or 0 for x in absent), 2),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": (
            "Absence is decided by parse/match.py's generous matcher against the myScheme "
            "records tagged Kerala, because claiming absence should require that even a "
            "generous matcher finds nothing. The list is a floor twice over. Once because "
            "the matcher over-joins: 8 of its 21 joins are wrong, so a row counted present "
            "may not be. And once because recall at the published bar is 12%: a real scheme "
            "with a Malayalam name, no benefit word and a head of account outside 2225 and "
            "2235 cannot clear a high bar on the evidence the Annual Plan prints."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/kerala/classification.json", out)
    return out


def check_sample():
    """Report which sampled or census rows have no hand label yet."""
    ke = json.load(open(os.path.join(ROOT, "data", "kerala", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "kerala", "labels.json"),
                            encoding="utf-8"))
    have = {x["key"] for x in labels["labels"]}
    entries = sorted(ke["entries"], key=lambda r: r["key"])
    frame = stratify(entries)
    missing = [(r["key"], st, r["name"]) for r, st, _, _ in frame if r["key"] not in have]
    print("sampling frame %d rows, labelled %d, unlabelled %d"
          % (len(frame), len(have), len(missing)))
    for k, st, name in missing:
        print("  [%s]  %s  %s" % (st, k, name[:80]))
    # The census half of the contract: nothing at or above CENSUS_FROM may be unlabelled.
    uncovered = [r["key"] for r in entries
                 if score_entry(r)[0] >= CENSUS_FROM and r["key"] not in have]
    print("census at score >= %d: %d rows unlabelled" % (CENSUS_FROM, len(uncovered)))
    for k in uncovered:
        print("  %s" % k)
    return missing, uncovered


def main():
    a = argparse.ArgumentParser(
        description="Classify Kerala Annual Plan rows as welfare scheme or budget head.")
    a.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    a.add_argument("--check-sample", action="store_true",
                   help="list sampled or census rows that carry no hand label yet")
    a.add_argument("--dump-frame", action="store_true",
                   help="print the stratified sampling frame, one row per line")
    args = a.parse_args()
    if args.dump_frame:
        ke = json.load(open(os.path.join(ROOT, "data", "kerala", "schemes.json"),
                            encoding="utf-8"))
        entries = sorted(ke["entries"], key=lambda r: r["key"])
        for r, st, sz, sm in stratify(entries):
            print("%-16s|%-14s|%s|%s|%s|%s" % (
                r["key"], st, r["be_lakh"], ",".join(sorted(r["hoas"] or [])),
                r["name"], (r.get("objectives") or "")[:200]))
        return
    if args.check_sample:
        check_sample()
        return
    o = run(args.threshold)
    v = o["validation"]
    print("kerala annual plan rows classified: %d (%d distinct names)"
          % (o["entries"], o["distinct_names"]))
    print("  scheme         %5d  (%d distinct names)"
          % (o["classified_scheme"], o["classified_scheme_distinct_names"]))
    print("  not a scheme   %5d" % o["classified_not_scheme"])
    print("  base rate on the stratified sample %.1f%% of %d rows"
          % (100 * v["base_rate_stratified"], v["n_labelled"]))
    print("  at threshold %d, sample   precision %.3f  recall %.3f"
          % (o["publish_threshold"], v["at_publish_threshold"]["precision"],
             v["at_publish_threshold"]["recall"]))
    print("  at threshold %d, held out precision %.3f  recall %.3f"
          % (o["publish_threshold"], v["at_publish_threshold_held_out"]["precision"],
             v["at_publish_threshold_held_out"]["recall"]))
    print("  at threshold %d, COUNTED  precision %.3f  over %d rows, %d not schemes"
          % (o["publish_threshold"], v["at_publish_threshold_census"]["precision"],
             v["at_publish_threshold_census"]["published"],
             v["at_publish_threshold_census"]["not_schemes"]))
    print("  myScheme Kerala records %d, joins %d"
          % (o["myscheme_kerala_records"], o["myscheme_joins"]))
    print("  absent from myScheme and classified scheme: %d (%d distinct names, Rs %.2f cr)"
          % (o["absent_from_myscheme_and_classified_scheme"],
             o["absent_distinct_names"], o["absent_cr"]))


if __name__ == "__main__":
    main()
