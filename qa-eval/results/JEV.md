# Jev grading of the per-model runs

The per-model runs in this directory are graded with TypeSafe's Jev instead of
the `ollama:qwen3.6` judge, and the scores in [README.md](README.md) are the
Jev verdicts. This document records how the switch was made: the experiment
that chose Jev, the grading run, and how the verdicts compare with qwen's. The
same switch for `results-<lang>/`: [../JEV.md](../JEV.md).

## Introduction experiment

The switch started from this directory. Under qwen the multi-model Ceiling
table had saturated: many models scored 98–100 in both languages, so the top
no longer separated models. [../jev/README.md](../jev/README.md) tried Jev on
the English Ceiling answers of six models from here, from saturated to
mid-table, plus four retrieval runs from `results-en/`. A single Choice
question over `judge.py`'s rubric moved the three models qwen scored 100 off
the top and widened the gap to `ollama_qwen3.6`, and its extra *partial*
verdicts were omitted parts of multi-part gold answers rather than style, so
the Choice was adopted as the judge.

## Grading run

Every answer file here was then graded by one `make judge-jev` run (see
[Makefile](Makefile)), writing `jev/*.tsv`.

- Judge: [judge-jev.py](../judge-jev.py), `jev-1.13.0`, scheme `choice@19579e23`
  (recorded for all 82 files in `jev/MODELS.tsv`)
- Scope: 82 answer files (41 per language) × 50 questions = 4,100 requests,
  one `judge-jev.py` call per language
- Wall time: 15m 7.5s (about 11.1 s per file of 50 questions, 0.22 s per
  request)
- Cost: $0.1385 in total (about $0.0017 per file, $0.034 per 1,000 requests)

Token usage, from llm7shi's `usage.jsonl` (one entry per language):

| Language | Files | Input | Output | Input / file | Output / file | Input / request | Output / request |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| English | 41 | 1,411,013 | 79,950 | 34,415 | 1,950 | 688 | 39 |
| Japanese | 41 | 1,887,319 | 79,950 | 46,032 | 1,950 | 921 | 39 |
| Total | 82 | 3,298,332 | 159,900 | 40,224 | 1,950 | 804 | 39 |

Output is a fixed 39 tokens per request regardless of content. Input follows
the length of the question, gold answer, rationale and candidate answer;
Japanese needs about 1.34× the tokens of English for the same material.

`make report-jev` aggregates the Jev verdicts into [report-jev.md](report-jev.md)
and [MODELS-jev.svg](MODELS-jev.svg); the qwen verdicts stay in `judge/` and
[report.md](report.md) / [MODELS.svg](MODELS.svg).

## Comparison with qwen

Each question counts as its most probable Jev verdict (the stricter one on a
tie), and scores are `(correct + 0.5·partial) / 50` in percent. **E** is the
same score over the probabilities, mean of P(correct) + 0.5·P(partial), which
also separates models that tie on verdicts.

### Ceiling

