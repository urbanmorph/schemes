"""
Classify Tamil Nadu Demand Book sub-heads: welfare scheme, or establishment and works head?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ and archive/. Never fetches.

    data/tamilnadu/labels.json         hand ground truth, the input
    data/tamilnadu/object_heads.json   a cache, rebuilt from the archive when stale
    data/tamilnadu/classification.json the verdicts, the output

parse/tamilnadu.py pulls 6,220 distinct heads of account out of the 55 per-department
Demand Books of the Revised Budget Estimate, and its own caveat already says the plain
truth: those are the state's FULL detailed estimates, so the list is a superset of Tamil
Nadu's schemes and not a count of them. 571 of the names begin with an establishment word,
184 are "Deduct - Recoveries" heads, 35 carry a negative provision. Set against myScheme's
234 Tamil Nadu records, essentially the whole 6,220 is absent from the national citizen
portal, and publishing that number as "schemes Tamil Nadu hides" would be false. It would
mean naming the district police establishment, the Chief Engineer's Buildings heads and the
house building advance to government servants as schemes a government hid.

WHAT IS DIFFERENT HERE, AND IT IS WHAT MAKES IT WORK. Karnataka's books print a purpose
line, one sentence saying what the money buys, and that was the strongest signal in
parse/classify_karnataka.py at P(scheme) 0.947. Tamil Nadu prints no purpose line either,
so this is the Andhra Pradesh situation. But Tamil Nadu prints something Andhra Pradesh did
not: under every sub-head it prints the OBJECT HEADS, the state saying in its own chart of
accounts whether this money is `301 Salaries`, `416 Major Works`, `311 Subsidies`,
`312 Scholarships and Stipends`, `327 Pensions` or `367 Feeding/Dietary Charges`. That is
the closest thing this corpus has to a purpose line and it is the strongest signal in this
file:

    every object head on the row is a benefit transfer head   P(scheme) 0.895 over 19 rows
    every object head on the row is an accounting head        P(scheme) 0.000 over 51 rows

WHERE THE OBJECT HEADS COME FROM, and why this file reads the archive. data/tamilnadu/
schemes.json does NOT carry them. parse/tamilnadu.py reads all 19,356 object rows and
deliberately drops them, for a good reason stated in its docstring: publishing "Major
Works", "Salaries" and "Motor Vehicles" as if they were schemes is the trap that file
exists to avoid. So this file rebuilds the object head index itself, out of
archive/tamilnadu/<date>/, by importing parse/tamilnadu.py and reusing its page geometry
rather than reimplementing it. That takes about 30 seconds across the 55 books, so the
result is cached at data/tamilnadu/object_heads.json and keyed on the archive date; a
different date rebuilds it. Nothing here fetches. The cleaner home for this is
parse/tamilnadu.py emitting an `object_heads` list on every entry, at which point this
whole section and its cache can be deleted.

THE KEY IS THE HEAD OF ACCOUNT. `2225 01 277 AB` is major head, sub-major, minor head and
sub-head, and it is Tamil Nadu's own identifier for the provision. 6,220 heads of account
carry 4,767 distinct names. EVERY COUNT IN THIS FILE IS ON THE 6,220 HEAD OF ACCOUNT BASIS
unless the field name says distinct, because the state votes a scheme's revenue head and
its capital head separately and because it books a recovery mirror of many schemes under
minor head 911 which carries the scheme's own name. Collapsing on the name would merge a
provision with its own recovery head. The distinct-name count is carried alongside every
published figure so a reader can see both, and the absent list is also published
de-duplicated by name.

There are two label sets and they answer different questions.
  stratified, 399 rows   A probability sample across department families and the allocation
                         range. This is what the threshold sweep runs on, because precision
                         and recall estimated on anything else would not generalise.
  audit, 430 rows        Every remaining row the classifier scores 8 or above. With the 32
                         stratified rows already there, the two sets are a CENSUS of the
                         published region and of the band below it, so the published list's
                         error count is counted, not estimated. The audit was made after the
                         weights were fixed and was deliberately not fed back into them,
                         which is why its findings are in known_errors rather than patched.

WHY THE CENSUS STARTS AT 8 AND NOT LOWER. This is the one methodological choice the scale
forces. Karnataka censused 969 rows from score 5 and Andhra Pradesh 552 rows from score 3.
Tamil Nadu has 6,220 rows, and the census sets at the lower thresholds are: 972 rows at
score 5, 640 at 7, 462 at 8, 376 at 9. 462 rows is the largest set that can be read one by
one and labelled reliably by hand, and it covers the published region plus the two bands
below it, which is what the threshold argument needs. Below 8 the precision numbers in this
file are estimates from the stratified sample and are labelled as such.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a fee waiver, a pension, insurance, a
                subsidy, a loan, free travel, free power, a house, treatment for a named
                beneficiary class, or training in which the trainee is the beneficiary.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, pays for the
                capacity of the delivery system rather than the benefit, discharges the
                state's obligation to its own serving or retired staff, or is an accounting
                or adjustment head.

Two lines did most of the work here and neither appears in Karnataka or Andhra Pradesh.
First, AN EMPLOYMENT OBLIGATION IS NOT A WELFARE SCHEME. The service pension, the family
pension, the death gratuity, the medical allowance to pensioners, the house building advance
to government servants and the funeral assistance to the state's own anganwadi and noon meal
workers are all cash paid to identifiable households, and all of them are labelled
not_scheme because the state pays them as an employer. The social pensions under major head
2235 are schemes and the service pensions under major head 2071 are not, and the books print
the two in the same words under the same object head 327. Second, for the central crop
missions THE STATE'S OWN OBJECT HEAD DECIDES: booked as 311 Subsidies the money is paid out
to the grower and the row is a scheme; booked as 309 Grants-in-Aid it goes to an
implementing agency and the row is not. 130 of the 829 labels sat close enough to one of
those lines to be flagged borderline, and each carries the sentence that decided it.

WHAT ACTUALLY DISCRIMINATES. Measured on the 200 rows of the development half against a
base rate of 16.0%, which is itself the first finding: only about one Tamil Nadu Demand Book
sub-head in six is a welfare scheme, where 41% of Andhra Pradesh's scheme-wise rows and 55%
of Karnataka's were.

  the state's own accounting classification, which is not a guess:
    every object head is a benefit transfer head          P(scheme) 0.895 over 19 rows
    every object head is an accounting head               P(scheme) 0.000 over 51 rows
    recovery or adjustment minor head, 911 and 902        P(scheme) 0.000 over 32 rows
    capital outlay or loan major head, 4xxx to 7xxx       P(scheme) 0.000 over 38 rows
    a running cost or works object head                   P(scheme) 0.047 over 86 rows
    sub-plan minor head, 789 793 794 796                  P(scheme) 0.526 over 19 rows
    welfare function major head                           P(scheme) 0.391 over 46 rows
    establishment or works minor head                     P(scheme) 0.077 over 26 rows
    sub-head code in the J, U, V or W blocks              P(scheme) 0.377 over 53 rows

  what the name says:
    the name begins with an establishment word            P(scheme) 0.000 over 15 rows
    the name begins Add or Deduct                         P(scheme) 0.000 over 10 rows
    an accounting word in the name                        P(scheme) 0.000 over 17 rows
    the name is a Buildings head                          P(scheme) 0.000 over  4 rows
    the name ends in a place                              P(scheme) 0.000 over  5 rows
    an asset or works word in the name                    P(scheme) 0.024 over 42 rows
    the name names a body                                 P(scheme) 0.056 over 72 rows
    a named beneficiary class in the name                 P(scheme) 0.500 over 38 rows
    a benefit word in the name                            P(scheme) 0.339 over 56 rows
    a scheme marker word in the name                      P(scheme) 0.286 over 42 rows

Three of those are worth pausing on. The FIRST is that Tamil Nadu's minor head 911 is not a
weak signal, it is an exact one: all 867 rows in the corpus under it carry exactly one
object head, 377 Deduct-Recoveries, and all 867 are funded at nil. They are accounting
mirrors that repeat the scheme's own name, which is why 731 of the 867 do not begin with
the word Deduct and would otherwise score like the schemes they mirror. The SECOND is that
309 Grants-in-Aid, which fires on 1,573 heads and is the single commonest object head in the
books, is NOT evidence of a scheme: rows whose only object head is 309 are schemes 18.4% of
the time against a base rate of 16.0%, because Tamil Nadu books a grant to a university and
a maternity assistance payment under the same object head. That is why the transfer group
in TRANSFER_OBJ excludes it and why "every object head is a transfer head", the rule that
carried Andhra Pradesh, had to be narrowed here to the object heads that name a benefit.
The THIRD is the sub-head letter. Tamil Nadu allots sub-head codes in blocks and the J, U, V
and W blocks carry the centrally sponsored and newer state schemes while the A block carries
the old establishment heads: P(scheme) 0.377 against 0.076 for A. It is real and it is
morphology rather than meaning, so it is worth one point and no more.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py,
parse/classify_karnataka.py and parse/classify_andhra.py. F1 peaks at threshold 5, where
the sample says precision is 83.3% and one published name in six is not a scheme. Publishing
runs at 10. The audit census settles that number, because it counts errors rather than
estimating them:

    threshold  8   462 rows published, 53 are not schemes   precision 88.5%
    threshold  9   376 rows published, 20 are not schemes   precision 94.7%
    threshold 10   326 rows published, 12 are not schemes   precision 96.3%
    threshold 11   243 rows published,  5 are not schemes   precision 97.9%
    threshold 12   173 rows published,  5 are not schemes   precision 97.1%
    threshold 13   109 rows published,  1 is not a scheme   precision 99.1%
    threshold 14    58 rows published,  0 are not schemes   precision 100.0%

The break is between 9 and 10. Read the bands rather than the cumulative column: the band at
exactly 8 is 86 rows of which 33 are not schemes, a marginal precision of 61.6%; the band at
exactly 9 is 50 rows with 8 errors, 84.0%; the band at exactly 10 is 83 rows with 7 errors,
91.6%; and the band at exactly 11 is 70 rows with none. Buying the 1.6 points between
threshold 10 and threshold 11 would mean dropping 83 rows of which 76 really are schemes,
which is not a trade, it is a loss. Note also that precision is not monotone: it FALLS from
97.9% at 11 to 97.1% at 12, because the clean band at 11 is removed and the four errors
above it are not. Threshold 10 it is, and the twelve errors that survive are named in
known_errors rather than patched out.

The stratified sample alone would have said 100% at threshold 10, on the strength of 25
rows. The census says 96.3%. Note the direction: here the probability sample was flattering,
as Karnataka's was, where Andhra Pradesh's was pessimistic, which is the same lesson either
way. A sample of 399 rows leaves too few above the bar to state the published list's
precision to better than a few points, and which way it errs is luck. Precision is counted.
Recall is estimated, because the rows the classifier rejects are too many to label
exhaustively.

WHAT IT STILL GETS WRONG, and it is one failure mode wearing several hats. Seven of the
twelve surviving errors are major head 2071, Pensions and Other Retirement Benefits, and all
twelve except two are the state paying its own retired staff: relief to All India Service
pensioners, family pension to ex-village officers, ex-gratia to families of deceased
non-provincialised employees, medical reimbursement to pensioners, the livelihood pension to
retired noon meal and child development workers, family pension for anganwadi employees.
Every one is cash to a household, booked under object head 327 Pensions, with a beneficiary
class in its name. Nothing in the head of account distinguishes it from the Indira Gandhi
National Old Age Pension. Adding major head 2071 to the penalty list would fix seven of the
twelve at a stroke and would be principled, but the fix was found by reading the audit, and
changing weights to suit the audit would destroy the one measurement in this file that
counts errors instead of estimating them. It is named here instead.

WHAT THE MISSING PURPOSE LINE COSTS. Recall at threshold 10 is 41.0% on the stratified
sample and 44.8% on the held-out half, against Karnataka's 31.6% and Andhra Pradesh's 36.5%
at their own published bars. Tamil Nadu does better than either without a purpose line
because its object heads are richer. The rows it loses are the ones where the state books a
transfer under an object head that is not one: Magalir Urimai Thogai's general head, Rs 9,803
crore of it, carries 308 Advertising and Publicity beside 311 Subsidies and is penalised for
saying so; every one of the ten Free Supply of Bicycles heads is booked as 309 Grants-in-Aid
and none of them clears the bar. A Tamil scheme name says nothing to a vocabulary of English
benefit words, and 309 rescues nothing because Tamil Nadu uses it for everything. The published count is a floor on Tamil Nadu's schemes and never a
total, and the state could raise it tomorrow by printing what each sub-head is for.
"""

