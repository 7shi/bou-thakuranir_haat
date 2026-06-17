# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Goal

Compare two retrieval strategies for QA over the translations of
*Bou-Thakuranir Haat* (50 questions — 25 single-passage + 25 cross-reference —
in `questions-<lang>.jsonl`, run per language via `-l/--lang {en,ja}`):

1. **Vector RAG** — embed scenes, retrieve top-k, expand context, answer.
2. **Per-Chapter Extraction** — for each chapter, extract relevant passages,
   then answer from collected excerpts.

Implementation, usage, and results live in [README.md](README.md). This file
tracks only what is not yet built.

## Remaining work

### BM25 hybrid retrieval (complements `sweep_rag.py`)

The 50-question English run ([results-en/README.md](results-en/README.md)) traces
RAG's losses to top-5 **vector** recall: a gold chapter ranks just outside `k=5`,
so the answerer never sees it. Several of those misses hinge on a rare proper noun
or concrete object — the signet ring (Q31, gold 21–23 all missed), the Emperor of
Delhi (Q49, Ch22 missed), Muktiyar Khan's assassination (Q27, Ch33 missed). Dense
embeddings are weakest exactly here: a low-frequency named entity gets washed out
in the embedding, whereas **BM25 matches it on the literal term**. Dense and sparse
fail on orthogonal cases, so a hybrid (RRF or a weighted blend of cosine + BM25)
should recover chapters dense retrieval drops.

This is a different lever from `sweep_rag.py`: that script tunes the existing
dense ranking, while hybrid retrieval adds a second retriever to surface chapters
dense scoring never ranks. `sweep_rag.py` already established the dense-only
ceiling — a cosine **threshold** does not separate gold from non-gold scenes (best
F1 ≈ 0.38, see [README.md](README.md#findings)), so **rank (k) is the only dense
lever**; the hybrid then measures how much BM25 closes the residual gap (bumping
`-k` alone plateaus near 0.93 chapter coverage at k=15 on the cross set).

Scope note: this only addresses the 6 RAG losses that are genuine retrieval
misses. The 2 cases where RAG retrieved the gold chapter but still answered wrong
(Q21, Q29) are answering failures that no retrieval change fixes.

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
