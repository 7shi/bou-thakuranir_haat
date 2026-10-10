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

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 50 questions
(`questions-en.jsonl`, 25 single-passage + 25 cross-reference). Vector k=5 →
`vector5.jsonl`; Vector k=10 → `vector10.jsonl`; Vector-line k=5/k=10 →
`vector-line5.jsonl` / `vector-line10.jsonl`; V-hybrid k=5/k=10 →
`vector-hybrid5.jsonl` / `vector-hybrid10.jsonl`; Hybrid k=5 → `hybrid5.jsonl`;
Hybrid k=10 → `hybrid10.jsonl`; Filter2 → `filter2.jsonl`; Filter3 →
`filter3.jsonl`; Ceiling → `ceiling.jsonl`.

## Headline (`report.py`)

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
------------------------------------------------------------------------------------
all      Vector k=5        50      38       6         6     0.820     0.720    0.337
all      Vector k=10       50      44       4         2     0.920     0.840    0.205
all      Vector-line k=5   50      33      11         6     0.770     0.660    0.401
all      Vector-line k=10  50      38       9         3     0.850     0.780    0.274
all      V-hybrid k=5      50      39       9         2     0.870     0.760    0.297
all      V-hybrid k=10     50      44       5         1     0.930     0.900    0.182
all      Hybrid k=5        50      40       8         2     0.880     0.800    0.251
all      Hybrid k=8        50      44       4         2     0.920     0.900    0.179
all      Hybrid k=10       50      48       2         0     0.980     0.920    0.154
all      Extract           50      40       6         4     0.860     0.740    0.843
all      Filter2           50      37       6         7     0.800     0.600    0.808
all      Filter3           50      45       3         2     0.930     0.880    0.775
all      Ceiling           50      49       1         0     0.990     1.000    1.000
all      GraphRAG local    50      24      13        13     0.610     0.860    0.135
all      GraphRAG global   50       3      11        36     0.170     0.220    0.029

single   Vector k=5        25      24       0         1     0.960     1.000    0.263
single   Vector k=10       25      25       0         0     1.000     1.000    0.136
single   Vector-line k=5   25      25       0         0     1.000     1.000    0.392
single   Vector-line k=10  25      24       0         1     0.960     1.000    0.244
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
single   GraphRAG global   25       2       1        22     0.100     0.080    0.005

cross    Vector k=5        25      14       6         5     0.680     0.440    0.411
cross    Vector k=10       25      19       4         2     0.840     0.680    0.274
cross    Vector-line k=5   25       8      11         6     0.540     0.320    0.409
cross    Vector-line k=10  25      14       9         2     0.740     0.560    0.305
cross    V-hybrid k=5      25      14       9         2     0.740     0.520    0.369
cross    V-hybrid k=10     25      19       5         1     0.860     0.800    0.245
cross    Hybrid k=5        25      16       8         1     0.800     0.600    0.325
cross    Hybrid k=8        25      20       4         1     0.880     0.800    0.242
cross    Hybrid k=10       25      23       2         0     0.960     0.840    0.211
cross    Extract           25      15       6         4     0.720     0.480    0.686
cross    Filter2           25      12       6         7     0.600     0.200    0.617
cross    Filter3           25      20       3         2     0.860     0.760    0.611
cross    Ceiling           25      24       1         0     0.980     1.000    1.000
cross    GraphRAG local    25       9      12         4     0.600     0.840    0.069
cross    GraphRAG global   25       1      10        14     0.240     0.360    0.053
```

The sweep's prediction holds: deepening retrieval lifts the cross-reference
score from 0.680 to 0.840 (incorrect 5→2), and single-passage saturates to
1.00. Chapter recall rises (cross 0.44→0.68) at the cost of precision
(0.41→0.27) — more context, looser filtering — yet **accuracy rises**, so the
extra context helps more than it distracts. Vector k=10 overtakes Extract on
accuracy (0.92 vs 0.86) while Extract still leads sharply on chapter precision
(0.84).

**Hybrid** (dense ∪ BM25 union) becomes the top retrieval method: Hybrid k=10
at 0.980 overtakes Filter3 (0.930) by fully recovering two of the three
lexically-distinctive cross-reference chapters that dense-only search cannot
rank (Q43, Q49 — the Class A cases from
[§ Both wrong](#both-wrong-what-k10-cannot-fix)) and partially recovering the
third (Q31 — Ch21 enters the union context but Ch22 still does not, so the
answer lands `partial`). The cross-reference score rises from 0.840 to 0.960
(incorrect 2→0). Hybrid k=8 (0.920) recovers Q43 and Q49 fully, partially
recovers Q31, and lifts cross to 0.880, sitting between k=5 (0.880) and k=10
(0.980). Single-passage saturates to 1.00 only at k=10: k=5 and k=8 both land
at 24/25, missing Q17, a single-passage question every Vector depth answers.

The **Filter** rows use the LLM as retriever rather than dense embeddings:
Filter3 posts 0.930, Filter2 0.800. The `maybe`-verdict mechanism, cost/gold-floor
analysis, and verdict that finds no retrieval advantage over Vector k=10 are in
[FILTER.md](../FILTER.md).

## Extract vs Vector k=10: where each method loses

The Headline's four-question margin is the whole story of "k=10 beats Extract,"
so [`report.py`](../README.md#reportpy)
breaks it open into its per-question causes — and it lands squarely on Extract's
two-stage filter. The disagreement pass prints three pairwise matrices (Vector k=5×Vector k=10,
Vector k=5×Extract, Vector k=10×Extract); the decisive one is the last:

```
Agreement matrix (rows = Vector k=10, cols = Extract):
                  Extract:correct  Extract:partial  Extract:incorrect | Vector k=10 total
