#!/usr/bin/env bash
# Build the site and serve it locally. Local only — this deploys nowhere.
#
#   ./serve.sh              build + serve on http://127.0.0.1:8788
#   ./serve.sh --port 9000  another port
#   ./serve.sh --build      build only, don't serve
#
# Binds to 127.0.0.1 explicitly, never 0.0.0.0, so it is not reachable from the network.
set -euo pipefail
cd "$(dirname "$0")"

port=8788
build_only=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port)  port="$2"; shift 2 ;;
    --build) build_only=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

echo "building…"
python3 site/build.py

if [ "$build_only" = "1" ]; then
  echo "built site/_out"
  exit 0
fi

url="http://127.0.0.1:$port/"
echo
echo "serving $url   (ctrl-c to stop)"
command -v open >/dev/null && (sleep 1 && open "$url" >/dev/null 2>&1 &) || true
exec python3 -m http.server "$port" --bind 127.0.0.1 --directory site/_out
