# Filter: the LLM as retriever

The Filter strategy ([`answer_filter.py`](#answer_filterpy)) uses the LLM itself
as the retriever: instead of dense-embedding similarity, it asks the model to
judge each chapter's relevance to each question, then answers from the **full
text** of the kept chapters. This document covers the method, the granularity
variants (**Filter2 / Filter3 / Filter10 / Filter100 / Filter5d**), the
standalone analysis scripts, the findings from the English run, and the final
verdict on where this strategy lands relative to Vector RAG.

## Coverage at a glance

Retrieval metrics by filter variant (50 questions, 86 gold chapter-pairs), with
RAG and Ceiling as reference points. Strict recall = fraction of questions
where gold ⊆ kept; partial recall = mean |gold ∩ kept| / |gold|; Phase 2
score = `(correct + 0.5·partial) / 50` (from [README](README.md#results)).

| method | strict recall | partial recall | avg kept | gold floor | Phase 2 score |
|---|---:|---:|---:|---:|---:|
| Filter2 (keep `yes`) | 0.60 | 0.73 | 1.3 | 33/86 | 0.790 |
| Filter3 (keep ≠ `no`) | 0.88 | 0.92 | 2.3 | 12/86 | 0.930 |
| Filter10 ≥3 (F1 peak) | 0.76 | 0.86 | 1.7 | 7/86 | — |
| Filter100 (any threshold) | — | — | — | 11/86 | — |
| Filter5d sum ≥5 | **1.00** | **1.00** | 14.3 | **0/86** | — |
| *RAG k=10 (reference)* | — | 0.84 | — | — | 0.920 |
| *Ceiling (reference)* | 1.00 | 1.00 | — | 0 | 0.990 |

Gold floor = gold chapters unrecoverable at any keep threshold (scored 0 under
the numeric variants, or marked `no` under the verdict variants). Filter5d
eliminates the floor (0/86) but only by keeping ~14 chapters/question — the
floor-vs-excess trade-off that is the method's hard limit (see
[Verdict](#verdict)).

## Verdict

**The LLM-as-retriever has no practical advantage over Vector RAG.**

- **Ceiling redefines the evaluation axis.** The Ceiling run (gold chapters fed
  verbatim as context) scores **0.990** — so once the gold chapters reach the
  answerer, the answer follows, and over-inclusion does not hurt accuracy (only
  Phase 2 token cost). That means a retrieval method can be judged on a single
  question — *does it surface the gold chapters?* — without running Phase 2 at
  all. The metric that matters is the **gold floor**: gold chapters that are
  unrecoverable at any keep threshold. Floor is the ceiling on a method's recall.
- **The floor-vs-excess trade-off is the method's hard limit.** A per-chapter
  filter can drive the floor to zero only by keeping almost everything. Filter5d
  achieves **floor 0/86** but at **~14 chapters kept per question** (excess 629
  non-gold pairs). Floor-0 and low excess do not coexist — you either tolerate a
  floor (Filter10, floor 7/86, ~1.7 kept) or you over-include (Filter5d). That
  trade-off *is* the limit of LLM-as-retriever.
- **The practical variant, Filter10, only matches Vector RAG k=10.** Filter10's
  retrieval (floor 7/86, partial recall ≈0.86) is on par with dense retrieval at
  k=10 (chapter recall 0.840). But Filter pays **1,850 LLM calls** in Phase 1
  (37 chapters × 50 questions) against k=10's single embedding + cosine pass —
  **hundreds of times the cost for an equivalent result.**

So while Filter3 posts the highest *Phase 2* QA score in the table (0.930,
slightly above RAG k=10's 0.920), that margin does not justify the cost, and the
gold-floor view shows no retrieval advantage. The residual the filter cannot
reach (the confident-wrong-`no` floor) needs a different *mechanism* — the
BM25/lexical hybrid in [PLAN.md](PLAN.md) — not a better LLM prompt.

## `answer_filter.py`

A trimmed variant of per-chapter extraction that plays the same role as Vector
RAG — a **retrieval step that selects chapters** — but uses the LLM itself as
the retriever instead of dense embeddings. Where Extract summarizes each chapter
and answers from the summaries, Filter asks only "is this chapter relevant?" and
answers from the **full text** of the kept chapters.

The `--verdicts {2,3,10,100,5d}` switch selects the classification granularity:

- **`--verdicts 2` (→ Filter2)**: two-level verdict `yes` / `no`. Phase 2 keeps
  only `yes`, a high bar that drops anything the model is not sure about.
- **`--verdicts 3` (default → Filter3)**: three-level verdict `yes` / `maybe` /
  `no`. Phase 2 keeps every chapter whose verdict is not `no` (both `yes` and
  `maybe`), so uncertainty is resolved toward inclusion. The `maybe` label is a
  trick for shifting the threshold: routing uncertain chapters through a middle
  verdict instead of forcing a yes/no call raises the effective `no` bar and
  lets more chapters survive into Phase 2.
- **`--verdicts 10` (→ Filter10, Phase 1 only)**: eleven-level verdict (integer
  `0`–`10`). Phase 1 records the raw score per `(chapter, question)` pair so the
  keep/drop threshold can be chosen *after* the distribution is observed — one
  Phase 1 run feeds every threshold under test, instead of one run per threshold
  as with the 2- and 3-level variants.
- **`--verdicts 100` (→ Filter100, Phase 1 only)**: 101-level verdict (integer
  `0`–`100`). Tried as a finer-grained counterpart of Filter10, but the model
  self-quantized to multiples of 10 (only 13 of 101 values used), so Filter100
  is effectively Filter10 scaled ×10 — sparse, with a *worse* floor (11 gold
  scored 0 vs 7). See [Filter100: filter10 ×10](#filter100-filter10-x10).
- **`--verdicts 5d` (→ Filter5d, Phase 1 only)**: five-axis verdict (five
  integers `0`–`10`). Decomposes relevance across orthogonal axes to attack the
  gold-scored-0 floor. See [Filter5d: multi-axis scoring](#filter5d-multi-axis-relevance-scoring).

The 2- and 3-level variants ultimately reduce Phase 2 to a binary keep/drop
decision; the difference is only where the drop threshold sits.

**Algorithm**

Phase 1 — Relevance classification (37 chapters × 50 questions = 1,850 calls):

1. Outer loop iterates over chapters; inner loop iterates over questions. This
   keeps the same chapter text in the KV cache across all questions for that
   chapter, mirroring `answer_extract.py`.
2. For each (chapter, question) pair, pass the chapter text as context and ask
   the model whether the chapter is relevant. CoT is disabled
   (`include_thoughts=False`). For V=2/3 the reply is a single token parsed by
   first character; for V=10/100 the first integer in `[0, scale]`; for V=5d a
   structured `AxisScores` object (five `int` fields, `ge=0 le=10`). On an
   unclear reply it retries up to 3 times, then falls back to the **inclusion**
   side of the chosen granularity (`yes` for V=2, `maybe` for V=3, mid-scale for
   V=10/100), so an unparseable answer keeps the chapter rather than dropping it.
3. Write the result immediately to the checkpoint file and flush.

Phase 2 — Answer (50 calls):

4. Collect the kept chapters for the question. For `--verdicts 2` that is only
   `yes`; for `--verdicts 3` it is every chapter whose verdict is not `no`. (The
   numeric variants V=10/100/5d are Phase 1 only — see the verdict above for why
   Phase 2 was not pursued.)
5. Build a context block with the **full chapter text** (not a summary) labeled
   `[Chapter N]`, and ask the model to answer using only that context.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level) and
  `../all/<lang>-gemini.jsonl` (scenes — needed in Phase 2 because Phase 1 stored
  only verdicts, unlike Extract which kept the summary text).
- **Output (Phase 2)**: `results-<lang>/filter{V}.jsonl` (`filter2.jsonl` /
  `filter3.jsonl`) — one record per question with `question_id`, `expanded`
  (kept chapter numbers), and `answer`.
- **Verdict file (Phase 1)**: `results-<lang>/filter{V}.tsv` — one row per
  classified `(chapter, question_id)` pair. For V=2/3/10/100 the columns are
  `chapter`, `question_id`, `verdict`; for V=5d the columns are `chapter`,
  `question_id`, and the five axis scores `factual entity causal reference
  thematic` (the sum is derived on read, not stored).

Resume-safe at two levels: question IDs already in the output file are skipped
entirely; `(question_id, chapter)` pairs already in the verdict file are skipped
in Phase 1.

### Failure mode

Its main failure mode is the same shape as Extract's but with a different cause:
a wrong `no` verdict drops a gold chapter unrecoverably (in V=2 only `yes` keeps
it; in V=3 both `yes` and `maybe` do). In the English V=3 run this hit 6
questions, three of them (Q32, Q34, Q42) total wipeouts where every gold chapter
was marked `no`. Of the 86 gold chapters, 42 were `yes`, 32 were `maybe`, and 12
were `no` — so keeping only `yes` gives chapter recall 0.49, while keeping
`yes`+`maybe` gives 0.86. The V=2 run confirms the contrast from the other side:
forced into a binary call, the model marks 33 of 86 gold chapters `no` and only
53 earn `yes` (recall 0.62), dropping Filter2 to 0.790 — below Extract.

---

## Single-axis variants (Filter2/3/10/100)

### `filter.py`

Standalone analysis script (no LLM, no output file — terminal tables only). It
reads the Phase 1 verdict TSVs and the gold chapters from `questions-<lang>.jsonl`
to answer three questions:

1. How are the scores distributed, and do they separate gold from non-gold?
2. Which keep/drop threshold maximizes recall / precision / F1, by question type?
3. How do the filter2/filter3 verdicts map onto the score scale, and which
   threshold reproduces each variant's keep/drop boundary?

The `--scale {10,100}` switch selects which verdict TSV to read. Scale 10 runs
the full eight-table suite; scale 100 prints only the raw score occurrence count
and stops, because filter100 is filter10 scaled ×10. Run:

```sh
make filter                  # filter10 verdicts + full analysis (LANG=en default)
make filter LANG=ja          # Japanese
make filter SCALE=100        # filter100 occurrence count only
```

### Score distribution and gold separation

50 questions, 37 chapters, 1,850 `(chapter, question)` pairs, 86 of them gold.
The model treats the 0–10 scale as effectively **bimodal**: 91.4% of all pairs
score 0, and the next-largest bucket is score 10 (2.1%). Scores 1 and 9 are
nearly absent, so the model collapses "slightly relevant" onto 2 and "highly
relevant" onto 10 rather than spreading across the scale.

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

Gold chapters cluster at the extremes: 41.9% score 10, but 8.1% (7 of 86) score
0 — **irrecoverably dropped** at any threshold. The score-2 bucket is the noisy
middle (11 gold, 59 non-gold). From score 3 upward the gold share clears 60%,
and from score 5 upward exceeds 80% — the scale separates, just not at score 2.

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
Filter3's 0.86 at higher precision (0.788 vs 0.632). The separation is
type-dependent: `single` questions are perfect (strict recall 1.000 at
thresholds 1–8); `cross` questions are the frontier (strict recall 0.800 at
threshold 1, 0.520 at 3, 0.200 at 5).

### Retrieval risk (the gold floor)

**7 of 86 gold chapters (8.1%) score 0** — no threshold can recover them. 25 of
86 (29%) score 3 or below. Every low-score gold chapter belongs to a `cross`
question, and the worst-hit (Q31, Q32, Q34, Q42) are exactly the Filter3
wipeouts. This is the same dense-retrieval blindness that RAG k=10 cannot fix:
load-bearing chapters whose relevance is indirect enough that neither embeddings
nor the LLM's own judgement surfaces them.

### Crosstab and equivalence: filter2/3 vs filter10

filter3 maps almost deterministically onto the score scale: `yes` lands at score
8–10 (median 10), `maybe` fills the middle band centered on score 2, `no` sits at
0. The `maybe` label is literally the "score-2" verdict wearing a different name.
filter2 is noisier because the forced binary call splits the `maybe` band
unevenly. Comparing the keep-rule metrics side by side, each variant matches a
specific filter10 threshold:

| keep rule | strict recall | partial recall | precision | avg kept |
|-----------|--------------:|---------------:|----------:|---------:|
| **filter2 (keep yes)** | 0.600 | 0.733 | 0.828 | 1.3 |
| **filter10 >= 5** | **0.600** | **0.730** | **0.867** | **1.2** |
| **filter3 (keep != no)** | 0.880 | 0.920 | 0.632 | 2.3 |
| **filter10 >= 2** | **0.880** | 0.943 | 0.503 | 3.1 |

So a single Filter10 Phase 1 run reproduces both categorical variants by
thresholding — `>= 5` for Filter2, `>= 2` for Filter3 — plus every threshold in
between, at no extra LLM cost. Filter2 and Filter3 each need a *separate* 1,850-
call Phase 1 (the verdict label is baked into the prompt); Filter10 runs Phase 1
once and tests every threshold from the same scores. This is why, among the
single-axis variants, **Filter10 is the cost-efficient one** and the natural
practical limit.

### Filter100: filter10 ×10

Filter100 (`make filter SCALE=100`) tested whether a 0–100 scale would spread
filter10's bimodal collapse. **It did not: the model treated 0–100 as 0–10 scaled
×10** — of 101 possible values only 13 were used, almost all multiples of 10 (a
few 25/85 aside). Every decile bucket collapses to a single score, so the
threshold sweep and crosstabs reproduce filter10's exactly.

The finer scale made the floor *worse*: **11 gold chapters scored 0 (vs 7 under
filter10)** — the extra room let the model express more confidence that
indirect-relevance chapters are irrelevant. The affected questions are the same
cross-reference wipeouts (Q32, Q34, Q42).

**Scale is not the lever.** The bimodal collapse is the model's genuine
uncertainty shape, not a resolution artifact — a chapter is either clearly
relevant or clearly not, with a thin intrinsically-ambiguous middle that no
finer scale resolves. The gold-scored-0 floor calls for judgement
*decomposition* (Filter5d, below), and the retrieval misses for a different
retrieval *mechanism* (BM25/lexical hybrid, [PLAN.md](PLAN.md)).

---

## Filter5d: multi-axis relevance scoring

### The problem — the gold-scored-0 floor

The single-axis variants share one failure mode: a handful of gold chapters
score 0 and are unrecoverable at any threshold (7/86 under Filter10, 11/86 under
Filter100). The lever is not scale but **decomposition**: rate each
`(chapter, question)` pair on five independent relevance axes, each 0–10, so that
a chapter scoring 0 on one axis can still earn points on another. Structurally, a
chapter must score 0 on **all five** axes to total 0 — a much higher bar than a
single snap-to-0.

| axis | captures |
|------|----------|
| `factual` | facts that directly answer the question |
| `entity` | the question's characters, objects, or places appear or act |
| `causal` | causes, prerequisites, or consequences of the question's event |
| `reference` | cross-references, callbacks, or foreshadowing linked to the question |
| `thematic` | themes, symbols, or motifs related to the question |

### `filter5d.py`

Standalone analysis script (no LLM, terminal tables only). It reads
`filter5d.tsv` and the gold chapters to answer: how many gold pairs land at
sum=0 (the floor)? does a sum threshold separate gold from non-gold? which axes
carry the gold signal? Run:

```sh
make filter5d              # builds filter5d.tsv if missing, then runs this
make filter5d LANG=ja      # Japanese
```

A design note specific to this script: **absence is the failure, surfeit is
not.** Since Ceiling (0.990) shows over-inclusion does not hurt accuracy, the
analysis reports an **excess** column (non-gold chapters kept) as a cost metric,
not a correctness one.

### The floor: eliminated

**0 of 86 gold pairs land at sum=0** — the design goal is fully achieved.

| variant | gold pairs at score/sum 0 | floor |
|---------|---------------------------|------:|
| Filter10 (single 0–10) | 7 / 86 | 8.1% |
| Filter100 (single 0–100) | 11 / 86 | 12.8% |
| **Filter5d (five-axis sum)** | **0 / 86** | **0%** |

No single axis is individually indispensable: removing any one axis from the sum
still yields 0 gold pairs at sum=0. Every gold pair has signal on at least two
axes.

### Sum distribution: a natural separation at sum=5

The gold minimum sum is **5** — no gold pair scores below it — while 615 non-gold
pairs occupy the sum 1–4 band:

| keep rule | strict recall | excess | avg kept |
|-----------|--------------:|-------:|---------:|
| sum > 0 (≥ 1) | 1.000 | 1244 | 26.6 |
| **sum ≥ 5** | **1.000** | **629** | **14.3** |
| sum ≥ 6 | 0.960 | 547 | 12.6 |

`sum ≥ 5` preserves all gold while cutting excess roughly in half versus the
binarized `sum > 0`. At `sum ≥ 6` the first gold pairs drop (Q42 Ch23, Q50 Ch23,
both at sum=5). As with the single-axis variants, the separation is
type-dependent: `single` questions hold recall 1.000 up to sum=21, while `cross`
questions hit the ceiling at sum=5 and start dropping at sum=6.

### Per-axis analysis: who carries the gold?

The five axes have sharply different signal-to-noise profiles:

| axis | gold > 0 | non-gold > 0 | noise ratio | role |
|------|---------:|-------------:|------------:|------|
| `factual` | 46/86 | 13 | **0.12** | precision anchor (but redundant in sum) |
| `entity` | **86/86** | 1209 | 0.84 | recall driver (catches everything, noisy) |
| `causal` | 84/86 | 446 | 0.69 | balanced |
| `reference` | 76/86 | 450 | 0.78 | underperforms (10 gold at 0) |
| `thematic` | 85/86 | 826 | 0.83 | noisy |

- **`entity` is the only axis where gold min > 0.** Every gold pair has at least
  entity=1 — the question's characters, objects, or places always appear in a
  gold chapter — so `entity ≥ 1` is the only single-axis rule with full gold
  inclusion, but at huge excess (1209 non-gold pairs).
- **`factual` is the most precise** (noise ratio 0.12) but catches only 46/86:
  the 40 gold pairs at factual=0 are cross-reference chapters that don't directly
  answer the question on their own. It is also **redundant in the sum** — every
  pair with factual>0 also fires on another axis, so dropping factual changes the
  floor and excess by nothing. It remains useful only as an independent precision
  gate (e.g. `factual ≥ 6` is near-pure gold but misses the cross-reference half).
- **`reference` underperforms expectations.** Designed to rescue cross-reference
  callbacks, it leaves 10 gold pairs at 0; `causal` (84/86) and `thematic`
  (85/86) rescue more than `reference` (76/86).

### Keep-rule recommendation, and why it is also the ceiling of the method

**`sum ≥ 5`** is the recommended keep rule. It matches the gold minimum exactly:
strict recall 1.000, excess halved versus `sum > 0`, and **zero degrees of
freedom** — one threshold on one derived quantity.

An exhaustive OR-combination search (Table 9, `axis_i ≥ t_i` for any axis, 5⁵ =
3,125 combinations) finds `entity≥3 OR causal≥2 OR reference≥5 OR thematic≥4` at
excess 613 — only 16 (2.5%) below `sum ≥ 5`. **This is an upper bound, not a
rule**: five thresholds fitted to the known 86-pair gold set after seeing the
answer is fitting the metric, not learning a generalizable rule. `sum ≥ 5` gives
the same gold inclusion with 2.5% more excess and far more robustness.

Crucially, even the *best* rule keeps **~14 chapters per question**. That is the
unavoidable cost of floor-0:

| metric | Filter10 (≥ 3) | Filter5d (sum ≥ 5) |
|--------|---------------:|-------------------:|
| strict recall | 0.760 | **1.000** |
| partial recall | 0.857 | **1.000** |
| precision | 0.788 | 0.120 |
| avg kept | 1.7 | 14.3 |
| gold floor | 7/86 | **0/86** |

Filter5d eliminates the floor only by trading away an order of magnitude of
precision. Floor-0 and a tight keep set are mutually exclusive for this method —
which is exactly the limit named in the [Verdict](#verdict).

---

## Conclusion

The Filter experiment establishes a clean boundary on the LLM-as-retriever idea:

1. **Evaluation collapses to the gold floor.** Ceiling (0.990) proves that gold
   inclusion suffices and over-inclusion is harmless, so a retrieval method needs
   only to surface the gold chapters — no Phase 2 QA run is required to rank it.
2. **The floor-vs-excess trade-off is a hard limit, not a tuning problem.**
   Filter5d reaches floor 0/86 but only by keeping ~14 chapters/question; the
   single-axis variants keep ~2 but leave a 7–11 gold floor. No prompt or scale
   bridges the two.
3. **The practical variant matches dense retrieval at hundreds of times the
   cost.** Filter10 (the cost-efficient single-axis variant, since one Phase 1
   run covers every threshold) lands at floor 7/86 and recall comparable to RAG
   k=10's 0.840 — but at 1,850 LLM calls versus one embedding pass. The highest
   Phase 2 score in the table (Filter3, 0.930) beats RAG k=10 (0.920) by one
   question, which does not justify that cost.

The residual the filter cannot reach — the confident-wrong-`no` floor on
indirectly-relevant chapters — is the same dense-retrieval blindness, and the
lever for it is a different *mechanism* (the BM25/lexical hybrid in
[PLAN.md](PLAN.md)), not a finer or differently-decomposed LLM judgement.
