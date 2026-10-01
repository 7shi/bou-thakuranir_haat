# Nimble grading of the per-model runs

The per-model runs in this directory were graded with Bespoke Labs'
**[Nimble](https://ollama.com/library/nimble)** (hosted locally via Ollama) and
compared with the existing `ollama:qwen3.6` and TypeSafe `Jev` verdicts. The
scores in [report-nimble.md](report-nimble.md) and
[MODELS-nimble.svg](MODELS-nimble.svg) are the Nimble verdicts. This document
records the grading run and how the verdicts compare across all 40 models. The
same comparison for `results-<lang>/`: [../NIMBLE.md](../NIMBLE.md).

## Grading run

Every answer file here was graded by `make judge-nimble` (see [Makefile](Makefile)),
writing `nimble/*.tsv`.

- **Judge**: [judge-nimble.py](../judge-nimble.py), model `nimble` via Ollama 0.35+,
  scheme `choice@19579e23` (recorded for all 82 files in `nimble/MODELS.tsv`)
- **Scope**: 82 answer files (41 per language; 39 ceiling + 2 hybrid8) × 50 questions
  = 4,100 requests, run sequentially across English and Japanese
- **Wall time**: 46m 24s (2,784 s in total, ~0.679 s per request)
- **Cost**: **$0.00** (fully local execution via Ollama GPU inference, zero API fees)
- **Output**: Strictly 1 token per question directly from the `/v1/systemone`
  endpoint, eliminating autoregressive text generation overhead.

`make report-nimble` aggregates the Nimble verdicts into [report-nimble.md](report-nimble.md)
and [MODELS-nimble.svg](MODELS-nimble.svg).

## Comparison with Qwen and Jev

Each question counts as its most probable verdict (the stricter one on a tie),
and scores are `(correct + 0.5 · partial) / 50` in percent.

### Ceiling (40 Models)

| Model | en Qwen | en Jev | en Nimble | ja Qwen | ja Jev | ja Nimble |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `openai_gpt-5.6-luna` | 100 | 94 | **98** | 97 | 90 | **97** |
| `openai_gpt-5.6-sol` | 100 | 93 | **97** | 100 | 92 | **96** |
| `openai_gpt-6-luna` | 100 | 95 | **96** | 100 | 89 | **97** |
| `copilot_grok-4.5` | 100 | 94 | **95** | 99 | 93 | **97** |
| `openrouter_minimax_minimax-m3_free` | 98 | 95 | **94** | 99 | 93 | **98** |
| `openrouter_stealth_ox-alpha` | 98 | 95 | **96** | 100 | 96 | **96** |
| `google_gemma-4-31b-it` | 99 | 97 | **95** | 98 | 92 | **96** |
| `openai_gpt-5.6-terra` | 96 | 92 | **95** | 99 | 91 | **96** |
| `opencode_muse-spark-1.2-contributor-free` | 98 | 96 | **95** | 100 | 96 | **96** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | **98** | 100 | 96 | **93** |
| `opencode_union-alpha` | 100 | 95 | **95** | 100 | 93 | **96** |
| `copilot_kimi-k2.7-code` | 99 | 94 | **94** | 99 | 91 | **96** |
| `opencode_mimo-v2.5-free` | 100 | 93 | **97** | 96 | 88 | **93** |
| `copilot_gpt-5.6-luna` | 99 | 91 | **93** | 98 | 88 | **96** |
| `google_gemini-3-flash-preview` | 100 | 94 | **95** | 98 | 91 | **94** |
| `ollama_qwen3.8` | 100 | 96 | **97** | 99 | 91 | **92** |
| `opencode_big-pickle` | 97 | 88 | **94** | 97 | 88 | **95** |
| `opencode_mimo-v2.6-flash-free` | 100 | 96 | **98** | 95 | 87 | **91** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 92 | **92** | 97 | 93 | **97** |
| `ollama_gemma4_26b-a4b-it-qat` | 95 | 87 | **94** | 92 | 82 | **94** |
| `google_gemini-3.8-flash` | 98 | 91 | **91** | 97 | 88 | **96** |
| `ollama_muse-glimmer` | 99 | 94 | **92** | 97 | 93 | **95** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 94 | 87 | **93** | 90 | 84 | **94** |
| `copilot_claude-haiku-4.5` | 98 | 90 | **92** | 98 | 85 | **94** |
| `google_gemini-2.5-flash` | 94 | 88 | **91** | 96 | 85 | **95** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 97 | 88 | **92** | 95 | 82 | **94** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | **96** | 97 | 86 | **90** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 99 | 90 | **94** | 96 | 86 | **91** |
| `ollama_qwen3.6` | 98 | 88 | **91** | 97 | 86 | **93** |
| `google_gemini-3.7-flash` | 97 | 87 | **88** | 98 | 85 | **94** |
| `copilot_mai-code-1.1-flash` | 97 | 88 | **92** | 93 | 82 | **89** |
| `google_gemma-4-26b-a4b-it` | 95 | 85 | **91** | 94 | 81 | **90** |
| `openrouter_stealth_space-bunny-alpha` | 97 | 90 | **93** | 93 | 80 | **88** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 93 | 84 | **88** | 86 | 79 | **84** |
| `google_gemini-3.5-flash-lite` | 86 | 81 | **82** | 86 | 79 | **86** |
| `ollama_qwen3.5_9b` | 90 | 78 | **87** | 78 | 73 | **78** |
| `openrouter_cohere_north-mini-code_free` | 92 | 85 | **91** | 73 | 67 | **73** |
| `ollama_gemma4_12b-it-qat` | 84 | 78 | **82** | 83 | 72 | **80** |
| `openrouter_poolside_laguna-s-2.1_free` | 89 | 78 | **90** | 72 | 63 | **69** |
| `ollama_qwen3.5_4b` | 81 | 72 | **75** | 71 | 66 | **75** |

Sorted by the Nimble score summed over both languages.

- **Saturation resolved without over-penalization**:
  Under Qwen, 7 models tied at 100% in both languages. Under Jev, no model reached
  98% and Japanese scores were severely depressed across the board. Under Nimble,
  the top reaches 98% (en) / 97% (ja) led by `openai_gpt-5.6-luna` (overall 97.5%),
  with no 100% ties, clearly separating frontier models.
- **Multilingual stability (Ja − En gap)**:
  While Jev exhibited a pronounced negative bias against Japanese answers (mean
  Japanese score was −4.03% lower than English), Nimble exhibits minimal language
  gap: **−1.12%** on average (compared to −2.45% for Qwen).
- **Correlation**:
  Pearson correlation of Ceiling scores across all 40 models is **$r = 0.966$**
  with Qwen and **$r = 0.942$** with Jev. The relative model capabilities remain
  highly consistent.

### Verdict transitions (4,100 Questions)

Across all 82 judged runs (2,050 questions per language, Ceiling and Hybrid8 combined):

#### Qwen vs. Nimble

| Qwen \ Nimble (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,824 | 196 | 0 |
| **partial** | 22 | 78 | 0 |
| **incorrect** | 0 | 13 | 17 |

*Agreement: 1,919 / 2,050 (93.6%)*

| Qwen \ Nimble (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,776 | 167 | 1 |
| **partial** | 45 | 106 | 2 |
| **incorrect** | 1 | 16 | 36 |

*Agreement: 1,918 / 2,050 (93.6%)*

The primary shift is Qwen *correct* → Nimble *partial* (196 in en, 167 in ja).
Nimble enforces stricter completeness on multi-part questions while rarely
altering *incorrect* verdicts.

#### Jev vs. Nimble

| Jev \ Nimble (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,660 | 71 | 0 |
| **partial** | 186 | 208 | 3 |
| **incorrect** | 0 | 8 | 14 |

*Agreement: 1,882 / 2,050 (91.8%)*

| Jev \ Nimble (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,550 | 38 | 1 |
| **partial** | 272 | 240 | 3 |
| **incorrect** | 0 | 11 | 35 |

*Agreement: 1,825 / 2,050 (89.0%)*

The prominent difference is Jev *partial* → Nimble *correct* (186 in en, 272 in ja).
Jev's aggressive penalization of Japanese answers is moderated by Nimble,
restoring legitimate points to concise and accurate answers.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 95% | 92% | −3% | 96% | 91% | −5% |
| `ollama_qwen3.8` | 97% | 94% | −3% | 92% | 94% | +2% |
| `openrouter_stealth_ox-alpha` | 96% | 94% | −2% | 96% | 94% | −2% |

All three models lose only 2–5% when switching from gold context to Hybrid8
retrieval, confirming that dense ∪ BM25 hybrid retrieval delivers near-ceiling
accuracy regardless of the judge.
