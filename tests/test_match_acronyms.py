"""probably_same against hand labels for every pair it once accepted on an acronym alone.

tests/fixtures/acronym_pairs.json holds 1,310 pairs, collected on 2026-10-30 by logging
every True verdict that came from an acronym rule while the registry, the CAG join, the
Union classifier, the 16 state classifiers and the site build ran, and then labelled by
hand. "same" means one scheme, or one a component of the other ("PMMSY: Insulated
Vehicles" against "Pradhan Mantri Matsya Sampada Yojana"). "different" means siblings
under an umbrella acronym (two AICTE scholarships), or names that only mention the same
body, Act or word (an NDPS Act advisory board against a disability pension).

The old rules got every one of the 912 "different" pairs wrong (precision 0.30); the
rewrite of 2026-10-30 gets 6 wrong (0.980), and keeps 293 of the 398 "same" pairs (0.736).

The test fails if precision on this set drops below the floor, or if any pair in
MUST_BE_RIGHT is wrong. Recall is reported, not enforced. A "same" pair the rules miss
costs a duplicate entry or, for a state, a row reported absent from a portal that lists
it under a component; a "different" pair they accept costs a scheme its register entry
and can attach one scheme's money to another (Rs 31,820 cr of the National Health
Mission's flexible pool sat under an R&D scheme on the word SPONSORED).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "parse"))
from match import probably_same  # noqa: E402

PRECISION_FLOOR = 0.97

# One pair per failure shape this set was collected to catch, and per shape that must keep
# matching. These are checked one by one, not averaged away.
MUST_BE_RIGHT = [
    ("Advisory Board under NDPS Act",
     "Indira Gandhi National Disability Pension Scheme (Punjab)", False),
    ("Haryana State Creche Scheme", "HSCST Fellowship Programme", False),
    ("MSME Champions Scheme", "Design Scheme Under MSME Innovative Scheme", False),
    ("AICTE - Swanath Scholarship Scheme - Degree",
     "AICTE - Distinguished Chair Professor Fellowship", False),
    ("PRADHAN MANTRI VIDYALAXMI (PM-Vidyalaxmi) SCHEME", "Pradhan Mantri Jan Dhan Yojana", False),
    ("BIRSA AWAS YOJANA", "Block Level Institute for Rural Skill Acquisition (BIRSA)", False),
    ("Prime Ministers Scholarship Scheme PMSS",
     "Post Matric Scholarship For Scheduled Caste", False),
    ("Rastriya Krishi Vikas yojna-RKVY", "Mukhyamantri Rajya Krishi Vikas Yojana", False),
    ("Scheme for Transformational and Advanced Research in Sciences (STARS)",
     "Strengthening Teaching-Learning and Results for States (STARS)", False),
    ("DBT Cell Ex. UPNL Personnel Equal Work Pay",
     "Payment of Ex-Gratia Amount on Death of the UPNL Employee During Service", False),
    ("Scheme for Development of Silk Industry",
     "Schemes for Development of Sugar Industries", False),
    ("Pradhan Mantri Matsya Sampada Yojana (PMMSY)",
     "PMMSY: Insulated vehicles - Gujarat", True),
    ("DeenDayal Anthyodaya Yojana (DAY-NRLM",
     "Deendayal Antyodaya Yojana - National Rural Livelihoods Mission", True),
    ("Mahatma Gandhi NREGA", "Mahatma Gandhi National Rural Employment Guarantee Act", True),
    ("MPEDA", "Marine Product Export Development Authority (MPEDA)", True),
    ("PM KISAN", "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)", True),
    ("Svamitva", "SVAMITVA Yojana (Survey of Villages and Mapping with Improvised Technology "
                 "in Village Areas)", True),
    ("Pradhana Mantri Maatru Vandana Yojane", "Pradhan Mantri Matru Vandana Yojana", True),
    ("Regional Connectivity Scheme - UDAN (Ude Desh Ka Aam Naagrik)",
     "Ude Desh ka Aam Nagrik (UDAN) Yojana - Uttarakhand", True),
]


def main():
    pairs = json.load(open(os.path.join(HERE, "fixtures", "acronym_pairs.json"), encoding="utf-8"))
    tp = fp = fn = tn = 0
    wrong_accepts = []
    for p in pairs:
        got = probably_same(p["a"], p["b"])[0]
        if got and p["same"]:
            tp += 1
        elif got:
            fp += 1
            wrong_accepts.append(p)
        elif p["same"]:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    print(f"  {len(pairs)} labelled pairs: precision {precision:.3f} ({fp} wrongly accepted), "
          f"recall {recall:.3f} ({fn} same pairs no longer accepted)")
    for p in wrong_accepts[:10]:
        print(f"     wrongly accepted: {p['a'][:50]!r} ~ {p['b'][:50]!r}")
    bad = 0
    for a, b, want in MUST_BE_RIGHT:
        got, why = probably_same(a, b)
        if got != want:
            bad += 1
            print(f"  FAIL want={want} got={got} ({why})\n        {a[:60]}\n        {b[:60]}")
    if precision < PRECISION_FLOOR:
        print(f"  FAIL precision {precision:.3f} is under the floor of {PRECISION_FLOOR}")
        bad += 1
    print("  ok" if not bad else f"  {bad} failure(s)")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
