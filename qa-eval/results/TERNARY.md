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
| `opencode_muse-spark-1.2-contributor-free` | 100 | 96 | 96 | 100 | **98** | 100 | 96 | 97 | 100 | **99** |
| `openrouter_stealth_ox-alpha` | 100 | 98 | 99 | 100 | **100** | 100 | 94 | 93 | 98 | **97** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 98 | 99 | **100** | 100 | 97 | 96 | 97 | **96** |
| `opencode_union-alpha` | 100 | 98 | 98 | 98 | **98** | 100 | 94 | 95 | 96 | **95** |
| `copilot_kimi-k2.7-code` | 100 | 95 | 96 | 98 | **98** | 99 | 92 | 94 | 93 | **95** |
| `openrouter_minimax_minimax-m3_free` | 100 | 98 | 96 | 97 | **97** | 99 | 91 | 96 | 96 | **95** |
| `opencode_ling-3.1-flash-free` | 100 | 95 | 96 | 97 | **97** | 99 | 90 | 93 | 93 | **95** |
| `openai_gpt-6-astra` | 100 | 93 | 98 | 99 | **96** | 100 | 89 | 97 | 98 | **95** |
| `openai_gpt-6.1-sol` | 100 | 95 | 95 | 99 | **97** | 100 | 87 | 95 | 95 | **93** |
| `ollama_qwen3.8` | 100 | 98 | 97 | 97 | **96** | 97 | 92 | 91 | 94 | **94** |
| `copilot_kimi-k3` | 100 | 96 | 95 | 98 | **93** | 100 | 94 | 97 | 97 | **96** |
| `ollama_muse-glimmer` | 99 | 95 | 96 | 96 | **96** | 99 | 93 | 95 | 94 | **93** |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | 97 | 98 | **97** | 95 | 87 | 91 | 91 | **90** |
| `google_gemma-4-31b-it` | 99 | 93 | 96 | 97 | **95** | 99 | 90 | 95 | 91 | **92** |
| `copilot_grok-4.5` | 100 | 95 | 96 | 95 | **95** | 100 | 94 | 96 | 91 | **92** |
| `openai_gpt-5.6-sol` | 100 | 91 | 97 | 94 | **95** | 100 | 90 | 97 | 96 | **91** |
| `openai_gpt-6-sol` | 100 | 94 | 99 | 96 | **96** | 100 | 90 | 99 | 92 | **90** |
| `google_gemini-3.8-flash` | 97 | 89 | 94 | 95 | **93** | 97 | 90 | 95 | 91 | **93** |
| `openrouter_apodex_apodex-1.1-mini_free` | 98 | 94 | 92 | 97 | **96** | 97 | 89 | 94 | 88 | **90** |
| `opencode_mimo-v2.5-free` | 100 | 94 | 97 | 96 | **98** | 95 | 88 | 92 | 85 | **88** |
| `openai_gpt-5.6-terra` | 100 | 94 | 94 | 94 | **94** | 100 | 89 | 96 | 92 | **91** |
| `copilot_claude-sonnet-5` | 100 | 97 | 98 | 98 | **94** | 95 | 84 | 88 | 91 | **90** |
| `copilot_gpt-5.6-luna` | 99 | 87 | 94 | 96 | **95** | 98 | 88 | 96 | 92 | **89** |
| `copilot_grok-4.6` | 100 | 93 | 96 | 98 | **95** | 99 | 90 | 96 | 90 | **89** |
| `opencode_fledge-alpha-free` | 99 | 94 | 97 | 94 | **95** | 99 | 90 | 96 | 92 | **89** |
| `google_gemini-3-flash-preview` | 100 | 94 | 97 | 95 | **95** | 100 | 91 | 94 | 89 | **89** |
| `openai_gpt-5.6-luna` | 100 | 92 | 97 | 95 | **94** | 98 | 89 | 96 | 91 | **89** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 93 | 93 | 92 | **94** | 96 | 91 | 97 | 91 | **89** |
| `openai_gpt-6-luna` | 98 | 91 | 97 | 93 | **90** | 99 | 88 | 98 | 94 | **91** |
| `opencode_big-pickle` | 99 | 91 | 94 | 95 | **93** | 96 | 87 | 95 | 89 | **88** |
| `opencode_longcat-2.5-preview-free` | 100 | 94 | 95 | 95 | **95** | 95 | 86 | 92 | 88 | **86** |
| `google_gemini-3.7-flash` | 98 | 89 | 91 | 91 | **92** | 97 | 88 | 95 | 90 | **88** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | 94 | 92 | **95** | 98 | 86 | 93 | 88 | **84** |
| `google_gemini-2.5-flash` | 93 | 87 | 92 | 93 | **91** | 96 | 86 | 94 | 88 | **86** |
| `copilot_claude-haiku-4.5` | 97 | 88 | 90 | 93 | **90** | 98 | 86 | 94 | 83 | **85** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 92 | 91 | **86** | 96 | 85 | 90 | 82 | **89** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 90 | 92 | 93 | **90** | 96 | 81 | 93 | 86 | **84** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 88 | 91 | 90 | **85** | 94 | 85 | 94 | 88 | **88** |
| `ollama_qwen3.6` | 97 | 90 | 91 | 89 | **89** | 96 | 86 | 94 | 84 | **83** |
| `copilot_mai-code-1.1-flash` | 99 | 89 | 95 | 92 | **91** | 93 | 84 | 89 | 83 | **78** |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | 93 | 89 | **88** | 94 | 84 | 90 | 85 | **81** |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 86 | 95 | 86 | **87** | 95 | 81 | 95 | 85 | **82** |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | 94 | 92 | **90** | 92 | 80 | 88 | 79 | **78** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 83 | 88 | 86 | **86** | 87 | 78 | 83 | 76 | **76** |
| `google_gemini-3.5-flash-lite` | 85 | 81 | 83 | 84 | **82** | 86 | 77 | 86 | 77 | **77** |
| `ollama_gemma4_12b-it-qat` | 83 | 76 | 81 | 79 | **78** | 82 | 72 | 80 | 75 | **69** |
| `ollama_qwen3.5_9b` | 91 | 78 | 87 | 81 | **81** | 77 | 73 | 78 | 76 | **65** |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | 91 | 84 | **85** | 74 | 67 | 73 | 68 | **60** |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | 90 | 86 | **84** | 71 | 63 | 69 | 65 | **59** |
| `openrouter_poolside_laguna-xs-2.1_free` | 91 | 81 | 90 | 81 | **79** | 68 | 64 | 73 | 63 | **59** |
| `ollama_qwen3.5_4b` | 79 | 72 | 74 | 70 | **68** | 72 | 67 | 74 | 68 | **59** |

