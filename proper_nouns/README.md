# Proper Nouns

`all.tsv` is the corpus-wide proper-noun dictionary, used as the default
`--proper-nouns` glossary by `scripts/translate_segments.py` and
`all/aligned/align_lines.py`. It is built from the survey/anchor pipeline in
[`survey/`](survey/README.md) - see that README for how the pipeline itself
works (surveying, clustering, anchoring, reviewing).

## The corpus-wide dictionary - `build_tsv.py`

Once `survey/normalized-bn.jsonl` and the three `survey/anchor-*.jsonl` are
settled, `build_tsv.py` joins them into `all.tsv`, one row per Bengali name:
canonical spelling, `kind`, and the canonical each language settled on. It
makes no model calls and never touches [`extract/all.tsv`](extract/all.tsv) -
that file came from a one-off extraction while the text was being read; this
one is sourced from the corpus as actually spelled, so the two are meant to
be compared, not merged.

A Bengali name can have more than one canonical spelling in a language
without that being an error - `survey/review.py`'s "drift" report catches
real typos, but also genuine polysemy, such as দাদা rendering as both "Dada"
and "Grandson" depending on which character says it (see
`survey/CORRECTIONS.md`). Such a cell lists every canonical, most-used
first, joined by `; `. A Bengali name no anchor ties any form to in a
language - untranslated, or the translator dropped it - is left blank there.

```
make -C proper_nouns all.tsv
```

or directly:

```
uv run proper_nouns/build_tsv.py
```

[`extract/`](extract/README.md) holds an earlier, one-off extraction
(`extract.py`/`translate.py`) done while the text was first being read. Its
`all.tsv` is kept for comparison but is no longer the active dictionary.
