"""
Derive the Chanakya byte-to-Devanagari table from the parallel corpus. NOT CONVERGED.

AGENT-EDITABLE (PLAN.md 7). Reads data/chhattisgarh/chanakya_corpus.json. Never fetches.
NOTHING CONSUMES ITS OUTPUT. It is checked in because the method works and the findings
below cost a day to establish; it is not checked in because it is finished.

WHERE IT STANDS. 6 of 114 corpus pairs decode exactly. That is not the number that
matters: the decoded text went from unreadable to Hindi a speaker would accept, and whole
names now come out right, "प्रशिक्षण", "बायोस्फियर", "का विकास", "बिगड़े वनों का सुधार".
The failures left are single glyphs with few examples in the corpus, not the systematic
faults that made the first passes gibberish. The bar for publishing 2,562 scheme names is
114 of 114 and it is not close enough yet to ship.

WHAT THE ENCODING IS, which took four wrong models to establish and is the real result:

  ONE BYTE IS ONE GLYPH, and a glyph is zero or more Unicode characters. There are no
  multi-byte codes. The first model assumed a flat character table and could not fit
  anything.

  THE TEXT IS IN GLYPH ORDER, not character order. The i-matra is drawn to the left of
  its consonant and stored there; the reph is drawn above a later consonant and stored
  after it. No monotonic alignment can fit that, which is why the second model scored
  zero on every pair. Both sides are put in glyph order before aligning and the result is
  reordered back afterwards.

  SOME CONSONANTS ARE DRAWN IN TWO PIECES, a left piece and a completing vertical stroke,
  and the same stroke glyph is also the aa-matra. That ambiguity is in the font, not in
  the extraction: a reader resolves it by knowing Hindi. It is resolved here by finding
  the left pieces statistically, they are followed by a stroke in 55% to 100% of their
  occurrences, and merging each with its follower into one token before alignment. Before
  this the aa-matra lost every time and का decoded as क.

  ो IS DRAWN AS THE AA-STROKE PLUS THE E-MATRA, and likewise ौ and ऑ. They are recombined
  after decoding.

WHAT WOULD FINISH IT. More corpus, first: this uses 114 pairs from 31 departments and the
join was filtered hard for clean rows, where 235 pairs and 44 departments exist. The
remaining errors are glyphs the corpus barely witnesses. Second, a held-out split, because
a table fitted and scored on the same 114 pairs proves less than it appears to.

THE BAR BEFORE ANY OF THIS REACHES THE SITE, and it is deliberately higher than the
statistics: every one of the corpus pairs decoding exactly, AND a sample of rows from
outside the corpus reading as Hindi to somebody who reads Hindi. The first is automatic
and the second is not. A table that is 95% right puts wrong Hindi names on a state page,
and this register exists to point at exactly that kind of error in other people.
"""
import json, collections, math, re

CORP = json.load(open("/Users/sathya/GitHub/schemes/data/chhattisgarh/chanakya_corpus.json",
                      encoding="utf-8"))["entries"]
C = "क-हक़-य़"
CLUS = f"((?:[{C}]्)*[{C}])"
def visual(s):
    s = re.sub(CLUS + "ि", "ि" + r"\1", s)
    s = re.sub("र्" + CLUS, r"\1" + "र्", s)
    return s
def recombine(s):
    return (s.replace("\u093e\u0947", "\u094b").replace("\u093e\u0948", "\u094c")
             .replace("\u093e\u0945", "\u0949"))

def unvisual(s):
    s = re.sub("ि" + CLUS, r"\1" + "ि", s)
    s = re.sub(CLUS + "र्", "र्" + r"\1", s)
    return s

