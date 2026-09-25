# Jev grading of the per-model runs

Every answer file in this directory was graded with Jev by one
`make judge-jev` run (see [Makefile](Makefile)), writing `jev/*.tsv`. Why Jev,
and how its verdicts compare with the qwen judge on `results-<lang>/`:
[../JEV.md](../JEV.md).

## Run

- Judge: [judge-jev.py](../judge-jev.py), `jev-1.13.0`, scheme `choice@19579e23`
  (recorded for all 82 files in `jev/MODELS.tsv`)
- Scope: 82 answer files (41 per language) × 50 questions = 4,100 requests,
  one `judge-jev.py` call per language
- Wall time: 15m 7.5s (about 0.22 s per request)
- Cost: $0.1385 in total (about $0.034 per 1,000 requests)

Token usage, from llm7shi's `usage.jsonl` (one entry per language):

| Language | Requests | Input | Output | Input / request | Output / request |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 2,050 | 1,411,013 | 79,950 | 688 | 39 |
| Japanese | 2,050 | 1,887,319 | 79,950 | 921 | 39 |
| Total | 4,100 | 3,298,332 | 159,900 | 804 | 39 |

Output is a fixed 39 tokens per request regardless of content. Input follows
the length of the question, gold answer, rationale and candidate answer;
Japanese needs about 1.34× the tokens of English for the same material.

## Comparison with qwen

`make report-jev` aggregates the Jev verdicts into [report-jev.md](report-jev.md)
and [MODELS-jev.svg](MODELS-jev.svg), beside the qwen [report.md](report.md) and
[MODELS.svg](MODELS.svg). As in `report-jev.md`, each question counts as its most
probable verdict (the stricter one on a tie), and scores are
`(correct + 0.5·partial) / 50` in percent. **E** is the same score over the
probabilities, mean of P(correct) + 0.5·P(partial), which also separates models
that tie on verdicts.

### Ceiling

| Model | en qwen | en Jev | en E | ja qwen | ja Jev | ja E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `opencode_muse-spark-1.3-contributor-free` | 100 | 97 | 94.1 | 100 | 96 | 92.6 |
| `opencode_muse-spark-1.2-contributor-free` | 98 | 96 | 93.5 | 100 | 96 | 93.8 |
| `openrouter_stealth_ox-alpha` | 98 | 95 | 94.3 | 100 | 96 | 92.1 |
| `opencode_union-alpha` | 100 | 95 | 93.8 | 100 | 93 | 89.5 |
| `openrouter_minimax_minimax-m3_free` | 98 | 95 | 91.2 | 99 | 93 | 89.7 |
| `ollama_qwen3.8` | 100 | 96 | 93.8 | 99 | 91 | 89.0 |
| `copilot_grok-4.5` | 100 | 94 | 91.6 | 99 | 93 | 90.9 |
| `ollama_muse-glimmer` | 99 | 94 | 90.2 | 97 | 93 | 89.6 |
| `copilot_kimi-k2.7-code` | 99 | 94 | 92.1 | 99 | 91 | 88.8 |
| `openai_gpt-5.6-sol` | 100 | 93 | 91.4 | 100 | 92 | 89.3 |
| `google_gemini-3-flash-preview` | 100 | 94 | 91.3 | 98 | 91 | 88.8 |
| `openrouter_nvidia_nemotron-3-ultra-550b-a55b_free` | 99 | 92 | 90.4 | 97 | 93 | 89.1 |
| `openai_gpt-6-luna` | 100 | 95 | 90.8 | 100 | 89 | 87.5 |
| `openai_gpt-5.6-luna` | 100 | 94 | 91.0 | 97 | 90 | 86.8 |
| `opencode_mimo-v2.6-flash-free` | 100 | 96 | 93.6 | 95 | 87 | 85.0 |
| `openai_gpt-5.6-terra` | 96 | 92 | 89.9 | 99 | 91 | 88.7 |
| `opencode_mimo-v2.5-free` | 100 | 93 | 90.5 | 96 | 88 | 85.1 |
| `google_gemini-3.8-flash` | 98 | 91 | 88.5 | 97 | 88 | 87.0 |
| `copilot_gpt-5.6-luna` | 99 | 91 | 89.2 | 98 | 88 | 85.7 |
| `llama.cpp_Ternary-Bonsai-2-27B-PTQ1_0` | 99 | 90 | 88.8 | 96 | 86 | 85.5 |
| `opencode_big-pickle` | 97 | 88 | 87.0 | 97 | 88 | 85.8 |
| `copilot_claude-haiku-4.5` | 98 | 90 | 88.8 | 98 | 85 | 84.3 |
| `ollama_qwen3.6` | 98 | 88 | 86.7 | 97 | 86 | 84.3 |
| `google_gemini-2.5-flash` | 94 | 88 | 86.0 | 96 | 85 | 85.7 |
| `openrouter_minimax_minimax-m2.7_free` | 95 | 87 | 87.1 | 97 | 86 | 84.5 |
| `google_gemini-3.7-flash` | 97 | 87 | 86.7 | 98 | 85 | 86.2 |
| `openrouter_nvidia_nemotron-3-super-120b-a12b_free` | 94 | 87 | 85.9 | 90 | 84 | 84.4 |
| `openrouter_inclusionai_ling-3.0-flash-fin_free` | 97 | 88 | 86.4 | 95 | 82 | 83.8 |
| `copilot_mai-code-1.1-flash` | 97 | 88 | 86.3 | 93 | 82 | 80.6 |
| `openrouter_stealth_space-bunny-alpha` | 97 | 90 | 87.4 | 93 | 80 | 78.7 |
| `ollama_gemma4_26b-a4b-it-qat` | 95 | 87 | 85.0 | 92 | 82 | 83.2 |
| `google_gemma-4-26b-a4b-it` | 95 | 85 | 84.3 | 94 | 81 | 82.1 |
| `openrouter_nvidia_nemotron-3.5-lightning_free` | 93 | 84 | 83.2 | 86 | 79 | 77.1 |
| `google_gemini-3.5-flash-lite` | 86 | 81 | 79.4 | 86 | 79 | 77.1 |
| `openrouter_cohere_north-mini-code_free` | 92 | 85 | 83.5 | 73 | 67 | 68.1 |
| `ollama_qwen3.5_9b` | 90 | 78 | 79.3 | 78 | 73 | 71.7 |
| `ollama_gemma4_12b-it-qat` | 84 | 78 | 76.1 | 83 | 72 | 72.8 |
| `openrouter_poolside_laguna-s-2.1_free` | 89 | 78 | 80.5 | 72 | 63 | 64.4 |
| `ollama_qwen3.5_4b` | 81 | 72 | 70.3 | 71 | 66 | 65.9 |

