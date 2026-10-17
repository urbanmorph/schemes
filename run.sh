#!/usr/bin/env bash
# Full monthly pipeline, in the order the design requires.
#
#   ./run.sh                 collect → verify → parse → enrich → build   (today's date)
#   ./run.sh --date 2026-08-30
#   ./run.sh --skip-collect  re-derive everything from the existing archive
#   ./run.sh --limit 20      smoke test (deliberately marked INCOMPLETE)
#   ./run.sh --refresh-annual  re-fetch the annual sources even if this cycle is held
#   ./run.sh --resume-month --if-needed --deadline-min 300     what the monthly job runs
#
# --resume-month continues the snapshot already started this month instead of opening a
# second one, --if-needed exits at once when this month's run already finished clean, and
# --deadline-min gives every collector a time budget inside that many minutes, keeping
# enough back to parse and build. A collector that hits its budget is stopped, what it
# archived stays on disk, and the run exits 75 so the next attempt continues it. See
# progress.py for what counts as done.
#
# The ordering is not a convenience. Collection writes raw bytes and nothing else;
# verification decides whether those bytes are a publishable snapshot; only then does
# anything parse them. A parse that ran before verification could build a change feed
# out of a throttled half-snapshot and publish "100 schemes removed this month".
#
# Everything the site reads is produced here. It used to stop after checks.py, so the
# union registry, the classifier, both enrichments, the change feed and both states were
# built only when someone ran them by hand. A register whose entire value is an unattended
# monthly series had half its pipeline outside the automation, which meant next month's
# run would have quietly published this month's stale data/registry.json as if it were
# current.
set -euo pipefail
cd "$(dirname "$0")"

DATE="$(date -u +%Y-%m-%d)"
CYCLE_YEAR=2026            # Union Budget cycle, and the year state books are keyed by
STATE_CYCLE="2026-27"
SKIP_COLLECT=0
REFRESH_ANNUAL=0
LIMIT=()
PACE=0.7
RESUME_MONTH=0
IF_NEEDED=0
DEADLINE=""
UNIT=${BUDGET_UNIT:-60}     # seconds per budget minute; only a test changes it

while [ $# -gt 0 ]; do
  case "$1" in
    --date)           DATE="$2"; shift 2 ;;
    --skip-collect)   SKIP_COLLECT=1; shift ;;
    --limit)          LIMIT=(--limit "$2"); shift 2 ;;
    --pace)           PACE="$2"; shift 2 ;;
    --refresh-annual) REFRESH_ANNUAL=1; shift ;;
    --resume-month)   RESUME_MONTH=1; shift ;;
    --if-needed)      IF_NEEDED=1; shift ;;
    --deadline-min)   DEADLINE=$(( $(date +%s) + $2 * UNIT )); shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

# The October 2026 run printed nothing for three hours and then everything at once,
# because Python buffers stdout when it is not a terminal. A log you cannot watch is a
# log that tells you what went wrong only after it is too late to matter.
export PYTHONUNBUFFERED=1

[ "$RESUME_MONTH" = "1" ] && DATE="$(python3 progress.py month-date)"
if [ "$IF_NEEDED" = "1" ] && python3 progress.py run-ok "$DATE"; then
  echo "the run for $DATE already finished clean (run.json); nothing to do"
  exit 0
fi

say() { printf '\n\033[1m== %s\033[0m  %s\n' "$1" "$(date -u +%H:%M:%SZ)"; }

# Every step that can fail runs through this, and the two things it replaces were both
# wrong in opposite directions. `|| true` swallowed a failure completely: parse/dbt.py
# could die every month and the run would print nothing and exit 0. A bare call under
# `set -e` aborted the whole run at the first failure, so one broken state classifier meant
# no sector pass, no change feed and no site build at all -- losing the month's publication
# to protect it. A monthly series wants neither. A failure here is named on stderr as it
# happens, the run continues and publishes what it can, and the exit status at the end says
# something went wrong.
FAILED=()
step() {
  local label="$1"; shift
  if ! "$@"; then
    FAILED+=("$label")
    printf '  \033[31m!! FAILED\033[0m %s\n' "$label" >&2
  fi
}

