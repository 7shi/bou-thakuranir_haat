# OpenAI Decisions grading of the per-model runs

The per-model runs in this directory were graded with OpenAI's **Decisions
API** (`gpt-6-luna`) and compared with the existing `ollama:qwen3.6`, TypeSafe
Jev and Bespoke Labs Nimble verdicts. The scores in
[report-openai.md](report-openai.md) and [MODELS-openai.svg](MODELS-openai.svg)
are the OpenAI verdicts. This document records the grading run and how the
verdicts compare across all 51 models. The same comparison for
`results-<lang>/`: [../OPENAI.md](../OPENAI.md). The same model replying with
the verdict word through the ordinary API: [TERNARY.md](TERNARY.md).

## Grading run

Every answer file here was graded by one `make judge-openai` run (see
[Makefile](Makefile)), writing `openai/*.tsv`.

- **Judge**: [judge-openai.py](../judge-openai.py), `gpt-6-luna` via
  `POST /decisions`, scheme `choice@849ecf1c` (recorded for all 104 files in
  `openai/MODELS.tsv`). The rubric is Jev's; the scheme differs only because
  the API takes the state as a JSON string and a single instruction string.
- **Scope**: 104 answer files (52 per language; 50 ceiling + 2 hybrid8) × 50
  questions = 5,200 requests, one `judge-openai.py` call per language
- **Wall time**: 21m 14.0s (about 12.3 s per file of 50 questions, 0.245 s per
  request)
- **Cost**: $0.2814 in total at $0.10 per 1M input tokens (about $0.0027 per
  file, $0.054 per 1,000 requests)

Token usage, from llm7shi's `usage.jsonl` (one entry per language, recorded as
`decisions:gpt-6-luna`):

| Language | Files | Input | Output | Input / file | Input / request |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 52 | 1,193,775 | 0 | 22,957 | 459 |
| Japanese | 52 | 1,620,684 | 0 | 31,167 | 623 |
| Total | 104 | 2,814,459 | 0 | 27,062 | 541 |

The Decisions API returns probabilities without generating anything, so there
are no output tokens and the cost is input only. Japanese needs about 1.36× the
tokens of English for the same material.

### Per-file comparison

The three grading runs covered different numbers of files (82 for Jev and
Nimble, 104 here), so they are compared per file (one model × one language,
50 questions):

| Judge | Files | Time / file | Input / file (en / ja) | Output / file | Cost / file |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Jev ([JEV.md](JEV.md)) | 82 | 11.1 s | 34,415 / 46,032 | 1,950 | $0.0017 |
| Nimble ([NIMBLE.md](NIMBLE.md)) | 82 | 34.0 s | — | — | — (local) |
| **OpenAI** | **104** | **12.3 s** | **22,957 / 31,167** | **0** | **$0.0027** |

- **Time** compares all three: OpenAI is about as fast as Jev, and Nimble takes
  about 3× as long.
- **Tokens and cost** compare the two paid APIs only, since Nimble runs locally
  at no cost. OpenAI counts about 2/3 of Jev's input tokens, but the two use
  different tokenizers, so the counts do not measure the same thing; cost is
  the comparable figure, and OpenAI costs about 1.6× Jev per file.
- **Ratio to Jev**: Jev : OpenAI is about 1 : 1.11 in time and 1 : 1.60 in
  cost per file. The `results-<lang>/` re-grading ([../OPENAI.md](../OPENAI.md))
  gives 1 : 1.26 and 1 : 1.59: the cost ratio holds across runs, while the time
  ratio varies with API response times.
- The Jev and Nimble figures come from runs over the first 82 files; the 22
  files added since are included only in this run, so the per-file figures
  are close but not exactly like-for-like.

`make report-openai` aggregates the OpenAI verdicts into
[report-openai.md](report-openai.md) and [MODELS-openai.svg](MODELS-openai.svg).

## Comparison with Qwen, Jev and Nimble

Each question counts as its most probable verdict (the stricter one on a tie),
and scores are `(correct + 0.5 · partial) / 50` in percent. **E** is the same
score over the OpenAI probabilities, mean of P(correct) + 0.5 · P(partial).

### Ceiling (51 Models)

