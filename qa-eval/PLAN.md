# QA Evaluation Plan

## Goal

Compare retrieval strategies for QA over the translations of
*Bou-Thakuranir Haat* (50 questions — 25 single-passage + 25 cross-reference —
in `questions-<lang>.jsonl`, run per language via `-l/--lang {en,ja}`).

## Current state

Implemented and evaluated (see [README.md](README.md), [FILTER.md](FILTER.md),
[HYBRID.md](HYBRID.md)):

- **Vector RAG** (k=5, k=10), **Extract**, **Filter** (2/3/10/100/5d),
  **Ceiling** — answering, judging, and analysis complete for English.
- **BM25 standalone** and **hybrid retrieval analysis** — terminal-table
  ranking analyses complete for English ([HYBRID.md](HYBRID.md)). Key finding:
  fusing dense + BM25 into a single ranking (RRF/Borda/CombSUM) underperforms
  dense alone at k=5 (RRF suppresses more hits than it recovers); the robust
  win is the **Union** — run both retrievers independently and take the
  set-theoretic union of their top-k chapter sets — which scores **46/50**
  strict recall at k=10 vs dense's 42/50, with no tunable parameters.

## Next: Union Phase 2 QA

The retrieval analysis proved the Union surfaces +4 gold-chapter questions over
dense alone (46/50 vs 42/50 at k=10), but this is **retrieval coverage only** —
those +4 questions have not been answered or judged. The next step is to
generate answers from the Union-retrieved context and evaluate them, to verify
the retrieval gain translates to a QA-accuracy gain.

### Approach: `answer_union.py`

Mirror [`answer_vector.py`](README.md#answer_vectorpy), but retrieve from both
indexers and union the hits before expansion:

1. Embed the question (dense) and tokenize it (BM25).
2. Retrieve dense top-k scenes and BM25 top-k scenes.
3. **Union** the two hit sets (set-theoretic, dedup by scene).
4. Expand ±N within chapters and merge (reuse
   [`answer_vector.expand_and_merge`](README.md#answer_vectorpy)).
5. Build context and answer (reuse [`answer.answer_question`](README.md#answerpy)).

- **Output**: `results-<lang>/union.jsonl` (same record shape as `vector5.jsonl`:
  `question_id`, `hits`, `expanded`, `answer`). A k-aware filename
  (`union<k>.jsonl`) mirrors `vector<k>.jsonl`.
- **Makefile**: `make union K=10` mirrors `make vector K=10`.
- **Judging / reporting**: [`judge.py`](README.md#judgepy) and
  [`report.py`](README.md#reportpy) auto-discover the new file —
  `judge-union.jsonl` and a "Union" row in the report follow with no code
  change (the method-discovery logic in `report.py` picks up any
  `results-<lang>/*.jsonl` with a matching judge file).

### Evaluation

Compare Union Phase 2 against the existing baselines (see
[README.md § Results](README.md#results)):

- **vs Vector k=10** (0.920): does the +4 retrieval coverage yield Phase 2 gains?
  The four questions Union recovers (where BM25 fills dense's gap) should
  improve if the missing gold context was the bottleneck.
- **vs Ceiling** (0.990): the gap to Ceiling is the residual — Union's 4
  shared blind spots (Q31/32/38/42, unrecoverable by either retriever) plus
  any synthesis failures from the +40% larger context.
- **Context cost**: Union feeds ~24 expanded scenes at k=10 (1.4× dense's
  ~17). Does the larger context cause "lost in the middle" synthesis failures
  that offset the retrieval gain? Ceiling = 0.990 suggests over-inclusion is
  harmless, but that was measured on the *gold* set (1.7 chapters/question), not
  a 11-chapter union — the Union Phase 2 run is the empirical test.

### Scope

- English only (BM25 is English-only; Japanese deferred).
- Union only; the retrieval analysis ([HYBRID.md](HYBRID.md)) ruled out
  RRF/Borda/CombSUM fusion.

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Opening the 4 shared blind spots (needs query expansion or multi-query, not
  a better retrieval blend).
