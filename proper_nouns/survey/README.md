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

Bengali only. It is the source language, and the other three are tied to its
names by `anchor.py` below rather than clustered on their own. The measurements
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
it uses with their canonical spelling, kind, the forms found there, and - when
`-S` gives it the source - how often the chapter uses the name and the
`segment:line` positions it stands on, read from the text rather than taken
from the survey, which has neither for a swept-in occurrence and lists a name
once for a line that uses it twice. For
Bengali, 363 forms across 37 chapters resolve to 180 names, 5 to 32 of them
per chapter. `collect_names()` aggregates the records into one entry per name
- canonical, kind, every form found anywhere, and the chapters it appears in -
for whatever wants the corpus-wide view, such as rebuilding `all.tsv`.

`-S all/bn.md` additionally sweeps each chapter for the occurrences the survey
missed. The survey reads one segment at a time and is not perfectly consistent
about what counts as a name; titles and kinship terms are where it wavers
most. মহারাজ is recorded 116 times out of 116 across the book yet was missed
in chapter 1, and মা, দাদা, পিতা and বাবা are recorded in some chapters and
passed over in others. In Bengali alone that unevenness is invisible, but it
breaks `anchor.py` below: a chapter whose Bengali list has no মহারাজ does not
leave the English "Maharaj" unresolved as instructed - it ties it to whatever
name is nearest.

By the time `-N` runs, the clustering has already settled which name each form
spells, so the gaps close without another call: every form the book has
established as a name - the canonical spellings included - is searched for in
each chapter's source, and one found where the chapter has no entry for it is
added to that name. Nothing is invented, nothing is removed, and matching is
longest-first so that "দাদা মহাশয়ের" is one match rather than a দাদা inside
it. A form two chapters file under different names is left alone rather than
guessed at, which is how the corrections keep the last word: fix the outlier
with `REASSIGN` and the form becomes sweepable. Forms that are also ordinary
words are listed in `EXCLUDE`, since no matching tells প্রাণ ("life") from the
villager পরাণ, or উদয় হইল ("dawned") from উদয়. For Bengali the sweep adds 197
chapter entries over 90 forms.

```
make -C proper_nouns/survey normalized-bn.jsonl
```

## Anchoring the other languages - `anchor.py`

`cluster.py` groups Bengali on its own; en/ja/hi are not clustered that way.
Whether a chapter's English "Vibha" and "Bibha" are one name is a question
about the Bengali বিভা they both render, so `anchor.py` gives the model one
chapter's target-language forms together with that chapter's Bengali names
from `normalized-bn.jsonl` - the 5 to 32 of them, never the book's whole cast
- and asks which Bengali name each group of forms renders and what base form
the translation should use for it. Both sides are listed with their counts and
the lines they stand on, which is what settles the cases spelling cannot: a
chapter's three "Grand-uncle" match a দাদামহাশয় used five times rather than a
খুড়া used once, and chapter 1's "Lord" and "lord" - one occurrence each -
separate into প্রভু and নাথ by the line each stands on. Positions are evidence
rather than proof, since the re-flow pass can move a phrase a line away, which
is why the decision stays at chapter level. The base form is chosen by comparison with
the Bengali, which is what lets a chapter resolve even when every occurrence
of a name in it is misspelled.

Every answer is checked to partition that chapter's forms, as in `cluster.py`,
and additionally that each `bengali` is one of the names offered for the
chapter; a failing chapter is retried with the offending forms and names
listed. `bengali` is left empty where forms tie to no name in the chapter - a
translator's addition, or a common noun the survey took for a name - and those
stay in the output as unresolved rather than being forced onto some name.
Several entries may carry the same `bengali`, since a name and the epithet
used for the same character stay separate entries.

Output, one JSON object per chapter:

```json
{"chapter": 1, "target_lang": "English", "source_lang": "Bengali",
 "model": "openai:gpt-5.6-terra",
 "entities": [{"canonical": "Udayaditya", "bengali": "উদয়াদিত্য",
               "kind": "person", "forms": ["Udayaditya", "Udayaditya's"]}]}
```

```
make -C proper_nouns/survey anchor        # en, ja and hi
make -C proper_nouns/survey anchor-hi.jsonl
```

or directly:

```
uv run proper_nouns/survey/anchor.py proper_nouns/survey/hi.jsonl -m openai:gpt-5.6-terra
```

- `survey` - a survey JSONL for the target language
- `-m/--model` (required)
- `-n/--names` - the Bengali names per chapter (default: `normalized-bn.jsonl`
  next to the survey)
- `-o/--output` - default: `anchor-<name>.jsonl` next to the input
- `-l/--lang` - language name to tell the model (default: the survey's
  `target_lang`)
- `-c/--chapter` - redo only these chapters (comma separated), counting every
  other chapter's renderings as settled; otherwise already-anchored chapters
  are skipped, so a run resumes where the last one stopped
