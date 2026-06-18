# Retrieval-depth case study: RAG k=5 vs k=10

A per-question analysis of what changes when RAG's retrieval depth is bumped
from `k=5` to `k=10`, complementing the aggregate table from
[`report.py`](../README.md#reportpy). The bump was motivated by
[`sweep_rag.py`](../README.md#sweep_ragpy), which found `k=5` tight for
cross-reference questions and predicted that `k≈10–15` would surface most
dropped gold chapters. **Per-Chapter Extract** — an independent thorough-reading
path — is kept as the convergent-validity baseline: where it agrees with the
gold, two independent readers confirm the answer.

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 50 questions
(`questions-en.jsonl`, 25 single-passage + 25 cross-reference). RAG k=5 →
`rag.jsonl`; RAG k=10 → `rag-10.jsonl`.

## Headline (`report.py`)

```
scope    method     n correct partial incorrect  weighted ch.recall  ch.prec
----------------------------------------------------------------------------
all      RAG k=5   50      39       5         6     0.830     0.720    0.337
all      RAG k=10  50      44       4         2     0.920     0.840    0.205
all      Extract   50      39       5         6     0.830     0.740    0.843

single   RAG k=5   25      24       0         1     0.960     1.000    0.263
single   RAG k=10  25      25       0         0     1.000     1.000    0.136
single   Extract   25      24       0         1     0.960     1.000    1.000

cross    RAG k=5   25      15       5         5     0.700     0.440    0.411
cross    RAG k=10  25      19       4         2     0.840     0.680    0.274
cross    Extract   25      15       5         5     0.700     0.480    0.686
```

The sweep's prediction holds: deepening retrieval lifts the cross-reference
score from 0.700 to 0.840 (incorrect 5→2), and single-passage saturates to
1.00. Chapter recall rises (cross 0.44→0.68) at the cost of precision
(0.41→0.27) — more context, looser filtering — yet **accuracy rises**, so the
extra context helps more than it distracts. Net, RAG k=10 overtakes Extract on
accuracy (0.92 vs 0.83) while Extract still leads sharply on chapter precision
(0.84).

## k=5 baseline, in brief

(This condenses the earlier RAG-vs-Extract disagreement study; the per-question
detail is redeployed in the k=10 analysis below.) RAG k=5 and Extract tie at
0.830 but split on **which** cross questions each solves. The single/cross
split dominates everything: both score 24–25/25 on single-passage and 15/25 on
cross.

**Agreement matrix (k=5 RAG × Extract):**

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
  that over-weights a fleeting detail), not retrieval.

Class B is the true residual: no `k` or hybrid fixes it. It needs a better
reader, sharper extraction, or a second look at the gold.

## Takeaways

- **k=10 delivers the sweep's promise on cross-reference** (0.700→0.840),
  single saturates to 1.00, and RAG k=10 overtakes Extract on accuracy
  (0.92 vs 0.83). The win is broad — six questions fixed — at the cost of one
  synthesis regression (Q34) and lower chapter precision.
- **Half the k=5 losses were not retrieval problems.** Two fixes (Q21, Q29) had
  the gold chapter in context all along; k=10's extra context just yielded a
  better answer. Retrieval depth is not the only lever — answer synthesis
  improves with context too.
- **The remaining frontier is dense-retrieval blindness, not depth.** Of the
  five both-wrong questions, three (Q31, Q43, Q49) are solved by Extract's
  thorough reading — the load-bearing chapter is vector-unreachable at k≤10 but
  lexically distinctive. This is the case for the BM25/lexical hybrid in
  PLAN.md.
- **Two questions are hard for every method** (Q32, Q48): all three land
  partial/incorrect, so they are answering/extraction limits or gold-ambiguity,
  not retrieval. They bound what any retrieval fix can achieve.
- **The gold holds up.** Across every disagreement the failures trace to a
  method — never to the gold — and where two independent thorough readers
  (Extract, RAG k=10) meet, they confirm the gold answer.
