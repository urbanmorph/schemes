"""
Which token in the draft Chanakya table is responsible for which wrong character.

AGENT-EDITABLE (PLAN.md 7). Reads data/chhattisgarh/. Never fetches. NOTHING CONSUMES IT.

parse/chanakya_derive.py produces a table that is mostly right and does not say where it is
wrong. This aligns each decoded string against the name the state printed, finds the spans
that differ, and blames the token whose output lands inside one. That turns "10 of 187
pairs are exact" into a ranked list of the handful of byte assignments actually costing the
difference, which is the census-error loop this register uses on its classifiers pointed at
its own decoder.

Run after chanakya_derive.py. Reading the output: a token seen often and blamed rarely is
fine; a token blamed on most of the rows it appears in is wrong, and the corpus says what
it should be.
"""
import json, collections, re
tab = {bytes.fromhex(k) if re.fullmatch(r"[0-9a-f]+", k) else k.encode(): v
       for k, v in json.load(open("data/chhattisgarh/chanakya_table_draft.json",
                                  encoding="utf-8")).items()}
CORP = json.load(open("data/chhattisgarh/chanakya_corpus.json", encoding="utf-8"))["entries"]
C = "क-हक़-य़"
CLUS = f"((?:[{C}]्)*[{C}])"
def unvisual(s):
    s = re.sub("ि" + CLUS, r"\1" + "ि", s)
    s = re.sub(CLUS + "र्", "र्" + r"\1", s)
    return s
def recombine(s):
    return (s.replace("ाे", "ो").replace("ाै", "ौ")
             .replace("ाॅ", "ॉ"))
import collections as _c
nxt, tot = _c.defaultdict(_c.Counter), _c.Counter()
for c, u, d, a in CORP:
    b = c.encode("mac_roman", "replace")
    for i, x in enumerate(b):
        tot[x] += 1
        if i + 1 < len(b): nxt[x][b[i + 1]] += 1
ST = {0xA4, 0xE6, 0x55, 0x6C}
LEFT = {x for x, n in tot.items() if n >= 6 and
        sum(v for k, v in nxt[x].items() if k in ST) / n >= 0.40}
def tok(b):
    out, i = [], 0
    while i < len(b):
        if b[i] in LEFT and i + 1 < len(b): out.append(bytes(b[i:i+2])); i += 2
        else: out.append(bytes(b[i:i+1])); i += 1
    return out

blame = collections.Counter()
seen = collections.Counter()
for c, u, d, a in CORP:
    ts = tok(c.encode("mac_roman", "replace"))
    pieces = [tab.get(t, "�") for t in ts]
    got = unvisual(recombine("".join(pieces)))
    for t in ts: seen[t] += 1
    if got == u: continue
    import difflib
    sm = difflib.SequenceMatcher(None, got, u)
    badspans = [(i1, i2) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    pos = 0
    for t, p in zip(ts, pieces):
        s0, s1 = pos, pos + len(p); pos = s1
        if any(not (s1 <= i1 or s0 >= i2) for i1, i2 in badspans):
            blame[t] += 1
print(f"{'token':>10} {'maps to':>8} {'blamed':>7} {'seen':>6}  rate")
for t, n in blame.most_common(18):
    print(f"  {t.hex():>8} {tab.get(t,'?')!r:>8} {n:>7} {seen[t]:>6}  {n/max(1,seen[t]):.0%}")
