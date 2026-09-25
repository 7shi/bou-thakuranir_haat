# Jev as the judge

An experiment in replacing the `judge.py` LLM judge (`ollama:qwen3.6`) with
TypeSafe's **Jev** (`jev-1.13.0`), a System One model that returns typed
answers with probabilities instead of generated text. The outcome is to
**grade with a single Choice question**; a production judge script is to be
derived from [judge-jev.py](judge-jev.py).

## Motivation

The qwen judge is lenient. In the multi-model Ceiling comparison
([results/report.md](../results/report.md)) many answerer models score 98–100
in both languages, so the top of the table no longer separates models. A
somewhat stricter judge is preferable, as long as the strictness is justified
by the gold answers rather than by style.

## Setup

[judge-jev.py](judge-jev.py) keeps `judge.py`'s grading contract: the judge
sees the question, the gold `answer` and `rationale`, and the candidate answer,
but not the chapter text, and the wording follows `judge.py`'s rubric. The
state is named JSON (`task`, `question`, `gold_answer`, `rationale`,
`candidate_answer`).

Two question shapes were compared, asked together in one request under
`--debug` (they cannot see each other's answers, and the state is billed once):

- **Choice** `verdict` over `correct` / `partial` / `incorrect`, with
  `judge.py`'s three definitions as the criteria. The verdict is the most
  probable option.
- **Noul** `correct` — "the candidate captures the essential facts of the gold
  answer". Only the poles are described (yes = `judge.py`'s *correct*, no =
  its *incorrect*), so that *partial* could be read off a middle band of the
  yes probability `p` with two thresholds: correct if `p ≥ hi`, partial if
  `lo ≤ p < hi`, incorrect otherwise.

`--debug` stores the raw API response per question; [analyze.py](analyze.py)
derives every table below from those logs and the qwen verdicts in the
matching `qa-eval` result directory.

Two English answer sets were judged:

| Set | Logs | Answers | Questions |
| --- | --- | --- | ---: |
| retrieval | [results-en/](results-en/) | `graphrag-local`, `filter2`, `vector-line5`, `graphrag-global` (chosen for a spread of qwen verdicts) | 200 |
| ceiling | [results/](results/) | Ceiling answers of six models, from saturated to mid-table | 300 |

## Results

### Jev is stricter than qwen, for reasons

On the retrieval set (weighted score = `(correct + 0.5·partial) / n`):

| Judge | c/p/i | Weighted | Agree w/ qwen | Agree w/ Choice |
| --- | --- | ---: | ---: | ---: |
| qwen | 103/35/62 | 60.2 | — | 169 |
| Choice | 79/61/60 | 54.8 | 169 | — |
| Noul 0.1/0.35 | 109/23/68 | 60.2 | 187 | 162 |
| Noul 0.1/0.6 | 91/41/68 | 55.8 | 181 | 180 |
| Noul 0.1/0.8 | 79/53/68 | 52.8 | 171 | 190 |

| qwen \ Choice | correct | partial | incorrect |
| --- | ---: | ---: | ---: |
| correct | 79 | 23 | 1 |
| partial | 0 | 33 | 2 |
| incorrect | 0 | 5 | 57 |

