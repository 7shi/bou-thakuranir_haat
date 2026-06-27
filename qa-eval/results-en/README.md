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
scope    method         n correct partial incorrect  weighted ch.recall  ch.prec
--------------------------------------------------------------------------------
all      Vector k=5        50      39       5         6     0.830     0.720    0.337
all      Vector k=10       50      44       4         2     0.920     0.840    0.205
all      Vector-line k=5   50      35      10         5     0.800     0.660    0.401
all      Vector-line k=10  50      41       7         2     0.890     0.780    0.274
all      V-hybrid k=5      50      40       9         1     0.890     0.760    0.297
all      V-hybrid k=10     50      43       5         2     0.910     0.900    0.182
all      Hybrid k=5        50      43       5         2     0.910     0.800    0.251
all      Hybrid k=8        50      46       2         2     0.940     0.900    0.179
all      Hybrid k=10       50      47       2         1     0.960     0.920    0.154
all      Extract           50      39       5         6     0.830     0.740    0.843
all      Filter2           50      36       7         7     0.790     0.600    0.808
all      Filter3           50      45       3         2     0.930     0.880    0.775
all      Ceiling           50      49       1         0     0.990     1.000    1.000
all      GraphRAG local    50      28      10        12     0.660     0.860    0.135
all      GraphRAG global   50       5       7        38     0.170     0.220    0.029

single   Vector k=5        25      24       0         1     0.960     1.000    0.263
single   Vector k=10       25      25       0         0     1.000     1.000    0.136
single   Vector-line k=5   25      25       0         0     1.000     1.000    0.392
single   Vector-line k=10  25      25       0         0     1.000     1.000    0.244
single   V-hybrid k=5      25      25       0         0     1.000     1.000    0.226
single   V-hybrid k=10     25      24       0         1     0.960     1.000    0.119
single   Hybrid k=5        25      24       0         1     0.960     1.000    0.178
single   Hybrid k=8        25      24       0         1     0.960     1.000    0.117
single   Hybrid k=10       25      24       0         1     0.960     1.000    0.097
single   Extract           25      24       0         1     0.960     1.000    1.000
single   Filter2           25      24       1         0     0.980     1.000    1.000
single   Filter3           25      25       0         0     1.000     1.000    0.940
single   Ceiling           25      25       0         0     1.000     1.000    1.000
single   GraphRAG local    25      15       1         9     0.620     0.880    0.201
single   GraphRAG global   25       2       1        22     0.100     0.080    0.005

cross    Vector k=5        25      15       5         5     0.700     0.440    0.411
cross    Vector k=10       25      19       4         2     0.840     0.680    0.274
cross    Vector-line k=5   25      10      10         5     0.600     0.320    0.409
cross    Vector-line k=10  25      16       7         2     0.780     0.560    0.305
cross    V-hybrid k=5      25      15       9         1     0.780     0.520    0.369
cross    V-hybrid k=10     25      19       5         1     0.860     0.800    0.245
cross    Hybrid k=5        25      19       5         1     0.860     0.600    0.325
cross    Hybrid k=8        25      22       2         1     0.920     0.800    0.242
cross    Hybrid k=10       25      23       2         0     0.960     0.840    0.211
cross    Extract           25      15       5         5     0.700     0.480    0.686
cross    Filter2           25      12       6         7     0.600     0.200    0.617
cross    Filter3           25      20       3         2     0.860     0.760    0.611
cross    Ceiling           25      24       1         0     0.980     1.000    1.000
cross    GraphRAG local    25      13       9         3     0.700     0.840    0.069
cross    GraphRAG global   25       3       6        16     0.240     0.360    0.053
```

The sweep's prediction holds: deepening retrieval lifts the cross-reference
score from 0.700 to 0.840 (incorrect 5→2), and single-passage saturates to
1.00. Chapter recall rises (cross 0.44→0.68) at the cost of precision
(0.41→0.27) — more context, looser filtering — yet **accuracy rises**, so the
extra context helps more than it distracts. Vector k=10 overtakes Extract on
accuracy (0.92 vs 0.83) while Extract still leads sharply on chapter precision
(0.84).

**Hybrid** (dense ∪ BM25 union) becomes the top retrieval method: Hybrid k=10
at 0.960 overtakes Filter3 (0.930) by recovering the three lexically-distinctive
cross-reference chapters that dense-only search cannot rank (Q31, Q43, Q49 —
the Class A cases from [§ Both wrong](#both-wrong-what-k10-cannot-fix)). The
cross-reference score rises from 0.840 to 0.960 (incorrect 2→0). Hybrid k=8
(0.940) recovers all three Class A chapters and lifts cross to 0.920, sitting
between k=5 (0.910) and k=10 (0.960). Single-passage does *not* saturate to 1.00
under any Hybrid depth — all three land at 24/25 — because the wider union context
occasionally confuses synthesis on single-passage questions.

The **Filter** rows use the LLM as retriever rather than dense embeddings:
Filter3 posts 0.930, Filter2 0.790. The `maybe`-verdict mechanism, cost/gold-floor
analysis, and verdict that finds no retrieval advantage over Vector k=10 are in
[FILTER.md](../FILTER.md).

## Extract vs Vector k=10: where each method loses

The Headline's five-question margin is the whole story of "k=10 beats Extract,"
so [`report.py`](../README.md#reportpy)
breaks it open into its per-question causes — and it lands squarely on Extract's
two-stage filter. The disagreement pass prints three pairwise matrices (Vector k=5×Vector k=10,
Vector k=5×Extract, Vector k=10×Extract); the decisive one is the last:

```
Agreement matrix (rows = Vector k=10, cols = Extract):
                  Extract:correct  Extract:partial  Extract:incorrect | Vector k=10 total
