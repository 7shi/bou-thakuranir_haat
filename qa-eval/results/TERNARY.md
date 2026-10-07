# Plain-LLM (Ternary) grading of the per-model runs

The per-model runs in this directory were graded by `gpt-6-luna` through the
**ordinary OpenAI API**, replying with the verdict word only, and compared
with the existing `ollama:qwen3.6`, TypeSafe Jev, Bespoke Labs Nimble and
OpenAI Decisions verdicts. The scores in [report-ternary.md](report-ternary.md)
and [MODELS-ternary.svg](MODELS-ternary.svg) are the Ternary verdicts. This
document records the grading run and how the verdicts compare across all 51
models. The same comparison for `results-<lang>/`:
[../TERNARY.md](../TERNARY.md).

## Grading run

Every answer file here was graded by one `make judge-ternary` run (see
[Makefile](Makefile)), writing `ternary/*.tsv`.

- **Judge**: [judge-ternary.py](../judge-ternary.py), `openai:gpt-6-luna` via
  llm7shi (Responses API) with reasoning off, scheme `ternary@70c12cb1`
  (recorded for all 104 files in `ternary/MODELS.tsv`). The rubric and input
  are those of the Decisions judge; the reply is one word, matched against the
  three verdicts.
- **Scope**: 104 answer files (52 per language; 50 ceiling + 2 hybrid8) × 50
  questions = 5,200 requests, one `judge-ternary.py` call per language
- **Wall time**: 101m 32.0s (about 58.6 s per file of 50 questions, 1.17 s per
  request)
- **Cost**: $0.00 (within the free tier)

Token usage, from llm7shi's `usage.jsonl` (one entry per language, recorded as
`gpt-6-luna`):

| Language | Files | Input | Output | Reasoning | Input / file | Input / request |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| English | 52 | 1,001,375 | 13,000 | 0 | 19,257 | 385 |
| Japanese | 52 | 1,428,284 | 13,000 | 0 | 27,467 | 549 |
| Total | 104 | 2,429,659 | 26,000 | 0 | 23,362 | 467 |

Every request used 5 output tokens and no reasoning tokens. Japanese needs
about 1.43× the tokens of English for the same material.

### Per-file comparison

The grading runs covered different numbers of files (82 for Jev and Nimble,
104 for OpenAI and here), so they are compared per file (one model × one
language, 50 questions):

| Judge | Files | Time / file | Input / file (en / ja) | Output / file | Cost / file |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Jev ([JEV.md](JEV.md)) | 82 | 11.1 s | 34,415 / 46,032 | 1,950 | $0.0017 |
| Nimble ([NIMBLE.md](NIMBLE.md)) | 82 | 34.0 s | — | — | — (local) |
| OpenAI ([OPENAI.md](OPENAI.md)) | 104 | 12.3 s | 22,957 / 31,167 | 0 | $0.0027 |
| **Ternary** | **104** | **58.6 s** | **19,257 / 27,467** | **250** | **$0 (free tier)** |

- **Time**: Ternary is the slowest of the four, about 1.7× Nimble and nearly
  5× OpenAI, although it uses the same model as OpenAI.
- **Tokens**: For the same rubric and input, the same model counts about
  0.86× OpenAI's input tokens (0.84× en, 0.88× ja). The output is 5 tokens
  per request, the verdict word.
- **Ratio**: OpenAI : Ternary is about 1 : 4.8 in time per file, and
  Jev : Ternary about 1 : 5.3. The `results-<lang>/` re-grading
  ([../TERNARY.md](../TERNARY.md)) gives 1 : 5.0 and 1 : 6.3 in total wall
  time; the ratios vary with API response times.

`make report-ternary` aggregates the Ternary verdicts into
[report-ternary.md](report-ternary.md) and
[MODELS-ternary.svg](MODELS-ternary.svg).

## Comparison with Qwen, Jev, Nimble and OpenAI

Each question counts as its verdict (for the probability judges, the most
probable one, the stricter one on a tie), and scores are
`(correct + 0.5 · partial) / 50` in percent. OPENAI.md's probability
expectation **E** is left out, since it equals the score when the
probabilities are 1 and 0.

### Ceiling (51 Models)

