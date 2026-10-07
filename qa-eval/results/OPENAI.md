# OpenAI Decisions grading of the per-model runs

The per-model runs in this directory were graded with OpenAI's **Decisions
API** (`gpt-6-luna`) and compared with the existing `ollama:qwen3.6`, TypeSafe
Jev and Bespoke Labs Nimble verdicts. The scores in
[report-openai.md](report-openai.md) and [MODELS-openai.svg](MODELS-openai.svg)
are the OpenAI verdicts. This document records the grading run and how the
verdicts compare across all 51 models. The same comparison for
`results-<lang>/`: [../OPENAI.md](../OPENAI.md).

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
| `openrouter_stealth_ox-alpha` | 98 | 95 | 96 | **100** | 98.4 | 100 | 96 | 96 | **99** | 98.1 |
| `opencode_muse-spark-1.2-contributor-free` | 98 | 96 | 95 | **99** | 98.3 | 100 | 96 | 96 | **99** | 98.5 |
| `copilot_kimi-k3` | — | 94 | 95 | **98** | 97.3 | — | 95 | 98 | **98** | 96.3 |
| `openai_gpt-6-astra` | — | 92 | 96 | **99** | 97.9 | — | 89 | 97 | **97** | 96.0 |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 98 | **99** | 98.0 | 100 | 96 | 93 | **97** | 97.3 |
| `opencode_union-alpha` | 100 | 95 | 95 | **98** | 96.6 | 100 | 93 | 96 | **97** | 95.0 |
| `copilot_kimi-k2.7-code` | 99 | 94 | 94 | **98** | 96.0 | 99 | 91 | 96 | **96** | 93.8 |
| `ollama_qwen3.8` | 100 | 96 | 97 | **97** | 96.6 | 99 | 91 | 92 | **96** | 95.9 |
| `openai_gpt-6.1-sol` | — | 95 | 95 | **97** | 97.4 | — | 84 | 97 | **96** | 94.8 |
| `openai_gpt-5.6-sol` | 100 | 93 | 97 | **96** | 94.7 | 100 | 92 | 96 | **96** | 93.6 |
| `openrouter_minimax_minimax-m3_free` | 98 | 95 | 94 | **96** | 95.5 | 99 | 93 | 98 | **96** | 95.6 |
| `copilot_grok-4.6` | — | 93 | 95 | **97** | 95.8 | — | 90 | 95 | **94** | 92.0 |
| `opencode_ling-3.1-flash-free` | — | 95 | 94 | **95** | 95.0 | — | 89 | 93 | **96** | 95.2 |
| `copilot_claude-sonnet-5` | — | 97 | 97 | **97** | 97.3 | — | 86 | 90 | **93** | 91.0 |
| `copilot_gpt-5.6-luna` | 99 | 91 | 93 | **98** | 95.0 | 98 | 88 | 96 | **92** | 91.5 |
| `openai_gpt-6-luna` | 100 | 95 | 96 | **95** | 94.9 | 100 | 89 | 97 | **95** | 94.1 |
| `openai_gpt-5.6-terra` | 96 | 92 | 95 | **95** | 93.1 | 99 | 91 | 96 | **94** | 91.3 |
| `opencode_mimo-v2.6-flash-free` | 100 | 96 | 98 | **99** | 97.1 | 95 | 87 | 91 | **90** | 89.5 |
| `google_gemma-4-31b-it` | 99 | 97 | 95 | **96** | 95.6 | 98 | 92 | 96 | **92** | 90.9 |
| `ollama_muse-glimmer` | 99 | 94 | 92 | **95** | 94.8 | 97 | 93 | 95 | **93** | 92.9 |
| `copilot_grok-4.5` | 100 | 94 | 95 | **93** | 93.1 | 99 | 93 | 97 | **94** | 92.5 |
| `google_gemini-3-flash-preview` | 100 | 94 | 95 | **95** | 94.5 | 98 | 91 | 94 | **92** | 91.0 |
| `openai_gpt-6-sol` | — | 96 | 98 | **96** | 95.3 | — | 90 | 97 | **91** | 90.6 |
| `opencode_big-pickle` | 97 | 88 | 94 | **95** | 93.2 | 97 | 88 | 95 | **92** | 90.1 |
| `google_gemini-3.8-flash` | 98 | 91 | 91 | **95** | 93.3 | 97 | 88 | 96 | **91** | 90.5 |
| `opencode_mimo-v2.5-free` | 100 | 93 | 97 | **97** | 95.9 | 96 | 88 | 93 | **89** | 87.2 |
| `opencode_fledge-alpha-free` | — | 94 | 96 | **94** | 93.0 | — | 91 | 93 | **91** | 90.7 |
| `openai_gpt-5.6-luna` | 100 | 94 | 98 | **95** | 95.5 | 97 | 90 | 97 | **89** | 90.5 |
| `google_gemini-3.7-flash` | 97 | 87 | 88 | **92** | 91.7 | 98 | 85 | 94 | **91** | 90.6 |
| `openrouter_apodex_apodex-1.1-mini_free` | — | 94 | 92 | **95** | 94.9 | — | 91 | 91 | **88** | 87.3 |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 92 | 92 | **92** | 93.0 | 97 | 93 | 97 | **91** | 90.7 |
| `opencode_longcat-2.5-preview-free` | — | 94 | 94 | **97** | 95.5 | — | 87 | 92 | **85** | 85.8 |
| `google_gemini-2.5-flash` | 94 | 88 | 91 | **91** | 90.3 | 96 | 85 | 95 | **89** | 87.9 |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 99 | 90 | 94 | **92** | 92.6 | 96 | 86 | 91 | **88** | 87.5 |
| `copilot_claude-haiku-4.5` | 98 | 90 | 92 | **94** | 93.1 | 98 | 85 | 94 | **84** | 84.5 |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 97 | 88 | 92 | **90** | 89.5 | 95 | 82 | 94 | **87** | 87.0 |
| `ollama_gemma4_26b-a4b-it-qat` | 95 | 87 | 94 | **88** | 87.0 | 92 | 82 | 94 | **88** | 85.8 |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 96 | **92** | 90.8 | 97 | 86 | 90 | **84** | 84.9 |
| `copilot_mai-code-1.1-flash` | 97 | 88 | 92 | **90** | 89.6 | 93 | 82 | 89 | **85** | 83.6 |
| `google_gemma-4-26b-a4b-it` | 95 | 85 | 91 | **90** | 88.5 | 94 | 81 | 90 | **85** | 83.7 |
| `ollama_qwen3.6` | 98 | 88 | 91 | **89** | 88.8 | 97 | 86 | 93 | **86** | 85.3 |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 94 | 87 | 93 | **89** | 87.6 | 90 | 84 | 94 | **85** | 85.2 |
| `openrouter_stealth_space-bunny-alpha` | 97 | 90 | 93 | **92** | 92.5 | 93 | 80 | 88 | **77** | 79.9 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 93 | 84 | 88 | **86** | 86.1 | 86 | 79 | 84 | **77** | 77.5 |
| `google_gemini-3.5-flash-lite` | 86 | 81 | 82 | **84** | 83.6 | 86 | 79 | 86 | **78** | 77.1 |
| `openrouter_cohere_north-mini-code_free` | 92 | 85 | 91 | **86** | 85.0 | 73 | 67 | 73 | **70** | 69.2 |
| `ollama_gemma4_12b-it-qat` | 84 | 78 | 82 | **80** | 80.5 | 83 | 72 | 80 | **75** | 74.5 |
| `ollama_qwen3.5_9b` | 90 | 78 | 87 | **80** | 80.7 | 78 | 73 | 78 | **75** | 74.0 |
| `openrouter_poolside_laguna-s-2.1_free` | 89 | 78 | 90 | **84** | 84.2 | 72 | 63 | 69 | **65** | 65.0 |
| `openrouter_poolside_laguna-xs-2.1_free` | — | 79 | 88 | **81** | 80.2 | — | 65 | 72 | **65** | 64.9 |
| `ollama_qwen3.5_4b` | 81 | 72 | 75 | **72** | 73.6 | 71 | 66 | 75 | **69** | 68.5 |

