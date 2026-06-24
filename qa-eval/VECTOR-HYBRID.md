# Segment ∪ Line dense hybrid — gold-coverage analysis

Measurement-only study of combining the two **dense** retrievers that share the
same embeddinggemma cosine:

- **Segment** — top-k over the segment index (`index-<lang>.safetensors`), the
  current Vector retriever ([answer_vector.py](answer_vector.py)).
- **Line** — top-k over the line index (`index-line-<lang>.safetensors`), the
  Vector-line retriever (`answer_vector.py --line`).

This is the dense∪dense counterpart of the dense∪BM25 study in
[HYBRID.md](HYBRID.md). Because both sides are the *same* cosine, there is no
second model and — unlike BM25 — no English-only restriction: **both en and ja**
are measured.

Script: [hybrid-vector.py](hybrid-vector.py). Print-only (no LLM, no answer
synthesis, no output file), mirroring [hybrid.py](hybrid.py) /
[sweep_vector.py](sweep_vector.py). The gold label is chapter-level
(`q["chapters"]`), so every metric is chapter coverage and a line maps directly
to its chapter (no line→segment resolution needed). It reuses
`sweep_vector.rank_all_scenes`, `hybrid.union_*` / `_minmax`, and
`bm25.coverage_at_k` / `precision_at_k` / `scopes_from_questions`, so segment,
line, and mix rankings are all graded on identical axes.

## Two ways to combine

- **Union (approach B)** — per-k set oracle: a gold chapter is covered iff it is
  in the segment top-k **OR** the line top-k. Parameter-free, scale-immune; the
  retrieval *upper bound*.
- **Mix (approach A)** — pool every segment unit and every line unit into one
  ranking and take the global top-k. Line cosines run systematically higher (see
  score scale below), so a per-source normalization is swept (raw / z-score /
  min-max).

## Metrics

- **sr (strict recall)** — per question, `1` iff `gold ⊆ top-k chapters`, else
  `0`; the report.py notion. The binary precondition for a *fully* correct
  answer. Primary metric.
- **cov (coverage)** — fraction of gold chapters with a hit in the top-k
  (partial credit). Less noisy than sr (50 questions; one chapter = 2 pt of sr)
  and the basis of the coverage@k curve. Equals sr only when coverage = 1.0.
- **prec (precision)** — `|gold ∩ top-k chapters| / |top-k chapters|`. Neither sr
  nor cov captures the context-size cost of union; prec does.

## Score scale (the line bias)

Both cosines are comparable but not identically distributed — line cosines run
systematically higher, so a naive merge-and-sort over-favors line hits:

| | segment top-k mean | line top-k mean | gap | seg top-1 | line top-1 |
| --- | --- | --- | --- | --- | --- |
| English | 0.481 | 0.520 | +0.039 | 0.580 | 0.617 |
| Japanese | 0.488 | 0.535 | +0.047 | 0.589 | 0.628 |

(top-10 pools.) Approach B is immune to this; approach A must normalize.

## Results

Strict recall / coverage / precision at k=5 and k=10, scope = all (n=50):

### English

| method | sr@5 | cov@5 | prec@5 | sr@10 | cov@10 | prec@10 |
| --- | --- | --- | --- | --- | --- | --- |
| Segment | 36/50 | 0.86 | 0.34 | 42/50 | 0.93 | 0.21 |
| Line | 33/50 | 0.78 | 0.40 | 39/50 | 0.87 | 0.27 |
| Mix (A) | 32/50 | 0.80 | 0.47 | 36/50 | 0.86 | 0.31 |
| **Union (B)** | **38/50** | 0.89 | 0.30 | **45/50** | 0.95 | 0.18 |

### Japanese

