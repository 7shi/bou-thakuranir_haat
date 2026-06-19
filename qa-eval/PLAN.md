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
granularity variants and their analysis in [filter.md](filter.md). This file
tracks only what is not yet built.

## In progress: Multi-axis relevance scoring (5d)

### The problem — the gold-scored-0 floor

The filter10/100 runs share one failure: a handful of gold chapters score 0 and
are unrecoverable at any threshold (**7 under filter10, 11 under filter100** —
all cross-reference chapters whose relevance is indirect). A single "rate
relevance 0–N" prompt lets the model collapse the call to a snap 0; a finer
scale did not help — filter100 is filter10 ×10 and the floor actually grew (see
[filter.md](filter.md#filter100-filter10-x10)). **Scale is not the lever.**

### The lever — decompose the judgement across axes

Rate each `(chapter, question)` pair on **five orthogonal relevance axes**, each
0–10, so that a chapter scoring 0 on one axis can still earn points on another.
A chapter that does not directly answer the question can still score non-zero on
`reference` or `causal` — exactly the cross-reference chapters the single-axis
prompt drops to 0. Structurally, a chapter must score 0 on **all five** axes to
total 0, which is a much higher bar than a single snap-to-0.

| axis | captures |
|------|----------|
| `factual` | facts that directly answer the question |
| `entity` | the question's characters, objects, or places appear or act |
| `causal` | causes, prerequisites, or consequences of the question's event |
| `reference` | cross-references, callbacks, or foreshadowing linked to the question |
| `thematic` | themes, symbols, or motifs related to the question |

### Implementation (DONE — Phase 1, generating)

- `answer_filter.py --verdicts 5d` (Phase 1 only for now). The Phase 2 path
  errors out until the keep rule is chosen (see below).
- **Structured output**: an `AxisScores` pydantic model (five `int` fields,
  `ge=0 le=10`). The JSON field description is injected as a third message via
  `create_json_descriptions_prompt` (same pattern as
  `scripts/translate_questions.py`), so the call is
  `generate_with_schema([context, prompt, json_description], AxisScores, ...)`.
  **`sum` is NOT a model field** — it is computed in logic, since it is pure
  arithmetic the model could only get wrong. `include_thoughts=False`, like the
  other filter variants; the default model is `ollama:gemma4:31b-it-qat`
  (overridable with `-m`).
- **Output**: `results-<lang>/filter5d.tsv` — a TSV with header
  `chapter	question_id	factual	entity	causal	reference	thematic`
  (six columns; **no sum column** — it is derived on read). Read it with
  `read_verdict_5d_tsv(path)` (yields `(chapter, qid, {axis: int})`), defined
  in `answer_filter.py` alongside `read_verdict_tsv`.
- **Makefile**: `make filter5d-tsv` (English) / `make filter5d-tsv LANG=ja`.
- Smoke-tested both directions on the gold model: a gold pairing (Q1 × Ch3,
  the horse question) scored sum=27 (`factual=10, entity=10, causal=5,
  reference=0, thematic=2`); a non-gold pairing (Q3 × Ch3, Vibha's bangles vs.
  the horse chapter) correctly scored all-zeros.

### Next step — distribution inspection + keep-rule decision

Once `filter5d.tsv` is complete, inspect the distribution and **decide the keep
rule** before wiring Phase 2. `filter.py` does NOT yet read the 5d format, so
inspect with a one-off script (load via `read_verdict_5d_tsv`, gold labels from
`questions-<lang>.jsonl`'s `chapters` field) or by adding a `filter.py --scale
5d` path. The questions to answer:

1. **The floor**: how many gold pairs land at **sum=0** (all five axes zero)?
   Target: toward 0. Prior single-axis floors were 7/86 (filter10) and 11/86
   (filter100); the cross-reference chapters behind Q31/Q32/Q34/Q42 are the
   expected hard cases.
2. **Per-axis distribution**: gold vs non-gold, per axis. Which axes carry the
   gold pairs that `factual` scores 0 on? (Expected: `reference` and `causal`
   do most of the rescue.)
3. **Sum distribution**: does a threshold separate gold from non-gold, or does
   it binarize to "sum=0 vs sum>0"?

Candidate keep rules (choose after seeing the distribution):

- **sum > 0** — the binarized rule: keep anything with any signal. **Predicted
  landing** given filter3/filter10's bimodal shapes ("all-no vs not"). The
  design goal stated upfront: *absence is the failure, surfeit is not* — the
  bar is "no gold in the sum=0 set," and over-inclusion costs only Phase 2
  tokens, not correctness.
- **sum >= threshold** — a numeric cutoff if the sum distribution shows
  separation.
- **max(axis) >= threshold** — keep if any one axis fires strongly (strongest
  floor defense, but lets single-axis noise through).
- **non-zero-axis count >= n** — a majority vote, robust to noise on one axis.

### Remaining work after the decision

1. **Wire Phase 2 for 5d** in `answer_filter.py`: the inclusion branch in the
   Phase 2 loop currently only handles `verdicts ∈ {2, 3}` (the `not in (2, 3)`
   guard rejects 5d). Add a branch that keeps chapters where the chosen rule
   fires (e.g. `sum(scores.values()) > 0`), then build context and answer
   exactly like filter3's Phase 2.
2. **Makefile**: add `filter5d` (full: tsv + Phase 2 jsonl + judge) and a
   `judge-filter5d.jsonl` rule, mirroring `filter2`/`filter3`.
3. **`filter.py`**: add a 5d analysis path (per-axis breakdown + floor + sum
   threshold sweep). It currently reads only 3-column verdict TSVs via
   `read_verdict_tsv`; route 5d through `read_verdict_5d_tsv`.
4. **`report.py`**: `discover_methods` ([report.py:262](report.py)) hardcodes
   the Filter rows as `[("filter2","Filter2"), ("filter3","Filter3")]` — add
   `("filter5d","Filter5d")` (after Filter3) so the judged 5d row appears in
   `make report`.

### Key empirical reference (informs interpretation)

Data comparison on the existing single-axis runs (86 gold pairs, crosstab of
filter3 × filter10 on the 1,850 common pairs):

- **Floors**: filter10 score-0 = **7/86**; filter3 `no` = **12/86**. The
  numeric floor is *lower* — the model expresses faint relevance as score 1–2
  instead of collapsing to `no`. This is why per-axis **numeric** (not
  categorical yes/maybe/no) was chosen: at the aggregate level numeric already
  beats categorical on the metric that matters here (the floor).
- **Rescue labels**: filter3 `maybe` rescues 32/86; filter10 score {1,2}
  rescues 12/86. `maybe` rescues more in isolation, BUT filter10's strict
  baseline (≥3) already absorbed 24/32 of the `maybe`-band at scores 3–8 — so
  the numeric scale doesn't rely on low scores to match filter3's rescue.
- See [filter.md](filter.md) for the full filter10/100 score-distribution,
  threshold-sweep, and crosstab analysis.

The 5d run is a distinct vector from both filter10/100 (judgement
*decomposition* across axes, not scale granularity) and the BM25 hybrid below
(retrieval *mechanism*, not LLM judgement). If the gold-sum-0 floor drops
toward zero, the residual retrieval misses become the pure BM25 case below.

## BM25 hybrid retrieval (complements `sweep_rag.py`)

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
