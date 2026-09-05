"""
Which schemes in this register the CAG has audited.

AGENT-EDITABLE (PLAN.md §7). Reads data/cag/reports.json and data/registry.json, writes
data/cag/audited.json. Never fetches.

WHY THIS IS A SEPARATE STEP. It needs the union registry, and parse/cag.py runs in the
sources stage before the registry exists. Reading a stale registry.json from last month's
run would produce a join that looks current and is not, which is the failure this project
is about. So the dependency is explicit and run.sh orders it after parse/registry.py.

WHAT IS PUBLISHED AND WHAT IS NOT. Nothing here reads, quotes or characterises an audit
FINDING; that is the CAG's to publish. What is published is that a report exists on a
scheme this register holds, which is not available as a list anywhere and today means
paging through 2,804 entries by hand.

ONE RULE, AND THE MEASUREMENT THAT REJECTED THE OTHERS. probably_same offers several
routes to a match and they do not have the same precision on this corpus. All 142 joins
were read by eye:

  similarity >= 0.85          22 joins, 22 correct.   PUBLISHED
  containment                 66 joins, and it is the rule that fails here. A CAG subject
                              is a phrase, not a name, so "Employees' Provident Fund
                              Organisation" contains all the content words of "Internship
                              Scheme Of Employees' Provident Fund Organisation" and the
                              audit of the ORGANISATION is filed against one of its
                              schemes. "Role of Tea Board in Tea Development" joins both
                              "Tea Board" and "Tea Development Scheme".      REJECTED
  acronym rules               ~17 joins, and the same shape of error as everywhere else in
                              this register: rkvy against mrkvy joins Rashtriya Krishi
                              Vikas Yojana to Mukhyamantri Rajya Krishi Vikas Yojana.
                                                                             REJECTED
  begins-with                 7 joins, not separately validated, and not published for
                              that reason rather than because it was measured and failed.

The published tier is small and it is right, which is the trade this register makes every
time: an audit attached to the wrong scheme is a factual error on that scheme's page, and
a missing one is a gap the next pass can close.

WIDENING THE POOL TO THE WHOLE REGISTER CHANGED NOTHING, WHICH IS THE FINDING.

This joined against data/registry.json alone, 5,475 names from the four NATIONAL sources,
and the other half of the register was not in the pool at all: 4,716 more names read out of
fifteen state budget books, which could not be joined to any audit however exactly they
matched. That was plainly the wrong half to leave out, because 2,257 of the 2,804 reports
in the catalogue, 80% of it, are audits of STATE governments.

The pool is now 10,191 and each state's schemes are scoped to that state's own reports, so
a Karnataka report is never offered a Kerala scheme. The published joins went from 22 to
22. Not one of the 4,716 state names clears the similarity rule.

The reason is in the shapes of the two strings. A CAG subject names a programme area:
"Housing for Urban Poor". A state budget line names an accounting provision: "Grants to
Tamil Nadu Shelter Fund under Inclusive...", "Schemes Implementation of Housing Projects",
"Grants to TNUHDB for implementation of Asian Development Bank...". Those three are all
plausibly what that audit is about and none of them is what it is CALLED, so the only rule
that joins them is containment, which this file already measured and rejected, and these
are three fresh examples of why: one report, three different schemes, no way to tell from
the strings which one it audited.

So the coverage stays where it is and the denominator is now honest about what it counted.
Joining a state audit to a state scheme needs evidence these two documents do not share --
a scheme code in the report, or the report's own text -- and inventing a rule to bridge
them here would be this register doing what it documents in everybody else.
"""

import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from match import probably_same, tokens, skeleton, acronyms  # noqa: E402

# The similarity floor. 0.85 is where the hand-read tier ends, not a round number: the
# lowest correct join is Mahatama Gandhi National Rural Employment Guarantee Act against
# its correctly spelled twin at 0.87, and the CAG's own misspelling is what costs it those
# points. Below 0.85 the rule starts joining phrases that merely share a subject.
FLOOR = 0.85
CAND_CAP = 40


