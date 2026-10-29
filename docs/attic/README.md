# Attic

Code and output that nothing runs or reads, kept for the record rather than deleted.
Moved here on 2026-10-29 by the whole-codebase review. Each file is exactly as it was;
`git log --follow` shows its history.

- `recall_investigation.py` and `recall_investigation.json`: a superseded investigation
  of classifier recall. Its own docstring says nothing in it is wired into a classifier.
- `chanakya_blame.py`: one-off research into the Chanakya font, run by hand once. Its
  companion `parse/chanakya_derive.py` stays in parse/ as unfinished work
  (docs/MAINTAINING.md).
- `wikidata.py` and `wikidata.json`: a Wikidata enrichment no step runs and no page
  reads. It also predates the caching and resume rules for programs that fetch, so it
  would need rebuilding to those rules before it ran again.

To bring one back, `git mv` it to where it was and wire it into run.sh.
