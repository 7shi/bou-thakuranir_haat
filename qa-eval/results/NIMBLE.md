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
- **Wall time**: 46m 24s (2,784 s in total, ~34.0 s per file of 50 questions,
  ~0.679 s per request)
- **Cost**: **$0.00** (fully local execution via Ollama GPU inference, zero API fees)
- **Output**: Strictly 1 token per question directly from the `/v1/systemone`
  endpoint, eliminating autoregressive text generation overhead.

Since Nimble runs locally, cost and tokens are not compared with the paid
judges; time is. Per file, Nimble takes about 3× as long as Jev (11.1 s, see
[JEV.md](JEV.md)).

`make report-nimble` aggregates the Nimble verdicts into [report-nimble.md](report-nimble.md)
and [MODELS-nimble.svg](MODELS-nimble.svg).

## Comparison with Qwen and Jev

Each question counts as its most probable verdict (the stricter one on a tie),
and scores are `(correct + 0.5 · partial) / 50` in percent.

### Ceiling (40 Models)

| Model | en Qwen | en Jev | en Nimble | ja Qwen | ja Jev | ja Nimble |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `openai_gpt-6-luna` | 98 | 91 | **97** | 99 | 88 | **98** |
| `openai_gpt-5.6-sol` | 100 | 91 | **97** | 100 | 90 | **97** |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | **98** | 100 | 97 | **96** |
| `openai_gpt-5.6-luna` | 100 | 92 | **97** | 98 | 89 | **96** |
| `opencode_muse-spark-1.2-contributor-free` | 100 | 96 | **96** | 100 | 96 | **97** |
| `opencode_union-alpha` | 100 | 98 | **98** | 100 | 94 | **95** |
| `copilot_grok-4.5` | 100 | 95 | **96** | 100 | 94 | **96** |
| `openrouter_minimax_minimax-m3_free` | 100 | 98 | **96** | 99 | 91 | **96** |
| `openrouter_stealth_ox-alpha` | 100 | 98 | **99** | 100 | 94 | **93** |
| `google_gemini-3-flash-preview` | 100 | 94 | **97** | 100 | 91 | **94** |
| `ollama_muse-glimmer` | 99 | 95 | **96** | 99 | 93 | **95** |
| `google_gemma-4-31b-it` | 99 | 93 | **96** | 99 | 90 | **95** |
| `copilot_gpt-5.6-luna` | 99 | 87 | **94** | 98 | 88 | **96** |
| `copilot_kimi-k2.7-code` | 100 | 95 | **96** | 99 | 92 | **94** |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 86 | **95** | 95 | 81 | **95** |
| `openai_gpt-5.6-terra` | 100 | 94 | **94** | 100 | 89 | **96** |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 93 | **93** | 96 | 91 | **97** |
| `google_gemini-3.8-flash` | 97 | 89 | **94** | 97 | 90 | **95** |
| `opencode_big-pickle` | 99 | 91 | **94** | 96 | 87 | **95** |
| `opencode_mimo-v2.5-free` | 100 | 94 | **97** | 95 | 88 | **92** |
| `ollama_qwen3.8` | 100 | 98 | **97** | 97 | 92 | **91** |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | **97** | 95 | 87 | **91** |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | **94** | 98 | 86 | **93** |
| `google_gemini-2.5-flash` | 93 | 87 | **92** | 96 | 86 | **94** |
| `google_gemini-3.7-flash` | 98 | 89 | **91** | 97 | 88 | **95** |
| `ollama_qwen3.6` | 97 | 90 | **91** | 96 | 86 | **94** |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 90 | **92** | 96 | 81 | **93** |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 88 | **91** | 94 | 85 | **94** |
| `copilot_claude-haiku-4.5` | 97 | 88 | **90** | 98 | 86 | **94** |
| `copilot_mai-code-1.1-flash` | 99 | 89 | **95** | 93 | 84 | **89** |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | **93** | 94 | 84 | **90** |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | **92** | 96 | 85 | **90** |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | **94** | 92 | 80 | **88** |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 83 | **88** | 87 | 78 | **83** |
| `google_gemini-3.5-flash-lite` | 85 | 81 | **83** | 86 | 77 | **86** |
| `ollama_qwen3.5_9b` | 91 | 78 | **87** | 77 | 73 | **78** |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | **91** | 74 | 67 | **73** |
| `ollama_gemma4_12b-it-qat` | 83 | 76 | **81** | 82 | 72 | **80** |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | **90** | 71 | 63 | **69** |
| `ollama_qwen3.5_4b` | 79 | 72 | **74** | 72 | 67 | **74** |

Sorted by the Nimble score summed over both languages.

- **Saturation resolved without over-penalization**:
  Under Qwen, 8 models tied at 100% in both languages. Under Jev, no model reached
  98% in Japanese and Japanese scores were severely depressed across the board.
  Under Nimble, the top reaches 99% (en) / 98% (ja) and is led overall by
  `openai_gpt-6-luna` (97.5%), with no 100% ties, clearly separating frontier models.
- **Multilingual stability (Ja − En gap)**:
  While Jev exhibited a pronounced negative bias against Japanese answers (mean
  Japanese score was −4.15% lower than English), Nimble exhibits a smaller language
  gap: **−1.90%** on average (compared to −2.38% for Qwen).
- **Correlation**:
  Pearson correlation of Ceiling scores across all 40 models is **$r = 0.981$**
  with Qwen and **$r = 0.933$** with Jev. The relative model capabilities remain
  highly consistent.

### Verdict transitions (4,300 Questions)

Across the 82 judged runs here plus the canonical Gemma Ceiling and Hybrid8
runs (43 runs and 2,150 questions per language, Ceiling and Hybrid8 combined):

#### Qwen vs. Nimble

| Qwen \ Nimble (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,842 | 180 | 0 |
| **partial** | 27 | 73 | 0 |
| **incorrect** | 0 | 11 | 17 |

*Agreement: 1,932 / 2,150 (89.9%)*

| Qwen \ Nimble (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,778 | 171 | 1 |
| **partial** | 37 | 107 | 3 |
| **incorrect** | 0 | 17 | 36 |

*Agreement: 1,921 / 2,150 (89.3%)*

The primary shift is Qwen *correct* → Nimble *partial* (180 in en, 171 in ja).
Nimble enforces stricter completeness on multi-part questions while rarely
altering *incorrect* verdicts.

#### Jev vs. Nimble

| Jev \ Nimble (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,668 | 59 | 0 |
| **partial** | 201 | 199 | 3 |
| **incorrect** | 0 | 6 | 14 |

*Agreement: 1,881 / 2,150 (87.5%)*

| Jev \ Nimble (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,547 | 35 | 1 |
| **partial** | 268 | 245 | 4 |
| **incorrect** | 0 | 15 | 35 |

*Agreement: 1,827 / 2,150 (85.0%)*

The prominent difference is Jev *partial* → Nimble *correct* (201 in en, 268 in ja).
Jev's aggressive penalization of Japanese answers is moderated by Nimble,
restoring legitimate points to concise and accurate answers.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 96% | 91% | −5% | 95% | 91% | −4% |
| `ollama_qwen3.8` | 97% | 93% | −4% | 91% | 93% | +2% |
| `openrouter_stealth_ox-alpha` | 99% | 95% | −4% | 93% | 94% | +1% |

All three models lose at most 5% when switching from gold context to Hybrid8
retrieval, and two gain slightly in Japanese, confirming that dense ∪ BM25 hybrid retrieval delivers near-ceiling
accuracy regardless of the judge.