def load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def run():
    cag = load("data/cag/reports.json")
    reg = load("data/registry.json")
    if not cag or not reg:
        raise SystemExit("need data/cag/reports.json and data/registry.json: "
                         "run parse/cag.py and parse/registry.py first")

    # THE POOL IS BOTH HALVES OF THE REGISTER, AND IT USED TO BE ONE.
    #
    # This joined against data/registry.json alone: 5,475 names from the four NATIONAL
    # sources. The other half of what this register holds, 5,120 schemes read out of fifteen
    # state budget books, was not in the pool at all, so no state scheme could be joined to
    # any audit however exactly it matched. That is the wrong half to leave out. 2,257 of
    # the 2,804 reports in the catalogue, 80% of it, are audits of STATE governments, and a
    # state audit is precisely the thing a state scheme would join to.
    #
    # A state's schemes are scoped to that state's own reports, which is a precision gain
    # and not only a coverage one: a Karnataka report cannot be an audit of a Kerala scheme,
    # so scoping removes a whole class of wrong join before the similarity rule is asked.
    # The national pool stays joinable to every government, because a centrally sponsored
    # scheme really is audited in a state report.
    names, scope = [], []
    seen = set()
    for e in (reg.get("entries") or []):
        n = e.get("name")
        if n and n not in seen:
            seen.add(n)
            names.append(n)
            scope.append(None)          # joinable to any government
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "*", "classification.json"))):
        d = load(os.path.relpath(f, ROOT)) or {}
        if not d.get("all_entries"):
            continue
        st, bar = d.get("state"), d.get("listing_threshold")
        if not st or bar is None:
            continue
        flag = "in_myscheme_" + os.path.basename(os.path.dirname(f))
        for r in d["all_entries"]:
            n = r.get("name")
            # The rows the site publishes for this state: at its listing bar, and not
            # already held under a national name, which is what `seen` carries.
            if not n or r.get("score", -99) < bar or r.get(flag) or n in seen:
                continue
            seen.add(n)
            names.append(n)
            scope.append(st)
    idx = collections.defaultdict(set)
    for i, n in enumerate(names):
        for k in (set(tokens(n)) | {skeleton(t) for t in tokens(n)}
                  | {a for a in acronyms(n) if len(a) >= 5}):
            idx[k].add(i)

    subjects = [r for r in cag["entries"] if r.get("subject")]
    by_scheme = collections.defaultdict(list)
    considered = published = 0
    for r in subjects:
        sub = r["subject"]
        hits = collections.Counter()
        for k in sorted(set(tokens(sub)) | {skeleton(t) for t in tokens(sub)}
                        | {a for a in acronyms(sub) if len(a) >= 5}):
            hits.update(idx.get(k, ()))
        # Sorted on (shared keys, index), never on most_common: its tie-break is insertion
        # order, which comes from iterating a set of strings and therefore changes between
        # runs. A join that is published on Tuesday and not on Wednesday is worse than no
        # join at all.
        for i, n in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))[:CAND_CAP]:
            if n < 2:
                continue
            # A state's scheme is only ever a candidate for that state's own reports.
            if scope[i] is not None and scope[i] != r.get("government"):
                continue
            ok, why = probably_same(sub, names[i])
            if not ok:
                continue
            considered += 1
            # Only the similarity rule, and only above the floor. The reason is in the
            # module docstring and it is a measurement, not a preference.
            if not why.startswith("similarity"):
                continue
            try:
                score = float(why.rsplit(" ", 1)[1])
            except (IndexError, ValueError):
                continue
            if score < FLOOR:
                continue
            published += 1
            by_scheme[names[i]].append({
                "id": r["id"], "title": r["title"], "subject": sub,
                "audit_type": r.get("audit_type"), "government": r.get("government"),
                "tabled": r.get("tabled"), "sector": r.get("sector"),
                "detail_url": r.get("detail_url"), "pdf_url": r.get("pdf_url"),
                "similarity": score,
            })

    out = {name: sorted(v, key=lambda x: (x["government"] or "", x["id"]))
           for name, v in sorted(by_scheme.items())}
    write_json("data/cag/audited.json", {
        "built": utcnow(),
        "snapshot": cag.get("snapshot"),
        "source": cag.get("source"),
        "reports_in_catalogue": cag.get("reports"),
        "subjects_offered": len(subjects),
        "register_names": len(names),
        "register_names_national": sum(1 for x in scope if x is None),
        "register_names_state": sum(1 for x in scope if x is not None),
        "pool_note": ("Both halves of the register: every name from the four national "
                      "sources, joinable to any government, plus each state's own budget "
                      "schemes, joinable only to that state's reports. A Karnataka report "
                      "cannot be an audit of a Kerala scheme."),
        "joins_considered": considered,
        "joins_published": published,
        "schemes_audited": len(out),
        "rule": f"similarity >= {FLOOR}, and no other rule",
        "method_note": ("Every one of the joins any rule produced was read by eye. The "
                        "similarity tier was correct in all of them and is published; "
                        "containment and the acronym rules were wrong often enough to "
                        "reject, and the module records which errors decided that. A CAG "
                        "title is a phrase and not a name, which is why containment fails "
                        "here and works elsewhere: 'Employees' Provident Fund Organisation' "
                        "contains every content word of 'Internship Scheme Of Employees' "
                        "Provident Fund Organisation', and an audit of the organisation is "
                        "not an audit of that scheme."),
        "scope_note": ("That a report exists on this scheme, and nothing about what it "
                       "found. The CAG's conclusions are the CAG's to publish."),
        "schemes": out,
    })
    return out, considered, published


def main():
    argparse.ArgumentParser(description="Join the CAG catalogue to the register.").parse_args()
    out, considered, published = run()
    print(f"CAG join: {published} published of {considered} joins any rule produced")
    print(f"  {len(out)} schemes in the register have been audited")
    for n, v in list(out.items())[:8]:
        print(f"    {n[:52]:<54}{len(v)} report(s)")


if __name__ == "__main__":
    main()
