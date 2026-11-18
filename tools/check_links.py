"""
Every internal link in the built site resolves to a file in it, and every top-level page
is in sitemap.xml.

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
from urllib.parse import urlsplit


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


# Top-level pages that are not for a crawler: the not-found page and Search Console's
# ownership file.
NOT_FOR_SITEMAP = re.compile(r"404\.html|google[0-9a-f]+\.html")


def unlisted(out):
    """Top-level pages that sitemap.xml leaves out. /releases once was: live, linked from
    llms.txt, and missing from the list a crawler is handed."""
    with open(os.path.join(out, "sitemap.xml"), encoding="utf-8") as fh:
        listed = {urlsplit(u).path.strip("/") or "index"
                  for u in re.findall(r"<loc>([^<]+)</loc>", fh.read())}
    return sorted(f"/{f[:-5]}" for f in os.listdir(out)
                  if f.endswith(".html") and not NOT_FOR_SITEMAP.fullmatch(f)
                  and f[:-5] not in listed)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "site/_out"
    pages, bad = broken(out)
    print(f"   {pages:,} pages, {len(bad)} broken link target(s)")
    for h, n in list(bad.items())[:5]:
        print(f"     {h}  ({n} references)")
    missing = unlisted(out)
    print(f"   {len(missing)} top-level page(s) missing from sitemap.xml")
    for u in missing:
        print(f"     {u}")
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    main()
