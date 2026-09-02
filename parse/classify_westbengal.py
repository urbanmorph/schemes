"""
Classify West Bengal Detailed Demands sub-heads: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ and archive/. Never fetches.

    data/westbengal/labels.json         hand ground truth, the input
    data/westbengal/heads.json          a cache, rebuilt from the archive when stale
    data/westbengal/classification.json the verdicts, the output

parse/westbengal.py pulls 9,024 sub-heads out of Budget Publications 11 to 26, the full
Detailed Demands for Grants for 2026-2027, and its own caveat already says the plain
truth: those are the state's FULL detailed estimates, so the list is a superset of West
Bengal's schemes and not a count of them. 3,758 of the 9,024 carry a Deduct Recoveries
object head, 760 carry a negative provision, 688 are interest on or repayment of the
state's own borrowing, 1,820 are capital or loan heads and 2,115 name a body rather than
a person. Set against myScheme's 110 West Bengal records, essentially the whole 9,024 is
absent from the national citizen portal, and publishing that number as "schemes West
Bengal hides" would be false. It would mean naming "9.4% West Bengal SDL 2024 received on
01.01.2014", the Governor's Secretariat and the house building advance to All India
Service officers as schemes a government hid.

THIS IS THE LARGEST AND THE THINNEST CORPUS IN THE REGISTER, and the two facts are the
same fact. The base rate on the 450 row stratified sample is 8.4%: about one West Bengal
sub-head in twelve is a welfare scheme, against one in six for Tamil Nadu's Demand Books,
41% of Andhra Pradesh's scheme-wise rows and 55% of Karnataka's. That is a fact about the
document and not about the state.

WHAT THE STATE PRINTS, AND WHAT IT IS WORTH. West Bengal prints no purpose line, so this
is the Tamil Nadu situation, but it prints OBJECT HEADS under every sub-head: two digit
codes saying whether this money is `01 Salaries`, `53 Major Works / Land and Buildings`,
`34 Scholarships and Stipends` or `70 Deduct Recoveries`. Those are not published in
data/westbengal/schemes.json, deliberately and for a good reason stated in its docstring,
so this file rebuilds them out of archive/westbengal/<date>/ by reusing parse/westbengal.py's
own regexes, and caches the result at data/westbengal/heads.json keyed on the archive date.
That takes about twenty seconds across the sixteen volumes. Nothing here fetches. The
minor head names come out of the same pass and are cached beside them.

But West Bengal's object classification is far COARSER than Tamil Nadu's, and this is the
central finding about the source. Tamil Nadu has thirteen object codes that name a benefit
transfer and the rule "every object head is a benefit transfer head" measured P(scheme)
0.895 there. West Bengal has FOUR such codes, 05 Rewards, 33 Subsidies, 34 Scholarships
and Stipends and 85 Dietary Charge, and between them they cover 154 of the 9,024 heads.
The same rule measures 0.800 here, on five development rows. Meanwhile 31
Grants-in-aid-GENERAL covers 2,363 heads, more than a quarter of the corpus, and carries
almost no information: rows whose only object head is 31 are schemes 14.7% of the time
against a base rate of 8.0%. The state books Lakshmir Bhandar, a salary grant to a
municipality, a grant to a university and the Jai Bangla old age pension under that one
code. So the rule that carried Andhra Pradesh at 0.667 was rejected here for the second
time, on the same measurement that rejected it for Tamil Nadu.

WHERE THE OBJECT HEADS DID EARN THEIR KEEP is on the negative side, and it is worth more
than the positive side is: rows where every object head is an accounting head are schemes
0.0% of the time over 57 development rows and 0.0% over 49 held-out rows, and that rule
fires on 2,051 heads. It is what separates the recovery mirror from the provision it
mirrors, and West Bengal needs that separation more than any state so far, because its
recovery heads carry the SCHEME'S OWN NAME: Lakshmir Bhandar appears at 2235-60-800-091 as
a Deduct Recoveries head funded at nil.

THE CORRECTION THAT MATTERS MOST, and it is measured rather than assumed. The first
version of this file charged -4 to any row carrying a running cost object head, as Tamil
Nadu's does. That put Lakshmir Bhandar, Rs 12,491 crore, at score 2 and Kanyashree at 0,
because the state books a scheme's advertising, office expenses and computerisation under
the same sub-head as the transfer it makes. The measurement says to narrow it: a row whose
object heads are ALL running costs, with no grant and no transfer head beside them, is a
scheme 1.4% of the time on the development half and 0.0% on the held-out half, while a row
carrying a running cost head BESIDE a grant or transfer head is a scheme 15.4% and 50.0% of
the time. The rule now fires only in the first case. Lakshmir Bhandar still does not clear
the bar, for a different reason given below, but it is no longer punished for saying what
it spends on.

THE KEY IS THE HEAD OF ACCOUNT. `2235-02-103-076` is major head, sub-major, minor head and
sub-head, and it is West Bengal's own identifier for the provision. 9,024 heads of account
carry 6,440 distinct names, 6,355 ignoring case. EVERY COUNT IN THIS FILE IS ON THE 9,024
HEAD OF ACCOUNT BASIS unless the field name says distinct, because the state votes a
scheme's general head, its Scheduled Caste head under minor head 789 and its Tribal head
under 796 separately, and because it books a Deduct Recoveries mirror of many schemes
under a name identical to the scheme's. Collapsing on the name would merge a provision
with its own recovery head. The distinct-name count is carried alongside every published
figure so a reader can see both, and the absent list is also published de-duplicated by
name.

THE 66 LETTER-SPACED NAMES. The state itself typesets 66 names one letter at a time, so
"Expenditure for payment" is printed "E x p e n d i t u r e f o r p a y m e n t", and
parse/westbengal.py publishes them exactly as printed because the PDF separates letters
and words with the same single space: closing the gaps gives one run-on word and guessing
where the words end would be inventing a name. That decision is respected here and no name
is ever rewritten. For SCORING only, such a name is collapsed to its run-on string and the
vocabularies are matched as SUBSTRINGS of it, which asks a question the data can answer
("does the word assistance occur in this letter run") without answering the one it cannot
("where does each word end"). Only words of five letters or more are tried. The detector
fires on 62 of the 9,024 names rather than 66; the four it does not are names where only a
bracketed acronym is spaced, "(F A W L O I)" inside an otherwise normal name, which needs
no run-on matching. Its effect is measured: it fires on 4 of the 450 stratified rows, 2 of
them schemes, and 4 of the 134 published heads are letter-spaced names, all four of them
Indira Gandhi National Widow Pension Scheme heads under minor heads 789 and 796. Without
it the words widow and pension would be invisible on those rows and each would score 4
instead of 10. Four more letter-spaced heads reach 8 and 9 without clearing the bar, the
two PMFME micro food enterprise heads and the two general IGNWPS heads.

There are two label sets and they answer different questions.
  stratified, 450 rows   A probability sample across major head function families and the
                         allocation range. This is what the threshold sweep runs on,
                         because precision and recall estimated on anything else would not
                         generalise. 38 schemes, 412 not schemes.
  audit, 508 rows        Every remaining row the classifier scores 6 or above. With the 24
                         stratified rows already there, the two sets are a CENSUS of the
                         published region and of the four bands below it, so the published
                         list's error count is counted, not estimated. The audit was made
                         after the weights were fixed and was deliberately not fed back
                         into them, which is why its findings are in known_errors rather
                         than patched.

WHY THE STRATIFICATION IS ON THE MAJOR HEAD AND NOT THE DEPARTMENT. Tamil Nadu stratified
on department family because its books are one per department. West Bengal's departmental
unit is the demand for grant, and it is not a partition of this corpus: 350 of the 9,024
sub-heads sit under more than one demand and one sits under sixteen. The other candidate,
the two-letter department tag the books append to a name ([WC], [PN], [HF]), is missing on
697 rows. The major head is on every row exactly once, it is the state's own functional
classification, and reducing capital and loan heads to the revenue head of the same
function (4202 to 2202, 6202 to 2202) gives six families of 40 to 3,789 rows. Crossed with
six allocation bands that is 30 non-empty strata. Six bands and not five because a NEGATIVE
provision is its own population here: 760 rows carry one, they are the Deduct Recoveries
heads, and folding them into the bottom quartile would have hidden them.

WHY THE CENSUS STARTS AT 6. 9,024 rows put 532 rows at score 6 or above, 918 at score 4
and 1,482 at score 2. 532 rows is the largest set that can be read one by one and labelled
reliably by hand, and it covers the published region plus the four bands below it, which
is what the threshold argument needs. Below 6 the precision numbers in this file are
estimates from the stratified sample and are labelled as such.

THE LABELLING RULE, applied to every row and recorded per row in labels.json:
    scheme      the money buys a benefit an identifiable person or household receives:
                cash, a kit, food, a scholarship, a stipend, a fee waiver, a pension,
                insurance, a subsidy that lowers what that household pays, a loan or an
                interest subvention on its own borrowing, free travel, free power, a house,
                a named treatment entitlement, or training in which the trainee is himself
                the beneficiary.
    not_scheme  the money runs, builds, staffs or maintains an organisation or an asset,
                devolves general purpose funds to another tier of government, pays for the
                capacity of the delivery system rather than the benefit, discharges the
                state's obligation to its own serving or retired staff, services the
                state's own debt, or is an accounting or adjustment head.

Four lines did most of the work and they are stated in full in labels.json. FIRST, a public
health programme delivered through the system to the population at large is not a scheme:
routine immunisation, pulse polio and vector control fund the delivery system, while
Swasthya Sathi, a card a household holds and presents, is a scheme. SECOND, the food
subsidy splits on who is paid: a subsidy that lowers the price the ration card holder pays
for rice, wheat or sugar is a scheme, and the transport subsidy, the fair price shop
dealer's margin, the gunny bags and the paddy procurement cost under the same major head
are not, because the payee is a carrier, a dealer or a mill. THIRD, an employment
obligation is not a welfare scheme, which is Tamil Nadu's line and it holds here: the death
gratuity, leave encashment, the house building advance, the gallantry reward to a police
officer and the insurance cover for anganwadi workers are all cash to identifiable
households and all are not_scheme. FOURTH, the recovery mirror is not the provision it
mirrors. 181 of the 958 labels sat close enough to one of those lines to be flagged
borderline, and each carries the sentence that decided it.

WHAT ACTUALLY DISCRIMINATES. Measured on the 225 rows of the development half against a
base rate of 8.0%.

  the state's own accounting classification, which is not a guess:
    every object head is an accounting head               P(scheme) 0.000 over 57 rows
    debt service major head, 2049 6003 6004               P(scheme) 0.000 over 17 rows
    capital outlay or loan major head, 4xxx to 7xxx       P(scheme) 0.000 over 49 rows
    running cost heads only, no grant or transfer beside  P(scheme) 0.014 over 69 rows
    establishment or works minor head                     P(scheme) 0.000 over 26 rows
    minor head 800 Other Expenditure                      P(scheme) 0.000 over 39 rows
    every object head is a benefit transfer head          P(scheme) 0.800 over  5 rows
    welfare function major head                           P(scheme) 0.321 over 28 rows
    sub-plan minor head, 789 796 797                      P(scheme) 0.255 over 47 rows
    the SPARSH single nodal agency route                  P(scheme) 0.222 over 18 rows

  what the name says:
    the name names a body                                 P(scheme) 0.000 over 65 rows
    the name begins with an establishment word            P(scheme) 0.000 over 10 rows
    the name begins Add or Deduct                         P(scheme) 0.000 over  5 rows
    an accounting word in the name                        P(scheme) 0.048 over 21 rows
    an asset or works word in the name                    P(scheme) 0.019 over 54 rows
    a named beneficiary class in the name                 P(scheme) 0.348 over 23 rows
    a benefit word in the name                            P(scheme) 0.400 over 30 rows

Three of those are worth pausing on. The FIRST is "the name names a body" at -4, twice
Tamil Nadu's weight for the same rule, and the reason is that so much of this corpus is
money moving to a local body rather than to a person: Panchayat, Panchayat Samiti, Zilla
Parishad, Municipality and Municipal Corporation are all in that vocabulary and it fires on
2,115 heads, catching 121 of the 450 stratified rows without a single scheme among them,
and exactly one scheme among the 123 it catches in the whole 958 row label set. The SECOND is
the sub-plan minor head, which looks strong at 0.255 on the development half and measures
only 0.127 on the held-out half, which is why it is worth one point: West Bengal books
establishment under 789 and 796 as freely as it books schemes there. The THIRD is that the
scheme MARKER word, which Tamil Nadu kept at one point, is rejected here. It measures 0.158
gross, but on the rows where a marker word fires and no benefit or beneficiary word does it
measures 0.047, BELOW the base rate. Mission Vatsalya is a child protection service, Swachh
Bharat Mission is sanitation works and Jal Jeevan Mission is a pipe network.

WHY THE PUBLISHED THRESHOLD IS NOT THE F1-OPTIMAL ONE. Same rule as parse/classify.py and
its four siblings. F1 peaks at threshold 3, where the sample says precision is 59.3% and
two published names in five are not schemes. Publishing runs at 10. The audit census
settles that number, because it counts errors rather than estimating them:

    threshold  6   532 rows published, 135 are not schemes  precision 74.6%
    threshold  7   365 rows published,  72 are not schemes  precision 80.3%
    threshold  8   241 rows published,  28 are not schemes  precision 88.4%
    threshold  9   221 rows published,  25 are not schemes  precision 88.7%
    threshold 10   134 rows published,  10 are not schemes  precision 92.5%
    threshold 11    73 rows published,   5 are not schemes  precision 93.2%
    threshold 12    61 rows published,   4 are not schemes  precision 93.4%
    threshold 13    37 rows published,   2 are not schemes  precision 94.6%
    threshold 14    31 rows published,   0 are not schemes  precision 100.0%

The break is between 9 and 10. Read the bands rather than the cumulative column: the band
at exactly 6 is 167 rows of which 63 are not schemes, a marginal precision of 62.3%; the
band at 7 is 64.5%; the band at 8 is 85.0% over only 20 rows; the band at 9 is 87 rows
with 15 errors, 82.8%; and the band at 10 is 61 rows with 5 errors, 91.8%. Every band from
10 upward is at least 91.7% except a six-row band at 13 with two errors in it. Buying the
remaining 7.5 points by publishing at 14 would mean dropping 103 heads of which 93 really
are schemes, which is not a trade, it is a loss. Threshold 10 it is, and the ten errors
that survive are named in known_errors rather than patched out.

92.5% IS THE WEAKEST COUNTED PRECISION IN THE REGISTER and it should be read as such:
Karnataka counted 91.9%, Andhra Pradesh 95.7%, Tamil Nadu 96.3% and Kerala 97.4%. One
published West Bengal head in thirteen is not a scheme. Four of the ten errors are ONE head
name, "Transport Subsidy on Distribution of Rice and Wheat to APL and BPL Families at
Subsidized Price", voted four times under different minor heads, and it is labelled
borderline: a reader who treats the whole food subsidy as one entitlement would call it a
scheme. On the distinct-name basis the published list is 98 names of which 7 are not
schemes.

The stratified sample alone would have said 100% at threshold 10, on the strength of 8
rows. The census says 92.5%. Note the direction: here the probability sample was
flattering, as Karnataka's, Tamil Nadu's and Kerala's were, where Andhra Pradesh's was
pessimistic, which is the same lesson either way. With a base rate of 8.4% a 450 row sample
holds 38 schemes in total and 8 above the bar, and no sample of that size can state the
published list's precision to better than ten points. Precision is counted. Recall is
estimated, because the rows the classifier rejects are too many to label exhaustively.

WHAT IT STILL GETS WRONG. Ten errors survive at the bar and they are three families. Six
are the food trade: four transport subsidy heads and two fair price shop dealer margin
heads, all booked under object head 33 Subsidies, all naming APL and BPL families, all
paying somebody other than the family. Three are the delivery system wearing a beneficiary
class in its name: two Child Helpline Services heads and one anganwadi worker training
head, all under major head 2235 in a child welfare minor head. One is a building the state
booked under a scholarship object head, the improvement of a residential school at
Belpahari. Every one of them was found by reading the audit, and none has been patched,
because changing the weights to suit the audit would destroy the one measurement in this
file that counts errors instead of estimating them.

WHAT IT MISSES, AND IT IS WORSE THAN WHAT IT GETS WRONG. Recall at the published bar is
21.1% on the stratified sample and 10.0% on the held-out half, the lowest in the register
against Tamil Nadu's 41.0%, Andhra Pradesh's 36.5% and Karnataka's 31.6%. The rows it
loses are the state's own brands. Lakshmir Bhandar, Rs 12,491 crore on its general head
alone, scores 3: "Lakshmir Bhandar (LAXMI) [WC]" carries no beneficiary class, no benefit
noun and no works word, its object heads are a grant head and its own administration, and
the only thing the classifier can see is that it sits under major head 2235. Kanyashree
and Rupashree score 3 for the same reason. Keeping Bhandar and Prakalpa in the benefit
vocabulary would have lifted all three, and it was rejected as circular: those words were
read off schemes already known, and a classifier that recognises the schemes you can
already name is not measuring anything. The Jai Bangla old age and widow pensions on their
general heads, Rs 2,800 crore and Rs 1,950 crore, score 9 and fall one short, while their
Scheduled Caste and Tribal twins clear the bar, so the published list names those schemes
and understates them. The published count is a floor on West Bengal's schemes and never a
total, and the state could raise it tomorrow by printing one sentence per sub-head saying
what the money is for, which is what Karnataka does.
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
# stratified sample only. See the docstring for why this is 6 and not lower.
CENSUS_FROM = 6

HEAD_CACHE = os.path.join("data", "westbengal", "heads.json")


# ---------------------------------------------------------------------------
# The object head index, rebuilt from the archive because the parsed file drops it.
#
# data/westbengal/schemes.json does NOT carry object heads, and its caveat says why:
# "the object heads beneath it (Salaries, Wages, Other Charges) are deliberately not
# published, because they are what a scheme spends money on and not schemes". That is
# right for a register of schemes and wrong for a classifier, because the object head is
# the state saying in its own chart of accounts what kind of money this is. So this file
# rebuilds the index from archive/westbengal/<date>/, reusing parse/westbengal.py's own
# regexes rather than reimplementing them, and caches the result keyed on the archive
# date. The minor head names come out of the same pass, off the same DETAILED ACCOUNT
# lines. Nothing here fetches. The cleaner home for both is parse/westbengal.py emitting
# them per entry, at which point this section and its cache can be deleted.
# ---------------------------------------------------------------------------

# An object head as West Bengal prints it: a TWO digit code at indent one or two, e.g.
# " 31- Grants-in-aid-GENERAL", " 50- Other Charges", " 70-Deduct Recoveries". The
# detail heads beneath it ("     02-Other Grants", "     01-Pay") are indented three or
# more and are deliberately not read: they are what an object head is spent on. The
# sub-major head ("60- OTHER PROGRAMMES") sits at indent zero and is excluded by the
# same rule. Measured on the 2026-09-02 archive: 8,318 of the 9,024 sub-heads carry at
# least one object head, and the 706 that do not are heads the state prints with no
# figure rows under them at all.
OBJ_ROW = re.compile(r"^ {1,2}(\d{2})-\s*(\S.*?)\s*$")


def _archive_date():
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "westbengal", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/westbengal/: run collect/westbengal.py first")
    return dates[-1]


def _heads_of_book(text, wb, objects, minors):
    """Every object head printed under every sub-head of one volume, plus the minor
    head names, accumulated into the two dicts passed in.

    The state machine is parse/westbengal.py's, cut down to the two things this file
    needs: which sub-head is live, and which coded rows belong to it. The minor head
    restatement trap that module documents is honoured here too, because without it the
    object heads of a restated "001- Direction and Administration" line would be filed
    against a sub-head that does not exist.
    """
    minor = None
    current = None
    for page in text.split("\f"):
        if "DETAILED ACCOUNT" not in page:
            continue
        for raw in page.split("\n"):
            s = raw.rstrip()
            if not s.strip():
                continue
            m = wb.DETAIL_ACCOUNT.search(s)
            if m:
                minor = (m.group(1), m.group(2), m.group(3), m.group(4).strip())
                minors["%s-%s-%s" % minor[:3]][minor[3]] += 1
                current = None
                continue
            t = wb.TOTAL.match(s.strip())
            if t:
                label = t.group(1).split()[0] if t.group(1) else ""
                if wb.HOA_SUB.match(label):
                    current = None
                continue
            c = wb.CODE3.match(s)
            if c and minor is not None:
                code, frag = c.group(1), c.group(2)
                if code == minor[2] and frag.strip().lower() == minor[3].lower():
                    current = None
                    continue
                current = "%s-%s-%s-%s" % (minor[0], minor[1], minor[2], code)
                continue
            o = OBJ_ROW.match(s)
            if o and current is not None:
                objects[current].add(o.group(1))


def heads(date=None, verbose=False):
    """{"object_heads": {hoa: [codes]}, "minor_heads": {major-sub-minor: name}}."""
    date = date or _archive_date()
    path = os.path.join(ROOT, HEAD_CACHE)
    if os.path.exists(path):
        cached = json.load(open(path, encoding="utf-8"))
        if cached.get("date") == date:
            return cached["object_heads"], cached["minor_heads"]
    wb = _load("wb_parse", os.path.join(HERE, "westbengal.py"))
    src = os.path.join(ROOT, "archive", "westbengal", date)
    objects = collections.defaultdict(set)
    minors = collections.defaultdict(collections.Counter)
    for p in sorted(glob.glob(os.path.join(src, "bp-*.pdf.gz"))):
        with gzip.open(p, "rb") as fh:
            body = fh.read()
        _heads_of_book(wb.pdftotext(body), wb, objects, minors)
        if verbose:
            print("    %s  %d sub-heads" % (os.path.basename(p), len(objects)))
    # Sorted lists, never sets: parse/registry.py once returned a different entry count
    # on every run because it iterated a set, and that manufactured false change events.
    obj = {k: sorted(v) for k, v in sorted(objects.items())}
    # A minor head is printed once per volume that uses it and the wording drifts between
    # volumes ("SECRETARIATE" and "SECRETARIAT" are both printed). The commonest spelling
    # wins, ties broken alphabetically so the result does not depend on dict order.
    mnr = {k: sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
           for k, v in sorted(minors.items())}
    write_json(HEAD_CACHE, {
        "date": date,
        "what": ("The object heads printed under each sub-head of the West Bengal "
                 "Detailed Demands, and the name the books print for each minor head, "
                 "rebuilt from archive/westbengal/%s by parse/classify_westbengal.py. A "
                 "cache and not a source: delete it and it is rebuilt. It exists because "
                 "data/westbengal/schemes.json deliberately does not carry object heads, "
                 "and they are the state's own statement of what kind of money this is."
                 % date),
        "object_heads": obj,
        "minor_heads": mnr,
    })
    return obj, mnr


# ---------------------------------------------------------------------------
# Vocabularies. Each list was written by reading the 6,440 distinct names in the corpus
# and the 58 object head names the books use, before any of the numbers in the docstring
# were computed, so the weights are fitted and the word choices are not. One exception is
# recorded honestly: BENEFIT was pruned ONCE after the first measurement. The pruning
# rule was stated before it was applied: keep only words that name the THING a person
# receives, and drop every word that names the ACT of giving to an institution (grant,
# grants), the abstract noun for the policy area (welfare, financial, benefit, aid), or a
# brand element of a West Bengal scheme name (bhandar, prakalpa, bandhu, sathi). Measured:
# the vocabulary as first written fired on 50 of the 225 development rows at P(scheme)
# 0.280; pruned it fires on 30 at 0.400, and the 25 rows where ONLY the pruned words fire
# measure 0.160 against a base rate of 0.080. Keeping the brand elements in would also
# have been circular, because they were read off the names of schemes already known.
# ---------------------------------------------------------------------------

# West Bengal's object heads are TWO digit codes and the books print a name beside each.
# The full vocabulary in the 2026-2027 volumes is 58 codes; these are the groups.
#
#   benefit transfers, money that leaves government and reaches a person:
#     05 Rewards, 33 Subsidies, 34 Scholarships and Stipends, 85 Dietary Charge.
#   The set is small because West Bengal's object classification is coarse: 33 fires on
#   141 sub-heads and 34 on 137, against 2,374 for 31 Grants-in-aid-GENERAL.
TRANSFER_OBJ = {"05", "33", "34", "85"}
#   31 Grants-in-aid-GENERAL, 32 Contribution, 35 Grants for creation of Capital Assets,
#   36 Grants-in-aid-Salaries. These are transfers too and are deliberately NOT in that
#   set. See REJECTED_SIGNALS: 31 is the commonest object head in the books and rows
#   carrying only 31 are schemes 14.7% of the time against a base rate of 8.0%. The state
#   books Lakshmir Bhandar, a grant to a university and a salary grant to a municipality
#   under the same code.
GRANT_OBJ = {"31", "32", "35", "36"}
#   running the office, buying the supplies, building the asset:
#     01 Salaries, 02 Wages, 07 Medical Reimbursements, 11 Travel Expenses,
#     12 Medical Reimbursements under WBHS 2008, 13 Office Expenses,
#     14 Rents Rates and Taxes, 15 Royalty, 16 Publications,
#     17 Transportation Cost On Retirement, 19 Maintenance,
#     20 Other Administrative Expenses, 21 Materials and Supplies,
#     22 Arms and Ammunition, 24 P.O.L., 25 Clothing and Tentage,
#     26 Advertising and Publicity, 27 Minor Works, 28 Professional and Special Services,
#     30 Other Contractual Services, 41 Secret Service Expenditure, 51 Motor Vehicles,
#     52 Machinery and Equipment, 53 Major Works / Land and Buildings,
#     60 Other Capital Expenditure, 75 Purchase, 77 Computerisation,
#     78 Outsourcing of Services, 86 Hospital and Sanitation Charges, 87 Regeneration,
#     88 Escort Charges, 89 Stock, 90 Miscellaneous works, 91 Renewals and Replacements,
#     98 Training, 99 Employees Provident Fund.
RUNNING_OBJ = {"01", "02", "07", "11", "12", "13", "14", "15", "16", "17", "19", "20",
               "21", "22", "24", "25", "26", "27", "28", "30", "41", "51", "52", "53",
               "60", "75", "77", "78", "86", "87", "88", "89", "90", "91", "98", "99"}
#   50 Other Charges is deliberately in NEITHER group. It fires on 1,928 sub-heads, it is
#   the second commonest head in the books, and it is where the state books a transfer it
#   has no other code for: Yuvashree, the relief food supply and the MAA meal scheme all
#   carry it. Rows whose only object head is 50 measure P(scheme) 0.000 on the
#   development half over 10 rows and 0.125 on the held-out half over 16, which is a
#   measurement that says nothing either way, so it earns no points in either direction.
#   accounting and adjustment:
#     04 Pension/Gratuities, 43 Suspense, 45 Interest/Dividend, 54 Investment,
#     55 Loans and Advances, 56 Repayment of Loans, 63 Inter-Account Transfer,
#     64 Write off / losses, 65 Cash Settlement Suspense Account, 70 Deduct Recoveries.
#   04 sits here rather than with the transfers on purpose and it is the same line Tamil
#   Nadu drew: a service pension is the state discharging an employment obligation, not
#   running a welfare scheme, and West Bengal's social pensions are booked under 31 and
#   not under 04.
ACCOUNT_OBJ = {"04", "43", "45", "54", "55", "56", "63", "64", "65", "70"}

# Major heads whose whole function is transferring benefits to people: 2216 Housing,
# 2225 Welfare of SC ST and OBC, 2230 Labour and Employment, 2235 Social Security and
# Welfare, 2236 Nutrition, 2505 Rural Employment.
WELFARE_MAJOR = {"2216", "2225", "2230", "2235", "2236", "2505"}
# 2049 Interest Payments, 6003 Internal Debt of the State, 6004 Loans and Advances from
# the Central Government. 495, 183 and 78 sub-heads. These are the state's own borrowing:
# "9.4% West Bengal SDL 2024 received on 01.01.2014" is a row here, and there are 344 of
# them. Nothing in the corpus is more reliably not a scheme.
DEBT_MAJOR = {"2049", "6003", "6004"}
# Minor heads are standardised across Indian government accounts: 001 Direction and
# Administration, 003 Training, 004 Research, 005 Investigation, 051 Construction,
# 052 Machinery and Equipment, 053 Maintenance and Repairs, 090 to 098 the secretariat,
# attached offices and other establishments.
ESTAB_MINOR = {"001", "003", "004", "005", "051", "052", "053",
               "090", "091", "092", "094", "095", "096", "097", "098"}
# 789 Development Action Plan for Scheduled Castes, 796 Development Action Plan for
# Scheduled Tribes, 797 Transfer to Reserve Fund. West Bengal votes a scheme's general,
# Scheduled Caste and Tribal heads separately, which is why the same scheme name appears
# three times in the corpus.
SUBPLAN_MINOR = {"789", "796", "797"}

# Words that name the BODY receiving the money. In West Bengal this is the single
# strongest name signal and it is stronger than in Tamil Nadu, because so much of this
# corpus is grants to local bodies: the Panchayat, the Municipality, the Zilla Parishad
# and the Panchayat Samiti are in here for that reason and they carry it.
BODY = {
    "corporation", "corporations", "board", "boards", "authority", "authorities",
    "directorate", "directorates", "commission", "commissionerate", "committee",
    "council", "academy", "agency", "agencies", "department", "departments", "office",
    "offices", "society", "societies", "federation", "trust", "laboratory",
    "laboratories", "museum", "library", "secretariat", "secretariate", "tribunal",
    "court", "courts", "bureau", "bureaux", "university", "universities", "institute",
    "institutes", "institution", "institutions", "company", "limited", "ltd",
    "undertaking", "undertakings", "mill", "mills", "factory", "press", "wing", "wings",
    "cell", "depot", "workshop", "establishment", "establishments", "staff", "engineer",
    "engineers", "commissioner", "collector", "organisation", "organization",
    "panchayat", "panchayats", "panchayati", "municipality", "municipalities",
    "municipal", "parishad", "parishads", "samity", "samities", "samiti",
}

# Words that name an accounting or adjustment operation, or the administration of one.
ACCOUNTING = {
    "deduct", "recoveries", "recovery", "overpayments", "refund", "refunds", "suspense",
    "adjustment", "adjustable", "reduction", "transferred", "transfer", "write", "writes",
    "off", "investment", "investments", "equity", "repayment", "ways", "means",
    "advances", "advance", "outgo", "charges", "collection", "audit", "census", "survey",
    "computerisation", "computerization", "monitoring", "evaluation", "inspection",
    "supervision", "publicity", "awareness", "campaign",
}

# Words that name an asset or a civil work.
WORKS = {
    "construction", "constructions", "building", "buildings", "infrastructure",
    "infrastructural", "road", "roads", "bridge", "bridges", "works", "work",
    "maintenance", "repair", "repairs", "renovation", "upgradation", "up", "gradation",
    "modernisation", "modernization", "equipment", "equipments", "machinery", "erection",
    "restoration", "electrification", "dam", "dams", "barrage", "barrages", "reservoir",
    "canal", "canals", "embankment", "drainage", "sewerage", "tubewell", "tubewells",
    "godown", "godowns", "land", "lands", "premises", "complex", "campus",
    "strengthening", "improvement", "widening", "laying", "installation", "setting",
    "procurement", "purchase", "creation", "asset", "assets",
}

# Words that name the THING a person receives. Pruned once; see the block comment above.
BENEFIT = {
    "scholarship", "scholarships", "stipend", "stipends", "pension", "pensions",
    "incentive", "incentives", "assistance", "subsidy", "subsidies", "subvention",
    "free", "insurance", "compensation", "kit", "kits", "nutrition", "nutritional",
    "reimbursement", "allowance", "relief", "meal", "meals", "gratia", "waiver", "dole",
    "doles", "feeding", "distribution", "marriage", "maternity", "uniform", "uniforms",
    "bicycle", "bicycles", "cycle", "laptop", "books", "footwear", "ration", "rice",
    "wheat", "atta", "milk", "egg", "eggs", "housing", "house", "houses", "bari", "awas",
    "treatment", "remuneration", "honorarium", "cash", "rehabilitation", "suraksha",
}

# Words that name who receives it. A head that names its beneficiary class is describing
# a transfer; a head that names none is usually describing an office or an asset.
BENEFICIARY = {
    "students", "student", "women", "woman", "girls", "girl", "farmers", "farmer",
    "weavers", "weaver", "fishermen", "fisherman", "beneficiaries", "beneficiary",
    "victims", "victim", "workers", "worker", "families", "family", "children", "child",
    "persons", "person", "people", "youth", "youths", "widow", "widows", "disabled",
    "handicapped", "citizens", "households", "household", "artisans", "entrepreneurs",
    "mothers", "adolescent", "destitute", "orphan", "orphans", "poor", "old", "aged",
    "senior", "tribal", "tribals", "scheduled", "backward", "minority", "minorities",
    "transgender", "labourers", "labour", "pensioners", "boys", "landless", "unemployed",
    "patients", "infirm", "needy", "indigent", "sportsmen", "affected",
}

# Scheme-name morphology. Written, measured and REJECTED; see REJECTED_SIGNALS. It is
# kept here because the rejection is published with the vocabulary that produced it.
MARKER = {"yojana", "yojna", "yojona", "abhiyan", "mission", "scheme", "schemes",
          "prakalpa", "programme", "nidhi", "vandana", "bhandar", "shree", "sree",
          "bangla", "jai"}

# The name begins with an establishment word.
ESTAB_LEAD = re.compile(
    r"^\s*(directorate|director\b|direction\b|head\s?quarter|headquarter|"
    r"secretariate?\b|establishment|office of|regional office|district office|"
    r"pay (of|and)|salary of|salaries|staff\b|attached office|other establishment|"
    r"chief engineer|superintending engineer|executive engineer|district head)", re.I)
# "Deduct Recoveries of Overpayments", "Deduct - Amount met from the Reserve Fund".
ADD_DEDUCT = re.compile(r"^\s*(deduct|add)\b", re.I)


def tokens(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


# 66 of the 9,024 names are LETTER-SPACED by the state itself, so "Expenditure for
# payment" is typeset "E x p e n d i t u r e f o r p a y m e n t". parse/westbengal.py
# publishes them exactly as printed and says why: the PDF separates letters and words
# with the same single space, so closing the gaps gives one run-on word and guessing
# where the words end would be inventing a name. That decision is respected here. The
# name is never rewritten and is published as the state printed it.
#
# For SCORING only, such a name is collapsed to its run-on string and the vocabularies
# are matched as SUBSTRINGS of it. That asks a question the data can answer, "does the
# word assistance occur in this letter run", without answering the one it cannot, "where
# does each word end". Only words of five letters or more are tried, because short words
# occur inside longer ones by accident. The rule is applied to the 66 rows the detector
# fires on and to no others, and its effect is measured: it fires on 4 of the 450
# stratified rows, 2 of them schemes, and it is what lets the two letter-spaced
# MGNREGA heads be read at all.
def letter_spaced(name):
    """The run-on string if the state printed this name letter-spaced, else None."""
    t = (name or "").split()
    if len(t) >= 6 and sum(1 for x in t if len(x) == 1) / len(t) >= 0.5:
        return re.sub(r"[^a-z0-9]+", "", name.lower())
    return None


def words_in(name, vocab):
    """Which vocabulary words this name carries, sorted. Substring match on the run-on
    string for a letter-spaced name, whole-token match otherwise."""
    run = letter_spaced(name)
    if run is not None:
        return sorted(w for w in vocab if len(w) >= 5 and w in run)
    return sorted(tokens(name) & vocab)


# The weights. Negative weights are larger than positive ones on purpose. A row that
# looks like an establishment and also carries benefit words, "Establishment for
# implementation of Kanyashree Prakalpa", should have to work to clear the bar, because
# that is the row that would embarrass the published list.
WEIGHTS = {
    "acct_obj": -6, "debt_major": -6, "capital": -4, "body": -4, "estab_lead": -4,
    "add_deduct": -4, "running": -4, "acc_word": -3, "works": -3, "estab_minor": -2,
    "other_minor": -1,
    "all_transfer": 6, "some_transfer": 3, "welfare": 3, "who": 3, "ben": 3,
    "subplan": 1, "sparsh": 1,
}


def score_entry(name, hoa, obj):
    """Additive and auditable. Returns (total, evidence) with every line's arithmetic."""
    f = (hoa or "").split("-")
    major = f[0] if f else ""
    minor = f[2] if len(f) > 2 else ""
    obj = set(obj or ())
    ev = []
    total = 0

    def add(key, why):
        nonlocal total
        total += WEIGHTS[key]
        ev.append(["%+d" % WEIGHTS[key], why])

    # Structure first: what the state's own accounting classification says this is.
    if obj and obj <= ACCOUNT_OBJ:
        add("acct_obj", "every object head on this row is an accounting head: "
            + ", ".join(sorted(obj)))
    if major in DEBT_MAJOR:
        add("debt_major", "interest on or repayment of the state's own debt, major head "
            + major)
    if major[:1] in "4567":
        add("capital", "capital outlay or loan major head " + major)

    # What the name says it is.
    if ESTAB_LEAD.match(name or ""):
        add("estab_lead", "the name begins with an establishment word")
    if ADD_DEDUCT.match(name or ""):
        add("add_deduct", "the name begins Add or Deduct")
    body = words_in(name, BODY)
    if body:
        add("body", "the name names a body: " + ", ".join(body[:3]))

    # The running cost penalty fires only on a row that carries NO grant and NO transfer
    # head. That narrowing is not a guess, it is the measurement: a row carrying a
    # running cost head and nothing else is a scheme 1.4% of the time on the development
    # half over 69 rows and 0.0% on the held-out half over 62, while a row carrying a
    # running cost head BESIDE a grant or transfer head is a scheme 15.4% and 50.0% of
    # the time. The second case is a scheme paying for its own delivery, and Lakshmir
    # Bhandar is exactly it: object heads 02 Wages, 13 Office Expenses, 26 Advertising,
    # 31 Grants-in-aid, 50 Other Charges and 77 Computerisation on one sub-head. Charging
    # it for saying so was what the first version of this file did.
    run = sorted(obj & RUNNING_OBJ)
    if run and not obj & (GRANT_OBJ | TRANSFER_OBJ):
        add("running", "every object head is a running cost or works head: "
            + ", ".join(run[:4]))

    acct = words_in(name, ACCOUNTING)
    if acct:
        add("acc_word", "accounting word in the name: " + ", ".join(acct[:3]))
    works = words_in(name, WORKS)
    if works:
        add("works", "asset or works word in the name: " + ", ".join(works[:3]))
    if minor in ESTAB_MINOR:
        add("estab_minor", "establishment or works minor head " + minor)
    if minor == "800":
        add("other_minor", "minor head 800 Other Expenditure")

    # Positive structure. The two transfer clauses are exclusive: a row where every
    # object head is a benefit head is not also charged the weaker partial credit.
    if obj and obj <= TRANSFER_OBJ:
        add("all_transfer", "every object head on this row is a benefit transfer head: "
            + ", ".join(sorted(obj)))
    elif obj & TRANSFER_OBJ:
        add("some_transfer", "a benefit transfer object head: "
            + ", ".join(sorted(obj & TRANSFER_OBJ)))
    if major in WELFARE_MAJOR:
        add("welfare", "welfare function major head " + major)

    # Positive name evidence.
    who = words_in(name, BENEFICIARY)
    if who:
        add("who", "named beneficiary class in the name: " + ", ".join(who[:3]))
    ben = words_in(name, BENEFIT)
    if ben:
        add("ben", "benefit word in the name: " + ", ".join(ben[:3]))

    if minor in SUBPLAN_MINOR:
        add("subplan", "sub-plan minor head " + minor)
    if "SPARSH" in (name or ""):
        add("sparsh", "the SPARSH single nodal agency route")

    return total, ev


