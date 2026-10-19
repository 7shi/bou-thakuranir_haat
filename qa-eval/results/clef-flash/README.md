# Clef Flash grading of the per-model runs

The per-model runs in `results/` were graded with Cloudflare's
**[Clef Flash](https://ollama.com/library/clef-flash)** (hosted locally via
Ollama) and compared with the existing `ollama:qwen3.6`, TypeSafe Jev and
Bespoke Labs Nimble verdicts. The scores in
[report-clef-flash.md](report-clef-flash.md) and
[MODELS-clef-flash.svg](MODELS-clef-flash.svg) are the Clef Flash verdicts.
This document records the grading run and how the verdicts compare across all
63 models. The same comparison for `results-<lang>/`:
[models/CLEF-FLASH.md](../../models/CLEF-FLASH.md).

**Frozen.** Jev is the default judge, and Clef Flash is no longer run
([models/README.md](../../models/README.md)). The verdicts (`*.tsv`), the last
report and the chart are kept in this directory for comparison, and
`make judge-clef-flash` / `make report-clef-flash` have been removed from the
[Makefile](../Makefile).

## Grading run

Every answer file in `results/` was graded by one `make judge-clef-flash` run,
writing `clef-flash/*.tsv`.

- **Judge**: [judge-clef-flash.py](../../judge-clef-flash.py), model `clef-flash`
  via Ollama's `/v1/systemone`, scheme `choice@19579e23` (recorded for all 128
  files in `clef-flash/MODELS.tsv`); the implementation is
  [ollama_systemone.py](../../ollama_systemone.py), shared with Nimble
- **Scope**: 128 answer files (64 per language; 62 ceiling + 2 hybrid8) × 50
  questions = 6,400 requests, one `judge-clef-flash.py` call per language
- **Wall time**: 64m 5.4s (about 30.0 s per file of 50 questions, 0.601 s per
  request)
- **Cost**: $0.00 (local)

Token usage, as reported by Ollama:

| Language | Files | Input | Output | Input / file | Input / request |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 64 | 1,560,131 | 0 | 24,377 | 488 |
| Japanese | 64 | 1,772,975 | 0 | 27,703 | 554 |
| Total | 128 | 3,333,106 | 0 | 26,040 | 521 |

Per file, Clef Flash takes about 30.0 s against Nimble's 34.0 s (82 files, see
[nimble/README.md](../nimble/README.md)), so the two local judges run at about
the same speed.

`make report-clef-flash` aggregated the Clef Flash verdicts into
[report-clef-flash.md](report-clef-flash.md) and
[MODELS-clef-flash.svg](MODELS-clef-flash.svg).

## Comparison with Qwen, Jev and Nimble

Each question counts as its most probable verdict (the stricter one on a tie),
and scores are `(correct + 0.5 · partial) / 50` in percent. Jev is the current
`jev-1.14.0`.

### Ceiling (63 Models)