# A collector under a time budget. The October 2026 run spent 96 minutes collecting a
# complete myScheme snapshot, then 81 more inside the CAG crawl, and was killed at the
# job's three-hour limit before anything was committed. Every byte was lost, including
# the finished snapshot, because one step had no limit of its own and the commit waited
# for all of them.
#
# So each collector gets a cap in minutes, and with --deadline-min also no more than the
# time left after RESERVE, which is what parsing and building need. A collector that hits
# it is stopped (SIGTERM, then SIGKILL 30s later), its archive stays on disk for the next
# run to continue, and it is recorded in STOPPED, not FAILED: nothing is wrong with it,
# it ran out of time. One that cannot be given two minutes is not started at all.
# Without --deadline-min nothing is capped, which is how a person runs this by hand.
STOPPED=()
RESERVE=$(( ${RESERVE_MIN:-40} * UNIT ))
TIMEOUT="$(command -v timeout || command -v gtimeout || true)"
budgeted() {
  local label="$1" secs=$(( $2 * UNIT )) rc=0 t0
  shift 2
  if [ -n "$DEADLINE" ]; then
    local left=$(( DEADLINE - $(date +%s) - RESERVE ))
    [ "$left" -lt "$secs" ] && secs=$left
    if [ "$secs" -lt $(( 2 * UNIT )) ]; then
      STOPPED+=("$label")
      printf '  \033[33m.. DEFERRED\033[0m %s: out of time this run, the next one starts it\n' "$label"
      return 0
    fi
  fi
  t0=$(date +%s)
  if [ -n "$DEADLINE" ] && [ -n "$TIMEOUT" ]; then
    "$TIMEOUT" -k 30 "$secs" "$@" || rc=$?
  else
    "$@" || rc=$?
  fi
  if [ "$rc" = 124 ] || [ "$rc" = 137 ]; then
    STOPPED+=("$label")
    printf '  \033[33m.. STOPPED\033[0m %s at its %ss budget; what it archived stays for the next run\n' \
      "$label" "$secs"
  elif [ "$rc" != 0 ]; then
    FAILED+=("$label")
    printf '  \033[31m!! FAILED\033[0m %s\n' "$label" >&2
  fi
  echo "  ($label: $(( $(date +%s) - t0 ))s)"
}
[ -n "$DEADLINE" ] && [ -z "$TIMEOUT" ] && \
  echo "  no timeout(1) on this machine: collectors run uncapped and the deadline is advisory" >&2

# An annual document does not change between January and December, and re-fetching 20MB
# of state budget PDFs twelve times a year to watch them not change is rude to a source
# this project depends on. These collect once per cycle and are skipped once the archive
# holds them, which --refresh-annual overrides when a state republishes mid-year.
have_annual() { [ "$REFRESH_ANNUAL" = "0" ] && compgen -G "$1" > /dev/null; }

# The same question for a STATE budget, and it has to be asked differently. A state's
# archive is keyed on the date it was collected, not on the cycle it covers, so
# `archive/karnataka/*` matches last year's book as happily as this year's. The guard used
# to be exactly that glob, which meant a state collected once was never collected again:
# roll STATE_CYCLE to 2027-28 and the register would go on publishing 2026-27 provisions
# for every one of the fifteen states, indefinitely and without a word. The Union Budget's
# guard was cycle-scoped and the states' was not, and only the Budget would have moved.
#
# So the question is asked exactly: is there an archive for THIS cycle? It used to assume
# every manifest records that as `cycle: "2026-27"`, and nine of sixteen do not, so those
# nine were re-downloaded every month. progress.py held knows all three ways they say it.
have_cycle() {
  [ "$REFRESH_ANNUAL" = "0" ] || return 1
  python3 progress.py held "$1" "$2"
}

