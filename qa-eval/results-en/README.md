# Disagreement case study: RAG vs. Extract

A manual, per-question analysis of where the two methods **disagree**, to
complement the aggregate table from [`report.py`](../README.md#reportpy). The goal
is to attribute each disagreement to a concrete failure mode and, along the way,
spot-check whether the gold answers are sound.

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 50 questions
(`questions-en.jsonl`, 25 single-passage + 25 cross-reference).

## Where the difficulty lives: single vs. cross

The two methods tie on accuracy (39/50 correct, weighted 0.830 each), but the tie
hides the real story. On the **single-passage** half both score 24/25; on the
**cross-reference** half both drop to 15/25. Every retrieval and synthesis failure
below is a cross question except two single misses (Q21, Q22), and even those two
are *answering* failures, not retrieval failures — the correct passage was in hand
both times. So single-passage QA is essentially solved by either method; the open
problem is multi-chapter integration.

## Verdict agreement matrix

Rows = RAG verdict, columns = Extract verdict.

| | Ext correct | Ext partial | Ext incorrect | RAG total |
| --- | --- | --- | --- | --- |
| **RAG correct** | 31 | 4 | 4 | 39 |
| **RAG partial** | 3 | 1 | 1 | 5 |
| **RAG incorrect** | 5 | 0 | 1 | 6 |
| **Ext total** | 39 | 5 | 6 | 50 |

The two off-diagonal blocks analyzed below:

- **RAG correct / Extract not correct** — 8 questions (§2): mostly Extract Phase 1
  retrieval misses, plus a few where Extract held the right chapters but only half
  synthesized them.
- **Extract correct / RAG not correct** — 8 questions (§3): six RAG vector
  retrieval misses and two where RAG retrieved the gold chapter but answered the
  wrong thing.

Only **3** questions are wrong under *both* methods (28, 32, 48); these are
examined in §4. All three are shared coverage/synthesis failures on cross
questions, not gold problems.

## 1. Gold validity spot-check (Q29)

Q29 — "While Pratapaditya's official decree aims to separate Surma and Udayaditya
by exiling her to her father's house, what covert action actually causes her
departure?" (gold chapters 16, 17).

Every claim in the gold answer is grounded in the source text (`all/en-gemini`):

| Gold claim | Source |
| --- | --- |
| Pratapaditya orders Surma to her father's house (the surface decree) | **Ch16**: the order that "Surma must go to her paternal home" |
| The Mahishi has Matangini secretly fetch "medicine" from Mangala to win the Yubaraj back | **Ch17**: "She sent Matangini to secretly fetch medicine from Mangala" |
| The "medicine" was actually a poison brewed by Mangala (Rukmini) | **Ch17**: "Mangala took various roots and spent the entire night... to prepare a **poison**" |
| Surma consumes it and dies — the true cause of her departure | **Ch17** (closing scene): "the physician said, 'It is over!'" |

The gold correctly distinguishes the **surface decree** (exile) from the **covert
cause** (poisoning), which is exactly what the question asks. Extract, reading
chapters 15–17 in full, reconstructed the same covert chain and was graded
correct. RAG retrieved chapters 16 and 17 too, but its answerer stopped at the
surface decree ("Pratapaditya threatens to have Udayaditya imprisoned if Surma
does not leave") — a reading failure, not a gold problem. Two independent paths
agreeing with the gold on the covert cause is convergent evidence the gold is
sound.

## 2. RAG correct / Extract not correct (8 questions)

| Q | type | gold ch | Extract used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 22 | single | 11 | **11** | incorrect | Phase 2 misattribution (see 2c) |
| 26 | cross | 11,29 | 15,30 | incorrect | Phase 1 miss (both gold chapters) |
| 34 | cross | 30,31,33 | 2 | incorrect | Phase 1 miss (kept one wrong chapter) |
| 42 | cross | 22,23,29 | — | incorrect | Phase 1 miss (nothing retained) |
| 40 | cross | 13,27 | 13 | partial | Phase 1 miss (Ch27) |
| 50 | cross | 8,18,23 | 6,8,12,18 | partial | Phase 1 miss (Ch23) |
| 30 | cross | 23,24,36 | **23,24,26,36** | partial | synthesis (had the chapters) |
| 33 | cross | 27,28 | **27,28** | partial | synthesis (had the chapters) |

### 2a. Phase 1 false negatives (26, 34, 42, 40, 50)

Extract makes a per-chapter binary call in Phase 1: extract the relevant passage,
or emit `None`. A wrong `None` is unrecoverable — that chapter never reaches Phase
2. In the worst cases the gold chapters were dropped entirely, so Phase 2 answered
that the text does not cover the question:

- **Q34** (gold 30,31,33) kept only Ch2 and concluded "the provided text does not
  explain a causal link... the order to kill Basanta Ray was given the day before
  the escape" — the exact causal chain the gold draws from Ch33 was thrown away.
- **Q42** (gold 22,23,29) retained *nothing* and returned "No relevant content
  found."
- **Q26** (gold 11,29) kept the wrong chapters (15, 30) and replied that the
  reversal "cannot be fully established."

Q40 and Q50 are the milder, partial version: one of the two gold chapters
survived, so Extract answered half the question (Q40 caught the sitar in Jessore,
Ch13, but missed the Raigarh half in Ch27). RAG retrieved the same gold chapters
by vector similarity in every case and answered correctly — vector retrieval is
harder to make miss a relevant scene than a binary per-chapter judgment is.

### 2b. Phase 2 synthesis shortfall (30, 33)

Q30 and Q33 are different: Phase 1 **kept every gold chapter** (Q30 used
23,24,36; Q33 used 27,28), yet the answer was only partial. Here the loss is in
Phase 2 synthesis, not retrieval — Q30 named the spiteful re-marriage but dropped
the gold's punchline that Vibha arrives *on the wedding day* and is rejected; Q33
explained the song's meaning but under-specified the two contrasting singing
contexts. The chapters were in hand; the answer model just didn't integrate them
fully. RAG happened to phrase the same material more completely.

### 2c. Phase 2 misattribution on a single question (Q22)

Q22 — "what specific item does Udayaditya use to tie up the compliant guard,
Sitaram?" (gold chapter 11; gold answer "His own cloth"). Phase 1 kept the right
chapter (Ch11), but the Phase 2 answer flipped the ownership: "**Sitaram's** own
cloth." The single fact the question turns on — *whose* cloth — was inverted, so
the judge scored it incorrect. RAG answered "his own cloth" verbatim. This is the
only single-passage question Extract missed, and it is an answering slip, not a
retrieval one.

## 3. Extract correct / RAG not correct (8 questions)

| Q | type | gold ch | RAG used | verdict | failure |
| --- | --- | --- | --- | --- | --- |
| 31 | cross | 21,22,23 | 12,27,29,33,34 | incorrect | retrieval miss (all gold) |
| 36 | cross | 1,17,21 | 1,21,33,34 | incorrect | retrieval miss (Ch17) |
| 49 | cross | 2,22 | 2,5,8,12 | incorrect | retrieval miss (Ch22) |
| 27 | cross | 2,4,33 | 2,4,5,10 | partial | retrieval miss (Ch33) |
| 43 | cross | 11,37 | 7,11,19,24 | partial | retrieval miss (Ch37) |
| 45 | cross | 18,25 | 1,16,21,25,29 | partial | retrieval miss (Ch18) |
| 21 | single | 5 | **2,5,12** | incorrect | retrieved Ch5, wrong incident |
| 29 | cross | 16,17 | **13,15,16,17,21** | incorrect | retrieved gold, surface answer |

### 3a. Vector retrieval misses (31, 36, 49, 27, 43, 45)

Six are RAG retrieval misses: a gold chapter ranked outside the top-5, so the
answerer never saw it. Two flavors:

- **Honest abstention → incorrect** (31, 49): RAG correctly says it cannot find the
  answer. Q31 (how the signet ring becomes evidence, gold 21–23) retrieved none of
  the three gold chapters and replied "the provided text does not mention a signet
  ring." Extract, reading Ch21–22, reconstructed the ring→seal→forged-petition
  chain in full.
- **Half answer → partial** (27, 43, 45): the question has two sides and RAG
  retrieved only one chapter. Q27 (Pratapaditya's failed *and* successful plot to
  kill Basanta Ray) got the failed Simultali plan from Ch2/4 but missed the
  successful Muktiyar-Khan method in Ch33; Q43 got the Jessore rescue (Ch11) but
  missed the Chandradwip one (Ch37). Extract retained both sides each time.

### 3b. Retrieval hit, wrong answer (21, 29)

The other two RAG losses are *not* retrieval misses — the gold chapter was in the
context and the answerer still went wrong:

- **Q21** (single, gold Ch5): RAG retrieved Ch5 but answered with a *different*
  reprimand entirely — guards failing to follow Prince Udayaditya — instead of the
  two offenses the question asks for (losing a letter; sending a man to Umesh Ray).
  Extract, given the same chapter, named both offenses exactly. The one
  single-passage question RAG missed, and like Q22 it is an answering failure.
- **Q29** (cross, gold 16,17): analyzed in §1 — RAG retrieved both gold chapters
  but reported the surface decree rather than the covert poisoning.

## 4. Both incorrect (Q28, Q32, Q48)

The three questions wrong under both methods — all cross-reference, all shared
coverage/synthesis failures rather than gold problems.

### 4a. Q28 — two-location question, each method finds one or none

Q28 — "In what two distinct locations and disguises does Ramai Bhand face physical
retaliation from Rammohan Mal...?" (gold chapters 9, 37). The gold names both
beatings (the Jessore inner quarters in disguise; the Chandradwip court). RAG
retrieved neither gold chapter and abstained; Extract kept only Ch37 and concluded
"the provided text only mentions one location." A two-part answer needs both
chapters, and neither method assembled the pair — RAG via vector miss, Extract via
a Phase 1 `None` on Ch9.

### 4b. Q32 — both miss the central mechanism, RAG also hallucinates

Q32 — "How do the repercussions of Ramchandra Ray's midnight escape indirectly
trigger the decree for Surma to be exiled?" (gold chapters 11, 15, 16). The gold's
load-bearing middle step is the **secret stipend** Udayaditya and Surma pay the
dismissed guards, which Pratapaditya discovers. Both methods reached the final
trigger (the discovered stipends → exile) but skipped *why* the guards needed
support. RAG additionally invented an unsupported detail (Basanta Ray bribing
Bhagavat to lie); Extract attributed the exile to vague "psychological tactics."
Both partial.

### 4c. Q48 — both miss the specific paranoid interpretation

Q48 — "...how does Ramchandra Ray later interpret his brother-in-law's behavior in
his own court?" (gold chapters 11, 19). The gold's key fact is that Ramchandra,
seeing Udayaditya whisper to a servant, paranoically assumes the prince is
plotting to insult him. Both methods caught Ramchandra's ingratitude but missed
the specific whisper-to-servant interpretation; both instead claimed he thought
Udayaditya acted only for his sister's sake. RAG partial, Extract incorrect.

## 5. Takeaways

- **Single-passage QA is solved; cross-reference is the frontier.** Both methods
  score 24/25 on single questions and 15/25 on cross. Every retrieval and
  synthesis failure above is a cross question except Q21 and Q22, and those two are
  answering slips with the correct passage already retrieved.
- **The gold is sound.** Disagreements are method failures, not gold problems. The
  Q29 spot-check shows the gold correctly separates a surface decree from the
  covert cause, confirmed independently by Extract's full reading.
- **Extract's weakness is Phase 1 recall** — a `None` on a gold chapter is
  unrecoverable (5 of its 8 unique losses, three of them total misses). A secondary
  loss is Phase 2: twice it held every gold chapter yet only half-synthesized
  (Q30, Q33), and once it inverted a single fact (Q22).
- **RAG's weakness is top-5 retrieval recall** — the gold chapter ranking just
  outside `k=5` (6 of its 8 unique losses, including three half-answers on
  two-sided questions). Lever: `-k` / `-N` / a score threshold, the target of
  [`sweep_rag.py`](../PLAN.md). Twice (Q21, Q29) RAG retrieved the gold chapter and
  still answered wrong — an answering failure no retrieval tuning fixes.
- This is consistent with the aggregate result (`report.py`: 39 correct each,
  Extract recall 0.740 ≥ RAG 0.720 at much higher precision): exhaustive reading
  and vector top-5 land in the same place overall, but split on which specific
  cross-reference questions each can assemble.
