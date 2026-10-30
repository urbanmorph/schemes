# collect/: proposed changes for human review

collect/ is frozen (PLAN.md §7): changing how the archive is collected needs a deliberate,
reviewed change. The whole-codebase review on 2026-10-29 found the problems below. None
of them has been changed. Each is listed with the evidence and the change proposed, most
serious first, so they can be reviewed and made as one change.

What was checked and is fine: no collector sends HEAD to a government host; every
workflow input reaches a script through `env:`; no secret is printed.

## 1. State collectors cannot resume and log nothing per book

All 16 state collectors keep their manifest in memory and write it once, at the end.
They print only after the loop, and nothing skips a book that is already on disk.
Karnataka and Uttar Pradesh record no sha256 per book.

Effect: a collector stopped at its 20-minute budget (run.sh `budgeted`) starts again from
the first book on the next attempt. Uttar Pradesh has about 97 grants. This breaks the
project's own rules for programs that fetch: cache as you go, resume, be idempotent, log
progress.

Proposed: write the manifest after each book (atomically, see 3), print one line per
book, record sha256 for every book, and skip a book whose file is present and whose
sha256 matches the manifest.

## 2. The CAG walk cannot resume

collect/cag.py writes one page file per index page but checks completeness only at the
end, so run.sh discards a walk stopped at its 120-minute budget. On a GitHub runner the
walk needs more than 81 minutes, so a stop throws away up to 81 minutes of pages.

Proposed: within the same date, keep page files that parse, fetch only the missing pages,
then run the same distinct-id check against the total the site prints. The check stays
exactly as strict.

## 3. Writes are not atomic

`common.write_json` and the 42 inline `gzip.open(..., "wb")` writes across 21 files
write in place. A collector killed mid-write leaves a truncated file, and Save in
collect.yml can commit it once myScheme is finished (it prunes manifest-less folders
only under archive/cag).

Proposed: write to `<path>.part` and `os.replace` it. `common.write_raw_gz` already
exists and has no callers; make it atomic and use it for every gzip write. Meanwhile
Save could also drop `archive/<state>/*/` folders without a manifest.

## 4. myScheme resume refetches the list and drops earlier segments

On resume collect/myscheme.py re-sends the census and all 48 list pages, rewrites
list.ndjson.gz and census.json.gz, and rebuilds the manifest from scratch, so
`segments` holds only the latest attempt. Its comments say it reuses the list and
records each segment. It also keeps details for slugs that have left the list, and
verify/verify.py compares counts rather than slug sets, so one stale record plus one
missing scheme passes.

Proposed: collector, keep the previous manifest's segments, reuse the list when the
census total is unchanged, and intersect `done` with the current slugs. verify.py (not
frozen), compare the set of slugs in details with the list's slugs.

## 5. Collectors that fail exit 0

Only myscheme.py and uttarpradesh.py exit non-zero. run.sh now checks CAG, DBT and the
Union Budget manifests after they run (`unfinished()`), and progress.py `held()` needs a
book on disk, so the worst effects are handled outside collect/. A collector that
cannot reach its index should still exit non-zero itself.

## 6. Copied code

- The same `note(s)` status histogram is in 18 collectors.
- The fetch, `%PDF` check, `looks_like_error`, gzip and manifest-entry block is in 17.
- `labelled_pdfs` is in 7; Delhi's and Haryana's `labelled_pdfs` and `discover` are
  identical, and their `collect()` differs only in the state name.
- `filename_of` is in 3 (Kerala, Punjab, Maharashtra).

Proposed: move `note`, a `save_pdf(man, out_dir, book, response)` and `labelled_pdfs`
into common.py in the same reviewed change as 1 and 3, since that change touches every
one of these blocks anyway.

## 7. Small

- collect/jharkhand.py imports `common` and does not use it.