if [ "$SKIP_COLLECT" = "0" ]; then
  # Each source is a chunk that is either finished for this snapshot, and skipped, or
  # not, and run under its budget. myScheme resumes from its own archive (collect/
  # myscheme.py keeps every whole record it already wrote), so a second attempt fetches
  # only what the first did not reach. A --limit smoke run is never "done", by design.
  say "collect · myScheme ($DATE)"
  if [ "${#LIMIT[@]}" -eq 0 ] && python3 progress.py finished myscheme "$DATE"; then
    echo "  every detail for $DATE is archived, skipping"
  else
    budgeted "collect/myscheme" 150 \
      python3 collect/myscheme.py --date "$DATE" --pace "$PACE" "${LIMIT[@]+"${LIMIT[@]}"}"
  fi

  say "collect · DBT Bharat"
  if python3 progress.py finished dbt "$DATE"; then
    echo "  DBT for $DATE is archived, skipping"
  else
    budgeted "collect/dbt" 15 python3 collect/dbt.py --date "$DATE"
  fi

  # The audit catalogue is append-mostly and grows a few reports a month, so unlike the
  # budgets it is collected every month. 282 paced requests: 26 minutes from a laptop in
  # India, but more than 81 from a GitHub runner, where it was still going when the
  # October 2026 job was killed. Hence 120 minutes, which still fits the deadline beside
  # a myScheme that needs its whole 96 (the budget gives it what is left either way).
  # The walk checks its own distinct-id count against the
  # total the site prints, a checksum an incremental crawl could not do, and that is also
  # why it cannot resume: a walk that stops part way is deleted rather than kept, so
  # parse/cag.py goes on reading the last complete one instead of a fragment.
  say "collect · CAG catalogue"
  if python3 progress.py finished cag "$DATE"; then
    echo "  a complete CAG walk for ${DATE:0:7} is archived, skipping"
  else
    budgeted "collect/cag" 120 python3 collect/cag.py --date "$DATE"
    if [ -d "archive/cag/$DATE" ] && [ ! -f "archive/cag/$DATE/_manifest.json" ]; then
      echo "  discarding the unfinished CAG walk for $DATE"
      rm -rf "archive/cag/$DATE"
    fi
  fi

  say "collect · annual sources"
  # These used to run bare under `set -e`, so one state's site being down ended the whole
  # month's run before verification. They are budgeted steps now, like everything else.
  if have_annual "archive/budget/$CYCLE_YEAR"; then
    echo "  Union Budget $CYCLE_YEAR already archived, skipping"
  else
    budgeted "collect/budget" 20 python3 collect/budget.py --year "$CYCLE_YEAR"
  fi
  for st in karnataka andhra kerala tamilnadu maharashtra odisha westbengal \
            telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh \
            chhattisgarh; do
    if have_cycle "$st" "$STATE_CYCLE"; then
      echo "  $st $STATE_CYCLE already archived, skipping"
    # Not every collector takes --cycle, and passing it to one that does not aborts the
    # whole run under `set -e`. A state takes it when the cycle is part of the ADDRESS of
    # its documents (Karnataka's index URL carries the financial year); a state that omits
    # it discovers the cycle from the page and asserts it, which is the same guarantee
    # reached the other way round. Asking the collector rather than keeping a second list
    # here means the two cannot drift.
    elif python3 "collect/$st.py" --help 2>/dev/null | grep -q -- "--cycle"; then
      budgeted "collect/$st" 20 python3 "collect/$st.py" --cycle "$STATE_CYCLE" --date "$DATE"
    else
      budgeted "collect/$st" 20 python3 "collect/$st.py" --date "$DATE"
    fi
  done
fi

# Non-fatal: an INCOMPLETE snapshot must still be recorded and still update status.json,
# so the failure is visible rather than aborting the run and leaving stale status behind.
say "verify"
VERIFY_OK=1
python3 verify/verify.py --date "$DATE" || VERIFY_OK=0

say "parse · sources"
# DBT is collected at $DATE alongside myScheme, so in a real run its archive is always
# there. Under --skip-collect it is there only if some earlier run collected that same
# date, and reporting its absence as a failed step would train the operator to read red as
# noise -- which is the exact habit step() exists to prevent. So the two causes are named
# apart: no archive because collection was skipped is a consequence of the flag, and no
# archive on a run that DID collect is a real failure. Neither is allowed to pass silently,
# because a missing DBT archive means the DBT half of the registry is last month's.
if [ "$SKIP_COLLECT" = "1" ] && [ ! -d "archive/dbt/$DATE" ]; then
  echo "  no DBT archive for $DATE and --skip-collect was passed, so none was made."
  echo "  the registry's DBT half is whatever data/dbt.json already holds. NOT re-parsed."
