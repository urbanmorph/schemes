"""tools/release.py: a release is named once, never changes, and is published as it was cut.

Plain asserts and a temporary directory, like the other tests here; no test framework.
"""
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import release  # noqa: E402

CSV = "name,slug\nA,a\nB,b\n"
CSV2 = "name,slug\nA,a\nC,c\nD,d\n"


def setup(tmp, csv=CSV, snapshot="2026-11-03", verdict="COMPLETE"):
    os.makedirs(os.path.join(tmp, "site", "_out"), exist_ok=True)
    with open(os.path.join(tmp, "site", "_out", "schemes.csv"), "w", encoding="utf-8", newline="") as fh:
        fh.write(csv)
    with open(os.path.join(tmp, "status.json"), "w") as fh:
        json.dump({"snapshot": snapshot, "verdict": verdict}, fh)


def read(tmp, *p):
    with open(os.path.join(tmp, *p), encoding="utf-8") as fh:
        return fh.read()


def test_code_comes_from_the_snapshot_month():
    assert release.release_code("2026-11-03") == "schemes-register-2026.11"
    assert release.release_code("2027-01-03") == "schemes-register-2027.01"


def test_first_release_is_cut_with_its_checksum():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp)
        code, made = release.make_release(tmp)
        assert (code, made) == ("schemes-register-2026.11", True)
        m = json.loads(read(tmp, "releases", code, "manifest.json"))
        assert m["sha256"] == hashlib.sha256(CSV.encode()).hexdigest()
        assert m["rows"] == 2 and m["snapshot"] == "2026-11-03"
        assert m["previous"] is None
        assert read(tmp, "releases", code, "schemes.csv") == CSV
        assert "first release" in read(tmp, "releases", code, "CHANGES.md").lower()


def test_a_second_run_changes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp)
        release.make_release(tmp)
        before = read(tmp, "releases", "schemes-register-2026.11", "manifest.json")
        code, made = release.make_release(tmp)
        assert made is False
        assert read(tmp, "releases", code, "manifest.json") == before


def test_a_release_never_changes_its_bytes():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp)
        release.make_release(tmp)
        setup(tmp, csv=CSV2)
        try:
            release.make_release(tmp)
        except release.ReleaseChanged as e:
            assert "schemes-register-2026.11" in str(e)
        else:
            raise AssertionError("a changed CSV under an existing code must be refused")


def test_an_unverified_snapshot_is_never_released():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp, verdict="INCOMPLETE")
        code, made = release.make_release(tmp)
        assert made is False and code is None
        assert not os.path.exists(os.path.join(tmp, "releases"))


def test_the_next_release_says_what_came_and_went():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp)
        release.make_release(tmp)
        setup(tmp, csv=CSV2, snapshot="2026-12-03")
        code, made = release.make_release(tmp)
        m = json.loads(read(tmp, "releases", code, "manifest.json"))
        assert m["previous"] == "schemes-register-2026.11"
        assert m["ids_added"] == 2 and m["ids_removed"] == 1
        notes = read(tmp, "releases", code, "CHANGES.md")
        assert "2 ids added" in notes and "1 id removed" in notes


def test_publish_copies_every_release_and_writes_the_index():
    with tempfile.TemporaryDirectory() as tmp:
        setup(tmp)
        release.make_release(tmp)
        setup(tmp, csv=CSV2, snapshot="2026-12-03")
        release.make_release(tmp)
        out = os.path.join(tmp, "site", "_out")
        release.publish(tmp, out)
        idx = json.loads(read(out, "releases", "index.json"))
        assert [r["code"] for r in idx["releases"]] == ["schemes-register-2026.12", "schemes-register-2026.11"]
        assert idx["latest"] == "schemes-register-2026.12"
        assert read(out, "releases", "schemes-register-2026.11", "schemes.csv") == CSV


def test_publish_with_no_releases_writes_an_empty_index():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out")
        release.publish(tmp, out)
        assert json.loads(read(out, "releases", "index.json")) == {"latest": None, "releases": []}


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print(f"   ok  {name}")
    print(f"   {n} release tests passed")