Vector k=10:correct                37               4                  3  | 44
Vector k=10:partial                 1               2                  1  |  4
Vector k=10:incorrect               2               0                  0  |  2
Extract total                      40               6                  4  | 50
```

For each off-diagonal question the disagreement pass asks whether the loser
actually held every gold chapter in context, then classes the loss:

- **missed context** — a gold chapter is absent from the loser's `expanded`. For
  Extract that is a **Phase 1 false negative** (a wrong `None` dropped it
  unrecoverably); for Vector a **retrieval miss** (the chapter ranked outside top-k).
- **synthesis** — the loser held every gold chapter yet still mis-synthesized.

The split is lopsided:

| direction | n | missed context | synthesis |
| --- | --- | --- | --- |
| Vector k=10 beats Extract | 8 | **5** (Phase 1 FN) | 3 |
| Extract beats Vector k=10 | 3 | 3 (retrieval miss) | 0 |

**Five of Extract's eight losses are Phase 1 false negatives** (Q26, Q28, Q34,
Q40, Q42) — the gold chapter a stage-1 `None` dropped, so stage 2
never saw it. The filter, not the synthesis, is where the gap lives. Three are
total wipeouts: Q42 (`expanded` empty — all of Ch22/23/29 dropped), Q34 (only
Ch2 kept, all of Ch30/31/33 dropped), and Q26 (used Ch15/30, disjoint from gold
Ch11/29). The remaining three losses (Q30, Q33, Q46) are genuine synthesis slips
where Extract held every gold chapter — the same half-answers the
[k=5 study](#k5-baseline-in-brief) flagged.

**Every one of Extract's wins is a retrieval miss Vector cannot fix.** Q31, Q43,
Q49 are the [Class A](#both-wrong-what-k10-cannot-fix) chapters dense embedding
ranks outside the top-10 at both depths — Extract's per-chapter reading finds
them, Vector k=10 never does. Extract never beats Vector k=10 on synthesis.

So the two architectures fail on **orthogonal axes**, and that is the read on
the 0.92 vs 0.86 margin: Extract's losses are self-inflicted by its own Phase 1
filter (cheaply fixable — keep more context, weaken the `None` bar, or quote
verbatim instead of summarize-or-discard), whereas Vector's losses are structural
dense-retrieval blindness (the BM25/lexical hybrid in [HYBRID.md](../HYBRID.md)).
Fixing Phase 1 alone lifts Extract toward a 40+5 = 45 ceiling — re-overtaking
k=10 — while its thorough-reading edge on the vector-unreachable three stays
intact. The lever for Extract is in its own stage 1; the lever for Vector is
hybrid retrieval.

## k=5 baseline, in brief

(This condenses the earlier Vector-vs-Extract disagreement study; the per-question
detail is redeployed in the k=10 analysis below.) Vector k=5 (0.820) and Extract
(0.860) land within 0.040 of each other but split on **which** cross questions
each solves. The single/cross split dominates everything: they score 24/25 and
25/25 on single-passage but only 14/25 and 15/25 on cross.

**Agreement matrix (k=5 Vector × Extract)** — now reproduced verbatim by the
`Vector k=5 × Extract` block of `report.py`'s disagreement pass:

| | Ext correct | Ext partial | Ext incorrect | Vector total |
| --- | --- | --- | --- | --- |
| **Vector correct** | 32 | 5 | 1 | 38 |
| **Vector partial** | 3 | 1 | 2 | 6 |
| **Vector incorrect** | 5 | 0 | 1 | 6 |

Two failure modes account for almost every off-diagonal loss:

- **Vector k=5's losses are mostly top-5 retrieval misses** — a gold chapter ranks
  just outside `k=5` (the +0.00–0.07 gaps `sweep_vector.py` flagged). Two exceptions
  (Q21, Q29) are *answering* slips where the gold chapter was already in context.
- **Extract's losses are Phase 1 false negatives** — a wrong `None` on a gold
  chapter drops it unrecoverably (Q26, Q34, Q42 dropped gold chapters entirely).
  A secondary loss is Phase 2 synthesis (Q30, Q33, Q46 held every gold chapter
  yet only half-answered).

**The gold is sound.** On Q29 (the covert poisoning behind the surface exile
decree), both Extract and Vector k=10 independently reconstruct the covert chain
the gold describes — two thorough paths agreeing with the gold is convergent
evidence it is correct, and Vector k=5's loss there is an answering failure, not a
gold problem.

## What changes at k=10

Thirteen questions are not-correct in at least one of k=5 / k=10. Their movement
(`k=10 retrieval` = gold chapters newly pulled into context vs. k=5):

| Q | type | gold | k=5 | k=10 | k=10 retrieval | class |
| --- | --- | --- | --- | --- | --- | --- |
| 21 | single | 5 | incorrect | **correct** | — (Ch5 already in k=5) | answering fix |
| 27 | cross | 2,4,33 | partial | **correct** | +Ch33 | retrieval fix |
| 28 | cross | 9,37 | incorrect | **correct** | +Ch9, +Ch37 | retrieval fix |
| 29 | cross | 16,17 | incorrect | **correct** | — (both already in k=5) | answering fix |
| 36 | cross | 1,17,21 | incorrect | **correct** | +Ch17 | retrieval fix |
| 42 | cross | 22,23,29 | partial | **correct** | +Ch29 (Ch23 still out) | retrieval fix |
| 45 | cross | 18,25 | partial | **correct** | +Ch18 | retrieval fix |
| 50 | cross | 8,18,23 | correct | **partial** | +Ch23 | **regression** |
| 31 | cross | 21,22,23 | incorrect | incorrect | +Ch23, but Ch21/22 still out | both wrong |
| 32 | cross | 11,15,16 | partial | partial | Ch15 still out | both wrong |
| 34 | cross | 30,31,33 | partial | partial | Ch31 still out | both wrong |
| 43 | cross | 11,37 | partial | partial | Ch37 still out | both wrong |
| 49 | cross | 2,22 | incorrect | incorrect | Ch22 still out | both wrong |

### The seven fixes

Two flavors, matching the k=5 failure-mode split:

- **Retrieval fixes (Q27, Q28, Q36, Q42, Q45).** A gold chapter that ranked just
  outside k=5 enters the top-10 — exactly the "gap +0.00–0.07" cases
  `sweep_vector.py` predicted: Ch33 (Q27), Ch9+Ch37 (Q28), Ch17 (Q36),
  Ch29 (Q42), Ch18 (Q45).
- **Answering fixes (Q21, Q29).** The gold chapter was *already* in k=5's
  context; k=10's broader supporting context let the answerer synthesize the
  right answer. Q21 (Ch5 present at both depths — k=5 cited the wrong incident,
  k=10 named both offenses); Q29 (Ch16+17 present at both — k=5 stopped at the
  surface exile decree, k=10 gave the covert poisoning). These are precisely the
  two k=5 losses `sweep_vector.py` could *not* have explained by retrieval alone.

### The one regression: Q50

Q50 (gold 8,18,23) goes correct→partial, and it is the judge's boundary rather
than the context that moved. Both depths describe Surma restyling Vibha's hair
and Vibha later waiting with it unbraided, and both omit the third step,
Rammohan pointing to her unkempt hair as proof of her neglect (Ch23, which only
k=10 retrieves). The judge notes that omission at both depths, but grades k=5
`correct` and k=10 `partial`. The net trade is overwhelmingly positive — seven
fixes for one regression.

## Both wrong: what k=10 cannot fix

Five questions stay not-correct at both depths (Q31, Q32, Q34, Q43, Q49) — all
cross-reference. The decisive cross-check is what **Extract**, reading every
chapter independently, makes of them:

| Q | gold | load-bearing chapter vector search misses | Vector k=5 | Vector k=10 | Hybrid k=8 | Hybrid k=10 | Extract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | 21,22,23 | Ch21,22 — the ring gift and the seal-forgery | incorrect | incorrect | partial | partial | **correct** |
| 43 | 11,37 | Ch37 — the Chandradwip palanquin extraction | partial | partial | **correct** | **correct** | **correct** |
| 49 | 2,22 | Ch22 — the forged petition to the Emperor of Delhi | incorrect | incorrect | **correct** | **correct** | **correct** |
| 32 | 11,15,16 | Ch15 — the secret stipend to the dismissed guards | partial | partial | partial | partial | partial |
| 34 | 30,31,33 | Ch31 — Rukmini's accusation in Pratapaditya's court | partial | partial | **correct** | **correct** | incorrect |

This splits the residual frontier cleanly into two classes.

### Class A — vector-unreachable chapters that thorough reading finds (Q31, Q43, Q49)

In three questions the answer turns on a single chapter that dense embedding
ranks outside the top-10 at *both* depths, so no k≤10 surfaces it; the answerer
honestly abstains (Q31, Q49) or gives half the answer (Q43). But **Extract,
reading those chapters in full, gets all three correct** — reconstructing the
ring→seal→forged-petition chain (Q31, Ch21–22), the Chandradwip palanquin
rescue (Q43, Ch37), and the Delhi-petition forgery (Q49, Ch22).

That convergent result is decisive: these are not gold problems (an independent
thorough reader confirms the gold) and not a depth problem (deeper k still
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

### Class B — the failures shared with Extract (Q32, Q34)

The remaining two questions are not-correct for **all three methods**, so deeper
Vector retrieval cannot be the lever:

- **Q32** (gold 11,15,16) — the gold's load-bearing middle step is the *secret
  monthly stipend* Udayaditya and Surma pay the dismissed guards, which
  Pratapaditya discovers. Ch15 never ranks in the top-10 for either Vector depth,
  and Extract's per-chapter extraction misses the stipend too, attributing the
  exile to vague "psychological tactics." All three land on partial. The causal
  detail is genuinely subtle and lives in a chapter none of the methods weighs
  heavily.
- **Q34** (gold 30,31,33) — the link is Ch31, where Rukmini tells Pratapaditya's
  court that Basanta Ray helped the escape. Both Vector depths hold Ch30 and
  Ch33 but not Ch31, and fill the gap with another cause (Rukmini alerting
  soldiers in Raigarh at k=5, a pre-existing order at k=10), landing partial;
  Extract's Phase 1 drops all three gold chapters and answers incorrectly.

Q32 is the true residual: no `k` or hybrid fixes it. Q34 is not — BM25 ranks
Ch31 into the union, and Hybrid k=8 and k=10 answer it correctly. Ceiling
([§ below](#ceiling-the-perfect-retrieval-upper-bound)) shows both limits are
retrieval-side after all: with the gold chapters verbatim in context the
answerer gets Q32 and Q34 correct.

## Hybrid (dense ∪ BM25 union)

The union approach from [HYBRID.md](../HYBRID.md) converts the strict-recall
retrieval gain into answer accuracy. At k=10, it achieves the top retrieval
accuracy of **0.980** (with k=8 at **0.920**), mostly recovering the Class A
chapters that dense-only search cannot reach — fully for Q43/Q49, partially for
Q31 (Ch22 stays out of reach).

### Hybrid k=5 vs Vector k=10

Hybrid k=5 (0.880) sits below Vector k=10 (0.920) overall, but the two
methods win on **orthogonal questions**:

| direction | n | questions | class |
| --- | --- | --- | --- |
| Hybrid k=5 beats Vector k=10 | 4 | Q31 (Ch21, Class A), Q34 (Ch31), Q49 (Ch22, Class A), Q50 (synthesis) | 3 missed-context, 1 synthesis |
| Vector k=10 beats Hybrid k=5 | 7 | Q17 (synthesis), Q27 (Ch33), Q28 (Ch9), Q37 (synthesis), Q42 (Ch29), Q46 (synthesis), Q48 (neither holds Ch11) | 4 missed-context, 3 synthesis |

Three of the four Hybrid k=5 wins are retrieval fixes — BM25's lexical signal
surfaces chapters that dense embedding ranks outside the top-10. Q31 and Q49 are
Class A: Ch21 (the ring gift; Ch22 stays out) and Ch22 (forged Delhi
petition), both lexically distinctive but semantically generic. The fourth, Q50,
is the judge boundary of [§ The one regression](#the-one-regression-q50): every
Vector and Hybrid answer omits Rammohan's remark, and the judge passes some of
them. Vector k=10's wins are mostly the reverse, chapters dense k=10 reaches
but the k=5 union does not (Q27, Q28, Q42), plus Q48, where neither holds Ch11
and only Vector k=10 supplies the court half from Ch19, and three synthesis
losses, one of them the single-passage Q17, where the wider union context
confuses the answerer on a single-chapter question. On cross-reference, Hybrid k=5 (0.800) trails Vector
k=10 (0.840).

### Hybrid k=10 recovers most of the Class A frontier

At k=10 the union closes most of the Class A gap. Hybrid k=10 beats Vector k=10
on five questions, four of them missed-context:

| Q | gold | dropped by Vector k=10 | why BM25 recovers it |
| --- | --- | --- | --- |
| Q31 | 21,22,23 | Ch21, Ch22 | only Ch21 recovers; Ch22 stays outside top-10 at any k≤10 for this question (see [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)) — partial credit only |
| Q34 | 30,31,33 | Ch31 | Ch31 enters the BM25 top-k |
| Q43 | 11,37 | Ch37 | "Chandradwip palanquin" — proper-noun-heavy |
| Q49 | 2,22 | Ch22 | "Emperor of Delhi", "forged petition" |

The fifth is Q50 again (Vector k=10 `partial`, Hybrid k=10 `correct` on the
same omission). Vector k=10 beats Hybrid k=10 on **no** question: the ~1.4×
larger union context that HYBRID.md warned could confuse synthesis costs nothing
here.

### Hybrid k=8: Performance and Trade-offs

Expanding the retrieval depth to `k=8` yields **44/50 (0.920)**, sitting between `k=5` (**0.880**) and `k=10` (**0.980**).

- **Gains over k=5:** Deepening the search to `k=8` recovers the missing gold chapters for **Q27** (Ch33), **Q28** (Ch9), **Q42** (Ch29) and **Q43** (Ch37), and answers **Q37** and **Q46** fully from the same chapters, upgrading all six to correct. It loses **Q29** (a synthesis regression, correct at `k=5` to incorrect) and **Q50** (the judge boundary above), netting +4 correct answers.
- **Comparison to k=10:** Unlike Japanese, where `k=10` (`0.910`) falls below `k=8` (`0.920`) and `k=5` (`0.930`), English improves all the way. `k=10` beats `k=8` on four questions and loses none: it recovers the regression on **Q29**, improves **Q17** to correct, completes **Q48**, and is graded correct on **Q50**. Only Q50 involves a new gold chapter (Ch23), and the `k=10` answer does not use it. Overall `k=10` nets +4 correct answers (**48/50** vs. **44/50**), so the English answerer handles the larger context at `k=10` (~25 scenes) without loss.

### The two-question residual

Ceiling beats Hybrid k=10 on two questions, both missed context:

- **Q31** — Ch22 (where the petition is actually forged) is
  outside both retrievers' top-k at k=10; Ch21 alone lets Hybrid k=10 describe
  the ring changing hands but not the petition's content, landing `partial`.
- **Q32** — Ch15 (the secret stipend detail) is outside both
  retrievers' top-k at k=10 and remains a Class B unreachable.

These two pin Hybrid k=10's residual: the two shared blind spots (Q31 Ch22,
Q32 Ch15) no retrieval blend fixes. Hybrid k=10 in turn beats Ceiling on Q48
([§ Q48](#q48-the-two-part-question)).

## Vector-line (line-level retrieval)

`Vector-line` keeps the dense pipeline but shrinks the retrieval unit from a
scene to a **single line**: [`build_index.py --line`](../README.md#build_indexpy)
embeds one vector per non-blank line, and
[`answer_vector.py --line`](../README.md#answer_vectorpy) ranks lines, then
resolves each hit line back to its containing segment before the same ±N
expansion and answering. The question is whether a finer unit — matching the one
sentence that answers the question, rather than diluting it across a whole scene
— retrieves better.

It does not, on balance. The headline is **0.770 (k=5) / 0.850 (k=10)**, below
segment Vector's 0.820 / 0.920 at both depths. The line unit does what
finer granularity should — it lifts **chapter precision** (k=5 0.337→0.401, k=10
0.205→0.274, the highest of any dense method) and **saturates single-passage to
1.000 at k=5**, beating segment k=5's 0.960. But it lowers **chapter
recall** (k=5 0.720→0.660, k=10 0.840→0.780), and almost the entire deficit is
cross-reference: cross drops to 0.540 (k=5) and 0.740 (k=10).

### Why cross-reference suffers

Most Vector-line losses against segment Vector are **missed-context** retrieval
misses, 9 of 10 at k=5 and 5 of 8 at k=10:

| direction | n | missed-context | synthesis |
| --- | --- | --- | --- |
| Vector k=5 beats Vector-line k=5 | 10 | 9 | 1 |
| Vector-line k=5 beats Vector k=5 | 5 | 3 | 2 |
| Vector k=10 beats Vector-line k=10 | 8 | 5 | 3 |
| Vector-line k=10 beats Vector k=10 | 3 | 2 | 1 |

The mechanism is the flip side of the precision gain. When a gold chapter's
relevance is carried by **one distinctive line**, the line unit surfaces it
cleanly; but when the relevant content is **diffuse across a scene**, no single
line accumulates enough similarity to crack the top-k, whereas the scene-level
average still ranks. Cross-reference questions lean on the diffuse case, so they
lose the most (e.g. Q26 Ch11/29 and Q40 Ch13/27, both dropped by
Vector-line k=5 but held by segment k=5).

### The misses are orthogonal

Crucially, Vector-line is not strictly worse retrieval — it has its **own** wins
that segment search drops. At k=10 it recovers **Q34 (Ch31)**, a chapter
segment search misses at both depths, here surfaced because one lexically sharp
line ranks where the averaged scene did not, and it lifts the
[Class A](#both-wrong-what-k10-cannot-fix) Q49 from incorrect to partial even
without Ch22. At k=5 it likewise lifts Q49 to partial, fixes Q21/Q29 by
synthesis and Q45 by retrieval, and lifts Q28 from incorrect to partial by
retrieving both of its chapters. So line and
segment granularity fail on **orthogonal chapters** — the same dense-vs-lexical
tension [Hybrid](#hybrid-dense--bm25-union) exploits, in miniature — but the line
unit drops more cross chapters than it recovers, so the net is negative and
segment-level retrieval stays the stronger dense baseline.

### Depth still helps

Like segment Vector, deepening k=5→k=10 is almost purely a retrieval gain:
Vector-line k=10 beats k=5 on 8 questions, **7 of them missed-context** (the
eighth, Q28, already has both gold chapters at k=5 but answers only partially),
against two synthesis regressions (Q22, Q48). The k=5 unit is simply too tight for cross-reference —
the same lesson [`sweep_vector.py`](../README.md#sweep_vectorpy) drew for the
segment index, only sharper here because the line unit retrieves less per hit.

## V-hybrid (segment ∪ line dense union)

`V-hybrid` (`answer_vector.py --hybrid`) unions the two *dense* retrievers —
segment top-k ∪ line top-k, resolved to segments — converting the segment∪line
strict-recall gain from [VECTOR-HYBRID.md](../VECTOR-HYBRID.md) (en +2 @ k=5, +3
@ k=10) into answer accuracy. It is the same union idea as
[Hybrid](#hybrid-dense--bm25-union), but with two same-model cosines instead of
dense + BM25, so it needs no score-scale reconciliation and works in both
languages.

It scores **0.870 (k=5) / 0.930 (k=10)** — above plain Vector k=5 (0.820) and
Vector-line (0.770 / 0.850), level with segment Vector k=10 (0.920) at k=10, and
below the dense∪BM25 Hybrid (0.880 / 0.980). The most striking column is
`incorrect`: V-hybrid k=5 has just **2** (vs Vector k=5's 6, Vector-line k=5's
6), with 9 partials. The
union surfaces so many gold chapters that almost nothing is fully missed — chapter
recall on cross-reference reaches **0.800 at k=10** (vs Vector k=10's 0.680) —
but the recovered chapters convert to *partial* more often than *correct*: the
right chapter is present, yet the wider context dilutes synthesis.

### Two ceilings it does not break

The disagreement pass pins why V-hybrid lands level with Vector k=10 and below
Hybrid:

- **vs segment Vector k=10 (wins 2–1).** V-hybrid k=10 beats Vector k=10 on two
  questions, Q49 (lifted to partial although neither holds Ch22) and Q50 (the
  judge boundary of [§ The one regression](#the-one-regression-q50)), and loses
  one, Q48, by **synthesis**, where the ~1.4× larger union context leaves the
  answer incomplete with the same chapters. The retrieval gain is real, but it
  barely shows in answer accuracy, as [VECTOR-HYBRID.md](../VECTOR-HYBRID.md)
  warned: synthesis pays for the extra context.
- **vs dense∪BM25 Hybrid k=10 (loses 5–0).** Hybrid strictly dominates: it wins
  five questions (three missed-context, two synthesis), V-hybrid wins none. The
  three missed-context losses are the [Class A](#both-wrong-what-k10-cannot-fix)
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
k=10 (0.920) — which it trails, losing five questions and winning none. **Japanese confirms the pattern rather than reversing
it:** there V-hybrid k=5 falls just below plain Vector k=10 (0.890 vs 0.900), never beating
it — the segment∪line union has no BM25-equivalent lever for the dense-blind
chapters, so it buys no accuracy over the simpler single-index retriever (see
[results-ja/README.md](../results-ja/README.md#v-hybrid-segment--line-dense-union)).

## Filter (LLM-as-retriever)

The per-chapter Filter strategy — reading every chapter and keeping those the
LLM does not mark irrelevant, then answering from their full text — is analyzed
in full in [FILTER.md](../FILTER.md). The short version relevant to this case
study: Filter3 (`yes`/`maybe`/`no`, keep all but `no`) answers the three
vector-unreachable Class A questions (Q31, Q43, Q49) correctly, the same wins
per-chapter Extract gets, confirming those are a dense-retrieval problem rather
than a gold one. Its residual losses are mostly confident-wrong-`no` wipeouts
(Q34, Q42, and the Class B Q32), the same chapters Extract also drops, plus
two partials on Q47 and Q50. The `maybe`
verdict is the lever — the strict two-level Filter2 (keep only `yes`) falls to
0.800, below Extract — but the gold-floor and cost analysis in FILTER.md finds
no retrieval advantage over Vector k=10. The Ceiling comparison below uses Filter3
as the best-scoring retrieval method.

## Ceiling: the perfect-retrieval upper bound

Ceiling strips out retrieval entirely: the gold `chapters` are fed verbatim as
context, so chapter recall and precision are both **1.000 by construction** —
the context *is* the gold set. Every Ceiling loss is therefore a pure
**synthesis** loss, and its score (0.990) is the upper bound every retrieval
strategy chases. The question it answers is not *"which chapters should the
answerer see?"* but *"given the right chapters, how well does the model read
and synthesize?"*

### Ceiling's margin over every method

Ceiling's margin over each method is the pure cost of that method's retrieval,
and the gradient tracks retrieval quality exactly:

| method | method score | Ceiling beats it on | missed-context | synthesis | beats Ceiling on |
| --- | --- | --- | --- | --- | --- |
| Filter2 | 0.800 | 12 | 12 | 0 | 0 |
| Vector k=5 | 0.820 | 12 | 10 | 2 | 1 |
| Extract | 0.860 | 10 | 7 | 3 | 1 |
| Hybrid k=5 | 0.880 | 9 | 6 | 3 | 0 |
| Vector k=10 | 0.920 | 6 | 5 | 1 | 1 |
| Filter3 | 0.930 | 5 | 4 | 1 | 1 |
| Hybrid k=10 | 0.980 | 2 | 2 | 0 | 1 |

The count never grows as accuracy rises: the better the retrieval, the
fewer questions separate it from the ceiling. **Hybrid k=10 — the top-scoring
retrieval method — sits just two questions below Ceiling**; Filter3 sits five.

Where the last column is non-zero it is always the same question: Q48, where
Ceiling lands `partial`. It is a completeness gap on a two-part answer, not a
retrieval effect, and only part of it is a real gap — Vector k=5, Extract and
Filter3 omit the same half Ceiling omits and are scored `correct` regardless.
See [§ Q48](#q48-the-two-part-question) below.

### The five-question gap to Filter3

Filter3 is the closest per-chapter method gets to Ceiling. Its five losses pin
down what classifier-based retrieval still cannot fix:

- **Q32, Q34, Q42 (missed-context)** — the confident-wrong-`no` wipeouts
  (see [FILTER.md](../FILTER.md#failure-mode)).
  Every gold chapter was marked `no`, so Phase 2 saw nothing. These are the
  same questions Extract drops too (two different classifiers, each reading
  the full chapter, independently decide they are irrelevant), and Ceiling
  recovers all three — confirming the gold chapters *do* contain the answer.
  No threshold trick fixes them: the model never hesitated (`no`, not
  `maybe`), so the `maybe` rescue cannot reach.
- **Q50 (missed-context)** — Ch23 was marked `no`, and with it Rammohan
  pointing to Vibha's unkempt hair; the answer stops at the unbraided hair.
- **Q47 (synthesis)** — Filter3 held both gold chapters (29, 31) and, like
  Ceiling, describes the fire, the burnt cell and the bones, skull and sword
  without the melted sword being brought before Pratapaditya. The judge marks
  that omission `partial` for Filter3 and passes it for Ceiling, so this loss
  is the judge's boundary, not a difference in reading.

So of Filter3's five losses, four are classifier confidence (fixable only by a
better `no` bar) and one is judge noise. None is a dense-retrieval
blindness case — Filter3's per-chapter reading already solved Q31, Q43, Q49, and
so does Hybrid k=10.

### Q48: the two-part question

Ceiling's lone loss — Q48 (gold 11,19), **partial** — is the one question where
several retrieval methods land `correct` and Ceiling does not. The gold has two
halves: Ramchandra's
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
difference in context. It is not a clean split either. Six methods land
`correct`, but only three of them — Vector k=10, Vector-line k=5 and
Hybrid k=10 — actually supply the court half. Vector k=5, Extract and Filter3
stop exactly where Ceiling stops, and the judge passes them anyway, granting
`correct` while noting in its own reason that the answer "omits the ... detail
about laughing and joking in court". So Ceiling's deficit on Q48 is real
against three methods and judge-boundary noise against the other three.

### What Ceiling confirms

- **The single-passage axis is solved.** Single-passage saturates to 1.000
  under Ceiling, Filter3, Extract, Vector k=10 and Hybrid k=10, and every
  method except GraphRAG reaches at least 24/25. The few single-passage losses
  (Q17, Q21, Q22) are synthesis slips with the gold chapter in context. The
  entire frontier is cross-reference.
- **The accuracy gap between methods traces almost entirely to retrieval.**
  Ceiling's context is identical in shape to Filter3's Phase 2 (full chapter
  text, same prompt, same model); the only difference is *which* chapters —
  Ceiling's are perfect, Filter3's are classifier-selected. So Ceiling's 0.990
  vs Filter3's 0.930 measures what Filter3's four `no` losses cost, plus one
  question of judge noise (Q47).
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

### GraphRAG local (0.610)

Local search posts 24/50 (0.610) — below Filter2 (0.800) and far below Hybrid
k=10 (0.980). The chapter-retrieval numbers tell the story: **recall 0.860,
precision 0.135** (the lowest of any non-global method). Entity-graph expansion
tends to pull in nearly all 37 chapters as expanded context, so gold chapters
are almost always present — but the answerer is forced to synthesize from an
overloaded context with minimal signal-to-noise.

The failure mode is therefore **synthesis-dominated**. Of GraphRAG local's 25
losses to Ceiling, **18 are synthesis** (the gold chapter is present but the
answer is wrong or vague) and only 7 are missed context. This is the inverse of
Vector k=5 (where most losses are retrieval misses) and is structurally similar
to the "lost in the middle" effect: the right content is there, but buried under
noise. Hybrid k=10 keeps its context to the union top-k and avoids this;
GraphRAG local has no equivalent precision control.

The synthesis collapse is sharpest on **single-passage questions** (15/25,
0.620) — the category every retrieval method with adequate recall saturates to
≥24/25. GraphRAG local drops 9 of those 25 to incorrect (and 1 to partial),
producing the worst single-passage score of any non-global method. On
cross-reference it lands at 9/25 (0.600), below Vector k=5 (0.680) — the
chapter-graph's entity links provide no structural advantage when the
bottleneck is synthesis over a noisy context.

GraphRAG local **beats Hybrid k=10 on a single question** (Q31, where the
union context still lacks Ch22). Hybrid k=10 wins 26 questions against it (19
synthesis, 7 missed context).

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

### GraphRAG global (0.170)

Global search is essentially non-functional for passage-level QA. It scores
3/50 (0.170) — the lowest of any method by a wide margin — and the mechanism is
clear from the chapter-retrieval numbers: **recall 0.220, precision 0.029**.
Community summaries operate at the wrong granularity: they abstract away the
specific chapter details the questions turn on. Of the 47 questions where
Ceiling beats GraphRAG global, **38 are missed context** — the relevant textual
evidence is simply absent from the retrieved context, not merely mis-synthesized.

Single-passage (2/25, 0.100) is almost a complete failure: community-level
summaries cannot anchor a question to the specific scene where an event occurs.
Cross-reference (1/25 correct, 0.240) fares slightly better on the weighted
score because a handful of prominent cross-cutting themes appear in the
community summaries, earning 10 partials, but the score is still far below
every other method including Filter2 (0.600).

### Summary

Neither GraphRAG mode reaches the level of the simplest pipeline method (Vector
k=5, 0.820). The local mode's high recall does not translate to accuracy because
synthesis degrades over an overloaded context; the global mode's community
abstractions miss the passage-level details entirely. For a chapter-structured
novel QA task with specific factual questions, the flat embedding pipeline —
especially with the BM25 union — outperforms the knowledge-graph approach at a
fraction of the indexing cost (4 h+ for GraphRAG vs. minutes for the embedding
index).

## Takeaways

- **k=10 delivers the sweep's promise on cross-reference** (0.680→0.840),
  single saturates to 1.00, and Vector k=10 overtakes Extract on accuracy
  (0.92 vs 0.86). The win is broad — seven questions fixed — at the cost of one
  regression (Q50, a judge boundary) and lower chapter precision. (The Filter
  rows — Filter3 at 0.93, Filter2 at 0.80 — are analyzed in
  [FILTER.md](../FILTER.md).)
- **The 0.92 vs 0.86 margin is Extract's Phase 1 filter, not its synthesis —
  and Filter3 confirms the fix.** `report.py`'s disagreement pass shows 5 of
  Extract's 8 losses to k=10 are Phase 1 false negatives (a gold chapter
  dropped by a wrong `None`); only 3 are synthesis slips. The k=10 study
  predicted the lever was to *weaken Extract's `None` bar* (ceiling 40+5 = 45
  correct, re-overtaking k=10); Filter3 is that lever made real — keeping
  every chapter not marked `no` recovers 3 of those 5 Phase 1 false negatives
  (plus all 3 synthesis slips) and lands at 45 correct / 0.930 weighted, level
  with the 45 ceiling even though Q34 and Q42 stay false negatives for Filter3
  too.
- **Two of the k=5 losses were not retrieval problems.** Two of the seven fixes
  (Q21, Q29) had the gold chapter in context all along; k=10's extra context
  just yielded a better answer. Retrieval depth is not the only lever — answer
  synthesis improves with context too.
- **The dense-retrieval blindness frontier is closeable without per-chapter cost.**
  Of the five both-wrong questions, three (Q31, Q43, Q49) are Class A: Extract
  and Filter3, reading the full chapter text, get all three correct, and
  **Hybrid k=10** gets Q43 and Q49 correct and Q31 partial. The chapter-question
  link is vector-unreachable at k≤10 but lexically distinctive; BM25 surfaces
  these chapters at k=10 (all but Q31's Ch22), making the union approach nearly
  as effective as per-chapter reading for the Class A frontier at a fraction of
  the cost.
- **Hybrid k=10 (0.980) is the top retrieval method** and the closest to Ceiling
  among all methods. It translates the +4 retrieval recall from HYBRID.md into
  +4 correct answers over Vector k=10, losing no question to it, and leaves two
  shared blind spots (Q31, Ch22; Q32, Ch15). Single-passage saturates to 1.00
  only at k=10 (k=5 and k=8 miss Q17), and on cross-reference Hybrid k=10
  (0.960) still trails the cross Ceiling (0.980) by the Q31/Q32 blind spots.
- **The `maybe` verdict is what makes the per-chapter filter work**, and its
  residual is a *confident* wrong `no` (Q32, Q34, Q42) that no threshold trick
  reaches — but the gold-floor and cost analysis still finds no retrieval
  advantage over Hybrid k=10. The full mechanism and verdict are in
  [FILTER.md](../FILTER.md).
- **One question is hard for every retrieval method** (Q32): all methods land
  partial (Hybrid k=10 included — Ch15 is outside the union's top-k at k=10).
  Ceiling disambiguates it: with Ch15 fed verbatim the answerer gets it
  *correct*, so the gold is sound and the other methods' failures are
  retrieval/extraction.
- **Ceiling isolates the synthesis ceiling at 0.990.** With retrieval stripped
  out (gold chapters verbatim), the answerer reads 49 of 50 correctly —
  including Q32, which every retrieval method gets partial — and its single
  `partial` is Q48, a completeness gap on a two-part answer that two of the
  seven methods below actually fill (three more are scored `correct` on the
  same omission — see [§ Q48](#q48-the-two-part-question)). Ceiling's margin
  over each method
  (12/12/10/9/6/5/2 for
  Filter2/Vector k=5/Extract/Hybrid k=5/Vector k=10/Filter3/Hybrid k=10) never
  grows with retrieval quality, tracing almost the entire accuracy gap to
  retrieval. Hybrid k=10 is within two questions — the two shared blind spots —
  and neither is a classifier or depth problem. The
  retrieval frontier is effectively closed; what remains is two chapters no blend
  of dense + BM25 can rank (Q31, Ch22; Q32, Ch15).
- **The gold holds up.** Across every disagreement the failures trace to a
  method or to the judge's boundary — never to the gold — and Ceiling confirms
  the ones the other methods most often miss: Q31/Q43/Q49 (the
  vector-unreachable trio, all correct under Ceiling), Q32 (the secret-stipend
  question, correct under Ceiling despite being partial for every retrieval
  method) and Q34 (correct under Ceiling, which holds Ch31).
- **GraphRAG does not match the pipeline on this task overall, but reveals what
  graph structure can and cannot do.** Local search (0.610) falls below Filter2:
  entity-graph expansion overloads context (recall 0.860, precision 0.135) and
  18 of 25 losses to Ceiling are synthesis failures, not missed context. Yet it
  has a coherent strength — questions about *character relationship arcs and
  narrative causality* (e.g. Q26/Q28, answered with 0 chapters from pure graph
  traversal, both partial; Q31/Q49, the Class A cases that
  dense+BM25 also recovers via lexical matching, here reached via entity
  chains, Q31 correct and Q49 partial). It fails on microdetail questions
  requiring specific text. Global
  search (0.170) is non-functional: community summaries are the wrong
  granularity (38 of 47 losses to Ceiling are missed context). Global never
  beats Hybrid k=10; local beats it only on Q31.
