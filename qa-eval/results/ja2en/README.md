# Where the Japanese gap comes from

Under Ternary ([../TERNARY.md](../TERNARY.md)), as under OpenAI and Jev, the
same model's Japanese Ceiling answers score several points below its English
ones. This directory tests where that gap lies, using the Japanese answers of
11 models graded three ways:

- against the Japanese question and gold answer, as in `../ternary/` (**ja**);
- against the English question and gold answer, the originals the Japanese ones
  were translated from (**xling**);
- translated into English, against the English question and gold answer
  (**ja→en**).

If xling came back to the English score (**en**), the gap would lie in the
Japanese gold answers; if ja→en came back, it would lie in grading Japanese
text; if neither does, it lies in the answers themselves. **retest** grades
the English answers a second time to show how far the judge moves on its own.

## Setup

- **Models**: the 11 models outside the weakest five whose Japanese score
  falls furthest below English under OpenAI and Jev (mean ja − en ≤ −5.5).
  They were chosen without Ternary so that its own noise does not select them.
  The list is `MODELS` in [Makefile](Makefile).
- **Judge**: [judge-ternary.py](../../judge-ternary.py) unchanged
  (`openai:gpt-6-luna`, reasoning off, scheme `ternary@70c12cb1`), with `-l en`
  for the English question and gold answer. en and ja are the existing
  verdicts in `../ternary/`.
- **Translation**: [translate.py](translate.py), `openai:gpt-6-luna` with
  reasoning off, told to translate faithfully without adding, dropping or
  correcting anything. It sees the English question for the spelling of names,
  but not the gold answer. `gpt-6-luna` is the strongest translator into
  Japanese in multilingual-reader's comparison, the nearest available measure
  for this direction.
- **Comparison**: [compare.py](compare.py) (`make compare`).

| Step | Output | Requests | Wall time | Input | Output |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `make xling` | `xling/*.tsv` | 550 | 9m 36.7s | 257,244 | 2,750 |
| `make translate` | `*.jsonl` | 550 | 15m 12.7s | 128,364 | 45,944 |
| `make judge` | `ternary/*.tsv` | 550 | 10m 36.9s | 217,420 | 2,750 |
| `make retest` | `retest/*.tsv` | 550 | 9m 50.5s | 211,189 | 2,750 |

Token counts are from the runs' totals; the translation run logged usage for
549 of its 550 requests.

## Results

Scores are `(correct + 0.5 · partial) / 50` in percent:

| Model | en | ja | xling | ja→en | retest | ja − en | xling − en | ja→en − en | retest − en |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `copilot_claude-haiku-4.5` | 93 | 87 | 87 | 82 | 93 | −6 | −6 | −11 | +0 |
| `copilot_claude-sonnet-5` | 93 | 91 | 89 | 81 | 93 | −2 | −4 | −12 | +0 |
| `copilot_mai-code-1.1-flash` | 91 | 77 | 79 | 76 | 92 | −14 | −12 | −15 | +1 |
| `ollama_gemma4_12b-it-qat` | 79 | 72 | 72 | 70 | 82 | −7 | −7 | −9 | +3 |
| `openai_gpt-6-sol` | 97 | 93 | 92 | 92 | 97 | −4 | −5 | −5 | +0 |
| `openai_gpt-6.1-sol` | 96 | 96 | 93 | 92 | 98 | +0 | −3 | −4 | +2 |
| `opencode_longcat-2.5-preview-free` | 92 | 88 | 89 | 85 | 94 | −4 | −3 | −7 | +2 |
| `opencode_mimo-v2.5-free` | 97 | 90 | 85 | 83 | 97 | −7 | −12 | −14 | +0 |
| `opencode_mimo-v2.6-flash-free` | 96 | 87 | 91 | 84 | 97 | −9 | −5 | −12 | +1 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 88 | 78 | 78 | 75 | 85 | −10 | −10 | −13 | −3 |
| `openrouter_stealth_space-bunny-alpha` | 91 | 78 | 79 | 74 | 91 | −13 | −12 | −17 | +0 |
| **Mean** | 92.09 | 85.18 | 84.91 | 81.27 | 92.64 | −6.91 | −7.18 | −10.82 | +0.55 |

| | Correct | Partial | Incorrect | Mean excl. Q7, Q9, Q12, Q25 |
| :--- | ---: | ---: | ---: | ---: |
| en | 468 | 77 | 5 | 91.40 |
| retest | 475 | 69 | 6 | 92.00 |
| ja | 406 | 125 | 19 | 84.09 |
| xling | 400 | 134 | 16 | 84.68 |
| ja→en | 365 | 164 | 21 | 83.89 |

The last column leaves out the four questions where translation itself costs
points (see below).

### The judge is stable

| en \ retest | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 462 | 6 | 0 |
| **partial** | 13 | 63 | 1 |
| **incorrect** | 0 | 0 | 5 |

*Agreement: 530 / 550 (96.4%)*

Grading the same answers again changes 20 of 550 verdicts, and a model's
score by 1.1 points on average (at most 3). Differences of a few points per
model are within this noise; the mean differences below are not.

### The Japanese gold answers are not the cause