else
  step "parse/dbt" python3 parse/dbt.py --date "$DATE"
fi
step "parse/budget" python3 parse/budget.py --year "$CYCLE_YEAR"
step "parse/outcome" python3 parse/outcome.py --year "$CYCLE_YEAR"
# No --date: the CAG crawl is stamped with its own date and is not tied to the myScheme
# snapshot, so passing this run's date asks it for an archive that does not exist.
step "parse/cag" python3 parse/cag.py

# States are parsed whether or not the myScheme snapshot verified, because they are
# derived from their own archives and nothing about a throttled myScheme crawl makes the
# Karnataka budget less true. Their absence claims are not, and those wait below.
say "parse · states"
for st in karnataka andhra kerala tamilnadu maharashtra odisha westbengal \
          telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh \
            chhattisgarh; do
  step "parse/$st" python3 "parse/$st.py"
done

# The legibility scoreboard, which is the only thing here that reads EVERY state at once.
# It runs after the state parsers because it checks each state's hand-entered verdicts
# against that state's own output. A disagreement between the survey table and the parsed
# data means one of them is wrong, and publishing either as fact before a person has
# decided which is the failure mode it exists to stop.
#
# Recorded rather than fatal, for the same reason as everything else here, with one thing
# a reader of the output has to know: if this fails, data/legibility.json is LAST month's
# and the site's state scoreboard will be built from it. The run exits non-zero and names
# the step; that is the signal to look before trusting the scoreboard.
step "parse/legibility" python3 parse/legibility.py

if [ "$VERIFY_OK" = "1" ]; then
  say "parse · myScheme"
  python3 parse/explode.py --date "$DATE"
  python3 parse/checks.py --snapshot "$DATE"

  # Order is a dependency chain, not a preference. registry joins the four sources and
  # needs checks.json; classify scores the registry's budget lines; the state classifiers
  # decide absence against the myScheme records explode has just written.
  say "parse · union registry"
  python3 parse/registry.py
  # The CAG join needs the registry, which is why it is here and not in the sources stage
  # beside parse/cag.py. Reading last month's registry.json would publish a join that looks
  # current and is not.
  step "parse/cag_join" python3 parse/cag_join.py
  python3 parse/classify.py
  # Every state has one now. A classifier that fails is a state that stops publishing
  # absence claims, which the run must SAY rather than either hide or die on.
  for st in karnataka andhra kerala tamilnadu maharashtra odisha westbengal \
            telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh \
            chhattisgarh; do
    step "classify_$st" python3 "parse/classify_$st.py"
  done
  # Sector runs after the state parsers and before the site, because it classifies exactly
  # the rows those produce and the ones the union registry holds with no myScheme record.
  step "parse/sector" python3 parse/sector.py

  say "enrich"
  step "enrich/budget" python3 enrich/budget.py --year "$CYCLE_YEAR"
  step "enrich/outcome" python3 enrich/outcome.py --year "$CYCLE_YEAR"
else
  echo "snapshot is INCOMPLETE — skipping everything downstream of it, as the design requires."
fi

# The change feed reads two archived snapshots and never the working tree, so it is safe
# after an INCOMPLETE run: it will refuse to diff against the bad snapshot itself.
say "changes"
step "parse/changes" python3 parse/changes.py

# AFTER the classifiers and after changes, because it reads what they concluded. The
# watchlist is the only file here with a MEMORY: it reads its own previous output, keeps the
# date each accusation was first made, and checks whether the portal has started listing it.
# That makes it the one thing in this repository that measures whether publishing an
# omission does anything, and it only works if it runs every cycle. A missed month is a hole
# in the record that cannot be filled in afterwards.
step "parse/watchlist" python3 parse/watchlist.py --date "$DATE"