import argparse
import collections
import glob
import gzip
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

PUBLISH_THRESHOLD = 10

# Every row at or above this score carries a hand label, from the stratified set or the
# audit set. Precision at or above it is counted; below it, it is estimated from the
# stratified sample only. See the docstring for why this is 8 and not 5.
CENSUS_FROM = 8

OBJECT_CACHE = os.path.join("data", "tamilnadu", "object_heads.json")


# ---------------------------------------------------------------------------
# The object head index, rebuilt from the archive because the parsed file drops it.
# ---------------------------------------------------------------------------

def _archive_date():
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "tamilnadu", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/tamilnadu/: run collect/tamilnadu.py first")
    return dates[-1]


def _object_heads_of_book(pages, tn):
    """Every object head printed under every sub-head of one book, as {hoa: [codes]}.

    The level test is parse/tamilnadu.py's own and is not reimplemented: a row carrying a
    head of account whose printed leading code is NOT the sub-head field, and whose
    detailed head is a X00 rather than the X0000 sub-head placeholder, is an object head.
    The page geometry, the money column anchors and the name and head of account split all
    come from that module, so a layout change breaks both files together rather than
    silently desynchronising them.
    """
    out = collections.defaultdict(set)
    for rows in pages:
        i, strip = tn.strip_row(rows)
        if strip is None or len(strip[2]) != 7:
            continue
        centres = [(c[0] + c[1]) / 2.0 for c in strip[2]]
        body = [r for r in rows if r[0] > strip[1]]
        name_left = (centres[0] + centres[1]) / 2.0
        anchors = tn.money_anchors(centres, body)
        for row in body:
            hoa, _figs, name, _seen = tn.split_row(row, name_left, anchors)
            if not hoa:
                continue
            f = hoa.split()
            sub, detail = f[3], f[4]
            lead = name[0][2] if name else None
            if lead == sub or not detail.endswith("00") or tn.SUB_DETAIL.match(detail):
                continue
            out[" ".join(f[:4])].add(detail[:3])
    return out


def object_heads(date=None, verbose=False):
    """{head of account: sorted object head codes}, from the cache or from the archive."""
    date = date or _archive_date()
    path = os.path.join(ROOT, OBJECT_CACHE)
    if os.path.exists(path):
        cached = json.load(open(path, encoding="utf-8"))
        if cached.get("date") == date:
            return cached["heads"]
    tn = _load("tn_parse", os.path.join(HERE, "tamilnadu.py"))
    src = os.path.join(ROOT, "archive", "tamilnadu", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))
    heads = collections.defaultdict(set)
    for book in sorted(man.get("books") or {}):
        p = os.path.join(src, "%s.pdf.gz" % book)
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            body = fh.read()
        for k, v in _object_heads_of_book(tn.pdf_pages(body), tn).items():
            heads[k] |= v
        if verbose:
            print("    %s  %d sub-heads" % (book, len(heads)))
    # Sorted lists, never sets: parse/registry.py once returned a different entry count on
    # every run because it iterated a set, and that manufactured false change events.
    out = {k: sorted(v) for k, v in sorted(heads.items())}
    write_json(OBJECT_CACHE, {
        "date": date,
        "what": ("The object heads printed under each sub-head of the Tamil Nadu Demand "
                 "Books, rebuilt from archive/tamilnadu/%s by parse/classify_tamilnadu.py. "
                 "A cache and not a source: delete it and it is rebuilt. It exists because "
                 "data/tamilnadu/schemes.json deliberately does not carry object heads, "
                 "and they are the strongest signal this classifier has." % date),
        "heads": out,
    })
    return out


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written by reading the 4,767 distinct names in the
# corpus, before any of the numbers in the docstring were computed, so the weights
# are fitted and the word choices are not. Two exceptions are recorded honestly:
# BODY and ACCOUNTING were each pruned ONCE after the first measurement, because as
# first written they fired on 45% and 32% of the development half and separated
# nothing. The pruning rule was stated before it was applied and is the same for
# both: keep only words that name the BODY receiving the money or the ACCOUNTING
# operation being performed, and drop every word that can equally name the place a
# benefit is delivered (school, college, hospital, hostel, home, centre, mission)
# or a scheme's own funding label (share, capital, contribution).
# ---------------------------------------------------------------------------

