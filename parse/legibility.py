"""
Score every surveyed state on whether its own budget can be read by a machine.

AGENT-EDITABLE (PLAN.md §7). Reads data/<state>/schemes.json, writes data/legibility.json.
Never fetches.

    data/legibility.json    one row per surveyed state, five tests, a count, and a reason

WHY THIS EXISTS. This register can name Karnataka's hidden schemes and cannot name
Gujarat's, and until now the site reported the first and was silent about the second. That
silence reads as "Gujarat has nothing to find", when the truth is the opposite: Gujarat
publishes a great deal and publishes it in a shape no machine can read. A state that
refuses to be read is a finding about that state, and it belongs on the page beside the
states that yielded rather than in a repository file nobody opens.

THE FIVE TESTS, in the order a reader hits them. They are sequential, and that matters for
how a failure is displayed:

  1. list      The state publishes a document that names schemes one by one, for THIS
               cycle, and serves it when asked.
  2. text      pdftotext returns those names. Not curves, not a legacy 8-bit font.
  3. bounded   A machine can find where a name ends: a column, a separator, a code.
               This is the twenty-minute test the survey is built on.
  4. english   The names are published in English somewhere, so they can be joined to a
               national list that is in English.
  5. closes    The book prints its own totals and the parse agrees with them, so the
               reading proves itself against the source's own arithmetic.

A test that was never reached is NOT a failure and is never scored as one. Bihar converts
its budget to curves, so nobody knows whether Bihar's names are bounded; recording that as
a cross would be this register inventing two more failures out of one. Unreached tests are
null, the count says how many of the tests actually RUN were cleared, and the site says so.

WHAT IS HAND-ENTERED AND WHAT IS NOT. The verdicts are hand-entered because they come from
a person reading documents, which is the only way this survey has ever been done. Every
verdict for a state that was BUILT is then checked against that state's own parser output,
and a disagreement raises rather than publishing. So the table cannot claim a state's names
are English when its data says otherwise, and cannot claim a book closes when it does not.
The refusals carry no data to check against, which is exactly what a refusal means, so each
carries the measurement that decided it as text instead.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

TESTS = [
    ("list", "Publishes a scheme list",
     "A document that names schemes one at a time, for this cycle, and serves it."),
    ("text", "The names are text",
     "pdftotext returns them. Not drawings, not a legacy 8-bit font."),
    ("bounded", "A name has an end",
     "A machine can find where the name stops: a column, a separator, a code."),
    ("english", "Named in English",
     "So the name can be joined to a national portal that lists in English."),
    ("closes", "The book proves itself",
     "It prints its own totals, and a parse of it agrees with them."),
]

# One entry per state surveyed. `built` is the parser key under data/, or None for a state
# whose documents were read and not parsed. `why` is the single sentence the site prints,
# and for a refusal it must name the MEASUREMENT that decided it rather than an impression.
SURVEY = [
    # ---- built -------------------------------------------------------------------
    ("Karnataka", "karnataka", dict(list=True, text=True, bounded=True, english=True, closes=False),
     "The Gender, Child and SCSP/TSP books print no totals at any level, so the reading "
     "has nothing to check itself against."),
    ("Andhra Pradesh", "andhra", dict(list=True, text=True, bounded=True, english=True, closes=False),
     "Plain English and a single script, and the Gender Budget prints no totals to check "
     "a reading against."),
    ("Kerala", "kerala", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "The Annual Plan statements carry a scheme code, an English column and Unicode "
     "Malayalam."),
    ("Tamil Nadu", "tamilnadu", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "Fifty-five bilingual demand books with English in its own column and object heads "
     "against every line."),
    ("Telangana", "telangana", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "The Pragathi Paddu is a plain English scheme table; the current cycle is on the "
     "IFMIS portal and not on the Finance Department's own budget page."),
    ("Maharashtra", "maharashtra", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "It publishes an English EDITION of a Marathi book rather than a bilingual one, "
     "which is the single most useful thing a state does for anyone reading it."),
    ("Odisha", "odisha", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "Forty-four demand books with English above Unicode Odia and a printed total at "
     "every level."),
    ("West Bengal", "westbengal", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "English throughout the detailed demands, keyed on the head of account."),
    ("Punjab", "punjab", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "Gurmukhi cannot share a codepoint with Latin, and the books check their own "
     "arithmetic at every level of the head of account."),
    ("Jharkhand", "jharkhand", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "It prints STATE SCHEME &lt;name&gt;(&lt;code&gt;) in English capitals, and the "
     "Hindi and English are separated by a slash."),
    ("Delhi", "delhi", dict(list=True, text=True, bounded=True, english=True, closes=False),
     "The whole scheme budget is one plain English file, and its Grand Total does not "
     "close: 62,55,000 lakh printed against 64,55,956 summed, 3.2 per cent over."),
    ("Haryana", "haryana", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "The Plan Memorandum names 970 schemes where the national portal lists 249."),
    ("Uttarakhand", "uttarakhand", dict(list=True, text=True, bounded=True, english=True, closes=False),
     "Volume 5 names 2,302 schemes against the portal's 446, and 806 of its 4,492 "
     "printed totals do not reconcile against the rows beneath them."),
    ("Uttar Pradesh", "uttarpradesh",
     dict(list=True, text=True, bounded=True, english=False, closes=False),
     "The only state here built WITHOUT clearing the English test: there is no English "
     "anywhere in its budget, and myScheme lists its schemes in romanised Hindi rather "
     "than in English, so the join is a change of script. 111 of its 4,198 printed totals "
     "do not reconcile."),
    ("Tripura", "tripura", dict(list=True, text=True, bounded=True, english=True, closes=True),
     "These 134 state schemes and the 74 centrally sponsored ones printed beside them "
     "come to 208 against DBT Bharat's 209, the closest any state document here has come "
     "to reproducing a national count."),

    # ---- surveyed and refused ----------------------------------------------------
    ("Gujarat", None, dict(list=True, text=True, bounded=False, english=None, closes=None),
     "The Outcome Budget puts the name, the head of account and sometimes the target in "
     "one column with no separator, and the column boundaries move between pages. There "
     "is no rule that finds the end of a name."),
    ("Madhya Pradesh", None, dict(list=True, text=False, bounded=None, english=None, closes=None),
     "The Gender Budget is set in KrutiDev, a legacy 8-bit font whose ToUnicode map "
     "points back at 8-bit codepoints, so the extracted characters are not the "
     "characters on the page."),
    ("Bihar", None, dict(list=True, text=False, bounded=None, english=None, closes=None),
     "It converts its budget to vector curves before publishing it. Its own file is "
     "called Demands For Grants Curve.pdf, and 108 pages of it yield 108 extractable "
     "characters."),
    ("Chhattisgarh", None, dict(list=True, text=False, bounded=None, english=None, closes=None),
     "Its 44 department books extract 2,429 scheme rows perfectly and 0 of 2,429 "
     "readable names, in the Krishna and Chanakya legacy fonts; all twelve English "
     "editions it links return 404 while the Hindi twins work."),
    ("Rajasthan", None, dict(list=True, text=True, bounded=False, english=True, closes=None),
     "The Output-Outcome Budget is in English and breaks names across lines mid-word "
     "with no hyphen, which cannot be undone from geometry alone, and prints no totals "
     "to check a guess against."),
    ("Assam", None, dict(list=False, text=None, bounded=None, english=None, closes=None),
     "Its seven documents for this cycle include no scheme list. The FY 2024-25 Gender "
     "Budget is a good table and is two cycles behind what this register publishes."),
    ("Himachal Pradesh", None, dict(list=False, text=None, bounded=None, english=None, closes=None),
     "It publishes thirty documents and serves none of them: every link is a "
     "__doPostBack that 302s back to the portal home."),
]

NON_ASCII = re.compile(r"[^\x00-\x7f]")


def measure(key):
    """What the state's own parser output says, for the tests it can answer.

    Returns None for a state that was not built. This is the check on the hand-entered
    verdicts above, so it reads the published artefact rather than any working state, and
    it answers only what a scheme list can answer: a list exists, its names came out as
    text, its names are in English, and its arithmetic closes. Whether a name was BOUNDED
    is not measurable here, because a parser that ran at all found the boundary.
    """
    p = os.path.join(ROOT, "data", key, "schemes.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    # Every state that parses is LISTED on the site, straight from its own budget book.
    # What a classifier buys is not the listing but the ACCUSATION: "this scheme is funded
    # and no portal lists it" needs counted precision behind it, and until a state has one
    # its rows appear with no score and no verdict. The site used to require a classifier
    # before it would list anything at all, which left eight states invisible; the flag is
    # kept, renamed to what it actually gates.
    accuses = os.path.exists(os.path.join(ROOT, "data", key, "classification.json"))
    ents = d.get("entries") or []
    names = [r.get("name") or "" for r in ents]
    latin = sum(1 for n in names if not NON_ASCII.search(n))

    rec = d.get("reconciliation") or {}
    checked = failed = 0
    # Every state's parser reports reconciliation in its own shape, because every state's
    # book prints totals at its own levels. What they share is a pair of integers per
    # block, so this walks for those rather than assuming one layout.
    def walk(o):
        nonlocal checked, failed
        if isinstance(o, dict):
            if isinstance(o.get("checked"), int):
                checked += o["checked"]
                failed += o.get("failed") or 0
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(rec)

    return {
        "rows": len(ents),
        "on_site": True,
        "absence_claims_published": accuses,
        "names_in_latin_script": latin,
        "names": len(names),
        "totals_checked": checked,
        "totals_failed": failed,
        "cycle": d.get("cycle"),
        "source": d.get("source"),
        # The measured verdicts, in the same vocabulary as the hand-entered ones.
        "says": {
            "list": len(ents) > 0,
            "text": len(ents) > 0,
            # A stray Devanagari word inside an otherwise English name does not make the
            # name unjoinable, and demanding 100% would fail West Bengal for 43 rows in
            # 9,024. The claim being tested is "a reader of English can use this list".
            "english": bool(names) and latin / len(names) >= 0.95,
            # Not "it printed some totals". The book proves itself only if the parse agrees
            # with ALL of them; one that disagrees with 806 has found something the reading
            # does not explain, and saying so is the whole point of the column.
            "closes": checked > 0 and failed == 0,
        },
    }


def run():
    rows, disagreements = [], []
    for state, key, verdict, why in SURVEY:
        m = measure(key) if key else None
        if key and m is None:
            raise SystemExit(f"{state} is listed as built from data/{key}/ and that file is "
                             f"not there. Either the parser has not run or the key is wrong.")
        if m:
            for t, got in m["says"].items():
                if verdict.get(t) is not None and verdict[t] != got:
                    disagreements.append(
                        f"{state}: the table says {t}={verdict[t]} and data/{key}/schemes.json "
                        f"says {got}")
        run_tests = [t for t, _, _ in TESTS if verdict.get(t) is not None]
        cleared = [t for t in run_tests if verdict[t]]
        rows.append({
            "state": state,
            "key": key,
            "built": bool(key),
            "tests": {t: verdict.get(t) for t, _, _ in TESTS},
            "tests_run": len(run_tests),
            "cleared": len(cleared),
            # The first test it failed, which is the one worth naming. A state that fails
            # test 3 has passed 1 and 2, and reporting "Gujarat: 2 of 5" without saying
            # WHICH two invites the reading that Gujarat publishes half a budget.
            "failed_at": next((t for t in run_tests if not verdict[t]), None),
            "why": why,
            "measured": m,
        })

    # A disagreement is not a warning. If the hand-entered table and a state's own parser
    # output disagree about that state, one of them is wrong and neither should be
    # published as fact until a person has decided which.
    if disagreements:
        raise SystemExit("the survey table disagrees with the parsed data:\n  "
                         + "\n  ".join(disagreements))

    # A state that has been parsed and is not in the table would be published by the site
    # and absent from the scoreboard, which is the exact silence this file exists to end.
    parsed = {os.path.basename(os.path.dirname(p)) for p in
              [os.path.join(ROOT, "data", d, "schemes.json") for d in
               os.listdir(os.path.join(ROOT, "data"))]
              if os.path.exists(p)}
    missing = parsed - {r["key"] for r in rows if r["key"]}
    if missing:
        raise SystemExit(f"parsed but not in the survey table: {', '.join(sorted(missing))}. "
                         f"Add it to SURVEY, with the five verdicts, before it can be built.")

    built = [r for r in rows if r["built"]]
    refused = [r for r in rows if not r["built"]]
    write_json("data/legibility.json", {
        "built_at": utcnow(),
        "tests": [{"key": k, "label": lab, "what": what} for k, lab, what in TESTS],
        "states_surveyed": len(rows),
        "states_built": len(built),
        "states_refused": len(refused),
        "schemes_named": sum((r["measured"] or {}).get("rows", 0) for r in built),
        "states_on_site": sum(1 for r in built if (r["measured"] or {}).get("on_site")),
        "schemes_named_on_site": sum((r["measured"] or {}).get("rows", 0) for r in built
                                     if (r["measured"] or {}).get("on_site")),
        "states_with_absence_claims": sum(
            1 for r in built if (r["measured"] or {}).get("absence_claims_published")),
        "unreached_note": ("A test with no verdict was never reached, because an earlier "
                           "test decided the state first. It is not scored as a failure: "
                           "nobody knows whether Bihar's scheme names are bounded, because "
                           "Bihar's scheme names are drawings."),
        "method_note": ("Verdicts are hand-entered from reading each state's documents, "
                        "which is the only way this survey has ever been done. Every "
                        "verdict for a state that was built is then checked against that "
                        "state's own parser output, and a disagreement stops the build "
                        "rather than publishing. The refusals have no output to check "
                        "against, which is what a refusal is, so each carries the "
                        "measurement that decided it instead."),
        "states": rows,
    })
    return rows


def main():
    argparse.ArgumentParser(description="Score each surveyed state on machine legibility.").parse_args()
    rows = run()
    mark = {True: "yes", False: "NO", None: "-"}
    print(f"{'State':<18}{'':2}" + "".join(f"{k[:7]:<9}" for k, _, _ in TESTS) + "cleared")
    for r in rows:
        print(f"{r['state']:<18}{'*' if r['built'] else ' ':2}"
              + "".join(f"{mark[r['tests'][k]]:<9}" for k, _, _ in TESTS)
              + f"{r['cleared']} of {r['tests_run']}")
    b = [r for r in rows if r["built"]]
    print(f"\n  {len(b)} of {len(rows)} states surveyed yield a machine-readable scheme "
          f"list, naming {sum((r['measured'] or {}).get('rows', 0) for r in b):,} schemes")
    for r in rows:
        if not r["built"]:
            print(f"    {r['state']:<18} stops at {r['failed_at']}")


if __name__ == "__main__":
    main()
