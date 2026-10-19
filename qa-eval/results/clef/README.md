# Clef grading of the per-model runs

The per-model runs in `results/` were graded with Cloudflare's
**[Clef](https://ollama.com/library/clef)** (hosted locally via Ollama) and
compared with the existing `ollama:qwen3.6`, TypeSafe Jev, Bespoke Labs Nimble
and Cloudflare Clef Flash verdicts. The scores in
[report-clef.md](report-clef.md) and [MODELS-clef.svg](MODELS-clef.svg) are the
Clef verdicts. This document records the grading run and how the verdicts
compare across all 63 models. The same comparison for `results-<lang>/`:
[models/CLEF.md](../../models/CLEF.md).

**Frozen.** Jev is the default judge, and Clef is no longer run
([models/README.md](../../models/README.md)). The verdicts (`*.tsv`), the last
report and the chart are kept in this directory for comparison, and
`make judge-clef` / `make report-clef` have been removed from the
[Makefile](../Makefile).

## Grading run

Every answer file in `results/` was graded by one `make judge-clef` run,
writing `clef/*.tsv`.

- **Judge**: [judge-clef.py](../../judge-clef.py), model `clef` via Ollama's
  `/v1/systemone`, scheme `choice@19579e23` (recorded for all 128 files in
  `clef/MODELS.tsv`); the implementation is
  [ollama_systemone.py](../../ollama_systemone.py), shared with Nimble and Clef
  Flash
- **Scope**: 128 answer files (64 per language; 62 ceiling + 2 hybrid8) × 50
  questions = 6,400 requests, one `judge-clef.py` call per language
- **Wall time**: 197m 5.1s (about 92.4 s per file of 50 questions, 1.848 s per
  request)
- **Cost**: $0.00 (local)

Token usage, as reported by Ollama:

| Language | Files | Input | Output | Input / file | Input / request |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 64 | 1,560,131 | 0 | 24,377 | 488 |
| Japanese | 64 | 1,772,975 | 0 | 27,703 | 554 |
| Total | 128 | 3,333,106 | 0 | 26,040 | 521 |

The input is the same as Clef Flash's, token for token
([clef-flash/README.md](../clef-flash/README.md)), but Clef takes about 92.4 s
per file against Clef Flash's 30.0 s, about three times as long.

`make report-clef` aggregated the Clef verdicts into
[report-clef.md](report-clef.md) and [MODELS-clef.svg](MODELS-clef.svg).

## Comparison with Qwen, Jev, Nimble and Clef Flash

Each question counts as its most probable verdict (the stricter one on a tie),
and scores are `(correct + 0.5 · partial) / 50` in percent. Jev is the current
`jev-1.14.0`; "Flash" is Clef Flash.

### Ceiling (63 Models)

| Model | en Qwen | en Jev | en Nimble | en Flash | en Clef | ja Qwen | ja Jev | ja Nimble | ja Flash | ja Clef |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `opencode_glm-5.3` | 100 | 98 | 98 | 100 | **98** | 100 | 96 | 97 | 100 | **98** |
| `openrouter_stealth_ox-alpha` | 100 | 98 | 99 | 100 | **98** | 100 | 96 | 93 | 100 | **96** |
| `opencode_muse-spark-1.2-contributor-free` | 100 | 98 | 96 | 100 | **98** | 100 | 97 | 97 | 100 | **95** |
| `copilot_kimi-k3` | 100 | 97 | 95 | 100 | **96** | 100 | 93 | 97 | 99 | **94** |
| `opencode_union-alpha` | 100 | 97 | 98 | 100 | **96** | 100 | 94 | 95 | 100 | **93** |
| `openrouter_minimax_minimax-m3_free` | 100 | 96 | 96 | 100 | **97** | 99 | 91 | 96 | 99 | **92** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 99 | 98 | 99 | **96** | 100 | 97 | 96 | 97 | **91** |
| `openai_gpt-6-astra` | 100 | 94 | 98 | 99 | **95** | 100 | 92 | 97 | 99 | **91** |
| `google_gemini-4-argon` | 100 | 96 | 98 | 99 | **95** | 99 | 91 | 95 | 100 | **91** |
| `opencode_ling-3.1-flash-free` | 100 | 97 | 96 | 100 | **95** | 99 | 89 | 93 | 100 | **91** |
| `ollama_qwen3.8` | 100 | 97 | 97 | 99 | **95** | 97 | 91 | 91 | 99 | **91** |
| `copilot_claude-sonnet-5` | 100 | 95 | 98 | 99 | **94** | 95 | 86 | 88 | 97 | **92** |
| `openai_gpt-6.1-sol` | 100 | 96 | 95 | 99 | **95** | 100 | 89 | 95 | 100 | **90** |
| `copilot_kimi-k2.7-code` | 100 | 96 | 96 | 100 | **92** | 99 | 92 | 94 | 100 | **91** |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | 97 | 99 | **93** | 95 | 89 | 91 | 97 | **89** |
| `opencode_step-5-preview-free` | 100 | 95 | 96 | 100 | **93** | 97 | 86 | 92 | 98 | **89** |
| `strata_Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S` | 99 | 96 | 97 | 97 | **92** | 98 | 95 | 97 | 100 | **89** |
| `google_gemini-3-flash-preview` | 100 | 95 | 97 | 98 | **91** | 100 | 93 | 94 | 98 | **90** |
| `openai_gpt-5.6-luna` | 100 | 93 | 97 | 99 | **91** | 98 | 90 | 96 | 98 | **87** |
| `opencode_big-pickle` | 99 | 91 | 94 | 99 | **90** | 96 | 86 | 95 | 100 | **88** |
| `openrouter_apodex_apodex-1.1-mini_free` | 98 | 92 | 92 | 99 | **93** | 97 | 88 | 94 | 98 | **84** |
| `copilot_claude-haiku-4.5` | 97 | 88 | 90 | 97 | **90** | 98 | 87 | 94 | 99 | **87** |
| `ollama_muse-glimmer` | 99 | 93 | 96 | 98 | **90** | 99 | 92 | 95 | 94 | **86** |
| `opencode_mimo-v2.5-free` | 100 | 95 | 97 | 97 | **90** | 95 | 87 | 92 | 99 | **86** |
| `openai_gpt-5.6-sol` | 100 | 92 | 97 | 99 | **88** | 100 | 89 | 97 | 99 | **87** |
| `copilot_gpt-5.6-luna` | 99 | 92 | 94 | 98 | **88** | 98 | 89 | 96 | 98 | **87** |
| `google_gemini-3.8-flash` | 97 | 91 | 94 | 97 | **89** | 97 | 92 | 95 | 97 | **86** |
| `google_gemma-4-31b-it` | 99 | 96 | 96 | 96 | **90** | 99 | 88 | 95 | 98 | **84** |
| `opencode_longcat-2.5-preview-free` | 100 | 94 | 95 | 98 | **90** | 95 | 87 | 92 | 98 | **84** |
| `openai_gpt-6-luna` | 98 | 95 | 97 | 100 | **86** | 99 | 87 | 98 | 99 | **87** |
| `openrouter_deepseek_deepseek-v4.1-flash` | 97 | 94 | 95 | 98 | **89** | 98 | 87 | 93 | 98 | **84** |
| `openai_gpt-5.6-terra` | 100 | 93 | 94 | 99 | **88** | 100 | 89 | 96 | 98 | **84** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 94 | 93 | 99 | **89** | 96 | 91 | 97 | 99 | **83** |
| `google_gemini-2.5-flash` | 93 | 87 | 92 | 96 | **87** | 96 | 83 | 94 | 99 | **85** |
| `google_gemini-3.7-flash` | 98 | 91 | 91 | 96 | **86** | 97 | 89 | 95 | 98 | **86** |
| `openai_gpt-6-sol` | 100 | 96 | 99 | 98 | **89** | 100 | 92 | 99 | 100 | **82** |
| `opencode_fledge-alpha-free` | 99 | 94 | 97 | 99 | **87** | 99 | 93 | 96 | 98 | **84** |
| `copilot_grok-4.5` | 100 | 94 | 96 | 99 | **87** | 100 | 93 | 96 | 99 | **84** |
| `llama.cpp_Underdog-Saluki-27B-1.0-IQ2-mix` | 97 | 90 | 95 | 95 | **89** | 97 | 83 | 96 | 97 | **82** |
| `copilot_grok-4.6` | 100 | 95 | 96 | 96 | **87** | 99 | 93 | 96 | 99 | **83** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | 94 | 99 | **89** | 98 | 88 | 93 | 99 | **81** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 89 | 92 | 97 | **86** | 96 | 82 | 93 | 96 | **82** |
| `copilot_mai-code-1.1-flash` | 99 | 89 | 95 | 97 | **86** | 93 | 81 | 89 | 95 | **82** |
| `openrouter_reflection_beam-1.0-501b-a23b` | 99 | 96 | 99 | 97 | **88** | 97 | 89 | 95 | 98 | **79** |
| `openrouter_deepseek_deepseek-v4.1-flash-1017` | 97 | 93 | 93 | 96 | **84** | 97 | 89 | 98 | 98 | **83** |
| `llama.cpp_MAI-Code-1.1-Flash-Q2-XS` | 93 | 89 | 95 | 94 | **85** | 94 | 80 | 93 | 97 | **80** |
| `ollama_qwen3.6` | 97 | 89 | 91 | 97 | **86** | 96 | 85 | 94 | 97 | **79** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 92 | 93 | **82** | 96 | 82 | 90 | 96 | **83** |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | 94 | 97 | **87** | 92 | 80 | 88 | 97 | **74** |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | 93 | 93 | **81** | 94 | 85 | 90 | 94 | **79** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 86 | 91 | 95 | **80** | 94 | 85 | 94 | 96 | **79** |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 85 | 95 | 93 | **79** | 95 | 83 | 95 | 95 | **78** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 85 | 88 | 95 | **80** | 87 | 77 | 83 | 97 | **75** |
| `ollama_qwen3.5_9b` | 91 | 78 | 87 | 97 | **79** | 77 | 72 | 78 | 89 | **73** |
| `google_gemini-3.5-flash-lite` | 85 | 80 | 83 | 90 | **79** | 86 | 76 | 86 | 88 | **71** |
| `sarashina_sarashina3-mini` | 87 | 76 | 85 | 96 | **78** | 78 | 70 | 81 | 85 | **71** |
| `openrouter_poolside_laguna-xs-2.1_free` | 91 | 79 | 90 | 95 | **82** | 68 | 64 | 73 | 82 | **66** |
| `ollama_gemma4_12b-it-qat` | 83 | 75 | 81 | 91 | **74** | 82 | 72 | 80 | 86 | **74** |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | 91 | 95 | **78** | 74 | 65 | 73 | 87 | **67** |
| `ollama_qwen3.5_4b` | 79 | 71 | 74 | 90 | **74** | 72 | 64 | 74 | 79 | **70** |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | 90 | 97 | **79** | 71 | 64 | 69 | 83 | **62** |
| `opencode_cat-jam-free` | 66 | 66 | 68 | 77 | **69** | 62 | 64 | 65 | 79 | **67** |
| `sarashina_sarashina3-nano` | 72 | 64 | 76 | 87 | **68** | 74 | 68 | 80 | 84 | **67** |

Sorted by the Clef score summed over both languages (ties by Nimble).

- **The strictest judge**: no model reaches 100% in either language under
  Clef; the best is 98% (`opencode_glm-5.3` in both languages). The mean over
  the 126 model × language scores is **85.4%**, below Jev (87.8%), Nimble
  (92.2%), Qwen (94.9%) and Clef Flash (96.3%). Only 3 models score 95% or more
  in both languages, against 5 under Jev and 22 under Nimble.
- **Lower across the board**: against Nimble, Clef scores 6.8 points lower on
  average (−17 to +4), about evenly for the top 30 models (−5.2 en / −8.2 ja)
  and the bottom 15 (−7.4 / −7.9). The largest drops include
  `ollama_gemma4_26b-a4b-it-qat` (95 → 79 en, 95 → 78 ja) and
  `openai_gpt-6-sol` (99 → 89 en, 99 → 82 ja). Against Jev, the difference is
  −2.4 points on average (−10 to +6).
- **Language gap**: Japanese is **−4.29%** below English on average, close to
  Jev (−4.81%) and larger than Qwen (−2.33%), Nimble (−1.90%) and Clef Flash
  (−0.89%).
- **Correlation**: over the 126 model × language Ceiling scores, Pearson's
  $r$ with Clef is **0.915** for Jev, **0.850** for Qwen, **0.819** for Clef
  Flash and **0.806** for Nimble. Any two of the other four judges correlate
  at 0.86–0.96, so apart from Jev, Clef ranks the models the most differently.

### Verdict transitions (6,600 Questions)

Across the 128 judged runs here plus the canonical Gemma Ceiling and Hybrid8
runs (66 runs and 3,300 questions per language, Ceiling and Hybrid8 combined):

#### Clef Flash vs. Clef

| Clef Flash \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,487 | 619 | 5 |
| **partial** | 36 | 125 | 6 |
| **incorrect** | 0 | 2 | 20 |

*Agreement: 2,632 / 3,300 (79.8%)*

| Clef Flash \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,254 | 805 | 5 |
| **partial** | 3 | 182 | 17 |
| **incorrect** | 1 | 1 | 32 |

*Agreement: 2,468 / 3,300 (74.8%)*

The two siblings differ in one direction: Clef Flash *correct* → Clef
*partial* (619 in en, 805 in ja), against 36 and 3 the other way. Clef almost
never grades an answer higher than Clef Flash does.

#### Jev vs. Clef

| Jev \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,387 | 306 | 1 |
| **partial** | 136 | 429 | 3 |
| **incorrect** | 0 | 11 | 27 |

*Agreement: 2,843 / 3,300 (86.2%)*

| Jev \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,074 | 347 | 0 |
| **partial** | 184 | 610 | 5 |
| **incorrect** | 0 | 31 | 49 |

*Agreement: 2,733 / 3,300 (82.8%)*

Clef agrees with Jev more than with any other judge. The disagreements go both
ways (Jev *correct* → Clef *partial* 306 / 347, the reverse 136 / 184), with
Clef the stricter on balance.

#### Nimble vs. Clef

| Nimble \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,414 | 462 | 1 |
| **partial** | 109 | 278 | 7 |
| **incorrect** | 0 | 6 | 23 |

*Agreement: 2,715 / 3,300 (82.3%)*

| Nimble \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,138 | 657 | 0 |
| **partial** | 119 | 310 | 8 |
| **incorrect** | 1 | 21 | 46 |

*Agreement: 2,494 / 3,300 (75.6%)*

#### Qwen vs. Clef

| Qwen \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,515 | 572 | 0 |
| **partial** | 8 | 156 | 1 |
| **incorrect** | 0 | 18 | 30 |

*Agreement: 2,701 / 3,300 (81.8%)*

| Qwen \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,247 | 734 | 0 |
| **partial** | 11 | 215 | 2 |
| **incorrect** | 0 | 39 | 52 |

*Agreement: 2,514 / 3,300 (76.2%)*

Against Nimble and Qwen, the main shift is again *correct* → Clef *partial*
(462 / 657 from Nimble, 572 / 734 from Qwen). No Qwen *incorrect* becomes a
Clef *correct*.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 90% | 85% | −5% | 84% | 78% | −6% |
| `ollama_qwen3.8` | 95% | 96% | +1% | 91% | 88% | −3% |
| `openrouter_stealth_ox-alpha` | 98% | 96% | −2% | 96% | 93% | −3% |

As under the other judges, Hybrid8 stays close to Ceiling (within 6%) for all
three models; under Clef, `ollama_qwen3.8` scores 1% above Ceiling in English.
