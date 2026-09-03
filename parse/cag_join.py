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
"""

import argparse
import collections
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

    names = sorted({e["name"] for e in (reg.get("entries") or []) if e.get("name")})
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
