# Lessons for a New QA Evaluation

This repository is a first draft. These are the lessons from it for building a
similar question-answering evaluation on another text.

## Building the question set

The questions and gold answers are built in this order. Steps 1–3 are in
[scripts/](../scripts/README.md#question-set), run from the repository root;
step 4 is in [gold-check/](gold-check/README.md).

| Step | Command | Output |
| :--- | :--- | :--- |
| 0. Freeze the texts | — | `all/<lang>-gemini.jsonl` |
| 1. Generate | `make questions` (first half) | `questions-en.jsonl` |
| 2. Translate | `make questions` (second half) | `questions-ja.jsonl` |
| 3. Remove duplicates | `uv run scripts/check_duplicates.py -l en` | `questions-en-cache.tsv` |
| 4. Check the gold answers | `make facts check claims` in `gold-check/` | `facts.jsonl`, `check-{en,ja}.jsonl` |
| 5. Fix, then freeze | by hand | `questions-{en,ja}.jsonl` |

**0. Freeze the texts.** The questions are written from the texts and the
answer models read them, so they must not change afterwards. Here the
translations `all/<lang>-gemini.jsonl` are frozen; later corrections go to the
`.md` files only, and every check reads the `.jsonl`.

**1. Generate.** [generate_questions.py](../scripts/generate_questions.py)
uploads the whole English text once and runs two multi-turn sessions: one for
*single* questions, each answerable from one scene, and one for *cross*
questions, each needing two or three separated chapters. Each record has the
question, the gold answer, the cited `chapters` and a `rationale` quoting the
text. The sessions are multi-turn so the model sees the questions it already
wrote; memoryless batches kept returning to the same few salient events.

**2. Translate.** [translate_questions.py](../scripts/translate_questions.py)
translates the question, answer and rationale into Japanese, with the
proper-noun dictionary and the cited chapters of the Japanese text as
reference, so the wording follows the text the Japanese answers are read
from. `anchor_id`, `type` and `chapters` are copied, keeping the two files
line-for-line parallel.

**3. Remove duplicates.** [check_duplicates.py](../scripts/check_duplicates.py)
ranks candidate pairs by embedding similarity and has an LLM judge each pair.
Here none of the 182 pairs judged was a duplicate.

**4. Check the gold answers** against every text, as
[gold-check/](gold-check/README.md) does: split each gold answer into short
claims, then check every claim against the full text of the cited chapters in
each language. Read every claim whose verdict differs between the languages
against both texts (and the original, for translations).

**5. Fix, then freeze.** Fix what step 4 found, in the questions as well as
the gold answers, and rerun the check for those questions
(`make redo QIDS=...` in `gold-check/`). Then freeze the questions, their
`chapters` and their `type` (see [GOLD-FIX.md](GOLD-FIX.md#what-may-change)),
and start answering.

## Why the check comes before answering

- **Fixing is free at this point.** Nothing has been answered or graded yet,
  so a corrected gold answer needs no re-grade.
- **The question can still be fixed.** Once answers are generated, the
  question is frozen: some answer models may no longer be runnable, so a
  changed question could not be answered again. A premise the text does not
  support, such as Q8.1 here
  ([gold-check/](gold-check/README.md#gold-answers-that-the-text-does-not-support)),
  can then no longer be fixed.
- **Per-language gaps show up early.** When each language's text is a
  separate translation, a detail one of them lacks can be dropped from the
  question or reworded before it turns into a difference between the
  languages that needs explaining afterwards.
- **The gold answers come from one language.** Here they were written from
  the English text and translated, so nothing in steps 1–3 checks them
  against the Japanese text.

## After answering, fix only real errors

Any change to a gold answer means re-grading every answer to that question
with every judge ([GOLD-FIX.md](GOLD-FIX.md)). Here, fixing the details of 19
gold answers changed 679 verdict files across five judges, and the reports
and documents that quote them, yet moved the scores very little: no judge's
mean moved by more than 0.8 points, a run moved by about 1 point on average,
and the ranking mostly held
([gold-check/](gold-check/README.md#effect-of-the-gold-answer-fix-on-the-scores)).

A fix of details alone is not worth that cost. Once answers exist:

- **Fix and re-grade** when the core answer is wrong, or when neither text
  supports it.
- **Record without re-grading** a difference of wording or detail, such as a
  word the two translations render differently.
- **Still run the check**: it is cheap (150 requests, about 20 minutes here)
  and finds the real errors, and its results answer questions about the
  texts without any fix. Here it showed that the Japanese text lacks no event
  a gold answer asks for, only the wording of six claims.

Individual runs still move by up to about 4 points from such a fix, so a
difference of a few points between two models is within that noise and
should not be read as a ranking.