| Model | en Qwen | en Jev | en Nimble | en OpenAI | en E | ja Qwen | ja Jev | ja Nimble | ja OpenAI | ja E |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `opencode_muse-spark-1.2-contributor-free` | 100 | 96 | 96 | **100** | 99.8 | 100 | 96 | 97 | **100** | 99.2 |
| `openrouter_stealth_ox-alpha` | 100 | 98 | 99 | **100** | 99.6 | 100 | 94 | 93 | **98** | 97.3 |
| `openai_gpt-6-astra` | 100 | 93 | 98 | **99** | 97.4 | 100 | 89 | 97 | **98** | 96.3 |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 98 | **99** | 97.9 | 100 | 97 | 96 | **97** | 95.9 |
| `copilot_kimi-k3` | 100 | 96 | 95 | **98** | 96.9 | 100 | 94 | 97 | **97** | 95.6 |
| `openai_gpt-6.1-sol` | 100 | 95 | 95 | **99** | 98.3 | 100 | 87 | 95 | **95** | 94.1 |
| `opencode_union-alpha` | 100 | 98 | 98 | **98** | 97.2 | 100 | 94 | 95 | **96** | 93.7 |
| `openrouter_minimax_minimax-m3_free` | 100 | 98 | 96 | **97** | 96.2 | 99 | 91 | 96 | **96** | 95.0 |
| `copilot_kimi-k2.7-code` | 100 | 95 | 96 | **98** | 97.1 | 99 | 92 | 94 | **93** | 92.3 |
| `ollama_qwen3.8` | 100 | 98 | 97 | **97** | 96.7 | 97 | 92 | 91 | **94** | 93.7 |
| `ollama_muse-glimmer` | 99 | 95 | 96 | **96** | 95.2 | 99 | 93 | 95 | **94** | 92.8 |
| `openai_gpt-5.6-sol` | 100 | 91 | 97 | **94** | 92.9 | 100 | 90 | 97 | **96** | 93.4 |
| `opencode_ling-3.1-flash-free` | 100 | 95 | 96 | **97** | 96.6 | 99 | 90 | 93 | **93** | 92.9 |
| `copilot_claude-sonnet-5` | 100 | 97 | 98 | **98** | 96.9 | 95 | 84 | 88 | **91** | 90.0 |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | 97 | **98** | 97.2 | 95 | 87 | 91 | **91** | 89.4 |
| `copilot_gpt-5.6-luna` | 99 | 87 | 94 | **96** | 93.5 | 98 | 88 | 96 | **92** | 90.9 |
| `copilot_grok-4.6` | 100 | 93 | 96 | **98** | 96.3 | 99 | 90 | 96 | **90** | 89.5 |
| `openai_gpt-6-sol` | 100 | 94 | 99 | **96** | 95.0 | 100 | 90 | 99 | **92** | 90.7 |
| `google_gemma-4-31b-it` | 99 | 93 | 96 | **97** | 95.4 | 99 | 90 | 95 | **91** | 89.7 |
| `openai_gpt-6-luna` | 98 | 91 | 97 | **93** | 93.4 | 99 | 88 | 98 | **94** | 92.6 |
| `copilot_grok-4.5` | 100 | 95 | 96 | **95** | 93.6 | 100 | 94 | 96 | **91** | 90.7 |
| `google_gemini-3.8-flash` | 97 | 89 | 94 | **95** | 93.0 | 97 | 90 | 95 | **91** | 90.2 |
| `openai_gpt-5.6-luna` | 100 | 92 | 97 | **95** | 94.4 | 98 | 89 | 96 | **91** | 91.1 |
| `openai_gpt-5.6-terra` | 100 | 94 | 94 | **94** | 93.0 | 100 | 89 | 96 | **92** | 90.6 |
| `opencode_fledge-alpha-free` | 99 | 94 | 97 | **94** | 93.1 | 99 | 90 | 96 | **92** | 90.6 |
| `openrouter_apodex_apodex-1.1-mini_free` | 98 | 94 | 92 | **97** | 95.6 | 97 | 89 | 94 | **88** | 86.9 |
| `google_gemini-3-flash-preview` | 100 | 94 | 97 | **95** | 93.4 | 100 | 91 | 94 | **89** | 89.6 |
| `opencode_big-pickle` | 99 | 91 | 94 | **95** | 94.0 | 96 | 87 | 95 | **89** | 88.4 |
| `opencode_longcat-2.5-preview-free` | 100 | 94 | 95 | **95** | 95.3 | 95 | 86 | 92 | **88** | 87.0 |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 93 | 93 | **92** | 93.3 | 96 | 91 | 97 | **91** | 89.7 |
| `google_gemini-2.5-flash` | 93 | 87 | 92 | **93** | 90.8 | 96 | 86 | 94 | **88** | 87.5 |
| `google_gemini-3.7-flash` | 98 | 89 | 91 | **91** | 90.5 | 97 | 88 | 95 | **90** | 89.5 |
| `opencode_mimo-v2.5-free` | 100 | 94 | 97 | **96** | 94.4 | 95 | 88 | 92 | **85** | 85.2 |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | 94 | **92** | 92.3 | 98 | 86 | 93 | **88** | 86.5 |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 90 | 92 | **93** | 90.6 | 96 | 81 | 93 | **86** | 85.3 |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 88 | 91 | **90** | 87.5 | 94 | 85 | 94 | **88** | 85.9 |
| `copilot_claude-haiku-4.5` | 97 | 88 | 90 | **93** | 91.5 | 98 | 86 | 94 | **83** | 82.4 |
| `copilot_mai-code-1.1-flash` | 99 | 89 | 95 | **92** | 90.4 | 93 | 84 | 89 | **83** | 81.8 |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | 93 | **89** | 88.1 | 94 | 84 | 90 | **85** | 83.1 |
| `ollama_qwen3.6` | 97 | 90 | 91 | **89** | 88.4 | 96 | 86 | 94 | **84** | 84.4 |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 92 | **91** | 89.2 | 96 | 85 | 90 | **82** | 84.2 |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 86 | 95 | **86** | 85.1 | 95 | 81 | 95 | **85** | 85.0 |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | 94 | **92** | 91.2 | 92 | 80 | 88 | **79** | 79.4 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 83 | 88 | **86** | 85.3 | 87 | 78 | 83 | **76** | 75.9 |
| `google_gemini-3.5-flash-lite` | 85 | 81 | 83 | **84** | 83.1 | 86 | 77 | 86 | **77** | 76.3 |
| `ollama_qwen3.5_9b` | 91 | 78 | 87 | **81** | 81.0 | 77 | 73 | 78 | **76** | 74.7 |
| `ollama_gemma4_12b-it-qat` | 83 | 76 | 81 | **79** | 78.7 | 82 | 72 | 80 | **75** | 74.5 |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | 91 | **84** | 83.5 | 74 | 67 | 73 | **68** | 67.8 |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | 90 | **86** | 84.4 | 71 | 63 | 69 | **65** | 65.1 |
| `openrouter_poolside_laguna-xs-2.1_free` | 91 | 81 | 90 | **81** | 80.4 | 68 | 64 | 73 | **63** | 64.0 |
| `ollama_qwen3.5_4b` | 79 | 72 | 74 | **70** | 72.7 | 72 | 67 | 74 | **68** | 68.2 |