# Object heads, the fifth field of a Tamil Nadu head of account, are the state saying what
# kind of spending this is. 3xx is the revenue section, 4xx capital, 5xx loans.
#
#   benefit transfers, money that leaves government and reaches a person:
#     311 Subsidies, 312 Scholarships and Stipends, 327 Pensions, 328 Gratuities,
#     339 Rewards, 343 Cost of Ration, 346 Clothing Tentage and Stores, 351 Compensation,
#     352 Gifts, 356 Feeding and Cash Doles, 367 Feeding and Dietary Charges, 368 Cost of
#     Books and Note Books, 370 Unemployment Relief.
TRANSFER_OBJ = {"311", "312", "327", "328", "339", "343", "346", "351", "352", "356",
                "367", "368", "370"}
#   309 Grants-in-Aid and 310 Contributions are transfers too and are deliberately NOT in
#   that set. See the docstring: 309 is the commonest object head in the books, it fires on
#   1,573 of 6,220 heads, and rows carrying only 309 are schemes 18.4% of the time against
#   a base rate of 16.0%. Tamil Nadu books a grant to a university and a maternity
#   assistance payment under the same code, so the code carries almost no information.
GRANT_OBJ = {"309", "310"}
#   running the office, buying the supplies, building the asset:
#     301 Salaries, 302 Wages, 303 Dearness Allowance, 304 Travel, 305 Office Expenses,
#     306 Rent Rates and Taxes, 307 Publications, 308 Advertising, 313 Hospitality,
#     314 Sumptuary Allowances, 315 Secret Service, 316 and 317 Minor Works,
#     318 Maintenance, 319 Machinery and Equipment, 320 Tools and Plant, 321 Motor
#     Vehicles, 324 Materials and Supplies, 333 Payments for Professional Services,
#     334 Other Charges, 342 Service or Commitment Charges, 344 Arms and Ammunition,
#     345 Petroleum Oil and Lubricants, 347 Stores and Equipments, 348 Foreign Allowances,
#     349 Festival Advances, 354 Expenses on Conducted Tours, 359 Prizes and Awards,
#     360 TA and DA to Non-Officials, 366 Medicine, 369 Procurement, 371 Printing,
#     372 Training, 373 Transport Charges, 374 Purchase and Upkeep, 375 Working Expenses,
#     376 Computer and Accessories, 381 Networking, 382 Specific Allowance, and the capital
#     section's 405 Office Expenses, 416 and 417 Major and Minor Works, 419 Machinery,
#     420 Tools and Plant, 421 Motor Vehicles, 433 Professional Services, 444 Arms,
#     464 Lands, 476 Computer.
#   359 Prizes and Awards is in this group and not in the transfer group, which looks wrong
#   until you count it: it fires on 649 heads and 91% of them also carry 301 Salaries. It is
#   the small standing line every establishment block prints, not a prize scheme.
RUNNING_OBJ = {"301", "302", "303", "304", "305", "306", "307", "308", "313", "314",
               "315", "316", "317", "318", "319", "320", "321", "324", "333", "334",
               "342", "344", "345", "347", "348", "349", "354", "359", "360", "366",
               "369", "371", "372", "373", "374", "375", "376", "381", "382",
               "405", "416", "417", "419", "420", "421", "433", "444", "464", "476"}
#   accounting and adjustment:
#     325 Interest, 329 Depreciation, 330 and 430 Inter-Account Transfers, 331 Writes off
#     and Losses, 332 Suspense, 335 Royalty, 336 International, 341 Other Discounts,
#     361 Refunds, 362 Notional Value of Gifts, 377 and 477 Deduct-Recoveries,
#     399 and 499 Miscellaneous, 422 Investments, 502 Outgo.
ACCOUNT_OBJ = {"325", "329", "330", "331", "332", "335", "336", "341", "361", "362",
               "377", "379", "399", "422", "430", "477", "499", "502"}

# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC ST and OBC, 2235 Social Security and Welfare, 2236 Nutrition,
# 2401 Crop Husbandry, 2501 Rural Development Programmes, 2505 Rural Employment.
# 2071, Pensions and Other Retirement Benefits, is deliberately absent and it is the single
# biggest cause of the errors that survive; see the docstring and known_errors.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2401", "2501", "2505"}

# Minor heads are standardised across Indian government accounts: 001 Direction and
# Administration, 003 Training, 004 Research, 005 Investigation, 051 Construction,
# 052 Machinery and Equipment, 053 Maintenance and Repairs, 090 Secretariat, 094 Other
# Establishments.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053", "090", "094"}
# 911 Deduct - Recoveries of Overpayments, 902 Deduct - Amount met from a fund. All 867
# rows in the corpus under 911 carry exactly one object head, 377, and all 867 are funded
# at nil. They are accounting mirrors carrying the scheme's own name.
RECOVERY_MINOR = {"911", "902"}
# 789 Special Component Plan for Scheduled Castes, 793 and 794 the tribal sub-plans, 796
# Tribal Area Sub-Plan. Tamil Nadu books scheme provisions here and establishment rarely.
SUBPLAN_MINOR = {"789", "793", "794", "796"}

# Words that name the BODY receiving the money. Pruned once; see the block comment above.
# "school", "college", "hospital", "hostel", "home" and "centre" are all deliberately out,
# because in Tamil Nadu they usually name where a benefit is delivered rather than who is
# paid: "Free Supply of Uniform to Students of Schools" is a scheme and "Government
# Royapettah Hospital" is not, and the object head separates those two on its own.
BODY = {
    "corporation", "corporations", "board", "boards", "authority", "directorate",
    "directorates", "commission", "commissionerate", "committee", "council", "academy",
    "agency", "agencies", "department", "departments", "office", "offices", "headquarters",
    "society", "societies", "federation", "trust", "laboratory", "laboratories", "museum",
    "library", "libraries", "secretariat", "tribunal", "court", "courts", "bureau",
    "university", "universities", "institute", "institutes", "company", "limited", "ltd",
    "undertaking", "undertakings", "mill", "mills", "factory", "press", "wing", "wings",
    "cell", "station", "stations", "depot", "workshop", "establishment", "establishments",
    "staff", "engineer", "engineers", "commissioner", "collector", "collectors",
    "inspectorate",
}

# Words that name an accounting or adjustment operation. Pruned once: "share", "capital"
# and "contribution" were in the first version and had to come out, because "- State Share"
# is printed on hundreds of genuine centrally sponsored scheme heads.
ACCOUNTING = {
    "deduct", "recoveries", "recovery", "overpayments", "percentage", "transferred",
    "suspense", "adjustment", "write", "writes", "refund", "refunds", "contingencies",
    "audit", "census", "survey", "investigation", "computerisation", "supervision",
    "inspection", "advance", "advances", "outgo", "ways", "means", "investment",
    "investments", "dues",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "constructions", "building", "buildings", "infrastructure", "road",
    "roads", "works", "work", "maintenance", "repair", "repairs", "renovation",
    "upgradation", "upgrading", "modernisation", "modernization", "equipment",
    "equipments", "machinery", "erection", "restoration", "assets", "electrification",
    "dam", "dams", "barrage", "reservoir", "reservoirs", "canal", "canals", "anicut",
    "bridge", "bridges", "desilting", "dredging", "quarters", "acquisition", "lands",
    "land", "premises", "complex", "campus", "strengthening", "improvement",
    "improvements", "formation", "widening", "laying", "installation",
}

