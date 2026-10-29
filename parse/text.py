"""
Text helpers the state parsers share. AGENT-EDITABLE (PLAN.md §7). Pure functions.

Each was written into a parser as that state was added and then copied to the next one:
joined() was in seven parsers and clean() in four, identical but for docstrings.
"""
import re
import sys


def joined(parts):
    """Join wrapped name fragments. A fragment ending in a hyphen against a letter is one
    word broken over the line, `Nadu-` + `Nedu`, and must not gain a space; a hyphen used
    as punctuation keeps its spaces."""
    out = ""
    for p in parts:
        p = (p or "").strip()
        if not p:
            continue
        if not out:
            out = p
        elif re.search(r"\w-$", out):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


def clean(s, strip=" .,;:-"):
    """Collapse whitespace and trim the punctuation a cell leaves at its edges."""
    return re.sub(r"\s+", " ", s or "").strip(strip)


def selftest():
    bad = 0
    for label, got, want in [
            ("a word broken over a line joins without a space",
             joined(["Nadu-", "Nedu Scheme"]), "Nadu-Nedu Scheme"),
            ("a hyphen used as punctuation keeps its spaces",
             joined(["Mission Shakti -", "Sambal"]), "Mission Shakti - Sambal"),
            ("empty and missing fragments are skipped", joined(["", None, " a ", "b"]), "a b"),
            ("inner whitespace collapses", joined(["a   b", "c"]), "a b c"),
            ("clean trims edge punctuation", clean("  Old Age  Pension.;  "), "Old Age Pension"),
            ("clean keeps a hyphen when asked to", clean("Scheme -", strip=" .,;:"), "Scheme -"),
            ("clean of nothing is empty", clean(None), "")]:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": want {want!r} got {got!r}"))
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        print("text self-test")
        sys.exit(1 if selftest() else 0)
    sys.exit("usage: python3 parse/text.py --self-test")
