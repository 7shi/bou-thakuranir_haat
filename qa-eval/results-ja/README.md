# Disagreement case study: Vector vs. Extract (Japanese)

A manual, per-question analysis of where the two methods **disagree** on the
Japanese question set, to complement the aggregate table from
[`report.py`](../README.md#reportpy). The goal is to attribute each disagreement
to a concrete failure mode and, along the way, spot-check whether the gold
answers are sound. Read alongside the English study
([results-en/README.md](../results-en/README.md)); the cross-language comparison
is in §5.

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 50 questions
(`questions-ja.jsonl`, 25 single-passage + 25 cross-reference). The answer model,
embedding model (`embeddinggemma`), and judge are all identical to the English
run, so any difference below is a language effect, not a model one.

## Where the difficulty lives: single vs. cross

Vector scores 38/50, Extract 40/50 (weighted 0.810 vs. 0.850) — Extract edges ahead,
where the English run tied 39/39. But the gap lives entirely in the
**cross-reference** half. On the **single-passage** half Vector scores 24/25 and
Extract 25/25; on the **cross-reference** half they drop to 14/25 and 15/25. The
one single-passage miss (Q21, Vector incorrect) is an *answering* failure with the
correct passage in hand, not a retrieval failure. So single-passage QA is
essentially solved by either method; the open problem is multi-chapter
integration — the same conclusion as the English run.

## Verdict agreement matrix

Rows = Vector verdict, columns = Extract verdict.

| | Ext correct | Ext partial | Ext incorrect | Vector total |
| --- | --- | --- | --- | --- |
| **Vector correct** | 35 | 2 | 1 | 38 |
| **Vector partial** | 1 | 2 | 2 | 5 |
| **Vector incorrect** | 4 | 1 | 2 | 7 |
| **Ext total** | 40 | 5 | 5 | 50 |

The two off-diagonal blocks analyzed below:

- **Vector correct / Extract not correct** — 3 questions (§2): two Extract Phase 1
  retrieval misses plus one where Extract held both gold chapters but
  mis-synthesized.
- **Extract correct / Vector not correct** — 5 questions (§3): three Vector vector
  retrieval misses and two where Vector retrieved the gold chapter but answered
  short.

**7** questions are not correct under *either* method (28, 29, 32, 34, 36, 43,
48); these are examined in §4. That is more than double the English run's 3
shared failures, and — since the answer model is the same — the difference is the
main cross-language divergence (§5): all of it is on cross questions, a
translation/question-specific reshuffling at near-constant total accuracy, not a
gold problem.

## 1. Gold validity spot-check (Q29)

Q29 — "Pratapaditya's official decree aims to separate Surma and Udayaditya by
sending her to her father's house; what *covert* action actually causes her
departure?" (gold chapters 16, 17). The gold answer: Surma dies after drinking a
poison brewed by the magician Mangala (Rukmini), who was secretly commissioned —
via the maid Matangini — to draw Udayaditya's heart away from his wife.

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
confusion is specific to the Japanese phrasing of the two threads. A shared answering
failure, not a gold problem.

## 2. Vector correct / Extract not correct (3 questions)

| Q | type | gold ch | Extract used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 42 | cross | 22,23,29 | — | incorrect | Phase 1 miss (nothing retained) |
| 46 | cross | 21,27,31 | 27,30,31 | partial | Phase 1 miss (Ch21) |
| 33 | cross | 27,28 | **27,28** | partial | synthesis (had the chapters) |

### 2a. Phase 1 false negatives (42, 46)

Extract makes a per-chapter binary call in Phase 1: extract the relevant passage,
or emit `None`. A wrong `None` is unrecoverable — that chapter never reaches Phase
2.

- **Q42** (gold 22,23,29) retained *nothing* and returned "No relevant content
  found." Vector retrieved Ch22 by vector similarity and reconstructed the
  fire-diversion prison break correctly.
- **Q46** (gold 21,27,31) kept 27 and 31 but dropped Ch21, the chapter that
  establishes the *playful* money-borrowing between Sitaram and Rukmini. Extract
  explicitly denied that premise ("提示されたテキストに『戯れのような金銭のやり取り』
  に関する記述はありません") and was graded partial; Vector retrieved all three gold
  chapters and traced the full escalation.

### 2b. Phase 2 synthesis shortfall (Q33)

Q33 (the song "私だけが、ただ一人残された", gold 27,28) is different: Phase 1 **kept
both gold chapters**, yet the answer was only partial. Vector correctly named both
contrasting singing contexts (alone at the Rajgarh sunset; to Bibha in Surma's
empty room at Jessore); Extract got the first but *invented* the second — a scene
where Khan Sahib asks after Basanta Ray, followed by an abrupt shift to a cheerful
song — missing the gold's discovery of death and shared grief. The chapters were
in hand; the answer model just synthesized the second half wrong.

## 3. Extract correct / Vector not correct (5 questions)

| Q | type | gold ch | Vector used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 27 | cross | 2,4,33 | 2,5,10,12,28 | incorrect | retrieval miss (Ch33) |
| 31 | cross | 21,22,23 | 25,27,33,34 | incorrect | retrieval miss (all gold) |
| 49 | cross | 2,22 | 2,10,12 | incorrect | retrieval miss (Ch22) |
| 21 | single | 5 | **2,5,8,12** | incorrect | retrieved Ch5, wrong incident |
| 47 | cross | 29,31 | **11,27,29,31** | partial | retrieved gold, short answer |

### 3a. Vector retrieval misses (27, 31, 49)

Three are Vector retrieval misses: a gold chapter ranked outside the top-5, so the
answerer never saw it — and all three reproduce English losses on the same
questions.

- **Q31** (how the signet ring becomes evidence, gold 21–23) retrieved none of the
  three gold chapters and replied "提供されたコンテキストの中に、ウダヤディティヤの
  印章指輪に関する記述はありません." Extract, reading Ch21–22, reconstructed the
  ring→seal→forged-petition→Pratapaditya chain in full.
- **Q27** (Pratapaditya's failed *and* successful plot to kill Basanta Ray, gold
  2,4,33) got the failed Simultali plan from Ch2 but missed the successful
  Muktiyar-Khan method in Ch33, then said the success "is not in the context" —
  graded incorrect. Extract retained both sides.
- **Q49** (the Delhi-Emperor threat turned into grounds for imprisonment, gold
  2,22) missed Ch22 and abstained. Extract had it.

These are exactly the named-entity / second-side-of-a-two-part-question misses
the English study traced to top-5 dense recall (the signet ring, the Emperor of
Delhi, Muktiyar Khan) — they recur in Japanese despite a different answer model,
because the embedding model is the same.

### 3b. Retrieval hit, short answer (21, 47)

The other two Vector losses are *not* retrieval misses — the gold chapter was in the
context and the answer still fell short:

- **Q21** (single, gold Ch5): Vector retrieved Ch5 but answered with *different*
  offenses (guards failing to attend the prince; reporting his disappearance)
  instead of the two the question asks for (losing a letter; sending a man to
  Umesh Ray instead of going personally). Extract named both exactly. This is the
  one single-passage question Vector missed, and — as in the English run — it is an
  answering failure, not a retrieval one.
- **Q47** (cross, gold 29,31): Vector retrieved *both* gold chapters but only
  partially synthesized — it described the fire-as-distraction and the faked-death
  props yet omitted the actual extraction (Sitaram opening the cell and spiriting
  Udayaditya onto the boat). Extract captured the two-phase strategy and was
  graded correct.

## 4. Both not correct (7 questions)

| Q | gold ch | Vector used | Vector | Extract used | Ext | shared failure |
| --- | --- | --- | --- | --- | --- | --- |
| 28 | 9,37 | 7,8,9,24 | partial | 9 | incorrect | only one of two locations found |
| 29 | 16,17 | 5,11,12,16,17 | incorrect | 14,15,16,17 | incorrect | wrong covert cause (stipend, not poison) |
| 32 | 11,15,16 | 9,10,11,12,24 | incorrect | 12,14 | incorrect | missed the secret-stipend mechanism |
| 34 | 30,31,33 | 10,12,21,30,33 | partial | 33 | partial | missed Lukmini's accusation in the hall |
| 36 | 1,17,21 | 1,4,21,33,34 | partial | 17,21,31 | partial | each dropped a different gold chapter |
| 43 | 11,37 | 7,11,19,24 | partial | 11,29,30,37 | incorrect | wrong scenes synthesized |
| 48 | 11,19 | 10,11 | incorrect | 19 | partial | missed the whisper-to-servant reading |

Three of these (28, 32, 48) are the same shared failures the English run isolates,
all two-sided or causal-chain cross questions where neither method assembles the
full picture. The Japanese run adds four more (29, 34, 36, 43):

- **Q29** — analyzed in §1: both gave the stipend cause instead of the poisoning.
- **Q43** (gold 11,37, "how Rammohan physically carries royals out of two hostile
  courts") is the sharpest new case: Extract retained *both* gold chapters yet
  Phase 2 synthesized entirely different events (Basanta Ray persuaded out; a
  prison-fire rescue of Udayaditya) and was graded incorrect, while Vector (missing
  Ch37) got the Jessore rope-rescue but fabricated the Chandradwip half. A
  full-recall Phase 2 failure.
- **Q34, Q36** are coverage-plus-synthesis partials: each method retrieved some
  gold chapters but both omitted the load-bearing fact (Lukmini bursting into the
  hall to expose Basanta Ray, Q34; Mangala sneaking into Udayaditya's room to
  demand his love, Q36).

None of the seven is a gold problem; all are coverage or synthesis failures on
hard cross questions.

## Vector-line (line-level retrieval)

The line-level dense variant —
[`build_index.py --line`](../README.md#build_indexpy) embeds one vector per
non-blank line, [`answer_vector.py --line`](../README.md#answer_vectorpy) ranks
lines and resolves each hit back to its containing segment for context — was run
for Japanese too, reproducing the English finding
([results-en/README.md](../results-en/README.md#vector-line-line-level-retrieval)).

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      38       5         7     0.810     0.720    0.332
all      Vector-line k=5   50      35       9         6     0.790     0.620    0.387
all      Vector-line k=10  50      40       4         6     0.840     0.760    0.260
single   Vector k=5        25      24       0         1     0.960     1.000    0.255
single   Vector-line k=5   25      24       0         1     0.960     0.960    0.376
single   Vector-line k=10  25      25       0         0     1.000     1.000    0.228
cross    Vector k=5        25      14       5         6     0.660     0.440    0.408
cross    Vector-line k=5   25      11       9         5     0.620     0.280    0.398
cross    Vector-line k=10  25      15       4         6     0.680     0.520    0.293
```

The trade is the same as English: the finer unit **raises chapter precision**
(k=5 0.332→0.387) but **lowers recall** (k=5 0.720→0.620), so line k=5 (0.790)
sits just below segment k=5 (0.810). Single-passage stays solved (line k=10
saturates to 1.000); the deficit is entirely cross-reference, where a gold
chapter's relevance is too diffuse across a scene for a single line to rank.
(Segment Vector k=10 reaches 0.890 here — see the V-hybrid section below — so line
k=10 at 0.840 trails plain segment retrieval at the same depth, just as in
English.)

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

The recovered set includes the named-entity cross misses §3a traces to dense
top-5 recall — **Q31 Ch23** (the signet-ring/seal chain) and **Q49 Ch22** (the
Delhi-petition forgery) — the same chapters Extract reads in full to win those
questions. Notably **Q38 Ch32**, one of the four shared blind spots both dense
*and* BM25 miss in the English [HYBRID.md](../HYBRID.md) analysis, is recovered by
line retrieval at k=10 here, exactly as in English. So segment and line
granularity fail on orthogonal chapters, and the union upper bound (+5 / +7
strict recall) makes the **section+line hybrid** — mixing same-model cosine
scores from both granularities — a concrete retrieval lever, distinct from the
dense∪BM25 hybrid because no second model or score-scale reconciliation is
needed.

## V-hybrid (segment ∪ line dense union)

The section+line union the Vector-line analysis above proposed as a "concrete
retrieval lever" is realized as `V-hybrid` (`answer_vector.py --hybrid`): segment
top-k ∪ line top-k, resolved to segments, then the usual answering. It delivers
the segment∪line strict-recall gain [VECTOR-HYBRID.md](../VECTOR-HYBRID.md)
measured (ja +5 @ k=5, +7 @ k=10 — larger than English's +2/+3), but graded
against the right baseline that gain does **not** beat plain segment Vector:

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      38       5         7     0.810     0.720    0.332
all      Vector k=10       50      42       5         3     0.890     0.900    0.206
all      Extract           50      40       5         5     0.850     0.760    0.807
all      V-hybrid k=5      50      42       5         3     0.890     0.820    0.298
all      V-hybrid k=10     50      42       4         4     0.880     0.900    0.179
all      Ceiling           50      47       3         0     0.970     1.000    1.000
single   V-hybrid k=5      25      25       0         0     1.000     1.000    0.213
cross    Vector k=10       25      17       5         3     0.780     0.800    0.276
cross    V-hybrid k=5      25      17       5         3     0.780     0.640    0.383
cross    V-hybrid k=10     25      17       4         4     0.760     0.800    0.237
```

**V-hybrid k=5 (0.890) ties plain Vector k=10 (0.890) exactly — same 42/5/3** —
and V-hybrid k=10 (0.880) sits just under it. The reason is budget: V-hybrid k=5
pools `seg5 ∪ line5`, a ~k=10 segment context, so the fair baseline is Vector
k=10, not Vector k=5. At that matched budget the dense union has no edge over the
single-index retriever.

The tie is a genuine trade, not an identity — across the five questions where
they disagree, V-hybrid k=5 wins 3 and Vector k=10 wins 2, netting the exact
aggregate tie:

- **V-hybrid k=5 > Vector k=10 on 3** — Q32 (Ch15/16) and Q42 (Ch23/29) are
  missed-context wins where the line side surfaces a cross chapter segment k=10
  drops; Q46 is synthesis.
- **Vector k=10 > V-hybrid k=5 on 2** — Q27 (Ch4/33, missed-context: the union's
  precision pressure pushes a gold chapter out) and Q47 (synthesis).

They reach 0.890 by opposite routes: Vector k=10 is broader (ch.recall 0.900),
V-hybrid k=5 is tighter (ch.prec 0.298 vs 0.206). V-hybrid's clean 6–0 domination
of Vector *k=5* still holds (surfacing Q28 Ch37, Q32 Ch15/16, Q34 Ch31, Q48 Ch19,
Q49 Ch22), but that is the wrong, under-budget baseline: simply running plain
Vector to k=10 recovers the same orthogonal chapters on its own, with one index
and no stable-tie-break path.

**The cross-language conclusion holds in Japanese too:** as in English, the
segment∪line dense union does not beat plain Vector at a matched context budget.
Following the implementation of the Japanese morphological tokenizer using spaCy,
Japanese now has its own dense∪BM25 Hybrid equivalent, which becomes the top-performing
retriever, beating the dense baseline. See [§ Hybrid](#hybrid-dense--bm25-union) below.

**Ceiling (0.970)** — gold chapters fed verbatim, 47 correct, three partial, zero
incorrect — sits 0.050 above that best retriever (Hybrid k=10), so the Japanese frontier is
retrieval, not comprehension: given the right chapters the answer model reads
them nearly perfectly, and the ~5-point headroom is all retrieval recall.

## Hybrid (dense ∪ BM25 union)

Following the implementation of the Japanese morphological tokenizer using spaCy, the union approach from [HYBRID.md](../HYBRID.md) converts the strict-recall retrieval gain into answer accuracy. At `k=8`, it hits the optimal sweet spot, achieving the highest QA accuracy for Japanese at **45/50 (0.940)**, recovering dense-blind Class A chapters and beating the plain Vector baseline.

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      38       5         7     0.810     0.720    0.332
all      Vector k=10       50      42       5         3     0.890     0.900    0.206
all      Extract           50      40       5         5     0.850     0.760    0.807
all      Hybrid k=5        50      44       4         2     0.920     0.860    0.248
all      Hybrid k=8        50      45       4         1     0.940     0.940    0.173
all      Hybrid k=10       50      44       4         2     0.920     0.960    0.148
all      Ceiling           50      47       3         0     0.970     1.000    1.000
```

### Hybrid k=5 vs Vector k=10

Hybrid k=5 (0.920) outperforms Vector k=10 (0.890) by two questions (44/50 vs 42/50), driven by the retrieval recovery of dense misses:

- **Q31 (Class A, correct vs incorrect):** Vector k=10 missed all gold chapters (Ch21–23), whereas Hybrid k=5's BM25 component retrieved Ch21 and Ch22, leading to a correct answer.
- **Q49 (Class A, correct vs incorrect):** Vector k=10 missed Ch22, whereas Hybrid k=5 successfully retrieved Ch22 and got it correct.

On cross-reference questions, Hybrid k=5 lifts the score to **0.840** (vs Vector k=10's 0.780), confirming that the lexical hybrid recovers the proper-noun-heavy contexts where dense search is blind.

### Hybrid k=8: The Optimal Sweet Spot

Setting the retrieval depth to **`k=8`** balances retrieval recall and context precision perfectly, yielding the best retriever performance of **45/50 (0.940)**:
- **Retrieval Gains:** It expands the context enough to retrieve the missing gold chapters for **Q27** (Ch33) and **Q36** (Ch17), upgrading both to correct.
- **Precision Retention:** At the same time, it keeps the context tight enough (~20 scenes) to avoid the "lost in the middle" synthesis errors that plague `k=10` (such as on **Q34**), resolving the trade-off.

### Hybrid k=10 and the Synthesis Trade-off

At `k=10`, the Union reaches a near-perfect retrieval recall (Strict Recall **48/50**, chapter recall **0.960**). The two questions where Hybrid k=10 beats Vector k=10 are the same Class A cases: Q31 and Q49.

However, Hybrid k=10 does *not* beat Hybrid k=5 or k=8 overall, landing back on **44/50 (0.920)**. This is a classic RAG trade-off: deepening the search to `k=10` successfully retrieves more contexts, but the larger context size (~25 scenes vs ~13 scenes, a 1.8× increase) dilutes the signal. For **Q34**, the extra noise confuses the answerer, causing a synthesis regression (`synthesis` error) and dropping it from correct to incorrect/partial compared to `k=5` and `k=8`.

### The two-question gap to Ceiling

Ceiling (0.970) beats Hybrid k=8 on only two questions (Q29, Q37), representing the remaining synthesis frontier:
- **Q29, Q37 (synthesis):** The union's supporting context still occasionally confuses the synthesis on these cross-reference questions; Ceiling, with only the gold context, answers them correctly (or partial).
- **Q32 (missed context):** Ch15 (the secret monthly stipend) remains a Class B unreachable, ranked outside both retrievers' top-k even at `k=10`.


## Filter2 / Filter3 (LLM-as-retriever)

The per-chapter relevance filter variants — Phase 1 classifies each chapter as
yes/no (Filter2) or yes/maybe/no (Filter3), Phase 2 answers from the full text of
the kept chapters — were run on Japanese, replicating the English analysis in
[FILTER.md](../FILTER.md).

```
scope    method             n correct partial incorrect  weighted ch.recall  ch.prec
all      Vector k=5        50      38       5         7     0.810     0.720    0.332
all      Vector k=10       50      42       5         3     0.890     0.900    0.206
all      Extract           50      40       5         5     0.850     0.760    0.807
all      Filter2           50      39       4         7     0.820     0.640    0.809
all      Filter3           50      43       2         5     0.880     0.880    0.783
all      Ceiling           50      47       3         0     0.970     1.000    1.000
single   Filter2           25      25       0         0     1.000     1.000    1.000
single   Filter3           25      25       0         0     1.000     1.000    0.980
cross    Filter2           25      14       4         7     0.640     0.280    0.619
cross    Filter3           25      18       2         5     0.760     0.760    0.586
```

**Filter3 (0.880) leads Filter2 (0.820) by 4 questions**, driven by the same
mechanism as English: Filter3's "keep ≠ no" rule retains chapters the strict
"yes-only" Filter2 drops. Filter3 beats Filter2 on 6 (all missed-context: Q26
Ch11/29, Q28 Ch37, Q31 Ch23, Q35 Ch8/19, Q38 Ch28/32, Q45 Ch18/25); Filter2
beats Filter3 on 2 (both synthesis: Q36, Q40). Single-passage is perfect under
both variants (25/25 each); all losses are cross-reference.

**Filter3 (0.880) ties V-hybrid k=10 (0.880) and falls just short of Vector k=10
(0.890)** — the reverse of English, where Filter3 (0.930) topped Vector k=10
(0.920). The two methods are tied 4–4 on pairwise disagreements: Filter3 wins Q31
(Ch21/22 ring-seal chain), Q32 (Ch11/15/16 secret-stipend), Q43 (Ch37 Rammohan
rescue), Q46 (synthesis); Vector k=10 wins Q34 (Ch30/31/33 Lukmini accusation),
Q40 (synthesis), Q42 (Ch22/23/29 prison-break chapters), Q48 (Ch11). Both sides
are symmetric — the LLM judge surfaces chapters dense retrieval drops but misses
others dense search finds — and neither fully closes the cross-reference gap.

**Ceiling (0.970) beats Filter3 by 6 questions** (Q29, Q40 synthesis;
Q32/Q34/Q42/Q48 missed-context) — the same lead as over Vector k=10 — confirming
the Japanese frontier is retrieval recall and synthesis quality on hard cross
questions, not a language barrier.

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
all      Vector k=5        50      38       5         7     0.810     0.720    0.332
all      Extract           50      40       5         5     0.850     0.760    0.807
all      Hybrid k=8        50      45       4         1     0.940     0.940    0.173
all      Ceiling           50      47       3         0     0.970     1.000    1.000
all      GraphRAG local    50      28       8        14     0.640     0.880    0.239
all      GraphRAG global   50       8       8        34     0.240     0.280    0.081
single   GraphRAG local    25      19       1         5     0.780     0.880    0.341
single   GraphRAG global   25       3       1        21     0.140     0.240    0.061
cross    GraphRAG local    25       9       7         9     0.500     0.880    0.137
cross    GraphRAG global   25       5       7        13     0.340     0.320    0.101
```

### GraphRAG local (0.640)

Local search scores 28/50 (0.640) — just below the English run (0.660), below
Filter2 (0.820), and far below Hybrid k=8 (0.940). As in English, the
chapter-retrieval numbers explain why: **recall 0.880** (nearly every gold
chapter is somewhere in the expanded context) but **precision 0.239** — low,
though notably *higher* than English's 0.135. The Japanese local search
expands a narrower context on average (mean 14.5 chapters vs. English's 21.1
out of 37), so the signal-to-noise ratio is somewhat better, but still far
below the pipeline methods.

The failure mode is the same **synthesis-dominated** pattern as English: of
GraphRAG local's 20 losses to Ceiling, **14 are synthesis** (the gold chapter
is present but the answer is wrong or vague) and only 6 are missed context.
GraphRAG local never beats Ceiling and never beats Hybrid k=8 on any question
(0 wins in both pairwise comparisons).

**Single vs. cross diverges from English in opposite directions.** Japanese
local search is *stronger* on single-passage (19/25, 0.780) than English
(15/25, 0.620) — the single-passage synthesis collapse that dominates the
English write-up is much milder here. But it is *weaker* on cross-reference
(9/25, 0.500 vs. English's 13/25, 0.700). Net effect: the two shifts largely
cancel, leaving the overall score close to English's.

### Where the English "structural strengths" don't transfer

The English study found two mechanisms that let GraphRAG local win despite its
low overall score: answering purely from graph traversal with zero retrieved
chapters (Q26, Q28), and recovering both Class A questions (the signet ring and
the Delhi-petition chains) that every Vector depth and Hybrid variant misses.
Neither holds cleanly in Japanese:

- **No question is answered from zero context.** Japanese local search has 5
  zero-context questions (Q9, Q14, Q16, Q30, Q33); all 5 are wrong (4
  incorrect, 1 partial) — compared to English's 6 zero-context questions, 2 of
  which (Q26, Q28) were correct. Q26 in Japanese is answered correctly, but
  only after expanding *all 37 chapters* — it wins on volume, not on pure graph
  traversal.
- **Only one of the two Class A questions is recovered.** Q49 (デリー皇帝の脅威
  が投獄の手段になる経緯, gold Ch2/22) is correct, with all 37 chapters
  expanded — the answer traces the forged-petition scheme in detail, including
  "ルクミニーが持ってきた指輪にある王太子の印章がこの文書に押印されました" (the
  signet on the ring Rukmini brought was stamped onto the document). But Q31
  (asking specifically how the signet ring becomes evidence, gold Ch21–23) is
  **incorrect** even with the same full 37-chapter context: the answer states
  outright that "指輪に関する具体的な言及は見当たりませんでした" (no specific
  mention of the ring was found). The graph clearly encodes the ring→seal→
  forged-petition edge — it surfaces unprompted in Q49's own answer — but Q31's
  query anchors to a different entity path and fails to reach it. The knowledge
  is present in the graph; retrieval is inconsistent across query framings of
  the same fact, which is a sharper failure mode than the clean "graph doesn't
  encode this" story in English.

### GraphRAG global (0.240)

Global search scores 8/50 (0.240) — the weakest of any Japanese method, but
noticeably better than English's global score (0.170). The mechanism is the
same: community summaries operate at the wrong granularity, abstracting away
the chapter-level detail the questions turn on. **Recall 0.280, precision
0.081** — the lowest precision of any method — with a mean of only 7.2
chapters expanded (vs. local's 14.5). Half the questions (26/50) expand *zero*
chapters, and every one of those 26 is incorrect.

Single-passage (3/25, 0.140) is nearly a complete failure, matching English
(2/25, 0.100). Cross-reference (5/25, 0.340) fares a little better than English
(3/25, 0.240), for the same reason as local search: a handful of prominent
cross-cutting themes surface in community summaries even when specific scene
detail does not.

**Q49 recovers even under global search** (correct, with only 4 chapters
expanded) — the Delhi-petition chain is the one fact that survives every
GraphRAG configuration in both languages (local and global, English and
Japanese), suggesting it is unusually well-represented as a graph relationship
regardless of search mode or language.

Within Japanese, local clearly beats global (25 wins to 1) — the same
ordering as English — confirming entity-anchored traversal is the more useful
of the two modes when it is available at all.

### Summary

Neither GraphRAG mode reaches the simplest pipeline method (Vector k=5, 0.810),
let alone Hybrid k=8 (0.940). Local search's language-comparison story is
mixed — slightly weaker overall than English (0.640 vs 0.660), stronger on
single-passage, weaker on cross-reference, and missing the "zero-context
graph traversal" mechanism that made English's local search occasionally
outperform its overall score. Global search is uniformly the weakest method in
both languages. The cost asymmetry is also larger for Japanese: building the
graph and running all 100 queries takes 20h 19m here vs. 13h 6m in English (see
[graphrag-ja/README.md § Measured runtime](../graphrag-ja/README.md#measured-runtime-evo-x2--ryzen-ai-max-395)),
against minutes for the flat embedding index — reinforcing that the
knowledge-graph approach is not a practical alternative to the pipeline for
this task in either language.

## 5. Takeaways and cross-language comparison

- **The headline findings hold across languages.** Single-passage QA is solved
  (Vector 24/25, Extract 25/25); cross-reference is the frontier (14/25, 15/25). The
  gold is sound — the Q29 spot-check confirms the poisoning against the Japanese
  source even though *both* methods missed it here.
- **Extract ≥ Vector holds, more strongly than in English.** Extract 40 vs. Vector 38
  (English tied 39/39), with Extract again at higher chapter precision (0.807 vs.
  0.332). Two independent thorough readers agreeing with the gold is convergent
  evidence the gold is sound.
- **The failure modes are the same.** Extract's losses are Phase 1 recall (Q42,
  Q46) plus Phase 2 synthesis with the chapters in hand (Q33, Q43). Vector's losses
  are top-5 vector recall (Q27, Q31, Q49 — the *same* named-entity questions as
  English) plus answering slips with the gold retrieved (Q21, Q47).
- **Language makes almost no difference to accuracy.** The answer model, embedding
  model, and judge are identical across the two runs, so this is a clean
  language comparison — and the totals match within one or two questions (English
  39/39, Japanese 38/40). The only structural divergence is that the
  both-not-correct set grew from 3 (English) to 7 (Japanese): Q28, Q32, Q48 recur,
  and Q29, Q34, Q36, Q43 are newly shared. This is a redistribution at
  near-constant total accuracy — the two methods' failures correlate more in
  Japanese — and it traces to the Japanese phrasing of specific cross questions
  (most starkly Q29, the covert cause, and Q43, full recall but wrong synthesis),
  not to a capability gap. Retrieval-side findings (which gold chapters dense
  search drops) are identical because the embedding model is the same.
- **Filter3 (0.880) replicates the English ordering** but narrows relative to
  Vector k=10 (0.890 in both languages; English Filter3 topped Vector k=10 by one
  question, Japanese ties V-hybrid k=10). The strict-vs-lenient pattern holds:
  Filter3 beats Filter2 by 4 questions, all missed-context. Filter is still
  impractical at ~1,850× Vector's call cost.
- The retrieval levers are unchanged: Vector's residual losses are dense top-5
  misses on rare proper nouns / second-side facts, the target of `sweep_vector.py`
  and the BM25 hybrid follow-up in [HYBRID.md](../HYBRID.md).
- **GraphRAG's language comparison is mixed, not uniform.** Local search scores
  close to English overall (0.640 vs 0.660) but the composition differs:
  stronger on single-passage (0.780 vs 0.620), weaker on cross-reference (0.500
  vs 0.700), and missing English's "answer from zero retrieved context"
  mechanism entirely (0/5 vs 2/6 zero-context questions correct). Global search
  is weak in both languages but less so in Japanese (0.240 vs 0.170). See
  [§ GraphRAG](#graphrag) above.
