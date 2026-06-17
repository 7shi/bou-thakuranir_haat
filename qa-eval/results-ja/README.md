# Disagreement case study: RAG vs. Extract (Japanese)

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

RAG scores 38/50, Extract 40/50 (weighted 0.810 vs. 0.850) — Extract edges ahead,
where the English run tied 39/39. But the gap lives entirely in the
**cross-reference** half. On the **single-passage** half RAG scores 24/25 and
Extract 25/25; on the **cross-reference** half they drop to 14/25 and 15/25. The
one single-passage miss (Q21, RAG incorrect) is an *answering* failure with the
correct passage in hand, not a retrieval failure. So single-passage QA is
essentially solved by either method; the open problem is multi-chapter
integration — the same conclusion as the English run.

## Verdict agreement matrix

Rows = RAG verdict, columns = Extract verdict.

| | Ext correct | Ext partial | Ext incorrect | RAG total |
| --- | --- | --- | --- | --- |
| **RAG correct** | 35 | 2 | 1 | 38 |
| **RAG partial** | 1 | 2 | 2 | 5 |
| **RAG incorrect** | 4 | 1 | 2 | 7 |
| **Ext total** | 40 | 5 | 5 | 50 |

The two off-diagonal blocks analyzed below:

- **RAG correct / Extract not correct** — 3 questions (§2): two Extract Phase 1
  retrieval misses plus one where Extract held both gold chapters but
  mis-synthesized.
- **Extract correct / RAG not correct** — 5 questions (§3): three RAG vector
  retrieval misses and two where RAG retrieved the gold chapter but answered
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
cause-of-departure threads even with the gold chapters retrieved (RAG used 16,17;
Extract used 14–17) — the same model gets this right in English, so the
confusion is specific to the Japanese phrasing of the two threads. A shared answering
failure, not a gold problem.

## 2. RAG correct / Extract not correct (3 questions)

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
  found." RAG retrieved Ch22 by vector similarity and reconstructed the
  fire-diversion prison break correctly.
- **Q46** (gold 21,27,31) kept 27 and 31 but dropped Ch21, the chapter that
  establishes the *playful* money-borrowing between Sitaram and Rukmini. Extract
  explicitly denied that premise ("提示されたテキストに『戯れのような金銭のやり取り』
  に関する記述はありません") and was graded partial; RAG retrieved all three gold
  chapters and traced the full escalation.

### 2b. Phase 2 synthesis shortfall (Q33)

Q33 (the song "私だけが、ただ一人残された", gold 27,28) is different: Phase 1 **kept
both gold chapters**, yet the answer was only partial. RAG correctly named both
contrasting singing contexts (alone at the Rajgarh sunset; to Bibha in Surma's
empty room at Jessore); Extract got the first but *invented* the second — a scene
where Khan Sahib asks after Basanta Ray, followed by an abrupt shift to a cheerful
song — missing the gold's discovery of death and shared grief. The chapters were
in hand; the answer model just synthesized the second half wrong.

## 3. Extract correct / RAG not correct (5 questions)

| Q | type | gold ch | RAG used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 27 | cross | 2,4,33 | 2,5,10,12,28 | incorrect | retrieval miss (Ch33) |
| 31 | cross | 21,22,23 | 25,27,33,34 | incorrect | retrieval miss (all gold) |
| 49 | cross | 2,22 | 2,10,12 | incorrect | retrieval miss (Ch22) |
| 21 | single | 5 | **2,5,8,12** | incorrect | retrieved Ch5, wrong incident |
| 47 | cross | 29,31 | **11,27,29,31** | partial | retrieved gold, short answer |

### 3a. Vector retrieval misses (27, 31, 49)

Three are RAG retrieval misses: a gold chapter ranked outside the top-5, so the
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

The other two RAG losses are *not* retrieval misses — the gold chapter was in the
context and the answer still fell short:

- **Q21** (single, gold Ch5): RAG retrieved Ch5 but answered with *different*
  offenses (guards failing to attend the prince; reporting his disappearance)
  instead of the two the question asks for (losing a letter; sending a man to
  Umesh Ray instead of going personally). Extract named both exactly. This is the
  one single-passage question RAG missed, and — as in the English run — it is an
  answering failure, not a retrieval one.
- **Q47** (cross, gold 29,31): RAG retrieved *both* gold chapters but only
  partially synthesized — it described the fire-as-distraction and the faked-death
  props yet omitted the actual extraction (Sitaram opening the cell and spiriting
  Udayaditya onto the boat). Extract captured the two-phase strategy and was
  graded correct.

## 4. Both not correct (7 questions)

| Q | gold ch | RAG used | RAG | Extract used | Ext | shared failure |
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
  prison-fire rescue of Udayaditya) and was graded incorrect, while RAG (missing
  Ch37) got the Jessore rope-rescue but fabricated the Chandradwip half. A
  full-recall Phase 2 failure.
- **Q34, Q36** are coverage-plus-synthesis partials: each method retrieved some
  gold chapters but both omitted the load-bearing fact (Lukmini bursting into the
  hall to expose Basanta Ray, Q34; Mangala sneaking into Udayaditya's room to
  demand his love, Q36).

None of the seven is a gold problem; all are coverage or synthesis failures on
hard cross questions.

## 5. Takeaways and cross-language comparison

- **The headline findings hold across languages.** Single-passage QA is solved
  (RAG 24/25, Extract 25/25); cross-reference is the frontier (14/25, 15/25). The
  gold is sound — the Q29 spot-check confirms the poisoning against the Japanese
  source even though *both* methods missed it here.
- **Extract ≥ RAG holds, more strongly than in English.** Extract 40 vs. RAG 38
  (English tied 39/39), with Extract again at higher chapter precision (0.807 vs.
  0.332). Two independent thorough readers agreeing with the gold is convergent
  evidence the gold is sound.
- **The failure modes are the same.** Extract's losses are Phase 1 recall (Q42,
  Q46) plus Phase 2 synthesis with the chapters in hand (Q33, Q43). RAG's losses
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
- The retrieval levers are unchanged: RAG's residual losses are dense top-5
  misses on rare proper nouns / second-side facts, the target of `sweep_rag.py`
  and the BM25 hybrid follow-up in [PLAN.md](../PLAN.md).
