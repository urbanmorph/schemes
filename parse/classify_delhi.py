"""
Classify Delhi's Scheme-wise Budget lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Delhi's own.

    data/delhi/labels.json          hand ground truth, the input
    data/delhi/classification.json  the verdicts, the output

373 hand labels: a 282-row stratified sample on the shape of the provision, then every row
at the publishing bar labelled so precision is a COUNT. 100 of 1,578 lines clear it,
precision 0.960 with four named errors, recall 0.835.

THE BASE RATE IS 0.145, THE LOWEST OF ANY STATE HERE, and that is a fact about the
document rather than about Delhi. The Scheme-wise Budget is the whole of Delhi's spending
laid out by department, so it carries section headings (HIGHER EDUCATION, REVENUE DEPTT),
one line per grant-in-aid component of every autonomous body (Hindi Academy GIA-Salary,
Telugu Academy GIA-General), machinery purchases for each hospital, and a fair number of
fragments the parser could not reassemble ("upto secondary Scholarship level"). Seven rows
in eight are not schemes.

WHAT DELHI PUBLISHES THAT SEPARATES THEM. The provision is split into revenue money and
capital-or-loan money, and the split is nearly decisive on its own:

    the provision is capital or loan money only   P(scheme) 0.000  over 47 rows
    a build, buy or run word in the name          P(scheme) 0.000  over 63
    the name is entirely upper case               P(scheme) 0.000  over 19
    an institution's name                         P(scheme) 0.019  over 53
    GIA-Salary or GIA-Capital                     P(scheme) 0.024  over 41
    a benefit word                                P(scheme) 0.889  over 27

An all-upper-case name is a heading rather than a line, and that is the parser's shape
showing through the data rather than anything Delhi decided.

"ASSISTANCE TO" IS TWO DIFFERENT PHRASES and the census is what showed it. The sample put
precision at 1.000 and the census brought it to 0.850, with eight of the seventeen errors
sharing one shape: Assistance to Voluntary Organisations, Assistance to State Agencies for
Inter-state movement of foodgrains, Assistance to State Scheduled Castes Development
Corporations. "Assistance to a PERSON" is the strongest positive in the file and
"assistance to an ORGANISATION" measures P(scheme) 0.000 over 10 rows. The distinction is
what follows the preposition, and the score now reads it.
"""

import argparse
import re

from classify_common import classify, norm, report

BENEFIT = re.compile(
    r"\b(scholarship|financial assistance|assistance to|subsidy|subsidies|incentive|"
    r"pension|reimbursement|help line|helpline|yojana|meal|nutrition|samman|samridhi|"
    r"award)\b", re.I)

INSTITUTION = re.compile(
    r"\b(academy|college|university|institute|commission|society|board|centre|center|"
    r"parishad|sansthan|hospital|directorate|deptt|department)\b", re.I)

BUILD = re.compile(
    r"\b(construction|c/o|renovation|machinery|equipment|infrastructure|upgradation|"
    r"remodelling|strengthening|purchase|maintenance|computeri[sz]ation|installation|"
    r"development of|works)\b", re.I)

# Delhi writes one line per grant-in-aid component. Salary and Capital pay an institution
# to exist; General is the one that sometimes pays people, so it is not scored.
GIA_STAFF = re.compile(r"gia.\s?(salary|capital)", re.I)

# The other half of "assistance to". A voluntary organisation, a state agency or a
# development corporation is not a person, and the preposition is the only thing in the
# name that says which kind of assistance this is.
TO_ORGANISATION = re.compile(
    r"assistance to\s+(the\s+)?(state|states|voluntary|.*?agenc|.*?corporation|"
    r".*?organisation|local bod)|extension reform|\bATMA\b|\b(poetry|literature)\b", re.I)

PUBLISH_THRESHOLD = 3
LISTING_THRESHOLD = 1


def score(r):
    n = norm(r["name"])
    s, ev = 0, []
    if BENEFIT.search(n):
        s += 3
        ev.append(("+3", "a benefit word in the name"))
    if BUILD.search(n):
        s -= 4
        ev.append(("-4", "the line builds, buys or runs something"))
    if r.get("be_capital_or_loan_lakh") and not r.get("be_revenue_lakh"):
        s -= 4
        ev.append(("-4", "the provision is capital or loan money, not revenue"))
    if re.fullmatch(r"[^a-z]+", n):
        s -= 4
        ev.append(("-4", "the name is entirely upper case, so it is a heading"))
    if INSTITUTION.search(n):
        s -= 3
        ev.append(("-3", "the name names an institution"))
    if GIA_STAFF.search(n):
        s -= 3
        ev.append(("-3", "grant-in-aid for salary or capital"))
    if TO_ORGANISATION.search(n):
        s -= 4
        ev.append(("-4", "assistance to an organisation rather than to a person"))
    return s, ev


REJECTED = [
    {"signal": "GIA-General",
     "measured": {"P_scheme": 0.105, "base_rate": 0.145, "n": 38},
     "why": ("Barely below the base rate, and unlike GIA-Salary and GIA-Capital it "
             "sometimes pays people: Mission Vatsalya's Child Help Line and PM-JAY are "
             "both filed under it.")},
    {"signal": "the group the line is totalled under",
     "measured": {"P_scheme": None, "base_rate": 0.145, "n": 1578},
     "why": ("Not usable and worth saying why. Delhi's `group` is the running-total label "
             "the book prints, so its values are Sub Total, Sub-Total, sub total and "
             "TOTAL [DGHS]. It is the parser's anchor, not a department.")},
    {"signal": "buses, roads and sadak in the name",
     "measured": {"P_scheme": 0.143, "base_rate": 0.308, "n": 7},
     "why": ("Below the base rate and not cleanly: Subsidy to Cluster buses for female "
             "Commuters pays a fare and Subsidy for Electric Vehicles for 579 e-buses "
             "buys a fleet, and the word does not tell them apart.")},
]


def main():
    argparse.ArgumentParser(description="Classify Delhi's scheme-wise budget lines.").parse_args()
    report("delhi", *classify("delhi", "Delhi", score, PUBLISH_THRESHOLD,
                              LISTING_THRESHOLD, REJECTED,
                              row_fields=lambda r: {"group": r.get("group")}),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
