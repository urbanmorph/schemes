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
  python3 collect/cag.py --date "$DATE" || true

  say "collect · annual sources"
  if have_annual "archive/budget/$CYCLE_YEAR"; then
    echo "  Union Budget $CYCLE_YEAR already archived, skipping"
  else
    python3 collect/budget.py --year "$CYCLE_YEAR"
  fi
  for st in karnataka andhra; do
    if have_annual "archive/$st/*"; then
      echo "  $st budget already archived, skipping"
    else
      python3 "collect/$st.py" --cycle "$STATE_CYCLE" --date "$DATE"
    fi
  done
fi

# Non-fatal: an INCOMPLETE snapshot must still be recorded and still update status.json,
# so the failure is visible rather than aborting the run and leaving stale status behind.
say "verify"
VERIFY_OK=1
python3 verify/verify.py --date "$DATE" || VERIFY_OK=0

say "parse · sources"
python3 parse/dbt.py --date "$DATE" || true
python3 parse/budget.py --year "$CYCLE_YEAR" || true
python3 parse/outcome.py --year "$CYCLE_YEAR" || true
# No --date: the CAG crawl is stamped with its own date and is not tied to the myScheme
# snapshot, so passing this run's date asks it for an archive that does not exist.
python3 parse/cag.py || true

# States are parsed whether or not the myScheme snapshot verified, because they are
# derived from their own archives and nothing about a throttled myScheme crawl makes the
# Karnataka budget less true. Their absence claims are not, and those wait below.
say "parse · states"
python3 parse/karnataka.py || true
python3 parse/andhra.py || true
python3 parse/kerala.py || true

if [ "$VERIFY_OK" = "1" ]; then
  say "parse · myScheme"
  python3 parse/explode.py --date "$DATE"
  python3 parse/checks.py --snapshot "$DATE"

  # Order is a dependency chain, not a preference. registry joins the four sources and
  # needs checks.json; classify scores the registry's budget lines; the state classifiers
  # decide absence against the myScheme records explode has just written.
  say "parse · union registry"
  python3 parse/registry.py
  python3 parse/classify.py
  python3 parse/classify_karnataka.py || true
  [ -f parse/classify_andhra.py ] && python3 parse/classify_andhra.py || true

  say "enrich"
  python3 enrich/budget.py --year "$CYCLE_YEAR" || true
  python3 enrich/outcome.py --year "$CYCLE_YEAR" || true
else
  echo "snapshot is INCOMPLETE — skipping everything downstream of it, as the design requires."
fi

# The change feed reads two archived snapshots and never the working tree, so it is safe
# after an INCOMPLETE run: it will refuse to diff against the bad snapshot itself.
say "changes"
python3 parse/changes.py || true

say "build"
python3 site/build.py

echo
if [ "$VERIFY_OK" = "1" ]; then
  echo "done. serve it with ./serve.sh"
else
  echo "done, but the snapshot did not verify. See status.json."
  exit 1
fi