Sorted by the Ternary score summed over both languages (ties by the OpenAI
sum).

- **The same top as OpenAI, with less saturation**:
  Under Ternary 6 models reach 98 in English and 1 in Japanese (OpenAI: 11 and
  3), and two scores are 100 (`openrouter_stealth_ox-alpha` and
  `opencode_muse-spark-1.3-contributor-free`, en; OpenAI gives 100 to
  `opencode_muse-spark-1.2-contributor-free` in both languages and to
  `openrouter_stealth_ox-alpha` in English). The top three are
  `opencode_muse-spark-1.2-contributor-free` (98 / 99),
  `openrouter_stealth_ox-alpha` (100 / 97) and
  `opencode_muse-spark-1.3-contributor-free` (100 / 96).
- **The largest Japanese penalty (Ja − En gap)**:
  Over all 51 models, the mean Japanese score is **−5.94** points below
  English under Ternary, beyond OpenAI (−5.27), Jev (−4.69), Qwen (−2.57) and
  Nimble (−2.10). The gap widens at the bottom of
  the table: `openrouter_cohere_north-mini-code_free` (85 → 60),
  `openrouter_poolside_laguna-s-2.1_free` (84 → 59),
  `openrouter_poolside_laguna-xs-2.1_free` (79 → 59) and `ollama_qwen3.5_9b`
  (81 → 65) fall by 16–25 points, against 5–21 under OpenAI. Grading the
  Japanese answers against the English gold answers recovers only a small part
  of the gap, and translating them into English recovers nothing more: most of
  it lies in the Japanese answers, which lack details of the gold answer, not
  in the Japanese gold answers or in grading Japanese
  ([ja2en/](ja2en/README.md)).
- **Correlation**:
  Pearson correlation of the Ceiling scores summed over both languages is
  **$r = 0.985$** with OpenAI, **$r = 0.980$** with Jev, **$r = 0.957$** with
  Qwen and **$r = 0.941$** with Nimble (51 models each). Rank agreement is
  highest with OpenAI (Spearman 0.90 en / 0.94 ja), close with Jev
  (0.88 / 0.90) and Qwen (0.86 / 0.85), and lowest with Nimble (0.80 / 0.66).

### Verdict transitions (5,200 Questions)

Across all 104 judged runs in this directory (2,600 questions per language,
Ceiling and Hybrid8 combined). Verdict totals of the five judges:

| Judge | Correct | Partial | Incorrect |
| :--- | ---: | ---: | ---: |
| Qwen | 4,838 (93.0%) | 273 (5.2%) | 89 (1.7%) |
| Nimble | 4,485 (86.2%) | 655 (12.6%) | 60 (1.2%) |
| OpenAI | 4,241 (81.6%) | 906 (17.4%) | 53 (1.0%) |
| **Ternary** | **4,167 (80.1%)** | **914 (17.6%)** | **119 (2.3%)** |
| Jev | 4,046 (77.8%) | 1,077 (20.7%) | 77 (1.5%) |

Ternary calls about as many answers *correct* and *partial* as OpenAI does,
but gives more than twice as many *incorrect* verdicts (119 vs. 53), most of
them in Japanese (89 vs. 39).