Sorted by the Jev score summed over both languages.

- **The ceiling is gone.** Under qwen, 21 of 39 models score ≥ 98 in English
  (10 at 100) and 15 in Japanese (6 at 100). Under Jev none reaches 98; the top
  is 97 (en) / 96 (ja). The mean drop is 6.8 points (en) and 8.3 (ja).
- **The order is broadly kept.** Spearman's rank correlation between the qwen
  and Jev scores is 0.88 (en) and 0.90 (ja); the weakest models stay at the
  bottom. Within the top, models that qwen could not separate spread out, and
  some move a long way — `openai_gpt-6-luna` and `openai_gpt-5.6-sol` score 100
  in Japanese under qwen but 89 and 92 under Jev, while
  `opencode_muse-spark-1.2/1.3` and `openrouter_stealth_ox-alpha`, also 100
  under qwen, drop only to 96.
- **The top is still compressed.** The 15 best English models lie within 93–97,
  and one question moves a score by 1 point (correct ↔ partial) or 2 (correct ↔
  incorrect), so neighbours there differ by one or two questions, within the
  grading noise. E, which does not round each question to a verdict, is the
  finer tiebreaker.
- **Almost every loss is a cross question.** Of the non-correct verdicts across
  the 39 Ceiling runs, 363 of 394 (en) and 501 of 526 (ja) are on cross
  questions. The most frequent are en Q42 (32 of 39 models) and ja Q46 (34 of
  39).

Verdict transitions over all 41 runs per language (Ceiling and Hybrid8):

| qwen \ Jev | en correct | en partial | en incorrect | ja correct | ja partial | ja incorrect |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| correct | 1,644 | 282 | 0 | 1,504 | 346 | 0 |
| partial | 1 | 92 | 3 | 6 | 137 | 5 |
| incorrect | 0 | 11 | 17 | 0 | 12 | 40 |

As on `results-<lang>/`, the shift is almost entirely qwen *correct* → Jev
*partial*; Jev never turns a qwen *correct* into *incorrect*.

### Hybrid8 vs. Ceiling

| Model | Lang | Ceiling qwen | Ceiling Jev | Hybrid8 qwen | Hybrid8 Jev |
| --- | --- | ---: | ---: | ---: | ---: |
| `openrouter_stealth_ox-alpha` | en | 98 | 95 | 97 | 95 |
| `openrouter_stealth_ox-alpha` | ja | 100 | 96 | 98 | 95 |
| `ollama_qwen3.8` | en | 100 | 96 | 99 | 94 |
| `ollama_qwen3.8` | ja | 99 | 91 | 95 | 90 |

Under Jev, Hybrid8 stays within 2 points (one question) of Ceiling for both
models in both languages, and ox-alpha en is level, so the
qwen-era reading that the Hybrid k=8 context costs these answerers little over
the gold chapters still holds.
