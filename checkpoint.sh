#!/usr/bin/env bash
# Save and restore an unfinished month's archive on a side branch, so a run that is
# stopped or killed loses at most the last ten minutes. ORCHESTRATION (PLAN.md §7).
#
#   ./checkpoint.sh save    wip/collect-2026-10   push archive/ + status.json + run.json
#   ./checkpoint.sh restore wip/collect-2026-10   bring the branch's archive back
#   ./checkpoint.sh drop    wip/collect-2026-10   delete it once main has the snapshot
#
# Why a side branch and not main. main is the record: every snapshot on it is one a
# person can cite. Partial bytes pushed there every ten minutes would sit in its history
# forever, ~7 MB a time. A side branch holds them until the month's snapshot reaches main
# and is then deleted.
#
# save commits through a private index, so main's index, working tree and history are
# untouched, and it pushes only when the content differs from the last push. archive/cag
# is left out: that walk cannot resume, so a partial one is worth nothing to a restart.
#
# restore takes only archive/ files the branch added or changed. Not status.json or
# run.json: those are verdicts about a run that did not finish, and the run being resumed
# writes its own.
set -euo pipefail
cd "$(dirname "$0")"

cmd="${1:-}"; branch="${2:-}"
[ -n "$cmd" ] && [ -n "$branch" ] || { sed -n '5,7p' "$0" >&2; exit 2; }
gitdir="$(git rev-parse --git-dir)"
remote_has() { git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; }

case "$cmd" in
save)
  idx="$gitdir/checkpoint-index"
  last="$gitdir/checkpoint-${branch//\//-}"
  GIT_INDEX_FILE="$idx" git read-tree HEAD
  paths=(archive ':(exclude)archive/cag' status.json)
  [ -f run.json ] && paths+=(run.json)
  GIT_INDEX_FILE="$idx" git add -A -- "${paths[@]}"
  tree="$(GIT_INDEX_FILE="$idx" git write-tree)"
  if [ "$tree" = "$(git rev-parse 'HEAD^{tree}')" ] || [ "$tree" = "$(cat "$last" 2>/dev/null)" ]; then
    echo "  checkpoint: nothing new since the last one"
    exit 0
  fi
  commit="$(git commit-tree "$tree" -p HEAD -m "checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)")"
  git push -q -f origin "$commit:refs/heads/$branch"
  echo "$tree" > "$last"
  echo "  checkpoint: pushed $(git diff --name-only HEAD "$commit" | wc -l | tr -d ' ') changed file(s) to $branch"
  ;;
restore)
  if ! remote_has; then
    echo "  no $branch: starting from main"
    exit 0
  fi
  git fetch -q --depth=1 origin "$branch"
  files=()
  while IFS= read -r f; do files+=("$f"); done < <(
    git diff --name-only --diff-filter=AM HEAD FETCH_HEAD -- archive)
  if [ "${#files[@]}" -gt 0 ]; then
    git restore --source=FETCH_HEAD --worktree -- "${files[@]}"
  fi
  echo "  restored ${#files[@]} archive file(s) from $branch"
  ;;
drop)
  if remote_has; then
    git push -q origin --delete "$branch"
    echo "  dropped $branch"
  fi
  ;;
*) sed -n '5,7p' "$0" >&2; exit 2 ;;
esac