# Words that name the thing a person receives.
BENEFIT = {
    "scholarship", "scholarships", "stipend", "stipends", "pension", "pensions",
    "incentive", "incentives", "assistance", "subsidy", "subsidies", "free", "insurance",
    "compensation", "kit", "kits", "nutrition", "nutritious", "nutritional",
    "reimbursement", "allowance", "relief", "meal", "meals", "gratia", "waiver", "doles",
    "dole", "feeding", "supply", "distribution", "grant", "grants", "thogai",
    "udhaviththogai", "marriage", "maternity", "welfare", "dhoties", "sarees", "uniform",
    "uniforms", "bicycles", "cycles", "laptop", "laptops", "books", "textbooks",
    "footwear", "sweaters", "spectacles", "ration", "rice", "eggs", "milk", "housing",
    "house", "houses", "treatment", "surgery", "aid", "aids",
}

# Words that name who receives it. A head that names its beneficiary class is describing a
# transfer; a head that names none is usually describing an office or an asset.
BENEFICIARY = {
    "students", "student", "women", "woman", "girls", "girl", "farmers", "farmer",
    "weavers", "weaver", "fishermen", "fisherwomen", "beneficiaries", "beneficiary",
    "victims", "victim", "workers", "worker", "families", "family", "children", "child",
    "persons", "person", "youth", "widow", "widows", "widowers", "disabled", "abled",
    "citizens", "households", "household", "artisans", "entrepreneurs", "graduates",
    "mothers", "adolescent", "destitute", "orphan", "orphans", "poor", "aged", "senior",
    "tribal", "tribals", "scheduled", "backward", "minority", "minorities", "transgender",
    "transgenders", "labourers", "labour", "pensioners", "boys", "differently",
    "denotified", "dnc", "mbc", "obc", "landless", "unemployed", "patients",
}

# Scheme-name morphology. Weak on its own and weighted accordingly: "Green Mission" is an
# afforestation head and "Mission Vatsalya" is a child protection service, so the word
# Mission in a Tamil Nadu name proves nothing either.
MARKER = {"yojana", "yojna", "abhiyan", "mission", "scheme", "schemes", "thittam",
          "karyakram", "programme", "nidhi", "urimai", "penn", "kalvi", "payanam",
          "vandanam"}

# The name begins with an accounting operation. "Add - Percentage Charges for Establishment
# transferred from the Major Head 2059 Public Works" is 92 rows of pure adjustment.
ADD_DEDUCT = re.compile(r"^\s*(deduct|add)\b", re.I)
# "Buildings - Medical and Rural Health Services (Administered by Chief Engineer)". 73 rows.
BUILDINGS_DASH = re.compile(r"^\s*buildings?\s*[-–]", re.I)
# parse/tamilnadu.py's own establishment pattern, widened by the officer titles Tamil Nadu
# files provisions under: a head called "Electrical Engineers" or "Chief Engineer -
# Projects" is a salary block.
ESTAB_LEAD = re.compile(
    r"^\s*(directorate|director\s|director-|director of|headquarters|district staff|"
    r"secretariat|establishment|office of|commissionerate|regional office|head office|"
    r"executive establishment|pay of|staff for|chief engineer|superintending engineer|"
    r"executive engineer|assistant engineer|electrical engineer|district establishment)",
    re.I)
# "Government Medical College Hospital, Ariyalur", "Central Press, Chennai". Karnataka's
# rule, and unlike Andhra Pradesh, where it never fired, it does fire here.
PLACE_TAIL = re.compile(r",\s*[A-Z][a-z]+(\s*(district|taluk))?\s*$")


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


# The weights. Negative weights are larger than positive ones on purpose. A row that looks
# like an establishment and also carries benefit words, "Staff for implementing
# Puratchithalaivar MGR Nutritious Meal Programme", should have to work to clear the bar,
# because that is the row that would embarrass the published list.
WEIGHTS = {
    "recovery": -6, "acct_obj": -6, "add_deduct": -4, "capital": -4, "running": -3,
    "estab_lead": -4, "acc_word": -3, "works": -3, "buildings": -3, "body": -2,
    "place": -2, "estab_minor": -1,
    "all_benefit_obj": 5, "some_benefit_obj": 2, "welfare": 2, "subplan": 1, "code": 1,
    "who": 3, "ben": 2, "marker": 1,
}


