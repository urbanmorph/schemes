"""
Remember which schemes this register accused, and check every month whether they appeared.

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

    data/watchlist.json   one row per accusation, with the date it was first made

WHY THIS EXISTS. The register names schemes that a state's budget funds and that no
national portal lists, and then it forgot them. parse/changes.py diffs myScheme against its
own previous snapshot, which catches what the portal did, but it has no memory of what this
register SAID, so the one question the project is uniquely able to answer went unasked: of
the schemes named as missing, did any of them ever get listed?

Nobody else can answer it. Answering needs the accusation, the date it was made, and a
monthly re-check against the same portal, and this repository is the only place all three
exist together.

WHAT A ROW MEANS, and the wording matters because the temptation here is enormous.

    first_named    the snapshot in which this register first published this scheme as
                   funded and unlisted
    listed_on      the first snapshot in which the same scheme joined a myScheme record
    left_the_books the first snapshot in which the state's budget stopped naming it at the
                   publishing bar, which is not the same thing and is never counted as a fix

A row that moves from absent to listed is recorded as exactly that: two dates and the
portal's own record. THIS FILE NEVER CLAIMS THE LISTING HAPPENED BECAUSE OF THE REGISTER.
It cannot know that, the portal publishes no reason, and a register whose whole argument is
that other people's numbers outrun their evidence cannot make that trade on its own behalf.
The dates are the finding. What caused them is somebody else's research.

WHY THE KEY IS (state, identifier) AND NOT THE NAME. A state renames a scheme between
cycles more often than it renumbers it, and a name-keyed watchlist would read a rename as
one scheme disappearing and another being accused for the first time. The identifier is
whatever that state's classifier uses as its own key, which is the same thing the hand
labels are keyed on.
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

OUT = "data/watchlist.json"


def state_key(path):
    return os.path.basename(os.path.dirname(path))


def ident_of(r):
    """The identity a state publishes its claim under.

    Not one rule, because the states do not use one. The eight built on classify_common
    publish one absent row per scheme key, so the key is the identity. The four oldest
    publish absent_distinct DE-DUPLICATED BY NAME, because their books file one scheme under
    several heads of account and the head is not the thing being accused; those rows carry
    no single identifier at all, only the name they were collapsed on. Using the key where
    there is one and the name where there is not is what makes this list count the same
    things the site publishes, which the first version of this file did not: it keyed
    everything on the head of account and produced 1,748 accusations against a published
    1,632.

    The name fallback is NOT lower-cased, because the classifiers that collapse on the name
    collapse on it case-sensitively, and Maharashtra publishes "Scholarships to Students
    (Persons with Disabilities)..." and "Scholarships to students (Persons with
    Disabilities)..." as two provisions with two scheme codes and two different amounts.
    Lower-casing here merged them and made this list one short of the published claim.
    """
    return str(r.get("key") or r.get("code") or r.get("hoa")
               or (r.get("hoas") or [None])[0] or (r.get("name") or "").strip())


def today_rows():
    """(the accusations this snapshot makes, the listing status of every row at the bar)."""
    accused, at_bar, snapshot = {}, {}, None
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "*", "classification.json"))):
        key = state_key(f)
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if not d.get("all_entries"):
            continue
        snapshot = snapshot or d.get("snapshot")
        bar = d.get("publish_threshold")
        flag = f"in_myscheme_{key}"

        # Every row at the bar, by the same identity, so a scheme that was accused before
        # can be looked up now and asked whether the portal carries it yet. A name-collapsed
        # row is listed when ANY of the heads it was collapsed from is listed.
        for r in d["all_entries"]:
            if r.get("score", -99) < bar:
                continue
            i = f"{key}|{ident_of(r)}"
            was = at_bar.get(i)
            at_bar[i] = {
                "state": d.get("state"), "state_key": key, "ident": ident_of(r),
                "name": r.get("name"), "be_lakh": r.get("be_lakh"),
                "listed": bool(r.get(flag)) or bool((was or {}).get("listed")),
                "myscheme_name": r.get("myscheme_name") or (was or {}).get("myscheme_name"),
            }

        # The published claim, which is the thing being tracked.
        for r in (d.get("absent_distinct") or []):
            i = f"{key}|{ident_of(r)}"
            accused[i] = {
                "state": d.get("state"), "state_key": key, "ident": ident_of(r),
                "name": r.get("name"), "be_lakh": r.get("be_lakh"),
            }
    return accused, at_bar, snapshot


def run(snapshot=None):
    accused_now, at_bar, snap = today_rows()
    snap = snapshot or snap
    prev = {}
    p = os.path.join(ROOT, OUT)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            prev = {e["key"]: e for e in (json.load(fh).get("entries") or [])}

    entries = {}
    # Everything accused today: new ones get today's date, old ones keep theirs.
    for k, cur in accused_now.items():
        was = prev.get(k) or {}
        entries[k] = {
            "key": k, **cur,
            "first_named": was.get("first_named") or snap,
            "listed_on": was.get("listed_on"),
            "left_the_books": None,
            "myscheme_name": None,
            "status": "absent",
        }
    # Everything accused before and NOT accused today. Two different reasons, kept apart.
    for k, was in prev.items():
        if k in entries or not was.get("first_named"):
            continue
        e = dict(was)
        row = at_bar.get(k)
        if row and row["listed"]:
            e["status"] = "listed"
            e["listed_on"] = e.get("listed_on") or snap
            e["myscheme_name"] = row["myscheme_name"]
            e["left_the_books"] = None
        else:
            # The state's own book no longer names it at the bar, or a signal moved. That is
            # not a portal listing a scheme and is never counted as one.
            e["status"] = "no longer named at the bar"
            e["left_the_books"] = e.get("left_the_books") or snap
        entries[k] = e

    vals = list(entries.values())
    listed = [e for e in vals if e["status"] == "listed"]
    gone = [e for e in vals if e["status"] == "no longer named at the bar"]
    still = [e for e in vals if e["status"] == "absent"]

    write_json(OUT, {
        "built": utcnow(), "snapshot": snap,
        "what": ("Schemes this register named as funded by a state and listed by no national "
                 "portal, with the date each accusation was first made and the date, if it "
                 "ever comes, that the portal began listing it."),
        "causation_note": (
            "A scheme moving from absent to listed is recorded here as two dates and "
            "nothing else. This register does not claim the listing happened because of "
            "it: the portal publishes no reason, and inferring one would be the exact "
            "move this project documents in others."),
        "accused_total": len(vals),
        "still_absent": len(still),
        "since_listed": len(listed),
        "no_longer_named": len(gone),
        "snapshots_of_evidence": sorted({e["first_named"] for e in vals if e.get("first_named")}),
        "first_snapshot": min([e["first_named"] for e in vals if e.get("first_named")],
                              default=None),
        "entries": sorted(vals, key=lambda e: (e["state_key"], e["ident"])),
    })
    return vals, still, listed, gone, snap


def main():
    ap = argparse.ArgumentParser(description="Track whether named-absent schemes get listed.")
    ap.add_argument("--date", help="snapshot date to record against")
    a = ap.parse_args()
    accused, still, listed, gone, snap = run(a.date)
    print(f"watchlist ({snap}): {len(accused):,} accusations on record")
    print(f"  still absent      {len(still):,}")
    print(f"  since listed      {len(listed):,}")
    print(f"  no longer named   {len(gone):,}")


if __name__ == "__main__":
    main()