# A consonant drawn in two pieces is ONE glyph as far as meaning goes. These bytes are
# followed by a completing stroke in 55% to 100% of their occurrences, which is what a
# left-piece looks like from the outside, so each is merged with whatever follows it into a
# single token before alignment. Without this the stroke byte has to be both "finish the
# consonant" and "the aa matra", and the aa matra is the one that loses.
def _left_pieces(thresh=0.40):
    import collections as _c
    nxt, tot = _c.defaultdict(_c.Counter), _c.Counter()
    for c, u, d, a in CORP:
        b = c.encode("mac_roman", "replace")
        for i, x in enumerate(b):
            tot[x] += 1
            if i + 1 < len(b): nxt[x][b[i + 1]] += 1
    ST = {0xA4, 0xE6, 0x55, 0x6C}
    return {x for x, n in tot.items()
            if n >= 6 and sum(v for k, v in nxt[x].items() if k in ST) / n >= thresh}

LEFT = _left_pieces()
def tok(b):
    out, i = [], 0
    while i < len(b):
        if b[i] in LEFT and i + 1 < len(b):
            out.append(bytes(b[i:i+2])); i += 2
        else:
            out.append(bytes(b[i:i+1])); i += 1
    return out

PAIRS = [(tok(c.encode("mac_roman", "replace")), visual(u), u)
         for c, u, d, a in CORP if c and u and len(c) < 90]
NEG = -16.0

def align(b, t, tab, bpen):
    n, m = len(b), len(t)
    best = [[-1e18] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if best[i][j] < -1e17: continue
            for db in (1,):
                if i + db > n: continue
                kb = b[i]
                for dt in (0, 1, 2, 3):
                    if j + dt > m: continue
                    s = best[i][j] + tab.get((kb, t[j:j + dt]), NEG) - bpen * (db - 1)
                    if s > best[i + db][j + dt]:
                        best[i + db][j + dt] = s
                        back[i + db][j + dt] = (i, j, kb, t[j:j + dt])
    if best[n][m] < -1e17: return []
    out, i, j = [], n, m
    while (i, j) != (0, 0):
        pi, pj, kb, kt = back[i][j]
        out.append((kb, kt)); i, j = pi, pj
    return out[::-1]

tab = collections.defaultdict(lambda: NEG)
seed = collections.Counter(); tot = collections.Counter()
for b, t, _ in PAIRS:
    for i, ch in enumerate(b):
        c = int(i * len(t) / max(1, len(b)))
        for j in range(max(0, c - 2), min(len(t), c + 3)):
            seed[(ch, t[j])] += 1
for (kb, kt), n in seed.items(): tot[kb] += n
for (kb, kt), n in seed.items(): tab[(kb, kt)] = math.log(n / tot[kb])

def build(tab, bpen):
    cnt = collections.Counter(); tt = collections.Counter()
    for b, t, _ in PAIRS:
        for kb, kt in align(b, t, tab, bpen):
            cnt[(kb, kt)] += 1; tt[kb] += 1
    nt = collections.defaultdict(lambda: NEG)
    for (kb, kt), n in cnt.items(): nt[(kb, kt)] = math.log((n + 0.05) / (tt[kb] + 0.5))
    best = {}
    for kb in tt:
        cands = [(n, kt) for (k2, kt), n in cnt.items() if k2 == kb]
        n, kt = max(cands)
        best[kb] = kt
    return nt, best, cnt

def decode(toks, best):
    return unvisual(recombine("".join(best.get(t, "\ufffd") for t in toks)))


for bpen in (0.0,):
    for it in range(30):
        tab, best, cnt = build(tab, bpen)
        ok = sum(1 for b, t, u in PAIRS if decode(b, best) == u)
        if it % 5 == 4 or it == 29:
            print(f"  bpen={bpen} iter {it+1:2d}: {ok}/{len(PAIRS)} exact, {len(best)} keys")
# Written beside the corpus so a later pass can diff against it. Nothing reads it.
import os as _os
_out = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                     "data", "chhattisgarh", "chanakya_table_draft.json")
json.dump({(kb.hex() if isinstance(kb, bytes) else str(kb)): kt for kb, kt in best.items()},
          open(_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
bad = [(u, decode(b, best)) for b, t, u in PAIRS if decode(b, best) != u]
print(f"\n{len(bad)} still wrong; first 6:")
for w, g in bad[:6]:
    print(f"   want {w}")
    print(f"   got  {g}")
