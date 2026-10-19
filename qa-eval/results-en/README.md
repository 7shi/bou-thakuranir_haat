# Retrieval-strategy case study: Vector depth and per-chapter reading

A per-question analysis of the retrieval strategies on the English question
set, complementing the aggregate table from
[`report.py`](../README.md#reportpy). The original thread follows what changes
when Vector's retrieval depth is bumped from `k=5` to `k=10` — motivated by
[`sweep_vector.py`](../README.md#sweep_vectorpy), which found `k=5` tight for
cross-reference questions and predicted that `k≈10–15` would surface most
dropped gold chapters. **Per-Chapter Extract** — an independent thorough-reading
path — is kept as the convergent-validity baseline: where it agrees with the
gold, two independent readers confirm the answer. **Hybrid** (dense ∪ BM25
union, [§ Hybrid](#hybrid-dense--bm25-union)) adds the Phase 2 answer
measurement for the retrieval analysis in [HYBRID.md](../HYBRID.md): does the
+4 strict-recall gain from unioning both retrievers translate to answer
accuracy? **V-hybrid** (segment ∪ line dense union,
[§ V-hybrid](#v-hybrid-segment--line-dense-union)) is the same union idea applied
to two *dense* granularities instead of dense+BM25 — the Phase 2 QA for
[VECTOR-HYBRID.md](../VECTOR-HYBRID.md). **Filter**, the fifth strategy, is
summarized at
([§ Filter](#filter-llm-as-retriever)) and analyzed in full in
[FILTER.md](../FILTER.md): a looser variant of Extract that reads the full text
of every chapter not marked `no`. **Ceiling** closes the study
([§ Ceiling](#ceiling-the-perfect-retrieval-upper-bound)): the gold chapters
fed verbatim as context, stripping out retrieval entirely to expose the
synthesis-only upper bound.

Run: answers `google:gemma-4-31b-it`, judge Jev (`jev-1.14.0`, verdicts in
`jev/`, each question counted as its most probable verdict), 50 questions
(`questions-en.jsonl`, 25 single-passage + 25 cross-reference). Vector k=5 →
`vector5.jsonl`; Vector k=10 → `vector10.jsonl`; Vector-line k=5/k=10 →
`vector-line5.jsonl` / `vector-line10.jsonl`; V-hybrid k=5/k=10 →
`vector-hybrid5.jsonl` / `vector-hybrid10.jsonl`; Hybrid k=5 → `hybrid5.jsonl`;
Hybrid k=10 → `hybrid10.jsonl`; Filter2 → `filter2.jsonl`; Filter3 →
`filter3.jsonl`; Ceiling → `ceiling.jsonl`. Jev returns probabilities, not
reasons; where a verdict below is called a near tie, its two top
probabilities are within about 0.1 of each other.

## Headline (`report.py --jev`)

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
------------------------------------------------------------------------------------
all      Vector k=5        50      28      17         5     0.730     0.720    0.337
all      Vector k=10       50      36      12         2     0.840     0.840    0.205
all      Vector-line k=5   50      30      14         6     0.740     0.660    0.401
all      Vector-line k=10  50      33      15         2     0.810     0.780    0.274
all      V-hybrid k=5      50      34      14         2     0.820     0.760    0.297
all      V-hybrid k=10     50      36      13         1     0.850     0.900    0.182
all      Hybrid k=5        50      35      14         1     0.840     0.800    0.251
all      Hybrid k=8        50      39       9         2     0.870     0.900    0.179
all      Hybrid k=10       50      39      11         0     0.890     0.920    0.154
all      Extract           50      35      11         4     0.810     0.740    0.843
all      Filter2           50      34      10         6     0.780     0.600    0.808
all      Filter3           50      41       7         2     0.890     0.880    0.775
all      Ceiling           50      46       4         0     0.960     1.000    1.000
all      GraphRAG local    50      19      19        12     0.570     0.860    0.135
all      GraphRAG global   50       1      11        38     0.130     0.220    0.029

single   Vector k=5        25      24       0         1     0.960     1.000    0.263
single   Vector k=10       25      24       1         0     0.980     1.000    0.136
single   Vector-line k=5   25      25       0         0     1.000     1.000    0.392
single   Vector-line k=10  25      24       1         0     0.980     1.000    0.244
single   V-hybrid k=5      25      25       0         0     1.000     1.000    0.226
single   V-hybrid k=10     25      25       0         0     1.000     1.000    0.119
single   Hybrid k=5        25      24       0         1     0.960     1.000    0.178
single   Hybrid k=8        25      24       0         1     0.960     1.000    0.117
single   Hybrid k=10       25      25       0         0     1.000     1.000    0.097
single   Extract           25      25       0         0     1.000     1.000    1.000
single   Filter2           25      25       0         0     1.000     1.000    1.000
single   Filter3           25      25       0         0     1.000     1.000    0.940
single   Ceiling           25      25       0         0     1.000     1.000    1.000
single   GraphRAG local    25      15       1         9     0.620     0.880    0.201
single   GraphRAG global   25       1       1        23     0.060     0.080    0.005

cross    Vector k=5        25       4      17         4     0.500     0.440    0.411
cross    Vector k=10       25      12      11         2     0.700     0.680    0.274
cross    Vector-line k=5   25       5      14         6     0.480     0.320    0.409
cross    Vector-line k=10  25       9      14         2     0.640     0.560    0.305
cross    V-hybrid k=5      25       9      14         2     0.640     0.520    0.369
cross    V-hybrid k=10     25      11      13         1     0.700     0.800    0.245
cross    Hybrid k=5        25      11      14         0     0.720     0.600    0.325
cross    Hybrid k=8        25      15       9         1     0.780     0.800    0.242
cross    Hybrid k=10       25      14      11         0     0.780     0.840    0.211
cross    Extract           25      10      11         4     0.620     0.480    0.686
cross    Filter2           25       9      10         6     0.560     0.200    0.617
cross    Filter3           25      16       7         2     0.780     0.760    0.611
cross    Ceiling           25      21       4         0     0.920     1.000    1.000
cross    GraphRAG local    25       4      18         3     0.520     0.840    0.069
cross    GraphRAG global   25       0      10        15     0.200     0.360    0.053
```

The sweep's prediction holds: deepening retrieval lifts the cross-reference
score from 0.500 to 0.700 (correct 4→12, incorrect 4→2), while single-passage
stays near saturation (0.960→0.980). Chapter recall rises (cross 0.44→0.68) at
the cost of precision (0.41→0.27) — more context, looser filtering — yet
**accuracy rises**, so the extra context helps more than it distracts. Vector
k=10 overtakes Extract on accuracy (0.84 vs 0.81) while Extract still leads
sharply on chapter precision (0.84).

**Hybrid** (dense ∪ BM25 union) is the top retrieval method together with
Filter3: Hybrid k=10 at 0.890 ties Filter3 (0.890) and is the only method other
than Ceiling with no incorrect answer. Against Vector k=10 it fully recovers two
of the three lexically-distinctive cross-reference chapters that dense-only
search cannot rank (Q43, Q49 — the Class A cases from
[§ Both wrong](#both-wrong-what-k10-cannot-fix)) and partially recovers the
third (Q31 — Ch21 enters the union context but Ch22 still does not, so the
answer lands `partial`). The cross-reference score rises from 0.700 to 0.780
(incorrect 2→0). Hybrid k=8 (0.870) recovers Q43 and Q49 as well and matches
k=10 on cross-reference (0.780); it trails only on single-passage. Single-passage
saturates to 1.00 only at k=10: k=5 and k=8 both land at 24/25, answering Q17
"the entire night" for the gold "Five days".

The **Filter** rows use the LLM as retriever rather than dense embeddings:
Filter3 posts 0.890, Filter2 0.780. The `maybe`-verdict mechanism and the
cost/gold-floor analysis are in [FILTER.md](../FILTER.md).

## Extract vs Vector k=10: where each method loses

The Headline's 0.03 margin is the net of two larger counts, so
[`report.py`](../README.md#reportpy)
breaks it open into its per-question causes — and most of it lands on Extract's
two-stage filter. The disagreement pass prints three pairwise matrices (Vector k=5×Vector k=10,
Vector k=5×Extract, Vector k=10×Extract); the decisive one is the last:

```
Agreement matrix (rows = Vector k=10, cols = Extract):
                  Extract:correct  Extract:partial  Extract:incorrect | Vector k=10 total
Vector k=10:correct                29               5                  2  | 36
Vector k=10:partial                 5               5                  2  | 12
Vector k=10:incorrect               1               1                  0  |  2
Extract total                      35              11                  4  | 50
```

For each off-diagonal question the disagreement pass asks whether the loser
actually held every gold chapter in context, then classes the loss:

- **missed context** — a gold chapter is absent from the loser's `expanded`. For
  Extract that is a **Phase 1 false negative** (a wrong `None` dropped it
  unrecoverably); for Vector a **retrieval miss** (the chapter ranked outside top-k).
- **synthesis** — the loser held every gold chapter yet still mis-synthesized.

The split:

| direction | n | missed context | synthesis |
| --- | --- | --- | --- |
| Vector k=10 beats Extract | 9 | **7** (Phase 1 FN) | 2 |
| Extract beats Vector k=10 | 7 | 4 (retrieval miss) | 3 |

**Seven of Extract's nine losses are Phase 1 false negatives** (Q26, Q28, Q34,
Q37, Q39, Q40, Q42) — the gold chapter a stage-1 `None` dropped, so stage 2
never saw it. The filter, not the synthesis, is where Extract loses. Three are
total wipeouts: Q42 (`expanded` empty — all of Ch22/23/29 dropped), Q34 (only
Ch2 kept, all of Ch30/31/33 dropped), and Q26 (used Ch15/30, disjoint from gold
Ch11/29). The remaining two losses (Q33, Q35) are synthesis slips where Extract
held every gold chapter.

**Extract's wins are mostly retrieval misses Vector cannot fix.** Q31, Q43,
Q49 are the [Class A](#both-wrong-what-k10-cannot-fix) chapters dense embedding
ranks outside the top-10 at both depths — Extract's per-chapter reading finds
them, Vector k=10 never does. The fourth, Q38, is counted as missed context
because Vector k=10 lacks Ch32, but Extract lacks it too; both answer from
Ch26/28, and only Vector k=10 leaves out what the letter actually said. The
three synthesis wins (Q17, Q27, Q36) are questions where Vector k=10 holds
every gold chapter and lands `partial`; Q17 is a near tie on "It took five days
to prepare the medicine" (see [§ The two regressions](#the-two-regressions-q17-and-q38)).

So the two architectures fail mostly on **orthogonal axes**, and that is the
read on the 0.84 vs 0.81 margin: Extract's losses are self-inflicted by its own
Phase 1 filter (cheaply fixable — keep more context, weaken the `None` bar, or
quote verbatim instead of summarize-or-discard), whereas Vector's are mostly
structural dense-retrieval blindness (the BM25/lexical hybrid in
[HYBRID.md](../HYBRID.md)). The lever for Extract is in its own stage 1 — Filter3
is that lever ([§ Filter](#filter-llm-as-retriever)) — and the lever for Vector
is hybrid retrieval.

## k=5 baseline, in brief

(This condenses the earlier Vector-vs-Extract disagreement study; the per-question
detail is redeployed in the k=10 analysis below.) Vector k=5 (0.730) and Extract
(0.810) both near-saturate single-passage (24/25 and 25/25 correct) and split
on cross-reference, where they get only 4/25 and 10/25 correct.

**Agreement matrix (k=5 Vector × Extract)** — reproduced verbatim by the
`Vector k=5 × Extract` block of `report.py`'s disagreement pass:

| | Ext correct | Ext partial | Ext incorrect | Vector total |
| --- | --- | --- | --- | --- |
| **Vector correct** | 26 | 2 | 0 | 28 |
| **Vector partial** | 6 | 8 | 3 | 17 |
| **Vector incorrect** | 3 | 1 | 1 | 5 |

Two failure modes account for almost every off-diagonal loss:

- **Vector k=5's losses are mostly top-5 retrieval misses** — 8 of its 10 losses
  to Extract lack a gold chapter that ranks just outside `k=5` (the +0.00–0.07
  gaps `sweep_vector.py` flagged). The two exceptions (Q21, Q29) are
  *answering* slips where the gold chapter was already in context.
- **Extract's losses are Phase 1 false negatives** — a wrong `None` on a gold
  chapter drops it unrecoverably (Q26, Q34, Q42 dropped gold chapters entirely,
  Q39 dropped Ch10). Its one synthesis loss is Q33.

**The gold is sound.** On Q29 (the covert poisoning behind the surface exile
decree), both Extract and Vector k=10 independently reconstruct the covert chain
the gold describes — two thorough paths agreeing with the gold is convergent
evidence it is correct, and Vector k=5's loss there is an answering failure, not a
gold problem.

## What changes at k=10

Twenty-four questions are not-correct in at least one of k=5 / k=10, all but
two of them cross-reference. Twelve of them move between the depths (`k=10
retrieval` = gold chapters newly pulled into context vs. k=5):

| Q | type | gold | k=5 | k=10 | k=10 retrieval | class |
| --- | --- | --- | --- | --- | --- | --- |
| 21 | single | 5 | incorrect | **correct** | — (Ch5 already in k=5) | answering fix |
| 26 | cross | 11,29 | partial | **correct** | — (both already in k=5) | answering fix |
| 28 | cross | 9,37 | incorrect | **correct** | +Ch9, +Ch37 | retrieval fix |
| 29 | cross | 16,17 | incorrect | **correct** | — (both already in k=5) | answering fix |
| 35 | cross | 8,19 | partial | **correct** | — (both already in k=5) | answering fix |
| 37 | cross | 1,34 | partial | **correct** | — (both already in k=5) | answering fix |
| 40 | cross | 13,27 | partial | **correct** | — (both already in k=5) | answering fix |
| 41 | cross | 5,20 | partial | **correct** | +Ch5 | retrieval fix |
| 45 | cross | 18,25 | partial | **correct** | +Ch18 | retrieval fix |
| 48 | cross | 11,19 | partial | **correct** | — (Ch11 out at both) | answering fix |
| 17 | single | 17 | correct | **partial** | — | **regression** |
| 38 | cross | 26,28,32 | correct | **partial** | — (Ch32 out at both) | **regression** |

The other twelve stay not-correct at both depths
([§ Both wrong](#both-wrong-what-k10-cannot-fix)).

### The ten fixes

Two flavors, matching the k=5 failure-mode split:

- **Retrieval fixes (Q28, Q41, Q45).** A gold chapter that ranked just outside
  k=5 enters the top-10 — exactly the "gap +0.00–0.07" cases `sweep_vector.py`
  predicted: Ch9+Ch37 (Q28), Ch5 (Q41), Ch18 (Q45). Three more chapters the
  sweep predicted also enter at k=10 — Ch33 (Q27), Ch17 (Q36), Ch29 (Q42) — but
  those answers stay `partial`.
- **Answering fixes (Q21, Q26, Q29, Q35, Q37, Q40, Q48).** The gold chapters
  were *already* in k=5's context (or, for Q48, Ch11 is missing at both depths);
  k=10's broader supporting context let the answerer complete the answer. Q21
  (Ch5 present at both depths — k=5 cited the wrong incident, k=10 named both
  offenses); Q29 (Ch16+17 present at both — k=5 stopped at the surface exile
  decree, k=10 gave the covert poisoning); Q48 (k=10 adds the court half of the
  answer from Ch19, see [§ Q48](#q48-the-two-part-question)). The other four
  are multi-part answers that k=5 left incomplete. `sweep_vector.py` could not
  have explained any of these by retrieval alone.

### The two regressions: Q17 and Q38

Both are the judge's boundary rather than a change in what the answer knows.

- **Q17** (single, gold "Five days"): k=5 answers "Five days" and is `correct`;
  k=10 answers "It took five days to prepare the medicine" and lands `partial`
  on a near tie (0.45 correct, 0.48 partial).
- **Q38** (gold 26,28,32): neither depth holds Ch32, and both describe
  Nayanchand handing the letter to the Mahishi and Basanta Ray advising her to
  announce that Ramchandra wants Vibha sent to Chandradwip. k=5 also says what
  the letter actually said (that Ramchandra had renounced Vibha); k=10 leaves
  that out and lands `partial` on a near tie (0.47 / 0.52).

The net trade is overwhelmingly positive — ten fixes for two regressions.

## Both wrong: what k=10 cannot fix

Twelve questions stay not-correct at both depths, all cross-reference. Six of
them (Q27, Q30, Q36, Q46, Q47, Q50) already hold every gold chapter at k=10 and
are `partial` on completeness, not retrieval; Ceiling gets four of them correct,
and Q46 and Q47 are `partial` even for Ceiling. The other six lack a gold chapter
at k=10. The decisive cross-check is what **Extract** and **Filter3**, reading
every chapter independently, make of them:

| Q | gold | load-bearing chapter vector search misses | Vector k=5 | Vector k=10 | Hybrid k=8 | Hybrid k=10 | Extract | Filter3 | Ceiling |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | 21,22,23 | Ch21,22 — the ring gift and the seal-forgery | incorrect | incorrect | partial | partial | partial | **correct** | **correct** |
| 43 | 11,37 | Ch37 — the Chandradwip palanquin extraction | partial | partial | **correct** | **correct** | **correct** | **correct** | **correct** |
| 49 | 2,22 | Ch22 — the forged petition to the Emperor of Delhi | incorrect | incorrect | **correct** | **correct** | **correct** | **correct** | **correct** |
| 32 | 11,15,16 | Ch15 — the secret stipend to the dismissed guards | partial | partial | partial | partial | partial | partial | **correct** |
| 34 | 30,31,33 | Ch31 — Rukmini's accusation in Pratapaditya's court | partial | partial | **correct** | **correct** | incorrect | incorrect | partial |
| 42 | 22,23,29 | Ch23 | partial | partial | partial | partial | incorrect | incorrect | **correct** |

This splits the residual frontier cleanly into two classes.

### Class A — vector-unreachable chapters that thorough reading finds (Q31, Q43, Q49)

In three questions the answer turns on a single chapter that dense embedding
ranks outside the top-10 at *both* depths, so no k≤10 surfaces it; the answerer
honestly abstains (Q31, Q49) or gives half the answer (Q43). But **the
per-chapter readers find them**: Filter3 gets all three correct —
reconstructing the ring→seal→forged-petition chain (Q31, Ch21–22), the
Chandradwip palanquin rescue (Q43, Ch37), and the Delhi-petition forgery (Q49,
Ch22) — and Extract gets Q43 and Q49 correct and Q31 `partial`, holding Ch21–22
but saying Rukmini obtained the ring "by manipulating his guilt and grief"
rather than that Udayaditya gave it to her.

That convergent result is decisive: these are not gold problems (independent
thorough readers confirm the gold) and not a depth problem (deeper k still
misses them). It is a **dense-retrieval problem** — the failing chapters are
lexically distinctive ("signet ring", "Emperor of Delhi", "palanquin") but
semantically generic, so cosine cannot separate them from topically-similar
neighbours. This is exactly the failure `sweep_vector.py`'s threshold table
predicted (best τ*≈0.50, F1 0.38) and the motivation for the **BM25/lexical
hybrid** in [HYBRID.md](../HYBRID.md): a lexical signal would match those
proper-noun/term-heavy queries where dense embedding is blind. Ch22 is the
standout — load-bearing for *two* of these questions (Q31 and Q49) and
resistant to retrieval in both.

**Hybrid k=8 and k=10 fully recover two of the three.** The BM25 component
ranks Ch37 (Q43) and Ch22 (Q49) high enough to enter the union top-k,
confirming that failure was lexical invisibility, not gold ambiguity. Q31 only
partially recovers: Ch21 enters the union context but **Ch22 — the chapter
where the petition is actually forged — does not**, at either k=8 or k=10 (see
[HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots), which lists
Ch22 as unrecoverable for Q31 at `k≤10`). With Ch21 alone, the answerer can
describe the ring changing hands but not the petition's specific content, which
the (corrected) gold answer now grades on — hence `partial`, not `correct`. See
[§ Hybrid](#hybrid-dense--bm25-union) for the per-question breakdown.

### Class B — the failures shared with the per-chapter readers (Q32, Q34, Q42)

The remaining three questions are not-correct for Vector, Extract and Filter3
alike, so deeper Vector retrieval cannot be the lever:

- **Q32** (gold 11,15,16) — the gold's load-bearing middle step is the *secret
  monthly stipend* Udayaditya and Surma pay the dismissed guards, which
  Pratapaditya discovers. Ch15 never ranks in the top-10 for either Vector depth,
  and Extract's per-chapter extraction misses the stipend too, attributing the
  exile to vague "psychological tactics." Every retrieval method lands on
  partial. The causal detail is genuinely subtle and lives in a chapter none of
  the methods weighs heavily.
- **Q34** (gold 30,31,33) — the link is Ch31, where Rukmini tells Pratapaditya's
  court that Basanta Ray helped the escape. Both Vector depths hold Ch30 and
  Ch33 but not Ch31, and fill the gap with another cause (Rukmini alerting
  soldiers in Raigarh at k=5, a pre-existing order at k=10), landing partial;
  Extract's and Filter3's Phase 1 drop all three gold chapters and answer
  incorrectly.
- **Q42** (gold 22,23,29) — Ch23 stays out of every Vector and Hybrid context.
  The answers describe the rescue under cover of the fire and the staged death;
  all but Vector k=10 leave out the forged petition, the damage being undone,
  and all land partial. Extract and Filter3 drop all three gold chapters.

Q32 is the true residual: no `k` or hybrid fixes it, and Ceiling
([§ below](#ceiling-the-perfect-retrieval-upper-bound)), which feeds Ch15
verbatim, gets it correct. Q42 behaves the same way: only Ceiling, holding
Ch23, is correct. Q34 is not — BM25 ranks Ch31 into the union, and Hybrid k=8
and k=10 answer it correctly, while Ceiling, with all three chapters in
context, lands `partial`: it has Rukmini go to Raigarh with Pratapaditya's men
and find Udayaditya there, instead of revealing Basanta Ray's part in the
escape.

## Hybrid (dense ∪ BM25 union)

The union approach from [HYBRID.md](../HYBRID.md) converts the strict-recall
retrieval gain into answer accuracy. At k=10, it ties Filter3 for the top
retrieval accuracy of **0.890** (with k=8 at **0.870**), mostly recovering the
Class A chapters that dense-only search cannot reach — fully for Q43/Q49,
partially for Q31 (Ch22 stays out of reach).

### Hybrid k=5 vs Vector k=10

Hybrid k=5 (0.840) ties Vector k=10 (0.840) overall, and the two methods win on
**orthogonal questions**:

| direction | n | questions | class |
| --- | --- | --- | --- |
| Hybrid k=5 beats Vector k=10 | 5 | Q30 (synthesis), Q31 (Ch21, Class A), Q38 (neither holds Ch32), Q47 (synthesis), Q49 (Ch22, Class A) | 3 missed-context, 2 synthesis |
| Vector k=10 beats Hybrid k=5 | 6 | Q17 (synthesis), Q26 (synthesis), Q28 (Ch9), Q37 (synthesis), Q40 (synthesis), Q48 (neither holds Ch11) | 2 missed-context, 4 synthesis |

Two of the five Hybrid k=5 wins are retrieval fixes — BM25's lexical signal
surfaces chapters that dense embedding ranks outside the top-10. Q31 and Q49 are
Class A: Ch21 (the ring gift; Ch22 stays out) and Ch22 (forged Delhi
petition), both lexically distinctive but semantically generic. The other three
are completeness: Q38 is the near tie of
[§ The two regressions](#the-two-regressions-q17-and-q38), and on Q30 and Q47
Vector k=10 holds every gold chapter and lands `partial`. Vector k=10's wins are
mostly synthesis, one of them the single-passage Q17, where Hybrid k=5 answers
"the entire night"; the rest are Q28, where dense k=10 reaches Ch9 but the k=5
union does not, and Q48, where neither holds Ch11 and only Vector k=10 supplies
the court half from Ch19. On cross-reference, Hybrid k=5 (0.720) edges Vector
k=10 (0.700).

### Hybrid k=10 recovers most of the Class A frontier

At k=10 the union closes most of the Class A gap. Hybrid k=10 beats Vector k=10
on six questions, five of them counted as missed context:

| Q | gold | dropped by Vector k=10 | why BM25 recovers it |
| --- | --- | --- | --- |
| Q31 | 21,22,23 | Ch21, Ch22 | only Ch21 recovers; Ch22 stays outside top-10 at any k≤10 for this question (see [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)) — partial credit only |
| Q34 | 30,31,33 | Ch31 | Ch31 enters the BM25 top-k |
| Q38 | 26,28,32 | Ch32 | it does not: Hybrid k=10 lacks Ch32 too, and the win is completeness |
| Q43 | 11,37 | Ch37 | "Chandradwip palanquin" — proper-noun-heavy |
| Q49 | 2,22 | Ch22 | "Emperor of Delhi", "forged petition" |

The sixth is Q17 (the near tie on "five days"). Vector k=10 beats Hybrid k=10
on two questions, Q26 and Q37, both synthesis with every gold chapter in both
contexts: the ~1.4× larger union context that HYBRID.md warned could confuse
synthesis costs two questions here.

### Hybrid k=8: Performance and Trade-offs

Expanding the retrieval depth to `k=8` yields **39/50 (0.870)**, sitting between `k=5` (**0.840**) and `k=10` (**0.890**).

- **Gains over k=5:** Deepening the search to `k=8` recovers the missing gold chapters for **Q27** (Ch33), **Q28** (Ch9) and **Q43** (Ch37), and answers **Q34** and **Q40** fully from the same chapters, upgrading all five to correct. It loses **Q29** (a synthesis regression, correct at `k=5` to incorrect), netting +4 correct answers.
- **Comparison to k=10:** `k=8` and `k=10` both get 39 correct and tie on cross-reference (0.780); they trade three questions each, all with the same gold chapters in context. `k=10` fixes the two `k=8` incorrect answers (**Q17**, "the entire night", and **Q29**) and completes **Q48**; `k=8` is graded correct on **Q27**, **Q30** and **Q47**, where `k=10` lands `partial`. The difference in score is therefore `k=8`'s two incorrect answers. Japanese peaks at `k=10` (`0.860`) too, but there `k=8` (`0.810`) falls below `k=5` (`0.850`), whereas English improves at every step.

### The residual to Ceiling

Ceiling beats Hybrid k=10 on nine questions, three of them missed context —
the shared blind spots no retrieval blend fixes:

- **Q31** — Ch22 (where the petition is actually forged) is
  outside both retrievers' top-k at k=10; Ch21 alone lets Hybrid k=10 describe
  the ring changing hands but not the petition's content, landing `partial`.
- **Q32** — Ch15 (the secret stipend detail) is outside both
  retrievers' top-k at k=10 and remains a Class B unreachable.
- **Q42** — Ch23 is outside the union too.

The other six (Q26, Q27, Q30, Q36, Q37, Q50) are synthesis: Hybrid k=10 holds
every gold chapter, inside a union context several times the size of Ceiling's,
and leaves part of a multi-part answer out. Hybrid k=10 in turn beats Ceiling on
Q34 (above) and Q48 ([§ Q48](#q48-the-two-part-question)).

## Vector-line (line-level retrieval)

`Vector-line` keeps the dense pipeline but shrinks the retrieval unit from a
scene to a **single line**: [`build_index.py --line`](../README.md#build_indexpy)
embeds one vector per non-blank line, and
[`answer_vector.py --line`](../README.md#answer_vectorpy) ranks lines, then
resolves each hit line back to its containing segment before the same ±N
expansion and answering. The question is whether a finer unit — matching the one
sentence that answers the question, rather than diluting it across a whole scene
— retrieves better.

It does not, on balance. The headline is **0.740 (k=5) / 0.810 (k=10)**: level
with segment Vector's 0.730 at k=5 and below its 0.840 at k=10. The line unit
does what finer granularity should — it lifts **chapter precision** (k=5
0.337→0.401, k=10 0.205→0.274, the highest of any dense method) and
**saturates single-passage to 1.000 at k=5**, beating segment k=5's 0.960. But
it lowers **chapter recall** (k=5 0.720→0.660, k=10 0.840→0.780), and the
cross-reference score falls with it: 0.480 (k=5) and 0.640 (k=10), against
segment Vector's 0.500 and 0.700.

### Why cross-reference suffers

Every loss of Vector-line k=5 to segment Vector k=5 is a **missed-context**
retrieval miss:

| direction | n | missed-context | synthesis |
| --- | --- | --- | --- |
| Vector k=5 beats Vector-line k=5 | 6 | 6 | 0 |
| Vector-line k=5 beats Vector k=5 | 6 | 4 | 2 |
| Vector k=10 beats Vector-line k=10 | 7 | 3 | 4 |
| Vector-line k=10 beats Vector k=10 | 4 | 3 | 1 |

The mechanism is the flip side of the precision gain. When a gold chapter's
relevance is carried by **one distinctive line**, the line unit surfaces it
cleanly; but when the relevant content is **diffuse across a scene**, no single
line accumulates enough similarity to crack the top-k, whereas the scene-level
average still ranks. Cross-reference questions lean on the diffuse case, so they
lose the most (e.g. Q26 Ch11/29 and Q40 Ch13/27, both dropped by
Vector-line k=5 but held by segment k=5, and both `incorrect` there).

### The misses are orthogonal

Crucially, Vector-line is not strictly worse retrieval — it has its **own** wins
that segment search drops. At k=10 it recovers **Q34 (Ch31)** and **Q38
(Ch32)**, chapters segment search misses at both depths, here surfaced because
one lexically sharp line ranks where the averaged scene did not, and it lifts
the [Class A](#both-wrong-what-k10-cannot-fix) Q49 from incorrect to partial even
without Ch22. At k=5 it likewise lifts Q49 to partial, fixes Q21/Q29 by
synthesis and Q45 by retrieval, lifts Q28 from incorrect to partial by
retrieving both of its chapters, and completes Q48 without Ch11. So line and
segment granularity fail on **orthogonal chapters** — the same dense-vs-lexical
tension [Hybrid](#hybrid-dense--bm25-union) exploits, in miniature. At k=5 the
wins and losses balance (6–6); at k=10 the line unit loses more than it
recovers (4–7), so segment-level retrieval stays the stronger dense baseline.

### Depth still helps

Like segment Vector, deepening k=5→k=10 is mostly a retrieval gain:
Vector-line k=10 beats k=5 on 7 questions, **5 of them missed-context** (the
other two, Q28 and Q35, already have both gold chapters at k=5 but answer only
partially), against three regressions: Q22 and Q48 by synthesis, and Q36, a
near tie where both depths lack Ch17/21. The k=5 unit is simply too tight for
cross-reference — the same lesson [`sweep_vector.py`](../README.md#sweep_vectorpy)
drew for the segment index, only sharper here because the line unit retrieves
less per hit.

## V-hybrid (segment ∪ line dense union)

`V-hybrid` (`answer_vector.py --hybrid`) unions the two *dense* retrievers —
segment top-k ∪ line top-k, resolved to segments — converting the segment∪line
strict-recall gain from [VECTOR-HYBRID.md](../VECTOR-HYBRID.md) (en +2 @ k=5, +3
@ k=10) into answer accuracy. It is the same union idea as
[Hybrid](#hybrid-dense--bm25-union), but with two same-model cosines instead of
dense + BM25, so it needs no score-scale reconciliation and works in both
languages.

It scores **0.820 (k=5) / 0.850 (k=10)** — above plain Vector k=5 (0.730) and
Vector-line (0.740 / 0.810), level with segment Vector k=10 (0.840) at k=10, and
below the dense∪BM25 Hybrid (0.840 / 0.890). The most striking column is
`incorrect`: V-hybrid k=5 has just **2** (vs Vector k=5's 5, Vector-line k=5's
6), with 14 partials. The
union surfaces so many gold chapters that almost nothing is fully missed — chapter
recall on cross-reference reaches **0.800 at k=10** (vs Vector k=10's 0.680) —
but the recovered chapters convert to *partial* more often than *correct*: the
right chapter is present, yet the wider context dilutes synthesis.

### Two ceilings it does not break

The disagreement pass pins why V-hybrid lands level with Vector k=10 and below
Hybrid:

- **vs segment Vector k=10 (wins 4–3).** V-hybrid k=10 beats Vector k=10 on
  four questions: Q49 (lifted to partial although neither holds Ch22), Q17 (the
  near tie on "five days"), and Q27 and Q47 by synthesis. It loses three, Q26,
  Q37 and Q48, all by **synthesis**, where the ~1.4× larger union context leaves
  the answer incomplete with the same chapters. The retrieval gain is real, but
  it barely shows in answer accuracy, as [VECTOR-HYBRID.md](../VECTOR-HYBRID.md)
  warned: synthesis pays for the extra context.
- **vs dense∪BM25 Hybrid k=10 (loses 6–2).** Hybrid wins six questions (three
  missed-context, three synthesis); V-hybrid wins two, Q27 and Q47, by
  synthesis. The three missed-context losses are the
  [Class A](#both-wrong-what-k10-cannot-fix)
  chapters — Q31 Ch21/22, Q43 Ch37, Q49 Ch22 — that dense embedding cannot rank at *any*
  granularity because they are lexically distinctive but semantically generic.
  Unioning two dense granularities cannot reach them; only BM25's lexical signal
  does. **This is the ceiling of dense∪dense union**: it recovers chapters that
  differ by granularity, but not chapters that are dense-blind.

So in English V-hybrid is a clean, parameter-free dense-only retriever with the
lowest incorrect rate of any Vector variant, yet it barely improves on segment
Vector k=10 (synthesis cost) and sits below the lexical Hybrid (dense-blind
Class A chapters). The matched-budget reading makes this sharper: V-hybrid k=5
pools `seg5 ∪ line5`, a ~k=10 segment context, so its real baseline is Vector
k=10 (0.840) — which it trails, losing three questions and winning one. **Japanese confirms the pattern rather than reversing
it:** there V-hybrid k=5 falls below plain Vector k=10 (0.800 vs 0.830) — the
segment∪line union has no BM25-equivalent lever for the dense-blind
chapters, so it buys no accuracy over the simpler single-index retriever (see
[results-ja/README.md](../results-ja/README.md#v-hybrid-segment--line-dense-union)).

## Filter (LLM-as-retriever)

The per-chapter Filter strategy — reading every chapter and keeping those the
LLM does not mark irrelevant, then answering from their full text — is analyzed
in full in [FILTER.md](../FILTER.md). The short version relevant to this case
study: Filter3 (`yes`/`maybe`/`no`, keep all but `no`) answers the three
vector-unreachable Class A questions (Q31, Q43, Q49) correctly, confirming
those are a dense-retrieval problem rather than a gold one. Its two incorrect
answers are confident-wrong-`no` wipeouts (Q34, Q42), and the Class B Q32 is a
third, landing partial; all three are chapters Extract also drops. The `maybe`
verdict is the lever — the strict two-level Filter2 (keep only `yes`) falls to
0.780, below Extract (0.810) — and with it Filter3 ties Hybrid k=10 at 0.890.
The Ceiling comparison below includes both.

## Ceiling: the perfect-retrieval upper bound

Ceiling strips out retrieval entirely: the gold `chapters` are fed verbatim as
context, so chapter recall and precision are both **1.000 by construction** —
the context *is* the gold set. Every Ceiling loss is therefore a pure
**synthesis** loss, and its score (0.960: 46 correct, 4 partial, no incorrect)
is the upper bound every retrieval strategy chases. The question it answers is
not *"which chapters should the answerer see?"* but *"given the right chapters,
how well does the model read and synthesize?"*

### Ceiling's margin over every method

Ceiling's margin over each method is the cost of that method's retrieval plus
the synthesis it loses in its own context:

| method | method score | Ceiling beats it on | missed-context | synthesis | beats Ceiling on |
| --- | --- | --- | --- | --- | --- |
| Vector k=5 | 0.730 | 18 | 11 | 7 | 0 |
| Filter2 | 0.780 | 14 | 14 | 0 | 1 |
| Extract | 0.810 | 13 | 10 | 3 | 1 |
| Hybrid k=5 | 0.840 | 12 | 7 | 5 | 1 |
| Vector k=10 | 0.840 | 11 | 6 | 5 | 1 |
| Hybrid k=8 | 0.870 | 9 | 4 | 5 | 2 |
| Filter3 | 0.890 | 7 | 4 | 3 | 1 |
| Hybrid k=10 | 0.890 | 9 | 3 | 6 | 2 |

The missed-context column falls as retrieval improves (14 or 11 at the bottom,
3 for Hybrid k=10), but the synthesis column does not: the dense and hybrid
methods keep losing five to seven questions to Ceiling with every gold chapter
in context. **The top two methods tie at 0.890 by different routes**: Filter3
loses fewer questions to Ceiling (seven), Hybrid k=10 loses fewer of them to
retrieval (three) and beats Ceiling twice.

Where the last column is non-zero it is always one of three Ceiling partials:
Q47 (Filter2, Hybrid k=5, Hybrid k=8, Filter3), Q48 (Extract, Vector k=10,
Hybrid k=10) and Q34 (Hybrid k=8, Hybrid k=10). Q34 is a real error in Ceiling's
answer (see [§ Class B](#class-b--the-failures-shared-with-the-per-chapter-readers-q32-q34-q42));
Q48 is a real completeness gap against some methods
([§ Q48](#q48-the-two-part-question)); Q47 is a near tie. Ceiling's fourth
partial, Q46, is `partial` for every method.

### The seven-question gap to Filter3

Filter3 is the closest per-chapter method gets to Ceiling. Its seven losses pin
down what classifier-based retrieval still cannot fix:

- **Q32, Q34, Q42 (missed-context)** — the confident-wrong-`no` wipeouts
  (see [FILTER.md](../FILTER.md#failure-mode)).
  Every gold chapter was marked `no`, so Phase 2 saw nothing. These are the
  same questions Extract drops too (two different classifiers, each reading
  the full chapter, independently decide they are irrelevant), and Ceiling
  gets Q32 and Q42 correct and Q34 partial — confirming the gold chapters *do*
  contain the answer. No threshold trick fixes them: the model never hesitated
  (`no`, not `maybe`), so the `maybe` rescue cannot reach.
- **Q50 (missed-context)** — Ch23 was marked `no`, and with it Rammohan
  pointing to Vibha's unkempt hair; the answer stops at the unbraided hair.
- **Q29, Q36, Q37 (synthesis)** — Filter3 held every gold chapter and left part
  of the answer out.

Filter3 in turn beats Ceiling on Q47. Both describe the fire, the burnt cell and
the bones, skull and sword without the melted sword being brought before
Pratapaditya, and both verdicts are near ties (Filter3 0.51 correct, Ceiling
0.52 partial), so that question is the judge's boundary, not a difference in
reading. None of Filter3's losses is a dense-retrieval blindness case —
Filter3's per-chapter reading already solved Q31, Q43, Q49.

### Q48: the two-part question

Q48 (gold 11,19) is the one Ceiling partial that separates the methods cleanly.
The gold has two halves: Ramchandra's
private reading of the midnight rescue (he owes nothing for it; Udayaditya acted
for his sister's sake) and what he does with it in his own court, where he joins
the minister and Ramai Bhand in mocking Udayaditya for being Pratapaditya's son.
Both are in Chapter 19:

> He was not grateful that Udayaditya had saved his life. He felt that it was
> bound to happen... he believed Udayaditya had saved him for the sake of his
> own sister; saving his life had not been Udayaditya's main objective.

The court half is not optional: the question itself asks how Ramchandra reads
the rescue *in his own court*, so an answer that stops at the private
rationalizations has not reached the scene the question names.

Both halves sit in the same chapter, so every method that retrieves Ch19 holds
the same evidence Ceiling does, and the split is answer completeness, not a
difference in context. Jev draws the line where the question does. Vector k=10,
Vector-line k=5 and Hybrid k=10 supply the court half and are `correct` with
0.82–0.86; Ceiling, Vector k=5 and Filter3 stop at the private
rationalizations and are `partial`. The one exception is Extract, which also
stops there and is `correct` on a near tie (0.51 / 0.49). So Ceiling's deficit
on Q48 is real against three methods and judge-boundary noise against one.

### What Ceiling confirms

- **The single-passage axis is solved.** Single-passage saturates to 1.000
  under Ceiling, Filter3, Extract and Hybrid k=10 (and Vector-line k=5,
  V-hybrid, Filter2), and every method except GraphRAG reaches at least 24/25.
  The few single-passage losses (Q17, Q21, Q22) are synthesis slips with the
  gold chapter in context. The entire frontier is cross-reference.
- **The gap between methods is retrieval at the bottom and synthesis at the
  top.** Ceiling's margin over Filter2 is entirely missed context, and over
  Vector k=5 and Extract mostly so; over Hybrid k=10 six of nine are synthesis.
  Ceiling's context is identical in shape to Filter3's Phase 2 (full chapter
  text, same prompt, same model); the only difference is *which* chapters —
  Ceiling's are perfect, Filter3's are classifier-selected. So Ceiling's 0.960
  vs Filter3's 0.890 measures what Filter3's four `no` losses cost, plus three
  synthesis slips, less the Q47 near tie.
- **Q32's gold answer is confirmed.** Q32 (the secret stipend to dismissed
  guards) was partial for every method including Filter3, with Extract and
  Filter both dropping Ch15. Ceiling — which feeds Ch15 verbatim — gets it
  correct, confirming the detail *is* in the chapter and the gold is sound;
  the other methods' failures are retrieval/extraction, not gold ambiguity.

## GraphRAG

[Microsoft GraphRAG](https://github.com/microsoft/graphrag) builds a knowledge
graph over the corpus and answers queries through two distinct search modes —
`local` (entity-anchored, traverses the graph from the nearest entity nodes) and
`global` (community-summary based, aggregates across cluster summaries). Both
modes run on `ollama:gemma4:31b-it-qat` with the same corpus; details in
[graphrag-en/README.md](../graphrag-en/README.md).

### GraphRAG local (0.570)

Local search posts 19/50 (0.570) — below Filter2 (0.780) and far below Hybrid
k=10 (0.890). The chapter-retrieval numbers tell the story: **recall 0.860,
precision 0.135** (the lowest of any non-global method). Entity-graph expansion
tends to pull in nearly all 37 chapters as expanded context, so gold chapters
are almost always present — but the answerer is forced to synthesize from an
overloaded context with minimal signal-to-noise.

The failure mode is therefore **synthesis-dominated**. Of GraphRAG local's 27
losses to Ceiling, **20 are synthesis** (the gold chapter is present but the
answer is wrong or vague) and only 7 are missed context. This is the inverse of
Vector k=5 (where most losses are retrieval misses) and is structurally similar
to the "lost in the middle" effect: the right content is there, but buried under
noise. Hybrid k=10 keeps its context to the union top-k and avoids this;
GraphRAG local has no equivalent precision control.

The synthesis collapse is sharpest on **single-passage questions** (15/25,
0.620) — the category every retrieval method with adequate recall saturates to
≥24/25. GraphRAG local drops 9 of those 25 to incorrect (and 1 to partial),
producing the worst single-passage score of any non-global method. On
cross-reference it lands at 4/25 correct (0.520, mostly partials), level with
Vector k=5 (0.500) — the chapter-graph's entity links provide no structural
advantage when the bottleneck is synthesis over a noisy context.

GraphRAG local **beats Hybrid k=10 on three questions** (Q27, Q30, and Q31,
where the union context still lacks Ch22). Hybrid k=10 wins 25 questions against
it (19 synthesis, 6 missed context).

### What GraphRAG local gets right

Despite the poor overall score, examining which questions GraphRAG local
answers correctly reveals a coherent pattern: it succeeds on questions whose
answers are encoded as **entity relationships or narrative arcs**, and fails on
questions requiring **specific microdetail from the raw text**.

**Pure graph traversal (0 chapters retrieved).** Two cross-reference
questions — Q26 and Q28 — are answered with `expanded=[]`: no chapter
text is retrieved at all. Q26 asks how the dynamic between Udayaditya and the
guard Sitaram *reverses* across two escapes; Q28 asks in what two locations and
disguises Ramai Bhand faces retaliation. Both turn on the *shape of a
relationship arc* — exactly what a knowledge graph's entity/relationship edges
encode. Both are partial. Q26 names the role reversal and the fire of the
second escape but omits the first event, Udayaditya tying up Sitaram at
Sitaram's request on the night of Ramchandra's escape. Q28 pairs each incident
with its target and disguise but places the second only in "a room", without
Chandradwip. The graph supplied the arc without any passage context, though
not every event or place.

**Class A recovery (Q31, Q49).** The two Class A questions that segment Vector
misses at both depths — Q31 (signet ring → seal forgery → imprisonment) and
Q49 (Emperor of Delhi → forged petition → imprisonment) — are both reached by
GraphRAG local (with 37 chapters retrieved): Q31 is correct, and Q49 partial,
as it does not say the petition was forged in Udayaditya's name. Dense embedding is lexically
blind to Ch21/22 and Ch22 because those chapters are semantically generic; BM25
recovers them via lexical matching. GraphRAG takes a third path: the
knowledge graph explicitly encodes the entity chain (ring → conspiracy →
imprisonment) as relationship edges, so local graph traversal reaches the answer
independently of chapter ranking. The same mechanism explains why Q26/Q28 can
be answered from zero chapters — entity chains carry the arc.

**The entity-vs-procedural boundary (Q43).** Q43 (Class A, Ch37 — palanquin
extraction) is partial: the graph correctly identifies *who* was rescued by
Rammohan Mal on two occasions, but misses *how* — the bedsheet rope from the
Jessore rooftop and the carried-unconscious-to-palanquin detail in Chandradwip.
Physical procedures are not entity-relationship edges; they live in the raw
text. GraphRAG captures entity actions but not the fine-grained procedural
specifics of those actions.

**The general pattern.** Questions GraphRAG local answers correctly tend to ask
about *character dynamics and their evolution*, *causal chains between named
entities*, or *narrative arc reversals* — all things the knowledge graph
represents explicitly. Questions it fails tend to ask for specific words, objects,
or physical actions at a particular scene — microdetails that entity extraction
abstracts away. This is exactly the mismatch described above: the graph encodes
relationships, not passages.

### GraphRAG global (0.130)

Global search is essentially non-functional for passage-level QA. It scores
1/50 correct (0.130) — the lowest of any method by a wide margin — and the
mechanism is clear from the chapter-retrieval numbers: **recall 0.220,
precision 0.029**. Community summaries operate at the wrong granularity: they
abstract away the specific chapter details the questions turn on. Of the 47
questions where Ceiling beats GraphRAG global, **38 are missed context** — the
relevant textual evidence is simply absent from the retrieved context, not
merely mis-synthesized.

Single-passage (1/25, 0.060) is almost a complete failure: community-level
summaries cannot anchor a question to the specific scene where an event occurs.
Cross-reference (0/25 correct, 0.200) fares slightly better on the weighted
score because a handful of prominent cross-cutting themes appear in the
community summaries, earning 10 partials, but the score is still far below
every other method including Filter2 (0.560).

### Summary

Neither GraphRAG mode reaches the level of the simplest pipeline method (Vector
k=5, 0.730). The local mode's high recall does not translate to accuracy because
synthesis degrades over an overloaded context; the global mode's community
abstractions miss the passage-level details entirely. For a chapter-structured
novel QA task with specific factual questions, the flat embedding pipeline —
especially with the BM25 union — outperforms the knowledge-graph approach at a
fraction of the indexing cost (4 h+ for GraphRAG vs. minutes for the embedding
index).

## Takeaways

- **k=10 delivers the sweep's promise on cross-reference** (0.500→0.700),
  single stays near saturation, and Vector k=10 overtakes Extract on accuracy
  (0.84 vs 0.81). The win is broad — ten questions fixed — at the cost of two
  regressions (Q17, Q38, both near ties on nearly the same answer) and lower
  chapter precision. (The Filter rows — Filter3 at 0.89, Filter2 at 0.78 — are
  analyzed in [FILTER.md](../FILTER.md).)
- **Extract's deficit is its Phase 1 filter, not its synthesis — and Filter3
  confirms the fix.** `report.py`'s disagreement pass shows 7 of Extract's 9
  losses to k=10 are Phase 1 false negatives (a gold chapter dropped by a wrong
  `None`); only 2 are synthesis slips. Filter3 is the lever made real — keeping
  every chapter not marked `no` turns four of those seven (Q26, Q28, Q39, Q40)
  and both synthesis slips (Q33, Q35) correct, and lands at 41 correct / 0.890
  weighted against Extract's 35 / 0.810, even though Q34 and Q42 stay false
  negatives for Filter3 too.
- **Most k=5 losses were not retrieval problems.** Seven of the ten fixes (Q21,
  Q26, Q29, Q35, Q37, Q40, Q48) had the gold chapters in context all along, or
  lacked the same chapter at both depths; k=10's extra context just yielded a
  more complete answer. Retrieval depth is not the only lever — answer
  synthesis improves with context too.
- **The dense-retrieval blindness frontier is closeable without per-chapter cost.**
  Three of the questions both Vector depths miss (Q31, Q43, Q49) are Class A:
  Filter3, reading the full chapter text, gets all three correct, Extract two,
  and **Hybrid k=10** gets Q43 and Q49 correct and Q31 partial. The
  chapter-question link is vector-unreachable at k≤10 but lexically distinctive;
  BM25 surfaces these chapters at k=10 (all but Q31's Ch22), making the union
  approach nearly as effective as per-chapter reading for the Class A frontier
  at a fraction of the cost.
- **Hybrid k=10 (0.890) ties Filter3 as the top retrieval method** and is the
  only method besides Ceiling with no incorrect answer. It wins six questions
  against Vector k=10 and loses two, both synthesis, and leaves three shared
  blind spots (Q31, Ch22; Q32, Ch15; Q42, Ch23). Single-passage saturates to
  1.00 only at k=10 (k=5 and k=8 miss Q17), and on cross-reference Hybrid k=10
  (0.780) trails the cross Ceiling (0.920) by those blind spots and six
  synthesis partials.
- **The `maybe` verdict is what makes the per-chapter filter work**, and its
  residual is a *confident* wrong `no` (Q32, Q34, Q42) that no threshold trick
  reaches. The full mechanism and the cost comparison are in
  [FILTER.md](../FILTER.md).
- **One question is hard for every retrieval method** (Q32): all methods land
  partial (Hybrid k=10 included — Ch15 is outside the union's top-k at k=10).
  Ceiling disambiguates it: with Ch15 fed verbatim the answerer gets it
  *correct*, so the gold is sound and the other methods' failures are
  retrieval/extraction.
- **Ceiling isolates the synthesis ceiling at 0.960.** With retrieval stripped
  out (gold chapters verbatim), the answerer reads 46 of 50 correctly —
  including Q32, which every retrieval method gets partial — and has no
  incorrect answer. Its four partials are all cross-reference: Q34 (a wrong
  causal link with every chapter in context), Q48 (a completeness gap on a
  two-part answer that three methods fill), and Q46 and Q47 (near ties).
  Ceiling's margin over each method
  (18/14/13/12/11/9/7/9 for
  Vector k=5/Filter2/Extract/Hybrid k=5/Vector k=10/Hybrid k=8/Filter3/Hybrid k=10)
  shrinks as retrieval improves, but at the top it is mostly synthesis: Hybrid
  k=10 is within three missed-context questions of Ceiling — the three shared
  blind spots — and loses six more with every gold chapter in context.
- **The gold holds up.** Across every disagreement the failures trace to a
  method or to the judge's boundary — never to the gold — and Ceiling confirms
  the ones the other methods most often miss: Q31/Q43/Q49 (the
  vector-unreachable trio, all correct under Ceiling), Q32 (the secret-stipend
  question, correct under Ceiling despite being partial for every retrieval
  method) and Q42 (correct under Ceiling, which holds Ch23).
- **GraphRAG does not match the pipeline on this task overall, but reveals what
  graph structure can and cannot do.** Local search (0.570) falls below Filter2:
  entity-graph expansion overloads context (recall 0.860, precision 0.135) and
  20 of 27 losses to Ceiling are synthesis failures, not missed context. Yet it
  has a coherent strength — questions about *character relationship arcs and
  narrative causality* (e.g. Q26/Q28, answered with 0 chapters from pure graph
  traversal, both partial; Q31/Q49, the Class A cases that
  dense+BM25 also recovers via lexical matching, here reached via entity
  chains, Q31 correct and Q49 partial). It fails on microdetail questions
  requiring specific text. Global
  search (0.130) is non-functional: community summaries are the wrong
  granularity (38 of 47 losses to Ceiling are missed context). Global never
  beats Hybrid k=10; local beats it on three questions (Q27, Q30, Q31).