| Model | en Qwen | en Jev | en Nimble | en OpenAI | en Ternary | ja Qwen | ja Jev | ja Nimble | ja OpenAI | ja Ternary |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `openrouter_stealth_ox-alpha` | 98 | 95 | 96 | 100 | **100** | 100 | 96 | 96 | 99 | **98** |
| `opencode_muse-spark-1.2-contributor-free` | 98 | 96 | 95 | 99 | **99** | 100 | 96 | 96 | 99 | **99** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 98 | 99 | **99** | 100 | 96 | 93 | 97 | **98** |
| `copilot_kimi-k3` | — | 94 | 95 | 98 | **95** | — | 95 | 98 | 98 | **98** |
| `openai_gpt-6-astra` | — | 92 | 96 | 99 | **96** | — | 89 | 97 | 97 | **96** |
| `opencode_union-alpha` | 100 | 95 | 95 | 98 | **99** | 100 | 93 | 96 | 97 | **93** |
| `ollama_qwen3.8` | 100 | 96 | 97 | 97 | **97** | 99 | 91 | 92 | 96 | **95** |
| `openai_gpt-6.1-sol` | — | 95 | 95 | 97 | **96** | — | 84 | 97 | 96 | **96** |
| `opencode_ling-3.1-flash-free` | — | 95 | 94 | 95 | **97** | — | 89 | 93 | 96 | **94** |
| `copilot_kimi-k2.7-code` | 99 | 94 | 94 | 98 | **96** | 99 | 91 | 96 | 96 | **94** |
| `openrouter_minimax_minimax-m3_free` | 98 | 95 | 94 | 96 | **95** | 99 | 93 | 98 | 96 | **95** |
| `openai_gpt-6-sol` | — | 96 | 98 | 96 | **97** | — | 90 | 97 | 91 | **93** |
| `openai_gpt-5.6-sol` | 100 | 93 | 97 | 96 | **95** | 100 | 92 | 96 | 96 | **94** |
| `ollama_muse-glimmer` | 99 | 94 | 92 | 95 | **95** | 97 | 93 | 95 | 93 | **94** |
| `copilot_grok-4.6` | — | 93 | 95 | 97 | **96** | — | 90 | 95 | 94 | **91** |
| `google_gemma-4-31b-it` | 99 | 97 | 95 | 96 | **97** | 98 | 92 | 96 | 92 | **90** |
| `google_gemini-3.8-flash` | 98 | 91 | 91 | 95 | **95** | 97 | 88 | 96 | 91 | **92** |
| `opencode_mimo-v2.5-free` | 100 | 93 | 97 | 97 | **97** | 96 | 88 | 93 | 89 | **90** |
| `openai_gpt-5.6-luna` | 100 | 94 | 98 | 95 | **96** | 97 | 90 | 97 | 89 | **91** |
| `copilot_gpt-5.6-luna` | 99 | 91 | 93 | 98 | **96** | 98 | 88 | 96 | 92 | **90** |
| `copilot_grok-4.5` | 100 | 94 | 95 | 93 | **93** | 99 | 93 | 97 | 94 | **92** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 92 | 92 | 92 | **94** | 97 | 93 | 97 | 91 | **91** |
| `copilot_claude-sonnet-5` | — | 97 | 97 | 97 | **93** | — | 86 | 90 | 93 | **91** |
| `google_gemini-3-flash-preview` | 100 | 94 | 95 | 95 | **95** | 98 | 91 | 94 | 92 | **89** |
| `opencode_fledge-alpha-free` | — | 94 | 96 | 94 | **96** | — | 91 | 93 | 91 | **88** |
| `openrouter_apodex_apodex-1.1-mini_free` | — | 94 | 92 | 95 | **95** | — | 91 | 91 | 88 | **89** |
| `openai_gpt-6-luna` | 100 | 95 | 96 | 95 | **92** | 100 | 89 | 97 | 95 | **91** |
| `openai_gpt-5.6-terra` | 96 | 92 | 95 | 95 | **92** | 99 | 91 | 96 | 94 | **91** |
| `opencode_mimo-v2.6-flash-free` | 100 | 96 | 98 | 99 | **96** | 95 | 87 | 91 | 90 | **87** |
| `google_gemini-3.7-flash` | 97 | 87 | 88 | 92 | **92** | 98 | 85 | 94 | 91 | **91** |
| `opencode_big-pickle` | 97 | 88 | 94 | 95 | **92** | 97 | 88 | 95 | 92 | **89** |
| `opencode_longcat-2.5-preview-free` | — | 94 | 94 | 97 | **92** | — | 87 | 92 | 85 | **88** |
| `copilot_claude-haiku-4.5` | 98 | 90 | 92 | 94 | **93** | 98 | 85 | 94 | 84 | **87** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 96 | 92 | **90** | 97 | 86 | 90 | 84 | **88** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 99 | 90 | 94 | 92 | **92** | 96 | 86 | 91 | 88 | **85** |
| `google_gemini-2.5-flash` | 94 | 88 | 91 | 91 | **90** | 96 | 85 | 95 | 89 | **85** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 97 | 88 | 92 | 90 | **90** | 95 | 82 | 94 | 87 | **85** |
| `google_gemma-4-26b-a4b-it` | 95 | 85 | 91 | 90 | **90** | 94 | 81 | 90 | 85 | **85** |
| `ollama_qwen3.6` | 98 | 88 | 91 | 89 | **88** | 97 | 86 | 93 | 86 | **86** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 94 | 87 | 93 | 89 | **85** | 90 | 84 | 94 | 85 | **87** |
| `ollama_gemma4_26b-a4b-it-qat` | 95 | 87 | 94 | 88 | **87** | 92 | 82 | 94 | 88 | **84** |
| `openrouter_stealth_space-bunny-alpha` | 97 | 90 | 93 | 92 | **91** | 93 | 80 | 88 | 77 | **78** |
| `copilot_mai-code-1.1-flash` | 97 | 88 | 92 | 90 | **91** | 93 | 82 | 89 | 85 | **77** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 93 | 84 | 88 | 86 | **88** | 86 | 79 | 84 | 77 | **78** |
| `google_gemini-3.5-flash-lite` | 86 | 81 | 82 | 84 | **82** | 86 | 79 | 86 | 78 | **79** |
| `ollama_gemma4_12b-it-qat` | 84 | 78 | 82 | 80 | **79** | 83 | 72 | 80 | 75 | **72** |
| `openrouter_cohere_north-mini-code_free` | 92 | 85 | 91 | 86 | **87** | 73 | 67 | 73 | 70 | **61** |
| `ollama_qwen3.5_9b` | 90 | 78 | 87 | 80 | **82** | 78 | 73 | 78 | 75 | **65** |
| `openrouter_poolside_laguna-s-2.1_free` | 89 | 78 | 90 | 84 | **83** | 72 | 63 | 69 | 65 | **61** |
| `openrouter_poolside_laguna-xs-2.1_free` | — | 79 | 88 | 81 | **80** | — | 65 | 72 | 65 | **58** |
| `ollama_qwen3.5_4b` | 81 | 72 | 75 | 72 | **69** | 71 | 66 | 75 | 69 | **59** |

