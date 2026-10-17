#!/usr/bin/env bash
# ORCHESTRATION TEST (PLAN.md §7): exercises checkpoint.sh / run.sh only, never fetches.
# End-to-end test of run.sh's chunking, with every collector and parser stubbed.
# Runs in a throwaway git worktree; nothing fetches, nothing touches the real checkout.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SP="$(mktemp -d)"
W="$SP/wt-e2e"; fails=0
want() { if [ "$2" = "$3" ]; then echo "  ok   $1"; else echo "  FAIL $1 (want '$3', got '$2')"; fails=$((fails+1)); fi; }

git -C "$REPO" worktree remove --force "$W" 2>/dev/null; rm -rf "$W"
git -C "$REPO" worktree add -q --detach "$W" HEAD
cp "$REPO/run.sh" "$REPO/progress.py" "$REPO/checkpoint.sh" "$W/"
cd "$W" || exit 1

# timeout(1) stand-in with GNU semantics: -k GRACE SECS cmd..., exit 124 on timeout
mkdir -p "$SP/bin"
cat > "$SP/bin/timeout" <<'EOF'
#!/usr/bin/env python3
import signal, subprocess, sys
a = sys.argv[1:]; grace = 0
if a[0] == "-k": grace, a = float(a[1]), a[2:]
secs, cmd = float(a[0]), a[1:]
p = subprocess.Popen(cmd)
try:
    sys.exit(p.wait(timeout=secs))
except subprocess.TimeoutExpired:
    p.send_signal(signal.SIGTERM)
    try: p.wait(timeout=grace)
    except subprocess.TimeoutExpired: p.kill(); p.wait()
    sys.exit(124)
EOF
chmod +x "$SP/bin/timeout"
export PATH="$SP/bin:$PATH" BUDGET_UNIT=1

