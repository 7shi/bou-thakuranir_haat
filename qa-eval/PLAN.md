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

### Multi-axis relevance scoring (prevents gold-scored-0)

The filter10/100 runs share one failure: a handful of gold chapters score 0
and are unrecoverable at any threshold (7 under filter10, 11 under filter100 —
all cross-reference chapters whose relevance is indirect). A single "rate
relevance 0–N" prompt lets the model collapse the call to a snap 0; a finer
scale did not help — filter100 is filter10 ×10 and the floor actually grew
(see [filter.md](filter.md#filter100-filter10-x10)).

A different lever: **decompose the relevance call across several axes so that
at least one axis scores non-zero on an indirectly-relevant chapter,
structurally preventing a 0 total.** Rate each `(chapter, question)` pair on
five relevance dimensions (each 0–20, summing to 0–100), for example:

| axis | captures |
|------|----------|
| factual answer | facts directly answering the question |
| character/action | the question's characters acting or appearing |
| causal chain | causes/consequences of the question's event |
| reference/foreshadow | cross-references, callbacks, foreshadowing |
| thematic/symbolic | the question's themes/symbols/motifs |

A chapter that scores 0 on "factual answer" can still earn points on
"reference/foreshadow" or "causal chain" — exactly the cross-reference
chapters the single-axis prompt drops to 0. The verdict TSV stores all five
subscores, so the keep rule is chosen afterwards:

- **sum >= threshold** — drop-in compatible with the existing
  [`filter.py`](filter.md) threshold sweep;
- **max >= threshold** — keep if any one axis fires (strongest floor defense);
- **non-zero-axis count >= n** — a majority vote, robust to noise.

This is a distinct vector from filter10/100 (judgement *decomposition*, not
scale granularity) and from the BM25 hybrid below (retrieval *mechanism*, not
LLM judgement). It costs one Phase 1 run (~1,850 calls) like the other filter
variants; CoT is effectively re-introduced because scoring five axes is
structured reasoning, which is also why it should calibrate better than the
single-token filter10 call. Wire it as `answer_filter.py --verdicts 5d` writing
`filter5d.tsv`, with `filter.py` gaining a per-axis breakdown table. If the
gold-scored-0 floor drops toward zero, the residual retrieval misses become the
pure BM25 case below.

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
