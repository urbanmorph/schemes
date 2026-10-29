#!/usr/bin/env bash
# ORCHESTRATION TEST (PLAN.md §7): exercises checkpoint.sh / run.sh only, never fetches.
# Tests checkpoint.sh against a throwaway repo and a local bare remote.
set -uo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)/checkpoint.sh"
T=$(mktemp -d); fails=0
trap 'rm -rf "$T"' EXIT
ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1"; fails=$((fails+1)); }
want() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (want '$3', got '$2')"; fi; }

export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q --bare "$T/remote.git"
git clone -q "$T/remote.git" "$T/a" 2>/dev/null
cd "$T/a" && git checkout -q -b main || exit 1
cp "$SRC" . && mkdir -p archive/myscheme/2026-09-03 && echo old > archive/myscheme/2026-09-03/details
echo '{}' > status.json && git add -A && git commit -qm base && git push -q origin main

# a run in progress: new snapshot bytes, a CAG walk that cannot resume, a run.json
mkdir -p archive/myscheme/2026-10-03 archive/cag/2026-10-03
echo part1 > archive/myscheme/2026-10-03/details
echo page > archive/cag/2026-10-03/page-000
echo '{"ok":false}' > run.json

out=$(./checkpoint.sh save wip/collect-2026-10)
want "first save pushes" "$(echo "$out" | grep -c pushed)" 1
want "main is untouched" "$(git rev-parse HEAD)" "$(git rev-parse origin/main)"
want "nothing staged on main" "$(git diff --cached --name-only | wc -l | tr -d ' ')" 0
files=$(git ls-tree -r --name-only "$(git ls-remote "$T/remote.git" refs/heads/wip/collect-2026-10 | cut -f1)")
want "snapshot bytes saved" "$(echo "$files" | grep -c 'archive/myscheme/2026-10-03/details')" 1
want "unresumable CAG walk not saved" "$(echo "$files" | grep -c archive/cag)" 0
want "run.json saved" "$(echo "$files" | grep -c '^run.json$')" 1

out=$(./checkpoint.sh save wip/collect-2026-10)
want "unchanged save does not push" "$(echo "$out" | grep -c pushed)" 0
echo part2 >> archive/myscheme/2026-10-03/details
out=$(./checkpoint.sh save wip/collect-2026-10)
want "changed save pushes again" "$(echo "$out" | grep -c pushed)" 1

# main moves on after the checkpoint: someone corrects last month's snapshot
git stash -q -u
echo corrected > archive/myscheme/2026-09-03/details
git commit -qam "correct September" && git push -q origin main
git stash pop -q

# the next day: a fresh checkout of main, as a runner gets
git clone -q --depth=1 --branch main "file://$T/remote.git" "$T/b" 2>/dev/null && cd "$T/b" || exit 1
./checkpoint.sh restore wip/collect-2026-10 >/dev/null
want "restore brings back the snapshot" "$(cat archive/myscheme/2026-10-03/details 2>/dev/null | tr '\n' ' ')" "part1 part2 "
want "restore keeps what main changed after the checkpoint" "$(cat archive/myscheme/2026-09-03/details)" "corrected"
want "restore does not bring run.json (a stale verdict)" "$([ -f run.json ] && echo yes || echo no)" "no"
want "restore stages nothing" "$(git diff --cached --name-only | wc -l | tr -d ' ')" 0
out=$(./checkpoint.sh restore wip/collect-2099-01); rc=$?
want "restore with no branch is a no-op that succeeds" "$rc" 0

out=$(./checkpoint.sh drop wip/collect-2026-10)
want "drop removes the branch" "$(git ls-remote "$T/remote.git" refs/heads/wip/collect-2026-10 | wc -l | tr -d ' ')" 0
out=$(./checkpoint.sh drop wip/collect-2026-10); rc=$?
want "dropping a missing branch succeeds" "$rc" 0

[ "$fails" = 0 ] && echo "all checkpoint tests pass" || { echo "$fails failed"; exit 1; }