| Model | en Qwen | en Jev | en Nimble | en Clef | ja Qwen | ja Jev | ja Nimble | ja Clef |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `opencode_glm-5.3` | 100 | 98 | 98 | **100** | 100 | 96 | 97 | **100** |
| `opencode_muse-spark-1.2-contributor-free` | 100 | 98 | 96 | **100** | 100 | 97 | 97 | **100** |
| `opencode_union-alpha` | 100 | 97 | 98 | **100** | 100 | 94 | 95 | **100** |
| `openrouter_stealth_ox-alpha` | 100 | 98 | 99 | **100** | 100 | 96 | 93 | **100** |
| `copilot_kimi-k2.7-code` | 100 | 96 | 96 | **100** | 99 | 92 | 94 | **100** |
| `opencode_ling-3.1-flash-free` | 100 | 97 | 96 | **100** | 99 | 89 | 93 | **100** |
| `openai_gpt-6-luna` | 98 | 95 | 97 | **100** | 99 | 87 | 98 | **99** |
| `google_gemini-4-argon` | 100 | 96 | 98 | **99** | 99 | 91 | 95 | **100** |
| `copilot_kimi-k3` | 100 | 97 | 95 | **100** | 100 | 93 | 97 | **99** |
| `openrouter_minimax_minimax-m3_free` | 100 | 96 | 96 | **100** | 99 | 91 | 96 | **99** |
| `openai_gpt-6.1-sol` | 100 | 96 | 95 | **99** | 100 | 89 | 95 | **100** |
| `opencode_big-pickle` | 99 | 91 | 94 | **99** | 96 | 86 | 95 | **100** |
| `openai_gpt-6-sol` | 100 | 96 | 99 | **98** | 100 | 92 | 99 | **100** |
| `openai_gpt-6-astra` | 100 | 94 | 98 | **99** | 100 | 92 | 97 | **99** |
| `openai_gpt-5.6-sol` | 100 | 92 | 97 | **99** | 100 | 89 | 97 | **99** |
| `copilot_grok-4.5` | 100 | 94 | 96 | **99** | 100 | 93 | 96 | **99** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 94 | 93 | **99** | 96 | 91 | 97 | **99** |
| `ollama_qwen3.8` | 100 | 97 | 97 | **99** | 97 | 91 | 91 | **99** |
| `opencode_step-5-preview-free` | 100 | 95 | 96 | **100** | 97 | 86 | 92 | **98** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | 94 | **99** | 98 | 88 | 93 | **99** |
| `strata_Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S` | 99 | 96 | 97 | **97** | 98 | 95 | 97 | **100** |
| `openai_gpt-5.6-luna` | 100 | 93 | 97 | **99** | 98 | 90 | 96 | **98** |
| `opencode_fledge-alpha-free` | 99 | 94 | 97 | **99** | 99 | 93 | 96 | **98** |
| `openai_gpt-5.6-terra` | 100 | 93 | 94 | **99** | 100 | 89 | 96 | **98** |
| `openrouter_apodex_apodex-1.1-mini_free` | 98 | 92 | 92 | **99** | 97 | 88 | 94 | **98** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 99 | 98 | **99** | 100 | 97 | 96 | **97** |
| `google_gemini-3-flash-preview` | 100 | 95 | 97 | **98** | 100 | 93 | 94 | **98** |
| `copilot_gpt-5.6-luna` | 99 | 92 | 94 | **98** | 98 | 89 | 96 | **98** |
| `opencode_mimo-v2.5-free` | 100 | 95 | 97 | **97** | 95 | 87 | 92 | **99** |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | 97 | **99** | 95 | 89 | 91 | **97** |
| `openrouter_deepseek_deepseek-v4.1-flash` | 97 | 94 | 95 | **98** | 98 | 87 | 93 | **98** |
| `opencode_longcat-2.5-preview-free` | 100 | 94 | 95 | **98** | 95 | 87 | 92 | **98** |
| `copilot_claude-sonnet-5` | 100 | 95 | 98 | **99** | 95 | 86 | 88 | **97** |
| `copilot_claude-haiku-4.5` | 97 | 88 | 90 | **97** | 98 | 87 | 94 | **99** |
| `openrouter_reflection_beam-1.0-501b-a23b` | 99 | 96 | 99 | **97** | 97 | 89 | 95 | **98** |
| `copilot_grok-4.6` | 100 | 95 | 96 | **96** | 99 | 93 | 96 | **99** |
| `google_gemini-2.5-flash` | 93 | 87 | 92 | **96** | 96 | 83 | 94 | **99** |
| `google_gemma-4-31b-it` | 99 | 96 | 96 | **96** | 99 | 88 | 95 | **98** |
| `openrouter_deepseek_deepseek-v4.1-flash-1017` | 97 | 93 | 93 | **96** | 97 | 89 | 98 | **98** |
| `google_gemini-3.8-flash` | 97 | 91 | 94 | **97** | 97 | 92 | 95 | **97** |
| `google_gemini-3.7-flash` | 98 | 91 | 91 | **96** | 97 | 89 | 95 | **98** |
| `ollama_qwen3.6` | 97 | 89 | 91 | **97** | 96 | 85 | 94 | **97** |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | 94 | **97** | 92 | 80 | 88 | **97** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 89 | 92 | **97** | 96 | 82 | 93 | **96** |
| `llama.cpp_Underdog-Saluki-27B-1.0-IQ2-mix` | 97 | 90 | 95 | **95** | 97 | 83 | 96 | **97** |
| `ollama_muse-glimmer` | 99 | 93 | 96 | **98** | 99 | 92 | 95 | **94** |
| `copilot_mai-code-1.1-flash` | 99 | 89 | 95 | **97** | 93 | 81 | 89 | **95** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 85 | 88 | **95** | 87 | 77 | 83 | **97** |
| `llama.cpp_MAI-Code-1.1-Flash-Q2-XS` | 93 | 89 | 95 | **94** | 94 | 80 | 93 | **97** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 86 | 91 | **95** | 94 | 85 | 94 | **96** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 92 | **93** | 96 | 82 | 90 | **96** |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 85 | 95 | **93** | 95 | 83 | 95 | **95** |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | 93 | **93** | 94 | 85 | 90 | **94** |
| `ollama_qwen3.5_9b` | 91 | 78 | 87 | **97** | 77 | 72 | 78 | **89** |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | 91 | **95** | 74 | 65 | 73 | **87** |
| `sarashina_sarashina3-mini` | 87 | 76 | 85 | **96** | 78 | 70 | 81 | **85** |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | 90 | **97** | 71 | 64 | 69 | **83** |
| `google_gemini-3.5-flash-lite` | 85 | 80 | 83 | **90** | 86 | 76 | 86 | **88** |
| `openrouter_poolside_laguna-xs-2.1_free` | 91 | 79 | 90 | **95** | 68 | 64 | 73 | **82** |
| `ollama_gemma4_12b-it-qat` | 83 | 75 | 81 | **91** | 82 | 72 | 80 | **86** |
| `sarashina_sarashina3-nano` | 72 | 64 | 76 | **87** | 74 | 68 | 80 | **84** |
| `ollama_qwen3.5_4b` | 79 | 71 | 74 | **90** | 72 | 64 | 74 | **79** |
| `opencode_cat-jam-free` | 66 | 66 | 68 | **77** | 62 | 64 | 65 | **79** |