# AFTER every classifier and before the build, because it checks what they concluded and
# the site is what publishes it. Three bugs in one day were a ratio computed over one
# population and labelled with another, which is the exact error this register documents in
# government sources. Publishing that while pointing at it would end the argument.
step "parse/ratios" python3 parse/ratios.py

say "build"
python3 site/build.py

# What the archive costs, printed every run so its growth is never a surprise. The archive
# is the evidence and stays in git, so it only grows; the question is when that stops being
# free. Measured 2026-09-05: 709 MB, of which 676 MB is the fifteen state budget books.
# Those are ANNUAL, so one full re-collection lands per cycle, and the monthly sources add
# about 111 MB a year on top. That is roughly 790 MB a year: past GitHub's 1 GB warning
# inside a year and into the 5 GB range where they ask you to reduce in about five.
#
# Nothing is restructured for that yet, on purpose. git-lfs needs paid data packs above
# 1 GB and a split archive repository costs the property that makes this one auditable,
# that the code and the bytes it read are one checkout. Both are worth doing when the
# number says so and not before. The number is here so that judgement is made against it.
say "archive"
python3 - <<'EOF'
import os
tot = sum(os.path.getsize(os.path.join(r, f))
          for r, _, fs in os.walk("archive") for f in fs)
print(f"  archive/ holds {tot / 1024**3:.2f} GB across "
      f"{sum(len(fs) for _, _, fs in os.walk('archive')):,} files")
if tot > 1024**3:
    print("  past 1 GB. GitHub warns here; see the note in run.sh before it reaches 5.")
EOF

echo
if [ "${#FAILED[@]}" -gt 0 ]; then
  printf '\033[31m%d step(s) failed:\033[0m\n' "${#FAILED[@]}"
  for f in ${FAILED[@]+"${FAILED[@]}"}; do echo "    $f"; done
fi
if [ "${#STOPPED[@]}" -gt 0 ]; then
  printf '\033[33m%d collector(s) ran out of time:\033[0m\n' "${#STOPPED[@]}"
  for f in ${STOPPED[@]+"${STOPPED[@]}"}; do echo "    $f"; done
fi

# What this run concluded, for --if-needed to read next time. Only a run with nothing
# failed, nothing stopped and a verified snapshot is ok; anything less is run again.
# A --limit smoke run never is, so it can never stand in for a real month. A
# --skip-collect re-derive says nothing about collection, so it leaves run.json alone.
[ "$SKIP_COLLECT" = "0" ] && python3 - "$DATE" "$VERIFY_OK" "${#LIMIT[@]}" "${#FAILED[@]}" \
  ${FAILED[@]+"${FAILED[@]}"} ${STOPPED[@]+"${STOPPED[@]}"} <<'EOF'
import json, sys
from datetime import datetime, timezone
date, verified, limited, nfail, rest = sys.argv[1], sys.argv[2] == "1", sys.argv[3] != "0", int(sys.argv[4]), sys.argv[5:]
failed, stopped = rest[:nfail], rest[nfail:]
with open("run.json", "w", encoding="utf-8") as fh:
    json.dump({"date": date, "finished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "verified": verified, "failed": failed, "stopped": stopped,
               "ok": verified and not failed and not stopped and not limited},
              fh, indent=1, sort_keys=True)
    fh.write("\n")
EOF

if [ "${#STOPPED[@]}" -gt 0 ]; then
  echo "the next run (./run.sh --resume-month) continues from here."
  exit 75                 # EX_TEMPFAIL: not broken, unfinished
fi

if [ "$VERIFY_OK" = "1" ] && [ "${#FAILED[@]}" -eq 0 ]; then
  echo "done. serve it with ./serve.sh"
  exit 0
fi
# The site is built either way and everything that worked is in it. The exit status is what
# a scheduler reads, so it has to be non-zero whenever any part of the month is missing.
if [ "$VERIFY_OK" != "1" ]; then
  echo "the snapshot did not verify. See status.json."
fi
echo "the site was built from what succeeded. Fix the above before trusting this month."
exit 1