Sorted by the Ternary score summed over both languages (ties by the OpenAI
sum). The 11 models without Qwen verdicts show "—".

- **The same top as OpenAI, with less saturation**:
  Under Ternary 4 models reach 98 in English and 4 in Japanese (OpenAI: 9 and
  3), and one score is 100 (`openrouter_stealth_ox-alpha`, en, as under
  OpenAI). The top three are `openrouter_stealth_ox-alpha` (100 / 98),
  `opencode_muse-spark-1.2-contributor-free` (99 / 99) and
  `opencode_muse-spark-1.3-contributor-free` (99 / 98).
- **The largest Japanese penalty (Ja − En gap)**:
  Over the 40 models all five judges graded, the mean Japanese score is
  **−5.58** points below English under Ternary, beyond OpenAI (−4.40), Jev
  (−4.03), Qwen (−2.45) and Nimble (−1.12). Over all 51 models it is −5.37
  (OpenAI −4.47, Jev −4.45, Nimble −1.37). The gap widens at the bottom of
  the table: `openrouter_cohere_north-mini-code_free` (87 → 61),
  `openrouter_poolside_laguna-s-2.1_free` (83 → 61),
  `openrouter_poolside_laguna-xs-2.1_free` (80 → 58) and `ollama_qwen3.5_9b`
  (82 → 65) fall by 17–26 points, against 5–19 under OpenAI.
- **Correlation**:
  Pearson correlation of the Ceiling scores summed over both languages is
  **$r = 0.980$** with OpenAI (51 models), **$r = 0.967$** with Jev (51
  models), **$r = 0.955$** with Qwen (40 models) and **$r = 0.944$** with
  Nimble (51 models). Rank agreement is also highest with OpenAI (Spearman
  0.89 en / 0.94 ja), followed by Qwen (0.83 / 0.91) and Jev (0.86 / 0.85),
  and lowest with Nimble (0.73 / 0.77).

### Verdict transitions (5,200 Questions)

Across all 104 judged runs in this directory (2,600 questions per language,
Ceiling and Hybrid8 combined). Qwen covers only the 82 runs it graded (2,050
questions per language). Verdict totals of the four judges that graded all
104 runs:

| Judge | Correct | Partial | Incorrect |
| :--- | ---: | ---: | ---: |
| Nimble | 4,453 (85.6%) | 687 (13.2%) | 60 (1.2%) |
| OpenAI | 4,274 (82.2%) | 876 (16.8%) | 50 (1.0%) |
| **Ternary** | **4,212 (81.0%)** | **871 (16.8%)** | **117 (2.3%)** |
| Jev | 4,044 (77.8%) | 1,082 (20.8%) | 74 (1.4%) |

Ternary calls about as many answers *correct* and *partial* as OpenAI does,
but gives more than twice as many *incorrect* verdicts (117 vs. 50), most of
them in Japanese (90 vs. 36).

#### Qwen vs. Ternary

