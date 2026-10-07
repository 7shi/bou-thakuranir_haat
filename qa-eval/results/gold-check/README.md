# Are the gold answers' details in the Japanese text?

[../ja2en/](../ja2en/README.md) found that the Japanese Ceiling answers score
below the English ones because they lack details of the gold answer, but left
open why. One candidate is the text itself: the English and Japanese texts are
separate machine translations of the Bengali original, the gold answers were
written from the English one, and nothing checked that the Japanese one carries
every detail they ask for. A detail missing there is one a Japanese answer
cannot give. This directory checks each gold answer's details against the
cited chapters in both languages.

## Setup

- **Claims** (`make facts`): each English gold answer (the original the
  Japanese ones were translated from) is split into short factual claims,
  214 for the 50 questions → `facts.jsonl`. Both texts are checked against
  this one list, so a claim's verdicts can be compared across the languages.
- **Check** (`make check`): for each question, the model is given the full
  text of its gold `chapters` in one language, as Ceiling gives them, and the
  claims, and returns a verbatim quote, a reason and a verdict per claim:
  *stated*, *missing* or *contradicted* → `check-{en,ja}.jsonl`. The text is
  `all/<lang>-gemini.jsonl`, the frozen text the Ceiling answers were given,
  not the corrected `.md`.
- **Model**: `gpt-6-astra` with reasoning effort `medium`, for both steps.
  Script: [check_gold.py](check_gold.py).
- **Comparison** (`make compare`, [compare.py](compare.py)): a claim is
  *ja-only missing* when the English text states it and the Japanese one does
  not. The Ternary ja − en gap over all 50 models ([../ternary/](../TERNARY.md))
  is measured on the questions with and without such a claim, with a two-sided
  sign test over the models.

| Step | Output | Requests | Wall time | Input | Output |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `make facts` | `facts.jsonl` | 50 | 4m 7.2s | 9,970 | 7,155 |
| `make check` (en) | `check-en.jsonl` | 50 | 9m 16s | 197,002 | 18,112 |
| `make check` (ja) | `check-ja.jsonl` | 50 | 8m 13s | 294,717 | 22,778 |

`make check` took 17m 33.4s for both languages. The Japanese text is about
half as many characters as the English but takes more input tokens.

## Results

| en \ ja | stated | missing | contradicted |
| :--- | ---: | ---: | ---: |
| **stated** | 172 | 8 | 3 |
| **missing** | 2 | 24 | 0 |
| **contradicted** | 1 | 0 | 4 |

The two texts agree on 200 of the 214 claims. 11 claims, in 8 questions, are
stated in the English text only; 3 claims (Q31, Q32, Q39) are stated in the
Japanese text only. 28 claims are not stated in either (see
[below](#gold-answers-that-the-text-does-not-support)).

### The ja-only missing claims are differences of wording

| Claim | English text | Japanese text |
| :--- | :--- | :--- |
| Q2.1 alap in Raga Vehag | alap named | the raga is named, the alap is not |
| Q8.1 the root is for Matangini's husband | stated | the man is not identified as her husband |
| Q20.2 pour whey over his head | "pour whey over it" | 酸っぱい乳 (sour milk) |
| Q22.1 tied up with Udayaditya's own cloth | "with his own cloth" | 彼の衣服で (with his, i.e. Sitaram's, clothing) |
| Q28.2–3 disguised as a middle-aged woman | "disguised as a woman" | 老婦人 (an old woman) |
| Q38.4, 6 Ramchandra *affectionately* sent for Vibha | stated | a request for her return, affection not stated |
| Q40.6 the sitar is there in Raigarh | stated | the sitar exists, the place is not stated |
| Q43.1 saved from *assassination* | stated | rescue from mortal danger, no plot named |
| Q43.2 a rope of *bedsheets* | "large sheets" | 大きな布 (large pieces of cloth) |

Each is a word the Japanese translation renders differently or leaves out,
not a missing event. Q22 is the one where the meaning differs: "his own
cloth" is ambiguous in English, and the Japanese text reads it as Sitaram's.

### Removing them leaves the gap

| Questions | n | en | ja | ja − en | ja < en | ja > en | Sign test |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 50 | 91.90 | 86.56 | −5.34 | 44 | 2 | 3.1 × 10⁻¹¹ |
| Without ja-only missing | 42 | 91.79 | 86.67 | −5.12 | 40 | 5 | 7.9 × 10⁻⁸ |
| With ja-only missing | 8 | 92.50 | 86.00 | −6.50 | 33 | 6 | 1.4 × 10⁻⁵ |
| All (single) | 25 | 98.60 | 97.44 | −1.16 | 18 | 12 | 0.36 |
| Without ja-only missing (single) | 21 | 98.71 | 97.57 | −1.14 | 16 | 8 | 0.15 |
| All (cross) | 25 | 85.20 | 75.68 | −9.52 | 43 | 3 | 4.6 × 10⁻¹⁰ |
| Without ja-only missing (cross) | 21 | 84.86 | 75.76 | −9.10 | 40 | 6 | 3.1 × 10⁻⁷ |

The questions with a ja-only missing claim lose a little more in Japanese
(−6.50), but without them the gap stays at −5.12, and at −9.10 on the cross
questions, significant in both. The questions with the largest gaps, Q29
(−30), Q50 (−22), Q37 (−19), Q27 (−17) and Q36 (−15), have no ja-only
missing claim. Details absent from the Japanese text therefore account for
little of the gap. The other candidate named in ../ja2en/, that the same model
answers with fewer details in Japanese, is not tested here.

## Gold answers that the text does not support

Of the 28 claims stated in neither text, several are errors of the gold
answer itself, which neither text supports:

| Question | Gold answer says | Both texts say |
| :--- | :--- | :--- |
| Q32 | Udayaditya overpowers Sitaram | Sitaram asks to be disarmed and bound |
| Q34 | Rukmini fails to board the boat and falls into the canal | she lunges at Udayaditya, is stopped by Sitaram, and jumps into the water |
| Q46 | Rukmini attacks Sitaram with a curved blade | Sitaram slips out before she returns with it; she strikes the floor |
| Q47 | Sitaram throws a melted sword into the flames | he throws in the sword; its melted remains are found afterwards |
| Q50 | Surma's suicide | Surma's death, cause not given in the cited chapters |

Others ask for a detail outside the question's `chapters`: Basanta Ray's
death as an execution (Q37), Vibha's journey to Chandradwip (Q38), the escape
boat (Q42), and Udayaditya's imprisonment (Q49, whose question presupposes
it). The rest are motives or attributes the text implies but does not state,
such as Bhagavat being a guard (Q31, Q49) or the "immense strength" of Q39.
These claims do not count as ja-only missing, so they do not affect the
comparison above. The gold answers can be corrected without regenerating any
answer; the questions and `chapters` cannot, since some answering models are
no longer available.

## Caveats

- **One run of one model**: each verdict is a single request. The checker is
  strict, marking as missing details the text implies but does not state, so
  the counts above are of literal support, not of what a reader could infer.
- **Claims from the English gold answer**: they follow its English wording
  (whey, bedsheets), so a Japanese rendering of the same thing can count as
  missing. This biases the ja-only count upward, not downward.
- **Claims include the question's premises** for the short single answers
  (e.g. Q8's paan), which also tests whether the premise is in the text.
