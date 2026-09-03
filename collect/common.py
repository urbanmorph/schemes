"""
Shared HTTP + archive primitives for the collectors.

FROZEN CODE. Read PLAN.md §7 before editing anything in collect/.

The repair agent may edit parse/. It must never edit collect/. The value of this
project is a *comparable* time series: a collector that breaks leaves a hole you can
see and date, while a collector that quietly adapts leaves a seam you cannot. Changes
here alter what every future snapshot means, and cannot be replayed against the
archive to find out what changed. Parser changes can.

Rules encoded here, each with a reason:

  - Never HEAD. indiabudget.gov.in returns 404 to HEAD and 200 to GET; dbtbharat and
    myscheme return 403/405. Measured: HEAD misclassifies 18% of live government URLs.
  - Always send a browser User-Agent, and identify the crawler honestly alongside it.
  - 401 from myScheme means rate-limited, not rotated. Confirmed 2026-08-30: after ~15
    rapid requests the API 401s, re-extracting the key from the JS bundle returns a
    byte-identical key, and the original works again ~3 minutes later. Callers must
    re-extract and COMPARE before treating a 401 as a key rotation.
  - Raw bytes are written before anything is parsed, so a parser bug can never cost a
    snapshot.
"""

import gzip
import hashlib
import json
import os
import random
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

# A browser string with an honest identification appended. The suffix is the point:
# these are public services and whoever runs them should be able to see who we are and
# tell us to stop.
BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
UA = BROWSER + " (+https://github.com/urbanmorph/schemes; monthly archival crawler)"

# Hosts that refuse to be told who is calling.
#
# indiabudget.gov.in returns 403 to *any* User-Agent that is not a bare browser string.
# Measured 2026-08-31: the plain string returns 200 in 0.12s, while the same string plus
# " crawler", plus "(+https://github.com/urbanmorph/schemes)", or plus the full honest
# suffix all return 403. It is matching on the trailing tokens, not on any bot keyword.
#
# So identification is dropped for this host and only this host. Recording the exception
# here, rather than quietly weakening the global UA, keeps the politeness default intact
# and makes the compromise reviewable. Three annual requests remain well-mannered either
# way; robots.txt is still honoured.
UA_BY_HOST = {
    "www.indiabudget.gov.in": BROWSER,
    "indiabudget.gov.in": BROWSER,
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Some government servers ship a broken certificate chain. finance.karnataka.gov.in
# serves a leaf issued by "GlobalSign GCC R46 OV TLS CA 2025" and then attaches the 2018
# intermediate, which signs nothing in that chain. Browsers paper over this by fetching
# the real intermediate from the leaf's Authority Information Access extension; Python
# does not do AIA fetching, so a certificate that is perfectly valid fails here with
# "unable to get local issuer certificate".
#
# The fix is to carry the missing link, never to stop checking. The chain still has to
# reach a root in the system store, so a host listed here is verified exactly as strictly
# as any other. Turning verification off for a source whose whole value is provenance
# would be the wrong trade in the wrong direction.
CA_BY_HOST = {
    "finance.karnataka.gov.in": "globalsign-gcc-r46-ov-tls-ca-2025.pem",
    # The same GlobalSign GCC R46 fault, on a second state. Registered here rather than
    # from collect/jharkhand.py, which had to reach into this module at import time to get
    # a fetch at all: a frozen collector poking a shared table is a worse precedent than
    # one more line in the table it pokes.
    "finance.jharkhand.gov.in": "globalsign-gcc-r46-ov-tls-ca-2025.pem",
}

_CTX = ssl.create_default_context()
_CTX_BY_HOST = {}


def _context(host):
    if host not in CA_BY_HOST:
        return _CTX
    if host not in _CTX_BY_HOST:
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(
            cafile=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "certs", CA_BY_HOST[host]))
        _CTX_BY_HOST[host] = ctx
    return _CTX_BY_HOST[host]


class Fetched:
    """One HTTP response. `ok` means we got bytes, not that they are meaningful."""

    __slots__ = ("url", "status", "body", "elapsed", "attempts")

    def __init__(self, url, status, body, elapsed, attempts):
        self.url, self.status, self.body = url, status, body
        self.elapsed, self.attempts = elapsed, attempts

    @property
    def ok(self):
        return isinstance(self.status, int) and 200 <= self.status < 400

    @property
    def sha256(self):
        return hashlib.sha256(self.body or b"").hexdigest()

    def json(self):
        return json.loads(self.body)