| method | sr@5 | cov@5 | prec@5 | sr@10 | cov@10 | prec@10 |
| --- | --- | --- | --- | --- | --- | --- |
| Segment | 36/50 | 0.86 | 0.33 | 45/50 | 0.94 | 0.21 |
| Line | 31/50 | 0.78 | 0.39 | 38/50 | 0.88 | 0.26 |
| Mix (A) | 32/50 | 0.79 | 0.44 | 38/50 | 0.88 | 0.29 |
| **Union (B)** | **41/50** | 0.91 | 0.30 | 45/50 | 0.94 | 0.18 |

Approach A normalization sweep (sr / cov, scope all) — normalization barely
moves the result, so the +0.04 bias is not the limiting factor:

| norm | en sr@5 | en sr@10 | ja sr@5 | ja sr@10 |
| --- | --- | --- | --- | --- |
| raw | 32/50 | 38/50 | 33/50 | 38/50 |
| z | 32/50 | 39/50 | 30/50 | 38/50 |
| min-max | 32/50 | 36/50 | 32/50 | 38/50 |

## Findings

- **Union (B) is the only combination that helps.** It beats Segment alone at
  every k in both languages (en sr 36→38 @5, 42→45 @10; ja sr 36→41 @5) and is
  the retrieval ceiling. These match the upper bound proposed in
  [PLAN.md](PLAN.md) (en sr@5 36, Union 38/45; ja Union sr@5 41). One small
  discrepancy: ja Union sr@10 measured **45**, vs the 43 PLAN.md sketched — the
  en figures match exactly, so the gap is a proposal-stage hand-estimate, not a
  retrieval difference.
- **Mix (A) is counter-productive for coverage.** Pooling 1132 lines with 82
  segments lets the strongest line units crowd out gold segments, dropping
  strict recall *below* Segment alone (en/ja sr@5 32 vs 36). Normalization
  (raw/z/min-max) does not recover it. Mix does win on precision (en prec@5 0.47,
  the highest), i.e. it keeps only the strongest units — but that does not convert
  to coverage.
- **Misses are orthogonal** — the precondition for a union win. Per-question
  provenance (Table 4) shows Line recovering gold chapters Segment drops (en k=5:
  Q28 Ch9/37, Q31 Ch23, Q45 Ch18 — 4 chapters) while Segment recovers 13 chapters
  Line drops. Each granularity covers what the other misses.
- **Line alone is weaker than Segment** on strict recall (en 33, ja 31 vs 36) —
  it is valuable only in union, not as a replacement.

## On using sr alone

sr is the right primary metric: full chapter coverage is the necessary condition
for a fully correct answer, and it is the most decision-relevant single number.
But it is a **ceiling, not a prediction**, and it discards information that the
actual answer score depends on:

1. If the judge gives partial credit, `cov` predicts the partial-correct cases
   that `sr=0` collapses (matters for cross questions; single questions have
   cov ∈ {0,1} = sr).
2. `sr` is noisy at n=50 (one chapter = 2 pt); `cov` and the coverage@k curve are
   smoother trend signals.
3. Neither `sr` nor `cov` sees the **context-size cost** of union (lower
   precision → "lost in the middle"). Whether union's higher sr converts to
   higher answer scores depends on synthesis over the wider context, which no
   retrieval metric measures — see [PLAN.md](PLAN.md) and
   [HYBRID.md § Context size](HYBRID.md).

## Conclusion

Approach **B (union)** is the only direction worth implementing; approach A does
not help coverage. The downstream answering script (`answer_seg_line.py` in
[PLAN.md](PLAN.md)) should be union-based. The final method ranking still requires
running the answers through the judge — these numbers bound retrieval, not answer
quality.

## Reproduce

```
uv run hybrid-vector.py -l en
uv run hybrid-vector.py -l ja
```

Prints the score-scale diagnostic, coverage@k by scope (Table 1), the summary
above (Table 2), the normalization sweep (Table 3), and per-question provenance
at k=5 and k=10 (Table 4). Indexes already exist for en+ja
(`index-*.safetensors`, `index-line-*.safetensors`).
