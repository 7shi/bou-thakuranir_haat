# Qwen (`ollama:qwen3.6`)

The original judge of qa-eval, replaced by Jev (`jev-1.14.0`) as the default
and now frozen ([README.md](README.md)). Its verdicts stay in `judge/` beside
each answer directory and are not run on new answer files or re-graded after a
gold answer fix.

## Setup

- **Judge**: [judge.py](../judge.py), `ollama:qwen3.6` through llm7shi with a
  structured output of a one-sentence `reason` followed by the `verdict`
  (`correct` / `partial` / `incorrect`). The reason comes first so that the
  verdict follows from it; a reason under 20 characters is retried up to 3
  times.
- **Inputs**: question, gold `answer` and `rationale`, candidate answer; no
  chapter source text.
- **Output**: `results-<lang>/judge/<method>.jsonl` and `results/judge/*.jsonl`,
  one record per question.
- **Aggregation**: `uv run report.py -l <lang>` (no flag) for
  `results-<lang>/`, and `uv run results/report.py` for the per-model runs,
  written to [results/judge/report.md](../results/judge/report.md) with the
  chart [results/judge/MODELS.svg](../results/judge/MODELS.svg).

## Results under Qwen

50 questions per language. `correct`/50 with the weighted score
`(correct + 0.5·partial) / 50` in parentheses.

| Method | English | Japanese |
| --- | --- | --- |
| Vector k=5 | 38/50 (0.820) | 37/50 (0.800) |
| Vector k=10 | 44/50 (0.920) | 43/50 (0.900) |
| Vector-line k=5 | 33/50 (0.770) | 34/50 (0.790) |
| Vector-line k=10 | 38/50 (0.850) | 41/50 (0.860) |
| V-hybrid k=5 | 39/50 (0.870) | 42/50 (0.890) |
| V-hybrid k=10 | 44/50 (0.930) | 43/50 (0.900) |
| Hybrid k=5 | 40/50 (0.880) | 45/50 (0.930) |
| Hybrid k=8 | 44/50 (0.920) | 43/50 (0.920) |
| Hybrid k=10 | 48/50 (0.980) | 42/50 (0.910) |
| Extract | 40/50 (0.860) | 41/50 (0.870) |
| Filter2 | 37/50 (0.800) | 38/50 (0.820) |
| Filter3 | 45/50 (0.930) | 41/50 (0.870) |
| Ceiling | 49/50 (0.990) | 49/50 (0.990) |
| GraphRAG local | 24/50 (0.610) | 26/50 (0.630) |
| GraphRAG global | 3/50 (0.170) | 6/50 (0.190) |

What these verdicts showed:

- **Practical optimum by language**: Dense ∪ BM25 Union is the best practical
  method in both languages, but at different depths: `Hybrid k=10` in English
  (0.980) and `Hybrid k=5` in Japanese (0.930).
- **Depth differs by language**: in English, Hybrid rises with depth, from
  40/50 (0.880) at `k=5` through 44/50 (0.920) at `k=8` to 48/50 (0.980) at
  `k=10`. In Japanese it does not: `k=5` scores 45/50 (0.930), `k=8` 43/50
  (0.920) and `k=10` 42/50 (0.910), as the larger contexts lose cross
  questions to partial answers (Q34, Q37, Q47, Q50 at `k=10`) although they
  keep every gold chapter.
- **Ceiling near-perfect**: 0.990 in both languages; the two remaining losses
  are completeness gaps on multi-part cross questions (en Q48, ja Q36).
- **Language invariance**: most methods land within 2 questions of each other
  across English and Japanese; the widest gap is 6 (Hybrid k=10).

## Why it was replaced

- **Lenient at the top**: over the 63 answerer models in `results/`, 13 score
  100% on Ceiling in both languages, so the frontier models are not separated
  (mean Ceiling score 94.9%, against Jev's 87.8%).
- **The stricter judges agree with one another**: Jev, OpenAI and Ternary
  correlate at $r$ 0.96–0.97 on the per-model Ceiling scores, Qwen at
  0.92–0.93 with them. Where Jev marks *partial* what Qwen
  marks *correct*, the answer mostly misses part of a multi-part gold answer
  ([JEV.md](JEV.md)).

The introduction of Jev is described in [jev/README.md](../jev/README.md) and
[JEV.md](JEV.md), and the comparison of all seven judges in
[README.md](README.md).
