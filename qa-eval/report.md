# Disagreement case study: RAG vs. Extract

A manual, per-question analysis of where the two methods **disagree**, to
complement the aggregate table from [`report.py`](README.md#reportpy). The goal
is to attribute each disagreement to a concrete failure mode and, along the way,
spot-check whether the gold answers are sound.

Run: answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`, 100 questions
(`questions-en.jsonl`).

## Verdict agreement matrix

Rows = RAG verdict, columns = Extract verdict.

| | Ext correct | Ext partial | Ext incorrect | RAG total |
| --- | --- | --- | --- | --- |
| **RAG correct** | 72 | 4 | 5 | 81 |
| **RAG partial** | 7 | 1 | 0 | 8 |
| **RAG incorrect** | 8 | 1 | 2 | 11 |
| **Ext total** | 87 | 6 | 7 | 100 |

The two off-diagonal blocks analyzed below:

- **RAG correct / Extract incorrect** — 5 questions (§2): mostly Extract Phase 1
  retrieval misses.
- **Extract correct / RAG incorrect** — 8 questions (§3): mostly RAG vector
  retrieval misses.

Only **2** questions are wrong under *both* methods (40, 43); these are examined
in §4. One (Q40) is a genuine gold/grading borderline; the other (Q43) is a
shared retrieval miss. The rest of the disagreements are method failures, not
gold problems.

## 1. Gold validity spot-check (Q23)

Q23 — "How did Udayaditya's secret financial support for the dismissed guards
lead to his wife Surma's death?" (gold chapters 15–17).

Every claim in the gold answer is grounded in the source text (`all/en-gemini`):

| Gold claim | Source |
| --- | --- |
| Secret stipends discovered → Pratapaditya orders Surma to her father's house | **Ch16**: "When word of the secret stipends reached Pratapaditya's ears... he sent an order... that Surma must go to her paternal home" |
| Mahishi seeks a love potion to win the Yubaraj's heart back before her departure | **Ch17**: "to win the Yubaraj's heart back from Surma before sending her away. She sent Matangini to secretly fetch medicine from Mangala" |
| The "potion" was actually a poison | **Ch17**: "Mangala took various roots and spent the entire night... to prepare a **poison**" |
| Surma consumed it and died | **Ch17** (closing scene): "the physician said, 'It is over!'" |

The gold correctly reconstructs the narrative's true causal chain (Mahishi's
love-potion request → Mangala's swap to poison), **not** the in-palace rumor
that "Surma was dying by her own hand, having taken poison." The gold is sound;
the disagreements on Q23 below are method failures.

## 2. RAG correct / Extract incorrect (5 questions)

| Q | gold ch | Extract used | failure |
| --- | --- | --- | --- |
| 23 | 15,16,17 | 16 | Phase 1 miss (Ch17, the death, returned `None`) |
| 46 | 15,16 | 12,16 | Phase 1 miss (Ch15) → answered a different incident |
| 51 | 2 | 5 | Phase 1 miss (Ch2, the justification) |
| 53 | 16,17 | — | Phase 1 miss (no chapter retained at all) |
| 79 | 19 | **19** | **Phase 2** premise rejection (see below) |

### 2a. Phase 1 false negatives (23, 46, 51, 53)

Extract makes a per-chapter binary call in Phase 1: extract the relevant
passage, or emit `None`. A wrong `None` is unrecoverable — that chapter never
reaches Phase 2. In all four cases the gold chapter was dropped, so Phase 2
answered "the text does not mention this." RAG retrieved the same gold chapters
by vector similarity and answered correctly. Vector retrieval is harder to make
miss a relevant scene than a binary per-chapter judgment is.

Q23 detail: Phase 1 kept Ch16 (the order to send Surma away) but returned `None`
for **Ch17** (the poison and death). RAG's top-5 hits included `17:1` at cosine
**0.554** — near the bottom of the five, yet enough to pull the death chapter
into context.

### 2b. Phase 2 premise rejection (Q79)

Q79 — "What was Ramchandra Ray's internal conflict regarding his wife, Vibha,
after his humiliating escape from Jessore?" (gold chapter 19).

Here Phase 1 was **excellent**: its Ch19 summary captured the gold answer almost
verbatim (desire for Vibha vs. fear of ridicule vs. revenge against
Pratapaditya). But the Phase 2 answer model **discarded** it, replying:

> The provided text does not mention a "humiliating escape from Jessore".

It fixated on verifying the question's framing phrase, which did not appear
verbatim in the excerpts, and refused to answer despite holding a correct,
relevant summary. This is a different lever than the Phase 1 `None` threshold —
it is the Phase 2 answering prompt over-validating the question's wording.

Ironically, RAG answered Q79 correctly **without** the gold chapter (its hits
were 10, 26, 37, 24, 6 — no Ch19), synthesizing the answer from the same theme
recurring in other chapters. This also suggests the gold's single-chapter label
`[19]` is narrower than where the relevant content actually lives.

## 3. Extract correct / RAG incorrect (8 questions)

| Q | gold ch | RAG used (miss) | failure |
| --- | --- | --- | --- |
| 25 | 23 | 9,24,36,37 (**23**) | retrieval miss → "context does not state" |
| 49 | 23 | 6,9,24,36,37 (**23**) | retrieval miss → vague "Vibha did not wish to come" |
| 57 | 23 | 6,9,24,36,37 (**23**) | retrieval miss → vague |
| 77 | 33 | 2,4,5,10,28 (**33**) | retrieval miss → answered the wrong (earlier) part |
| 82 | 1 | 2,29,33,34 (**1**) | retrieval miss → "context does not mention" |
| 92 | 9 | 8,9,10,12,19 (none) | **empty answer** despite correct retrieval |
| 95 | 16 | 2,12,15,19 (**16**) | retrieval miss → confident wrong answer from Ch15 |
| 99 | 31,33 | 4,12,27,28,33 (**31**) | retrieval miss (Ch31) → "no information" |

### 3a. Vector retrieval misses (25, 49, 57, 77, 82, 95, 99)

Seven of the eight are RAG retrieval misses: the gold chapter ranked outside the
top-5, so the answerer never saw it. Two sub-flavors:

- **Honest abstention** (25, 82, 99): RAG correctly says it cannot find the
  answer — safer, but still scored incorrect.
- **Confident wrong answer** (77, 95): RAG answered from a *related* chapter it
  did retrieve. E.g. Q95 (consequence of discovering the stipends, gold Ch16 =
  order to send Surma away) was answered from Ch15 ("no more financial help") —
  plausible but wrong.

**Systematic gap — the Ch23 / Vibha cluster (25, 49, 57).** All three ask why
Vibha refused to go to Chandradwip (gold Ch23). RAG missed Ch23 on **all three**
— it consistently retrieved chapters 9, 24, 36, 37 instead, with Ch23's
segments (`23:1`, `23:2`) never breaking into the top-5. This is not random: the
embedding for that content ranks ~6th or lower for this question phrasing.
Exactly the case [`sweep_rag.py`](PLAN.md) is meant to diagnose — would a larger
`k` (or a recall-oriented threshold) recover Ch23?

### 3b. Empty generation despite correct retrieval (Q92)

Q92 retrieved the gold chapter (`9:2` at 0.623) — retrieval succeeded — but the
answer field is the **empty string**. The judge even noted the candidate was
blank. This is a pure generation failure (the answer model emitted nothing),
unrelated to retrieval, and the mirror image of Q79's Phase 2 failure on the
Extract side: both methods occasionally throw away good context at the
answering step.

## 4. Both incorrect (Q40, Q43)

The two questions wrong under both methods — the only candidates for a gold
problem rather than a method failure.

### 4a. Q40 — gold defensible but one-sided (grading too harsh)

Q40 — "Why did Udayaditya willingly take an oath to renounce the throne of
Jessore forever?" (gold chapter 34). **Not a retrieval miss**: both methods read
Ch34 (Extract used `[34]`, RAG used `[1,33,34]`). They disagree with the gold on
*interpretation*, and both gave the same alternative — Udayaditya's sense of
guilt, weakness, and unworthiness.

Ch34 actually contains **both** motivations explicitly:

- **Unworthiness / guilt** (what both methods extracted, and the chapter's most
  prominent surface text): his monologue to Muktiyar — "I am a weak coward... those
  who were the joy of the world... were destroyed for my sake. No more, I am
  taking my leave of this world" — and to Pratapaditya, "No, Maharaj, I am not
  worthy."
- **Freedom / Kashi / oath-as-price** (what the gold emphasizes): "I do not want
  your kingdom—grant me release from your throne—this is my plea"; "Abandon me, I
  will leave for Kashi right now"; the oath at Ma-Kali's feet.

So the gold is well-grounded but **narrow** — it foregrounds the
transactional/narrative reason and omits the unworthiness motivation that
dominates the chapter's actual text. The candidates are not fabrications. The
judge's "no factual overlap" is too harsh: "not worthy of the kingdom" appears
in *both* the gold rationale and the candidates. This is the one question where
the gold answer (or at least the grading) genuinely deserves revision toward a
both-motivations answer.

### 4b. Q43 — gold sound, shared retrieval miss on Ch1

Q43 — "How did Udayaditya learn about the assassination plot against Basanta
Ray, and what actions did he take?" (gold chapters 1, 3). The gold (Vibha rushes
to warn him in Ch1; he arms himself and rides to the Simultali inn in Ch3) is
clearly grounded in the source. Both methods missed **Ch1** (Vibha's warning):
Extract's Phase 1 returned `None` for it (keeping only Ch3); RAG missed both Ch1
and Ch3. Lacking the warning scene, both misattributed "how he learned" to the
Pathan's later confession *at* Simultali — a downstream event, not the source of
his knowledge. Extract at least recovered the Simultali ride from Ch3 but buried
it in a list of secondary actions. Gold is fine; this is a dual retrieval
failure, the same two levers as §2/§3.

## 5. Takeaways

- **The gold is sound with one caveat.** Disagreements are overwhelmingly method
  failures. Of the 2/100 questions wrong under both methods, only **Q40** is a
  real gold/grading issue (the chapter supports a both-motivations answer the
  gold and judge under-credit); Q43 is a shared retrieval miss.
- **Extract's weakness is Phase 1 recall** — a `None` on a gold chapter is
  unrecoverable (4 of its 5 unique losses). Lever: the Phase 1 extraction prompt
  / `None` threshold. Plus one Phase 2 premise-rejection (Q79).
- **RAG's weakness is top-5 retrieval recall** — the gold chapter ranking just
  outside `k=5` (7 of its 8 unique losses), including a systematic miss on the
  Ch23/Vibha cluster. Lever: `-k` / `-N` / a score threshold, the target of
  `sweep_rag.py`.
- **Both share a rare answering failure** (Q79 Extract, Q92 RAG): good context
  retrieved, then discarded or left blank by the answer model.
- This is consistent with the aggregate result (`report.py`: Extract 87 vs RAG
  81 correct): Extract's exhaustive reading beats vector top-5 on recall overall,
  but loses specific questions where Phase 1 misjudges relevance.