SIGNALS = [
    {"points": -6, "signal": "every object head on the row is an accounting head",
     "measured": ("P(scheme) 0.000 over 57 development rows and 0.000 over 49 held-out "
                  "rows, base rate 0.080. It fires on 2,051 of the 9,024 heads and it is "
                  "the biggest single thing the object heads buy this classifier. 3,758 "
                  "sub-heads carry object head 70 Deduct Recoveries and the ones carrying "
                  "nothing else are accounting mirrors that repeat the scheme's own name: "
                  "Lakshmir Bhandar, the National Family Benefit Scheme and the West "
                  "Bengal Urban Employment Scheme all appear in the corpus as rows of "
                  "this kind.")},
    {"points": -6,
     "signal": "interest on or repayment of the state's own debt, major heads 2049, "
               "6003 and 6004",
     "measured": ("P(scheme) 0.000 over 17 development rows and 0.000 over 16 held-out "
                  "rows. 688 heads in the corpus, and 344 of them are named like "
                  "\"9.4% West Bengal SDL 2024 received on 01.01.2014\". Nothing in this "
                  "corpus is more reliably not a scheme.")},
    {"points": -4, "signal": "capital outlay or loan major head, 4xxx to 7xxx",
     "measured": ("P(scheme) 0.000 over 49 development rows and 0.000 over 49 held-out "
                  "rows. 1,820 of the 9,024 heads. In West Bengal the capital section "
                  "really is works, equity participation and advances rather than schemes "
                  "booked on the capital side, with one important exception that this "
                  "signal costs: Pradhan Mantri Awas Yojana Gramin's revenue heads clear "
                  "the bar and its capital heads do not.")},
    {"points": -4, "signal": "the name names a body",
     "measured": ("P(scheme) 0.000 over 65 development rows and 0.000 over 56 held-out "
                  "rows. It fires on 2,115 heads. This is stronger in West Bengal than in "
                  "Tamil Nadu, where the same rule was worth -2, and the reason is that so "
                  "much of this corpus is money moving to a local body: Panchayat, "
                  "Panchayat Samiti, Zilla Parishad, Municipality and Municipal "
                  "Corporation are all in the vocabulary and all of them carry it.")},
    {"points": -4, "signal": "the name begins with an establishment word",
     "measured": "P(scheme) 0.000 over 10 development rows and 0.000 over 9 held-out rows, "
                 "323 heads in the corpus"},
    {"points": -4, "signal": "the name begins Add or Deduct",
     "measured": "P(scheme) 0.000 over 5 development rows and 0.000 over 6 held-out rows, "
                 "271 heads in the corpus"},
    {"points": -4,
     "signal": "every object head is a running cost or works head, with no grant and no "
               "transfer head beside it",
     "measured": ("P(scheme) 0.014 over 69 development rows and 0.000 over 62 held-out "
                  "rows, against 0.154 and 0.500 for the 13 and 2 rows that carry a "
                  "running cost head BESIDE a grant or transfer head. That contrast is "
                  "why the rule is written this way and it is the correction that matters "
                  "most for recall: a sub-head carrying 02 Wages, 13 Office Expenses, "
                  "26 Advertising and 77 Computerisation beside 31 Grants-in-aid is a "
                  "scheme paying for its own delivery, and Lakshmir Bhandar is exactly "
                  "that row.")},
    {"points": -3, "signal": "an accounting word in the name",
     "measured": "P(scheme) 0.048 over 21 development rows and 0.000 over 27 held-out "
                 "rows, 886 heads in the corpus"},
    {"points": -3, "signal": "an asset or works word in the name",
     "measured": "P(scheme) 0.019 over 54 development rows and 0.043 over 47 held-out "
                 "rows, 2,059 heads in the corpus"},
    {"points": -2,
     "signal": "establishment or works minor head, 001 003 004 005 051 052 053 and the "
               "090 block",
     "measured": "P(scheme) 0.000 over 26 development rows and 0.000 over 32 held-out "
                 "rows, 1,045 heads in the corpus"},
    {"points": -1, "signal": "minor head 800 Other Expenditure",
     "measured": ("P(scheme) 0.000 over 39 development rows and 0.067 over 30 held-out "
                  "rows. It is the commonest minor head in the books, 1,582 of 9,024, and "
                  "it is where a state parks what it has no other head for. One point and "
                  "no more, because real schemes are parked there too: the Yuvashree "
                  "recovery head and the pre-matric stipends for children in unclean "
                  "occupations both sit under 800.")},
    {"points": 6, "signal": "every object head on the row is a benefit transfer head",
     "measured": ("P(scheme) 0.800 over 5 development rows and 0.667 over 3 held-out "
                  "rows, and 0.692 over the 130 rows in the whole label set. It is the "
                  "strongest signal here and the thinnest: only 154 of the 9,024 heads "
                  "have every object head in 05 Rewards, 33 Subsidies, 34 Scholarships "
                  "and Stipends or 85 Dietary Charge, because West Bengal's object "
                  "classification is far coarser than Tamil Nadu's. Tamil Nadu measured "
                  "0.895 for the same rule over 19 rows out of a set of 13 transfer "
                  "codes; West Bengal has four.")},
    {"points": 3, "signal": "some but not all object heads are benefit transfer heads",
     "measured": ("P(scheme) 0.000 over the 5 development rows in this case exactly, and "
                  "there are NO such rows in the held-out half. That measurement says "
                  "nothing: five rows cannot separate anything. Across the whole 958 row "
                  "label set the case measures 0.689 over 45 rows, which is almost "
                  "exactly the 0.692 of the all-transfer case. It is kept, and the reason "
                  "is measured at the publishing bar rather than argued: setting it to 0 "
                  "instead takes the published list from 134 heads to 118 and the counted "
                  "errors from 10 to 9, so 15 of the 16 rows it adds are genuine schemes.")},
    {"points": 3, "signal": "welfare function major head, 2216 2225 2230 2235 2236 2505",
     "measured": "P(scheme) 0.321 over 28 development rows and 0.444 over 27 held-out "
                 "rows, against a base rate of 0.080, 1,255 heads in the corpus"},
    {"points": 3, "signal": "a named beneficiary class in the name",
     "measured": "P(scheme) 0.348 over 23 development rows and 0.333 over 24 held-out "
                 "rows, 1,002 heads in the corpus"},
    {"points": 3, "signal": "a benefit word in the name",
     "measured": ("P(scheme) 0.400 over 30 development rows and 0.359 over 39 held-out "
                  "rows, 1,350 heads in the corpus. This is the vocabulary that was "
                  "pruned once; as first written it fired on 50 development rows at "
                  "0.280, and the 25 rows where only the pruned words fire measure 0.160.")},
    {"points": 1, "signal": "sub-plan minor head, 789 796 797",
     "measured": ("P(scheme) 0.255 over 47 development rows but only 0.127 over 55 "
                  "held-out rows, which is why it is worth one point and not three. It "
                  "fires on 2,026 heads, nearly a quarter of the corpus, because West "
                  "Bengal votes a general, a Scheduled Caste and a Tribal head for the "
                  "same scheme and books establishment under the sub-plans too.")},
    {"points": 1, "signal": "the SPARSH single nodal agency route",
     "measured": ("P(scheme) 0.222 over 18 development rows and 0.375 over 8 held-out "
                  "rows, 473 heads in the corpus. SPARSH is how a centrally sponsored "
                  "scheme's money is routed to a single nodal agency, so this is the "
                  "state saying the head is a scheme rather than an establishment. It is "
                  "real and it is a funding label rather than a purpose, so it is worth "
                  "one point.")},
]

