# Retrieval-strategy case study: RAG depth and per-chapter reading

A per-question analysis of the retrieval strategies on the English question
set, complementing the aggregate table from
[`report.py`](../README.md#reportpy). The original thread follows what changes
when RAG's retrieval depth is bumped from `k=5` to `k=10` — motivated by
[`sweep_rag.py`](../README.md#sweep_ragpy), which found `k=5` tight for
cross-reference questions and predicted that `k≈10–15` would surface most
dropped gold chapters. **Per-Chapter Extract** — an independent thorough-reading
path — is kept as the convergent-validity baseline: where it agrees with the
gold, two independent readers confirm the answer. **Filter**, the third
strategy, is summarized at the end
([§ Filter](#filter-llm-as-retriever)) and analyzed in full in
[FILTER.md](../FILTER.md): a looser variant of Extract that reads the full text
of every chapter not marked `no`, which sidesteps the dense-retrieval blindness
the depth study cannot fix. **Ceiling** closes the study
([§ Ceiling](#ceiling-the-perfect-retrieval-upper-bound)): the gold chapters
fed verbatim as context, stripping out retrieval entirely to expose the
synthesis-only upper bound.

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 50 questions
(`questions-en.jsonl`, 25 single-passage + 25 cross-reference). RAG k=5 →
`rag.jsonl`; RAG k=10 → `rag-10.jsonl`; Filter2 → `filter2.jsonl`; Filter3 →
`filter3.jsonl`; Ceiling → `ceiling.jsonl`.

## Headline (`report.py`)

```
scope    method     n correct partial incorrect  weighted ch.recall  ch.prec
----------------------------------------------------------------------------
all      RAG k=5   50      39       5         6     0.830     0.720    0.337
all      RAG k=10  50      44       4         2     0.920     0.840    0.205
all      Extract   50      39       5         6     0.830     0.740    0.843
all      Filter2   50      36       7         7     0.790     0.600    0.808
all      Filter3   50      45       3         2     0.930     0.880    0.775
all      Ceiling   50      49       1         0     0.990     1.000    1.000

single   RAG k=5   25      24       0         1     0.960     1.000    0.263
single   RAG k=10  25      25       0         0     1.000     1.000    0.136
single   Extract   25      24       0         1     0.960     1.000    1.000
single   Filter2   25      24       1         0     0.980     1.000    1.000
single   Filter3   25      25       0         0     1.000     1.000    0.940
single   Ceiling   25      25       0         0     1.000     1.000    1.000

cross    RAG k=5   25      15       5         5     0.700     0.440    0.411
cross    RAG k=10  25      19       4         2     0.840     0.680    0.274
cross    Extract   25      15       5         5     0.700     0.480    0.686
cross    Filter2   25      12       6         7     0.600     0.200    0.617
cross    Filter3   25      20       3         2     0.860     0.760    0.611
cross    Ceiling   25      24       1         0     0.980     1.000    1.000
```

The sweep's prediction holds: deepening retrieval lifts the cross-reference
score from 0.700 to 0.840 (incorrect 5→2), and single-passage saturates to
1.00. Chapter recall rises (cross 0.44→0.68) at the cost of precision
(0.41→0.27) — more context, looser filtering — yet **accuracy rises**, so the
extra context helps more than it distracts. RAG k=10 overtakes Extract on
accuracy (0.92 vs 0.83) while Extract still leads sharply on chapter precision
(0.84).

The **Filter** rows use the LLM as retriever rather than dense embeddings:
Filter3 posts the table's top Phase 2 score (0.930), Filter2 the lowest among
the per-chapter methods (0.790). That spread, the `maybe`-verdict mechanism
behind it, and the cost/gold-floor verdict that finds no retrieval advantage
over RAG k=10 are all in [FILTER.md](../FILTER.md); this case study focuses on
the RAG-depth, Extract, and Ceiling comparison.

## Extract vs RAG k=10: where each method loses

The Headline's five-question margin is the whole story of "k=10 beats Extract,"
so [`report.py`](../README.md#reportpy)
breaks it open into its per-question causes — and it lands squarely on Extract's
two-stage filter. The disagreement pass prints three pairwise matrices (RAG×RAG-10,
RAG×Extract, RAG-10×Extract); the decisive one is the last:

```
Agreement matrix (rows = RAG-10, cols = Extract):
                  Extract:correct  Extract:partial  Extract:incorrect | RAG-10 total
RAG-10:correct                36               4                  4  | 44
RAG-10:partial                 1               1                  2  |  4
RAG-10:incorrect               2               0                  0  |  2
Extract total                 39               5                  6  | 50
```

For each off-diagonal question the disagreement pass asks whether the loser
actually held every gold chapter in context, then classes the loss:

- **missed context** — a gold chapter is absent from the loser's `expanded`. For
  Extract that is a **Phase 1 false negative** (a wrong `None` dropped it
  unrecoverably); for RAG a **retrieval miss** (the chapter ranked outside top-k).
- **synthesis** — the loser held every gold chapter yet still mis-synthesized.

The split is lopsided:

| direction | n | missed context | synthesis |
| --- | --- | --- | --- |
| RAG-10 beats Extract | 10 | **7** (Phase 1 FN) | 3 |
| Extract beats RAG-10 | 3 | 3 (retrieval miss) | 0 |

**Seven of Extract's ten losses are Phase 1 false negatives** (Q26, Q28, Q34,
Q40, Q42, Q48, Q50) — the gold chapter a stage-1 `None` dropped, so stage 2
never saw it. The filter, not the synthesis, is where the gap lives. Three are
total wipeouts: Q42 (`expanded` empty — all of Ch22/23/29 dropped), Q34 (only
Ch2 kept, all of Ch30/31/33 dropped), and Q26 (used Ch15/30, disjoint from gold
Ch11/29). The remaining three losses (Q22, Q30, Q33) are genuine synthesis slips
where Extract held every gold chapter — the same single-passage inversion and
half-answers the [k=5 study](#k5-baseline-in-brief) flagged.

**Every one of Extract's wins is a retrieval miss RAG cannot fix.** Q31, Q43,
Q49 are the [Class A](#both-wrong-what-k10-cannot-fix) chapters dense embedding
ranks outside the top-10 at both depths — Extract's per-chapter reading finds
them, RAG-10 never does. Extract never beats RAG-10 on synthesis.

So the two architectures fail on **orthogonal axes**, and that is the read on
the 0.92 vs 0.83 margin: Extract's losses are self-inflicted by its own Phase 1
filter (cheaply fixable — keep more context, weaken the `None` bar, or quote
verbatim instead of summarize-or-discard), whereas RAG's losses are structural
dense-retrieval blindness (the BM25/lexical hybrid in [PLAN.md](../PLAN.md)).
Fixing Phase 1 alone lifts Extract toward a 39+7 = 46 ceiling — re-overtaking
k=10 — while its thorough-reading edge on the vector-unreachable three stays
intact. The lever for Extract is in its own stage 1; the lever for RAG is
hybrid retrieval.

## k=5 baseline, in brief

(This condenses the earlier RAG-vs-Extract disagreement study; the per-question
detail is redeployed in the k=10 analysis below.) RAG k=5 and Extract tie at
0.830 but split on **which** cross questions each solves. The single/cross
split dominates everything: both score 24–25/25 on single-passage and 15/25 on
cross.

**Agreement matrix (k=5 RAG × Extract)** — now reproduced verbatim by the
`RAG × Extract` block of `report.py`'s disagreement pass:

| | Ext correct | Ext partial | Ext incorrect | RAG total |
| --- | --- | --- | --- | --- |
| **RAG correct** | 31 | 4 | 4 | 39 |
| **RAG partial** | 3 | 1 | 1 | 5 |
| **RAG incorrect** | 5 | 0 | 1 | 6 |

Two failure modes account for almost every off-diagonal loss:

- **RAG k=5's losses are mostly top-5 retrieval misses** — a gold chapter ranks
  just outside `k=5` (the +0.00–0.07 gaps `sweep_rag.py` flagged). Two exceptions
  (Q21, Q29) are *answering* slips where the gold chapter was already in context.
- **Extract's losses are Phase 1 false negatives** — a wrong `None` on a gold
  chapter drops it unrecoverably (Q26, Q34, Q42 dropped gold chapters entirely).
  A secondary loss is Phase 2 synthesis (Q30, Q33 held every gold chapter yet
  only half-answered); and one single-passage inversion (Q22).

**The gold is sound.** On Q29 (the covert poisoning behind the surface exile
decree), both Extract and RAG k=10 independently reconstruct the covert chain
the gold describes — two thorough paths agreeing with the gold is convergent
evidence it is correct, and RAG k=5's loss there is an answering failure, not a
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
  `sweep_rag.py` predicted: Ch33 (Q27), Ch9+Ch37 (Q28), Ch17 (Q36), Ch18 (Q45).
- **Answering fixes (Q21, Q29).** The gold chapter was *already* in k=5's
  context; k=10's broader supporting context let the answerer synthesize the
  right answer. Q21 (Ch5 present at both depths — k=5 cited the wrong incident,
  k=10 named both offenses); Q29 (Ch16+17 present at both — k=5 stopped at the
  surface exile decree, k=10 gave the covert poisoning). These are precisely the
  two k=5 losses `sweep_rag.py` could *not* have explained by retrieval alone.

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

| Q | gold | load-bearing chapter vector search misses | RAG k=5 | RAG k=10 | Extract |
| --- | --- | --- | --- | --- | --- |
| 31 | 21,22,23 | Ch21,22 — the ring gift and the seal-forgery | incorrect | incorrect | **correct** |
| 43 | 11,37 | Ch37 — the Chandradwip palanquin extraction | partial | partial | **correct** |
| 49 | 2,22 | Ch22 — the forged petition to the Emperor of Delhi | incorrect | incorrect | **correct** |
| 32 | 11,15,16 | Ch15 — the secret stipend to the dismissed guards | partial | partial | partial |
| 48 | 11,19 | (Ch19 *is* retrieved; the paranoid detail is misread) | partial | partial | incorrect |

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
neighbours. This is exactly the failure `sweep_rag.py`'s threshold table
predicted (best τ*≈0.50, F1 0.38) and the motivation for the **BM25/lexical
hybrid** in [PLAN.md](../PLAN.md): a lexical signal would match those
proper-noun/term-heavy queries where dense embedding is blind. Ch22 is the
standout — load-bearing for *two* of these questions (Q31 and Q49) and
resistant to retrieval in both.

### Class B — failures shared with Extract (Q32, Q48)

The remaining two are not-correct for **all three methods**, so deeper
retrieval cannot be the lever:

- **Q32** (gold 11,15,16) — the gold's load-bearing middle step is the *secret
  monthly stipend* Udayaditya and Surma pay the dismissed guards, which
  Pratapaditya discovers. Ch15 never ranks in the top-10 for either RAG depth,
  and Extract's per-chapter extraction misses the stipend too, attributing the
  exile to vague "psychological tactics." All three land on partial. The causal
  detail is genuinely subtle and lives in a chapter none of the methods weighs
  heavily.
- **Q48** (gold 11,19) — the gold's key fact is Ramchandra's *paranoid* reading
  of Udayaditya whispering to a servant as an insult plot. Ch19 (which contains
  it) *is* retrieved by both RAG depths, yet both answerers — and Extract,
  reading it in full — misread it as Ramchandra thinking Udayaditya acted "for
  his sister's sake." Three independent paths converge on the same wrong
  reading, which points to an answering-model limitation (and possibly a gold
  that over-weights a fleeting detail), not retrieval. Ceiling
  ([§ below](#ceiling-the-perfect-retrieval-upper-bound)) confirms this
  decisively: with Ch11+19 verbatim in context it still lands partial — the
  same misreading, now with zero retrieval noise.

Class B is the true residual: no `k` or hybrid fixes it. It needs a better
reader, sharper extraction, or a second look at the gold.

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
no retrieval advantage over RAG k=10. The Ceiling comparison below uses Filter3
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
| RAG k=5 | 0.830 | 10 | 8 | 2 |
| RAG k=10 | 0.920 | 5 | 5 | 0 |
| Filter3 | 0.930 | 4 | 3 | 1 |

The count shrinks monotonically with accuracy: the better the retrieval, the
fewer questions separate it from the ceiling. Filter3 — the top-scoring
retrieval method — sits just four questions below, and those four are the
entire remaining retrieval frontier (below).

### The four-question gap to Filter3

Filter3 is the closest any retrieval method gets to Ceiling, so its four
losses pin down exactly what retrieval still cannot fix:

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

So of the four questions separating the best retrieval method from perfect
retrieval, three are classifier confidence (fixable only by a better `no`
bar) and one is context precision. None is a dense-retrieval blindness case —
Filter3's per-chapter reading already solved those (Q31, Q43, Q49).

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
  under Ceiling, Filter3, and RAG k=10 — any method with perfect single-chapter
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

## Takeaways

- **k=10 delivers the sweep's promise on cross-reference** (0.700→0.840),
  single saturates to 1.00, and RAG k=10 overtakes Extract on accuracy
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
- **The dense-retrieval blindness frontier is closeable per-chapter.** Of the
  five both-wrong questions, three (Q31, Q43, Q49) are solved by a thorough
  reading the vector retriever cannot do — Extract gets them, and so does
  Filter3. The chapter-question link is vector-unreachable at k≤10 but
  lexically distinctive, so the BM25/lexical hybrid in PLAN.md and the
  per-chapter reading of Extract/Filter3 both recover it. RAG's loss there is
  structural to dense embedding, not to depth.
- **The `maybe` verdict is what makes the per-chapter filter work**, and its
  residual is a *confident* wrong `no` (Q32, Q34, Q42) that no threshold trick
  reaches — but the gold-floor and cost analysis still finds no retrieval
  advantage over RAG k=10. The full mechanism and verdict are in
  [FILTER.md](../FILTER.md).
- **Two questions are hard for every retrieval method** (Q32, Q48): all five
  land partial/incorrect. Ceiling disambiguates them — Q32 it gets *correct*
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
  each (14/11/10/5/4 for Filter2/Extract/RAG-5/RAG-10/Filter3) shrinks
  monotonically with retrieval quality, tracing the entire accuracy gap to
  retrieval. Filter3 is within four questions — three confident-wrong-`no`
  wipeouts and one precision-driven synthesis slip — and none of the four is a
  dense-retrieval case. The retrieval frontier, in other words, is closeable;
  what remains is classifier confidence and one comprehension limit.
- **The gold holds up.** Across every disagreement the failures trace to a
  method — never to the gold — and Ceiling confirms the two the other methods
  most often miss: Q31/Q43/Q49 (the vector-unreachable trio, all correct
  under Ceiling) and Q32 (the secret-stipend question, correct under Ceiling
  despite being partial for every retrieval method).