Vector k=10:correct                36               4                  4  | 44
Vector k=10:partial                 1               1                  2  |  4
Vector k=10:incorrect               2               0                  0  |  2
Extract total                      39               5                  6  | 50
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
| Vector k=10 beats Extract | 10 | **7** (Phase 1 FN) | 3 |
| Extract beats Vector k=10 | 3 | 3 (retrieval miss) | 0 |

**Seven of Extract's ten losses are Phase 1 false negatives** (Q26, Q28, Q34,
Q40, Q42, Q48, Q50) — the gold chapter a stage-1 `None` dropped, so stage 2
never saw it. The filter, not the synthesis, is where the gap lives. Three are
total wipeouts: Q42 (`expanded` empty — all of Ch22/23/29 dropped), Q34 (only
Ch2 kept, all of Ch30/31/33 dropped), and Q26 (used Ch15/30, disjoint from gold
Ch11/29). The remaining three losses (Q22, Q30, Q33) are genuine synthesis slips
where Extract held every gold chapter — the same single-passage inversion and
half-answers the [k=5 study](#k5-baseline-in-brief) flagged.

**Every one of Extract's wins is a retrieval miss Vector cannot fix.** Q31, Q43,
Q49 are the [Class A](#both-wrong-what-k10-cannot-fix) chapters dense embedding
ranks outside the top-10 at both depths — Extract's per-chapter reading finds
them, Vector k=10 never does. Extract never beats Vector k=10 on synthesis.

So the two architectures fail on **orthogonal axes**, and that is the read on
the 0.92 vs 0.83 margin: Extract's losses are self-inflicted by its own Phase 1
filter (cheaply fixable — keep more context, weaken the `None` bar, or quote
verbatim instead of summarize-or-discard), whereas Vector's losses are structural
dense-retrieval blindness (the BM25/lexical hybrid in [HYBRID.md](../HYBRID.md)).
Fixing Phase 1 alone lifts Extract toward a 39+7 = 46 ceiling — re-overtaking
k=10 — while its thorough-reading edge on the vector-unreachable three stays
intact. The lever for Extract is in its own stage 1; the lever for Vector is
hybrid retrieval.

## k=5 baseline, in brief

(This condenses the earlier Vector-vs-Extract disagreement study; the per-question
detail is redeployed in the k=10 analysis below.) Vector k=5 and Extract tie at
0.830 but split on **which** cross questions each solves. The single/cross
split dominates everything: both score 24–25/25 on single-passage and 15/25 on
cross.

**Agreement matrix (k=5 Vector × Extract)** — now reproduced verbatim by the
`Vector k=5 × Extract` block of `report.py`'s disagreement pass:

| | Ext correct | Ext partial | Ext incorrect | Vector total |
| --- | --- | --- | --- | --- |
| **Vector correct** | 31 | 4 | 4 | 39 |
| **Vector partial** | 3 | 1 | 1 | 5 |
| **Vector incorrect** | 5 | 0 | 1 | 6 |

Two failure modes account for almost every off-diagonal loss:

- **Vector k=5's losses are mostly top-5 retrieval misses** — a gold chapter ranks
  just outside `k=5` (the +0.00–0.07 gaps `sweep_vector.py` flagged). Two exceptions
  (Q21, Q29) are *answering* slips where the gold chapter was already in context.
- **Extract's losses are Phase 1 false negatives** — a wrong `None` on a gold
  chapter drops it unrecoverably (Q26, Q34, Q42 dropped gold chapters entirely).
  A secondary loss is Phase 2 synthesis (Q30, Q33 held every gold chapter yet
  only half-answered); and one single-passage inversion (Q22).

**The gold is sound.** On Q29 (the covert poisoning behind the surface exile
decree), both Extract and Vector k=10 independently reconstruct the covert chain
the gold describes — two thorough paths agreeing with the gold is convergent
evidence it is correct, and Vector k=5's loss there is an answering failure, not a
gold problem.

## What changes at k=10

Twelve questions are not-correct in at least one of k=5 / k=10. Their movement
(`k=10 retrieval` = gold chapters newly pulled into context vs. k=5):

| Q | type | gold | k=5 | k=10 | k=10 retrieval | class |
| --- | --- | --- | --- | --- | --- | --- |
| 21 | single | 5 | incorrect | **correct** | — (Ch5 already in k=5) | answering fix |
| 27 | cross | 2,4,33 | partial | **correct** | +Ch33 | retrieval fix |
| 28 | cross | 9,37 | incorrect | **correct** | +Ch9, +Ch37 | retrieval fix |
| 29 | cross | 16,17 | incorrect | **correct** | — (both already in k=5) | answering fix |
| 36 | cross | 1,17,21 | incorrect | **correct** | +Ch17 | retrieval fix |
| 45 | cross | 18,25 | partial | **correct** | +Ch18 | retrieval fix |
| 34 | cross | 30,31,33 | correct | **partial** | — (same chapters as k=5) | **regression** |
| 31 | cross | 21,22,23 | incorrect | incorrect | +Ch23, but Ch21/22 still out | both wrong |
| 32 | cross | 11,15,16 | partial | partial | Ch15 still out | both wrong |
| 43 | cross | 11,37 | partial | partial | Ch37 still out | both wrong |
| 48 | cross | 11,19 | partial | partial | Ch11 still out | both wrong |
| 49 | cross | 2,22 | incorrect | incorrect | Ch22 still out | both wrong |

### The six fixes

Two flavors, matching the k=5 failure-mode split:

- **Retrieval fixes (Q27, Q28, Q36, Q45).** A gold chapter that ranked just
  outside k=5 enters the top-10 — exactly the "gap +0.00–0.07" cases
  `sweep_vector.py` predicted: Ch33 (Q27), Ch9+Ch37 (Q28), Ch17 (Q36), Ch18 (Q45).
- **Answering fixes (Q21, Q29).** The gold chapter was *already* in k=5's
  context; k=10's broader supporting context let the answerer synthesize the
  right answer. Q21 (Ch5 present at both depths — k=5 cited the wrong incident,
  k=10 named both offenses); Q29 (Ch16+17 present at both — k=5 stopped at the
  surface exile decree, k=10 gave the covert poisoning). These are precisely the
  two k=5 losses `sweep_vector.py` could *not* have explained by retrieval alone.

### The one regression: Q34

Q34 (gold 30,31,33) goes correct→partial despite identical gold-chapter
coverage (Ch30+33 at both depths). With more surrounding context at k=10, the
answerer misstated the causal mechanism — crediting a "pre-existing order"
Udayaditya explained, rather than Rukmini going to court to accuse Basanta Ray.
This is the one place larger context *hurt* synthesis (a mild "lost in the
middle" effect), though Q34 is genuinely hard: Extract scores it incorrect too.
The net trade is overwhelmingly positive — six fixes for one regression.

## Both wrong: what k=10 cannot fix

Five questions stay not-correct at both depths (Q31, Q32, Q43, Q48, Q49) — all
cross-reference. The decisive cross-check is what **Extract**, reading every
chapter independently, makes of them:

| Q | gold | load-bearing chapter vector search misses | Vector k=5 | Vector k=10 | Hybrid k=8 | Hybrid k=10 | Extract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | 21,22,23 | Ch21,22 — the ring gift and the seal-forgery | incorrect | incorrect | **correct** | **correct** | **correct** |
| 43 | 11,37 | Ch37 — the Chandradwip palanquin extraction | partial | partial | **correct** | **correct** | **correct** |
| 49 | 2,22 | Ch22 — the forged petition to the Emperor of Delhi | incorrect | incorrect | **correct** | **correct** | **correct** |
| 32 | 11,15,16 | Ch15 — the secret stipend to the dismissed guards | partial | partial | partial | partial | partial |
| 48 | 11,19 | (Ch19 *is* retrieved; the paranoid detail is misread) | partial | partial | partial | partial | incorrect |

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

**Hybrid k=8 and k=10 recover all three.** The BM25 component ranks Ch21/22 (Q31),
Ch37 (Q43), and Ch22 (Q49) high enough to enter the union top-k — confirming
that the failure was lexical invisibility, not gold ambiguity. See
[§ Hybrid](#hybrid-dense--bm25-union) for the per-question breakdown.

### Class B — failures shared with Extract (Q32, Q48)

The remaining two are not-correct for **all three methods**, so deeper
retrieval cannot be the lever:

- **Q32** (gold 11,15,16) — the gold's load-bearing middle step is the *secret
  monthly stipend* Udayaditya and Surma pay the dismissed guards, which
  Pratapaditya discovers. Ch15 never ranks in the top-10 for either Vector depth,
  and Extract's per-chapter extraction misses the stipend too, attributing the
  exile to vague "psychological tactics." All three land on partial. The causal
  detail is genuinely subtle and lives in a chapter none of the methods weighs
  heavily.
- **Q48** (gold 11,19) — the gold's key fact is Ramchandra's *paranoid* reading
  of Udayaditya whispering to a servant as an insult plot. Ch19 (which contains
  it) *is* retrieved by both Vector depths, yet both answerers — and Extract,
  reading it in full — misread it as Ramchandra thinking Udayaditya acted "for
  his sister's sake." Three independent paths converge on the same wrong
  reading, which points to an answering-model limitation (and possibly a gold
  that over-weights a fleeting detail), not retrieval. Ceiling
  ([§ below](#ceiling-the-perfect-retrieval-upper-bound)) confirms this
  decisively: with Ch11+19 verbatim in context it still lands partial — the
  same misreading, now with zero retrieval noise.

Class B is the true residual: no `k` or hybrid fixes it. It needs a better
reader, sharper extraction, or a second look at the gold.

## Hybrid (dense ∪ BM25 union)

The union approach from [HYBRID.md](../HYBRID.md) converts the strict-recall
retrieval gain into answer accuracy. At k=10, it achieves the top retrieval
accuracy of **0.960** (with k=8 at **0.940**), recovering the Class A chapters
that dense-only search cannot reach.

### Hybrid k=5 vs Vector k=10

Hybrid k=5 (0.910) sits just below Vector k=10 (0.920) overall, but the two
methods win on **orthogonal questions**:

| direction | n | questions | class |
| --- | --- | --- | --- |
| Hybrid k=5 beats Vector k=10 | 3 | Q31 (Ch21/22, Class A), Q34 (Ch31), Q49 (Ch22, Class A) | all missed-context |
| Vector k=10 beats Hybrid k=5 | 4 | Q17 (synthesis), Q27 (Ch33), Q28 (Ch9), Q50 (Ch23) | 3 missed-context, 1 synthesis |

The three Hybrid k=5 wins are all retrieval fixes — BM25's lexical signal surfaces
chapters that dense embedding ranks outside the top-10. Q31 and Q49 are Class A:
Ch21/22 (ring-gift / seal-forgery chain) and Ch22 (forged Delhi petition), both
lexically distinctive but semantically generic. On cross-reference, Hybrid k=5
(0.860) actually edges Vector k=10 (0.840) — it is the single-passage regression
(Q17, synthesis — the wider union context confuses the answerer on a single-chapter
question) that costs it overall.

### Hybrid k=10 recovers the Class A frontier

At k=10 the union closes the Class A gap entirely. The four questions where
Hybrid k=10 beats Vector k=10 are all missed-context:

| Q | gold | dropped by Vector k=10 | why BM25 recovers it |
| --- | --- | --- | --- |
| Q31 | 21,22,23 | Ch21, Ch22 | "signet ring", "seal" — low-semantic, high-lexical |
| Q34 | 30,31,33 | Ch31 | partial recovery: Ch31 enters BM25 top-k |
| Q43 | 11,37 | Ch37 | "Chandradwip palanquin" — proper-noun-heavy |
| Q49 | 2,22 | Ch22 | "Emperor of Delhi", "forged petition" |

Vector k=10 beats Hybrid k=10 on only **one** question: Q22 (gold Ch11,
single-passage), where the larger union context triggers a "lost in the middle"
synthesis regression. This is the trade-off HYBRID.md predicted — the ~1.4×
larger context occasionally confuses synthesis even when the gold chapter is
present. Note that Hybrid k=5 and k=8 get Q22 right; the regression is introduced by the
additional scenes at k=10.

### Hybrid k=8: Performance and Trade-offs

Expanding the retrieval depth to `k=8` yields a weighted score of **46/50 (0.940)**, sitting directly between `k=5` (**0.910**) and `k=10` (**0.960**). 

- **Retrieval Gains over k=5:** Deepening the search to `k=8` expands the retrieved context sufficiently to recover the missing gold chapters for **Q27** (Ch33), **Q28** (Ch9), **Q43** (Ch37), and **Q50** (Ch23), upgrading all of them from partial/incorrect to correct. While it suffers a single synthesis regression on **Q29** (dropping from correct at `k=5` to incorrect), it nets a +3 correct answer gain.
- **Comparison to k=10:** Unlike Japanese, where context dilution at `k=10` offsets retrieval gains and pulls the overall score down to `0.920` (below `k=8`'s `0.940`), English shows greater synthesis resilience. Moving from `k=8` to `k=10` retrieves no new missing contexts (both share identical performance on the missed-context questions above), but `k=10` recovers the regression on **Q29** and improves **Q17** to correct. Although `k=10` triggers the regression on **Q22** (which `k=8` gets correct), it still nets +1 correct answer overall (**47/50** vs. **46/50**), confirming that English LLM synthesis handles the larger context at `k=10` (~25 scenes) successfully.

### The two-question residual

Ceiling beats Hybrid k=10 on just two questions:

- **Q22 (synthesis)** — the union's extra context triggers an incorrect answer on
  this single-passage question; Ceiling, with *only* the gold chapter, reads it
  correctly.
- **Q32 (missed context)** — Ch15 (the secret stipend detail) is outside both
  retrievers' top-k at k=10 and remains a Class B unreachable.

These two together pin Hybrid k=10's residual: one precision problem (the union
is too wide for a single-passage question), one shared blind spot no retrieval
blend fixes.

## Vector-line (line-level retrieval)

`Vector-line` keeps the dense pipeline but shrinks the retrieval unit from a
scene to a **single line**: [`build_index.py --line`](../README.md#build_indexpy)
embeds one vector per non-blank line, and
[`answer_vector.py --line`](../README.md#answer_vectorpy) ranks lines, then
resolves each hit line back to its containing segment before the same ±N
expansion and answering. The question is whether a finer unit — matching the one
sentence that answers the question, rather than diluting it across a whole scene
— retrieves better.

It does not, on balance. The headline is **0.800 (k=5) / 0.890 (k=10)**, below
segment Vector's 0.830 / 0.920 at both depths. The line unit does exactly what
finer granularity should — it lifts **chapter precision** (k=5 0.337→0.401, k=10
0.205→0.274, the highest of any dense method) and **saturates single-passage to
1.000 at both depths**, beating segment k=5's 0.960. But it lowers **chapter
recall** (k=5 0.720→0.660, k=10 0.840→0.780), and the entire deficit is
cross-reference: cross drops to 0.600 (k=5) and 0.780 (k=10).

### Why cross-reference suffers

Every Vector-line loss against segment Vector is a **missed-context** retrieval
miss — never a synthesis slip:

| direction | n | missed-context | synthesis |
| --- | --- | --- | --- |
| Vector k=5 beats Vector-line k=5 | 8 | 8 | 0 |
| Vector-line k=5 beats Vector k=5 | 5 | 3 | 2 |
| Vector k=10 beats Vector-line k=10 | 5 | 5 | 0 |
| Vector-line k=10 beats Vector k=10 | 2 | 2 | 0 |

The mechanism is the flip side of the precision gain. When a gold chapter's
relevance is carried by **one distinctive line**, the line unit surfaces it
cleanly; but when the relevant content is **diffuse across a scene**, no single
line accumulates enough similarity to crack the top-k, whereas the scene-level
average still ranks. Cross-reference questions lean on the diffuse case, so they
lose the most (e.g. Q26 Ch11/29, Q40 Ch13/27, Q42 Ch23/29 — all dropped by
Vector-line k=5 but held by segment k=5).

### The misses are orthogonal

Crucially, Vector-line is not strictly worse retrieval — it has its **own** wins
that segment search drops. At k=10 it recovers **Q34 (Ch31)** and **Q49 (Ch22)**
— the latter a [Class A](#both-wrong-what-k10-cannot-fix) chapter (the forged
Delhi petition) that dense *segment* search misses at both depths, here surfaced
because one lexically sharp line ranks where the averaged scene did not. At k=5
it additionally fixes Q21/Q29 by synthesis and Q28/Q45 by retrieval. So line and
segment granularity fail on **orthogonal chapters** — the same dense-vs-lexical
tension [Hybrid](#hybrid-dense--bm25-union) exploits, in miniature — but the line
unit drops more cross chapters than it recovers, so the net is negative and
segment-level retrieval stays the stronger dense baseline.

### Depth still helps

Like segment Vector, deepening k=5→k=10 is a pure retrieval gain: Vector-line
k=10 beats k=5 on 7 questions, **all missed-context**, against a single
regression (Q50, Ch23). The k=5 unit is simply too tight for cross-reference —
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

It scores **0.890 (k=5) / 0.910 (k=10)** — above plain Vector k=5 (0.830) and
Vector-line (0.800 / 0.890), below segment Vector k=10 (0.920) and the dense∪BM25
Hybrid (0.910 / 0.960). The most striking column is `incorrect`: V-hybrid k=5
has just **1** (vs Vector k=5's 6, Vector-line k=5's 5), with 9 partials. The
union surfaces so many gold chapters that almost nothing is fully missed — chapter
recall on cross-reference reaches **0.800 at k=10** (vs Vector k=10's 0.680) —
but the recovered chapters convert to *partial* more often than *correct*: the
right chapter is present, yet the wider context dilutes synthesis.

### Two ceilings it does not break

The disagreement pass pins why V-hybrid lands between Vector k=10 and Hybrid:

- **vs segment Vector k=10 (loses by 1).** V-hybrid k=10 beats Vector k=10 on one
  question (a missed-context recovery) but loses two — both **synthesis**, where
  the ~1.4× larger union context makes the answerer lose a chapter it already
  had. This is exactly the "lost in the middle" cost
  [VECTOR-HYBRID.md](../VECTOR-HYBRID.md) flagged: the retrieval gain is real, but
  net answer accuracy dips slightly because synthesis pays for the extra context.
- **vs dense∪BM25 Hybrid k=10 (loses 4–0).** Hybrid strictly dominates: it wins
  four questions (two missed-context, two synthesis), V-hybrid wins none. The two
  missed-context losses are the [Class A](#both-wrong-what-k10-cannot-fix)
  chapters — Q31 Ch21/22, Q43 Ch37 — that dense embedding cannot rank at *any*
  granularity because they are lexically distinctive but semantically generic.
  Unioning two dense granularities cannot reach them; only BM25's lexical signal
  does. **This is the ceiling of dense∪dense union**: it recovers chapters that
  differ by granularity, but not chapters that are dense-blind.

So in English V-hybrid is a clean, parameter-free dense-only retriever with the
lowest incorrect rate of any Vector variant, yet it sits below both segment
Vector k=10 (synthesis cost) and the lexical Hybrid (dense-blind Class A
chapters). The matched-budget reading makes this sharper: V-hybrid k=5 pools
`seg5 ∪ line5`, a ~k=10 segment context, so its real baseline is Vector k=10
(0.920) — which it trails. **Japanese confirms the pattern rather than reversing
it:** there V-hybrid k=5 only *ties* plain Vector k=10 (both 0.890), never beating
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
than a gold one. Its residual losses are confident-wrong-`no` wipeouts (Q34,
Q42, and the Class B Q32), the same chapters Extract also drops. The `maybe`
verdict is the lever — the strict two-level Filter2 (keep only `yes`) falls to
0.790, below Extract — but the gold-floor and cost analysis in FILTER.md finds
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

### No method beats Ceiling

Ceiling wins or ties on every question against every method — never the
reverse. Its margin over each is the pure cost of that method's retrieval,
and the gradient tracks retrieval quality exactly:

| method | method score | Ceiling beats it on | missed-context | synthesis |
| --- | --- | --- | --- | --- |
| Filter2 | 0.790 | 14 | 13 | 1 |
| Extract | 0.830 | 11 | 8 | 3 |
| Vector k=5 | 0.830 | 10 | 8 | 2 |
| Hybrid k=5 | 0.910 | 6 | 5 | 1 |
| Vector k=10 | 0.920 | 5 | 5 | 0 |
| Filter3 | 0.930 | 4 | 3 | 1 |
| Hybrid k=10 | 0.960 | 2 | 1 | 1 |

The count shrinks monotonically with accuracy: the better the retrieval, the
fewer questions separate it from the ceiling. **Hybrid k=10 — the top-scoring
retrieval method — sits just two questions below Ceiling**; Filter3 sits four.

### The four-question gap to Filter3

Filter3 is the closest per-chapter method gets to Ceiling. Its four losses pin
down what classifier-based retrieval still cannot fix:

- **Q32, Q34, Q42 (missed-context)** — the confident-wrong-`no` wipeouts
  (see [FILTER.md](../FILTER.md#failure-mode)).
  Every gold chapter was marked `no`, so Phase 2 saw nothing. These are the
  same questions Extract drops too (two different classifiers, each reading
  the full chapter, independently decide they are irrelevant), and Ceiling
  recovers all three — confirming the gold chapters *do* contain the answer.
  No threshold trick fixes them: the model never hesitated (`no`, not
  `maybe`), so the `maybe` rescue cannot reach.
- **Q37 (synthesis)** — Filter3 held every gold chapter (1, 34) yet still
  half-answered. Ceiling, with the same chapters but *only* those chapters,
  got it correct. The likely cause is noise: Filter3's context also carried
  non-gold chapters that diluted the signal — a precision effect that
  Ceiling's clean gold-only context avoids by construction.

So of Filter3's four losses, three are classifier confidence (fixable only by a
better `no` bar) and one is context precision. None is a dense-retrieval
blindness case — Filter3's per-chapter reading already solved Q31, Q43, Q49, and
so does Hybrid k=10.

### Q48: the synthesis floor

Ceiling's lone loss — Q48 (gold 11,19), **partial** — is the single question
where even perfect context is not enough. The gold's key fact is Ramchandra's
*paranoid* reading of Udayaditya whispering to a servant as an insult plot,
and that passage is in Chapter 19 verbatim:

> he had seen Yubaraj Udayaditya whispering something to that servant — of
> course, they must have been plotting to insult him, what else could it be!

Yet the model, with this text directly in context, reads it as Ramchandra
believing Udayaditya acted "for his sister's sake" — the same misreading every
other method produces (see [§ Class B](#class-b--failures-shared-with-extract-q32-q48)).
Ceiling makes the diagnosis definitive: retrieval is perfect, the detail is
present, the model still mis-reads it. This is an answering-model
comprehension limit — the floor that no retrieval fix can break through — and
possibly a gold that over-weights a fleeting detail.

### What Ceiling confirms

- **The single-passage axis is solved.** Single-passage saturates to 1.000
  under Ceiling, Filter3, and Vector k=10 — any method with perfect single-chapter
  recall reads a single chapter perfectly. The entire frontier is
  cross-reference.
- **The accuracy gap between methods traces entirely to retrieval.** Ceiling's
  context is identical in shape to Filter3's Phase 2 (full chapter text, same
  prompt, same model); the only difference is *which* chapters — Ceiling's are
  perfect, Filter3's are classifier-selected. So Ceiling's 0.990 vs Filter3's
  0.930 is a clean measure of what Filter3's three confident-wrong-`no`
  wipeouts cost.
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

### GraphRAG local (0.660)

Local search posts 28/50 (0.660) — below Filter2 (0.790) and far below Hybrid
k=10 (0.960). The chapter-retrieval numbers tell the story: **recall 0.860,
precision 0.135** (the lowest of any non-global method). Entity-graph expansion
tends to pull in nearly all 37 chapters as expanded context, so gold chapters
are almost always present — but the answerer is forced to synthesize from an
overloaded context with minimal signal-to-noise.

The failure mode is therefore **synthesis-dominated**. Of GraphRAG local's 21
losses to Ceiling, **16 are synthesis** (the gold chapter is present but the
answer is wrong or vague) and only 5 are missed context. This is the inverse of
Vector k=5 (where most losses are retrieval misses) and is structurally similar
to the "lost in the middle" effect: the right content is there, but buried under
noise. Hybrid k=10 keeps its context to the union top-k and avoids this;
GraphRAG local has no equivalent precision control.

The synthesis collapse is sharpest on **single-passage questions** (15/25,
0.620) — the category every retrieval method with adequate recall saturates to
≥24/25. GraphRAG local drops 9 of those 25 to incorrect (and 1 to partial),
producing the worst single-passage score of any method. On cross-reference it
matches Vector k=5 (13/25, 0.700) — the chapter-graph's entity links provide
no structural advantage when the bottleneck is synthesis over a noisy context.

GraphRAG local **never beats Hybrid k=10** on any question. Hybrid k=10 wins 19
questions against it (14 synthesis, 5 missed context); GraphRAG local wins 0.

### What GraphRAG local gets right

Despite the poor overall score, examining which questions GraphRAG local
answers correctly reveals a coherent pattern: it succeeds on questions whose
answers are encoded as **entity relationships or narrative arcs**, and fails on
questions requiring **specific microdetail from the raw text**.

**Pure graph traversal (0 chapters retrieved, yet correct).** Two cross-reference
questions — Q26 and Q28 — receive correct answers with `expanded=[]`: no chapter
text is retrieved at all. Q26 asks how the dynamic between Udayaditya and the
guard Sitaram *reverses* across two escapes; Q28 asks in what two locations and
disguises Ramai Bhand faces retaliation. Both turns on the *shape of a
relationship arc* — exactly what a knowledge graph's entity/relationship edges
encode. The graph answered without needing any passage context.

**Class A recovery (Q31, Q49).** The two Class A questions that every Vector
depth and Hybrid misses — Q31 (signet ring → seal forgery → imprisonment) and
Q49 (Emperor of Delhi → forged petition → imprisonment) — are answered correctly
by GraphRAG local (with 37 chapters retrieved). Dense embedding is lexically
blind to Ch21/22 and Ch22 because those chapters are semantically generic; BM25
recovers them via lexical matching. GraphRAG takes a third path: the
knowledge graph explicitly encodes the entity chain (ring → conspiracy →
imprisonment) as relationship edges, so local graph traversal reaches the answer
independently of chapter ranking. The same mechanism explains why Q26/Q28 need
zero chapters — entity chains suffice.

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
5/50 (0.170) — the lowest of any method by a wide margin — and the mechanism is
clear from the chapter-retrieval numbers: **recall 0.220, precision 0.029**.
Community summaries operate at the wrong granularity: they abstract away the
specific chapter details the questions turn on. Of the 45 questions where
Ceiling beats GraphRAG global, **37 are missed context** — the relevant textual
evidence is simply absent from the retrieved context, not merely mis-synthesized.

Single-passage (2/25, 0.100) is almost a complete failure: community-level
summaries cannot anchor a question to the specific scene where an event occurs.
Cross-reference (3/25, 0.240) fares slightly better because a handful of
prominent cross-cutting themes appear in the community summaries, but the score
is still far below every other method including Filter2 (0.600).

### Summary

Neither GraphRAG mode reaches the level of the simplest pipeline method (Vector
k=5, 0.830). The local mode's high recall does not translate to accuracy because
synthesis degrades over an overloaded context; the global mode's community
abstractions miss the passage-level details entirely. For a chapter-structured
novel QA task with specific factual questions, the flat embedding pipeline —
especially with the BM25 union — outperforms the knowledge-graph approach at a
fraction of the indexing cost (4 h+ for GraphRAG vs. minutes for the embedding
index).

## Takeaways

- **k=10 delivers the sweep's promise on cross-reference** (0.700→0.840),
  single saturates to 1.00, and Vector k=10 overtakes Extract on accuracy
  (0.92 vs 0.83). The win is broad — six questions fixed — at the cost of one
  synthesis regression (Q34) and lower chapter precision. (The Filter rows —
  Filter3 at 0.93, Filter2 at 0.79 — are analyzed in [FILTER.md](../FILTER.md).)
- **The 0.92 vs 0.83 margin is Extract's Phase 1 filter, not its synthesis —
  and Filter3 confirms the fix.** `report.py`'s disagreement pass shows 7 of
  Extract's 10 losses to k=10 are Phase 1 false negatives (a gold chapter
  dropped by a wrong `None`); only 3 are synthesis slips. The k=10 study
  predicted the lever was to *weaken Extract's `None` bar* (ceiling 39+7 = 46
  correct, re-overtaking k=10); Filter3 is that lever made real — keeping
  every chapter not marked `no` recovers 5 of those 7 Phase 1 false negatives
  (plus all 3 synthesis slips) and lands at 45 correct / 0.930 weighted, one
  shy of the 46 ceiling because Q34 and Q42 stay false negatives for Filter3
  too.
- **Half the k=5 losses were not retrieval problems.** Two fixes (Q21, Q29) had
  the gold chapter in context all along; k=10's extra context just yielded a
  better answer. Retrieval depth is not the only lever — answer synthesis
  improves with context too.
- **The dense-retrieval blindness frontier is closeable without per-chapter cost.**
  Of the five both-wrong questions, three (Q31, Q43, Q49) are solved by any method
  that reads the full chapter text — Extract, Filter3, and **Hybrid k=10** all get
  them correct. The chapter-question link is vector-unreachable at k≤10 but
  lexically distinctive; BM25 surfaces these chapters at k=10, making the union
  approach as effective as per-chapter reading for the Class A frontier at a
  fraction of the cost.
- **Hybrid k=10 (0.960) is the top retrieval method** and the closest to Ceiling
  among all methods. It translates the +4 retrieval recall from HYBRID.md into
  +3 correct answers over Vector k=10, with one synthesis regression (Q22) and one
  shared blind spot (Q32, Ch15). Single-passage does not saturate to 1.00 under
  Hybrid — the wider union context occasionally distracts on single-chapter
  questions — but on cross-reference Hybrid k=10 (0.960) is essentially at the
  cross Ceiling (0.980).
- **The `maybe` verdict is what makes the per-chapter filter work**, and its
  residual is a *confident* wrong `no` (Q32, Q34, Q42) that no threshold trick
  reaches — but the gold-floor and cost analysis still finds no retrieval
  advantage over Hybrid k=10. The full mechanism and verdict are in
  [FILTER.md](../FILTER.md).
- **Two questions are hard for every retrieval method** (Q32, Q48): all methods
  land partial/incorrect (and Q32 is partial for Hybrid k=10 too — Ch15 is outside
  the union's top-k at k=10). Ceiling disambiguates them — Q32 it gets *correct*
  (the detail is in Ch15 after all; the gold is sound, the other methods'
  failures are retrieval/extraction), while Q48 stays *partial* even with
  perfect context. Q48 alone is the true comprehension floor: the
  paranoid-detail passage is in Chapter 19 verbatim, yet the model
  mis-reads it the same way every time. It bounds what any retrieval fix can
  achieve.
- **Ceiling isolates the synthesis ceiling at 0.990.** With retrieval stripped
  out (gold chapters verbatim), the model mis-synthesizes exactly one question
  (Q48) and reads the other 49 correctly — including Q32, which every
  retrieval method gets partial. No method ever beats Ceiling; its margin over
  each (14/11/10/6/5/4/2 for
  Filter2/Extract/Vector k=5/Hybrid k=5/Vector k=10/Filter3/Hybrid k=10) shrinks
  monotonically with retrieval quality, tracing the entire accuracy gap to
  retrieval. Hybrid k=10 is within two questions — one synthesis regression and
  one shared blind spot — and neither is a classifier or depth problem. The
  retrieval frontier is effectively closed; what remains is one comprehension
  limit (Q48) and one chapter no blend of dense + BM25 can rank (Q32, Ch15).
- **The gold holds up.** Across every disagreement the failures trace to a
  method — never to the gold — and Ceiling confirms the two the other methods
  most often miss: Q31/Q43/Q49 (the vector-unreachable trio, all correct
  under Ceiling) and Q32 (the secret-stipend question, correct under Ceiling
  despite being partial for every retrieval method).
- **GraphRAG does not match the pipeline on this task overall, but reveals what
  graph structure can and cannot do.** Local search (0.660) falls below Filter2:
  entity-graph expansion overloads context (recall 0.860, precision 0.135) and
  16 of 21 losses to Ceiling are synthesis failures, not missed context. Yet it
  has a coherent strength — questions about *character relationship arcs and
  narrative causality* (e.g. Q26/Q28, answered with 0 chapters from pure graph
  traversal; Q31/Q49, the Class A cases that dense+BM25 also recovers via
  lexical matching, here recovered via entity chains). It fails on microdetail
  questions requiring specific text. Global search (0.170) is non-functional:
  community summaries are the wrong granularity (37 of 45 losses to Ceiling are
  missed context). Neither mode beats Hybrid k=10 on any question.