#### Qwen vs. Ternary

| Qwen \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,202 | 264 | 2 |
| **partial** | 5 | 92 | 8 |
| **incorrect** | 0 | 7 | 20 |

*Agreement: 2,314 / 2,600 (89.0%)*

| Qwen \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,956 | 412 | 2 |
| **partial** | 4 | 133 | 31 |
| **incorrect** | 0 | 6 | 56 |

*Agreement: 2,145 / 2,600 (82.5%)*

As with the other judges, the shift is Qwen *correct* → Ternary *partial*
(264 in en, 412 in ja), larger in Japanese.

#### Jev vs. Ternary

| Jev \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,036 | 88 | 1 |
| **partial** | 171 | 275 | 10 |
| **incorrect** | 0 | 0 | 19 |

*Agreement: 2,330 / 2,600 (89.6%)*

| Jev \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,798 | 122 | 1 |
| **partial** | 162 | 428 | 31 |
| **incorrect** | 0 | 1 | 57 |

*Agreement: 2,283 / 2,600 (87.8%)*

At the *correct* / *partial* boundary Ternary is the more lenient, as OpenAI
is: Jev *partial* → Ternary *correct* (171 en, 162 ja) outnumbers the reverse
(88 en, 122 ja). At the *partial* / *incorrect* boundary it is the stricter
(31 Jev *partial* → Ternary *incorrect* in ja).

#### Nimble vs. Ternary

| Nimble \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,105 | 175 | 1 |
| **partial** | 102 | 185 | 17 |
| **incorrect** | 0 | 3 | 12 |

*Agreement: 2,302 / 2,600 (88.5%)*

| Nimble \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,887 | 317 | 0 |
| **partial** | 73 | 231 | 47 |
| **incorrect** | 0 | 3 | 42 |

*Agreement: 2,160 / 2,600 (83.1%)*

As with OpenAI, Nimble *correct* → Ternary *partial* dominates in Japanese
(317 vs. 73), and Nimble *partial* → Ternary *incorrect* adds 47 more.

#### OpenAI vs. Ternary

| OpenAI \ Ternary (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,146 | 97 | 0 |
| **partial** | 61 | 266 | 16 |
| **incorrect** | 0 | 0 | 14 |

*Agreement: 2,426 / 2,600 (93.3%)*

| OpenAI \ Ternary (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,873 | 125 | 0 |
| **partial** | 87 | 426 | 50 |
| **incorrect** | 0 | 0 | 39 |

*Agreement: 2,338 / 2,600 (89.9%)*

The same model through the two APIs agrees most of all pairs. At the
*correct* / *partial* boundary the disagreements run both ways in similar
numbers (97 vs. 61 en, 125 vs. 87 ja); the one-sided difference is OpenAI
*partial* → Ternary *incorrect* (16 en, 50 ja).

##### Where the extra *incorrect* verdicts go

The Japanese *incorrect* verdicts concentrate on the weakest models: the five
Japanese runs of `openrouter_poolside_laguna-xs-2.1_free`,
`openrouter_cohere_north-mini-code_free`, `ollama_qwen3.5_4b`,
`openrouter_poolside_laguna-s-2.1_free` and `ollama_qwen3.5_9b` hold 58 of
Ternary's 89 (10–13 each), against 20 under OpenAI. These are the models whose
Japanese scores fall furthest in the table above.

The answers involved are mostly confused rather than incomplete. On Q26, for
example, the gold answer contrasts two nights: Udayaditya first disarms and
ties up the guard Sitaram, at Sitaram's own request, to help Ramchandra
escape, and later Sitaram throws open the prison door during a fire and leads
Udayaditya out of his cell. The Japanese answer of
`ollama_qwen3.5_9b` swaps the two nights, putting the fire rescue first and
the tying-up second. OpenAI grades it *partial* (P = 0.88), and Ternary
*incorrect*. Answers like these name the right people and events in the wrong
relations; the Decisions API credits the overlap, while the plain reply
rejects the answer as a whole.

Across all four pairs, *correct* and *incorrect* rarely swap: 2 Qwen
*correct* → Ternary *incorrect* in each language, 1 Jev *correct* → Ternary
*incorrect* in each language and 1 Nimble *correct* → Ternary *incorrect* in
English, and none against OpenAI.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models, under Ternary:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 95% | 86% | −9% | 92% | 86% | −6% |
| `ollama_qwen3.8` | 96% | 94% | −2% | 94% | 89% | −5% |
| `openrouter_stealth_ox-alpha` | 100% | 96% | −4% | 97% | 95% | −2% |

The 9-point English drop of `google_gemma-4-31b-it` matches Jev's (93 → 84);
OpenAI shows 10, Qwen 7 and Nimble 5. The 5-point Japanese drop of
`ollama_qwen3.8` matches Jev's (92 → 87) and is larger than under the other
judges (OpenAI 3, Qwen 1, Nimble a 2-point gain).