# Every parser, enricher, verifier and the build: succeed, do nothing.
for f in parse/*.py enrich/*.py verify/verify.py site/build.py; do echo 'import sys; sys.exit(0)' > "$f"; done
# myScheme: one record a second up to NEED, resuming from what is on disk, like the real one.
cat > collect/myscheme.py <<'EOF'
import argparse, json, os, time
ap = argparse.ArgumentParser(); ap.add_argument("--date"); ap.add_argument("--pace"); ap.add_argument("--limit")
a = ap.parse_args(); d = f"archive/myscheme/{a.date}"; os.makedirs(d, exist_ok=True)
NEED = int(os.environ.get("NEED", "6")); f = f"{d}/details"
have = sum(1 for _ in open(f)) if os.path.exists(f) else 0
def man(done): json.dump({"finished": "x" if done else None, "in_progress": not done, "details_expected": NEED,
                          "details_written": have, "pages_expected": 1, "pages_written": 1}, open(f"{d}/_manifest.json", "w"))
while have < NEED:
    time.sleep(1); open(f, "a").write("rec\n"); have += 1; man(False)
man(True)
EOF
cat > collect/dbt.py <<'EOF'
import argparse, json, os
ap = argparse.ArgumentParser(); ap.add_argument("--date"); a = ap.parse_args()
os.makedirs(f"archive/dbt/{a.date}", exist_ok=True)
json.dump({"error_count": 0}, open(f"archive/dbt/{a.date}/_manifest.json", "w"))
EOF
cat > collect/cag.py <<'EOF'
import argparse, json, os, time
ap = argparse.ArgumentParser(); ap.add_argument("--date"); a = ap.parse_args()
d = f"archive/cag/{a.date}"; os.makedirs(d, exist_ok=True); open(f"{d}/page-000.html.gz", "w").write("x")
time.sleep(int(os.environ.get("CAG_SECS", "0")))
json.dump({"complete": True}, open(f"{d}/_manifest.json", "w"))
EOF
# Annual sources: mark themselves held for the cycle, as the real manifests do.
for f in collect/*.py; do
  case "$f" in collect/myscheme.py|collect/dbt.py|collect/cag.py|collect/common.py) continue ;; esac
  st=$(basename "$f" .py)
  cat > "$f" <<EOF
import argparse, json, os
ap = argparse.ArgumentParser(); ap.add_argument("--date"); ap.add_argument("--cycle"); ap.add_argument("--year")
a = ap.parse_args(); d = "archive/$st/" + (a.year or a.date); os.makedirs(d, exist_ok=True)
json.dump({"cycle": "2026-27"}, open(d + "/_manifest.json", "w"))
EOF
done
rm -rf archive/myscheme/2026-10-* run.json

# Every file under archive/ plus run.json, with its modification time: a run that writes
# anything at all changes this.
fingerprint() {
  python3 - <<'EOF'
import hashlib, os
files = [os.path.join(r, f) for r, _, fs in os.walk("archive") for f in fs] + ["run.json"]
print(hashlib.sha256(repr(sorted((f, os.stat(f).st_mtime_ns) for f in files)).encode()).hexdigest())
EOF
}

DAY1=$(date -u +%Y-%m-%d)

echo "-- attempt 1: myScheme needs 6s, the run has 6s for collection"
NEED=6 RESERVE_MIN=2 ./run.sh --resume-month --if-needed --deadline-min 8 > "$SP/e2e-1.log" 2>&1; rc=$?
want "an unfinished run exits 75" "$rc" 75
want "myScheme was stopped, not failed" "$(grep -c 'STOPPED.*collect/myscheme' "$SP/e2e-1.log")" 1
got=$(wc -l < "archive/myscheme/$DAY1/details" | tr -d ' ')
want "what it fetched stays on disk" "$([ "$got" -ge 3 ] && [ "$got" -lt 6 ] && echo yes || echo "no ($got)")" yes
want "sources it had no time for are deferred" "$(grep -c 'DEFERRED' "$SP/e2e-1.log" | awk '{print ($1>0)?"yes":"no"}')" yes
want "run.json says not ok" "$(python3 -c "import json;print(json.load(open('run.json'))['ok'])")" False

echo "-- attempt 2: continues the same snapshot, CAG hangs past its budget"
NEED=6 CAG_SECS=100 RESERVE_MIN=2 ./run.sh --resume-month --if-needed --deadline-min 60 > "$SP/e2e-2.log" 2>&1; rc=$?
want "the same snapshot date is resumed" "$(grep -c "collect · myScheme ($DAY1)" "$SP/e2e-2.log")" 1
want "myScheme finished from where it stopped" "$(wc -l < "archive/myscheme/$DAY1/details" | tr -d ' ')" 6
want "a stopped CAG walk is discarded" "$([ -d "archive/cag/$DAY1" ] && echo kept || echo gone)" gone
want "still exits 75 while CAG is unfinished" "$rc" 75

echo "-- attempt 3: everything left fits"
NEED=6 RESERVE_MIN=2 ./run.sh --resume-month --if-needed --deadline-min 60 > "$SP/e2e-3.log" 2>&1; rc=$?
want "finished myScheme is skipped" "$(grep -c 'every detail for .* is archived, skipping' "$SP/e2e-3.log")" 1
want "finished DBT is skipped" "$(grep -c 'DBT for .* is archived, skipping' "$SP/e2e-3.log")" 1
want "a clean run exits 0" "$rc" 0
want "run.json says ok" "$(python3 -c "import json;print(json.load(open('run.json'))['ok'])")" True

echo "-- attempt 4: the month is done"
before=$(fingerprint)
./run.sh --resume-month --if-needed --deadline-min 60 > "$SP/e2e-4.log" 2>&1; rc=$?
after=$(fingerprint)
want "a repeat exits 0" "$rc" 0
want "a repeat says there is nothing to do" "$(grep -c 'nothing to do' "$SP/e2e-4.log")" 1
want "a repeat changes no file" "$before" "$after"

cd "$REPO" && git worktree remove --force "$W"
[ "$fails" = 0 ] && echo "all e2e tests pass" || { echo "$fails failed"; exit 1; }
