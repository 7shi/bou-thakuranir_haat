# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done (both languages, 50-question set)** — see [README.md](README.md) for details.

- `build_index.py` — scene embedding index (`index-<lang>.safetensors`)
- `answer_rag.py` — Vector RAG → `results-<lang>/rag.jsonl`
  (answers `google:gemma-4-31b-it` for both languages)
- `answer_extract.py` — Per-chapter extraction → `results-<lang>/extract.jsonl`
  (same answer model)
- `judge.py` — LLM grading vs. gold (judge `ollama:qwen3.6` for both) → `results-<lang>/judge-<stem>.jsonl`
- `report.py` — RAG-vs-Extract table; per-question case studies in
  [results-en/README.md](results-en/README.md) and [results-ja/README.md](results-ja/README.md).
  - **EN**: RAG and Extract tie at 39/50; single-passage solved (24/25 each),
    cross-reference the open problem (15/25 each); gold sound.
  - **JA**: Extract 40/50, RAG 38/50; single 25/25 and 24/25, cross 15/25 and
    14/25. Headline findings match EN; with the same answer model, language makes
    almost no difference to accuracy (the only divergence is a larger
    both-methods-wrong set, 7 vs. 3, at near-constant total accuracy).
    `questions-ja.jsonl` gained the `type` field (single/cross) so `report.py
    -l ja` breaks scope down.

After that, the optional retrieval follow-ups below (`sweep_rag.py`, then BM25
hybrid) tune RAG using the gold chapter labels — these are the only remaining work.

## Goal

Compare two retrieval strategies for QA over the translations of
*Bou-Thakuranir Haat* (50 questions — 25 single-passage + 25 cross-reference —
in `questions-<lang>.jsonl`, run per language via `-l/--lang {en,ja}`):

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

### BM25 hybrid retrieval (follow-up — complements `sweep_rag.py`)

The 50-question English run ([results-en/README.md](results-en/README.md)) traces
RAG's losses to top-5 **vector** recall: a gold chapter ranks just outside `k=5`,
so the answerer never sees it. Several of those misses hinge on a rare proper noun
or concrete object — the signet ring (Q31, gold 21–23 all missed), the Emperor of
Delhi (Q49, Ch22 missed), Muktiyar Khan's assassination (Q27, Ch33 missed). Dense
embeddings are weakest exactly here: a low-frequency named entity gets washed out
in the embedding, whereas **BM25 matches it on the literal term**. Dense and sparse
fail on orthogonal cases, so a hybrid (RRF or a weighted blend of cosine + BM25)
should recover chapters dense retrieval drops.

This is a different lever from `sweep_rag.py`: that script asks whether tuning
`k`/`N`/a score threshold pulls the gold chapter into the existing dense ranking;
hybrid retrieval instead adds a second retriever to surface chapters dense scoring
never ranks. Run them together — sweep to characterize the dense recall curve,
then measure how much BM25 closes the residual gap.

Scope note: this only addresses the 6 RAG losses that are genuine retrieval
misses. The 2 cases where RAG retrieved the gold chapter but still answered wrong
(Q21, Q29) are answering failures that no retrieval change fixes.

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
