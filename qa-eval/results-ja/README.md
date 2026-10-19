# Disagreement case study: Vector vs. Extract (Japanese)

A manual, per-question analysis of where the two methods **disagree** on the
Japanese question set, to complement the aggregate table from
[`report.py`](../README.md#reportpy). The goal is to attribute each disagreement
to a concrete failure mode and, along the way, spot-check whether the gold
answers are sound. Read alongside the English study
([results-en/README.md](../results-en/README.md)); the cross-language comparison
is in §5.

Run: answers `google:gemma-4-31b-it`, judge Jev (`jev-1.14.0`, verdicts in
`jev/`, each question counted as its most probable verdict), 50 questions
(`questions-ja.jsonl`, 25 single-passage + 25 cross-reference). The answer model,
embedding model (`embeddinggemma`), and judge are all identical to the English
run, so any difference below is a language effect, not a model one. Jev's
Japanese verdicts have not been checked separately; where one below is called
a near tie, its two top probabilities are within about 0.1 of each other.

## Where the difficulty lives: single vs. cross

Vector and Extract both score 31/50 correct (weighted 0.750 vs. 0.770) — Extract
edges ahead on partial credit, as in the English run, where it leads by seven
correct (28/35). On the **single-passage** half Vector scores 23/25 and Extract
24/25; on the **cross-reference** half they drop to 8/25 and 7/25 (0.560
each). The three single-passage misses (Q21, Vector incorrect; Q23, both
partial) are *answering* failures with the correct passage in hand, not
retrieval failures. So single-passage QA is essentially solved by either method;
the open problem is multi-chapter integration — the same conclusion as the
English run.

## Verdict agreement matrix

Rows = Vector verdict, columns = Extract verdict.

| | Ext correct | Ext partial | Ext incorrect | Vector total |
| --- | --- | --- | --- | --- |
| **Vector correct** | 27 | 4 | 0 | 31 |
| **Vector partial** | 2 | 8 | 3 | 13 |
| **Vector incorrect** | 2 | 3 | 1 | 6 |
| **Ext total** | 31 | 15 | 4 | 50 |

The two off-diagonal blocks analyzed below:

- **Vector correct / Extract not correct** — 4 questions (§2): two Extract
  Phase 1 retrieval misses plus two where Extract held the gold chapters but
  fell short.
- **Extract correct / Vector not correct** — 4 questions (§3): one Vector
  retrieval miss and three where Vector retrieved the gold chapters but answered
  short.

**15** questions are not correct under *either* method (23, 27, 28, 29, 30, 32,
34, 36, 42, 43, 45, 46, 47, 48, 49); these are examined in §4. That is close to
the English run's 13 shared failures, and seven of them are the same questions;
the difference is the main cross-language divergence (§5): a
translation/question-specific reshuffling at near-constant total accuracy, not a
gold problem.

## 1. Gold validity spot-check (Q29)

Q29 — "Pratapaditya's official decree aims to separate Surma and Udayaditya by
sending her to her father's house; what *covert* action actually causes her
departure?" (gold chapters 16, 17). The gold answer: Surma dies after drinking a
poison brewed by the magician Mangala (Rukmini), to whom the Mahishi had
secretly sent the maid Matangini for a medicine to win Udayaditya's heart back
from his wife.

This gold is grounded in the Japanese source (`all/ja-gemini`): Ch17 opens with
Mangala preparing the poison — "一晩中、切ったり、浸したり、すり潰したり、混ぜ合わせ
たりしながら、呪文を唱えて毒を調合し続けた" (all night she cut, soaked, ground, and
mixed, chanting spells, brewing the poison). The surface decree (exile to the
father's house) versus the covert cause (poisoning) is exactly what the question
asks, and both are in the text.

The interesting divergence from English: in the English run Extract read Ch15–17
in full and reconstructed the poisoning, confirming the gold; here **both methods
answered wrong the same way** — they reported the *secret monthly stipend* that
Udayaditya and Surma paid the dismissed guards (which is the Q32 storyline)
instead of the poisoning. When two independent readers fail identically, the gold
is the natural suspect, so this is precisely the case worth checking — and the
source confirms the gold is sound. Both methods conflated two adjacent
cause-of-departure threads even with the gold chapters retrieved (Vector used 16,17;
Extract used 14–17) — the same model gets this right in English, so the
confusion is specific to the Japanese phrasing of the two threads. Every method
but Ceiling is incorrect here, and Ceiling only partial. A shared answering
failure, not a gold problem.

## 2. Vector correct / Extract not correct (4 questions)

| Q | type | gold ch | Extract used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 26 | cross | 11,29 | 11,30,31 | partial | Phase 1 miss (Ch29) |
| 39 | cross | 10,11 | 4,11 | partial | Phase 1 miss (Ch10) |
| 33 | cross | 27,28 | **27,28** | partial | synthesis (had the chapters) |
| 37 | cross | 1,34 | **1,30,34** | partial | near tie (had the chapters) |

### 2a. Phase 1 false negatives (Q26, Q39)

Extract makes a per-chapter binary call in Phase 1: extract the relevant passage,
or emit `None`. A wrong `None` is unrecoverable — that chapter never reaches Phase
2.

- **Q26** (gold 11,29) kept Ch11 but dropped Ch29, the night of Udayaditya's own
  escape. The answer keeps the reversal in outline (Sitaram's submission on the
  first night, his devoted help on the second) but not the events that define
  it, and adds a staged death to the second night. Vector retrieved both gold
  chapters and named both events: Sitaram letting himself be bound out of
  gratitude, then carrying the prince out of the burning prison.
- **Q39** (how Pratapaditya's attempt to trap Ramchandra Ray at the canal
  fails, gold 10,11) dropped Ch10. The answer describes the log barrier and how
  the boat was dragged over it, but no longer says that Pratapaditya ordered
  the canal blocked; Vector, holding both chapters, does, and is correct on a
  near tie (0.54).

### 2b. Phase 2 shortfalls (Q33, Q37)

Q33 (the song "私だけが、ただ一人残された", gold 27,28) is different: Phase 1 **kept
both gold chapters**, yet the answer was only partial. Vector correctly named both
contrasting singing contexts (alone at the Rajgarh sunset; to Bibha in Surma's
empty room at Jessore); Extract got the first but *invented* the second — a scene
where Khan Sahib asks after Basanta Ray, followed by an abrupt shift to a cheerful
song — missing the gold's discovery of death and shared grief. The chapters were
in hand; the answer model just synthesized the second half wrong.

Q37 (how Udayaditya's early lament over being crown prince ends in a formal
renunciation, gold 1,34) is the judge's boundary: both answers give the early
lament, the despair over Basanta Ray's death and the vow before Kali naming
Samaraditya heir. Vector is `correct` on a near tie (0.52 / 0.46), Extract
`partial` (0.66).

## 3. Extract correct / Vector not correct (4 questions)

| Q | type | gold ch | Vector used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 31 | cross | 21,22,23 | 25,27,33,34 | incorrect | retrieval miss (all gold) |
| 21 | single | 5 | **2,5,8,12** | incorrect | retrieved Ch5, wrong incident |
| 41 | cross | 5,20 | **1,5,15,20,21** | partial | retrieved gold, added a wrong detail |
| 44 | cross | 8,36,37 | **8,9,28,36,37** | partial | near tie (retrieved gold) |

### 3a. Vector retrieval miss (Q31)

- **Q31** (how the signet ring becomes evidence, gold 21–23) retrieved none of the
  three gold chapters and replied "提供されたコンテキストの中に、ウダヤディティヤの
  印章指輪に関する記述はありません." Extract, reading Ch21–22, reconstructed the
  ring→seal→forged-petition→Pratapaditya chain in full.

This is exactly the named-entity miss the English study traced to dense recall
(the signet ring) — it recurs in Japanese because the embedding model is the
same. The other named-entity misses of the English study (the Emperor of Delhi,
Muktiyar Khan, Q27/Q48/Q49) also recur, but Extract does not get them fully
right either, so they are in §4.

### 3b. Retrieval hit, short answer (21, 41, 44)

The other three Vector losses are *not* retrieval misses — the gold chapter was in the
context and the answer still fell short:

- **Q21** (single, gold Ch5): Vector retrieved Ch5 but answered with *different*
  offenses (guards failing to attend the prince; reporting his disappearance)
  instead of the two the question asks for (losing a letter; sending a man to
  Umesh Ray instead of going personally). Extract named both exactly. This is the
  one single-passage question Vector got incorrect, and — as in the English run — it
  is an answering failure, not a retrieval one.
- **Q41** (cross, gold 5,20): both describe Udayaditya's earlier courage on the
  people's behalf and his fearful retreat after Surma's death, but Vector adds
  that he paid a stipend to dismissed officials, which belongs to the Q32
  storyline; it lands `partial` on a near tie (0.47 / 0.51).
- **Q44** (cross, gold 8,36,37): both contrast Bibha's heavy jewellery at
  Jessore with her plain dress at Chandradwip. Extract adds that Ramchandra took
  her for a beggar, as the gold does; Vector says only that she looked like one,
  and lands `partial` on a near tie (0.49 / 0.50).

## 4. Both not correct (15 questions)

| Q | gold ch | Vector used | Vector | Extract used | Ext | shared failure |
| --- | --- | --- | --- | --- | --- | --- |
| 23 | 15 | 15,21,27,29,31 | partial | 15 | partial | both add an ulterior motive to the stated reason |
| 27 | 2,4,33 | 2,5,10,12,28 | partial | 2,4,5,33 | partial | Vector misses Ch33; Extract mixes a second failed plot into the first |
| 28 | 9,37 | 7,8,9,24 | partial | 9 | partial | only one of two locations found |
| 29 | 16,17 | 5,11,12,16,17 | incorrect | 14,15,16,17 | incorrect | wrong covert cause (stipend, not poison) |
| 30 | 23,24,36 | 9,23,36,37 | partial | 23,24,26,36 | partial | remarriage named, arrival on the wedding day missing |
| 32 | 11,15,16 | 9,10,11,12,24 | incorrect | 12,14 | partial | missed the secret-stipend mechanism |
| 34 | 30,31,33 | 10,12,21,30,33 | partial | 33 | incorrect | missed Lukmini's accusation in the hall |
| 36 | 1,17,21 | 1,4,21,33,34 | partial | 17,21,31 | partial | each dropped a different gold chapter |
| 42 | 22,23,29 | 12,15,22,27,31 | partial | — | incorrect | Ch23/29 missed; no rescue from the cell |
| 43 | 11,37 | 7,11,19,24 | partial | 11,29,30,37 | incorrect | wrong scenes synthesized |
| 45 | 18,25 | 1,20,21,25,29 | partial | 17,18,20,21,25,29 | partial | near ties; the bedroom-window details missing |
| 46 | 21,27,31 | 21,27,31 | partial | 27,30,31 | partial | the escalation's first and last steps incomplete |
| 47 | 29,31 | 11,27,29,31 | partial | 29,31 | partial | the melted sword before Pratapaditya missing |
| 48 | 11,19 | 10,11 | incorrect | 19 | partial | Vector misses Ch19; Extract has no court half |
| 49 | 2,22 | 2,10,12 | incorrect | 2,22,23 | partial | Vector misses Ch22; Extract has no dismissed warning |

Seven of these (28, 30, 32, 34, 42, 46, 47) are the same shared failures the
English run has, all two-sided or causal-chain cross questions where neither
method assembles the full picture. In Q42 Extract retained *nothing* ("No
relevant content found"), and Vector, without Ch23 and Ch29, has Sitaram stage
the Yubaraj's death in the burning cell instead of opening the door and carrying
him out. The Japanese run adds eight more:

- **Q29** — analyzed in §1: both gave the stipend cause instead of the poisoning.
- **Q43** (gold 11,37, "how Rammohan physically carries royals out of two hostile
  courts") is the sharpest new case: Extract retained *both* gold chapters yet
  Phase 2 synthesized entirely different events (Basanta Ray persuaded out; a
  prison-fire rescue of Udayaditya) and was graded incorrect, while Vector (missing
  Ch37) got the Jessore rope-rescue but fabricated the Chandradwip half. A
  full-recall Phase 2 failure.
- **Q36** is a coverage-plus-synthesis partial: each method retrieved some
  gold chapters but both omitted the load-bearing fact (Mangala sneaking into
  Udayaditya's room to demand his love). Q34, shared with English, fails the
  same way (Lukmini bursting into the hall to expose Basanta Ray).
- **Q27, Q48, Q49** are Vector retrieval misses that Extract only half repairs.
  Vector misses Ch33 (the successful Muktiyar-Khan method, Q27) and says the
  success "is not in the context", misses Ch19 (Ramchandra's reading of the
  rescue, Q48) and Ch22 (the forged Delhi petition, Q49), and abstains on the
  last two. Extract holds those chapters but leaves part out: on Q27 it folds a
  second failed plan into the first, on Q48 it gives the "it was bound to
  happen" entitlement and the for-his-sister motive but not the mockery in
  Ramchandra's court, and on Q49 it gives the forged petition but not the
  minister's warning Pratapaditya once dismissed.
- **Q23** (single) and **Q45** are partial for both on the same content: on
  Q23 both add that the widow meant to put Sitaram in her debt, and on Q45 both
  give the window as grief and then hope (near ties, 0.48–0.52) without the
  empty seat left for Surma.

None of the fifteen is a gold problem; all are coverage or synthesis failures on
hard cross questions, or the judge's boundary.

## Vector-line (line-level retrieval)

The line-level dense variant —
[`build_index.py --line`](../README.md#build_indexpy) embeds one vector per
non-blank line, [`answer_vector.py --line`](../README.md#answer_vectorpy) ranks
lines and resolves each hit back to its containing segment for context — was run
for Japanese too, reproducing the English finding
([results-en/README.md](../results-en/README.md#vector-line-line-level-retrieval)).

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      31      13         6     0.750     0.720    0.332
all      Vector-line k=5   50      28      17         5     0.730     0.620    0.387
all      Vector-line k=10  50      33      13         4     0.790     0.760    0.260
single   Vector k=5        25      23       1         1     0.940     1.000    0.255
single   Vector-line k=5   25      24       0         1     0.960     0.960    0.376
single   Vector-line k=10  25      24       1         0     0.980     1.000    0.228
cross    Vector k=5        25       8      12         5     0.560     0.440    0.408
cross    Vector-line k=5   25       4      17         4     0.500     0.280    0.398
cross    Vector-line k=10  25       9      12         4     0.600     0.520    0.293
```

The trade is the same as English: the finer unit **raises chapter precision**
(k=5 0.332→0.387) but **lowers recall** (k=5 0.720→0.620), so line k=5 (0.730)
sits just below segment k=5 (0.750). Single-passage stays near-solved (0.960 /
0.980); the deficit is cross-reference, where a gold chapter's relevance is too
diffuse across a scene for a single line to rank. (Segment Vector k=10 reaches
0.830 here — see the V-hybrid section below — so line k=10 at 0.790 trails plain
segment retrieval at the same depth, just as in English.)

### The orthogonal recoveries are stronger than in English

The key cross-language result: line retrieval **surfaces gold chapters segment
search drops**, and in Japanese this is more pronounced than in English. Against
the segment k=5 baseline, line retrieval pulls these gold chapters into context
that segment k=5 misses:

```
line-only gold chapters (vs segment k=5):
  k=5 : Q28 Ch37 · Q31 Ch23 · Q34 Ch31 · Q45 Ch18 · Q48 Ch19 · Q49 Ch22   (6)
  k=10: above + Q38 Ch32 · Q50 Ch23                                        (8)

strict recall (subset coverage):
  segment k=5            = 36/50
  segment k=5 ∪ line k=5  = 41/50   (+5)
  segment k=5 ∪ line k=10 = 43/50   (+7)
```

The recovered set includes the named-entity cross misses §3a and §4 trace to
dense top-5 recall — **Q31 Ch23** (the signet-ring/seal chain) and **Q49 Ch22**
(the Delhi-petition forgery) — the same chapters Extract reads in full.
Line k=5 converts several of them: it beats segment k=5 on Q28, Q34 and Q45
(correct) and lifts Q48 and Q49 from incorrect to partial. Notably **Q38 Ch32**,
one of the four shared blind spots both dense *and* BM25 miss in the English
[HYBRID.md](../HYBRID.md) analysis, is recovered by line retrieval at k=10 here,
exactly as in English. So segment and line granularity fail on orthogonal
chapters, and the union upper bound (+5 / +7 strict recall) makes the
**section+line hybrid** — mixing same-model cosine scores from both
granularities — a concrete retrieval lever, distinct from the dense∪BM25 hybrid
because no second model or score-scale reconciliation is needed.

## V-hybrid (segment ∪ line dense union)

The section+line union the Vector-line analysis above proposed as a "concrete
retrieval lever" is realized as `V-hybrid` (`answer_vector.py --hybrid`): segment
top-k ∪ line top-k, resolved to segments, then the usual answering. It delivers
the segment∪line strict-recall gain [VECTOR-HYBRID.md](../VECTOR-HYBRID.md)
measured (ja +5 @ k=5, +7 @ k=10 — larger than English's +2/+3), but graded
against the right baseline that gain does **not** beat plain segment Vector:

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      31      13         6     0.750     0.720    0.332
all      Vector k=10       50      36      11         3     0.830     0.900    0.206
all      Extract           50      31      15         4     0.770     0.760    0.807
all      V-hybrid k=5      50      34      12         4     0.800     0.820    0.298
all      V-hybrid k=10     50      35      11         4     0.810     0.900    0.179
all      Ceiling           50      38      12         0     0.880     1.000    1.000
single   V-hybrid k=5      25      25       0         0     1.000     1.000    0.213
cross    Vector k=10       25      11      11         3     0.660     0.800    0.276
cross    V-hybrid k=5      25       9      12         4     0.600     0.640    0.383
cross    V-hybrid k=10     25      11      10         4     0.640     0.800    0.237
```

**V-hybrid k=5 (0.800) lands below plain Vector k=10 (0.830)**, and V-hybrid
k=10 (0.810) does not reach it either on roughly twice its context. The reason
is budget: V-hybrid k=5 pools
`seg5 ∪ line5`, a ~k=10 segment context, so the fair baseline is Vector k=10, not
Vector k=5. At that matched budget the dense union has no edge over the
single-index retriever.

Across the five questions where V-hybrid k=5 and Vector k=10 disagree, Vector
k=10 wins four:

- **Vector k=10 > V-hybrid k=5 on 4** — Q38 (Ch32) and Q42 (Ch23/29) are
  missed-context: the union's precision pressure pushes a gold chapter out;
  Q34 and Q39 are synthesis, with every gold chapter in both contexts.
- **V-hybrid k=5 > Vector k=10 on 1** — Q26, synthesis.

V-hybrid k=5 is tighter (ch.prec 0.298 vs 0.206) but loses recall (0.820 vs
0.900). Against Vector *k=5* it wins 8–4 (surfacing Q28 Ch37, Q45 Ch18, Q48
Ch19, Q49 Ch22, plus four synthesis wins), but that is the wrong, under-budget
baseline: simply running plain Vector to k=10 recovers the same orthogonal
chapters on its own, with one index and no stable-tie-break path.

**The cross-language conclusion holds in Japanese too:** as in English, the
segment∪line dense union does not beat plain Vector at a matched context budget.
Following the implementation of the Japanese morphological tokenizer using spaCy,
Japanese now has its own dense∪BM25 Hybrid equivalent, which becomes the top-performing
retriever, beating the dense baseline. See [§ Hybrid](#hybrid-dense--bm25-union) below.

**Ceiling (0.880)** — gold chapters fed verbatim, 38 correct, 12 partial, zero
incorrect — sits only 0.020 above the best retriever (Hybrid k=10). All twelve
partials are cross-reference, so even with the right chapters the answer model
leaves part of a multi-part answer out about half the time. Part of this is the
judge's boundary in Japanese: three of the twelve are near ties, and on Q39
Ceiling's answer contains every element of the gold and lands `partial` (0.54),
while Hybrid k=10's answer with the same content is `correct` (0.55). The
headroom above the retrievers is therefore small and mostly synthesis (see
[§ The gap to Ceiling](#the-gap-to-ceiling)).

## Hybrid (dense ∪ BM25 union)

Following the implementation of the Japanese morphological tokenizer using spaCy, the union approach from [HYBRID.md](../HYBRID.md) converts the strict-recall retrieval gain into answer accuracy. Already at `k=5` it reaches **36/50 (0.850)**, recovering dense-blind Class A chapters and beating the plain Vector baseline; `k=10` is the highest Japanese method at **37/50 (0.860)**, while `k=8` dips below both.

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      31      13         6     0.750     0.720    0.332
all      Vector k=10       50      36      11         3     0.830     0.900    0.206
all      Extract           50      31      15         4     0.770     0.760    0.807
all      Hybrid k=5        50      36      13         1     0.850     0.860    0.248
all      Hybrid k=8        50      32      17         1     0.810     0.940    0.173
all      Hybrid k=10       50      37      12         1     0.860     0.960    0.148
all      Ceiling           50      38      12         0     0.880     1.000    1.000
```

### Hybrid k=5 vs Vector k=10

Hybrid k=5 (0.850) outperforms Vector k=10 (0.830), winning four questions and losing three. Two of its wins are the retrieval recovery of dense misses:

- **Q31 (Class A, correct vs incorrect):** Vector k=10 held only Ch23, whereas Hybrid k=5's BM25 component retrieved Ch21 and Ch22 as well, leading to a correct answer.
- **Q32 (partial vs incorrect):** Vector k=10 held only Ch11; Hybrid k=5 added Ch16 and answered partially even without Ch15.
- **Q26 (correct vs partial)** and **Q47 (correct vs partial)** are synthesis: both methods held every gold chapter.

Vector k=10 wins back Q37, Q41 and Q44, all three with the same gold chapters as Hybrid k=5. On cross-reference questions, Hybrid k=5 lifts the score to **0.700** (vs Vector k=10's 0.660), confirming that the lexical hybrid recovers the proper-noun-heavy contexts where dense search is blind.

### Hybrid k=8 and k=10: deeper is not monotonic

Deepening the union retrieves more gold chapters (chapter recall 0.860 → 0.940 → 0.960), but the score dips before it rises: **32/50 (0.810)** at `k=8` and **37/50 (0.860)** at `k=10`.

- **k=8 vs k=5:** `k=8` gains only Q37, and loses Q31, Q34, Q39, Q40 and Q47, all five with the same gold chapters as `k=5`. The larger context (~20 scenes) dilutes the synthesis without adding a gold chapter that changes a verdict.
- **k=10 vs k=8:** `k=10` gains Q27 (Ch33) and five questions with the same chapters (Q39, Q40, Q41, Q43, Q44), and loses only Q37. Against `k=5`, `k=10` wins four (Q27 and Q43 by retrieval, Ch33 and Ch37; Q41 and Q44 by synthesis) and loses three (Q31, Q34, Q47, all synthesis). Hybrid k=10 beats Vector k=10 on five questions (Q31, Q32 and Q43 on retrieval, Ch21/22, Ch16 and Ch37; Q26 and Q27 with the same chapters) and loses two (Q34, Q37, synthesis).

### The gap to Ceiling

Ceiling (0.880) beats Hybrid k=10 on four questions, representing the remaining frontier:
- **Q42 (missed context):** Ch23 and Ch29 are outside the union's top-10.
- **Q29, Q30, Q35 (synthesis):** Hybrid k=10 holds every gold chapter, but the union's supporting context still confuses the synthesis on these cross-reference questions (Q29 is incorrect for every method but Ceiling, which is itself only partial).

Hybrid k=10 in turn beats Ceiling on Q39 and Q41, both near ties for Ceiling. Hybrid k=5 shows the same shape with more retrieval in it: Ceiling beats it on seven (Q27, Q42, Q43 missed context; Q29, Q30, Q35, Q44 synthesis), and it beats Ceiling on four (Q31, Q34, Q39, Q47).


## Filter2 / Filter3 (LLM-as-retriever)

The per-chapter relevance filter variants — Phase 1 classifies each chapter as
yes/no (Filter2) or yes/maybe/no (Filter3), Phase 2 answers from the full text of
the kept chapters — were run on Japanese, replicating the English analysis in
[FILTER.md](../FILTER.md).

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      31      13         6     0.750     0.720    0.332
all      Vector k=10       50      36      11         3     0.830     0.900    0.206
all      Extract           50      31      15         4     0.770     0.760    0.807
all      Filter2           50      30      14         6     0.740     0.640    0.809
all      Filter3           50      37       9         4     0.830     0.880    0.783
all      Ceiling           50      38      12         0     0.880     1.000    1.000
single   Filter2           25      25       0         0     1.000     1.000    1.000
single   Filter3           25      25       0         0     1.000     1.000    0.980
cross    Filter2           25       5      14         6     0.480     0.280    0.619
cross    Filter3           25      12       9         4     0.660     0.760    0.586
```

**Filter3 (0.830) leads Filter2 (0.740) by 7 correct answers (37 vs 30)**,
driven by the same mechanism as English: Filter3's "keep ≠ no" rule retains
chapters the strict "yes-only" Filter2 drops. Filter3 beats Filter2 on 8, every
one by holding gold chapters Filter2 dropped (Q26 Ch11/29, Q28 Ch37, Q31 Ch23,
Q35 Ch8/19, Q37 Ch1, Q38 Ch28/32, Q44 Ch8/36, Q45 Ch18/25); Filter2 beats
Filter3 on 2 (Q30, Q40, synthesis). Single-passage is perfect under both
variants (25/25 each); all losses are cross-reference.

**Filter3 (0.830) ties Vector k=10 (0.830) and falls short of Hybrid k=5 and
k=10 (0.850, 0.860)** — unlike English, where Filter3 (0.890) is well above
Vector k=10 (0.840) and ties Hybrid k=10. Filter3 wins 5–4 on pairwise
disagreements with Vector k=10: Filter3 wins Q31 (Ch21/22 ring-seal chain), Q43
(Ch37 Rammohan rescue), Q32 (partial vs incorrect, neither holding Ch15) and
Q26 and Q35 (synthesis); Vector k=10 wins Q34 (Ch30/31/33 Lukmini accusation),
Q42 (Ch22, the one prison-break chapter it holds), and Q40 and Q41 (synthesis).
Both sides are symmetric — the LLM classifier surfaces chapters dense retrieval
drops but misses others dense search finds — and neither fully closes the
cross-reference gap.

**Ceiling (0.880) beats Filter3 by 6 questions** (Q27, Q29, Q30, Q40
synthesis; Q34/Q42 missed-context) and loses 3 to it (Q31, Q37, Q39) —
confirming the Japanese frontier is retrieval recall and synthesis quality on
hard cross questions, not a language barrier.

## GraphRAG

[Microsoft GraphRAG](https://github.com/microsoft/graphrag) builds a knowledge
graph over the corpus and answers queries through two search modes — `local`
(entity-anchored) and `global` (community-summary based). Both modes run on
`ollama:gemma4:31b-it-qat`, the same model used for every other Japanese method
here; the Japanese config additionally swaps in `extractor_type:
syntactic_parser` (instead of `regex_english`) for entity extraction. Details
in [graphrag-ja/README.md](../graphrag-ja/README.md).

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      31      13         6     0.750     0.720    0.332
all      Extract           50      31      15         4     0.770     0.760    0.807
all      Hybrid k=10       50      37      12         1     0.860     0.960    0.148
all      Ceiling           50      38      12         0     0.880     1.000    1.000
all      GraphRAG local    50      20      15        15     0.550     0.880    0.239
all      GraphRAG global   50       3      16        31     0.220     0.280    0.081
single   GraphRAG local    25      18       2         5     0.760     0.880    0.341
single   GraphRAG global   25       3       2        20     0.160     0.240    0.061
cross    GraphRAG local    25       2      13        10     0.340     0.880    0.137
cross    GraphRAG global   25       0      14        11     0.280     0.320    0.101
```

### GraphRAG local (0.550)

Local search scores 20/50 (0.550) — just below the English run (0.570), below
Filter2 (0.740), and far below Hybrid k=10 (0.860). As in English, the
chapter-retrieval numbers explain why: **recall 0.880** (nearly every gold
chapter is somewhere in the expanded context) but **precision 0.239** — low,
though notably *higher* than English's 0.135. The Japanese local search
expands a narrower context on average (mean 14.5 chapters vs. English's 21.1
out of 37), so the signal-to-noise ratio is somewhat better, but still far
below the pipeline methods.

The failure mode is the same **synthesis-dominated** pattern as English: of
GraphRAG local's 24 losses to Ceiling, **18 are synthesis** (the gold chapter
is present but the answer is wrong or vague) and only 6 are missed context.
GraphRAG local beats Ceiling, Hybrid k=5 and Hybrid k=10 on a single question,
Q49 (see below), while losing 24, 22 and 20 to them.

**Single vs. cross diverges from English in opposite directions.** Japanese
local search is *stronger* on single-passage (18/25, 0.760) than English
(15/25, 0.620) — the single-passage synthesis collapse that dominates the
English write-up is much milder here. But it is *weaker* on cross-reference
(2/25, 0.340 vs. English's 4/25, 0.520). Net effect: the two shifts largely
cancel, leaving the overall score close to English's.

### Where the English "structural strengths" don't transfer

The English study found two mechanisms that let GraphRAG local win despite its
low overall score: answering from graph traversal with zero retrieved
chapters (Q26 and Q28, both partial), and reaching both Class A questions (the
signet ring and the Delhi-petition chains) that segment Vector misses at every
depth. Neither holds cleanly in Japanese:

- **Zero-context answers are weaker still.** Japanese local search has 5
  zero-context questions (Q9, Q14, Q16, Q30, Q33): 4 incorrect, 1 partial —
  compared to English's 6 zero-context questions, of which three are partial
  (Q26, Q28, Q44) and none correct. Q26 in Japanese is partial as in English,
  but only after expanding *all 37 chapters* — volume, not pure graph
  traversal.
- **Only one of the two Class A questions is recovered.** Q49 (デリー皇帝の脅威
  が投獄の手段になる経緯, gold Ch2/22) is correct, with all 37 chapters
  expanded — the answer traces the forged-petition scheme in detail, including
  "ルクミニーが持ってきた指輪にある王太子の印章がこの文書に押印されました" (the
  signet on the ring Rukmini brought was stamped onto the document); it is the
  one question where local search beats Ceiling, which leaves out the
  minister's dismissed warning. But Q31
  (asking specifically how the signet ring becomes evidence, gold Ch21–23) is
  **incorrect** even with the same full 37-chapter context: the answer states
  outright that "指輪に関する具体的な言及は見当たりませんでした" (no specific
  mention of the ring was found). The graph clearly encodes the ring→seal→
  forged-petition edge — it surfaces unprompted in Q49's own answer — but Q31's
  query anchors to a different entity path and fails to reach it. The knowledge
  is present in the graph; retrieval is inconsistent across query framings of
  the same fact, which is a sharper failure mode than the clean "graph doesn't
  encode this" story in English.

### GraphRAG global (0.220)

Global search scores 3/50 correct (0.220) — the weakest of any Japanese method,
but better than English's global score (0.130). The mechanism is the
same: community summaries operate at the wrong granularity, abstracting away
the chapter-level detail the questions turn on. **Recall 0.280, precision
0.081** — the lowest precision of any method — with a mean of only 7.2
chapters expanded (vs. local's 14.5). Half the questions (26/50) expand *zero*
chapters, and every one of those 26 is incorrect.

Single-passage (3/25, 0.160) is nearly a complete failure, matching English
(1/25, 0.060). Cross-reference (0/25 correct, 0.280) scores a little above
English (0/25 correct, 0.200) on the weighted score through 14 partials; it
fares better than single-passage for the same reason as local search: a
handful of prominent cross-cutting themes surface in community summaries even
when specific scene detail does not.

**Q49 is partial even under global search** (with only 4 chapters expanded).
The Delhi-petition chain is correct under Japanese local search, partial under
Japanese global and English local search, and missed only by English global,
so it is unusually well-represented as a graph relationship.

Within Japanese, local clearly beats global (23 wins to 4) — the same
ordering as English — confirming entity-anchored traversal is the more useful
of the two modes when it is available at all.

### Summary

Neither GraphRAG mode reaches the simplest pipeline method (Vector k=5, 0.750),
let alone Hybrid k=10 (0.860). Local search's language-comparison story is
mixed — close to English overall (0.550 vs 0.570), stronger on
single-passage, weaker on cross-reference, and weaker still on the
"zero-context graph traversal" that gave English's local search its partial
answers. Global search is uniformly the weakest method in
both languages. The cost asymmetry is also larger for Japanese: building the
graph and running all 100 queries takes 20h 19m here vs. 13h 6m in English (see
[graphrag-ja/README.md § Measured runtime](../graphrag-ja/README.md#measured-runtime-evo-x2--ryzen-ai-max-395)),
against minutes for the flat embedding index — reinforcing that the
knowledge-graph approach is not a practical alternative to the pipeline for
this task in either language.

## 5. Takeaways and cross-language comparison

- **The headline findings hold across languages.** Single-passage QA is solved
  (Vector 23/25, Extract 24/25); cross-reference is the frontier (8/25, 7/25). The
  gold is sound — the Q29 spot-check confirms the poisoning against the Japanese
  source even though *both* methods missed it here.
- **Extract ≥ Vector holds, more weakly than in English.** Extract and Vector
  tie on correct answers (31 each) and Extract leads on partial credit (0.770
  vs. 0.750), against English's 35/28 (0.810 vs. 0.730), with Extract again at
  higher chapter precision (0.807 vs. 0.332). Two independent thorough readers
  agreeing with the gold is convergent evidence the gold is sound.
- **The failure modes are the same.** Extract's losses are Phase 1 recall (Q26,
  Q39, and the wipeouts Q34 and Q42) plus Phase 2 synthesis with the chapters in
  hand (Q33, Q43). Vector's losses are top-5 vector recall (Q31, Q48, Q49 — the
  *same* named-entity questions as English) plus answering slips with the gold
  retrieved (Q21, Q41, Q44).
- **Language changes accuracy little.** The answer model, embedding model, and
  judge are identical across the two runs, so this is a clean language
  comparison. Vector k=5 is slightly higher in Japanese (0.750 vs 0.730) and
  Extract lower (0.770 vs 0.810), and across the full table Japanese is lower on
  12 of 15 methods by 0.021 on average. The both-not-correct set has 13 questions
  in English and 15 in Japanese, and only seven are shared (Q28, Q30, Q32, Q34,
  Q42, Q46, Q47). This is a redistribution at near-constant total accuracy, and
  it traces to the Japanese phrasing of specific cross questions (most starkly
  Q29, the covert cause, and Q43, full recall but wrong synthesis), not to a
  capability gap. Retrieval-side findings (which gold chapters dense search drops)
  are identical because the embedding model is the same.
- **Ceiling is lower in Japanese** (0.880 vs 0.960, 12 partials against 4, all
  cross-reference), and the top retriever, Hybrid k=10, sits 0.020 below it
  instead of 0.070. Part of this is the judge's boundary: Q39's Ceiling answer
  holds every element of the gold and lands `partial`.
- **Filter3 (0.830) keeps the English ordering against Filter2** but not
  against Vector k=10: it is level with Vector k=10 in Japanese (0.830 each),
  against 0.890 vs 0.840 in English. The strict-vs-lenient pattern holds:
  Filter3 beats Filter2 by 7 correct answers, all 8 of its wins by holding gold
  chapters Filter2 dropped. Filter is still impractical at ~1,850× Vector's
  call cost.
- The retrieval levers are unchanged: Vector's residual losses are dense top-5
  misses on rare proper nouns / second-side facts, the target of `sweep_vector.py`
  and the BM25 hybrid follow-up in [HYBRID.md](../HYBRID.md).
- **GraphRAG's language comparison is mixed, not uniform.** Local search scores
  close to English overall (0.550 vs 0.570) but the composition differs:
  stronger on single-passage (0.760 vs 0.620), weaker on cross-reference (0.340
  vs 0.520), and weaker on answers from zero retrieved context (1 partial of 5
  vs 3 partial of 6, none correct in either). Global search is weak in both
  languages, less so in Japanese (0.220 vs 0.130). See
  [§ GraphRAG](#graphrag) above.
