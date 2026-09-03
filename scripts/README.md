# scripts

The tooling that turns the Bengali source into the translations and the site.
Every script runs from the repository root:

```
uv run scripts/<name>.py ...
```

Related tooling lives elsewhere and is documented with its own data:
[`proper_nouns/`](../proper_nouns/README.md) for the glossary,
[`qa-eval/`](../qa-eval/README.md) for the retrieval evaluation, and
[`templates/`](../templates/README.md) for the site build.

## Translation pipeline

The main path, in order. Each stage writes a file the next one reads, and the
expensive ones are resumable: re-running after an interruption skips the records
already in the output.

### `segment_chapters.py`

Splits each chapter of `all/bn.md` into translation-sized scenes and writes
`segmentations.jsonl`. It asks the model for boundary line numbers with a
reasoning field rather than cutting on a fixed length, so a scene break falls
where the story breaks. Everything downstream addresses text as
`chapter:segment`, and that numbering starts here.

```
uv run scripts/segment_chapters.py -m google:gemini-2.5-pro -o segmentations.jsonl
```

Run once; `segmentations.jsonl` is committed and the rest of the pipeline takes
it as a default. Re-running it renumbers the corpus and invalidates every
translation, so treat it as frozen.

### `translate_segments.py`

Translates each segment and writes `all/<lang>-gemini.jsonl`. A record holds
`summary`, `translation_notes` and `translation`; the summaries feed forward as
running story context so a later scene knows what happened earlier, and
`proper_nouns/all.tsv` is passed in to keep names stable across 82 segments.

```
make translate
```

which runs it once per language (`-f`/`-t` for the language pair, `-m` for the
model, `-o` for the output). The four outputs - English, Japanese, Hindi and
modern Bengali - are what everything else in the repository is built on. They
are also what `qa-eval/` was measured against, so they are not regenerated
casually.

### `jsonl_to_md.py`

Renders a translation JSONL as Markdown, grouped by chapter.

```
make convert
```

`--mode` picks what to include: `translation` (default, the text alone),
`summary` (per-segment summaries) or `full` (text with summaries and notes).
This is what produces `all/*.md`, the input to the site build.

`-a`/`--aligned` reads a second file: an aligned JSONL (see Line alignment
below) whose translations replace the input's, while the structure, summaries
and notes still come from the input. The pairing must be exact in both
directions, so a partially aligned file is an error rather than a silent mix.
`make convert` passes it for English and Japanese, unpacking the deltas first.

## Line alignment

The translations above store each scene as one flowing paragraph, losing the
source's one-line-per-utterance structure. `align_lines.py` and
`pack_aligned.py` restore it and live in
[`all/aligned/`](../all/aligned/) alongside the files they produce; see
[`all/aligned/README.md`](../all/aligned/README.md) for the full rationale,
model comparison and check descriptions, and `all/aligned/Makefile` for the
`unpack`/`align`/`pack` targets.

## Question set

The RAG/QA evaluation questions in `questions-en.jsonl` and `questions-ja.jsonl`,
consumed by [`qa-eval/`](../qa-eval/README.md).

### `generate_questions.py`

Generates detail-oriented questions from `all/en-gemini.md` in two separate
multi-turn sessions over one uploaded copy of the text: a *single-passage*
session, where a question is answerable only by close reading of one scene, and
a *cross-reference* session, where answering requires synthesising two or three
separated chapters. The sessions are multi-turn on purpose - the earlier
memoryless approach kept regenerating questions about the same few salient
events.

```
make questions
```

which runs this and then `translate_questions.py`. `--only single` or
`--only cross` runs one session; `--turns` and `--per-turn` set the volume, and
`-m` overrides the model.

### `translate_questions.py`

Translates the `question`, `answer` and `rationale` fields into Japanese,
keeping proper nouns consistent with `proper_nouns/all.tsv` and the Japanese
translation. `anchor_id`, `type` and `chapters` are language-independent and
copied verbatim so the two files stay line-for-line parallel. Resumable by
`anchor_id`.

Runs as the second half of `make questions`, or on its own:

```
uv run scripts/translate_questions.py -i questions-en.jsonl -o questions-ja.jsonl
```

### `check_duplicates.py`

Finds semantically duplicate questions. Every question acts as a seed: candidates
are ranked by embedding similarity, judged pairwise by an LLM from the top down
until `--stop` consecutive "different" verdicts, and the "same" judgments are
unioned into groups. Judgments are cached symmetrically, so the pass is order
independent and cheap to re-run. Reports the groups and the effective unique
question count.

```
uv run scripts/check_duplicates.py -l en
```

## Images

### `imagen.py`

Reads the per-chapter prompts from `images.md` and generates four candidate
images per chapter into `images/` via the Gemini image API. Skips any candidate
that already exists. Needs `GEMINI_API_KEY`.

### `compress_images.py`

Publishes one chosen candidate per chapter to `dist/images/NN.jpg`, resized to
1,024px wide and re-encoded down until it fits in 50 KB. The choice is the
`SELECTED_SUFFIX` table at the top of the file, edited by hand.

```
make images
```

## Derived files and analysis

### `generate_titles.py`

Writes a short scene title for every segment to `all/<lang>-gemini.tsv`, read by
the site to label scenes. Titles come from the translation JSONL, which is
already segmented, so no re-slicing of the Markdown is involved. Resumable, and
`--title-lang` sets the language of the titles rather than of the source.

```
make titles
```

### `split-line.py`

Re-splits a Markdown translation to one sentence per line with spaCy, producing
`all/*-gemini-lines.md`. Headings and blank lines pass through untouched.
`-t` picks the pipeline (`3`, the default, uses the full language model; `2` uses
the lightweight sentencizer) and `-l` the language.

```
make split
```

This is sentence splitting, not line alignment - it divides the translation by
its own sentence boundaries, where `align_lines.py` reproduces the source's line
structure. The two are unrelated despite the similar output.

### `analyze_chapters.py`

Prints a per-chapter line count table for `all/bn.md` (start line, end line,
content lines, total) and optionally writes `chapter_analysis.csv`. A
measurement tool from the segmentation work, kept for re-checking the source.

## Shared

### `utils.py`

`load_chapter_blocks(jsonl_path, md_path)` reads a segmentation JSONL together
with the source Markdown and returns `{"title": ..., "chapters": [[segment, ...],
...]}`. It is how `translate_segments.py` and `align_lines.py` agree on what
`chapter:segment` refers to. A chapter with no entry in the segmentation file
comes back as a single block.