| Model | en qwen | en Jev | en E | ja qwen | ja Jev | ja E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 94.2 | 100 | 97 | 92.6 |
| `opencode_muse-spark-1.2-contributor-free` | 100 | 96 | 95.2 | 100 | 96 | 93.6 |
| `opencode_union-alpha` | 100 | 98 | 94.5 | 100 | 94 | 89.7 |
| `openrouter_stealth_ox-alpha` | 100 | 98 | 95.6 | 100 | 94 | 91.5 |
| `ollama_qwen3.8` | 100 | 98 | 94.4 | 97 | 92 | 88.4 |
| `copilot_grok-4.5` | 100 | 95 | 92.0 | 100 | 94 | 91.4 |
| `openrouter_minimax_minimax-m3_free` | 100 | 98 | 93.1 | 99 | 91 | 89.5 |
| `ollama_muse-glimmer` | 99 | 95 | 90.5 | 99 | 93 | 89.2 |
| `copilot_kimi-k2.7-code` | 100 | 95 | 92.9 | 99 | 92 | 89.3 |
| `google_gemini-3-flash-preview` | 100 | 94 | 92.0 | 100 | 91 | 89.3 |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 93 | 90.6 | 96 | 91 | 88.7 |
| `openai_gpt-5.6-terra` | 100 | 94 | 91.4 | 100 | 89 | 88.3 |
| `opencode_mimo-v2.5-free` | 100 | 94 | 90.6 | 95 | 88 | 85.1 |
| `opencode_mimo-v2.6-flash-free` | 100 | 95 | 93.0 | 95 | 87 | 85.4 |
| `openai_gpt-5.6-luna` | 100 | 92 | 90.4 | 98 | 89 | 87.5 |
| `openai_gpt-5.6-sol` | 100 | 91 | 90.3 | 100 | 90 | 89.2 |
| `google_gemini-3.8-flash` | 97 | 89 | 87.9 | 97 | 90 | 87.4 |
| `openai_gpt-6-luna` | 98 | 91 | 89.4 | 99 | 88 | 87.3 |
| `opencode_big-pickle` | 99 | 91 | 88.7 | 96 | 87 | 85.5 |
| `google_gemini-3.7-flash` | 98 | 89 | 87.5 | 97 | 88 | 87.6 |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 100 | 91 | 89.2 | 98 | 86 | 85.5 |
| `ollama_qwen3.6` | 97 | 90 | 87.6 | 96 | 86 | 84.3 |
| `copilot_gpt-5.6-luna` | 99 | 87 | 88.5 | 98 | 88 | 86.2 |
| `copilot_claude-haiku-4.5` | 97 | 88 | 87.5 | 98 | 86 | 84.3 |
| `copilot_mai-code-1.1-flash` | 99 | 89 | 86.3 | 93 | 84 | 81.2 |
| `google_gemini-2.5-flash` | 93 | 87 | 85.7 | 96 | 86 | 85.4 |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 95 | 88 | 85.3 | 94 | 85 | 84.3 |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 86.8 | 96 | 85 | 84.5 |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 98 | 90 | 86.9 | 96 | 81 | 83.2 |
| `google_gemma-4-26b-a4b-it` | 95 | 86 | 84.9 | 94 | 84 | 82.8 |
| `openrouter_stealth_space-bunny-alpha` | 98 | 88 | 86.4 | 92 | 80 | 78.7 |
| `ollama_gemma4_26b-a4b-it-qat` | 96 | 86 | 85.3 | 95 | 81 | 84.2 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 90 | 83 | 82.8 | 87 | 78 | 76.6 |
| `google_gemini-3.5-flash-lite` | 85 | 81 | 80.4 | 86 | 77 | 76.1 |
| `ollama_qwen3.5_9b` | 91 | 78 | 78.7 | 77 | 73 | 71.6 |
| `openrouter_cohere_north-mini-code_free` | 90 | 83 | 81.8 | 74 | 67 | 67.3 |
| `ollama_gemma4_12b-it-qat` | 83 | 76 | 75.3 | 82 | 72 | 72.2 |
| `openrouter_poolside_laguna-s-2.1_free` | 87 | 80 | 80.8 | 71 | 63 | 64.2 |
| `ollama_qwen3.5_4b` | 79 | 72 | 69.8 | 72 | 67 | 65.5 |

Sorted by the Jev score summed over both languages.

- **The saturation is gone.** Under qwen, 24 of 39 models score ≥ 98 in English
  (15 at 100) and 16 in Japanese (8 at 100). Under Jev four reach 98 in
  English and none in Japanese, where the top is 97. The mean drop is 6.8
  points (en) and 8.5 (ja).
- **The order is broadly kept.** Spearman's rank correlation between the qwen
  and Jev scores is 0.92 (en) and 0.90 (ja); the weakest models stay at the
  bottom. Within the top, models that qwen could not separate spread out, and
  some move a long way — `openai_gpt-5.6-terra` and `openai_gpt-5.6-sol` score
  100 in Japanese under qwen but 89 and 90 under Jev, while
  `opencode_muse-spark-1.2/1.3`, also 100 under qwen, drop only to 96 and 97.

### Verdict transitions

Over all 41 runs per language (Ceiling and Hybrid8):

| qwen \ Jev | en correct | en partial | en incorrect | ja correct | ja partial | ja incorrect |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| correct | 1,646 | 283 | 0 | 1,505 | 353 | 0 |
| partial | 2 | 91 | 2 | 4 | 129 | 7 |
| incorrect | 0 | 10 | 16 | 0 | 10 | 42 |

As on `results-<lang>/`, the shift is almost entirely qwen *correct* → Jev
*partial*; Jev never turns a qwen *correct* into *incorrect*.

### Hybrid8

Under qwen the Hybrid k=8 context costs `ollama_qwen3.8` and
`openrouter_stealth_ox-alpha` at most 2 points over the gold chapters in
either language. Under Jev that holds only for `stealth_ox-alpha` (3 points in
English, 1 in Japanese); qwen3.8 loses 6 and 5, and Gemma 9 and 7
([README.md § Hybrid8 vs. ceiling](README.md#hybrid8-vs-ceiling-what-retrieval-costs)).

The grading of questions whose gold chapters are absent from the k=8 context
also differs. qwen split answers that name what they can and leave the rest
open between *partial* and *incorrect*: ja Q27 is *incorrect* for
`stealth_ox-alpha` but *partial* for Gemma and qwen3.8. Jev grades ja Q27
*partial* for all three, and every other missing-evidence question *partial*
or *correct* except ja Q42 for qwen3.8, which it grades *incorrect* where qwen
gives *partial*.
