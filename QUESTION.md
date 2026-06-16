# RAG Question Set Rebuild Plan (anchor-based)

## Goal

Rebuild the evaluation question sets so they are **structurally non-duplicating**
and **detail-oriented** (good for RAG: answerable only by closely reading specific
passages, not by recalling the broad plot). Target **50 questions**, defined in
English first, then translated to Japanese so both languages ask the same things.

## Why a new algorithm

The previous generator (`scripts/create_rag_questions.py`) uploaded the whole text
and asked for N questions in independent batches of 10. With no memory across
batches, every batch gravitated to the same salient events, so the 100-question
sets were heavily duplicated (English: only ~36 unique by `check_duplicates.py`).

The fix is to **anchor each question to a specific passage** instead of generating
freely over the whole text. Distinct anchors give coverage and avoid duplication;
grounding each question in the actual scene text (not a summary) keeps the
questions detail-level ("nitpicky").

## Data sources (all aligned by chapter / segment)

| Use | File | Content |
|---|---|---|
| Anchor design (overview) | `all/en-gemini-summary.md` | 82 scene summaries — used only to *select and link* anchors |
| Scene titles | `all/en-gemini.tsv` | 82 scene titles (`chapter`, `segment`, `title`) |
| Question grounding (detail) | `all/en-gemini.jsonl` | 82 scene **full texts** in `response.translation` |
| Japanese parallel text | `all/ja-gemini.jsonl`, `all/ja-gemini.tsv` | same structure, for reference |
| Transliteration dictionary | `proper_nouns/all.tsv` | proper-noun consistency for EN↔JA |

Summaries are only for the high-level *design* step. Question text must be grounded
in the full scene text, never the summary.

## Pipeline

1. **Anchor design** — feed the 82 summaries to the LLM in one pass; emit a coverage
   plan of **50 anchors**, split:
   - **(a) Single-passage — 25**: one scene each, chosen to cover all 37 chapters by
     importance + coverage. Question must be answerable only by close reading of that
     one passage.
   - **(b) Cross-reference — 25**: 2–3 separated scenes each (command↔execution,
     foreshadow↔payoff, consistency checks). Question must require synthesizing the
     linked passages.
   - Each anchor records its `chapter`/`segment` references and the question type.

2. **Question generation** — for each anchor, pass the actual scene **full text(s)**
   (from `all/en-gemini.jsonl`) plus chapter numbers, and generate one question.
   Output schema = existing `RagQuestion` (`question`, `answer`, `chapters`,
   `rationale`). Model: Gemini via `llm7shi`.

3. **Dedup validation** — run `scripts/check_duplicates.py -l en` on the 50 results
   as a **QA check** (expect ≈0 duplicate groups), confirming the anchor approach
   worked. Not a removal step.

4. **EN→JA translation** — new `scripts/translate_questions.py`: translate all fields
   (`question`, `answer`, `rationale`) with Gemini + `proper_nouns/all.tsv`;
   `chapters` is language-independent and copied as-is. Mirror the proper-noun
   handling in `scripts/translate_segments.py`.

5. **Assemble** — write the final `questions-en.jsonl` / `questions-ja.jsonl`
   (50 each, parallel), then merge the branch.

## Parameters

- Total: **50** — single-passage **25** + cross-reference **25**.
- Generation / translation model: **Gemini** (via `llm7shi`).
- Dedup judge (validation only): `ollama:gemma4:31b-it-qat` (default in
  `check_duplicates.py`).

## Status

- Branch `rebuild-questions` created off `main`.
- Committed (`ba20ae0`): `check_duplicates.py` + `questions-en-cache.tsv` +
  `questions-ja-cache.tsv`. Duplicate **judgment** phase is complete for both
  languages; the English **keep-selection** is intentionally **deferred** because
  the sets are being regenerated, not pruned.
- The current `questions-en.jsonl` / `questions-ja.jsonl` (100 each, old generator)
  are the **replace targets**.

## Next actions (resume here)

1. Build the **anchor-design** script (step 1) → produces a 50-anchor plan
   (25 single + 25 cross), with chapter/segment refs and question type.
2. Build the **anchor-based generation** (step 2) → 50 English questions grounded
   in scene full text.
3. Run **dedup validation** (step 3, user-run since `check_duplicates.py` is
   interactive in its keep phase, but validation needs no keep input).
4. Build **`translate_questions.py`** (step 4) and produce the Japanese set.
5. Replace `questions-en.jsonl` / `questions-ja.jsonl`, merge.

## Division of labour

`check_duplicates.py`'s keep phase uses `input()`, so interactive grouping is
**user-run**; the assistant builds the generation / translation tooling.

## Key files

- `scripts/check_duplicates.py` — duplicate detection / validation (done)
- `scripts/create_rag_questions.py` — old whole-text generator (reference)
- `scripts/translate_segments.py` — chapter translation w/ proper nouns (reference)
- `all/en-gemini.jsonl`, `all/en-gemini.tsv`, `all/en-gemini-summary.md` — anchors + text
- `questions-en.jsonl`, `questions-ja.jsonl` — sets to rebuild
- `questions-en-cache.tsv`, `questions-ja-cache.tsv` — dedup judgment caches
