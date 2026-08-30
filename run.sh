#!/usr/bin/env bash
# Full monthly pipeline, in the order the design requires.
#
#   ./run.sh                 collect → verify → parse → build   (today's date)
#   ./run.sh --date 2026-08-30
#   ./run.sh --skip-collect  re-derive everything from the existing archive
#   ./run.sh --limit 20      smoke test (deliberately marked INCOMPLETE)
#
# The ordering is not a convenience. Collection writes raw bytes and nothing else;
# verification decides whether those bytes are a publishable snapshot; only then does
# anything parse them. A parse that ran before verification could build a change feed
# out of a throttled half-snapshot and publish "100 schemes removed this month".
set -euo pipefail
cd "$(dirname "$0")"

DATE="$(date -u +%Y-%m-%d)"
SKIP_COLLECT=0
LIMIT=()
PACE=0.7

while [ $# -gt 0 ]; do
  case "$1" in
    --date)         DATE="$2"; shift 2 ;;
    --skip-collect) SKIP_COLLECT=1; shift ;;
    --limit)        LIMIT=(--limit "$2"); shift 2 ;;
    --pace)         PACE="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

if [ "$SKIP_COLLECT" = "0" ]; then
  say "collect · myScheme ($DATE)"
  python3 collect/myscheme.py --date "$DATE" --pace "$PACE" "${LIMIT[@]+"${LIMIT[@]}"}"
  say "collect · DBT Bharat"
  python3 collect/dbt.py --date "$DATE"
fi

# Non-fatal: an INCOMPLETE snapshot must still be recorded and still update status.json,
# so the failure is visible rather than aborting the run and leaving stale status behind.
say "verify"
VERIFY_OK=1
python3 verify/verify.py --date "$DATE" || VERIFY_OK=0

say "parse"
python3 parse/dbt.py --date "$DATE" || true
if [ "$VERIFY_OK" = "1" ]; then
  python3 parse/explode.py --date "$DATE"
  python3 parse/checks.py --snapshot "$DATE"
else
  echo "snapshot is INCOMPLETE — skipping explode/checks, as the design requires."
fi

say "build"
python3 site/build.py

echo
if [ "$VERIFY_OK" = "1" ]; then
  echo "done. serve it with ./serve.sh"
else
  echo "done, but the snapshot did not verify. See status.json."
  exit 1
fi