REJECTED_SIGNALS = [
    {"signal": "every object head on the row is a transfer head, counting 31 "
               "Grants-in-aid-GENERAL and its companions 32, 35 and 36 as transfers",
     "measured": ("P(scheme) 0.160 over 50 development rows and 0.167 over 60 held-out "
                  "rows, against a base rate of 0.080 and against 0.800 for the rows where "
                  "every head is a BENEFIT transfer head. Rows whose ONLY object head is "
                  "31 measure 0.147 and 0.190."),
     "why": ("This is the rule that carried Andhra Pradesh at 0.667 and it does not carry "
             "West Bengal, for the same reason it had to be narrowed for Tamil Nadu. 31 "
             "Grants-in-aid-GENERAL fires on 2,363 of the 9,024 heads and is the commonest "
             "object head in the books. The state books Lakshmir Bhandar, a salary grant to "
             "a municipality, a grant to a university and the Jai Bangla old age pension "
             "under the same code. Including it would have added roughly 1,500 rows at "
             "about twice the base rate, which is another way of saying it would have "
             "added noise. The narrowing costs real recall and it is visible in the "
             "known_errors: every Jai Bangla pension head in the corpus is booked as 31.")},
    {"signal": "object head 36 Grants-in-aid-Salaries as evidence either way",
     "measured": "P(scheme) 0.083 over 12 development rows and 0.000 over 11 held-out rows, "
                 "against a base rate of 0.080. 297 heads in the corpus.",
     "why": ("It looked like a clean negative before it was measured, because a grant that "
             "pays somebody else's salaries is the definition of funding an institution. On "
             "the development half it sits exactly on the base rate. Two measurements of "
             "eleven and twelve rows that disagree in sign are not a signal, so it earns "
             "nothing.")},
    {"signal": "object head 50 Other Charges as a running cost head",
     "measured": "rows whose only object head is 50 measure P(scheme) 0.000 over 10 "
                 "development rows and 0.125 over 16 held-out rows. 530 heads carry 50 "
                 "and nothing else; 1,928 carry it at all.",
     "why": ("The two halves disagree, and the reason is visible in the names: 50 is the "
             "catch-all the state uses when it has no other code, and it is where several "
             "real transfers are booked. Yuvashree, the MAA cooked meal scheme, the supply "
             "of food and milk to disaster affected persons and the disaster management "
             "kit all carry it. Adding it to the running cost group would have penalised "
             "each of those; leaving it out costs nothing measurable. It is in neither "
             "group.")},
    {"signal": "a scheme marker word in the name (yojana, abhiyan, mission, prakalpa, "
               "scheme, shree, bangla)",
     "measured": ("P(scheme) 0.158 over 57 development rows and 0.174 over 46 held-out "
                  "rows, against a base rate of 0.080. But on the rows where a marker word "
                  "fires and no benefit word and no beneficiary word does, it measures "
                  "0.047 and 0.094, which is BELOW the base rate."),
     "why": ("The apparent lift is entirely the benefit and beneficiary words the same "
             "names also carry. On its own margin the word contributes nothing, and it "
             "fires on 1,932 heads: Mission Vatsalya is a child protection service, "
             "Swachh Bharat Mission is sanitation works, Jal Jeevan Mission is a pipe "
             "network, and Krishionnati Yojana is an agriculture programme. Tamil Nadu "
             "kept this signal at one point on a lift of +0.126; here the lift is +0.078 "
             "gross and negative on the margin, so it is dropped.")},
    {"signal": "the head is funded at nil",
     "measured": "P(scheme) 0.112 over 89 development rows and 0.094 over 85 held-out "
                 "rows, against a base rate of 0.080 and 0.089. 3,811 of the 9,024 heads "
                 "carry no provision this year.",
     "why": ("42% of this corpus is funded at nil and the state means something by that: "
             "the head exists and carries no provision this year. Read either way it is "
             "not evidence about whether the head is a scheme, and the two halves put it "
             "within two points of the base rate. Scoring it would also penalise a real "
             "scheme the state has parked, which is exactly the fact a register of hidden "
             "schemes should surface rather than hide.")},
    {"signal": "the head carries a NEGATIVE provision",
     "measured": ("P(scheme) 0.000 over 27 development rows and 0.053 over 19 held-out "
                  "rows, which looks like a usable negative. It is not: all 760 rows in "
                  "the corpus with a negative provision carry object head 70 Deduct "
                  "Recoveries, and the count of negative rows WITHOUT object head 70 is "
                  "zero, in the corpus and in the label set."),
     "why": ("The signal is real and it is already counted. Adding it would double charge "
             "the accounting object head rule, which is the strongest negative in the "
             "file, and would make the arithmetic on those rows unreadable. Exactly "
             "redundant signals are worse than useless: they look like independent "
             "evidence.")},
    {"signal": "the OCASPS central assistance route",
     "measured": "P(scheme) 0.158 over 19 development rows and 0.103 over 29 held-out "
                 "rows, against a base rate of 0.080 and 0.089. 867 heads in the corpus.",
     "why": ("Tested alongside SPARSH, which survived. OCASPS marks Other Centrally "
             "Assisted State Plan Schemes and it fires on almost twice as many heads, "
             "including every crop mission, every school infrastructure head and every "
             "urban works head that draws central assistance. The held-out half puts it "
             "within two points of the base rate. It labels a funding route with no view "
             "about what the money buys.")},
    {"signal": "the minor head's own printed NAME names a beneficiary class",
     "measured": ("P(scheme) 0.235 over 51 development rows and 0.133 over 55 held-out "
                  "rows, which reads like a signal until the sub-plan minor heads are "
                  "taken out: on the remaining rows it measures 0.000 over 4 and 0.200 "
                  "over 5."),
     "why": ("It is the sub-plan signal wearing a different hat. Minor heads 789 and 796 "
             "are printed \"DEVELOPMENT ACTION PLAN FOR SCHEDULED CASTES\" and \"... "
             "SCHEDULED TRIBES\", the word scheduled is a beneficiary word, and those two "
             "minor heads alone are 1,980 of the 2,223 rows the rule fires on. The minor "
             "head names are read from the archive and published in the cache anyway, "
             "because they are useful context for a reader, but they score nothing.")},
    {"signal": "the name matches a myScheme record tagged West Bengal",
     "measured": ("parse/westbengal.py already measured this and recorded the result in "
                  "myscheme_join_summary: 126 joins produced, 51 wrong on inspection. Of "
                  "the 109 West Bengal myScheme records only 21 have a join that survived "
                  "inspection, and 66 heads of account out of 9,024 have one."),
     "why": ("This is the borrowed ground truth the hand labels replace, and here it is "
             "both bad and circular. Bad, because the defects are catalogued: a four "
             "letter acronym matching the five letter one it is a prefix of joined the "
             "State Disaster Response Fund to a stamp duty subsidy five times, and the "
             "state's own name reduced to two transliteration skeletons joined three "
             "myScheme records to an 8.00% government bond. Worse, the parser refused to "
             "settle the biggest question in its own join and said so: 44 heads matched "
             "myScheme's single \"Old Age Pension\" record and whether West Bengal runs "
             "one old age pension or nine is not decided by anything in these books. "
             "Circular, because the question this file answers is which heads are ABSENT "
             "from myScheme, so scoring presence would push down exactly the rows the "
             "answer is made of. Karnataka measured the same signal at a lift of 0.047 "
             "and rejected it.")},
]

