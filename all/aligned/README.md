# Aligned translations

The segment translations in [`../en-gemini.jsonl`](../en-gemini.jsonl) and
[`../ja-gemini.jsonl`](../ja-gemini.jsonl) lost the source's line structure.
This directory holds the same translations with the line breaks put back.

## Contents

| File | Bytes | |
| --- | --- | --- |
| `en-gemini-terra.delta.jsonl` | 7,021 | **English, `gpt-5.6-terra` - the aligned English text** |
| `ja-gemini-terra.delta.jsonl` | 4,311 | **Japanese, `gpt-5.6-terra` - the aligned Japanese text** |
| `en-gemini-luna.delta.jsonl` | 6,976 | English, `gpt-5.6-luna` - comparison record |
| `ja-gemini-luna.delta.jsonl` | 4,377 | Japanese, `gpt-5.6-luna` - comparison record |
| `en-gemini-luna-test.jsonl` | 329,707 | the discarded first run, kept as a test fixture |

The two Terra files are the aligned text. The two Luna files are the losing side
of the model comparison, kept as a record and not worked on further.

A `.delta.jsonl` is not the aligned data itself but the edits that produce it
(decision 7). Unpack before use:

```
uv run scripts/pack_aligned.py unpack all/aligned/ja-gemini-terra.delta.jsonl
```

That writes `ja-gemini-terra.jsonl`, which `.gitignore` excludes - the unpacked
files are derived and never committed.

`en-gemini-luna-test.jsonl` is stored raw instead. It is the first English run,
produced by an earlier prompt that also asked for proofreading: 55 of its 82
segments are violations under the current checks, 11 of them leaking Bengali
into the output. It is not a candidate for publication and must never be resumed
onto or merged into the aligned files. It is kept for two reasons - it is the
only artefact of a prompt that no longer exists in the code, so no amount of
money reproduces it; and the checks below were tuned against it, so it is the
fixture for any future re-tuning. Storing it as a delta would only save 3.1x
against the 35-91x the others get, because it rewrote the text rather than
re-flowing it.

### The prompt that produced it

`align_lines.py` was never committed at that stage, so the prompt survives only
in the session logs. Recovered from the edit history there, it read:

```
The text above is an existing translation of the numbered source lines. It was produced as flowing prose, so the source's line structure was lost.

Primary task: re-emit that translation with the source's line structure restored. Prefix every line with its source line number, numbered consecutively from 1, one output line per source line, in order.

Secondary task: while doing so, proofread the translation against the source. Correct mistranslations, grammatical errors and unnatural phrasing.

Constraints:
- Leave anything that is already correct and natural unchanged. Keep corrections local to what needs fixing; do not rewrite for stylistic or vocabulary preference.
- The line structure takes priority over prose flow. Never merge, split or drop a source line to make the result read better.
- Output the numbered lines only. No commentary, no headings, no blank lines.
```

with the per-segment noun list already carried as its own message, closing on:

```
- The words listed above are fixed proper nouns, not ordinary vocabulary. Keep whatever rendering the existing translation already uses for each of them, and never replace one with a more familiar or more readable equivalent.
```

Two differences from the current prompt account for what the run produced. It
asked for proofreading as an explicit secondary task, which is where the drift
came from - and why decision 2 now refuses it. And it never said what language to
answer in: `Every output line must be written in {target_lang}. Never copy a word
or a line of the source text into the output, and never re-translate the source`
was added afterwards, in response to this run's 11 leaking segments. The current
`INSTRUCTIONS` in `align_lines.py` is what remained after both changes.

Two caveats on reading the file as a single artefact. The proper-noun constraint
was in flux around it: an inline `Keep every proper noun... "Mahishi" must stay
"Mahishi" and must not become "queen"` rule had been tried and removed nine
minutes before the run started, replaced by the per-segment noun list above. And
the file is not uniform - the run wrote all 82 segments, but 11:1, 11:3, 13:1 and
16:1 were later overwritten by `-s` redos under the amended prompt, the one that
had gained the `{target_lang}` line. Everything else is the original run.

## Why

