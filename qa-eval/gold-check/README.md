# Are the gold answers' details in the Japanese text?

The gold answers were written from the English text and translated into
Japanese, but the English and Japanese texts are separate machine translations
of the Bengali original, and nothing checked that each text carries every
detail a gold answer asks for. A detail missing from a text is one an answer
in that language cannot give, and one missing from both is an error in the
gold answer. This directory checks each gold answer's details against the
cited chapters in both languages. It reads only the questions and the texts,
not any model's answers, and is rerun after a gold answer is corrected
([GOLD-FIX.md](../GOLD-FIX.md)). How the claims missing from the Japanese text
relate to the Japanese gap: [results/ja2en/](../results/ja2en/README.md#the-japanese-text-carries-the-gold-answers-details).

## Setup

- **Claims** (`make facts`): each English gold answer (the original the
  Japanese ones were translated from) is split into short factual claims,
  230 for the 50 questions → `facts.jsonl`. Both texts are checked against
  this one list, so a claim's verdicts can be compared across the languages.
- **Check** (`make check`): for each question, the model is given the full
  text of its gold `chapters` in one language, as Ceiling gives them, and the
  claims, and returns a verbatim quote, a reason and a verdict per claim:
  *stated*, *missing* or *contradicted* → `check-{en,ja}.jsonl`. The text is
  `all/<lang>-gemini.jsonl`, the frozen text the Ceiling answers were given,
  not the corrected `.md`.
- **Model**: `gpt-6-astra` with reasoning effort `medium`, for both steps.
  Script: [check_gold.py](check_gold.py).
- **Review**: every claim whose verdict differed between the languages was
  read against both texts and the Bengali original. Where the two texts say
  the same thing, the verdict was set to the same value in both, by the
  checker's own strict reading; the one verdict changed this way (Q8.1 in
  English) carries `"revised": true` and a rewritten reason.
- **Summary** (`make claims`, [claims.py](claims.py)): the verdict matrix,
  the per-question counts and the claim lists. A claim is *ja-only missing*
  when the English text states it and the Japanese one does not.

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
| **stated** | 223 | 4 | 2 |
| **missing** | 0 | 1 | 0 |
| **contradicted** | 0 | 0 | 0 |