KNOWN_ERRORS = [
    {"name": "Transport Subsidy on Distribution of Rice and Wheat to APL and BPL Families "
             "at Subsidized Price",
     "heads": ["2235-60-200-053", "2408-01-102-007", "2408-01-789-010", "2408-01-796-012"],
     "score": "12 to 13",
     "kind": "false positive, four of the ten counted errors at the published bar",
     "why": ("The single largest surviving error, and it is one head name voted four "
             "times, under the general, Scheduled Caste and Tribal heads and again under "
             "the food subsidy major head. It is booked under object head 33 Subsidies, "
             "it names APL and BPL families as its beneficiary class, and it carries the "
             "word Subsidy, so every positive signal in the file fires on it. The money "
             "goes to whoever carries the grain. It is labelled borderline in "
             "labels.json, because a reader who treats the whole food subsidy as one "
             "entitlement would call it a scheme, and the register should show that "
             "argument rather than settle it silently.")},
    {"name": "State Subsidy for payment of FPS Dealers claim of Margin and Distributors "
             "claim of Margin under NFSA",
     "heads": ["2408-01-789-008", "2408-01-796-010"],
     "score": "10",
     "kind": "false positive",
     "why": ("The same defect as the transport subsidy and the same object head. The "
             "payee is the fair price shop dealer. The line this file drew is that a "
             "subsidy which lowers the price the ration card holder pays is a scheme and "
             "one that pays the trade that carries it is not, and the head of account "
             "does not carry that distinction anywhere.")},
    {"name": "Child Helpline Services under Mission Vatsalya",
     "heads": ["2235-02-102-117", "2235-02-789-100"],
     "score": "10 to 11",
     "kind": "false positive",
     "why": ("A helpline is a service, not a transfer, but the head sits under major head "
             "2235 in the child welfare minor head, carries the beneficiary word child, "
             "and is routed through SPARSH. Nothing in the accounting distinguishes "
             "running a helpline from paying a child's family.")},
    {"name": "Assistance for Continuation of ICDS Training Programme - Anganwadi Workers "
             "under Saksham Anganwadi and POSHAN 2.0",
     "heads": ["2235-02-102-124"],
     "score": "10",
     "kind": "false positive, and it is the employment obligation line again",
     "why": ("Training the state's own anganwadi workers is staffing the delivery system. "
             "The head names workers, which is a beneficiary word, and sits in the child "
             "welfare minor head under the welfare major head. Two further heads of the "
             "same name score 9 and are below the bar by luck rather than by evidence.")},
    {"name": "Improvement of residential schools for Girls at Belpahari",
     "heads": ["2225-02-796-023"],
     "score": "10",
     "kind": "false positive",
     "why": ("A building, and the classifier says so: it is charged -3 for the works word "
             "Improvement. It clears the bar anyway because its ONLY object head is 34 "
             "Scholarships and Stipends, worth +6, and the state's own classification is "
             "the strongest evidence in this file. The state has booked a hostel building "
             "under a scholarship head, and no rule written from the head of account can "
             "see past that.")},
    {"name": "Lakshmir Bhandar (LAXMI) [2235-02-103-076], Rs 12,491 crore, Implementation "
             "of Kanyashree Prakalpa [2235-02-103-026], Rs 804 crore, and Implementation "
             "of Rupashree Prakalpa [2235-02-103-068], Rs 661 crore",
     "heads": ["2235-02-103-076", "2235-02-103-026", "2235-02-103-068"],
     "score": "3, and 4 on their sub-plan heads",
     "kind": "false negative, and it is the biggest one in the file",
     "why": ("West Bengal's largest cash transfer and its best known scholarship do not "
             "clear the bar, and the reason is the name. \"Lakshmir Bhandar (LAXMI)\" and "
             "\"Implementation of Kanyashree Prakalpa\" say nothing to a vocabulary of "
             "English benefit words: no beneficiary class, no benefit noun, and after the "
             "vocabulary prune not even a brand word, because keeping Bhandar and Prakalpa "
             "in the benefit list would have been reading the answer off schemes already "
             "known. Their object heads are 31 Grants-in-aid, which is worth nothing here, "
             "and the general head sits under minor head 103 rather than a sub-plan head. "
             "Every one of them scores 3, the welfare major head and nothing else; their "
             "Scheduled Caste and Tribal heads score 4 and still fall short by six. This "
             "is the same failure Tamil Nadu recorded for Magalir Urimai Thogai, and the "
             "fix is not in the classifier: the state could raise the "
             "count tomorrow by printing one sentence per sub-head saying what the money "
             "buys, which is what Karnataka does.")},
    {"name": "Pradhan Mantri Awas Yojna - Rural capital heads under major head 4216 and "
             "the Jai Bangla pension heads under minor head 102",
     "heads": ["2235-60-102-021", "2235-60-102-020", "2235-60-102-019"],
     "score": "6 to 9",
     "kind": "false negative, the recall cost of two deliberate choices",
     "why": ("The Jai Bangla old age, widow and Manabik pensions carry Rs 2,800 crore, "
             "Rs 1,950 crore and Rs 1,000 crore and score 9, 9 and 6. They are booked "
             "under object head 31 Grants-in-aid, which was measured and rejected, and "
             "their names carry Pension and a beneficiary class but sit under minor head "
             "102 rather than a sub-plan head. Their Scheduled Caste and Tribal twins do "
             "clear the bar, so the published list names the scheme and understates it. "
             "Recall at the published bar is 21.1% on the stratified sample: the published "
             "count is a floor on West Bengal's schemes and never a total.")},
]


