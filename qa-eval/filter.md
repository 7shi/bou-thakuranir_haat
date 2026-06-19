# Filter Analysis

The per-chapter relevance filter ([`answer_filter.py`](#answer_filterpy)) uses
the LLM itself as the retriever: instead of dense-embedding similarity, it asks
the model to judge each chapter's relevance to each question. This document
covers the granularity variants (**Filter2**, **Filter3**, **Filter10**,
**Filter100**), the standalone analysis script ([`filter.py`](#filterpy)) that
tunes the keep/drop threshold from the gold labels, and the findings from the
English run.

## `answer_filter.py`

A trimmed variant of per-chapter extraction that plays the same role as Vector
RAG — a **retrieval step that selects chapters** — but uses the LLM itself as
the retriever instead of dense embeddings. Where Extract summarizes each
chapter and answers from the summaries, Filter asks only "is this chapter
relevant?" and answers from the **full text** of the kept chapters.

The `--verdicts {2,3,10}` switch selects the classification granularity. The
two- and three-level variants ultimately reduce Phase 2 to a binary keep/drop
decision; the difference is where the drop threshold sits:

- **`--verdicts 2` (→ Filter2)**: two-level verdict `yes` / `no`. Phase 2 keeps
  only `yes`, a high bar that drops anything the model is not sure about.
- **`--verdicts 3` (default → Filter3)**: three-level verdict `yes` / `maybe` /
  `no`. Phase 2 keeps every chapter whose verdict is not `no` (i.e., both
  `yes` and `maybe`), so uncertainty is resolved toward inclusion. The `maybe`
  label is a trick for shifting the threshold: routing uncertain chapters
  through a middle verdict instead of forcing a yes/no call raises the
  effective `no` bar and lets more chapters survive into Phase 2.
- **`--verdicts 10` (→ Filter10, Phase 1 only)**: eleven-level verdict (an
  integer `0`–`10`). Phase 1 records the raw score per `(chapter, question)`
  pair so the keep/drop threshold can be chosen *after* the distribution is
  observed — a single Phase 1 run feeds every threshold under test, instead of
  one run per threshold as with the 2- and 3-level variants. Phase 2 is not
  wired up for this variant yet: run only Phase 1 (with `--phase1`) to produce
  `filter10.tsv`, inspect the score distribution with
  [`filter.py`](#filterpy), then decide a threshold and add the Phase 2 path.
- **`--verdicts 100` (→ Filter100, Phase 1 only)**: 101-level verdict (an
  integer `0`–`100`). It was tried as a finer-grained counterpart of Filter10,
  but the model self-quantized to multiples of 10 (only 13 of 101 values used),
  so Filter100 is effectively Filter10 scaled ×10 — sparse, with a *worse*
  unrecoverable floor (11 gold scored 0 vs 7). The scale is not the lever; see
  [Filter100: filter10 ×10](#filter100-filter10-x10). Same Phase-1-only posture
  as Filter10: run with `--phase1` to produce `filter100.tsv`, then inspect the
  occurrence count with `filter.py --scale 100`.

**Algorithm**

Phase 1 — Relevance classification (37 chapters × 50 questions = 1,850 calls):

1. Outer loop iterates over chapters; inner loop iterates over questions. This
   keeps the same chapter text in the KV cache across all questions for that
   chapter, mirroring `answer_extract.py`.
2. For each (chapter, question) pair, pass the chapter text as context and ask
   the model whether the chapter is relevant to the question. CoT is disabled
   (`include_thoughts=False`) and the reply is a single token (plain text, no
   structured schema) — for V=2/3 parsed by first character, for V=10/100
   parsed for the first integer in `[0, scale]` (`scale` = 10 or 100),
   retrying up to 3 times on an unclear reply. The fallback on a still-unclear
   reply is the inclusion side of the chosen granularity: `yes` for
   `--verdicts 2`, `maybe` for `--verdicts 3`, and mid-scale (`5` for V=10,
   `50` for V=100) for the numeric variants, so an unparseable answer keeps
   the chapter rather than dropping it.
3. Write the result immediately to the checkpoint file and flush.

Phase 2 — Answer (50 calls):

4. Collect the kept chapters for the question. For `--verdicts 2` that is
   only `yes`; for `--verdicts 3` it is every chapter whose verdict is not
   `no` (both `yes` and `maybe`).
5. Build a context block with the **full chapter text** (not a summary)
   labeled `[Chapter N]`, and ask the model to answer in English using only
   that context.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level) and
  `../all/<lang>-gemini.jsonl` (scenes — needed in Phase 2 because Phase 1
  stored only verdicts, unlike Extract which kept the summary text)
- **Output**: `results-<lang>/filter{V}.jsonl` — `filter2.jsonl` for
  `--verdicts 2`, `filter3.jsonl` for the default `--verdicts 3` — one record
  per question:
  - `question_id` — 1-origin line number in the input file
  - `expanded` — kept chapter numbers, as `["5", "10", ...]` strings
  - `answer` — the model's answer
  - *(Filter10/Filter100 have no `.jsonl` yet — Phase 2 is deferred until the
    threshold is chosen; only the verdict TSV below exists.)*
- **Verdict file**: `results-<lang>/filter{V}.tsv` — a TSV with a
  `chapter	question_id	verdict` header followed by one row per classified
  `(chapter, question_id)` pair (all chapters in a single file):
  - `chapter` — chapter number
  - `question_id` — 1-origin line number in the input file
  - `verdict` — relevance verdict: `yes` or `no` for V=2; `yes`, `maybe`, or
    `no` for V=3; an integer `0`–`10` for V=10; an integer `0`–`100` for V=100

Resume-safe at two levels: question IDs already in the output file are skipped
entirely; `(question_id, chapter)` pairs already in the verdict file are skipped
in Phase 1.

### Failure mode

Its main failure mode is the same shape as Extract's but with a different
cause: a wrong `no` verdict drops a gold chapter unrecoverably (in V=2 only
`yes` keeps it; in V=3 both `yes` and `maybe` do). In the English V=3 run
this hit 6 questions, three of them (Q32, Q34, Q42) total wipeouts where every
gold chapter was marked `no`. The `maybe` bar still earns its keep: of the 86
gold chapters, 42 were `yes`, 32 were `maybe`, and 12 were `no` — so keeping
only `yes` would have given chapter recall 0.49, while keeping `yes`+`maybe`
gives 0.86. That rescue is what lifts the Filter3 row in the
[Results table](README.md#results) to 0.930 — top of the table. The V=2 run
confirms the contrast from the other side: forced into a binary call, the
model marks 33 of 86 gold chapters `no` (vs. 12 under V=3) and only 53 earn
`yes` (recall 0.62), which drops Filter2 to 0.790 — below Extract. See the
[Filter case study](results-en/README.md#filter-per-chapter-reading-with-a-loose-relevance-bar).

## `filter.py`

Standalone analysis script (no LLM, no output file — terminal tables only,
like [`sweep_rag.py`](README.md#sweep_ragpy)). It reads the Phase 1 verdict
TSVs produced by `answer_filter.py` and the gold chapters from
`questions-<lang>.jsonl` to answer three questions:

1. How are the scores distributed, and do they separate gold from non-gold
   chapters?
2. Which keep/drop threshold maximizes chapter recall / precision / F1,
   broken down by question type?
3. How do the filter2 (yes/no) and filter3 (yes/maybe/no) verdicts map onto
   the score scale, and which threshold reproduces each variant's keep/drop
   boundary?

The `--scale {10,100}` switch selects which verdict TSV to read (`filter10.tsv`
or `filter100.tsv`). Scale 10 runs the full eight-table suite below; scale 100
prints only the raw score occurrence count (zeros filtered) and stops, because
filter100 is filter10 scaled ×10 and the detailed tables add nothing (see
[Filter100: filter10 ×10](#filter100-filter10-x10)). Requires the matching
verdict TSV; the filter2/filter3 crosstabs (Tables 5-8) appear only when those
TSVs also exist. Run:

```sh
make filter                  # filter10 verdicts + full analysis (LANG=en default)
make filter LANG=ja          # Japanese
make filter SCALE=100        # filter100 occurrence count only
```

Eight tables (scale 10 only):

1. **Score distribution** — histogram of scores over all
   `(chapter, question)` pairs, split by gold vs non-gold.
2. **Threshold sweep** — for each threshold: strict subset recall, partial
   coverage recall, precision, F1, and mean chapters kept. Sweeps every
   integer `0`–`11`.
3. **Per-type breakdown** — the threshold sweep repeated for each gold `type`
   (`single` / `cross`), so the recall-precision frontier is visible per scope.
4. **Retrieval risk** — gold chapters scored at or below the cutoff (3), which
   no higher threshold can recover (the unrecoverable floor).
5. **Crosstab** — filter2 verdict (Table 5a) and filter3 verdict (Table 5b)
   crossed against score, both overall and gold-only.
6. **Equivalence** — retrieval metrics for the filter2/3 keep rules side by
   side with every threshold, so the matching threshold can be read off
   directly.
7. **Agreement rate** — fraction of pairs where the score's keep/drop call
   matches filter2/3's, per threshold.
8. **Score summary** — mean / median / mode of the raw score within each
   filter2/3 verdict label.

---

## Findings (English run)

50 questions, 37 chapters, 1,850 `(chapter, question)` pairs, 86 of them gold.
The Filter10 findings are below; Filter100 follows in
[Filter100: filter10 ×10](#filter100-filter10-x10). Generated by `make filter`
(Filter10) or `make filter SCALE=100` (Filter100) — see [`filter.py`](#filterpy).

### Score distribution and gold separation

The model treats the 0-10 scale as effectively **bimodal**: 91.4% of all pairs
receive score 0 (irrelevant), and the next largest bucket is score 10
(2.1%, 38 pairs). Scores 1 and 9 are nearly absent (4 and 0 pairs), so the
model collapses "slightly relevant" onto 2 and "highly relevant" onto 10
rather than spreading across the scale.

| score | count | gold | non-gold | gold share |
|------:|------:|-----:|---------:|-----------:|
| 0 | 1691 | 7 | 1684 | 0.4% |
| 1 | 4 | 1 | 3 | 25.0% |
| 2 | 70 | 11 | 59 | 15.7% |
| 3 | 10 | 6 | 4 | 60.0% |
| 4 | 15 | 9 | 6 | 60.0% |
| 5 | 6 | 5 | 1 | 83.3% |
| 6 | 6 | 2 | 4 | 33.3% |
| 7 | 1 | 1 | 0 | 100.0% |
| 8 | 9 | 8 | 1 | 88.9% |
| 9 | 0 | 0 | 0 | — |
| 10 | 38 | 36 | 2 | 94.7% |

Gold chapters cluster at the extremes: 41.9% score 10 (directly relevant), but
8.1% (7 of 86) score 0 — **irrecoverably dropped** at any threshold. The
score-2 bucket is the noisy middle: 11 gold but 59 non-gold (gold share only
15.7%). From score 3 upward the gold share clears 60%, and from score 5 upward
it exceeds 80% — so the scale does separate, just not at score 2.

### Threshold sweep

Keeping chapters with `score >= threshold`:

| threshold | strict recall | partial recall | precision | F1 | avg kept |
|----------:|--------------:|---------------:|----------:|---:|---------:|
| 1 | 0.900 | 0.953 | 0.497 | 0.653 | 3.2 |
| 2 | 0.880 | 0.943 | 0.503 | 0.656 | 3.1 |
| **3** | **0.760** | **0.857** | **0.788** | **0.821** | **1.7** |
| 4 | 0.680 | 0.803 | 0.813 | 0.808 | 1.5 |
| 5 | 0.600 | 0.730 | 0.867 | 0.792 | 1.2 |
| 7 | 0.560 | 0.673 | 0.938 | 0.784 | 1.0 |

The F1 peak is at **threshold 3** (0.821) — partial recall 0.857 matches
Filter3's 0.86, at higher precision (0.788 vs Filter3's 0.632). Thresholds 1-2
buy a few points of recall (partial 0.94-0.95) but roughly halve precision
(0.50) by letting the 59 non-gold score-2 chapters through. Thresholds 5+ trade
recall for precision: at threshold 5 the model keeps ~1.2 chapters/question on
average and still hits 0.73 partial recall.

### Per-type breakdown

The 50 questions split into 25 `single` (one gold chapter) and 25 `cross`
(multiple gold chapters). The separation is type-dependent:

- **single** — perfect: strict recall is **1.000 at thresholds 1-8**, and
  precision is 1.000 from threshold 5 up. A single-chapter question is an easy
  relevance call; the model never confuses it.
- **cross** — the frontier. Strict recall drops sharply with threshold: 0.800
  at threshold 1, 0.520 at threshold 3, 0.200 at threshold 5. Cross-reference
  questions require keeping *several* chapters, and each extra gold chapter at
  a low score is a potential drop.

### Retrieval risk (unrecoverable gold)

**7 of 86 gold chapters (8.1%) score 0** — no threshold can recover them.
25 of 86 (29%) score 3 or below. Every single low-score gold chapter belongs
to a `cross` question (none are `single`), and the worst-hit questions (Q31,
Q32, Q34, Q42) are exactly the Filter3 wipeouts. This is the same dense-
retrieval blindness that RAG `k=10` cannot fix: load-bearing chapters whose
relevance is indirect enough that neither embeddings nor the LLM's own
judgement surfaces them.

### Crosstab: filter2/3 vs filter10

Cross-referencing each variant's verdict against the filter10 score (1,850
common pairs) reveals how the categorical labels map onto the numeric scale.

**filter3** maps almost deterministically:

| filter3 verdict | pairs | filter10 median | filter10 mode | reading |
|-----------------|------:|----------------:|--------------:|---------|
| `yes` | 44 | 10 | 10 | "directly relevant" ≈ score 8-10 |
| `maybe` | 73 | 2 | 2 | "uncertain" ≈ score 2-6 |
| `no` | 1733 | 0 | 0 | "irrelevant" ≈ score 0 |

filter3 `yes` lands almost entirely at score 8-10 (43 of 44 pairs); `no` at
score 0 (1687 of 1733). The `maybe` label fills the middle band centered on
score 2 — it is literally the "score-2" verdict wearing a different name.

**filter2** (`yes`/`no`) is noisier because the forced binary call splits the
`maybe` band unevenly: filter2 `yes` (64 pairs) has median 10 but spreads down
to score 2, and filter2 `no` absorbs score-2 pairs (68) that filter3 calls
`maybe`.

### Equivalence

Comparing the keep-rule metrics side by side (Table 6), each filter variant
matches a specific filter10 threshold:

| keep rule | strict recall | partial recall | precision | avg kept |
|-----------|--------------:|---------------:|----------:|---------:|
| **filter2 (keep yes)** | 0.600 | 0.733 | 0.828 | 1.3 |
| **filter10 >= 5** | **0.600** | **0.730** | **0.867** | **1.2** |
| **filter3 (keep != no)** | 0.880 | 0.920 | 0.632 | 2.3 |
| **filter10 >= 2** | **0.880** | 0.943 | 0.503 | 3.1 |

- **filter2 (keep yes) ≡ filter10 >= 5.** Strict recall matches exactly
  (0.600); partial recall (0.733 vs 0.730) and avg kept (1.3 vs 1.2) are
  within rounding. The cleanest correspondence.
- **filter3 (keep != no) ≡ filter10 >= 2, slightly loosened.** Strict recall
  matches exactly (0.880), but filter10 >= 2 keeps one more chapter per
  question on average (3.1 vs 2.3) and has lower precision (0.503 vs 0.632).
  The gap is the 40 score-2 pairs that filter3 calls `no` — the three-level
  verdict acts as an additional filter on the noisy score-2 band that a bare
  numeric threshold cannot replicate.

### Why Filter10 costs less

Filter2 and Filter3 each require a **separate** Phase 1 run (1,850 LLM calls
each, 3,700 total) because the verdict label is baked into the prompt. Filter10
runs Phase 1 **once** (1,850 calls) and reproduces both variants' keep/drop
boundaries by thresholding the same scores — `>= 5` for Filter2, `>= 2` for
Filter3 — plus every threshold in between, at no extra LLM cost. Phase 2
(answering) is only ~50 calls per threshold, so testing several thresholds is
cheap once the single Phase 1 run exists.

### Filter100: filter10 ×10

Filter100 (`make filter SCALE=100`) tested whether a 0–100 scale would spread
filter10's bimodal collapse (91.4% at score 0). **It did not: the model
treated 0–100 as 0–10 scaled ×10 and the distribution is sparse** — of 101
possible values only 13 were used, almost all multiples of 10:

| score | count |
|------:|------:|
| 0 | 1720 |
| 10 | 3 |
| 20 | 37 |
| 25 | 2 |
| 30 | 8 |
| 40 | 16 |
| 50 | 7 |
| 60 | 8 |
| 70 | 1 |
| 80 | 1 |
| 85 | 3 |
| 90 | 1 |
| 100 | 43 |

(13 distinct values; the 88 unused are all non-multiples of 10 except 25/85.)
Because the model self-quantized to multiples of 10, every decile bucket
collapses to a single score, so the threshold sweep and crosstabs reproduce
filter10's exactly — there is nothing further to analyze, and `filter.py
--scale 100` prints just this occurrence count and stops.

The finer scale made the unrecoverable floor *worse*, not better: **11 gold
chapters scored 0 (vs 7 under filter10)** — the extra room let the model
express more confidence that indirect-relevance chapters are irrelevant. The
affected questions are the same cross-reference wipeouts (Q32, Q34, Q42 recur
from filter10's floor).

**Scale is not the lever.** The bimodal collapse is the model's genuine
uncertainty shape, not a resolution artifact — a chapter is either clearly
relevant or clearly not, with a thin intrinsically-ambiguous middle that no
finer scale resolves. The gold-scored-0 floor calls for judgement
*decomposition* (multi-axis scoring), and the retrieval misses a different
retrieval *mechanism* (BM25/lexical hybrid); both are laid out in
[PLAN.md](PLAN.md).

### Where this leaves the threshold

Phase 2 is still not wired up for Filter10. The threshold sweep puts the
answer-accuracy-optimal threshold in the loose band (1–3, where partial recall
stays above 0.85), so sweeping filter10 thresholds 1, 2, and 3 in Phase 2
(~150 calls total) is the cheapest way to confirm which maximizes QA accuracy.
Filter100 earns no Phase 2 of its own — it is filter10 ×10. The chapters no
threshold can recover (the gold-scored-0 floor) need a different lever:
multi-axis scoring to prevent the 0 verdict, and BM25/lexical hybrid to surface
what the LLM mis-judges — both in [PLAN.md](PLAN.md).
