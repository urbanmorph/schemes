#!/usr/bin/env bash
# Everything that can be checked without the network, in one command.
#
# There is no CI here beyond the monthly collection job, and that job is the wrong place
# to find out you broke something: it runs once a month and its failure costs a snapshot.
# Run this before you push. It touches no government server and takes a few seconds.
set -uo pipefail
cd "$(dirname "$0")"

FAILED=()
step() {
  local label="$1"; shift
  printf '\033[1m%s\033[0m\n' "-- $label"
  if ! "$@"; then
    FAILED+=("$label")
    printf '   \033[31m!! FAILED\033[0m %s\n' "$label" >&2
  fi
}

# 1. Everything imports and parses. Catches the commonest breakage by far: an edit to a
#    1,200-line classifier that leaves a syntax error nothing notices until the 3rd.
step "python syntax" python3 - <<'PY'
import ast, pathlib, sys
bad = 0
for p in sorted(pathlib.Path(".").rglob("*.py")):
    if any(x in p.parts for x in (".git", "__pycache__", "site")) and p.name != "build.py":
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"   {p}:{e.lineno}: {e.msg}"); bad += 1
print(f"   {bad} file(s) with a syntax error")
sys.exit(1 if bad else 0)
PY

# 2. The self-tests. Each of these exists because the thing it tests was wrong once and
#    the failure was invisible in the output.
step "parse/match.py self-tests"    python3 parse/match.py
step "parse/krutidev.py self-tests" python3 parse/krutidev.py
[ -f parse/devanagari.py ] && step "parse/devanagari.py self-tests" python3 parse/devanagari.py

# 3. Every published ratio divides two counts of the same list. See PLAN.md §4.
step "parse/ratios.py" python3 parse/ratios.py

# 4. The site builds, and every internal link in it resolves. A dead link here serves the
#    whole register under the wrong URL with HTTP 200, which is how 15,108 of them once
#    stayed invisible.
step "site builds" python3 site/build.py
step "internal links resolve" python3 - <<'PY'
import os, re, glob, sys
out = "site/_out"
have = set()
for r, _, fs in os.walk(out):
    for f in fs:
        p = os.path.relpath(os.path.join(r, f), out)
        have.add("/" + p)
        if p.endswith(".html"):
            have.add("/" + p[:-5])
            if p == "index.html":
                have.add("/")
bad = {}
pages = glob.glob(out + "/**/*.html", recursive=True)
for p in pages:
    for h in re.findall(r'href="(/[^"#?]*)', open(p, encoding="utf-8").read()):
        if h not in have:
            bad[h] = bad.get(h, 0) + 1
print(f"   {len(pages):,} pages, {len(bad)} broken link target(s)")
for h, n in list(bad.items())[:5]:
    print(f"     {h}  ({n} references)")
sys.exit(1 if bad else 0)
PY

echo
if [ "${#FAILED[@]}" -gt 0 ]; then
  printf '\033[31m%d check(s) failed:\033[0m\n' "${#FAILED[@]}"
  for f in "${FAILED[@]}"; do echo "    $f"; done
  exit 1
fi
printf '\033[32mall checks passed\033[0m\n'
