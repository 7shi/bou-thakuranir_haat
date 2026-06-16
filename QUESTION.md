# Question Set Deduplication & Cross-Lingual Alignment Plan

## Background

The evaluation question sets (`questions-en.jsonl`, `questions-ja.jsonl`, 100 each)
were generated **independently per language** by `scripts/create_rag_questions.py`.
This means the English and Japanese sets are not parallel, and within each language
many questions are semantic duplicates (they cover the same central plot events,
e.g. Udayaditya's prison escape, Pratapaditya's decision to kill Basanta Ray).

Duplicate detection is done by `scripts/check_duplicates.py`:
- Embed every question (`embeddinggemma`, no prefix), sort others by cosine similarity.
- Every question acts as a **seed**; judge candidates top-down with an LLM
  (`ollama:gemma4:31b-it-qat`, plain `same`/`different`), stop after `--stop` (default 5)
  consecutive `different`. Judgments are cached symmetrically in a TSV
  (`q1<TAB>q2<TAB>same<TAB>selected`, 1-based, y/n) and reused forward or reverse.
- Aggregation phase: union-find over all `same` judgments → final groups.
- Per group, the user is prompted (`input()`) for which question to keep; the choice
  is stored in the `selected` column.

### Result so far (Japanese)
```
13 group(s) found.
Total: 100  Duplicates removed: 60  Unique: 40
```
Less than half the Japanese questions are semantically distinct.

## Goal

Build a single set of questions that is **identical across both languages**, so that
evaluation differences reflect language rather than differing question content.

## Pipeline

1. **English grouping** — run `check_duplicates.py -l en`, dedup the English set the
   same way as Japanese. *(STATUS: in progress — waiting on this result.)*

2. **Cross-lingual grouping** — translate `questions-ja.jsonl` into English, merge with
   `questions-en.jsonl` into one file, and run grouping on the combined set. Groups that
   span both halves reveal questions that exist in both languages. Provenance
   (EN-i / JA-i origin per merged line) must be tracked so originals can be mapped back.

3. **Identify the truly-unique set** — what remains after cross-lingual dedup is the set
   of genuinely distinct questions. Confirm the count.

4. **Round + align** — adjust to a round number, define the canonical set **in English**
   (a group's English representative; if the representative is JA-origin, use its English
   translation), then **translate English → Japanese** so both languages ask the exact
   same questions. This makes language differences measurable.

## To build

- **`scripts/translate_questions.py`** — translate a questions JSONL between languages.
  - For step 2: only the `question` field is needed (grouping ignores other fields).
  - For step 4: translate all fields (`question`, `answer`, `chapters`, `rationale`;
    `chapters` is language-independent and copied as-is).
  - Reuse `llm7shi` (`generate_with_schema` / `config_from_schema`) like
    `scripts/create_rag_questions.py` and `scripts/translate_segments.py`.
  - Use the proper-nouns dictionary under `proper_nouns/` for transliteration
    consistency, as `translate_segments.py` does.
  - **OPEN: which translation model** (project's main translations use Gemini; the dedup
    judge uses ollama gemma — confirm with user).

- **Merge helper** for step 2 (200-line combined JSONL with provenance), and a
  **final assembly** for step 4 (pick representatives, emit the parallel EN/JA sets).

## Division of labour

`check_duplicates.py` is interactive (the keep phase uses `input()`), so the **user runs
the grouping steps**; the assistant builds the translation/merge/assembly tooling.

## Key files
- `scripts/check_duplicates.py` — duplicate detection (done)
- `scripts/create_rag_questions.py` — original question generation (reference)
- `scripts/translate_segments.py` — chapter translation w/ proper nouns (reference)
- `questions-en.jsonl`, `questions-ja.jsonl` — the two question sets
- `questions-ja-cache.tsv` — Japanese grouping cache (done)
