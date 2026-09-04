# Proper Nouns

`all.tsv` is the corpus-wide proper-noun dictionary, used as the default
`--proper-nouns` glossary by `scripts/translate_segments.py` and
`all/aligned/align_lines.py`. It was built once from the survey/anchor
pipeline in [`survey/`](survey/README.md) - see that README for how the
pipeline itself works (surveying, clustering, anchoring, reviewing, and
`build_tsv.py`, the survey-stage script that produced this file).

**`all.tsv` is hand-edited from here on** (see "Correcting a rendering
found by inspection" below and [`CORRECTIONS.md`](CORRECTIONS.md)), so
`survey/build_tsv.py` must not be re-run as a routine step - doing so
overwrites every hand edit with whatever the survey/anchor pipeline
currently says. It stays a `survey/` script (a build tool for the pipeline
that produces this file), not a `proper_nouns/` one, precisely to keep it
apart from the file it would clobber.

[`extract/`](extract/README.md) holds an earlier, one-off extraction
(`extract.py`/`translate.py`) done while the text was first being read. Its
`all.tsv` is kept for comparison but is no longer the active dictionary.

## Correcting a rendering found by inspection

A rendering problem in `all.tsv` spotted by reading it (as opposed to one
`survey/review.py` finds during the survey/anchor pipeline itself) is fixed
in three steps:

1. **Edit `all.tsv` directly** - it is a plain TSV, safe to hand-edit for a
   single-cell fix such as an inconsistent or under-translated rendering.
2. **Apply the same fix to the published text**, via
   [`all/aligned/README.md`](../all/aligned/README.md)'s "Correcting the
   published text" workflow: edit `all/<lang>-gemini.md`, then
   `fold-<lang>`, `pack-<lang>` and `make convert` to fold it back into the
   aligned JSONL/delta and regenerate the other Markdown variants.
3. **Log it in [`CORRECTIONS.md`](CORRECTIONS.md)** as a new entry (a new
   pass section if the existing ones are already closed out) - this is a
   target-language-local correction as that file defines it, since the fix
   is confined to one language's rendering with no Bengali-side problem.

`all.tsv` step 1 and the published text in step 2 must not drift apart -
the TSV is the glossary `align_lines.py` and `translate_segments.py` read,
and the Markdown is what is actually deployed.

## Recording fixes - `CORRECTIONS.md`

[`CORRECTIONS.md`](CORRECTIONS.md) is the standing log of what
`survey/review.py`, the manual sweeps described in
[`survey/README.md`](survey/README.md), and direct inspection of `all.tsv`
have found and fixed in the published translations - a history, not a
to-do list, so it is never emptied out or deleted once a pass finishes;
each pass gets its own section. Two kinds of entries appear there:

- **Bengali-side**: the survey/clustering got a name wrong or missed a
  form. Fixed with `cluster.py`'s `patch()` on `survey/cluster-bn.jsonl`,
  then `survey/normalized-bn.jsonl` and any `survey/anchor-*.jsonl`
  rebuilt.
- **Target-language-local**: one language's translation drifted between
  two spellings of the same name, or stayed transliterated where it
  should read as a translation, with no Bengali-side problem. Fixed by
  hand in `all/<lang>-gemini.md` and folded back per
  [`all/aligned/README.md`](../all/aligned/README.md)'s "Correcting the
  published text".