The two texts agree on 224 of the 230 claims. 6 claims, in 5 questions, are
stated in the English text only, and none in the Japanese text only. One
claim is not stated in either (see
[below](#gold-answers-that-the-text-does-not-support)).

### The ja-only missing claims are differences of wording

| Claim | Bengali | English text | Japanese text |
| :--- | :--- | :--- | :--- |
| Q2.1 an alap in Raga Vehag | *behag alap* | "an alap in the raga Vehag" | ベハーグの旋律 (the Behag melody) |
| Q20.2 pour whey over his head | *ghol* (buttermilk) | "pour whey over it" | 酸っぱい乳 (sour milk) |
| Q28.2–3 disguised as a middle-aged woman | *prouDha* (a woman past her youth) | "a middle-aged woman" | 老婦人 (an old woman) |
| Q43.3 a rope of bedsheets | *chador* (a sheet or wrap) | "large sheets" | 大きな布 (large pieces of cloth) |
| Q46.10 a curved blade | *bonti* (a curved blade fixed to a base) | "a curved blade" | ボーティ（肉切り包丁） (boti, a meat-cutting knife) |

Each is a word the two translations render differently, not a missing event.
In Q2 the raga, which is the answer, is in both texts; only the alap of the
question's premise is dropped. In Q20, Q28 and Q46 both renderings fit the
Bengali.

## Gold answers that the text does not support

One claim is stated in neither text. Q8.1 has Mangala give the dried root to
Matangini to feed to Matangini's husband, but both texts call the man only a
wretch who has turned to another woman, not her husband. The detail comes from
the question, which is frozen: the gold answer itself, "A dried root.", is
stated in both texts. This claim does not count as ja-only missing.

## Effect of the gold-answer fix on the scores

The fix of 19 gold answers (b144d29) and the re-grade (e0857d5) moved the
per-model Ceiling scores in `results/report*.md` very little. The table
compares each report before the fix (b144d29) with the one updated for it
(32ee5ca), over the runs present in both. The 11 qwen runs added later
(f85b9a5) were only graded after the fix and are left out. A score is the
weighted %, so one question moving between correct and partial changes it by
1 point.

| Judge | Lang | Runs | Mean (before → after) | Mean change | Mean \|change\| | Range | Unchanged | Spearman | en − ja (before → after) |
| :--- | :--- | ---: | :--- | ---: | ---: | :--- | ---: | ---: | :--- |
| qwen | en | 40 | 96.3 → 96.4 | +0.12 | 0.97 | −3 to +4 | 15 | 0.843 | 2.45 → 2.38 |
| qwen | ja | 40 | 93.8 → 94.0 | +0.20 | 0.85 | −2 to +4 | 15 | 0.939 | |
| Jev | en | 51 | 90.3 → 90.4 | +0.12 | 1.37 | −4 to +3 | 14 | 0.907 | 4.45 → 4.69 |
| Jev | ja | 51 | 85.9 → 85.7 | −0.12 | 1.02 | −2 to +3 | 16 | 0.965 | |
| Nimble | en | 51 | 92.9 → 93.6 | +0.69 | 1.20 | −4 to +4 | 15 | 0.884 | 1.37 → 2.10 |
| Nimble | ja | 51 | 91.5 → 91.5 | −0.04 | 0.86 | −3 to +3 | 21 | 0.892 | |
| OpenAI | en | 51 | 92.7 → 92.8 | +0.06 | 0.92 | −2 to +3 | 20 | 0.950 | 4.47 → 5.27 |
| OpenAI | ja | 51 | 88.3 → 87.5 | −0.75 | 1.41 | −4 to +3 | 11 | 0.959 | |
| Ternary | en | 51 | 92.0 → 91.8 | −0.20 | 1.18 | −4 to +3 | 12 | 0.924 | 5.37 → 5.94 |
| Ternary | ja | 51 | 86.6 → 85.9 | −0.76 | 1.43 | −4 to +3 | 9 | 0.954 | |

- **The level is unchanged**: no judge's mean moves by more than 0.8 points,
  and a run moves by about 1 point on average, as many runs gaining as
  losing.
- **The ranking mostly holds**: Spearman's ρ is 0.9 or above for Jev, OpenAI
  and Ternary. It is lower for qwen in English (0.84) and for Nimble
  (0.88–0.89), whose top runs are bunched at 93–100, where a 1–2 point move
  swaps places.
- **Japanese slightly stricter under OpenAI and Ternary**: their Japanese mean
  drops by about 0.75 points, widening the en − ja gap by 0.6–0.8 points. The
  Nimble gap widens by a similar amount from an English gain instead.
- **Hybrid8** (3 runs per judge, not in the table) moves by at most 3 points
  and is too few runs to read a direction from.

A fix of details alone is therefore not worth a re-grade; see
[LESSONS.md](../LESSONS.md#after-answering-fix-only-real-errors).

## Caveats

- **One run of one model**: each verdict is a single request. The checker is
  strict, marking as missing details the text implies but does not state, so
  the counts above are of literal support, not of what a reader could infer.
  It is also inconsistent: of the 7 claims it judged differently in the two
  languages, 1 differed although the two texts say the same thing, and was
  revised (see Setup). Claims it judged alike in both languages were not
  reviewed.
- **Claims from the English gold answer**: they follow its English wording
  (whey, bedsheets), so a Japanese rendering of the same thing can count as
  missing. This biases the ja-only count upward, not downward.
- **Claims include the question's premises** for the short single answers
  (e.g. Q8's paan), which also tests whether the premise is in the text.
