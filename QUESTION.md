# RAG Question Set Rebuild Plan (session/turn-based, type-split)

## Goal

Rebuild the evaluation question sets so they are **structurally non-duplicating**
and **detail-oriented** (good for RAG: answerable only by closely reading specific
passages, not by recalling the broad plot). Target **50 questions** — **25
single-passage + 25 cross-reference** — defined in English first, then translated
to Japanese so both languages ask the same things.

## Why a new algorithm

The previous generator (`scripts/create_rag_questions.py`) uploaded the whole text
and asked for N questions in **independent batches of 10**. With no memory across
batches, every batch gravitated to the same salient events, so the 100-question
sets were heavily duplicated (English: only ~36 unique by `check_duplicates.py`),
and "pick the important questions" pulled toward broad plot, not close detail.

The fix keeps the old strength (**upload the full text as one file**, which Gemini
auto-caches) but adds the two things the old loop lacked:

1. **Memory** — generate within a **single multi-turn session** whose conversation
   history carries the questions already produced, so each new turn can avoid
   duplicates and fill chapter-coverage gaps.
2. **Type separation** — run **two separate sessions**, one for single-passage
   detail questions and one for cross-reference questions, so each session's
   instructions, history, and coverage are focused and never mixed.

No anchor / planning phase is needed: a focused session that sees the full text and
its own prior questions distributes coverage and avoids duplication on its own.

## Data sources

| Use | File | Content |
|---|---|---|
| Generation input (one upload) | `all/en-gemini.md` | full English translation (combined), uploaded via `upload_file`, auto-cached by Gemini |
| Dedup validation | `scripts/check_duplicates.py` | semantic duplicate QA over the 50 results |
| Transliteration dictionary | `proper_nouns/all.tsv` | proper-noun consistency for EN→JA |
| Japanese parallel text | `all/ja-gemini.md` | reference only (JA set comes from translating EN) |

## Pipeline

1. **Generation (single-passage session)** — new script. Upload `all/en-gemini.md`
   once. Maintain a Gemini-native `contents` list by hand: file first, then append
   each turn's user prompt and the model's response (as a `model`-role turn). Per
   turn ask for **5 questions × 5 turns = 25**. Each turn sees the prior turns
   (memory) and is told to avoid overlap and cover chapters not yet used. Prompt:
   each question must be answerable only by close reading of **one** scene — a
   concrete, nitpicky detail (a specific line, object, number, gesture, reaction),
   never a plot summary.

2. **Generation (cross-reference session)** — a **separate** session over the same
   uploaded file, same 5×5 turn structure and memory. Prompt: each question must
   require synthesizing **2–3 separated chapters** (command↔execution,
   foreshadow↔payoff, consistency checks) and must not be answerable from a single
   scene.

   Both sessions emit the existing `RagQuestion` fields (`question`, `answer`,
   `chapters`, `rationale`); combined output → `questions-en.jsonl` (50).
   Model: `gemini-3.1-pro-preview` via `llm7shi`.

3. **Dedup validation** — run `scripts/check_duplicates.py -l en` on the 50 results
   as a **QA check** (expect ≈0 duplicate groups). Not a removal step. User-run
   because the keep phase uses `input()` (no input needed when there are no groups).

4. **EN→JA translation** — `scripts/translate_questions.py` (already built):
   translate `question` / `answer` / `rationale` with `gemini-3.5-flash` +
   `proper_nouns/all.tsv`; copy `chapters` as-is. Records stay parallel by line
   order. → `questions-ja.jsonl` (50).

5. **Assemble** — verify both files are 50 lines and parallel, update `README.md`
   if needed, then merge the branch.

## Implementation notes

- `generate_content_retry` is the **Gemini-native** path (it pairs with
  `upload_file`); its `contents` are file/string/`Content` items, **not** OpenAI
  message dicts. Multi-turn = manage the `contents` list manually, appending the
  model's reply as a `model`-role turn each round. (OpenAI-style messages belong to
  `compat.generate_with_schema`.)
- The uploaded file is the cached prefix, so the 5 turns per session and the second
  session reuse it cheaply.
- All Gemini steps need `GEMINI_API_KEY` in the environment and are billed. The key
  is **not** in the non-interactive shell, so generation/translation are run by the
  user (e.g. `! GEMINI_API_KEY=… uv run …`) or with the key exported; the assistant
  then verifies the output. Make the generation script **resumable** (append to
  output, skip questions already present) like `translate_segments.py`.

## Parameters

- Total **50** = single **25** + cross **25**; **5 questions/turn × 5 turns** per
  session.
- Generation model: **`gemini-3.1-pro-preview`**; translation model:
  **`gemini-3.5-flash`** (both via `llm7shi`).
- Dedup judge (validation only): `ollama:gemma4:31b-it-qat` (default in
  `check_duplicates.py`).

## Status

- Branch `rebuild-questions` off `main`.
- `scripts/generate_questions.py` is **built** (steps 1–2): two type-split sessions
  over one uploaded `all/en-gemini.md`, 5×5 turns each with a manually managed
  Gemini-native `contents` history (model replies appended as `model`-role turns).
  Emits `RagQuestion` fields plus `type` and `anchor_id` → `questions-en.jsonl`;
  resumable by replaying completed turns.
- `scripts/translate_questions.py` is **built** (step 4): translates EN→JA with
  proper nouns, copies `chapters`, resumes by `anchor_id`.
- The old 100-question sets and their dedup caches are retired to `*.old` files.
  The generation/translation/QA steps run fresh against empty
  `questions-en.jsonl` / `questions-ja.jsonl`.

## Next actions (resume here)

1. Run **generation** (steps 1–2, user-run, Gemini-billed):
   `GEMINI_API_KEY=… uv run scripts/generate_questions.py` → `questions-en.jsonl` (50).
2. Run **dedup validation** (step 3, user-run): `uv run scripts/check_duplicates.py -l en`.
3. Run **`translate_questions.py`** (step 4, user-run) → `questions-ja.jsonl` (50).
4. Verify both files are 50 lines and parallel by `anchor_id`, update `README.md`,
   delete the `*.old` files, merge.

## Key files

- `scripts/generate_questions.py` — memory + type-split question generator (done)
- `scripts/translate_questions.py` — EN→JA translation (done)
- `scripts/check_duplicates.py` — duplicate detection / validation (done)
- `scripts/create_rag_questions.py` — old whole-text generator (reference for
  upload + `RagQuestion` schema)
- `scripts/translate_segments.py` — proper-noun + generate helpers reused by
  `translate_questions.py`
- `all/en-gemini.md` — generation input (single upload)
- `questions-en.jsonl`, `questions-ja.jsonl` — sets to rebuild
