# MEMO

## Translated segments lose the source's line breaks

`all/en-gemini.jsonl` and `all/ja-gemini.jsonl` (produced by
`scripts/translate_segments.py`) store each segment's translation as a
single JSON string in `response.translation`. The source text
(`wikisource/chapters/NN.txt`) has one line per line of dialogue/narration —
37 chapters, 1,159 lines total, ~31 lines/chapter — but the translated
segments collapse almost all of that structure: each segment typically ends
up as one giant paragraph with only 10-14 embedded `\n` left (vs. dozens in
the corresponding source lines), some running past 4,000 characters with no
line break at all.

Likely cause: `SegmentTranslation.translation` in
`scripts/translate_segments.py` (`Field(description="Complete translation of
the segment text into the target language")`) gives the model no
instruction to preserve the source's per-line/per-utterance structure, so it
naturally produces flowing prose instead of mirroring the original line
breaks.

Discovered while building `qa-eval/opencode/`: `extract.py` writes these
segments out verbatim as chapter `.txt` files for `opencode run -f`
(`qa-eval/opencode/make_ceiling.py`), and opencode's file-attachment reader
truncates any single line past 2,000 characters (confirmed by reading
opencode's own source — `packages/opencode/src/tool/read.ts`,
`MAX_LINE_LENGTH = 2000`), silently dropping content past the cut. The
original report was English chapter 37 (`opencode run -f en/37.txt`): the
model claimed the file was truncated mid-sentence and refused to use content
past that point, even though the underlying line was intact.

Only English segments actually cross that 2,000-char threshold — Japanese
never does (max 1,326 chars, ch25 seg1). 14 English segments across 13
chapters exceed it:

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
| 19 | 2 | 2,198 |
| 28 | 1 | 2,107 |
| 31 | 1 | 2,130 |
| 17 | 1 | 2,064 |
| 3  | 1 | 2,367 |

Worked around in `qa-eval/opencode/` by having `extract.py` wrap each line
to 1,800 columns before writing (content-preserving — verified byte-for-byte
on the non-whitespace characters across all 37 chapters × 2 languages), but
that's a downstream patch, not a fix to the actual translation data.

**Not fixing now** — re-running `translate_segments.py` would mean
re-translating (or at least re-diffing) `all/en-gemini.jsonl` and
`all/ja-gemini.jsonl`, which a lot of `qa-eval/` results are built on top of.
If this is revisited: have `SegmentTranslation.translation`'s field
description ask the model to preserve the source segment's paragraph/line
breaks, and check whether that alone is enough or whether the prompt in
`translate_segment()` needs the same instruction.