# ---------------------------------------------------------------------------
# The sampling frame, kept here so the label set is reproducible and extendable.
# ---------------------------------------------------------------------------

def normalised_major(major):
    """A capital or loan major head reduced to the revenue head of the same function.

    Indian government accounts number the capital section 2000 above the revenue one
    (2202 Education, 4202 Capital Outlay on Education) and the loan section 2000 above
    that (6202). Reducing them lets one function family cover all three sections, which
    is what a department family means.
    """
    n = int(major)
    while n >= 4000:
        n -= 2000
    return n


def family(major):
    """Six function families over the 165 major heads in the corpus."""
    n = normalised_major(major)
    if n < 2200:
        return "GOVERNANCE"
    if n < 2300:
        return "SOCIAL"
    if n < 2500:
        return "AGRI"
    if n < 2600:
        return "RURAL"
    if n < 3600:
        return "ECONOMY"
    return "TRANSFERS"


def stratify(entries, target=400):
    """Deterministic stratified sample: function family crossed with allocation band.

    The axis is the MAJOR HEAD's function family and not the department, and the reason
    is West Bengal specific. The obvious departmental axis here is the demand for grant,
    but 350 of the 9,024 sub-heads sit under more than one demand and one sits under
    sixteen, so a demand is not a partition of the corpus. The other candidate, the
    two-letter department tag the books append to a name, is missing on 697 rows. The
    major head is on every row exactly once, it is the state's own functional
    classification, and the six families come out at 40 to 3,789 rows.

    Six allocation bands and not five: a NEGATIVE provision is its own band, because 760
    of these rows carry one and they are a distinct population, the Deduct Recoveries
    heads. Folding them into the bottom quartile would have hidden them.

    No random seed anywhere. Rows inside a stratum are sorted by head of account and
    picked at even spacing, so this returns the same rows on every machine and every run.
    """
    pos = sorted(r["be_lakh"] for r in entries if (r.get("be_lakh") or 0) > 0)
    cuts = [pos[int(len(pos) * f)] for f in (0.25, 0.5, 0.75)] if pos else [0, 0, 0]

    def band(r):
        v = r.get("be_lakh") or 0.0
        if v < 0:
            return "neg"
        if v == 0:
            return "nil"
        return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"

    cells = {}
    for r in entries:
        cells.setdefault((family(r["major_head"]), band(r)), []).append(r)
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