Sorted by the OpenAI score summed over both languages.

- **Top separation, with a little saturation in English**:
  Under Qwen, 35 of 51 models score ≥ 98 in English (23 at 100). Under Jev 4
  (en) / none (ja) reach 98, and under Nimble 6 (en) / 2 (ja) do. Under OpenAI
  11 models reach 98 in English and 3 in Japanese, and three scores are 100
  (`opencode_muse-spark-1.2-contributor-free` in both languages,
  `openrouter_stealth_ox-alpha` in English). The top is
  `opencode_muse-spark-1.2-contributor-free` (100 / 100) and
  `openrouter_stealth_ox-alpha` (100 / 98).
- **Japanese penalty like Jev's (Ja − En gap)**:
  Over all 51 models, the mean Japanese score is **−5.27** points below
  English under OpenAI, beyond Jev (−4.69) and well beyond Qwen (−2.57) and
  Nimble (−2.10). Some models fall sharply, e.g.
  `copilot_claude-haiku-4.5` (93 → 83) and
  `openrouter_stealth_space-bunny-alpha` (92 → 79).
- **Correlation**:
  Pearson correlation of the Ceiling scores summed over both languages is
  **$r = 0.965$** with Jev, **$r = 0.945$** with Qwen and **$r = 0.937$**
  with Nimble (51 models each). Rank agreement is lower against Nimble
  (Spearman 0.78 en / 0.76 ja) than against Jev (0.88 en / 0.86 ja) and Qwen
  (0.83 en / 0.87 ja).

