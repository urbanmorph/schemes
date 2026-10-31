"""
Every internal link in the built site resolves to a file in it.

SITE TOOLING (PLAN.md §7): reads site/_out only, never fetches. Used by check.sh before a
push and by .github/workflows/deploy.yml as the last gate before the public site.

Cloudflare Pages answers an unknown path with index.html and HTTP 200 unless 404.html
exists, so a dead link does not look like one: it serves the whole register under the
wrong URL, which is how 15,108 of them once stayed invisible.

    python3 tools/check_links.py [site/_out]
"""
import glob
import os
import re
import sys


def broken(out):
    """(pages read, {target: references}) for every href="/..." with no file behind it."""
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
    pages = glob.glob(os.path.join(out, "**", "*.html"), recursive=True)
    for p in pages:
        with open(p, encoding="utf-8") as fh:
            for h in re.findall(r'href="(/[^"#?]*)', fh.read()):
                if h not in have:
                    bad[h] = bad.get(h, 0) + 1
    return len(pages), bad


def main():
    pages, bad = broken(sys.argv[1] if len(sys.argv) > 1 else "site/_out")
    print(f"   {pages:,} pages, {len(bad)} broken link target(s)")
    for h, n in list(bad.items())[:5]:
        print(f"     {h}  ({n} references)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
