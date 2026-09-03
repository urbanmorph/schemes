"""
Classify Uttarakhand's Volume 5 lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Uttarakhand's own.

    data/uttarakhand/labels.json          hand ground truth, the input
    data/uttarakhand/classification.json  the verdicts, the output

373 hand labels: a 265-row stratified sample on whether the major head is revenue or
capital, then every row at the publishing bar labelled so precision is a COUNT. 112 of
2,324 lines clear it, precision 1.000 with no errors, recall 0.783.

THIS IS THE RAWEST BOOK OF THE ELEVEN. Uttarakhand's Volume 5 is the detailed estimates
with nothing filtered out, so the sample is full of Dearness Allowance, Travelling
Allowance, Pay, leave encashment, "Contribution for pension (pool corpus", "Deduct
-Recoveries" and 22 rows with no name at all. The base rate is 0.196. Four separate
negative groups measure EXACTLY zero over 265 labels:

    an allowance, pay or encashment                P(scheme) 0.000  over 22 rows
    construction, land, purchase, a building       P(scheme) 0.000  over 40
    a loan, share capital or a grant to a body     P(scheme) 0.000  over 17
    training, survey, census, computerisation      P(scheme) 0.000  over 16

THE WORD SCHEME IS ALMOST NOISE HERE, at P(scheme) 0.351 against a base of 0.196, and the
reason is one repeated line: "State Share Relative to Centrally Assisted Scheme" appears
throughout the book as the state's matching half of whatever precedes it, with no name of
its own. 25 sampled rows are that line or its bare partner "Centrally Assisted Scheme", and
none is a scheme. So the scoring is graded rather than flat: the words that name a benefit
carry +3, mission and abhiyan +2, and yojana or scheme only +1.

TWO GROUPS THE CENSUS FOUND, both of them a real scheme's name attached to something that
is not one. Staff pensions read exactly like citizen pensions -- Family pension, All India
Service Pensioners, Contribution to pension and gratuity, Payment to CRA for new pension
scheme -- and the word pension is one of the strongest positives in the file. And Pradhan
Mantri Krishi Sinchai Yojana appears six times as "Water to every field", "Har khet ko
pani" and "Integrated Watershed Management": PMKSY pays for micro-irrigation on a farm in
one line and digs a watershed in another, and only the sub-title tells them apart. Both
groups measure P(scheme) 0.000 and both are in the score.
"""

import argparse
import re

from classify_common import classify, norm, report

# Words that name a benefit somebody receives.
STRONG = re.compile(
    r"(krishi|poshan|anganwadi|aanganwadi|aajeevika|ajeevika|livelihood|awas|rural housing|"
    r"helpline|help line|palna|scholarship|pension|stipend|insurance|financial assistance|"
    r"assistance to dependents|free textbooks|free travel|self.?help group|"
    r"self.?employment)", re.I)
# Weaker: a programme word.
MID = re.compile(r"(mission|abhiyan)", re.I)
# Weakest, and deliberately so: see the docstring on "State Share Relative to Centrally
# Assisted Scheme".
WEAK = re.compile(r"(yojana|yojna|scheme)", re.I)

ASSET = re.compile(
    r"(allowance|\bpay\b|wages|encashment|pension \(pool|establishment expenses|"
    r"establishment of|\bestablishment\b|directorate|university|college|institute|council|"
    r"board|commission|authority|corporation|construction|building|buildings|\bland\b|"
    r"purchase|infrastructure|renovation|repair|capital asset|stadium|museum|\bloan|loans|"
    r"share capital|grant to|grants to|grant for|grant in aid|deduct|"
    r"state share relative to|centrally assisted scheme$|externally aided|nabard funded|"
    r"sasci|training|survey|census|computeri[sz]ation|digitization|monitoring|evaluation|"
    r"awareness|maintenance|road|roads|solid waste|area development|border area)", re.I)

# A pension for the state's own retired servants, which is written exactly like a pension
# for a citizen and is not one.
STAFF = re.compile(
    r"(all india service|family pension|gratuity|provident fund|new pension scheme|"
    r"legislators pension|legislature|employee group|pension \(pool|contribution to pension|"
    r"contributions for pension|payment to cra|pensioners|retired employee|work-charge|"
    r"interest on|payment against)", re.I)

# The same scheme name doing something else: PMKSY digging a watershed, RKVY cleaning a
# river, Saksham Anganwadi paying district staff.
SUBTITLE = re.compile(
    r"(har khet ko pani|water to every|watershed|namami gange|digital agriculture|"
    r"article 275|district level staff|cell constituted|reimbursement of salary|"
    r"payment of gst|information, education)", re.I)

PUBLISH_THRESHOLD = 4
LISTING_THRESHOLD = 1


def score(r):
    n = norm(r.get("name") or "")
    s, ev = 0, []
    if STRONG.search(n):
        s += 3
        ev.append(("+3", "a word that names a benefit"))
    if MID.search(n):
        s += 2
        ev.append(("+2", "a programme word: mission or abhiyan"))
    if WEAK.search(n):
        s += 1
        ev.append(("+1", "the word yojana or scheme, which this book uses loosely"))
    if ASSET.search(n):
        s -= 5
        ev.append(("-5", "an allowance, a work, a loan or an administrative line"))
    if STAFF.search(n):
        s -= 5
        ev.append(("-5", "a pension for the state's own staff, not for a citizen"))
    if SUBTITLE.search(n):
        s -= 5
        ev.append(("-5", "a scheme's name attached to infrastructure or to its own admin"))
    return s, ev


REJECTED = [
    {"signal": "the word scheme or yojana on its own",
     "measured": {"P_scheme": 0.351, "base_rate": 0.196, "n": 74},
     "why": ("Not rejected but demoted to +1, which is the only place in this directory "
             "that happens. 'State Share Relative to Centrally Assisted Scheme' is a line "
             "Uttarakhand repeats throughout Volume 5 as the matching half of whatever "
             "precedes it, with no name of its own, and it carries the word.")},
    {"signal": "whether the book's own printed total reconciles for the line",
     "measured": {"P_scheme": None, "base_rate": 0.196, "n": 2324},
     "why": ("Available and not used. 115 of 2,324 rows failed reconciliation, which says "
             "the reading of that row is uncertain, not that the row is or is not a "
             "scheme. Mixing a parse-quality flag into a content classifier would make "
             "precision a statement about the parser.")},
    {"signal": "the major head the line sits under",
     "measured": {"P_scheme": None, "base_rate": 0.196, "n": 2324},
     "why": ("Used to STRATIFY and not scored. Capital heads hold construction, but 2401 "
             "(Crop Husbandry) is the largest revenue head at 199 lines and holds both "
             "farm subsidies and directorate salaries.")},
]


def main():
    argparse.ArgumentParser(description="Classify Uttarakhand's Volume 5 lines.").parse_args()
    report("uttarakhand", *classify("uttarakhand", "Uttarakhand", score, PUBLISH_THRESHOLD,
                                    LISTING_THRESHOLD, REJECTED,
                                    row_fields=lambda r: {
                                        "major_head": r.get("major_head"),
                                        "minor_head": r.get("minor_head"),
                                        "books": r.get("books") or [],
                                        "total_reconciled": r.get("total_reconciled"),
                                    }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