Sorted by the OpenAI score summed over both languages. The 11 models without
Qwen verdicts show "—".

- **Top separation, with a little saturation in English**:
  Under Qwen, 22 of 40 models score ≥ 98 in English (10 at 100). Under Jev none
  reaches 98, and under Nimble 4 (en) / 2 (ja) do. Under OpenAI 9 models reach
  98 in English and 3 in Japanese, and one score is 100
  (`openrouter_stealth_ox-alpha`, en). The top is
  `openrouter_stealth_ox-alpha` (100 / 99) and
  `opencode_muse-spark-1.2-contributor-free` (99 / 99).
- **Japanese penalty like Jev's (Ja − En gap)**:
  Over the 40 models all four judges graded, the mean Japanese score is
  **−4.40** points below English under OpenAI, close to Jev (−4.03) and well
  beyond Qwen (−2.45) and Nimble (−1.12). Over all 51 models it is −4.47
  (Jev −4.45, Nimble −1.37). Some models fall sharply, e.g.
  `copilot_claude-haiku-4.5` (94 → 84) and
  `openrouter_stealth_space-bunny-alpha` (92 → 77).
- **Correlation**:
  Pearson correlation of the Ceiling scores summed over both languages is
  **$r = 0.960$** with Jev (51 models), **$r = 0.943$** with Qwen (40 models)
  and **$r = 0.940$** with Nimble (51 models). Rank agreement is lower against
  Nimble (Spearman 0.76 in both languages) than against Jev (0.84 en / 0.85 ja).

### Verdict transitions (5,200 Questions)

Across all 104 judged runs in this directory (2,600 questions per language,
Ceiling and Hybrid8 combined). Qwen covers only the 82 runs it graded (2,050
questions per language).

#### Qwen vs. OpenAI

| Qwen \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,736 | 190 | 0 |
| **partial** | 6 | 90 | 0 |
| **incorrect** | 1 | 14 | 13 |