Sorted by the Clef Flash score summed over both languages (ties by Nimble).

- **Saturation returns**: 6 models score 100% in both languages under Clef
  Flash, against 13 under Qwen and none under Jev or Nimble. The top 35 models
  sit within 97–100% in both languages, so Clef Flash separates the frontier
  models less than Nimble does.
- **The bottom is lifted most**: the weaker the model, the larger the gain over
  Nimble, e.g. `ollama_qwen3.5_4b` 74 → 90 (en), `sarashina_sarashina3-nano`
  76 → 87 (en), `openrouter_poolside_laguna-s-2.1_free` 69 → 83 (ja), against
  −1 to +8 points for the top 30 models. The range of English scores shrinks
  from 68–99 (Nimble) to 77–100.
- **Language gap**: Japanese is **−0.89%** below English on average, the
  smallest of the four judges (Qwen −2.33%, Nimble −1.90%, Jev −4.81%).
- **Correlation**: over the 126 model × language Ceiling scores, Pearson's
  $r$ with Clef Flash is **0.932** for Qwen, **0.892** for Nimble and
  **0.859** for Jev. Clef Flash tracks Qwen, the other lenient judge, most
  closely.

### Verdict transitions (6,600 Questions)

Across the 128 judged runs here plus the canonical Gemma Ceiling and Hybrid8
runs (66 runs and 3,300 questions per language, Ceiling and Hybrid8 combined):

#### Nimble vs. Clef Flash

| Nimble \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,802 | 75 | 0 |
| **partial** | 303 | 89 | 2 |
| **incorrect** | 6 | 3 | 20 |

*Agreement: 2,911 / 3,300 (88.2%)*

| Nimble \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,740 | 55 | 0 |
| **partial** | 319 | 116 | 2 |
| **incorrect** | 5 | 31 | 32 |

*Agreement: 2,888 / 3,300 (87.5%)*

The main shift is Nimble *partial* → Clef *correct* (303 in en, 319 in ja),
four to six times the reverse. Although both are fine-tuned from Qwen 3.5 9B
and receive the same input, Clef Flash accepts most of the omissions that
Nimble marks *partial*.

#### Qwen vs. Clef Flash

| Qwen \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,998 | 89 | 0 |
| **partial** | 104 | 61 | 0 |
| **incorrect** | 9 | 17 | 22 |

*Agreement: 3,081 / 3,300 (93.4%)*

| Qwen \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,908 | 71 | 2 |
| **partial** | 142 | 86 | 0 |
| **incorrect** | 14 | 45 | 32 |

*Agreement: 3,026 / 3,300 (91.7%)*

Clef Flash agrees with Qwen more than with any other judge. Where they differ,
Clef Flash is the more lenient for Qwen's *partial* verdicts (104 / 142 moved up
to *correct*, none down), and it moves more than half of Qwen's *incorrect*
verdicts up (26 of 48 in en, 59 of 91 in ja).

#### Jev vs. Clef Flash

| Jev \ Clef (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,633 | 61 | 0 |
| **partial** | 472 | 96 | 0 |
| **incorrect** | 6 | 10 | 22 |

*Agreement: 2,751 / 3,300 (83.4%)*

| Jev \ Clef (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,395 | 25 | 1 |
| **partial** | 662 | 135 | 2 |
| **incorrect** | 7 | 42 | 31 |

*Agreement: 2,561 / 3,300 (77.6%)*

Jev *partial* → Clef *correct* (472 in en, 662 in ja) is the largest single
shift in the three comparisons.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 96% | 93% | −3% | 98% | 96% | −2% |
| `ollama_qwen3.8` | 99% | 99% | 0% | 99% | 95% | −4% |
| `openrouter_stealth_ox-alpha` | 100% | 99% | −1% | 100% | 97% | −3% |

As under the other judges, Hybrid8 stays within 4% of Ceiling for all three
models; under Clef Flash it never scores above Ceiling.
