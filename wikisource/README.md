# Wikisource Extraction and First-Pass Translation

This directory holds the pipeline that turned the Bengali Wikisource edition
of বৌ-ঠাকুরাণীর হাট into [`all/bn.md`](../all/bn.md), the source text every
later stage of the repository works from, together with the first English,
Hindi and Japanese translations of it.

The pipeline runs off a full `bnwikisource` XML dump rather than the live
site: one download, then everything else is local. The dump and the files
derived directly from it (`*.bz2`, `*.db`, `db-*.tsv`, `*.mw`) are ignored by
git, so a rerun from scratch starts with `make download`. The text files that
survive - `chapters/*.txt` and the translation XMLs - are committed.

## Pipeline

```
bnwikisource-YYYYMMDD-pages-articles-multistream.xml.bz2   make download
  -> tools/db-make.py, tools/db.sql -> dump.db             make db-make
  -> tools/mediawiki.py             -> index.mw
  -> extract.py                     -> chapters/*.mw, pages/*.mw   make extract
  -> convert.py                     -> chapters/*.txt      make convert
  -> gemini/translate.py            -> {en,hi,ja}/chapters/*.xml   make -C en
  -> concat.py                      -> ../all/bn.md        make text
```

## Makefile

`TITLE` names the work inside the dump; `TARGET1`/`TARGET2` name the wiki and
the dump date.

target | what it does
-------|-------------
`download` | fetch the dump from dumps.wikimedia.org
`db-make` | build `dump.db` - stream index and page table - from the dump
`extract` | pull this work's chapter and scan-page wikitext into `chapters/` and `pages/`
`convert` | render the wikitext to plain text as `chapters/*.txt`
`text` | concatenate the query XMLs into `../all/*.md`

## Scripts

- **`extract.py`** - reads `index.mw` for the work's table of contents, writes
  one `chapters/NN.mw` per chapter, and pulls every scanned page of the
  underlying PDF into `pages/NNN.mw`. Chapters on Wikisource are transclusions
  of page ranges, so both halves are needed.
- **`convert.py`** - resolves those transclusions (`<pages from= to=>`,
  optionally section-bounded) and renders the wikitext into paragraph-per-line
  plain text: templates such as `{{gap}}` and `{{nop}}` dropped, `{{C|...}}`
  and `{{larger|...}}` turned into headings, `{{block center}}` and `:` turned
  into indentation, poem blocks kept as separate lines.
- **`concat.py`** - collects the query XMLs into one markdown file, taking the
  last line of each query's `<prompt>` with `-p` (the Bengali that was sent)
  or of its `<result>` without (the translation that came back).
- **`common.mk`** - the `DIRS`/`XMLS` variables shared by the three
  per-language Makefiles.

## `tools/` - dump handling

- **`db-make.py`** - walks the multistream dump, writing `db-*.tsv`: stream
  offsets, page titles, namespaces, language links and templates.
- **`db.sql`** - loads those TSVs into `dump.db` and indexes them.
- **`mediawiki_parse.py`** - the bz2 stream and `<page>` parsing that
  `db-make.py` builds on.
- **`mediawiki.py`** - the `DB` class the rest of the pipeline uses to fetch a
  page by title or id, decompressing only the stream that holds it; also a CLI
  for dumping a page or the site's table of contents.
- **`splitrans.py`** - a clipboard shuttle for translating a file by hand
  through a web translator, block by block. Not part of the automated flow.

## `gemini/` - the translation driver

The Gemini API driver that produced the first English, Hindi and Japanese
versions, carried over from an earlier Divine Comedy translation project and
first-generation throughout. Documented separately in
[`gemini/README.md`](gemini/README.md), along with the quirks that came with
it - among them a chapter loop that stops two chapters short of this book.

## Per-language directories

`en/`, `hi/` and `ja/` each hold a `Makefile`, an `init.xml` few-shot prelude,
and one `chapters/NN.xml` per chapter holding the prompts sent and the
answers received. See [`gemini/README.md`](gemini/README.md) for the record
format and the Makefile targets.

Note that `xml7shi.py` lives in `gemini/`, so `convert.py` and `concat.py`
import it from there even though they have nothing else to do with the
translation driver.

## Notes

- `concat.py` normalizes the vowel sign O while assembling the text: the
  Wikisource edition writes it both as the single sign and as the pair AA + E
  (822 times), which renders almost alike but is a different string, enough to
  read as a spelling variant when proper nouns are compared. `chapters/*.txt`
  and the `<prompt>` sections keep the original spelling, since those record
  what was actually digitized and sent.
- The translations here are the first pass, made with the Gemini API against
  the raw text (see [`gemini/README.md`](gemini/README.md)). The translations
  the repository uses now are in [`all/`](../all/), built by
  [`scripts/`](../scripts/) and line-aligned under
  [`all/aligned/`](../all/aligned/). `make text` still rewrites
  `../all/{en,hi,ja}-gemini.md` from these older XMLs, so run only the
  `../all/bn.md` line of that target unless you mean to overwrite them.
