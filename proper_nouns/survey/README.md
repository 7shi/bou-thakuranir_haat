# Proper-Noun Survey

`survey.py` reads one target-language translation on its own terms - no
source text, no glossary - and asks the model which proper nouns appear on
each line, exactly as spelled there. The result is a surface-form census that
can be compared against [`proper_nouns/all.tsv`](../all.tsv), or against
itself to find spelling that drifts within the same translation (the
Bibha/Vibha and Udayaditya/Udayditya kind of finding). Unlike
[`extract.py`](../extract.py), it never looks at the source language.

## Input

- `all/aligned/{en,ja,hi}-gemini-terra.jsonl` - the aligned translations, not
  the raw `all/{lang}-gemini.jsonl`. Alignment is what makes a given line
  number mean the same source line across languages; the raw translations
  carry no such guarantee (see [`all/aligned/README.md`](../../all/aligned/README.md)).
- `all/bn.md` for Bengali - the classical source itself. The Modern Bengali
  translation (`all/bn-gemini.jsonl`) copies proper nouns verbatim and is out
  of scope for this survey.

A `.jsonl` input is read as a translation (`response.translation` per
record); a `.md` input is read as source markdown, segmented the same way
`translate_segments.py` and `extract.py` segment it
(`scripts.utils.load_chapter_blocks`), so its chapter/segment numbers line up
with the translation JSONLs built from the same file.

## Output

`survey/<lang>.jsonl`, one JSON object per segment:

```json
{"chapter": 1, "segment": 2, "target_lang": "hindi", "model": "openai:gpt-5.6-terra",
 "proper_nouns": {"1": ["उदयदित्य"], "2": [], "3": ["सुरमा"]}}
```

`proper_nouns` has one entry per line of that segment's text (string keys,
matching the input's own line numbering), listing every proper noun found on
that line exactly as spelled - not normalized to a base form, since surface
spelling is the whole point.

## Usage

```
make -C proper_nouns/survey          # all four languages
make -C proper_nouns/survey hi.jsonl  # one language
```

or directly:

```
uv run proper_nouns/survey/survey.py all/aligned/hi-gemini-terra.jsonl -m openai:gpt-5.6-terra
```

- `translations` - an aligned JSONL or a source markdown file, as above
- `-m/--model` (required) - Terra, not Luna: Luna's accuracy drops on text
  this long, and per-line calls would be too many (1,159 lines total)
- `-o/--output` - default: `<lang>.jsonl` in this directory, `<lang>` taken
  from the input filename (`hi-gemini-terra.jsonl` -> `hi`, `bn.md` -> `bn`)
- `-l/--lang` - language name to tell the model (default: the JSONL's
  `target_lang`, or `Bengali` for a markdown input)
- `-s/--segment` - redo only named `chapter:segment` references (comma
  separated), overwriting any existing records; otherwise already-surveyed
  segments are skipped, so a run resumes where the last one stopped
- `--segmentation` - segmentation JSONL, only used for a markdown input
  (default: `segmentations.jsonl` at the repo root)

## Clustering into names - `cluster.py`

The survey records spelling as found, so one name is spread over many entries:
inflected (প্রতাপাদিত্যের), shortened (প্রতাপ), and now and then misspelled
(প্রতপাদিত্য). `cluster.py` groups a chapter's forms by the name they spell and
gives each group that name's base form and a `kind`, which is what makes the
misspellings stand out. Why it works by chapter, why it groups by name rather
than by referent, and why a base form may be one the chapter never uses: see
the comments in the script.

Bengali only for now. It is the source language, and the other three are meant
to be tied to its names rather than clustered on their own. The measurements
behind the chapter unit: Bengali runs 11 to 48 distinct forms per chapter, 29
typically, against 361 for the corpus at once.

Chapters are processed in order and each call is given the names the earlier
chapters settled, as a reference rather than a checklist. `-c` redoes named
chapters, counting every other chapter's names as established, whichever side
of it they fall on. Every answer is checked to be a partition of that
chapter's forms - same set, no duplicates, nothing invented - and a chapter
that fails is retried with the offending forms named.

Output, one JSON object per chapter:

```json
{"chapter": 1, "target_lang": "Bengali", "model": "openai:gpt-5.6-terra",
 "entities": [{"canonical": "উদয়াদিত্য", "kind": "person",
               "forms": ["উদয়াদিত্য", "উদয়াদিত্যের"]}]}
```

```
make -C proper_nouns/survey cluster-bn.jsonl
```

or directly:

```
uv run proper_nouns/survey/cluster.py proper_nouns/survey/bn.jsonl -m openai:gpt-5.6-terra
```

- `survey` - a survey JSONL produced above
- `-m/--model` (required)
- `-o/--output` - default: `cluster-<name>.jsonl` next to the input
- `-l/--lang` - language name to tell the model (default: the survey's
  `target_lang`)
- `-c/--chapter` - redo only these chapters (comma separated), overwriting
  their records; otherwise already-clustered chapters are skipped, so a run
  resumes where the last one stopped
- `-N/--normalize` - make no calls; fold the chapters already clustered into
  one corrected list (see below)

## The corrected list - `cluster.py -N`

`-N` makes no calls. It applies the corrections held in `REASSIGN`, `MERGE`,
`KINDS` and `DROP` at the top of `cluster.py` - hard-coded there rather than
edited into `cluster-<lang>.jsonl`, each one annotated with the passage of
`all/bn.md` that settles it - and writes `normalized-<lang>.jsonl`.

The file keeps the per-chapter shape, one record per chapter listing the names
it uses with their canonical spelling, kind, and the forms found there. For
Bengali, 359 forms across 37 chapters resolve to 180 names, 5 to 29 of them
per chapter. `collect_names()` aggregates the records into one entry per name
- canonical, kind, every form found anywhere, and the chapters it appears in -
for whatever wants the corpus-wide view, such as rebuilding `all.tsv`.

```
make -C proper_nouns/survey normalized-bn.jsonl
```
