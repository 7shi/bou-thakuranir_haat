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

## Clustering by entity - `cluster.py`

The survey records spelling as found, so one name is spread over many entries:
inflected (প্রতাপাদিত্যের), shortened (প্রতাপ), and now and then misspelled
(প্রতপাদিত্য). `cluster.py` groups a survey's forms by the name they spell and
gives each group that name's base form, which is what makes the misspellings
stand out.

Grouping is by **name, not by referent**. A character called by name, by
title, by kinship term and by epithet yields four entries, not one: the
glossary is a table of spellings, so collapsing নারায়ণ and বিধাতা into one
entity, or filing প্রতাপাদিত্য under মহারাজ, would destroy exactly what it
records. Each entity carries a `kind` (`person`, `place`, `title`, `other`) so
the titles and forms of address can be told apart later.

The canonical form is the name's base form and is allowed not to appear among
the forms: a name whose every occurrence in a chapter is case-marked has no
uninflected form to pick from.

Chapters are processed in order, and each call carries the names the earlier
chapters settled - base form and kind, one line each. That is what keeps a
name to one spelling across the book, with no separate reconciliation pass
afterwards, and it is also what catches a chapter where a name is misspelled
in every one of its occurrences: with the established spelling in hand, the
chapter's own is read as a variant of it rather than becoming a name of its
own. The list is given as a reference, not a checklist - a chapter is free to
introduce names that are not on it. Redoing a chapter with `-c` counts every
other chapter's names as established, whichever side of it they fall on.

The unit is the **chapter**. A chapter holds few enough distinct forms for one
call to cover exhaustively and for a human to check afterwards (Bengali: 11 at
the least, 29 typically, 48 at most), while its recurring cast is the context
that tells the model two spellings are the same person. The whole corpus at
once (361 distinct Bengali forms) invites dropped and invented forms. Grouping
mechanically instead is not enough either: blocking on a prefix collects Indic
suffix inflection well, but splits any variant that differs near the head of
the word - exactly the drift being looked for.

Every answer is checked to be a partition of that chapter's forms: same set,
no duplicates, nothing invented. A chapter that fails is retried with the
offending forms named.

Bengali only for now. It is the source language, and the other three are meant
to be tied to its entities rather than clustered on their own.

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

`-N` applies the corrections to the clustered chapters and writes
`normalized-<lang>.jsonl`, which keeps the per-chapter shape: one record per
chapter, listing the names that chapter uses with their canonical spelling,
kind, and the forms found there. For Bengali, 359 forms across 37 chapters
resolve to 180 names, 5 to 29 of them per chapter.

The list stays per chapter because that is how it gets used: anchoring
another language to Bengali happens a chapter at a time, and what should be
offered to the model is that chapter's two or three dozen names, not the
book's entire cast - a full list only invites matches to characters who are
not in the passage. `collect_names()` aggregates the records into one entry
per name (canonical, kind, every form found anywhere, and the chapters it
appears in) for whatever needs the corpus-wide view, such as rebuilding
`all.tsv`.

```
make -C proper_nouns/survey normalized-bn.jsonl
```

Folding applies the corrections held in `REASSIGN`, `MERGE`, `KINDS` and
`DROP` at the top of `cluster.py`. They are hard-coded there, rather than
edited into `cluster-<lang>.jsonl`, so that the clustered file stays a plain
record of what the model answered and re-running a chapter cannot silently
lose them. Each was checked against `all/bn.md`:

- **Reassigned.** A form filed under the wrong name, mostly where the survey
  split a two-word name across two entries and left the chapter's clustering
  two halves to place: chapter 2's রায়ের belongs to প্রতাপাদিত্য rather than
  বসন্তরায় (the same chapter's বসন্ত রায়কে really is Basantaray); chapter
  11's রাম and চন্দ্র are the one name রাম চন্দ্র written with a space;
  chapter 28's রাম, রাম! is the god invoked in dismay, as in chapter 4, not
  Ramchandra Ray; chapter 33's পরাণ is a villager - পরাণ ও হরি দুই ভাই আসিল -
  not the word প্রাণ it was filed under.
- **Merged.** Names the chapters settled separately that the text shows to be
  one: রমাই, রমাই ঠাকুর and রমাই ভাঁড় are the jester, who is also called
  সেনাপতি রমাই in jest after he bests the general in a battle of wit; উদয় is
  short for উদয়াদিত্য.
- **Dropped.** তাঁর, তাহা and তোরা - pronouns the survey mistook for forms of
  address.