Noul thresholds can be fitted to qwen (best 0.1/0.37, 187/200; 183/200 when
each file's thresholds are fitted on the other three), but reproducing qwen is
not the goal. The disagreements are almost all qwen *correct* → Jev *partial*,
and reading them shows Jev catching real gaps:

- graphrag-global Q20: the candidate says it cannot answer; qwen graded it
  *correct* (Noul 0.01).
- filter2 Q49, Q36, Q46: two-part questions whose first half is missing (the
  rejected warnings, the youthful infatuation, the flirtatious loans).
- The verbose GraphRAG answers that stay vague or break off before the key
  facts (graphrag-local Q26, Q42; graphrag-global Q47).

### The Choice separates the top of the Ceiling table

Weighted score per answerer model on the ceiling set:

| Model | qwen | Choice | Noul 0.1/0.6 | Noul 0.1/0.8 | Mean Noul |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ollama_qwen3.8` | 100 | 96 | 100 | 98 | 0.929 |
| `openai_gpt-6-luna` | 100 | 96 | 99 | 95 | 0.904 |
| `openai_gpt-5.6-sol` | 100 | 93 | 100 | 92 | 0.915 |
| `ollama_qwen3.6` | 98 | 88 | 96 | 89 | 0.856 |
| `google_gemini-3.5-flash-lite` | 86 | 81 | 85 | 81 | 0.782 |
| `ollama_qwen3.5_9b` | 90 | 78 | 85 | 77 | 0.749 |

The Choice moves the three saturated models off 100 and widens the gap to
qwen3.6. The Noul needs its upper threshold near 0.8 to do the same; at 0.6
the top stays at 99–100.

The Choice's *partial* verdicts on the two OpenAI models (11 in all) are mostly
answers that address the question but omit a supporting fact the gold answer
carries — e.g. Q29 omits that the maid Matangini engaged the poisoner, Q30 that
Vibha arrives on the wedding day, Q42 the forged petition. That is a strict but
defensible reading of "misses key facts"; the margins are mostly narrow
(P(correct) 0.18–0.46), the exception being gpt-6-luna Q34 (0.01).

### A Noul at 0.8 reproduces the Choice

| Set | Noul 0.1/0.8 vs Choice | Best | Best thresholds |
| --- | ---: | ---: | --- |
| retrieval | 190/200 | 199/200 | 0.05/0.79 |
| ceiling | 292/300 | 292/300 | 0.13/0.8 |

Noul yes probability by Choice verdict (min / median / max):

| Choice | retrieval | ceiling |
| --- | --- | --- |
| correct | 0.79 / 0.98 / 0.99 | 0.73 / 0.98 / 0.99 |
| partial | 0.05 / 0.34 / 0.83 | 0.08 / 0.65 / 0.84 |
| incorrect | 0.01 / 0.01 / 0.04 | 0.01 / 0.01 / 0.09 |

Fitted independently, both sets put the upper threshold at 0.79–0.80: Jev
draws the Choice's correct/partial boundary where the Noul's yes probability
is about 0.8. The two shapes carry the same judgment, and only the region
0.73–0.84 overlaps.

### Token usage

Per request, with the Choice and the Noul together:

| Set | Requests | Input total | Input / request | Output / request |
| --- | ---: | ---: | ---: | ---: |
| retrieval | 200 | 170,089 | 850 | 56 |
| ceiling | 300 | 237,183 | 791 | 56 |

Input is dominated by the candidate answer (graphrag-local averages 1,041);
output is fixed at 56 regardless of content. The Choice alone takes 39 output
tokens ([../JEV.md](../JEV.md#cost)), so the Noul accounts for 17.

The experiment ran as five `judge-jev.py --debug` calls, each logged once in
llm7shi's `usage.jsonl`. The last two grade Q7 and Q28, whose rows the first
three no longer hold:

| Run | Requests | Input | Output |
| --- | ---: | ---: | ---: |
| retrieval, first 3 questions of graphrag-local (`-n 3` trial) | 3 | 2,479 | 168 |
| retrieval, the remaining questions of the four files | 197 | 166,946 | 11,032 |
| ceiling, six models | 300 | 236,187 | 16,800 |
| retrieval, Q7 and Q28 of the four files | 8 | 6,947 | 448 |
| ceiling, Q7 and Q28 of the six models | 12 | 9,998 | 672 |
| Total | 520 | 422,557 | 29,120 |

Billed $0.017 for the first 500 requests, about $0.034 per 1,000; the last 20
add about $0.001 at the same rate.

## Decision

Grade with the **Choice** only. It gives the needed strictness without a
threshold to choose, and the Noul adds nothing a threshold of 0.8 does not
already reproduce. The production script derived from `judge-jev.py` drops
the Noul and `--debug`.

## Files

- [judge-jev.py](judge-jev.py) — the experiment's judge. Normal mode asks the
  Choice and writes `judge-jev-<stem>.jsonl`; `--debug` asks the Choice and the
  Noul and writes the raw responses to `jev-<stem>.jsonl`. Output goes under
  this directory, in a subdirectory named after the input's directory.
  Requires `TYPESAFE_API_KEY`.
- [analyze.py](analyze.py) — prints the tables above from the logs.
- [results-en/](results-en/), [results/](results/) — `--debug` logs.

Reproduce (from `qa-eval/`):

```
uv run python jev/judge-jev.py --debug results-en/graphrag-local.jsonl results-en/filter2.jsonl results-en/vector-line5.jsonl results-en/graphrag-global.jsonl
uv run python jev/judge-jev.py --debug results/ceiling-openai_gpt-6-luna-en.jsonl results/ceiling-openai_gpt-5.6-sol-en.jsonl results/ceiling-ollama_qwen3.8-en.jsonl results/ceiling-ollama_qwen3.6-en.jsonl results/ceiling-google_gemini-3.5-flash-lite-en.jsonl results/ceiling-ollama_qwen3.5_9b-en.jsonl
python3 jev/analyze.py
```