`scripts/translate_segments.py` stores each segment's translation as a single
JSON string in `response.translation`. The source
(`wikisource/chapters/NN.txt`) has one line per line of dialogue or narration -
37 chapters, 1,159 lines, ~31 lines per chapter - but the translations collapse
almost all of it: a segment is typically one giant paragraph with 10-14 embedded
`\n` left where the source had dozens, some running past 4,000 characters with
no line break at all.

The cause is that `SegmentTranslation.translation`
(`Field(description="Complete translation of the segment text into the target
language")`) never asks the model to preserve the source's per-line structure,
so it produces flowing prose.

This surfaced while building `qa-eval/opencode/`. Its `extract.py` writes the
segments out verbatim as chapter `.txt` files for `opencode run -f`, and
opencode's file-attachment reader truncates any single line past 2,000
characters (`packages/opencode/src/tool/read.ts`, `MAX_LINE_LENGTH = 2000`),
silently dropping the rest. English chapter 37 was the original report: the model
claimed the file was cut mid-sentence and refused to use anything past that
point, though the underlying line was intact.

Only English crosses that threshold - Japanese never does (max 1,326 chars,
25:1). 14 English segments across 13 chapters exceed it:

| Chapter | Segment | Max line (chars) |
| --- | --- | --- |
| 5  | 1 | 4,473 |
| 37 | 1 | 3,957 |
| 25 | 1 | 3,333 |
| 32 | 1 | 2,633 |
| 29 | 2 | 2,620 |
| 30 | 1 | 2,569 |
| 29 | 3 | 2,442 |
| 8  | 1 | 2,444 |
| 34 | 1 | 2,242 |
| 3  | 1 | 2,367 |
| 19 | 2 | 2,198 |
| 31 | 1 | 2,130 |
| 28 | 1 | 2,107 |
| 17 | 1 | 2,064 |

`qa-eval/opencode/extract.py` works around it by wrapping every line to 1,800
columns before writing (content-preserving - verified byte-for-byte on the
non-whitespace characters across all 37 chapters and both languages), but that
is a downstream patch, not a fix to the data.

## The pass

Re-running `translate_segments.py` would invalidate the `qa-eval/` results built
on the current translations, so
[`../../scripts/align_lines.py`](../../scripts/align_lines.py) re-flows the
existing translations onto the source's line structure as a post-processing
pass instead. It inserts line breaks; it does not edit the translation.

```
uv run scripts/align_lines.py all/en-gemini.jsonl -m openai:gpt-5.6-terra -o all/aligned/en-gemini-terra.jsonl
uv run scripts/align_lines.py all/ja-gemini.jsonl -m openai:gpt-5.6-terra -o all/aligned/ja-gemini-terra.jsonl
```

Add `-s 37:1` to redo a single segment, or `-s 11:1,16:1` for several. Defaults
for `--source` (`all/bn.md`), `--segmentation` (`segmentations.jsonl`) and
`--proper-nouns` (`proper_nouns/all.tsv`) rarely need overriding.

