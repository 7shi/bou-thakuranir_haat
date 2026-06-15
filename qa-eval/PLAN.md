# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done** — see [README.md](README.md) for details.

- `build_index.py` — scene embedding index (`index-en.safetensors`)
- `answer_rag.py` — Vector RAG; run with `google:gemma-4-31b-it` on 2026-06-14 → `results-en/rag.jsonl`
- `answer_extract.py` — Per-chapter extraction; run with `google:gemma-4-31b-it` on 2026-06-15 → `results-en/extract.jsonl`
- `judge.py` — LLM grading of answers vs. gold (judge model `ollama:qwen3.6`) → `results-en/judge-<stem>.jsonl`
- `report.py` — RAG-vs-Extract comparison table (accuracy + chapter retrieval)

**Next step**

The pipeline is now language-parameterized via `-l/--lang {en,ja}` (see
[README.md](README.md#languages)); the Japanese run reuses the same scripts with
`-l ja`. Remaining: generate `all/ja-gemini.tsv` (`make titles`), then run the
ja pipeline (`build_index` → `answer_*` → `judge` → `report`, all with `-l ja`).

`sweep_rag.py` (optional follow-up below) — tune RAG's retrieval depth from the
gold chapter labels.

## Goal

Compare two retrieval strategies for QA over the English translation of
*Bou-Thakuranir Haat* (100 questions in `questions-en.jsonl`):

1. **Vector RAG** — embed scenes, retrieve top-k, expand context, answer.
2. **Per-Chapter Extraction** — for each chapter, extract relevant passages,
   then answer from collected excerpts.

## Remaining work

### `sweep_rag.py` (optional follow-up — separate script, does not block `report.py`)

A standalone analysis script, independent of `report.py`. It uses the gold
`chapters` as a relevance label to *tune* RAG's retrieval depth, asking: **at
what similarity score / rank do the gold chapters actually appear?**

This is a separate concern from the report table: `report.py` *reports* the
RAG-vs-Extract results, while `sweep_rag.py` *tunes* RAG's `-k` / `-N` (and a
possible score-threshold) knobs instead of guessing them. Order is free — do
this whenever, after `report.py` or independently.

**Analysis goals:**

- For each question, find the best-scoring hit whose chapter is in the gold
  `chapters` (a true positive) and the scores of the non-gold hits. Comparing
  the score distributions of gold vs. non-gold hits shows whether a cosine
  **threshold** could separate relevant from irrelevant scenes — and what cutoff
  trades recall against precision.
- Equivalently, plot **chapter recall vs. k** (1..k): the smallest k at which
  most gold chapters are already covered tells us whether the current `k=5` is
  generous or tight.

**Data note**: `results-en/rag.jsonl` currently holds only the top-5 hits per
question (run with `k=5`), so a full recall-vs-threshold sweep needs the scores
of lower-ranked scenes too. This is cheap to get: the embeddings already live in
`index-en.safetensors`, so re-retrieving is just one matmul + argsort per
question (no LLM, no re-embedding). The simplest path is to load the index,
re-embed the questions, and dump the **full** score vector (or a large-`k`
slice) per question to a separate file — reuse `load_index` / `embed_query` /
`top_k_search` from `answer_rag.py`.

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors).