def fetch(url, headers=None, timeout=45, retries=5, pace=0.0):
    """GET a URL with backoff. Never HEAD. Returns Fetched; never raises on HTTP status.

    Backs off on 401/429/5xx — for myScheme all three mean "slow down". The caller
    decides whether a persistent 401 is a rotated key (see myscheme.resolve_key).
    """
    host = urllib.parse.urlsplit(url).netloc.lower()
    h = {"User-Agent": UA_BY_HOST.get(host, UA)}
    if headers:
        h.update(headers)
    started = time.time()
    last_status = None

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=h, method="GET")
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=_context(host)) as r:
                body = r.read()
                if pace:
                    time.sleep(pace)
                return Fetched(url, r.status, body, time.time() - started, attempt)
        except urllib.error.HTTPError as e:
            last_status = e.code
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            # 401/429/5xx are usually "slow down" and are worth the full retry budget.
            # 403 is usually a policy decision about who we are — retrying a UA block
            # just burns twenty minutes to arrive at the same 403, so it gets two
            # attempts in case it is a transient WAF rule, then gives up.
            budget = 2 if e.code == 403 else retries
            if (e.code in (401, 429) or e.code >= 500 or e.code == 403) and attempt < budget:
                _backoff(attempt)
                continue
            return Fetched(url, e.code, body, time.time() - started, attempt)
        except urllib.error.URLError as e:
            reason = str(getattr(e, "reason", e))
            low = reason.lower()
            if "name or service" in low or "not known" in low or "nodename" in low:
                # A resolver saying "name not known" usually means the host does not
                # exist, which is why this used to give up at once. Under a long paced
                # walk it means something else: a resolver under sustained sequential
                # queries returns transient failures, and cag.gov.in produced 394 of them
                # in a row on a catalogue walk that had just fetched six pages fine and
                # answered every request normally a minute later.
                #
                # Giving up without a retry turned that into a whole source recorded as
                # dead, which for an unattended monthly job is the difference between a
                # blip and a missing month. Retried like any other transient failure, and
                # only reported as DNS once the budget is spent, so a host that really has
                # gone away still resolves to the same verdict a little more slowly.
                last_status = "DNS"
                if attempt < retries:
                    _backoff(attempt)
                    continue
                return Fetched(url, "DNS", b"", time.time() - started, attempt)
            last_status = "TIMEOUT" if "timed out" in low else "CONN"
            if attempt < retries:
                _backoff(attempt)
                continue
            return Fetched(url, last_status, b"", time.time() - started, attempt)
        except Exception:
            last_status = "ERR"
            if attempt < retries:
                _backoff(attempt)
                continue
            return Fetched(url, "ERR", b"", time.time() - started, attempt)

    return Fetched(url, last_status or "ERR", b"", time.time() - started, retries)


def _backoff(attempt):
    """Exponential with jitter. myScheme's throttle cleared in ~3 min when measured."""
    time.sleep(min(90, (2 ** attempt) * 2) + random.uniform(0, 1.5))


# --------------------------------------------------------------- error-shape guard

# A 200 is not proof of a real payload: a throttle or a WAF challenge can arrive with
# any status. Any archived body matching one of these is treated as a failed fetch,
# so it can never be committed as if it were data. PLAN.md §8, assertion 4.
ERROR_SHAPES = (
    b'{"message":"Unauthorized"}',
    b'{"message":"Forbidden"}',
    b"Missing Authentication Token",
    b"<title>Just a moment",          # Cloudflare interstitial
    b"cf-browser-verification",
    b"Attention Required! | Cloudflare",
)


def looks_like_error(body):
    if not body:
        return "empty body"
    head = body[:2048]
    for shape in ERROR_SHAPES:
        if shape in head:
            return shape.decode("utf-8", "replace")[:60]
    return None


# --------------------------------------------------------------- archive writing

def write_json(relpath, obj):
    """Pretty, key-sorted, trailing newline — so git diffs are line-wise and readable.

    Stability matters more than compactness here: /changes is a git diff, and an
    unstable key order would make every field look changed every month.
    """
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return path


def write_raw_gz(relpath, body):
    """Immutable raw bytes, gzipped. The audit trail behind every parsed value."""
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(body)
    return path


def read_json(relpath, default=None):
    path = os.path.join(ROOT, relpath)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())