def score_entry(name, hoa, obj):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic."""
    tk = tokens(name)
    f = (hoa or "").split()
    major = f[0] if f else ""
    minor = f[2] if len(f) > 2 else ""
    code = f[3] if len(f) > 3 else ""
    obj = set(obj or ())
    ev = []
    total = 0

    def add(key, why):
        nonlocal total
        total += WEIGHTS[key]
        ev.append(["%+d" % WEIGHTS[key], why])

    # Structure first: what the state's own accounting classification says this is.
    if minor in RECOVERY_MINOR:
        add("recovery", "recovery or adjustment minor head " + minor)
    if obj and obj <= ACCOUNT_OBJ:
        add("acct_obj", "every object head on this row is an accounting head: "
            + ", ".join(sorted(obj)))
    if ADD_DEDUCT.match(name or ""):
        add("add_deduct", "the name begins Add or Deduct")
    if major[:1] in "4567":
        add("capital", "capital outlay or loan major head " + major)
    run = sorted(obj & RUNNING_OBJ)
    if run:
        add("running", "running cost or works object head " + ", ".join(run[:4]))

    # What the name says it is.
    if ESTAB_LEAD.match(name or ""):
        add("estab_lead", "the name begins with an establishment word")
    acct = sorted(tk & ACCOUNTING)
    if acct:
        add("acc_word", "accounting word in the name: " + ", ".join(acct[:3]))
    works = sorted(tk & WORKS)
    if works:
        add("works", "asset or works word in the name: " + ", ".join(works[:3]))
    if BUILDINGS_DASH.match(name or ""):
        add("buildings", "the name is a Buildings head")
    body = sorted(tk & BODY)
    if body:
        add("body", "the name names a body: " + ", ".join(body[:3]))
    if PLACE_TAIL.search(name or ""):
        add("place", "the name ends in a place, which is how an institution is named")
    if minor in ESTAB_MINOR:
        add("estab_minor", "establishment or works minor head " + minor)

    # Positive structure. The two clauses are exclusive: a row where every object head is a
    # benefit head is not also charged the weaker partial credit.
    if obj and obj <= TRANSFER_OBJ:
        add("all_benefit_obj", "every object head on this row is a benefit transfer head: "
            + ", ".join(sorted(obj)))
    elif obj & TRANSFER_OBJ:
        add("some_benefit_obj", "a benefit transfer object head: "
            + ", ".join(sorted(obj & TRANSFER_OBJ)[:3]))
    if major in WELFARE_MAJOR:
        add("welfare", "welfare function major head " + major)
    if minor in SUBPLAN_MINOR:
        add("subplan", "sub-plan minor head " + minor)
    if code[:1] in "JUVW":
        add("code", "sub-head code " + code + ", one of the scheme blocks")

    # Positive name evidence.
    who = sorted(tk & BENEFICIARY)
    if who:
        add("who", "named beneficiary class in the name: " + ", ".join(who[:3]))
    ben = sorted(tk & BENEFIT)
    if ben:
        add("ben", "benefit word in the name: " + ", ".join(ben[:3]))
    mark = sorted(tk & MARKER)
    if mark:
        add("marker", "scheme marker word in the name: " + ", ".join(mark[:2]))

    return total, ev


SIGNALS = [
    {"points": -6, "signal": "recovery or adjustment minor head, 911 and 902",
     "measured": ("P(scheme) 0.000 over 32 development rows, base rate 0.160. Not a weak "
                  "signal but an exact one: all 867 rows in the corpus under minor head 911 "
                  "carry exactly one object head, 377 Deduct-Recoveries, and all 867 are "
                  "funded at nil. 731 of the 867 do not begin with the word Deduct, "
                  "because the recovery head repeats the scheme's own name. 42 further "
                  "rows sit under minor head 902, Deduct - Amount met from a fund.")},
    {"points": -6, "signal": "every object head on the row is an accounting head",
     "measured": "P(scheme) 0.000 over 51 development rows"},
    {"points": -4, "signal": "the name begins Add or Deduct",
     "measured": "P(scheme) 0.000 over 10 development rows"},
    {"points": -4, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": ("P(scheme) 0.000 over 38 development rows. 1,118 of the 6,220 heads are "
                  "capital or loan heads, and in Tamil Nadu they really are works, share "
                  "capital and advances rather than schemes booked on the capital side.")},
    {"points": -4, "signal": "the name begins with an establishment word",
     "measured": "P(scheme) 0.000 over 15 development rows"},
    {"points": -3, "signal": "a running cost or works object head",
     "measured": ("P(scheme) 0.047 over 86 development rows. This is the object head doing "
                  "the work a purpose line would do: the state saying the money is a "
                  "salary, a vehicle, a major work or an office expense.")},
    {"points": -3, "signal": "an accounting word in the name",
     "measured": "P(scheme) 0.000 over 17 development rows"},
    {"points": -3, "signal": "an asset or works word in the name",
     "measured": "P(scheme) 0.024 over 42 development rows"},
    {"points": -3, "signal": "the name is a Buildings head",
     "measured": "P(scheme) 0.000 over 4 development rows, 73 rows in the corpus"},
    {"points": -2, "signal": "the name names a body",
     "measured": ("P(scheme) 0.056 over 72 development rows. As first written this "
                  "vocabulary also held school, college, hospital, hostel, home, centre and "
                  "mission, fired on 90 of 200 rows and measured 0.144 against a base of "
                  "0.160, which is nothing. Those words name where a benefit is delivered "
                  "in Tamil Nadu, not who is paid.")},
    {"points": -2, "signal": "the name ends in a place",
     "measured": ("P(scheme) 0.000 over 5 development rows. Karnataka's rule, dead in "
                  "Andhra Pradesh, alive here: Tamil Nadu appends the district to an "
                  "institution's name.")},
    {"points": -1, "signal": "establishment or works minor head, 001 003 004 005 051 052 "
                             "053 090 094",
     "measured": "P(scheme) 0.077 over 26 development rows"},
    {"points": 5, "signal": "every object head on the row is a benefit transfer head",
     "measured": ("P(scheme) 0.895 over 19 development rows, the strongest signal in the "
                  "file and the substitute for the purpose line Tamil Nadu does not print. "
                  "Rows whose only object head is 311 Subsidies are schemes 90% of the "
                  "time and rows whose only object head is 312 Scholarships and Stipends "
                  "100% of the time.")},
    {"points": 3, "signal": "a named beneficiary class in the name",
     "measured": "P(scheme) 0.500 over 38 development rows"},
    {"points": 2, "signal": "some but not all object heads are benefit transfer heads",
     "measured": (
         "P(scheme) 0.138 over the 29 development rows in this case exactly, against a base "
         "rate of 0.160. On its own margin the signal is worth nothing, and this is the one "
         "weight in the table the marginal measurement does not support. It is kept, and "
         "the reason is measured at the publishing bar rather than argued: setting it to 0 "
         "instead takes the published list from 326 heads to 303 with the same twelve "
         "counted errors, so all 23 rows it adds are genuine schemes, and recall falls from "
         "41.0% to 36.1% for 0.3 points of precision. The signal is weak alone and useful "
         "in combination, because a row carrying both a running cost head and a benefit "
         "head has already paid -3 for the first. The 0.438 figure over the 48 rows "
         "carrying ANY benefit transfer object head is the one that reads well, and it is "
         "the wrong cut: it is the 19 all-benefit rows at 0.895 dragging the average up.")},
    {"points": 2, "signal": "welfare function major head, 2216 2225 2235 2236 2401 2501 2505",
     "measured": "P(scheme) 0.391 over 46 development rows, lift +0.231"},
    {"points": 2, "signal": "a benefit word in the name",
     "measured": ("P(scheme) 0.339 over 56 development rows. Weaker than in Karnataka and "
                  "Andhra Pradesh because Tamil Nadu's establishment heads are wordy: "
                  "Assistance, Grant, Supply and Welfare all appear in names that buy an "
                  "institution.")},
    {"points": 1, "signal": "sub-plan minor head, 789 793 794 796",
     "measured": "P(scheme) 0.526 over 19 development rows, the highest P of any signal "
                 "here after the object head, on too few rows to weight more heavily"},
    {"points": 1, "signal": "sub-head code in the J, U, V or W blocks",
     "measured": ("P(scheme) 0.377 over 53 development rows against 0.076 for the 105 rows "
                  "in the A block. Tamil Nadu allots sub-head codes in blocks as provisions "
                  "are created, so this is really 'a recently created head' and it is "
                  "morphology rather than meaning. One point and no more.")},
    {"points": 1, "signal": "a scheme marker word in the name",
     "measured": "P(scheme) 0.286 over 42 development rows, the weakest positive"},
]

REJECTED_SIGNALS = [
    {"signal": "every object head on the row is a transfer head, counting 309 Grants-in-Aid "
               "and 310 Contributions as transfers",
     "measured": ("P(scheme) 0.421 over 57 development rows, against 0.895 for the 19 rows "
                  "where every head is a BENEFIT transfer head. Rows whose only object head "
                  "is 309 measure 0.184 against a base rate of 0.160."),
     "why": ("This is the rule that carried Andhra Pradesh and it does not carry Tamil "
             "Nadu. 309 Grants-in-Aid fires on 1,573 of the 6,220 heads and is the "
             "commonest object head in the books; the state uses it for a grant to a "
             "university, a cash deficit grant to the water board, devolution to a "
             "municipal corporation and the Muthulakshmi Reddy maternity assistance alike. "
             "Including it would have added about 500 rows to the published list at roughly "
             "the base rate, which is another way of saying it would have added noise.")},
    {"signal": "the head is funded at nil",
     "measured": ("P(scheme) 0.038 over 53 development rows, but 0.095 once the recovery "
                  "heads are taken out and 0.286 on the 7 rows that survive the running "
                  "cost, recovery and accounting filters."),
     "why": ("1,588 heads are funded at nil and the state means something by that: the head "
             "exists and carries no provision this year. It is not evidence that the head "
             "is not a scheme. The apparent signal is almost entirely the 867 recovery "
             "heads under minor head 911, every one of which is nil, and those are already "
             "scored by their minor head. Scoring nil as well would double count them and "
             "would penalise a real scheme the state has parked, which is exactly the fact "
             "a register of hidden schemes should surface rather than hide.")},
    {"signal": "the name matches a myScheme record tagged Tamil Nadu",
     "measured": ("parse/tamilnadu.py already measured this and recorded the result in "
                  "myscheme_join_defects: 201 joins produced, 118 wrong on inspection. Of "
                  "234 Tamil Nadu myScheme records only 32 have a sound join at all."),
     "why": ("This is the borrowed ground truth the hand labels replace, and here it is "
             "both bad and circular. Bad, because the matcher joins 'Buildings - Animal "
             "Husbandry' to a livestock subsidy on two shared content words, 63 times. "
             "Circular, because the question the register asks is which budget rows are "
             "ABSENT from myScheme, so scoring a row higher for being present on myScheme "
             "would systematically push down exactly the rows the answer is made of. Read "
             "myscheme_join_defects as evidence about the matcher, not about schemes.")},
    {"signal": "the department family the book belongs to",
     "measured": ("On all 399 stratified rows: WELFARE 0.310 over 58 rows, ECONOMY 0.194 "
                  "over 98, SERVICE 0.137 over 73, GOVERNANCE 0.122 over 90, INFRA 0.037 "
                  "over 80, against a base rate of 0.153."),
     "why": ("Real, an eightfold spread, and deliberately unused. It would score the book "
             "rather than the provision, and it would guarantee that a welfare scheme run "
             "by an infrastructure department could never clear the bar. It is also the "
             "stratification axis, so scoring it would make the sample and the classifier "
             "agree with each other rather than with the books.")},
    {"signal": "the size of the allocation",
     "measured": ("The four allocation quartiles run 0.361, 0.130, 0.074 and 0.237 on the "
                  "development half against a base of 0.160, and the nil band runs 0.038."),
     "why": ("Non-monotone, which is another way of saying it is noise: the smallest "
             "quartile is the highest and the third is the lowest. A scheme is not larger "
             "or smaller than an establishment head in Tamil Nadu. The district police "
             "establishment is Rs 5,668 crore and the inter caste marriage assistance "
             "scheme is Rs 30 crore, while the free bus travel reimbursement for women is "
             "Rs 2,439 crore and a directorate can be Rs 40 lakh.")},
]

KNOWN_ERRORS = [
    {"name": "Relief to All-India Service pensioners [2071 01 101 AH], Relief to All-India "
             "Service Family Pensioners [2071 01 105 AD], Payment of Family Pension to "
             "ex-Village Officers [2071 01 105 AG], Ex-gratia payment to families of "
             "deceased Non-Provincialised Employees [2071 01 200 AB and 2071 01 800 AH], "
             "Reimbursement of Medical expenses to pensioners and Family Pensioners "
             "[2071 01 200 AI and 2071 01 800 AN]",
     "score": 10,
     "kind": "false positive, published at threshold 10, seven rows",
     "why": ("The single failure mode that produces most of the surviving errors, and it is "
             "structural rather than a slip. Every one of these is cash paid to an "
             "identifiable household, booked under object head 327 Pensions, with a "
             "beneficiary class in its name. Nothing in the head of account tells them "
             "apart from the Indira Gandhi National Old Age Pension, which is a scheme, "
             "except the major head: 2235 Social Security and Welfare is a welfare function "
             "and 2071 Pensions and Other Retirement Benefits is the state discharging its "
             "obligation to its own retired staff. Adding 2071 to a penalty list would fix "
             "all seven and would be principled. It is not done, because the fix was found "
             "by reading the audit and refitting on the audit would destroy the one "
             "measurement in this file that counts errors rather than estimating them. "
             "Fixing it would take counted precision at threshold 10 from 96.3% to 98.4%, on 319 heads instead of 326.")},
    {"name": "Livelihood Special Pension to Retired Noon Meal Workers [2235 60 102 AQ], "
             "Special Pension for Livelihood Support to Retired ICDS Workers "
             "[2235 60 102 AP], Financial Assistance to Anganwadi employees family pensions "
             "[2235 60 102 BM]",
     "score": "12 to 13",
     "kind": "false positive, published at threshold 10, three rows",
     "why": ("The same failure mode wearing the right major head. Anganwadi workers, noon "
             "meal workers and child development workers are the state's own scheme staff, "
             "paid an honorarium rather than a salary, and Tamil Nadu books their pensions "
             "under 2235 Social Security and Welfare alongside the destitute widow pension. "
             "These are the highest scoring errors in the published list, at 13 and 12, "
             "which is worth saying plainly: score is not confidence. A reader who thinks a "
             "pension to a retired anganwadi worker IS a welfare scheme should flip these "
             "three labels in data/tamilnadu/labels.json and rerun, and counted precision "
             "would read 97.2%.")},
    {"name": "Assistance to Co-operative Institution in Tribal areas [2425 00 796 JA] and "
             "Assistance to Co-operative Institution in Tribal Area - (LAMPS) "
             "[2425 00 796 JB]",
     "score": 12,
     "kind": "false positive, published at threshold 10",
     "why": ("Money for a body, scoring 12 because it sits on a tribal sub-plan minor head "
             "in the J block with the words Assistance and Tribal in its name and object "
             "head 311 Subsidies beneath it. The word Institution is not in the BODY "
             "vocabulary, deliberately, because it was pruned along with school and "
             "hospital. This is the cost of that pruning and it is two rows.")},
    {"name": "New Programme for feeding to poor children in the age group of 10 to 15 in "
             "Denotified Community Schools [2236 02 102 JT]",
     "score": 8,
     "kind": "false positive, excluded at threshold 10",
     "why": ("The clearest illustration of why the object head matters and of why the "
             "corpus needs both. This row's object heads are 301 Salaries, 303 Dearness "
             "Allowance and 305 Office Expenses: it is the STAFF of the feeding programme, "
             "not the feeding. Its name is indistinguishable from the eight sibling rows "
             "that are the feeding and that score 11 to 15. Only the chart of accounts "
             "separates them, and it does.")},
    {"name": "The band at exactly 8: Investors Incentive Scheme, Agent's Incentive Scheme, "
             "Medical Allowances to Pensioners, Death-cum-Retirement Gratuities, Capital "
             "Subsidy for Mega Industries, Effluent Treatment Plant Subsidy, National "
             "Mission on Natural Farming, Integrated Watershed Management Programme, and 25 "
             "others",
     "score": 8,
     "kind": "false positive, excluded at threshold 10, and the reason the bar is where it is",
     "why": ("The band at exactly 8 is 86 rows of which 33 are not schemes, a marginal "
             "precision of 61.6%, against 84.0% for the band at 9, 91.6% for the band at 10 "
             "and 100% for the band at 11. It is a mixture of three things: the state "
             "paying its own retired staff, subsidies paid to firms rather than people, and "
             "central missions booked as 309 Grants-in-Aid where the money stops at the "
             "implementing agency.")},
    {"name": "Magalir Urimai Thogai [2235 02 103 CD], the general head, at Rs 9,803 crore",
     "score": 4,
     "kind": "false negative, and the largest single miss in the corpus",
     "why": ("The state's flagship cash transfer, Rs 1,000 a month to a woman head of "
             "household, is voted under three heads totalling Rs 14,414 crore. The two "
             "sub-plan heads, at Rs 4,323 crore and Rs 288 crore, carry object head 311 "
             "Subsidies alone, score 11 and 12 and are published. The general head, which "
             "is Rs 9,803 crore or 68% of the scheme, carries 308 Advertising and "
             "Publicity beside 311, takes the running cost penalty of -3 and scores 4. The "
             "penalty is exactly the margin. Two thirds of the largest welfare scheme in "
             "the Tamil Nadu budget is excluded because the state books its publicity under "
             "the same sub-head, and the published be_lakh for that scheme is therefore a "
             "third of the truth. The Chief Minister's Breakfast Scheme fails the same way: "
             "its general head at Rs 483 crore carries 333 Payments for Professional "
             "Services beside 309 and scores 3.")},
    {"name": "Free Supply of Bicycles to students, ten heads across four communities "
             "[2225 01 277 KJ, 2225 03 277 KR and others], Rs 255 crore",
     "score": "6 and 7",
     "kind": "false negative, and it is object head 309 costing recall",
     "why": ("An unambiguous in-kind benefit to a named beneficiary class. Every one of "
             "the ten heads is booked under 309 Grants-in-Aid alone, so no benefit transfer "
             "object head fires and the row is left with a welfare major head, a "
             "beneficiary class and a benefit word: 7 points, three short. That is the "
             "price of excluding 309 from TRANSFER_OBJ, and it is the right price, because "
             "including it would have added about 500 rows at the base rate. 'Supply of "
             "bags and other learning materials to students' fails differently and worse, "
             "at 6, because it carries 324 Materials and Supplies, which is where an "
             "in-kind benefit is actually bought. Charging a row for the accounting of the "
             "transfer it makes is the same defect parse/classify_andhra.py recorded "
             "against its own supplies group.")},
    {"name": "Illam Thedi Kalvi [2202 01 101 DD] at score 1, Grants to Naan Mudhalvan "
             "Scheme [2230 03 800 AJ] at score 3, Kalaignarin Kanavu Illam "
             "[2216 03 789 JG] at score 7",
     "score": "1 to 7",
     "kind": "false negative, the recall cost, and it is the state's own brands",
     "why": ("A Tamil scheme name says nothing to a vocabulary of English benefit words, "
             "and object head 309 rescues nothing because Tamil Nadu uses it for "
             "everything. Recall at the published bar is 41.0% on the stratified sample, "
             "so the published count is a floor on Tamil Nadu's schemes and never a total. "
             "The state could raise it tomorrow by printing one sentence per sub-head "
             "saying what the money is for, which is what Karnataka does.")},
]

# parse/tamilnadu.py already read every myScheme join this corpus produces, by eye, and
# recorded what it found in myscheme_join_defects: 201 joins, 118 wrong. Those findings are
# reproduced in the output rather than restated here, because they are evidence about
# parse/match.py and belong with the parser that measured them.


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

# Five department families, a fixed partition of the 55 demand books. The books cannot each
# be a stratum: 55 books crossed with 5 allocation bands is 275 cells, and a sample large
# enough to fill them could not be labelled by hand. The partition is by what the
# department does, written before the labels were made, and the five families come out at
# 898 to 1,537 rows each, which is close enough to even that no stratum dominates.
FAMILIES = [
    ("WELFARE", ["SOCIAL JUSTICE", "SOCIAL WELFARE AND WOMEN", "BACKWARD CLASSES",
                 "DIFFERENTLY ABLED", "LABOUR WELFARE", "YOUTH WELFARE"]),
    ("SERVICE", ["HEALTH AND FAMILY", "SCHOOL EDUCATION", "HIGHER EDUCATION",
                 "FOOD AND CONSUMER", "TAMIL DEVELOPMENT", "HINDU RELIGIOUS"]),
    ("ECONOMY", ["AGRICULTURE", "ANIMAL HUSBANDRY", "FISHERIES", "DAIRY",
                 "RURAL DEVELOPMENT", "CO-OPERATION", "HANDLOOMS", "KHADI", "MICRO, SMALL",
                 "INDUSTRIES", "FORESTS", "ENVIRONMENT AND CLIMATE", "NATURAL RESOURCES"]),
    ("INFRA", ["WATER RESOURCES", "HIGHWAYS", "BUILDINGS", "MUNICIPAL ADMINISTRATION",
               "HOUSING AND URBAN", "ENERGY", "TRANSPORT", "INFORMATION TECHNOLOGY",
               "TOURISM"]),
]


def family(dept):
    u = (dept or "").upper()
    for name, prefixes in FAMILIES:
        if any(u.startswith(p) for p in prefixes):
            return name
    return "GOVERNANCE"


def stratify(entries, target=400):
    """Deterministic stratified sample: department family crossed with allocation band.

    No random seed anywhere. Rows inside a stratum are sorted by head of account and picked
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
        rows = sorted(cells[k], key=lambda x: x["hoa"])
        # Proportional allocation with a floor of 6, so the sample is close to self
        # weighting and every stratum still gets enough rows to say anything about.
        n = min(len(rows), max(6, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda t: t[0]["hoa"])


def myscheme_tamilnadu():
    """Scheme names myScheme lists for Tamil Nadu. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("tamil" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    6,220 heads against 234 records is 1.46 million calls to probably_same, and each one
    re-tokenises, re-skeletonises and re-derives the acronyms of both names from scratch.
    Naively that is four minutes of a run that otherwise takes forty seconds. This is the
    same indexed join parse/tamilnadu.py describes doing, and it is an EXACT superset
    rather than a speed-for-accuracy trade: every branch in probably_same that can return
    True requires the pair to share a content token, share a transliteration skeleton, or
    stand in an acronym relation, so a pair that shares none of the three cannot match.

      similarity >= 0.75      similarity is min(ratio, (overlap + ratio) / 2) and ratio
                              cannot exceed 1, so an overlap of zero caps it at 0.5.
      content word containment  the smaller token set is non-empty and inside the larger.
      one name begins with the other  the shorter name's content words are all in the longer.
      transliteration variant   the smaller skeleton set is inside the larger.
      acronym match             an acronym of one is a token or an acronym of the other.
      acronym containment       one acronym is a substring of the other.

    The one branch this does not index exactly is the prefix rule for a name made entirely
    of stop words, which cannot occur in a scheme name.
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
    tn = json.load(open(os.path.join(ROOT, "data", "tamilnadu", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(tn["entries"], key=lambda x: x["hoa"])
    obj = object_heads(verbose=verbose)

    labels = json.load(open(os.path.join(ROOT, "data", "tamilnadu", "labels.json"),
                            encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_tamilnadu()
    idx = myscheme_index(listed)

    rows = []
    for r in entries:
        heads = obj.get(r["hoa"], [])
        total, ev = score_entry(r["name"], r["hoa"], heads)
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in myscheme_candidates(r["name"], idx)
               if probably_same(r["name"], n)[0]]
        rows.append({
            "key": r["hoa"],
            "hoa": r["hoa"],
            "name": r["name"],
            "department": r["department"],
            "major_head": r["major_head"],
            "code": r["code"],
            "be_lakh": r.get("be_lakh"),
            "object_heads": heads,
            "books": sorted(r.get("books") or []),
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_tamilnadu": bool(hit),
            "myscheme_match": sorted(hit) or None,
            "hand_label": by_key[r["hoa"]]["label"] if r["hoa"] in by_key else None,
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

    full_sweep = sweep(scored, max(lo, -10), hi)
    held_sweep = sweep(held, max(lo, -10), hi)
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
            "the_errors": sorted("%s [%s]" % (x["name"], x["hoa"]) for x in bad),
        })
    at_census = next(x for x in census if x["threshold"] == threshold)

    schemes = [x for x in rows if x["verdict"] == "scheme"]
    absent_all = [x for x in rows if not x["in_myscheme_tamilnadu"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_tamilnadu"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per NAME as well as per head of account, because the same scheme is voted
    # under several heads: the general head, the Special Component Plan head, the Tribal
    # Sub-Plan head, the state share and the central share. Publishing the heads would
    # print Post-Matric Scholarship six times down a page and read as six findings.
    # The allocations add, because these are separate provisions out of separate
    # sub-plans and not overlapping cuts of one figure. The score is the best any head
    # achieved, because the evidence for a scheme being a scheme does not weaken by being
    # voted twice.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"])
        if e is None:
            e = by_name[x["name"]] = {"name": x["name"], "departments": [], "heads": [],
                                      "be_lakh": 0.0, "score": x["score"],
                                      "evidence": x["evidence"]}
        if x["department"] not in e["departments"]:
            e["departments"].append(x["department"])
        e["heads"].append(x["hoa"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["departments"] = sorted(r["departments"])
        r["heads"] = sorted(r["heads"])
        r["be_lakh"] = round(r["be_lakh"], 2)

    out = {
        "built": utcnow(),
        "snapshot": tn.get("snapshot"),
        "state": "Tamil Nadu",
        "cycle": tn.get("cycle"),
        "variant": tn.get("variant"),
        "source": "data/tamilnadu/schemes.json, plus the object heads rebuilt from "
                  "archive/tamilnadu/ and cached at " + OBJECT_CACHE,
        "question": ("Which of Tamil Nadu's 6,220 Demand Book sub-heads are welfare "
                     "schemes, and which are establishment heads, works heads, "
                     "institutions, employment obligations or accounting heads?"),
        "entries": len(rows),
        # Lower-cased, so this is the same 4,767 that parse/tamilnadu.py publishes in
        # its counts block. 53 names differ only in capitalisation.
        "distinct_names": len({x["name"].lower() for x in rows}),
        "counting_basis": (
            "EVERY COUNT HERE IS ON THE 6,220 HEAD OF ACCOUNT BASIS unless the field name "
            "says distinct. The head of account is Tamil Nadu's own identifier for a "
            "provision and it is what the state votes: a scheme's revenue head and its "
            "capital head are separate provisions, its Special Component Plan and Tribal "
            "Sub-Plan heads are separate provisions, and its recovery mirror under minor "
            "head 911 carries the same name as the scheme it mirrors. The 6,220 heads "
            "carry 4,767 distinct names. Collapsing on the name would merge a provision "
            "with its own recovery head, so the head of account is the published basis and "
            "absent_distinct is the de-duplicated view of the same list."),
        "publish_threshold": threshold,
        # The F1 optimum, the bar for the WEAKER claim: "this state's budget names
        # this as a scheme". It lived only in site/build.py, so the data could not
        # say which rows the site lists and anything else reading this file had to
        # guess. parse/cag_join.py guessed by skipping this state entirely.
        "listing_threshold": 5,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"].lower() for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "funded_at_nil": sum(1 for x in rows if not x.get("be_lakh")),
        "funded_at_nil_and_classified_scheme": sum(
            1 for x in schemes if not x.get("be_lakh")),
        "recovery_heads": sum(1 for x in rows if x["hoa"].split()[2] in RECOVERY_MINOR),
        "object_head_coverage": sum(1 for x in rows if x["object_heads"]),
        "ground_truth": {
            "file": "data/tamilnadu/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "sets": labels["sets"],
            "why_not_myscheme": (
                "myScheme membership cannot be the ground truth here, and it was not a "
                "close call. parse/tamilnadu.py produced 201 joins between these 6,220 "
                "heads and the 234 Tamil Nadu myScheme records and read every one by eye: "
                "118 are wrong. 63 of them come from a single defect, containment on two "
                "generic content words, which joined a livestock subsidy to every head of "
                "the Animal Husbandry department including its recovery and buildings "
                "heads. The defects are reproduced in myscheme_join_defects below. They "
                "are evidence about the matcher, not ground truth about schemes. Worse, "
                "the signal is circular: the question is which rows are absent from "
                "myScheme, so scoring presence would push down exactly the rows the answer "
                "is made of."),
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
            "base_rate_note": (
                "About one Tamil Nadu Demand Book sub-head in six is a welfare scheme, "
                "against 41% of Andhra Pradesh's scheme-wise rows and 55% of Karnataka's. "
                "That is not a fact about Tamil Nadu's schemes, it is a fact about the "
                "document: these are the full detailed estimates and the other two states' "
                "books are scheme-wise annexures."),
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
                "thresholds is counted rather than estimated. The census starts at %d and "
                "not lower because of the scale: 6,220 rows put 972 rows above score 5 and "
                "640 above 7, and 462 is the largest set that can be read one by one and "
                "labelled reliably. Recall still comes from the stratified sample, because "
                "the rows the classifier rejects are too many to label exhaustively."
                % (CENSUS_FROM, CENSUS_FROM)),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": (
                "F1 peaks at threshold 5, where the sample says precision is 83.3% and one "
                "published name in six is not a scheme. Naming a scheme as hidden by a "
                "government is an accusation, so this runs at the high-precision end and "
                "accepts the recall loss. The break in the census is between 9 and 10, and "
                "it is visible in the bands rather than the cumulative column: the band at "
                "exactly 8 is 61.6% precise, the band at 9 is 84.0%, the band at 10 is "
                "91.6% and the band at 11 is 100%. Note that cumulative precision is not "
                "monotone, falling from 97.9% at threshold 11 to 97.1% at 12, because "
                "raising the bar past 11 discards a band with no errors in it."),
            "sample_versus_census": (
                "The stratified sample alone would have claimed 100% precision at threshold "
                "10, on the strength of 25 rows above the bar. The census counts 96.3%. It "
                "erred flatteringly here, as Karnataka's did, and pessimistically in Andhra "
                "Pradesh, which is the same lesson either way: a probability sample is the "
                "right tool for recall, which cannot be censused, and the wrong one for "
                "counting mistakes in a list short enough to read."),
            "what_the_missing_purpose_line_costs": (
                "Karnataka's books print a purpose line and it was that classifier's "
                "strongest signal at P(scheme) 0.947. Tamil Nadu prints none on any of the "
                "6,220 sub-heads. What it prints instead is the object head, and that is "
                "worth a great deal: P(scheme) 0.895 where every object head under a "
                "sub-head is a benefit transfer head. Recall at the published bar is 41.0% "
                "on the stratified sample and 44.8% on the held-out half, better than "
                "Karnataka's 31.6% and Andhra Pradesh's 36.5% at their own bars. It still "
                "loses every scheme the state books as 309 Grants-in-Aid, which is the "
                "commonest object head in the books."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_tamilnadu_records": len(listed),
        "myscheme_record_count_note": (
            "This is counted live off data/myscheme/schemes/, every record whose "
            "beneficiaryState list mentions Tamil Nadu. parse/tamilnadu.py's "
            "myscheme_join_summary below says 234 and that figure is hard coded there from "
            "an earlier count of the same directory. The two are reported side by side "
            "rather than reconciled, because a silently moving denominator is exactly the "
            "kind of thing a register should show rather than smooth over."),
        "myscheme_join_defects": tn.get("myscheme_join_defects"),
        "myscheme_join_summary": tn.get("myscheme_join_summary"),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_distinct_names": len({x["name"].lower() for x in absent}),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": (
            "Absence is decided by parse/match.py's generous matcher against the myScheme "
            "records tagged Tamil Nadu, because claiming absence should require that even a "
            "generous matcher finds nothing. Read that number against "
            "myscheme_join_summary: the matcher produced 201 joins over the whole corpus "
            "and 118 of them are wrong, so a row counted present may not be, and the "
            "absent count here is if anything an understatement. The surviving list is a "
            "floor for the opposite reason too: no book prints a purpose line, recall at "
            "the published bar is 41%, and a real scheme booked as a plain grant-in-aid "
            "with a Tamil name cannot clear a high bar on the evidence the books print."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/tamilnadu/classification.json", out)
    return out


def check_sample():
    """Report which sampled or census rows have no hand label yet."""
    tn = json.load(open(os.path.join(ROOT, "data", "tamilnadu", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "tamilnadu", "labels.json"),
                            encoding="utf-8"))
    obj = object_heads()
    have = {x["key"] for x in labels["labels"]}
    entries = sorted(tn["entries"], key=lambda x: x["hoa"])
    frame = stratify(entries)
    missing = [(r["hoa"], st, r["name"]) for r, st, _, _ in frame if r["hoa"] not in have]
    print("sampling frame %d rows, labelled %d, unlabelled %d"
          % (len(frame), len(have), len(missing)))
    for k, st, name in missing:
        print("  [%s]  %s  %s" % (st, k, name[:80]))
    # The census half of the contract: nothing at or above CENSUS_FROM may be unlabelled.
    uncovered = [r["hoa"] for r in entries
                 if score_entry(r["name"], r["hoa"], obj.get(r["hoa"], []))[0] >= CENSUS_FROM
                 and r["hoa"] not in have]
    print("census at score >= %d: %d rows unlabelled" % (CENSUS_FROM, len(uncovered)))
    for k in uncovered:
        print("  %s" % k)
    return missing, uncovered


def main():
    a = argparse.ArgumentParser(
        description="Classify Tamil Nadu Demand Book sub-heads as welfare scheme or "
                    "budget head.")
    a.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    a.add_argument("--check-sample", action="store_true",
                   help="list sampled or census rows that carry no hand label yet")
    a.add_argument("--rebuild-object-heads", action="store_true",
                   help="drop the object head cache and read the archive again")
    a.add_argument("--verbose", action="store_true")
    args = a.parse_args()
    if args.rebuild_object_heads:
        p = os.path.join(ROOT, OBJECT_CACHE)
        if os.path.exists(p):
            os.remove(p)
    if args.check_sample:
        check_sample()
        return
    o = run(args.threshold, verbose=args.verbose)
    v = o["validation"]
    print("tamilnadu heads of account classified: %d (%d distinct names)"
          % (o["entries"], o["distinct_names"]))
    print("  scheme         %5d  (%d distinct names)"
          % (o["classified_scheme"], o["classified_scheme_distinct_names"]))
    print("  not a scheme   %5d" % o["classified_not_scheme"])
    print("  of which recovery heads under minor head 911 or 902: %d\n"
          % o["recovery_heads"])
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
    print("  census precision  %.1f%%  (%d/%d published heads really are schemes, counted)"
          % (c["precision"] * 100, c["published"] - c["not_schemes"], c["published"]))
    print("  sample precision  %.1f%%  on %d stratified rows"
          % (p["precision"] * 100, v["n_labelled"]))
    print("  recall            %.1f%%  (%d real schemes scored below the bar)"
          % (p["recall"] * 100, p["false_negative"]))
    print("  held out          %.1f%% precision, %.1f%% recall on the %d rows no weight "
          "was fitted to\n" % (h["precision"] * 100, h["recall"] * 100, v["n_held_out"]))
    print("absent from myScheme Tamil Nadu and classified a scheme: %d of %d absent heads, "
          "%d distinct names, Rs %s cr"
          % (o["absent_from_myscheme_and_classified_scheme"],
             o["absent_from_myscheme_all_rows"], o["absent_distinct_names"],
             format(o["absent_cr"], ",.0f")))
    for x in o["absent_distinct"][:12]:
        print("   Rs %10s cr  score %3d  %s"
              % (format((x["be_lakh"] or 0) / 100, ",.0f"), x["score"], x["name"][:58]))


if __name__ == "__main__":
    main()