### Verdict transitions (5,200 Questions)

Across all 104 judged runs in this directory (2,600 questions per language,
Ceiling and Hybrid8 combined).

#### Qwen vs. OpenAI

| Qwen \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,234 | 234 | 0 |
| **partial** | 9 | 96 | 0 |
| **incorrect** | 0 | 13 | 14 |

*Agreement: 2,344 / 2,600 (90.2%)*

| Qwen \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,994 | 376 | 0 |
| **partial** | 4 | 163 | 1 |
| **incorrect** | 0 | 24 | 38 |

*Agreement: 2,195 / 2,600 (84.4%)*

As with Jev and Nimble, the shift is Qwen *correct* → OpenAI *partial* (234 in
en, 376 in ja), larger in Japanese.

#### Jev vs. OpenAI

| Jev \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,061 | 64 | 0 |
| **partial** | 182 | 274 | 0 |
| **incorrect** | 0 | 5 | 14 |

*Agreement: 2,349 / 2,600 (90.3%)*

| Jev \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,812 | 109 | 0 |
| **partial** | 186 | 434 | 1 |
| **incorrect** | 0 | 20 | 38 |

*Agreement: 2,284 / 2,600 (87.8%)*

The disagreements run both ways: Jev *partial* → OpenAI *correct* (182 en,
186 ja) outnumbers Jev *correct* → OpenAI *partial* (64 en, 109 ja), so OpenAI
is the more lenient of the two, but less one-sidedly than Nimble.

##### Why Jev stays below 100

Under Jev the best scores are 98 (en, four models) / 97 (ja), while OpenAI
gives 98–100 to the strongest answers. Looking at the English Ceiling answers
of all 51 models:

- **Deductions sit on particular questions, not particular answers.** Jev
  grades Q46 below *correct* for 43 of 51 models, Q37 for 39, Q34 for 35 and
  Q32 for 33, so nearly every model loses the same few questions. This
  per-question floor is what caps the scores.
- **Jev holds to the gold answer's details.** On Q32,
  `openrouter_stealth_ox-alpha` gives the guards' dismissal, the secret
  stipend, Pratapaditya's discovery and the exile decree, but says only that
  the guards failed to stop Udayaditya, not that he tied up Sitaram at
  Sitaram's own request. Jev grades it *partial* (0.76); OpenAI grades it
  *correct* (0.87).
- **Some deductions are closer to ties.** On Q37 for the same model, Jev gives
  *correct* 0.34 and *partial* 0.66, which the most-probable-verdict rule
  rounds down. E keeps it at about 0.67 of a question instead of 0.5.

Jev's ceiling therefore comes from attachment to the gold answer's details,
with some rounding of split probabilities to *partial*. OpenAI credits answers
that carry the substance without every gold detail, and its scores reach 100,
which keeps the top of the table easier to read.

#### Nimble vs. OpenAI

| Nimble \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,128 | 153 | 0 |
| **partial** | 115 | 186 | 3 |
| **incorrect** | 0 | 4 | 11 |

*Agreement: 2,325 / 2,600 (89.4%)*

| Nimble \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,917 | 287 | 0 |
| **partial** | 81 | 264 | 6 |
| **incorrect** | 0 | 12 | 33 |

*Agreement: 2,214 / 2,600 (85.2%)*

In English, Nimble *correct* → OpenAI *partial* is somewhat more common than
the reverse (153 vs. 115). In Japanese it dominates (287 vs. 81), which is
where OpenAI's Japanese penalty comes from.

Across all three pairs, *correct* and *incorrect* never swap; every judge
agrees on what is wrong and differs only at the *correct* / *partial*
boundary.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models, under OpenAI:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 97% | 87% | −10% | 91% | 88% | −3% |
| `ollama_qwen3.8` | 97% | 96% | −1% | 94% | 91% | −3% |
| `openrouter_stealth_ox-alpha` | 100% | 97% | −3% | 98% | 95% | −3% |

`ollama_qwen3.8` and `openrouter_stealth_ox-alpha` lose 1–3 points with the
Hybrid8 context. The 10-point English drop of `google_gemma-4-31b-it` is not
specific to OpenAI: the same pair of runs drops 7 points under Qwen and 9
under Jev, while Nimble shows 5.
