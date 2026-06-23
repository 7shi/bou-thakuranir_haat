# Hybrid: dense + BM25 retrieval

The Hybrid analysis covers two standalone scripts —
[`bm25.py`](README.md#bm25py) and [`hybrid.py`](README.md#hybridpy) — that
together answer the question [PLAN.md](PLAN.md) poses: **does combining sparse
lexical (BM25) and dense semantic (cosine) retrieval recover the gold chapters
each alone drops?**

The retrieval unit is a **scene** (segment), identical to Vector RAG,
[`sweep_rag.py`](README.md#sweep_ragpy), `bm25.py`, and `hybrid.py`, so
coverage@k and the per-question metrics read on identical axes across all
retrievers. Neither script calls an LLM or writes an output file — both are
pure terminal-table ranking analyses over the 82-scene English corpus.

Ceiling = 0.990 means surfacing the gold chapters suffices, so retrieval
quality is judged on a single axis — **does the method surface the gold
chapters?** — without running Phase 2 QA (per [FILTER.md](FILTER.md) § Verdict).
The success metric is **strict recall** (gold ⊆ top-k) unless noted otherwise.

## Coverage at a glance

Retrieval strict recall (gold ⊆ top-k) and coverage (mean |gold ∩ top-k| /
|gold|) for each method, 50 questions (86 gold chapter-pairs). RRF / Borda /
CombSUM fuse dense and BM25 into a single ranking; Union takes the
set-theoretic union of their top-k chapter sets (no fusion). The RRF row uses
the a-priori default (K=60, equal-weight) — see
[RRF parameter sweep](#rrf-parameter-sweep-and-overfitting) for why the
"best" sweep cell is overfit.

| method | k=5 strict | k=5 coverage | k=10 strict | k=10 coverage |
|---|---:|---:|---:|---:|
| Dense (cosine) | **36/50** | 0.857 | 42/50 | 0.930 |
| BM25 (lexical) | 33/50 | 0.830 | 41/50 | 0.910 |
| RRF (K=60, equal) | 32/50 | 0.843 | 43/50 | 0.950 |
| Borda | 33/50 | 0.843 | 43/50 | 0.950 |
| CombSUM | 35/50 | 0.860 | 42/50 | 0.937 |
| **Union (oracle)** | **40/50** | **0.913** | **46/50** | **0.973** |

No fusion method beats dense at k=5; Union beats dense by +4 at both depths.
Four questions are unrecoverable by either retriever at k≤10 — see
[Shared blind spots](#shared-blind-spots).

## Verdict

**Fusing the two retrievers into a single ranking (RRF, Borda, CombSUM) does
not beat dense alone at k=5, and barely beats it at k=10. The win is the
union — running both retrievers independently and taking the set-theoretic
union of their top-k chapters — which is parameter-free and robust.**

- **Rank-blending suppresses more than it recovers.** At k=5, RRF scores
  **32/50** strict recall — four questions *worse* than dense alone (36/50).
  The provenance table shows why: RRF recovers 4 gold-pairs dense missed but
  **suppresses 9** that dense or BM25 had (both retrievers' hits get displaced
  when two rankings are squeezed into one list at depth k). There are **zero
  "pure wins"** — no gold chapter that *neither* retriever surfaced enters
  RRF's top-5. The blend can only re-rank what the retrievers already found.

- **The RRF "best" parameters are overfit.** A K × weight sweep on the same
  50 questions finds K=30, w_d=1.3/w_b=0.7 → 45/50 at k=10, but this is
  post-hoc parameter selection on the test set (the dense-bias direction is
  itself learned from these questions — on a different set BM25 might be
  stronger and the bias would reverse). The a-priori default (K=60,
  equal-weight) scores 32/50 at k=5 and 43/50 at k=10 — worse than dense at
  k=5, +1 at k=10. The sweep's "best" is fitting the metric, not learning a
  generalizable rule (same caveat as [FILTER.md](FILTER.md)'s OR-combination
  search).

- **The Union oracle is the robust winner.** Taking the union of dense top-k
  and BM25 top-k chapter sets — no ranking fusion at all — scores **40/50 at
  k=5** and **46/50 at k=10**, beating dense (36/42) and every fusion method.
  It is parameter-free, so it cannot overfit, and since Ceiling = 0.990 shows
  over-inclusion is harmless, the only cost is the larger context (~24
  expanded scenes vs ~17 for dense alone at k=10).

- **Four questions are unrecoverable by either retriever.** Q31 (Ch22), Q32
  (Ch15), Q38 (Ch32), Q42 (Ch23) each have a gold chapter that ranks 12–38 in
  *both* retrievers — the shared blind spot that no dense+BM25 hybrid can
  reach. These are the same indirectly-relevant cross-reference chapters
  [FILTER.md](FILTER.md) identifies as the gold floor; opening them needs a
  different retrieval mechanism (query expansion, multi-query), not a better
  blend.

## `bm25.py` — sparse lexical standalone

Sibling of [`sweep_rag.py`](README.md#sweep_ragpy): same scene unit, same
gold-coverage lens, but ranks scenes by **Okapi BM25** on the literal scene
text instead of cosine on the dense embedding index. Read the two side by side
to answer the question PLAN.md poses — does sparse lexical matching recover the
chapters dense retrieval drops (the low-frequency proper nouns embeddings wash
out)?

The BM25 implementation is pure stdlib (`re` + `collections` + `math`), k1=1.5,
b=0.75 (standard Okapi defaults), using the Lucene/Elasticsearch IDF variant
`ln(1 + (N − n + 0.5)/(n + 0.5))` so IDF is always non-negative. Tokenization is
English-only (lowercase + `[a-z0-9]+` + stopword removal); no morphology, so
Japanese is deferred. The ranking functions (`BM25Index`, `rank_all_scenes`,
`tokenize`) are importable so `hybrid.py` reuses them without reimplementing.

**Algorithm**

1. Tokenize each scene document (title + body) and build a BM25 index over the
   corpus.
2. For each question, tokenize the question and score every scene.
3. Rank all 82 scenes by BM25 score (ties break in narrative order) and record
   where each gold chapter first appears.
4. Print five tables (1 and 3–5 mirror `sweep_rag.py` so the two retrievers read
   side by side; 2 is the per-question row-level view; 5 is the PLAN.md
   cross-reference).

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level) and
  `all/<lang>-gemini.jsonl` + `.tsv` (scene text + titles). No embedding index,
  no ollama — reads the raw scene text directly.

### Findings

BM25 matches dense retrieval on coverage@k but recovers almost all of dense's
misses — the orthogonal-failure hypothesis holds, which is the precondition for
a hybrid:

- **BM25 recovers 6/7 dense retrieval misses at k≤5, 7/7 at k≤10.** PLAN.md's
  named misses all land inside BM25's top band: the signet ring (Q31, Ch21/23
  at rank 5/3 — all three gold chapters missed by dense's top-5), the Emperor
  of Delhi (Q49, Ch22 at rank 5), Muktiyar Khan's assassination (Q27, Ch33 at
  rank 9). The only miss not recovered at k=5 is Q43 (first gold rank 6), and
  it enters at k≤10. Dense and sparse fail on orthogonal cases — exactly the
  precondition for a hybrid to recover what either alone misses.
- **Per-question coverage (Table 2).** Global gold coverage is **64/86 at k=5
  (0.744), 74/86 at k=10 (0.860)**; strict recall (gold ⊆ top-k) is **33/50
  → 41/50**. Every `single` question is fully covered at both depths; all the
  drops are `cross`. At k=5, 17 of 25 cross questions lose at least one gold
  chapter, and four cross questions still miss gold at k=10 — the same
  indirectly-relevant chapters dense retrieval also struggles with, where the
  literal question terms do not appear in the gold scene.
- **Coverage@k parity with dense.** BM25 at k=5: single 1.00, cross 0.66
  (dense: single 1.00, cross 0.71). Single is trivial for both; cross is the
  frontier for both, and the two retrievers drop *different* cross chapters —
  so the residual gap each leaves is exactly what the other fills.
- **A global BM25 threshold is also a poor lever.** Best τ\*≈9.69 (F1 0.36), on
  par with cosine's F1≈0.38. Neither score separates gold from
  topically-similar non-gold scenes, so **rank (k) is the lever for both
  retrievers** — and rank-blending two rankings (RRF) is the natural next step
  rather than a score-weighted blend of unbounded BM25 vs. bounded cosine.
- **Per-question gaps are large for single, thin for cross.** Single questions
  sit at first-gold rank 1–2 with gaps of +8 to +29; cross questions hover at
  rank 1–6 with gaps of +0.05 to +0.72 — BM25, like dense, finds cross
  chapters but interleaves them with near-misses. The thin cross margin is
  where a hybrid earns its keep.

## `hybrid.py` — fusion analysis

Standalone analysis script in the `sweep_rag.py` / `bm25.py` lineage (no LLM,
no output file — terminal tables only). It fuses the two retrievers' rankings
and asks whether a hybrid recovers both retrievers' misses *simultaneously*.

### Fusion strategies

Four strategies are compared so the choice between rank-blending and
score-blending is empirical, not assumed:

- **RRF (Reciprocal Rank Fusion)** — blends ranks, not scores. The PLAN.md
  choice, because both retrievers' scores fail to separate gold (F1 ≈ 0.36–0.38)
  while rank (k) is the lever for both, and rank-blending sidesteps the
  unbounded-BM25 vs. bounded-cosine scale mismatch:

  `RRF(scene) = w_d / (K + rank_dense) + w_b / (K + rank_bm25)`

- **Borda Count** — the other classic rank-fusion method, with a linear decay
  `(N − rank)` instead of RRF's reciprocal. Both are rank-based; Borda weights
  the top of the list more heavily. Including it isolates whether RRF's
  reciprocal shape (vs. any rank-blend) matters.

- **CombSUM** — min-max normalizes each retriever's scores to [0, 1] and sums
  them. The score-based baseline PLAN.md argues *against*: it inherits both
  retrievers' score-blindness, so it should underperform the rank-blends.

- **Union oracle** — the per-k set-theoretic upper bound: coverage if the
  hybrid kept every chapter *either* retriever surfaced in its top-k. Not a
  ranking (the kept set changes with k), but the ceiling any fusion could
  reach at depth k. RRF's goal was to match it from a single ranking.

`hybrid.py` reuses `bm25.BM25Index` / `rank_all_scenes` / `tokenize` (sparse),
`answer_rag.load_index` / `embed_query` / `expand_and_merge` (dense), and
`bm25.coverage_at_k` / `precision_at_k` / `scopes_from_questions` (analysis).

### Retrieval comparison at k=5 and k=10

English run (strict recall = gold ⊆ top-k; coverage = mean |gold ∩ top-k| /
|gold|):

| method | k=5 strict | k=5 cov | k=5 prec | k=10 strict | k=10 cov |
|---|---:|---:|---:|---:|---:|
| Dense | **36/50** | 0.857 | 0.337 | 42/50 | 0.930 |
| BM25 | 33/50 | 0.830 | 0.298 | 41/50 | 0.910 |
| RRF (K=60, equal) | 32/50 | 0.843 | 0.318 | 43/50 | **0.950** |
| Borda | 33/50 | 0.843 | 0.317 | 43/50 | 0.950 |
| CombSUM | 35/50 | **0.860** | 0.331 | 42/50 | 0.937 |
| **Union** | **40/50** | **0.913** | 0.251 | **46/50** | **0.973** |

At k=5, **every fusion method is worse than dense alone** (RRF is −4, Borda −3,
CombSUM −1). At k=10, RRF and Borda edge dense by +1 (43 vs 42). The Union
oracle clears dense by +4 at both depths with no fusion at all. The cross scope
tells the same story more sharply: at k=5, dense holds 11/25 cross questions,
RRF drops to 7/25, while Union reaches 15/25.

### RRF parameter sweep and overfitting

| K | w_d | w_b | k=5 strict | k=5 cov | k=10 strict | k=10 cov |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1.0 | 1.0 | 35/50 | 0.853 | 41/50 | 0.933 |
| 5 | 0.7 | 1.3 | 33/50 | 0.827 | 41/50 | 0.937 |
| 5 | 1.3 | 0.7 | **36/50** | 0.857 | 44/50 | 0.953 |
| 30 | 1.0 | 1.0 | 33/50 | 0.850 | 44/50 | 0.957 |
| 30 | 0.7 | 1.3 | 35/50 | 0.860 | 43/50 | 0.947 |
| 30 | 1.3 | 0.7 | 35/50 | 0.860 | **45/50** | **0.963** |
| **60** | **1.0** | **1.0** | **32/50** | **0.843** | **43/50** | **0.950** |
| 60 | 0.7 | 1.3 | 35/50 | 0.860 | 42/50 | 0.937 |
| 60 | 1.3 | 0.7 | 35/50 | 0.860 | 44/50 | 0.957 |

The best cell (K=30, w_d=1.3/w_b=0.7 → 45/50) was chosen *after* seeing the
results on the same 50 questions — classic post-hoc selection. On 50 questions
each question is 2% of the metric, so moving 1–2 questions is within noise. The
dense-bias direction (w_d > w_b) is itself learned: on this set dense is the
stronger retriever, but on a different set BM25 might lead and the optimal
bias would reverse. The only honest, a-priori data point is the K=60
equal-weight default (bolded): 32/50 at k=5, 43/50 at k=10 — worse than dense
at k=5, +1 at k=10. The sweep confirms that no RRF parameter makes fusion
beat the Union oracle (46/50), and that biasing toward dense only recovers
dense's own score, defeating the purpose of adding BM25.

### Provenance: the union property

Does RRF's covered set equal dense ∪ BM25? The per-question provenance at k=5
shows it does not — the rank-blend suppresses union hits:

- RRF covers **4** gold-pairs dense missed.
- RRF covers **5** gold-pairs BM25 missed.
- RRF **pure wins** (neither retriever surfaced): **0**.
- RRF **suppressions** (dense or BM25 surfaced, RRF dropped): **9**.

Zero pure wins means RRF never surfaces a chapter *both* retrievers missed —
it can only re-rank what one of them already found. And the 9 suppressions mean
fusing into one list at depth k forces out hits that the individual retrievers
held. Net: −5 at k=5 (32 vs dense's 36). This is structural, not a tuning
problem — a single ranking at depth k cannot contain the union of two rankings'
top-k.

### Dense-miss recovery

For the seven questions dense top-5 dropped a gold chapter (the PLAN.md named
misses plus Q49), the first-gold-rank under each method:

| qid | gold | 1st Dense | 1st BM25 | 1st RRF | 1st Borda | 1st CombSUM |
|---:|---|---:|---:|---:|---:|---:|
| 27 | [2, 4, 33] | 1 | 1 | 1 | 1 | 1 |
| 28 | [9, 37] | 6 | 2 | 5 | 6 | 5 |
| 31 | [21, 22, 23] | 7 | 3 | 2 | 2 | 2 |
| 36 | [1, 17, 21] | 3 | 1 | 1 | 1 | 1 |
| 43 | [11, 37] | 1 | 6 | 5 | 5 | 4 |
| 45 | [18, 25] | 2 | 2 | 1 | 1 | 1 |
| 49 | [2, 22] | 1 | 1 | 1 | 1 | 1 |

Recovery counts at k≤5 / k≤10 (by first-gold-rank):

| method | k≤5 | k≤10 |
|---|---:|---:|
| BM25 | 6/7 | 7/7 |
| RRF | 7/7 | 7/7 |
| Borda | 6/7 | 7/7 |
| CombSUM | 7/7 | 7/7 |

**Note the metric:** this table uses **first-gold-rank** — whether the *first*
gold chapter enters top-k (coverage > 0). It is **not** strict recall (all gold
chapters ⊆ top-k). Q31's first gold chapter enters at rank 2, but its third
gold chapter (Ch22) sits at dense rank 38 / BM25 rank 24, so Q31 still fails
strict recall at k=10. The two notions agree only when coverage = 1.0 (see
[`sweep_rag.py`](README.md#sweep_ragpy) § "Note on the two recall notions").

### Context size with ±1 expansion

`answer_rag.py` expands each top-k hit by ±1 scene within its chapter and
merges overlaps, so the answerer sees more than the raw top-k scenes. The
table below applies the same ±1 expansion to each method's top-10 hits so the
context sizes are directly comparable to what the real RAG pipeline feeds:

| method | expanded scenes (mean) | chapters (mean) |
|---|---:|---:|
| Dense k=10 | 16.7 | 7.6 |
| BM25 k=10 | 16.5 | 8.2 |
| **Union k=10** | **23.6** | **11.1** |

The Union feeds ~24 expanded scenes — about **1.4×** dense's ~17. Since
Ceiling = 0.990 shows over-inclusion is harmless, this +40% context cost buys
+4 strict-recall questions (46 vs 42) and is the only robust win in the table.
The union's scene count (24) is well under 2× a single retriever's (17) because
the two retrievers' top-10 lists overlap substantially — the same scene often
ranks in both.

### Shared blind spots

Four questions have a gold chapter that **neither** retriever surfaces in
top-10 — the residual that no dense+BM25 hybrid can reach:

| qid | gold | unrecoverable | dense rank | BM25 rank |
|---:|---|---|---:|---:|
| 31 | [21, 22, 23] | Ch22 | 38 | 24 |
| 32 | [11, 15, 16] | Ch15 | 25 | 23 |
| 38 | [26, 28, 32] | Ch32 | 12 | 15 |
| 42 | [22, 23, 29] | Ch23 | 25 | 15 |

These are indirectly-relevant cross-reference chapters where the literal
question terms do not appear in the gold scene, so lexical (BM25) and semantic
(dense) matching both miss them. They are the same chapters
[FILTER.md](FILTER.md) identifies as the **gold floor** — the LLM-as-retriever
scores them 0 (Filter10) or near-0, confirming the failure is not
retriever-specific but intrinsic to the question–chapter relationship. Opening
them needs a different mechanism (query expansion, multi-query, or a larger k
that tolerates the precision drop), not a better blend of the two existing
retrievers.

## Conclusion

The Hybrid experiment establishes what combining sparse and dense retrieval can
and cannot do on this corpus:

1. **Fusion into a single ranking is the wrong architecture.** RRF, Borda, and
   CombSUM all underperform dense alone at k=5 because squeezing two rankings
   into one list at depth k suppresses more hits than it recovers (9
   suppressions vs. 4 recoveries, 0 pure wins). At k=10 the fusion methods edge
   dense by +1, which does not justify the added complexity — and the RRF
   parameter sweep's apparent gains are overfit to the 50-question test set.
2. **The union is the right architecture.** Running both retrievers
   independently and taking the set-theoretic union of their top-k chapters
   scores 40/50 (k=5) and 46/50 (k=10) — beating dense by +4 at both depths,
   with no tunable parameters (so no overfitting risk), at a +40% context cost
   that Ceiling = 0.990 proves is harmless to accuracy.
3. **Four questions are beyond both retrievers.** Q31, Q32, Q38, Q42 each have
   a gold chapter ranked 12–38 by both retrievers — the shared blind spot that
   no dense+BM25 hybrid can open. These are the same indirectly-relevant
   chapters [FILTER.md](FILTER.md) identifies as the gold floor; they need a
   different retrieval mechanism, not a better blend.

The practical takeaway: **don't fuse — union.** Replace single-retriever RAG
with a two-retriever union at the same k, feed the merged chapter set as
context, and accept the +40% token cost for +4 questions of retrieval coverage.
The four residual questions are the next frontier, and they require changing
the query, not the ranking.
