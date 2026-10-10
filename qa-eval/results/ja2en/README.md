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
| `copilot_claude-haiku-4.5` | 90 | 85 | 86 | 83 | 89 | −5 | −4 | −7 | −1 |
| `copilot_claude-sonnet-5` | 94 | 90 | 91 | 87 | 94 | −4 | −3 | −7 | +0 |
| `copilot_mai-code-1.1-flash` | 91 | 78 | 83 | 77 | 93 | −13 | −8 | −14 | +2 |
| `ollama_gemma4_12b-it-qat` | 78 | 69 | 72 | 72 | 80 | −9 | −6 | −6 | +2 |
| `openai_gpt-6-sol` | 96 | 90 | 96 | 93 | 95 | −6 | +0 | −3 | −1 |
| `openai_gpt-6.1-sol` | 97 | 93 | 94 | 93 | 97 | −4 | −3 | −4 | +0 |
| `opencode_longcat-2.5-preview-free` | 95 | 86 | 87 | 87 | 95 | −9 | −8 | −8 | +0 |
| `opencode_mimo-v2.5-free` | 98 | 88 | 84 | 85 | 97 | −10 | −14 | −13 | −1 |
| `opencode_mimo-v2.6-flash-free` | 97 | 90 | 90 | 86 | 96 | −7 | −7 | −11 | −1 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 86 | 76 | 77 | 70 | 82 | −10 | −9 | −16 | −4 |
| `openrouter_stealth_space-bunny-alpha` | 90 | 78 | 81 | 76 | 90 | −12 | −9 | −14 | +0 |
| **Mean** | 92.00 | 83.91 | 85.55 | 82.64 | 91.64 | −8.09 | −6.45 | −9.36 | −0.36 |

| | Correct | Partial | Incorrect | Mean excl. Q7, Q9, Q12, Q25 |
| :--- | ---: | ---: | ---: | ---: |
| en | 468 | 76 | 6 | 91.30 |
| retest | 466 | 76 | 8 | 90.91 |
| ja | 391 | 141 | 18 | 82.71 |
| xling | 408 | 125 | 17 | 85.38 |
| ja→en | 381 | 147 | 22 | 85.38 |

The last column leaves out the four questions where translation itself costs
points (see below).

### The judge is stable

| en \ retest | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 455 | 13 | 0 |
| **partial** | 11 | 63 | 2 |
| **incorrect** | 0 | 0 | 6 |

*Agreement: 524 / 550 (95.3%)*

Grading the same answers again changes 26 of 550 verdicts, and a model's
score by 1.1 points on average (at most 4). Differences of a few points per
model are within this noise; the mean differences below are not.

### The Japanese gold answers account for a small part

| ja \ xling | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 367 | 24 | 0 |
| **partial** | 41 | 100 | 0 |
| **incorrect** | 0 | 1 | 17 |

*Agreement: 484 / 550 (88.0%)*

Grading the Japanese answers against the English gold instead of the Japanese
one raises the mean from 83.91 to 85.55, 1.64 of the 8.09-point gap. Individual
verdicts move more than in retest (66 changes, a model's score by 2.4 points
on average), more often up than down (42 vs. 24), and 9 of the 11 models gain.
The rises gather on the long questions of the second half: Q40 (5 models),
Q38 (4), Q37, Q44 and Q50 (3 each). Their Japanese gold answers say the same
as the English ones, so on these questions the judge grades the same Japanese
answer more strictly against the Japanese wording. The largest drop is Q12
(9 models), whose Japanese gold answer follows the Japanese text (see below).

### Translation costs points on short quoted answers

| ja \ ja→en | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 331 | 54 | 6 |
| **partial** | 50 | 90 | 1 |
| **incorrect** | 0 | 3 | 15 |

*Agreement: 436 / 550 (79.3%)*

ja→en falls a further 2.91 points below xling. Of the 60 verdicts that drop
from xling to ja→en, 30 are on four short questions whose gold answer is a
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

### Most of the gap lies in the answers

Without Q7, Q9, Q12 and Q25, ja scores 82.71, xling and ja→en both 85.38,
against 91.30 for en. Changing the gold answer to English (ja → xling) gains
2.67 points, and changing the answer itself to English (xling → ja→en) leaves
the score where it was, while the English answers of the same models score
about 6 points higher still. That remainder is neither in the Japanese gold
answers nor in how Japanese is graded: the Japanese answers lack details of
the gold answer that the English ones give.

Across all 50 per-model Ceiling runs the gap is significant under the judges
that hold to the gold answer's details, and not under Nimble:

| Judge | ja < en | ja > en | Tie | Mean ja − en | Sign test |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Ternary | 44 | 5 | 1 | −6.00 | p = 8 × 10⁻⁹ |
| OpenAI | 47 | 2 | 1 | −5.24 | p = 4 × 10⁻¹² |
| Jev | 46 | 1 | 3 | −4.74 | p = 7 × 10⁻¹³ |
| Nimble | 26 | 16 | 8 | −2.12 | p = 0.16 |

Without the weakest five models, p stays below 10⁻⁶ for Ternary, OpenAI and
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
answer's details against the cited chapters in both languages. Only 6 of 230
details are missing from the Japanese text alone, all differences of wording,
and without their 5 questions the gap stays at −5.89 points. The
second is not tested directly.

## Caveats

- **space-bunny-alpha's answers are corrupt**: 17 of its 50 Japanese answers
  carry stray Latin or Chinese fragments, and Q46 runs to about 39,000
  characters, mostly repeated dots. The translation tidies some of this away
  and leaves Q33 and Q50 in (cleaned-up) Japanese, so its ja→en is not a
  faithful translation. Its gap comes from the corruption itself; without it,
  the means change by less than a point (en 92.20, ja 84.50, xling 86.00,
  ja→en 83.30).
- **Translator and judge are the same model**: the translation could lean
  toward wording `gpt-6-luna` grades favorably. ja→en came out lower, not
  higher, so this did not inflate it.
- **11 models**: chosen for a large gap under OpenAI and Jev, so the size of
  the gap here is larger than the average over all models; the comparison
  between ja, xling and ja→en does not depend on it.
