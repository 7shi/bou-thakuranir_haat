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