def myscheme_westbengal():
    """Scheme names myScheme lists for West Bengal. Sorted, so absence is reproducible."""
    names = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        states = d.get("_list", {}).get("beneficiaryState") or []
        if not any("bengal" in (s or "").lower() for s in states):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            names.add(n.strip())
    return sorted(names)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    9,024 heads against 110 records is a million calls to probably_same, each of which
    re-tokenises, re-skeletonises and re-derives the acronyms of both names from scratch.
    This is the same indexed join parse/westbengal.py describes doing, and it is an EXACT
    superset rather than a speed-for-accuracy trade: every branch in probably_same that
    can return True requires the pair to share a content token, share a transliteration
    skeleton, or stand in an acronym relation, so a pair that shares none of the three
    cannot match.
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
    wb = json.load(open(os.path.join(ROOT, "data", "westbengal", "schemes.json"),
                        encoding="utf-8"))
    entries = sorted(wb["entries"], key=lambda x: x["hoa"])
    obj, mnr = heads(verbose=verbose)

    labels = json.load(open(os.path.join(ROOT, "data", "westbengal", "labels.json"),
                            encoding="utf-8"))
    by_key = {x["key"]: x for x in labels["labels"]}

    listed = myscheme_westbengal()
    idx = myscheme_index(listed)

    rows = []
    for r in entries:
        oh = obj.get(r["hoa"], [])
        total, ev = score_entry(r["name"], r["hoa"], oh)
        # [0] because probably_same returns (bool, why) and a tuple is always truthy.
        hit = [n for n in myscheme_candidates(r["name"], idx)
               if probably_same(r["name"], n)[0]]
        rows.append({
            "key": r["hoa"],
            "hoa": r["hoa"],
            "name": r["name"],
            "major_head": r["major_head"],
            "minor_head": r["hoa"].split("-")[2],
            "minor_head_name": mnr.get("-".join(r["hoa"].split("-")[:3])),
            "sub_head": r["sub_head"],
            "be_lakh": r.get("be_lakh"),
            "object_heads": oh,
            "books": sorted(r.get("books") or []),
            "demands": sorted(r.get("demands") or []),
            "letter_spaced": letter_spaced(r["name"]) is not None,
            "score": total,
            "evidence": ev,
            "verdict": "scheme" if total >= threshold else "not a scheme",
            "in_myscheme_westbengal": bool(hit),
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
    absent_all = [x for x in rows if not x["in_myscheme_westbengal"]]
    absent = sorted((x for x in schemes if not x["in_myscheme_westbengal"]),
                    key=lambda x: (-(x["be_lakh"] or 0), x["key"]))

    # One row per NAME as well as per head of account, because the same scheme is voted
    # under several heads: the general head, the Scheduled Caste head under minor head
    # 789, the Tribal head under 796, the central share and the state share. Publishing
    # the heads alone would print Old Age Pension Scheme under Jai Bangla nine times down
    # a page and read as nine findings. The allocations add, because these are separate
    # provisions out of separate sub-plans and not overlapping cuts of one figure. The
    # score is the best any head achieved, because the evidence for a scheme being a
    # scheme does not weaken by being voted twice.
    by_name = {}
    for x in absent:
        e = by_name.get(x["name"])
        if e is None:
            e = by_name[x["name"]] = {"name": x["name"], "major_heads": [], "heads": [],
                                      "be_lakh": 0.0, "score": x["score"],
                                      "evidence": x["evidence"]}
        if x["major_head"] not in e["major_heads"]:
            e["major_heads"].append(x["major_head"])
        e["heads"].append(x["hoa"])
        e["be_lakh"] += x["be_lakh"] or 0.0
        if x["score"] > e["score"]:
            e["score"], e["evidence"] = x["score"], x["evidence"]
    distinct = sorted(by_name.values(), key=lambda r: (-(r["be_lakh"] or 0), r["name"]))
    for r in distinct:
        r["major_heads"] = sorted(r["major_heads"])
        r["heads"] = sorted(r["heads"])
        r["be_lakh"] = round(r["be_lakh"], 2)

    out = {
        "built": utcnow(),
        "snapshot": wb.get("snapshot"),
        "state": "West Bengal",
        "cycle": wb.get("cycle"),
        "variant": wb.get("variant"),
        "source": "data/westbengal/schemes.json, plus the object heads and minor head "
                  "names rebuilt from archive/westbengal/ and cached at " + HEAD_CACHE,
        "question": ("Which of West Bengal's 9,024 Detailed Demands sub-heads are welfare "
                     "schemes, and which are establishment heads, works heads, "
                     "institutions, devolution to local bodies, employment obligations, "
                     "debt service or accounting heads?"),
        "entries": len(rows),
        "distinct_names": len({x["name"].lower() for x in rows}),
        "counting_basis": (
            "EVERY COUNT HERE IS ON THE 9,024 HEAD OF ACCOUNT BASIS unless the field name "
            "says distinct. The head of account is West Bengal's own identifier for a "
            "provision and it is what the state votes: a scheme's revenue head and its "
            "capital head are separate provisions, and so are its general head, its "
            "Scheduled Caste head under minor head 789 and its Tribal head under 796, "
            "which is why the same name is printed three times. The 9,024 heads carry "
            "6,440 distinct names, or 6,355 once case is ignored, which is the number "
            "distinct_names reports. Collapsing on the name would merge a provision with "
            "its own Deduct Recoveries mirror, which carries the same name and is not the "
            "same thing, so the head of account is the published basis and "
            "absent_distinct is the de-duplicated view of the same list."),
        "publish_threshold": threshold,
        "classified_scheme": len(schemes),
        "classified_scheme_distinct_names": len({x["name"].lower() for x in schemes}),
        "classified_not_scheme": len(rows) - len(schemes),
        "funded_at_nil": sum(1 for x in rows if not x.get("be_lakh")),
        "funded_at_nil_and_classified_scheme": sum(
            1 for x in schemes if not x.get("be_lakh")),
        "negative_provision": sum(1 for x in rows if (x.get("be_lakh") or 0) < 0),
        "object_head_coverage": sum(1 for x in rows if x["object_heads"]),
        "letter_spaced_names": sum(1 for x in rows if x["letter_spaced"]),
        "letter_spaced_note": (
            "The state printed 66 names letter-spaced and parse/westbengal.py counts them "
            "that way. The detector here fires on 62, and the four it does not are names "
            "where only a bracketed acronym is spaced, \"(F A W L O I)\" inside an "
            "otherwise normal name, which needs no run-on matching. Every name is "
            "published exactly as the state printed it; the run-on collapse is used for "
            "scoring only and never rewrites the name."),
        "ground_truth": {
            "file": "data/westbengal/labels.json",
            "labelled": labels["labelled"],
            "scheme": labels["scheme"],
            "not_scheme": labels["not_scheme"],
            "borderline": labels["borderline"],
            "rule": labels["rule"],
            "sampling": labels["sampling"],
            "sets": labels["sets"],
            "why_not_myscheme": (
                "myScheme membership cannot be the ground truth here, and it was not a "
                "close call. parse/westbengal.py produced 126 joins between these 9,024 "
                "heads and the West Bengal myScheme records and read every one by eye: 51 "
                "are wrong, and the defects are reproduced in myscheme_join_defects below. "
                "Of 109 myScheme records only 21 have a join that survived inspection. The "
                "parser also refused to settle the largest question in its own join and "
                "said so in myscheme_join_summary.uncertain: 44 heads matched a single "
                "\"Old Age Pension\" record, 16 were counted sound and 28 wrong, and "
                "whether West Bengal runs one old age pension or nine is not decided by "
                "anything in these books. That judgement is not treated as ground truth "
                "here and no label in labels.json depends on it. Worse than bad, the "
                "signal would be circular: the question is which heads are absent from "
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
                "About one West Bengal sub-head in twelve is a welfare scheme, against "
                "one in six for Tamil Nadu's Demand Books, 41% of Andhra Pradesh's "
                "scheme-wise rows and 55% of Karnataka's. This is the lowest base rate in "
                "the register and it is a fact about the document rather than about West "
                "Bengal's schemes: these are the full detailed estimates of sixteen "
                "volumes, 3,758 of the 9,024 sub-heads carry a Deduct Recoveries object "
                "head, 688 are the state's own borrowing, 1,820 are capital or loan heads "
                "and 2,115 name a body rather than a person."),
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
                "not lower because of the scale: 9,024 rows put 532 rows at score 6 or "
                "above, 918 at score 4 and 1,482 at score 2. 532 rows is the largest set "
                "that can be read one by one and labelled reliably by hand, and it covers "
                "the published region plus the four bands below it, which is what the "
                "threshold argument needs. Below %d the precision numbers in this file are "
                "estimates from the stratified sample and are labelled as such. Recall "
                "always comes from the stratified sample, because the rows the classifier "
                "rejects are too many to label exhaustively."
                % (CENSUS_FROM, CENSUS_FROM, CENSUS_FROM)),
            "at_publish_threshold_census": at_census,
            "f1_optimal_threshold": max(full_sweep, key=lambda x: x["f1"])["threshold"],
            "why_not_f1": (
                "F1 peaks at threshold 3 on the stratified sample, where precision is "
                "59.3% and two published names in five are not schemes. Naming a scheme as "
                "hidden by a government is an accusation, so this runs at the "
                "high-precision end and accepts the recall loss. The break in the census "
                "is between 9 and 10 and it is visible in the bands rather than the "
                "cumulative column: the band at exactly 6 is 62.3% precise, the band at 7 "
                "is 64.5%, the band at 8 is 85.0% over only 20 rows, the band at 9 is "
                "82.8%, and the band at 10 is 91.8%. Every band from 10 upward is at least "
                "91.7% except a six-row band at 13. Note that cumulative precision is not "
                "monotone above the bar: it is 93.2% at 11, 93.4% at 12 and 94.6% at 13, "
                "and reaches 100% only at 14, where 31 heads out of 9,024 would be "
                "published. Buying the last 7.5 points would mean dropping 103 heads of "
                "which 93 really are schemes, which is not a trade, it is a loss."),
            "sample_versus_census": (
                "The stratified sample alone would have claimed 100% precision at "
                "threshold 10, on the strength of 8 rows above the bar. The census counts "
                "92.5%. It erred flatteringly here, as Karnataka's and Tamil Nadu's and "
                "Kerala's did, and pessimistically in Andhra Pradesh, which is the same "
                "lesson either way: a probability sample is the right tool for recall, "
                "which cannot be censused, and the wrong one for counting mistakes in a "
                "list short enough to read. With a base rate of 8.4% a 450 row sample "
                "holds only 38 schemes in total and 8 above the publishing bar, and no "
                "sample of that size can state a published list's precision to better "
                "than ten points."),
            "what_the_missing_purpose_line_costs": (
                "Karnataka's books print a purpose line, one sentence saying what the "
                "money buys, and that was the strongest signal in "
                "parse/classify_karnataka.py at P(scheme) 0.947. West Bengal prints none "
                "on any of the 9,024 sub-heads. What it prints instead is the object head, "
                "and here that is worth much less than in Tamil Nadu, because West "
                "Bengal's object classification is coarse: four codes in the whole book "
                "name a benefit transfer and they cover 154 sub-heads, while 31 "
                "Grants-in-aid-GENERAL alone covers 2,363 and carries almost no "
                "information. Recall at the published bar is 21.1% on the stratified "
                "sample and 10.0% on the held-out half, the lowest in the register, "
                "against Tamil Nadu's 41.0%, Andhra Pradesh's 36.5% and Karnataka's 31.6% "
                "at their own bars. The published count is a floor on West Bengal's "
                "schemes and never a total."),
        },
        "known_errors": KNOWN_ERRORS,
        "myscheme_westbengal_records": len(listed),
        "myscheme_record_count_note": (
            "This is counted live off data/myscheme/schemes/, every record whose "
            "beneficiaryState list mentions West Bengal. parse/westbengal.py's "
            "myscheme_join_summary below says 109 and that figure is hard coded there from "
            "an earlier count of the same directory. The two are reported side by side "
            "rather than reconciled, because a silently moving denominator is exactly the "
            "kind of thing a register should show rather than smooth over."),
        "myscheme_join_defects": wb.get("myscheme_join_defects"),
        "myscheme_join_summary": wb.get("myscheme_join_summary"),
        "absent_from_myscheme_all_rows": len(absent_all),
        "absent_from_myscheme_and_classified_scheme": len(absent),
        "absent_distinct_names": len({x["name"].lower() for x in absent}),
        "absent_cr": round(sum(x["be_lakh"] or 0 for x in absent) / 100.0, 2),
        "absent_note": (
            "Absence is decided by parse/match.py's generous matcher against the myScheme "
            "records tagged West Bengal, because claiming absence should require that even "
            "a generous matcher finds nothing. Read that number against "
            "myscheme_join_summary: the matcher produced 126 joins over the whole corpus "
            "and 51 of them are wrong, so a row counted present may not be, and the absent "
            "count here is if anything an understatement. The surviving list is a floor "
            "for the opposite reason too: no book prints a purpose line, recall at the "
            "published bar is 21%, and a scheme the state names Lakshmir Bhandar and books "
            "as a plain grant-in-aid cannot clear a high bar on the evidence the books "
            "print."),
        "absent_schemes": absent,
        "absent_distinct": distinct,
        "all_entries": rows,
    }
    write_json("data/westbengal/classification.json", out)
    return out


def check_sample():
    """Report which sampled or census rows have no hand label yet."""
    wb = json.load(open(os.path.join(ROOT, "data", "westbengal", "schemes.json"),
                        encoding="utf-8"))
    labels = json.load(open(os.path.join(ROOT, "data", "westbengal", "labels.json"),
                            encoding="utf-8"))
    obj, _mnr = heads()
    have = {x["key"] for x in labels["labels"]}
    entries = sorted(wb["entries"], key=lambda x: x["hoa"])
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
        description="Classify West Bengal Detailed Demands sub-heads as welfare scheme "
                    "or budget head.")
    a.add_argument("--threshold", type=int, default=PUBLISH_THRESHOLD)
    a.add_argument("--check-sample", action="store_true",
                   help="list sampled or census rows that carry no hand label yet")
    a.add_argument("--rebuild-heads", action="store_true",
                   help="drop the object head cache and read the archive again")
    a.add_argument("--verbose", action="store_true")
    args = a.parse_args()
    if args.rebuild_heads:
        p = os.path.join(ROOT, HEAD_CACHE)
        if os.path.exists(p):
            os.remove(p)
    if args.check_sample:
        check_sample()
        return
    o = run(args.threshold, verbose=args.verbose)
    v = o["validation"]
    print("westbengal heads of account classified: %d (%d distinct names)"
          % (o["entries"], o["distinct_names"]))
    print("  scheme         %5d  (%d distinct names)"
          % (o["classified_scheme"], o["classified_scheme_distinct_names"]))
    print("  not a scheme   %5d" % o["classified_not_scheme"])
    print("  of which carry a negative provision: %d, funded at nil: %d\n"
          % (o["negative_provision"], o["funded_at_nil"]))
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
    print("absent from myScheme West Bengal and classified a scheme: %d of %d absent heads, "
          "%d distinct names, Rs %s cr"
          % (o["absent_from_myscheme_and_classified_scheme"],
             o["absent_from_myscheme_all_rows"], o["absent_distinct_names"],
             format(o["absent_cr"], ",.0f")))
    for x in o["absent_distinct"][:12]:
        print("   Rs %10s cr  score %3d  %s"
              % (format((x["be_lakh"] or 0) / 100, ",.0f"), x["score"], x["name"][:58]))


if __name__ == "__main__":
    main()