The first-generation translator (`wikisource/gemini/translate.py`, used for
Dante) never had this problem because line identity was part of the wire format:
every source line was sent with a number, the model answered with the same
numbers, and `common.read_source()` reassembled by number. Breakage was
detectable (`send_lines()`'s `check`), collectable (`pickup.py`) and re-runnable
(`redo.py`). The second generation dropped that scaffolding when it moved to
structured output. This pass restores the numbering idea as the alignment
protocol.

## Results

Both models, both languages, 82 segments each:

| Output | Model | Violations | Time |
| --- | --- | --- | --- |
| `en-gemini-terra` | `gpt-5.6-terra` | **0/82** | 11m19s |
| `en-gemini-luna` | `gpt-5.6-luna` | 5/82 | 12m21s |
| `ja-gemini-terra` | `gpt-5.6-terra` | **2/82**, then 1/82 | 15m30s |
| `ja-gemini-luna` | `gpt-5.6-luna` | 3/82 | 17m12s |

56m22s of wall clock in total. Luna is the lighter model but ran slower in both
languages.

**Terra wins both languages**, and both of Luna's predicted failure modes appear
in its list and in neither Terra run:

- Dropped or repacked lines - English 6:1 (`line count 9 != 8`), 18:1 (`8 != 6`)
  and 31:1 (`26 != 21`). 31:1 loses five lines at 0.0% drift, so the text is all
  there and the line breaks are not.
- A proper noun quietly re-rendered - `Yubaraj 12->11` in English 3:1,
  `ウダヤディティヤ 15->14` in Japanese 34:1.
- On top of that, Luna's two English drift violations sit at 1.3-1.5%, the range
  of the runs that were asked to proofread, so it also went back to correcting
  the text.

Terra's flags were both `check_proportions` in Japanese at 0.0% drift, and both
were read against `../ja-gemini.jsonl`:

- **8:2 line 9 is a false positive.** The line is long because the original
  translation carries a translator's note there - `（訳注：アーディティヤは太陽神で
  あり…）`, 96 characters of it - which the aligned output reproduces faithfully.
  The pairing is correct. Both models flag this same line at the same 2.27x.
- **30:1 line 3 was a real misalignment.** Source line 1 ends with Sitaram's
  `“যুবরাজ, নৌকায় উঠুন।”`; the output moved that utterance down into line 2 and
  packed the next two - the prince's `“কেন, নৌকায় কেন?”` and Sitaram's reply -
  together into line 3. 16 lines for 16 at 0.0% drift, with two lines attached to
  the wrong source lines. Exactly what `check_proportions` exists for, and it
  found it with no other line disturbed. Redone with `-s 30:1` on the same model
  and correct on the second attempt.

So one real failure in 164 segments. What makes 30:1 hard is a source line of
1,083 characters ending in a short quoted line of dialogue, where the pull is to
start the new line at the quote.

**Final state: 0/82 English, 1/82 Japanese, that one being 8:2's false
positive.**

## Decisions

1. **`llm7shi`'s `Client`, no structured output.** The response is plain numbered
   text, so a schema buys nothing. See `~/repos/llm7shi/examples/essay.py` for
   `Client` usage (the schema argument is simply omitted here).
2. **Numbered source, unnumbered translation, numbered output.** The prompt
   carries the source segment with `N ` prefixes plus the existing translation as
   flowing text, and asks for the translation re-emitted with the same line
   numbers. It states one job:

   - Put the line breaks back, and nothing else. Reproduce the existing
     translation word for word.
   - Where the wording does not divide cleanly at a source line's boundary,
     adjust it at that boundary only: the fewest words moved, and only what the
     split itself makes necessary.
   - Change nothing else - wording, punctuation, spelling and names stay as they
     are, including anything the model judges to be a mistranslation, an error or
     an awkward phrase. Correcting it is out of scope.

   Proofreading is deliberately not asked for. Invited to correct the text, the
   model returns real fixes mixed with edits that cannot be accepted, in one
   undifferentiated diff: a segment-wide register shift (every contraction
   expanded), or a vocative rendered against the rest of the corpus - `Dada` to
   `Brother` in 11:1 while 23:2 in the same run kept `Ma`, where the corpus uses
   `Dada` 51 times against 9 for `Brother`. Nothing separates those from the
   genuine corrections without reading every site by hand. The originals' own
   mistranslations are out of scope under the acceptance criterion anyway, so
   declining them costs nothing, and a near-zero drift becomes a usable gate
   rather than a number to be interpreted.

   A vocative like `Dada` shows why this cannot be handled by widening the
   glossary instead: it is not a proper noun, it is not in
   `proper_nouns/all.tsv`, and the conventions that hold the corpus together are
   not enumerable in advance.

   A fourth message lists the proper nouns that occur in this segment, and adds
   one constraint: those words are fixed terms, and whatever rendering the
   existing translation uses for each of them must be kept. Naming the words is
   what matters - under a general "keep proper nouns unchanged" rule the model
   read `Mahishi` as an ordinary transliteration and turned it into `queen` in
   all three places of 37:1. The list is largely redundant with "reproduce word
   for word" and kept anyway: it costs almost nothing, and it names exactly the
   words whose substitution is hardest to spot.

   The list holds source-language headwords only, taken from
   `proper_nouns/all.tsv` by scanning the segment's source text, longest term
   first with matched spans masked so that `উদয়` is not reported inside
   `উদয়াদিত্য`. Two things it is deliberately not:

   - Not the target renderings. The existing translation is the authority on
     spelling, and the glossary has drifted from it - `বিভা` is `Bibha` in the TSV
     and `Vibha` in all 472 occurrences across the translations. Sending the
     glossary's spelling would invite a mass rewrite.
   - Not `proper_nouns/en.jsonl`. Its per-segment lists record only each term's
     first appearance, so segment 37:1 holds three terms and not `মহিষী` - the one
     that actually needed protecting.

   The cost is negligible: 10.8 terms per segment on average, 179 characters for
   37:1.
3. **No retry.** Run once, count the violations, report the totals.
   Retry/`redo.py`-style recovery is only worth building once the failure rate is
   known, and at one real failure in 164 segments it is not worth building.
4. **`-s` / `--segment` selects segments by name, for testing and for redoing
   failures.** The argument is `chapter:segment` or a comma-separated list
   (`-s 37:1`, `-s 11:1,11:3,13:1`). Without it the script processes everything
   and skips segments already present in the output file, so a run can be
   resumed - the same behaviour as `translate_segments.py`. With it, every named
   segment is processed and its existing record is overwritten rather than
   skipped, so a prompt change can be re-tested on the same segments and a batch
   of failures can be redone in one command, on one client, under one violation
   summary. Unknown references are all reported before anything runs. Overwriting
   means the output cannot be a pure append: the record is replaced in place,
   rewriting the JSONL file.
5. **Write to new files; never overwrite the originals.** `../en-gemini.jsonl`
   and `../ja-gemini.jsonl` stay untouched, and `qa-eval/` keeps evaluating
   against them - re-running those evaluations would burn a large amount of
   compute for no gain.

   The aligned records carry the translation only - no `summary`, no
   `translation_notes`. Those exist in the originals to feed the running story
   context of `translate_segments.py`, and this pass has no use for them. An
   aligned file is therefore a translation overlay on the original, not a
   replacement for it; see decision 8.
6. **`-m` / `--model` is required.** The script takes the model on the command
   line with no default, the same as `scripts/translate_segments.py`. It is not
   wired into the Makefile.

   The candidates were `openai:gpt-5.6-luna` and `openai:gpt-5.6-terra`, not the
   `gemini-2.5-pro` that produced the original translations. GPT-5.6 runs
   Sol/Terra/Luna in descending capability; Luna is the lightest. In the
   67-language benchmark in `~/repos/multilingual-reader/examples/tr/README.md`
   Luna is the strongest and most stable model measured (mean 90.39, stdev 8.13,
   Bengali 93 - the top score for that language) and it is cheap. Terra scored
   below it there, on short-passage translation where it produced artefacts; this
   task is neither short nor a translation, so that ranking did not carry over on
   its own.

   It did not carry over in practice either, first on a three-segment trial and
   then on the full runs. Terra's cost was a heavier hand on the text, and that
   did not survive the current prompt: its remaining flags are all at 0.0% drift.
   See Results above.

   Whichever had won, the choice was bounded: this pass re-flows rather than
   re-translates, so the existing translation anchors the output and the result
   cannot be rewritten wholesale.
7. **Store the aligned files as deltas, not as copies.**
   [`../../scripts/pack_aligned.py`](../../scripts/pack_aligned.py) packs an
   aligned JSONL into the edits that turn the base translations into it, and
   unpacks it back:

   ```
   uv run scripts/pack_aligned.py pack   all/aligned/ja-gemini-terra.jsonl
   uv run scripts/pack_aligned.py unpack all/aligned/ja-gemini-terra.delta.jsonl
   ```

   The pass re-flows rather than re-translates, so an aligned file is very nearly
   a copy of its base - the same words with line breaks inserted and a word or
   two moved at the seams. Storing the whole thing costs 300-400 KB per file to
   say something the repository already contains, and buries the part that is
   actually new.

   | | raw | delta |
   | --- | --- | --- |
   | `en-gemini-terra` | 313,707 | 7,021 |
   | `en-gemini-luna` | 313,424 | 6,976 |
   | `ja-gemini-terra` | 418,894 | 4,311 |
   | `ja-gemini-luna` | 418,808 | 4,377 |

   1.4 MB becomes 22.7 KB, and the delta is reviewable: a record whose `ops` is
   `[]` had nothing to re-flow, and every other one shows its seams as text.

   The format is `difflib` opcodes over the translation string, as
   `[start, end, replacement]`. The tag is dropped because it carries no
   information - every opcode is a replacement of `before[start:end]`, an insert
   has `start == end` and a delete an empty replacement. `autojunk=False` for the
   same reason as in the drift check: the default treats the letters the text is
   made of as noise, and produces a much larger delta.

   The alternative considered and rejected was **storing line-break offsets
   only**. It cannot represent the seam edits: 28 of 82 English segments are not
   pure newline insertions (Japanese is better at 81 of 82, but splitting the
   format by language buys nothing). Plain gzip was also measured - 106-122 KB
   per file, an order of magnitude worse than the delta.

   Two properties make this safe to rely on:

   - **`pack` refuses to write a delta it cannot round-trip.** It rebuilds the
     file from its own output in memory and compares the bytes before creating
     anything, so a delta on disk is one already proved reversible. All four were
     then re-verified through the real `unpack` path: byte-identical.
   - **The base is pinned by hash.** The header records the base file and its
     SHA-256, and `unpack` refuses to run against a base that has changed - the
     failure mode otherwise is silent corruption, not an error. Both bases are
     committed and unmodified, so the hash is fixed by git history.

   Only the constant fields are hoisted into the header (`source_lang`,
   `target_lang`, `model`); `pack` checks that they really are constant rather
   than assuming it.
8. **Regenerate `all/*.md` from the aligned data and deploy that.** Because an
   aligned file holds translations only, `jsonl_to_md.py` takes two files: the
   original JSONL for the structure, `summary` and `translation_notes`, and the
   aligned JSONL passed as `-a`/`--aligned` to substitute in for the
   translations. That keeps `--mode summary` and `--mode full` working, and the
   originals stay untouched as decision 5 requires.

   ```
   uv run scripts/jsonl_to_md.py all/en-gemini.jsonl -a all/aligned/en-gemini-terra.jsonl
   ```

   `make convert` does this for English and Japanese, with a pattern rule that
   unpacks a delta into the file it needs; `make unpack` is the same step on its
   own. Hindi and modern Bengali have not been aligned and convert as before, so
   `make deploy` waits until they have and all five languages change over in one
   deployment.

   The substitution is required to be exact in both directions - every base
   segment aligned, every aligned segment placed - because a partial overlay
   would publish flowing prose next to aligned text without saying so. All 82
   segments pair in both languages.

   Effect on the published text: Japanese is the same characters with different
   line breaks (identical ignoring whitespace), English differs slightly at the
   seams as decision 2 allows, and the longest English line drops from 4,473 to
   3,333 characters. `make build` and `make deploy` need no change.

## Verification

Every check reports a failure the current prompt is not allowed to produce, so a
violation means the segment needs redoing. Nothing is rejected automatically
(decision 3); the run counts and lists them.

- **Structure matched**: the output's line numbering is contiguous and its line
  count matches the source segment's. This is the actual goal, so mismatches are
  counted per segment and in total.
- **Line proportions**: a matching line count does not mean the lines match up.
  Each output line's length is divided by its source line's and compared against
  the segment's own median ratio; anything outside 0.5x-2.0x is reported as
  `line 3 is 0.41x the expected length`. Shifted lines are paired with the wrong
  source line and stop being proportionate, which is the only visible trace of
  the failure 16:1 produced twice: one source line split in two, another dropped
  or merged to compensate, and 11 lines returned for 11. The median is per
  segment because the target-to-source length ratio varies by language and by
  passage; lines of 40 characters or less are skipped, since an interjection can
  legitimately be half or twice its source's length. Tuned on
  `en-gemini-luna-test.jsonl`: it flags 16:1 alone across 82 segments, with no
  false positives. It caught the one real failure of the final runs (Japanese
  30:1) and produced one false positive there (8:2, a translator's note).
- **No source-language leak**: characters that the source has and the existing
  translation does not must not appear in the output. That definition names no
  alphabet, so it catches Bengali in English and in Japanese output alike; both
  halves are needed, since letters the translation lacks are otherwise ordinary
  (a segment with no `x` in it) and letters the source has are otherwise shared
  (Bengali text carries ASCII digits and punctuation). Letters only - a newline or
  a curly quote is a re-flow artefact, not carried-over source text.
  `en-gemini-luna-test.jsonl` leaked into 11 of its 82 segments: three
  re-translated into Bengali wholesale, one re-emitted the source verbatim, the
  rest left a proper noun or a single line in the original script. Validated
  against it - flags exactly those 11 and nothing else.
- **Glossary preserved**: for each term in the target-language column of
  `proper_nouns/all.tsv`, compare its occurrence count before and after. A drop
  is reported as `Mahishi 3->0`. Counts rather than mere presence, so a term
  replaced in one place out of three still shows. The glossary is only used here
  and for the prompt's noun list, never sent wholesale. Note what it cannot see:
  `Dada`, `Ma` and the other vocatives are not proper nouns and not in the TSV,
  so a model that renders them differently passes this check silently - which is
  why decision 2 forbids the edit rather than trying to detect it.
- **Content drift**: compare the whitespace-stripped output (after stripping the
  `^\d+\s+` line-number prefixes) against the same normalisation of the original
  translation. Only the seams may move, so anything above `DRIFT_LIMIT` (1.0%) is
  reported as `drift over 1.0%` and means the model went back to proofreading.
  The limit sits between the 0.38% of a re-flow with no corrections and the
  1.3-2.6% of the runs that were asked to proofread.

  Two things distort this measurement if left alone. Straight and curly quotes
  are folded together first, because the originals mix them (717 straight vs 378
  curly apostrophes across `../en-gemini.jsonl`) and a model that merely settled
  on one style would otherwise register as drift; only the comparison is folded,
  since the stored text's quotes are directionally correct in a way a regex could
  not reproduce. And `difflib.SequenceMatcher` needs `autojunk=False` - its
  default treats any character occurring in over 1% of a long string as noise,
  which here means the letters the comparison is made of, and inflated the
  reported drift several-fold.

## Acceptance criterion

The aligned text must be **the same translation with line breaks in it**. The
originals already contain mistranslations; those stay, because a pass that
corrects some of them also changes things it should not, and the two cannot be
told apart at review time (decision 2). So the bar is not "no new
mistranslations" but "no new anything": text identical to the original apart from
what a line break at that point requires.

That makes the review mechanical. The checks measure exactly this, and a run with
no violations needs no reading; only violations get a word diff against the base.

## Open points

- One source line does not always map to exactly one translated line (a Bengali
  line can become two English sentences, or vice versa). Strict 1:1 is the goal,
  not a hard requirement; the run reports how often it fails.
- The hardest place for the model is a source line holding two utterances - the
  pull is to give each its own output line and then merge two other lines to keep
  the count. `check_proportions` exists for that case, and Japanese 30:1 is what
  it looks like in practice.
- The aligned text still diverges from the evaluated text, now only at the seams.
  Decision 5 keeps `qa-eval/` on the original files; the two remain separate
  artefacts and must not be treated as interchangeable.
- The noun list still carries a little noise: `রাম` and `রায়` survive masking
  because the source spells Rammohan `রামমােহন` while the glossary headword uses a
  different composition, so the longer term never matches. Harmless - every listed
  word is a real proper noun, and the list only marks which words are fixed terms.
  Glossary coverage itself is fine: 142 of 143 headwords occur in the source.
- Only English actually needs this for the opencode truncation problem (Japanese
  never crosses 2,000 chars), but both languages are processed so the published
  text is consistent.
- **The pass does not solve the 2,000-character problem on its own.** 13 English
  segments still exceed it after alignment, against 14 before, because the source
  lines themselves are that long: 25:1's longest source line is 2,875 characters,
  so its English cannot come in under about 3,300 while 1:1 holds. What alignment
  fixes is the other kind of long line - 5:1 and 37:1, where the source lines were
  short and the translation had collapsed several into one.
  `qa-eval/opencode/extract.py`'s 1,800-column wrap is therefore permanent, not a
  fallback for failed segments.
