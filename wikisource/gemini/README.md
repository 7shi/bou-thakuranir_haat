# Gemini Translation Driver (first generation)

The translation driver that produced the first English, Hindi and Japanese
versions of the novel, in [`../en/`](../en/), [`../hi/`](../hi/) and
[`../ja/`](../ja/). It is carried over from an earlier project that translated
Dante's *Divine Comedy*, and was not rewritten for this book - the traces are
visible and are listed under [Inherited quirks](#inherited-quirks) below.

This is a first-generation implementation: `google-generativeai` with
`gemini-pro`, three source lines per request, one chat per chapter. The
translations the repository uses now are in [`../../all/`](../../all/), made
by [`../../scripts/`](../../scripts/) and line-aligned under
[`../../all/aligned/`](../../all/aligned/). What lives here is kept as the
record of how the first pass was made, and because
[`../concat.py`](../concat.py) still reads its XML files to reproduce the
Bengali source.

Needs `GOOGLE_API_KEY` in the environment.

## How a translation run works

`translate.py` walks `../chapters/NN.txt` and, for each chapter, opens one
chat and sends the text three lines at a time - extended past three until a
line ends in a full stop, so a sentence is not split across requests. Lines go
out numbered, with the instruction to translate each line literally, and the
numbering is what lets the answer be matched back line for line.

Every chapter becomes one XML file of query records:

```xml
<query>
<info>[Chapter 1] 1/49</info>
<prompt>
Please translate each line literally into English.

# বৌ-ঠাকুরাণীর হাট
</prompt>
<result>
# Bou-Thakurani's Market
</result>
</query>
```

Prompt and answer are both kept. That is what allows [`../concat.py`](../concat.py)
to rebuild either side later - `-p` for the Bengali that was sent,
without it for the translation that came back.

`init.xml` is the few-shot prelude replayed at the head of every chat so that
names stay consistent across chapters: the title, the first heading, the
opening lines, and a hand-added query that translates the main proper nouns in
one go. `translate.py` generates it from the start of chapter 1 when it is
missing; the committed ones were edited by hand from there.

A response is rejected and retried when it is more than three times the length
of the prompt (six for a two-language run), or, with `--need-space`, when a
numbered line comes back without spaces in it. Requests are throttled to 60
per 62 seconds.

## Files

- **`translate.py`** - the run above. `--need-space` and `-3` (always send
  exactly three lines) on top of the shared options.
- **`gemini.py`** - the API call itself: model setup (`gemini-pro`,
  temperature 0.1, safety filters off), chat history, rate limiting, retries.
- **`common.py`** - the `query` record type, and reading and writing the
  query XML files.
- **`xml7shi.py`** - the small XML reader/writer everything here is built on;
  [`../convert.py`](../convert.py) and [`../concat.py`](../concat.py) use it
  too.
- **`option.py`** - shared argument parsing and the per-chapter file loop.
  Skips a chapter whose output XML already exists, so an interrupted run
  resumes.
- **`pickup.py`** - collect the queries that came back without a result into
  an error XML for review (`-t`: the ones whose result is not a well-formed
  table).
- **`redo.py`** - re-run the queries an error XML names.
- **`replace.py`** - splice corrected answers back into the chapter XMLs.

## Options

Shared by `translate.py` through `option.py`:

option | meaning
-------|--------
`-d dir` | subdirectory to walk (default: the three canticle names)
`-i file` | few-shot prelude (default: `init.xml`)
`-n num` | re-send the prelude every *num* queries (default 10)
`-r num` | highest chapter number to try (default 35)
`-1` | stop after one chapter
`--no-retry` | do not retry failed queries
`--no-show` | do not echo queries and responses

## Per-language Makefiles

Each of `../en/`, `../hi/` and `../ja/` has a Makefile wrapping these scripts:

target | what it does
-------|-------------
`translate` | run `translate.py` into `chapters/`
`check` | `pickup.py` the failures into `1-error.xml`
`redo` / `redo1` | re-run those queries, all at once or one at a time
`backup` | copy `chapters/` to `chapters.orig`
`replace` | `backup`, then splice `1-error-ok.xml` back in
`archive` | tar up `chapters/`

## Inherited quirks

Nothing here was renamed after the move from Dante, so:

- `-d` defaults to `inferno purgatorio paradiso`, none of which exist here.
- `-r` defaults to 35, two short of this book's 37 chapters.
- Progress is labelled "Canto", built from the capitalized directory name, so
  this code would announce a chapter as `[Chapters Canto 1]`. The committed
  XMLs say `[Chapter 1]`, which means the copy that actually produced them
  differed from the one committed here.

The committed Makefiles pass only `-n 1`, so a rerun needs `-d chapters -r 37`
on top of that to walk this book at all.

## Origin

- [dante-gemini](https://github.com/7shi/dante-gemini) - A multilingual
  exploration of Dante's Divine Comedy using Gemini 1.0 Pro, featuring
  detailed linguistic analysis of the opening lines in Italian, English,
  Hindi, Chinese, Ancient Greek, Arabic, Bengali and other languages with
  word-by-word breakdowns, grammatical details, and etymologies.

The scripts here are that project's driver, brought over as it stood -
`gemini-pro` being the same Gemini 1.0 Pro it was written against.
