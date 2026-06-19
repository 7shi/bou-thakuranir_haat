# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Goal

Compare retrieval strategies for QA over the translations of
*Bou-Thakuranir Haat* (50 questions — 25 single-passage + 25 cross-reference —
in `questions-<lang>.jsonl`, run per language via `-l/--lang {en,ja}`):

1. **Vector RAG** — embed scenes, retrieve top-k, expand context, answer.
2. **Per-Chapter Extraction** — for each chapter, extract relevant passages,
   then answer from collected excerpts.
3. **Per-Chapter Filter** — ask the LLM whether each chapter is relevant, then
   answer from the full text of the kept chapters (the LLM as retriever).

Implementation, usage, and results live in [README.md](README.md); the Filter
granularity variants, their analysis, and the final verdict in
[FILTER.md](FILTER.md); the BM25 standalone findings in
[README.md § `bm25.py`](README.md#bm25py). This file tracks only what is not
yet built.

## BM25 standalone (done) → motivates the hybrid

[`bm25.py`](README.md#bm25py) confirmed the precondition for a hybrid: dense
and sparse fail on orthogonal cases. The English run shows BM25 recovers **6/7
of dense's top-5 retrieval misses at k≤5 (7/7 at k≤10)** — the signet ring
(Q31, Ch21/23), the Emperor of Delhi (Q49, Ch22), Muktiyar Khan's assassination
(Q27, Ch33). Global gold coverage: **64/86 at k=5, 74/86 at k=10** (strict
recall 33/50 → 41/50). And critically, a global **score threshold** fails to
separate gold for BM25 too (best F1 0.36, on par with cosine's 0.38) — so
**rank (k) is the only lever for either retriever**, which settles the hybrid's
design toward a rank-blend (RRF) rather than a score-weighted blend.

The 2 cases where RAG retrieved the gold chapter but still answered wrong
(Q21, Q29) are answering failures that no retrieval change fixes; they stay
out of scope.

## Hybrid retrieval (dense + BM25) — next

The remaining question is whether a rank-blend recovers both retrievers' misses
*simultaneously* — i.e. whether the hybrid's covered set is the set-theoretic
union of dense and BM25 coverage at each k, or whether one retriever's noise
suppresses the other's hits.

### Approach: Reciprocal Rank Fusion (RRF)

Both retrievers' *scores* fail to separate gold (F1 ≈ 0.36–0.38), so rank (k)
is the lever for both; RRF blends ranks, not scores, which matches the shape of
the problem and sidesteps the unbounded-vs-bounded scale mismatch (BM25 ∈
[0, ~30], cosine ∈ [−1, 1]):

```
RRF(scene) = w_d / (K + rank_dense) + w_b / (K + rank_bm25)
```

- **K** controls how sharply rank position decays (standard 60; sweep
  {5, 30, 60} — the 82-scene corpus is small, so a smaller K may discriminate
  better).
- **w_d / w_b** biases toward either retriever (start equal-weight, sweep
  {0.7/1.3, 1.0/1.0, 1.3/0.7}).

### Implementation: `hybrid.py`

Standalone analysis script in the `sweep_rag.py` / `bm25.py` lineage (no LLM,
no output file — terminal tables only). Reuses:

- `bm25.BM25Index`, `bm25.rank_all_scenes`, `bm25.tokenize` — sparse ranking
- `answer_rag.load_index`, `answer_rag.embed_query`,
  `sweep_rag.rank_all_scenes` — dense ranking
- `bm25.scopes_from_questions`, `bm25.coverage_at_k`,
  `bm25.print_per_question_coverage_table` — analysis helpers (importable
  because `bm25.py` pulls in only `answer`, not ollama)

A `make hybrid` target mirrors `make sweep` / `make bm25`.

Output — a three-way comparison (dense-only vs BM25-only vs hybrid):

1. **Chapter coverage@k by scope** — one row per retriever (k = 1…82).
2. **Per-question gold coverage at k=5 / k=10** (`x/y` form, like `bm25.py`
   Table 2) — one block per retriever.
3. **Strict recall + global coverage at k=5 / k=10**, side by side for all
   three.
4. **Per-question provenance** — for each covered gold chapter at k=5, which
   retriever(s) surfaced it: dense-only, BM25-only, or both. The key
   diagnostic: if the hybrid's covered set equals dense ∪ BM25, RRF is working
   as a union; if some union hits drop out, the rank-blend is suppressing them
   and K / weights need tuning.

K and w_d/w_b are flags; the default run reports equal-weight K=60 plus a small
grid sweep to confirm robustness.

### Evaluation (gold coverage only)

Ceiling = 0.990 means surfacing the gold chapters suffices, so the hybrid is
judged on the same single axis as `bm25.py` and `sweep_rag.py` (per
[FILTER.md](FILTER.md) § Verdict) — no Phase 2 QA run required. The success
bars are concrete:

- **Strict recall at k=5**: beat dense's 33/50 and BM25's 33/50 — toward
  Filter10's 0.840 (38/50) without Filter's 1,850-call cost.
- **Recover the residual cross floor**: the four cross questions BM25 still
  misses at k=10 (Q32, Q42, Q44, Q50) — does dense surface what BM25 drops
  there, giving the hybrid coverage neither achieves alone?
- **Union property**: per-question provenance (Table 4) should show the
  hybrid's covered set equaling dense ∪ BM25 at each k; gaps point to
  rank-blend suppression.

### Scope

- English only (BM25 is English-only; Japanese deferred).
- Retrieval evaluation only; Phase 2 QA (answering from hybrid-retrieved
  context, reusing `answer_rag.py`'s expand-and-merge) is a follow-on once
  retrieval is shown to help.
- RRF only; a weighted score-blend is not pursued because both score
  distributions fail to separate gold (F1 ≈ 0.36–0.38), so blending scores
  inherits that blindness.

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