| ja \ xling | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 367 | 38 | 1 |
| **partial** | 33 | 92 | 0 |
| **incorrect** | 0 | 4 | 15 |

*Agreement: 474 / 550 (86.2%)*

Grading the Japanese answers against the English gold instead of the Japanese
one leaves the mean where it was (85.18 → 84.91). Individual verdicts move
more than in retest (76 changes, a model's score by 1.7 points on average), but
in both directions about equally (38 vs. 33), so the Japanese gold answers
are faithful to the English ones and the judge does not grade them harder.

### Translation costs points on short quoted answers

| ja \ ja→en | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 327 | 72 | 7 |
| **partial** | 38 | 86 | 1 |
| **incorrect** | 0 | 6 | 13 |

*Agreement: 426 / 550 (77.5%)*

ja→en falls a further 3.6 points below xling. Of the 68 verdicts that drop
from xling to ja→en, 23 are on four short questions whose gold answer is a
fixed phrase, and none of them rise there:

| Question | Gold answer | Models dropping | Example translation |
| :--- | :--- | ---: | :--- |
| Q25 | "Grand-uncle, beware!" | 11 | "Great-uncle, watch out!" |
| Q9 | A parakeet. | 10 | "Parrot", "A parrot." |
| Q7 | A pipeful of tobacco. | 5 | "A puff of tobacco.", "A smoke." |
| Q12 | Mother Nikasha. | 4 | "Lady Nikasha" |

The Japanese answer is right, but its translation picks other words than the
gold answer's (*inko* covers both parakeet and parrot, and *-sama* reads as
"Lady"), which the judge counts as *partial*. Translation is therefore a
lossy route for answers like these, and ja→en is read with those four
questions left out.

### The gap lies in the answers

Without Q7, Q9, Q12 and Q25, ja, xling and ja→en all score about 84 (84.09,
84.68, 83.89), against 91.40 for en. Changing the gold answer to English
(ja → xling) and then the answer itself to English (xling → ja→en) both leave
the score where it was, while the English answers of the same models score
about 7 points higher. The gap is neither in the Japanese gold answers nor in
how Japanese is graded: the Japanese answers lack details of the gold answer
that the English ones give.

Across all 50 per-model Ceiling runs the gap is significant under the judges
that hold to the gold answer's details, and absent under Nimble:

| Judge | ja < en | ja > en | Tie | Mean ja − en | Sign test |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Ternary | 44 | 2 | 4 | −5.34 | p = 3 × 10⁻¹¹ |
| OpenAI | 41 | 2 | 7 | −4.46 | p = 2 × 10⁻¹⁰ |
| Jev | 45 | 3 | 2 | −4.54 | p = 1 × 10⁻¹⁰ |
| Nimble | 24 | 22 | 4 | −1.42 | p = 0.88 |

Without the weakest five models, p stays below 10⁻⁸ for Ternary, OpenAI and
Jev. The gap is therefore a lack of the gold answer's details, which only the
detail-oriented judges count, rather than answers that are worse by any
measure.

### What this does not separate

The Japanese answers differ from the English ones in two ways at once, and
every column above shares both:

- **They read a different text.** The English and Japanese texts are separate
  machine translations of the Bengali original (Gemini 2.5 Pro). The questions
  and gold answers were written from the English text
  ([generate_questions.py](../../../scripts/generate_questions.py)) and
  translated into Japanese
  ([translate_questions.py](../../../scripts/translate_questions.py)). That
  translation follows the proper-noun dictionary and is given the cited
  chapters' Japanese text, so the short answers follow its wording (Q12's gold
  answer is ニカシャ様 [Nikasha-sama], as in the Japanese text, not "Mother
  Nikasha"). But nothing checks that each detail of a gold answer is present
  in the Japanese text; if the Japanese translation leaves one out, a Japanese
  answer cannot give it.
- **They are written in Japanese.** The same model may answer more briefly in
  Japanese. On Q29, for example, `openai_gpt-6-luna` answers in English that
  Surma took poison prepared by Mangala (Rukmini) and that this, not the
  decree, caused her departure, but in Japanese only that Surma took the
  poison Mangala prepared.

[../gold-check/](../gold-check/README.md) checks the first: each gold
answer's details against the cited chapters in both languages. Only 5 of 214
details are missing from the Japanese text alone, all differences of wording,
and without their 4 questions the gap stays at −5.24 points. The
second is not tested directly.

## Caveats

- **space-bunny-alpha's answers are corrupt**: 17 of its 50 Japanese answers
  carry stray Latin or Chinese fragments, and Q46 runs to about 39,000
  characters, mostly repeated dots. The translation tidies some of this away
  and leaves Q33 and Q50 in (cleaned-up) Japanese, so its ja→en is not a
  faithful translation. Its gap comes from the corruption itself; without it,
  the means change by less than a point (en 92.20, ja 85.90, xling 85.50,
  ja→en 82.00).
- **Translator and judge are the same model**: the translation could lean
  toward wording `gpt-6-luna` grades favorably. ja→en came out lower, not
  higher, so this did not inflate it.
- **11 models**: chosen for a large gap under OpenAI and Jev, so the size of
  the gap here is larger than the average over all models; the comparison
  between ja, xling and ja→en does not depend on it.
