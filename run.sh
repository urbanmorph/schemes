#!/usr/bin/env bash
# Full monthly pipeline, in the order the design requires.
#
#   ./run.sh                 collect → verify → parse → enrich → build   (today's date)
#   ./run.sh --date 2026-08-30
#   ./run.sh --skip-collect  re-derive everything from the existing archive
#   ./run.sh --limit 20      smoke test (deliberately marked INCOMPLETE)
#   ./run.sh --refresh-annual  re-fetch the annual sources even if this cycle is held
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

while [ $# -gt 0 ]; do
  case "$1" in
    --date)           DATE="$2"; shift 2 ;;
    --skip-collect)   SKIP_COLLECT=1; shift ;;
    --limit)          LIMIT=(--limit "$2"); shift 2 ;;
    --pace)           PACE="$2"; shift 2 ;;
    --refresh-annual) REFRESH_ANNUAL=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

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

# An annual document does not change between January and December, and re-fetching 20MB
# of state budget PDFs twelve times a year to watch them not change is rude to a source
# this project depends on. These collect once per cycle and are skipped once the archive
# holds them, which --refresh-annual overrides when a state republishes mid-year.
have_annual() { [ "$REFRESH_ANNUAL" = "0" ] && compgen -G "$1" > /dev/null; }

if [ "$SKIP_COLLECT" = "0" ]; then
  say "collect · myScheme ($DATE)"
  python3 collect/myscheme.py --date "$DATE" --pace "$PACE" "${LIMIT[@]+"${LIMIT[@]}"}"

  say "collect · DBT Bharat"
  python3 collect/dbt.py --date "$DATE"

  # The audit catalogue is append-mostly and grows a few reports a month, so unlike the
  # budgets it is collected every run. 281 paced requests, about nine minutes, and the
  # walk checks its own distinct-id count against the total the site prints, which is a
  # checksum an incremental crawl could not do.
  say "collect · CAG catalogue"
  step "collect/cag" python3 collect/cag.py --date "$DATE"

  say "collect · annual sources"
  if have_annual "archive/budget/$CYCLE_YEAR"; then
    echo "  Union Budget $CYCLE_YEAR already archived, skipping"
  else
    python3 collect/budget.py --year "$CYCLE_YEAR"
  fi
  for st in karnataka andhra kerala tamilnadu maharashtra odisha westbengal \
            telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh; do
    if have_annual "archive/$st/*"; then
      echo "  $st budget already archived, skipping"
    # Not every collector takes --cycle, and passing it to one that does not aborts the
    # whole run under `set -e`. A state takes it when the cycle is part of the ADDRESS of
    # its documents (Karnataka's index URL carries the financial year); a state that omits
    # it discovers the cycle from the page and asserts it, which is the same guarantee
    # reached the other way round. Asking the collector rather than keeping a second list
    # here means the two cannot drift.
    elif python3 "collect/$st.py" --help 2>/dev/null | grep -q -- "--cycle"; then
      python3 "collect/$st.py" --cycle "$STATE_CYCLE" --date "$DATE"
    else
      python3 "collect/$st.py" --date "$DATE"
    fi
  done
fi

# Non-fatal: an INCOMPLETE snapshot must still be recorded and still update status.json,
# so the failure is visible rather than aborting the run and leaving stale status behind.
say "verify"
VERIFY_OK=1
python3 verify/verify.py --date "$DATE" || VERIFY_OK=0

say "parse · sources"
step "parse/dbt" python3 parse/dbt.py --date "$DATE"
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
          telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh; do
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
            telangana punjab jharkhand tripura delhi haryana uttarakhand uttarpradesh; do
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

say "build"
python3 site/build.py

echo
if [ "${#FAILED[@]}" -gt 0 ]; then
  printf '\033[31m%d step(s) failed:\033[0m\n' "${#FAILED[@]}"
  for f in ${FAILED[@]+"${FAILED[@]}"}; do echo "    $f"; done
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