| Qwen \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,723 | 203 | 0 |
| **partial** | 4 | 86 | 6 |
| **incorrect** | 2 | 6 | 20 |

*Agreement: 1,829 / 2,050 (89.2%)*

| Qwen \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,546 | 300 | 4 |
| **partial** | 7 | 113 | 28 |
| **incorrect** | 0 | 8 | 44 |

*Agreement: 1,703 / 2,050 (83.1%)*

As with the other judges, the shift is Qwen *correct* → Ternary *partial*
(203 in en, 300 in ja), larger in Japanese.

#### Jev vs. Ternary

| Jev \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,031 | 88 | 0 |
| **partial** | 182 | 271 | 7 |
| **incorrect** | 0 | 1 | 20 |

*Agreement: 2,322 / 2,600 (89.3%)*

| Jev \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,802 | 122 | 1 |
| **partial** | 197 | 389 | 36 |
| **incorrect** | 0 | 0 | 53 |

*Agreement: 2,244 / 2,600 (86.3%)*

At the *correct* / *partial* boundary Ternary is the more lenient, as OpenAI
is: Jev *partial* → Ternary *correct* (182 en, 197 ja) outnumbers the reverse
(88 en, 122 ja). At the *partial* / *incorrect* boundary it is the stricter
(36 Jev *partial* → Ternary *incorrect* in ja).

#### Nimble vs. Ternary

| Nimble \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,095 | 152 | 0 |
| **partial** | 118 | 205 | 15 |
| **incorrect** | 0 | 3 | 12 |

*Agreement: 2,312 / 2,600 (88.9%)*

| Nimble \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,917 | 289 | 0 |
| **partial** | 82 | 219 | 48 |
| **incorrect** | 0 | 3 | 42 |

*Agreement: 2,178 / 2,600 (83.8%)*

As with OpenAI, Nimble *correct* → Ternary *partial* dominates in Japanese
(289 vs. 82), and Nimble *partial* → Ternary *incorrect* adds 48 more.

#### OpenAI vs. Ternary

| OpenAI \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,145 | 95 | 0 |
| **partial** | 68 | 265 | 13 |
| **incorrect** | 0 | 0 | 14 |

*Agreement: 2,424 / 2,600 (93.2%)*

| OpenAI \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,909 | 125 | 0 |
| **partial** | 90 | 385 | 55 |
| **incorrect** | 0 | 1 | 35 |

*Agreement: 2,329 / 2,600 (89.6%)*

The same model through the two APIs agrees most of all pairs. At the
*correct* / *partial* boundary the disagreements run both ways in similar
numbers (95 vs. 68 en, 125 vs. 90 ja); the one-sided difference is OpenAI
*partial* → Ternary *incorrect* (13 en, 55 ja).

##### Where the extra *incorrect* verdicts go

The Japanese *incorrect* verdicts concentrate on the weakest models: the five
Japanese runs of `openrouter_poolside_laguna-xs-2.1_free`,
`openrouter_cohere_north-mini-code_free`, `ollama_qwen3.5_4b`,
`openrouter_poolside_laguna-s-2.1_free` and `ollama_qwen3.5_9b` hold 56 of
Ternary's 90 (10–12 each), against 16 under OpenAI. These are the models whose
Japanese scores fall furthest in the table above.

The answers involved are mostly confused rather than incomplete. On Q26, for
example, the gold answer contrasts two nights: Udayaditya first overpowers and
ties up the guard Sitaram to help Ramachandra escape, and later Sitaram sets a
fire to take Udayaditya out of his cell. The Japanese answer of
`ollama_qwen3.5_9b` swaps the two nights, putting the fire rescue first and
the tying-up second. OpenAI grades it *partial* (P = 1.00), and Ternary
*incorrect*. Answers like these name the right people and events in the wrong
relations; the Decisions API credits the overlap, while the plain reply
rejects the answer as a whole.

Across all four pairs, *correct* and *incorrect* rarely swap: 4 Qwen
*correct* → Ternary *incorrect* in Japanese, 2 Qwen *incorrect* → Ternary
*correct* in English and 1 Jev *correct* → Ternary *incorrect* in Japanese,
and none against Nimble or OpenAI.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models, under Ternary:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 97% | 87% | −10% | 90% | 89% | −1% |
| `ollama_qwen3.8` | 97% | 94% | −3% | 95% | 87% | −8% |
| `openrouter_stealth_ox-alpha` | 100% | 97% | −3% | 98% | 94% | −4% |

The 10-point English drop of `google_gemma-4-31b-it` matches Jev's (97 → 87);
OpenAI shows 8, Qwen 6 and Nimble 3. The 8-point Japanese drop of
`ollama_qwen3.8` is larger than under the other judges (OpenAI 4, Qwen 4,
Jev 1, Nimble a 2-point gain).
