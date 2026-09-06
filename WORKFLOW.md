# Workflow

How the Bengali Wikisource text becomes the published site: what runs in what
order, what each stage leaves behind, and why the stages are shaped the way
they are. The per-script detail lives in the READMEs next to the scripts
([`scripts/`](scripts/README.md), [`all/aligned/`](all/aligned/README.md),
[`wikisource/`](wikisource/README.md), [`proper_nouns/`](proper_nouns/README.md),
[`templates/`](templates/README.md)); this file is the map between them.

Everything below runs from the repository root, and every stage that calls a
model is resumable: re-running after an interruption skips the records already
in its output.

## The stages

| # | Stage | Command | Writes |
|---|-------|---------|--------|
| 1 | Extract the source | `make -C wikisource ...` | `all/bn.md` |
| 2 | Segment | `uv run scripts/segment_chapters.py` | `segmentations.jsonl` |
| 3 | Translate | `make translate` | `all/{en,ja,hi,bn}-gemini.jsonl` |
| 4 | Align lines | `make -C all/aligned align pack` | `all/aligned/*-terra.delta.jsonl` |
| 5 | Convert to Markdown | `make convert` | `all/*-gemini{,-full,-summary}.md` |
| 6 | Split sentences | `make split` | `all/*-gemini-lines.md` |
| 7 | Caption the segments | `make captions` | `all/captions.jsonl` |
| 8 | Title the scenes | `make titles` | `all/{en,ja}-gemini.tsv` |
| 9 | Write the questions | `make questions` | `questions-{en,ja}.jsonl` |
| 10 | Build and deploy | `make build`, `make deploy` | `dist/`, the `gh-pages` branch |

Stages 1 and 2 are run once. Stages 3-4 are the expensive ones and are not
regenerated casually - `qa-eval/` was measured against exactly this text.
Stages 5-10 are cheap to redo, except 7-9, which call a model.

**1. Extract the source.** [`wikisource/`](wikisource/README.md) turns a
`bnwikisource` XML dump into `all/bn.md`, the classical-Bengali text every
later stage works from. It runs off a downloaded dump rather than the live
site, so a rerun is local.

**2. Segment.** `scripts/segment_chapters.py` splits each chapter into
translation-sized scenes by asking the model for boundary line numbers with a
reasoning field, so a break falls where the story breaks rather than at a fixed
length. The result is 82 segments across 37 chapters.

**3. Translate.** `scripts/translate_segments.py` runs once per target language
- English, Japanese, Hindi, and a modern Bengali retelling of the classical
original - and writes one record per segment holding `summary`,
`translation_notes` and `translation`. The summaries feed forward as running
story context so a later scene knows what happened earlier, and
`proper_nouns/all.tsv` is passed in to keep names stable across the corpus.

**4. Align lines.** The translations above return each scene as flowing prose,
losing the source's one-line-per-utterance structure.
[`all/aligned/`](all/aligned/README.md) puts it back. Only the deltas are
committed; `make -C all/aligned unpack` regenerates the full files, and both
`make convert` and `make build` do that for you.

**5-6. Convert.** `scripts/jsonl_to_md.py` renders the JSONL as Markdown with
the aligned translations substituted in: the text alone, the text with
summaries and notes (`-full`), and the summaries alone (`-summary`).
`scripts/split-line.py` additionally produces a one-sentence-per-line variant
with spaCy.

**7. Caption the segments.** `scripts/generate_captions.py` reads the four
`-summary.md` files and writes one short scene label per segment in all four
languages, as a matched set (see below).

**8. Title the scenes.** `scripts/generate_titles.py` writes a scene title per
segment per language into `all/{en,ja}-gemini.tsv`. These are an input to
`qa-eval/`'s embedding index, not a reading artefact; the site does not use
them.

**9. Write the questions.** The RAG/QA question set, generated from the English
translation and then translated to Japanese, consumed by
[`qa-eval/`](qa-eval/README.md).

**10. Build and deploy.** `templates/build.py` renders the chapter pages, the
per-language summary pages, the QA pages, the `docs/*.md` pages and the landing
page into `dist/`; `make deploy` pushes `dist/` to `gh-pages`.

## `chapter:segment` is the spine

The numbering established in stage 2 is what every later file agrees on: the
translation JSONLs, the aligned JSONLs, `all/captions.jsonl`, the scene-title
TSVs, the question set's chapter references, and `qa-eval`'s indexes all
address text as `chapter:segment`.

Re-running stage 2 renumbers the corpus and invalidates all of it, so
`segmentations.jsonl` is frozen. The Markdown files do not mark the boundaries,
which is why `templates/build.py` recovers them from `segmentations.jsonl` (for
the original) and from the aligned JSONLs (for the translations) rather than
from the Markdown itself.

## Why the reading page is shaped the way it is

This is a novel, and the workflow is specialised for prose. Three decisions
follow from that, and they are the ones most worth understanding before
changing anything.

**No summaries inside the text.** The chapter page presents the text to be read
straight through. Segmentation already keeps each unit short, so what the page
needs at a segment boundary is a place-marker, not a retelling: a caption heads
each segment, and the paragraph-length summaries stay on their own
`summary-{lang}.html` pages. A verse text has the opposite problem - the
line-by-line surface is fragmentary and the thread is hard to follow, so a
summary earns its place before the text - but in prose an interleaved retelling
only competes with the sentences it is describing.

**One language at a time.** Prose paragraphs do not line up the way verse lines
do, and five languages of full-width prose will not sit side by side. The
chapter page therefore switches language rather than showing languages in
parallel, and each language's panel carries its own text split into the same
segments, headed by the caption in that language.

**Captions are a matched set.** Because the page switches language, a reader
who switches mid-chapter has to land in the same place: the four captions of a
segment have to name the same scene the same way. That also makes them usable
as one index key across all four languages - the role the English and Japanese
scene titles play for `qa-eval` today, which they can only play in the two
languages they exist in. The per-segment summaries cannot supply it: they were written
independently, one per translation run, and differ in detail and emphasis. So
`generate_captions.py` captions a segment in all four languages in a single
call - Bengali first, then the other three as strict translations of it -
rather than shortening each language's summary on its own.

## What to re-run when something changes

| Changed | Re-run |
|---------|--------|
| `all/bn.md` | everything (and the corpus is renumbered - see above) |
| a translation JSONL | `make -C all/aligned align-<lang> pack-<lang>`, `make convert`, then 7-9 if the summaries moved, then `make build` |
| published text, edited in `all/<lang>-gemini.md` | `make -C all/aligned fold-<lang> pack-<lang>`, `make convert`, `make build` |
| `proper_nouns/all.tsv` | nothing automatically - it is an input to stage 3, so only a re-translation picks it up |
| `all/captions.jsonl` | `make build` |
| templates or static assets | `make build` |

Deleting a resumable stage's output regenerates it in full; leaving it in place
fills in only what is missing. `all/captions.jsonl` is the usual case: remove
the file to re-caption the whole novel, or leave it and only the segments not
yet in it are generated.