*Agreement: 1,839 / 2,050 (89.7%)*

| Qwen \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,577 | 273 | 0 |
| **partial** | 9 | 138 | 1 |
| **incorrect** | 0 | 21 | 31 |

*Agreement: 1,746 / 2,050 (85.2%)*

As with Jev and Nimble, the shift is Qwen *correct* → OpenAI *partial* (190 in
en, 273 in ja), larger in Japanese.

#### Jev vs. OpenAI

| Jev \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,054 | 65 | 0 |
| **partial** | 186 | 274 | 0 |
| **incorrect** | 0 | 7 | 14 |

*Agreement: 2,342 / 2,600 (90.1%)*

| Jev \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,824 | 101 | 0 |
| **partial** | 210 | 410 | 2 |
| **incorrect** | 0 | 19 | 34 |

*Agreement: 2,268 / 2,600 (87.2%)*

The disagreements run both ways: Jev *partial* → OpenAI *correct* (186 en,
210 ja) outnumbers Jev *correct* → OpenAI *partial* (65 en, 101 ja), so OpenAI
is the more lenient of the two, but less one-sidedly than Nimble.

##### Why Jev tops out around 96

Under Jev no model passes 97 (en) / 96 (ja), while OpenAI gives 98–100 to the
strongest answers. Looking at the English Ceiling answers of all 51 models:

- **Deductions sit on particular questions, not particular answers.** Jev
  grades Q42 below *correct* for 40 of 51 models, Q37 for 35, and Q46 and Q34
  for 29 each, so nearly every model loses the same few questions. This
  per-question floor is what caps the scores.
- **The gold answer's wording outweighs the rationale.** On Q42,
  `openrouter_stealth_ox-alpha` gives the forged petition with the Yubaraj's
  seal, the imprisonment, the fire at the guard huts and the rescue from the
  cell, missing only the "waiting escape boat" of the gold answer. The
  rationale does not mention the boat ("rushing Udayaditya out to safety"),
  and the answer matches it. Jev grades it *partial* (0.80); OpenAI grades it
  *correct*. The rubric tells the judge to use the rationale as supporting
  evidence, but Jev holds to the gold answer's details.
- **Even an answer containing the gold answer can lose credit.** On Q22 the
  gold answer is "His own cloth." and the same model answers "His own cloth",
  adding whose cloth it took it to be. Jev grades it *partial* (0.69). The
  added reading may be what Jev objects to, but the source sentence ("tied him
  up with his own cloth") is itself ambiguous on that point.
- **Many deductions are near-ties.** On Q32, Q33 and Q37 for the same model,
  Jev gives *correct* 0.42–0.45 and *partial* 0.54–0.58: not a confident
  *partial*, but a near-even split that the most-probable-verdict rule rounds
  down. E keeps these at roughly 0.7 of a question each instead of 0.5.

Jev's ceiling therefore comes from attachment to the gold answer's details
combined with rounding near-even splits to *partial*. OpenAI credits answers
that carry the substance without every gold detail, and its scores reach 100,
which keeps the top of the table easier to read.

#### Nimble vs. OpenAI

| Nimble \ OpenAI (en) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 2,108 | 139 | 0 |
| **partial** | 132 | 203 | 3 |
| **incorrect** | 0 | 4 | 11 |

*Agreement: 2,322 / 2,600 (89.3%)*

| Nimble \ OpenAI (ja) | correct | partial | incorrect |
| :--- | ---: | ---: | ---: |
| **correct** | 1,937 | 269 | 0 |
| **partial** | 97 | 249 | 3 |
| **incorrect** | 0 | 12 | 33 |

*Agreement: 2,219 / 2,600 (85.3%)*

In English the two judges disagree about equally in each direction (139 vs.
132). In Japanese, Nimble *correct* → OpenAI *partial* dominates (269 vs. 97),
which is where OpenAI's Japanese penalty comes from.

Across all three pairs, *correct* and *incorrect* almost never swap (one
Qwen *incorrect* → OpenAI *correct* in English); every judge agrees on what is
wrong and differs only at the *correct* / *partial* boundary.

### Hybrid8 vs. Ceiling

Comparing retrieval context (`hybrid8`) vs. gold chapters (`ceiling`) for the
three tested models, under OpenAI:

| Model | en Ceiling | en Hybrid8 | en Δ | ja Ceiling | ja Hybrid8 | ja Δ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `google_gemma-4-31b-it` | 96% | 88% | −8% | 92% | 89% | −3% |
| `ollama_qwen3.8` | 97% | 95% | −2% | 96% | 92% | −4% |
| `openrouter_stealth_ox-alpha` | 100% | 97% | −3% | 99% | 96% | −3% |

`ollama_qwen3.8` and `openrouter_stealth_ox-alpha` lose 2–4 points with the
Hybrid8 context. The 8-point English drop of `google_gemma-4-31b-it` is not
specific to OpenAI: the same pair of runs drops 6 points under Qwen and 10
under Jev, while Nimble shows only 3.
