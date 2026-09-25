# Per-model answerer runs

This directory holds runs with **answerer models other than the default**
`google:gemma-4-31b-it`, without touching the canonical `results-<lang>/`
trees — the existing per-strategy results stay as they are, and each new
(method, model, language) triple gets its own file here.

Two methods are available:

- **hybrid8** — Hybrid k=8 (dense ∪ BM25 union; [HYBRID.md](../HYBRID.md))
  context, **replayed** from the canonical `results-<lang>/hybrid8.jsonl` via
  `answer_hybrid.py --retrieval` rather than recomputed. Retrieval is supposed to
  be model-independent, but the dense side embeds the question at run time and
  that is not bit-stable across ollama backends — ROCm vs Vulkan moves cosines in
  the 4th decimal, enough to swap a chapter sitting near the top-8 cutoff (see
  [MEMO.md](../MEMO.md)). Replaying pins `hits` and `expanded`, so every model
  here answers a byte-identical context and only the answer is generated.
- **ceiling** — no retrieval at all: the gold chapters as context
  (`answer_ceiling.py`). This is the cleaner model comparison: the context is
  fixed by the gold annotation, so it is byte-identical for every model and
  every run with nothing to pin, and the whole difference is synthesis. It is
  also much smaller than a hybrid8 context, hence cheaper and faster per
  question.

Filenames encode the method, model and language so multiple experiments coexist
("`:`" and "`/`" in the model string are replaced by "`_`"):

- `<METHOD>-<MODEL>-<LANG>.jsonl` — answers, e.g.
  `hybrid8-google_gemini-4-31b-it-ja.jsonl`
- `judge/<METHOD>-<MODEL>-<LANG>.jsonl` — verdicts (`judge.py`, opt-in)
- `jev/<METHOD>-<MODEL>-<LANG>.tsv` — Jev probabilities (`judge-jev.py`,
  opt-in; see [JEV.md](../JEV.md)), with `jev/MODELS.tsv` recording the Jev
  version and scheme per file; the run's cost and time are in
  [JEV.md](JEV.md)

The method leads so runs group by method, and the language trails so it can be
read straight off the filename — the model is the only field that may itself
contain "`-`".

The scores in this README are **Jev** verdicts, each question counting as its
most probable verdict, aggregated by `report.py --jev` into
[report-jev.md](report-jev.md). The `ollama:qwen3.6` verdicts, the judge of the
main table in [README.md](../README.md), stay in `judge/` and are aggregated
into [report.md](report.md). How this directory switched from qwen to Jev —
the introduction experiment, the grading run, and a per-model comparison of
the two judges with the expected score E computed from the Jev probabilities
— is recorded in [JEV.md](JEV.md).

## Usage

Run via [Makefile](Makefile) (the directory's default target prints the usage
line):

```
make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions → hybrid8-<MODEL>-<LANG>.jsonl
make ceiling MODEL=... LANG={en,ja}   # answer 50 questions → ceiling-<MODEL>-<LANG>.jsonl
make test    MODEL=... LANG={en,ja}   # answer question 1 only, both methods, no file output
make judge                            # opt-in: grade every ungraded answer file
make judge-jev                        # opt-in: the same with Jev → jev/*.tsv
make report                           # aggregate every judged run → report.md
make report-jev                       # aggregate jev/*.tsv → report-jev.md
```

- `MODEL` — llm7shi model string of the answerer (e.g.
  `google:gemini-4-31b-it`, `ollama:gemma4:31b-it-qat`)
- `LANG` — `en` | `ja` (selects the questions file and, for hybrid8, the
  reference run whose retrieval is replayed)

`make test` is a smoke test, not a data run: it answers question 1 under both
methods and writes to `/dev/null`, so it leaves nothing in `results/` — useful
for checking a model/backend combination (e.g. the ROCm issue below) without
polluting the directory with a throwaway file to clean up afterward.

`make judge` needs neither: it scans this directory for answer files that have
no `judge/` counterpart yet and reads the language off each filename.
`make judge-jev` does the same against `jev/`, passing the pending files to one
`judge-jev.py` call per language.

Example:

```
make ceiling MODEL=google:gemini-4-31b-it LANG=ja
```

## Ceiling: comparing answerer models

`ceiling` puts the gold chapters in the context and nothing else, so the context
is byte-identical for every model and every run, with nothing to pin. Retrieval
is not a variable at all here and the whole difference is **synthesis**, which
is what makes this the comparison worth growing: one more model costs 100
questions and no index.

Rows are grouped by provider, and within the same model series, ordered
roughly by performance (not a strict mechanical sort on any single column).

| Model | English | Japanese |
| --- | --- | --- |
| `copilot:grok-4.5` | 94 (44/6/0) | 93 (43/7/0) |
| `copilot:kimi-k2.7-code` | 94 (45/4/1) | 91 (41/9/0) |
| `copilot:gpt-5.6-luna` | 91 (41/9/0) | 88 (39/10/1) |
| `copilot:claude-haiku-4.5` | 90 (40/10/0) | 85 (35/15/0) |
| `copilot:mai-code-1.1-flash` | 88 (38/12/0) | 82 (33/16/1) |
| `google:gemini-3-flash-preview` | 94 (44/6/0) | 91 (41/9/0) |
| `google:gemini-3.8-flash` | 91 (42/7/1) | 88 (39/10/1) |
| `google:gemini-2.5-flash` | 88 (39/10/1) | 85 (35/15/0) |
| `google:gemini-3.7-flash` | 87 (38/11/1) | 85 (36/13/1) |
| `google:gemini-3.5-flash-lite` | 81 (35/11/4) | 79 (33/13/4) |
| `google:gemma-4-31b-it` | 97 (47/3/0) | 92 (42/8/0) |
| `ollama:gemma4:26b-a4b-it-qat` | 87 (38/11/1) | 82 (32/18/0) |
| `google:gemma-4-26b-a4b-it` | 85 (36/13/1) | 81 (32/17/1) |
| `ollama:gemma4:12b-it-qat` | 78 (32/14/4) | 72 (27/18/5) |
| `ollama:qwen3.8` (27B) | 96 (46/4/0) | 91 (42/7/1) |
| `ollama:qwen3.6` (35B-A3B) | 88 (38/12/0) | 86 (36/14/0) |
| `ollama:qwen3.5:9b` | 78 (29/20/1) | 73 (26/21/3) |
| `ollama:qwen3.5:4b` | 72 (24/24/2) | 66 (23/20/7) |
| `ollama:muse-glimmer` (30B) | 94 (44/6/0) | 93 (43/7/0) |
| `llama.cpp:Ternary-Bonsai-2-27B-PTQ1_0` | 90 (40/10/0) | 86 (36/14/0) |
| `openai:gpt-5.6-sol` | 93 (43/7/0) | 92 (42/8/0) |
| `openai:gpt-6-luna` | 95 (45/5/0) | 89 (39/11/0) |
| `openai:gpt-5.6-luna` | 94 (44/6/0) | 90 (40/10/0) |
| `openai:gpt-5.6-terra` | 92 (42/8/0) | 91 (41/9/0) |
| `opencode:muse-spark-1.3-contributor-free` | 97 (47/3/0) | 96 (46/4/0) |
| `opencode:muse-spark-1.2-contributor-free` | 96 (46/4/0) | 96 (46/4/0) |
| `opencode:union-alpha` | 95 (45/5/0) | 93 (43/7/0) |
| `opencode:mimo-v2.6-flash-free` | 96 (46/4/0) | 87 (39/9/2) |
| `opencode:mimo-v2.5-free` | 93 (43/7/0) | 88 (39/10/1) |
| `opencode:big-pickle` | 88 (38/12/0) | 88 (38/12/0) |
| `openrouter:stealth/ox-alpha` (320B-A18B) | 95 (45/5/0) | 96 (46/4/0) |
| `openrouter:stealth/space-bunny-alpha` | 90 (40/10/0) | 80 (30/20/0) |
| `openrouter:poolside/laguna-s-2.1:free` | 78 (29/20/1) | 63 (20/23/7) |
| `openrouter:cohere/north-mini-code:free` | 85 (36/13/1) | 67 (23/21/6) |
| `openrouter:inclusionai/ling-3.0-flash-fin:free` | 88 (39/10/1) | 82 (33/16/1) |
| `openrouter:minimax/minimax-m3:free` | 95 (45/5/0) | 93 (43/7/0) |
| `openrouter:minimax/minimax-m2.7:free` | 87 (37/13/0) | 86 (36/14/0) |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | 92 (42/8/0) | 93 (43/7/0) |
| `openrouter:nvidia/nemotron-3-super-120b-a12b:free` | 87 (37/13/0) | 84 (34/16/0) |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 84 (34/16/0) | 79 (31/17/2) |

(Weighted score `(correct + 0.5×partial) / n`, as an integer percentage rounded
down, then correct/partial/incorrect out of 50 in parentheses. The
`gemma-4-31b-it` row is the canonical `results-<lang>/ceiling.jsonl` run,
graded in `results-<lang>/jev/ceiling.tsv`; the other rows live in this
directory and are aggregated in [report-jev.md](report-jev.md).
The `opencode:*` rows are produced by a separate pipeline that drives the
`opencode` coding-agent CLI instead of the llm7shi-based `answer_ceiling.py`
used for every other row — see [opencode/README.md](../opencode/README.md).)

* **No model is perfect, and the top is compressed.** The best scores are 97
  in English (`muse-spark-1.3-contributor-free` and the default
  `gemma-4-31b-it`) and 96 in Japanese (`muse-spark-1.2/1.3-contributor-free`
  and `stealth/ox-alpha`). The 15 best English models lie within 93–97, and one
  question moves a score by 1 point (correct ↔ partial) or 2 (correct ↔
  incorrect), so neighbours there differ by one or two questions, within the
  grading noise. [JEV.md](JEV.md)'s expected score E is the finer tiebreaker.
* **The floor sits far below.** English goes down to 72 (`qwen3.5:4b`) and
  Japanese to 63 (`poolside/laguna-s-2.1:free`), even with the gold chapters
  supplied. Almost every loss is a partial on a multi-chapter `cross` question
  (26–50): the answer covers some of the gold's elements and misses others.
* **Japanese costs almost every model.** 36 of the 40 models score lower in
  Japanese; `nemotron-3-ultra` and `stealth/ox-alpha` score 1 point higher,
  and `big-pickle` and `muse-spark-1.2-contributor-free` score the same in both.
  The largest English-to-Japanese gaps are `cohere/north-mini-code:free`'s 18
  points and `poolside/laguna-s-2.1:free`'s 15.
* **`llama.cpp:Ternary-Bonsai-2-27B-PTQ1_0` is a ternary ({-1, 0, +1})
  quantization of Qwen 3.8 27B, not an independent model.** Its
  publisher claims 98.2% performance retention against the full-precision
  base at a 9x smaller footprint (5.9 GB). Here it scores 90/86 against
  qwen3.8's 96/91, about 94% of the base in both languages, somewhat below
  that claim.
* **Three models needed `NO_THINK=1` to produce a usable ceiling run.**
  `ollama:gemma4:12b-it-qat` stays on task in English without it (the English
  row above), but in Japanese its thinking trace sometimes loses track of the
  context and produces no usable answer, so the Japanese row is a
  `NO_THINK=1` run. `ollama:qwen3.5:9b` is worse: with thinking enabled its CoT
  falls into a loop and never terminates, so both rows above are `NO_THINK=1`
  runs. `ollama:qwen3.5:4b` was presumed even less stable and was only run with
  `NO_THINK=1`.

## Hybrid8 vs. ceiling: what retrieval costs

The models run under both methods — the default `google:gemma-4-31b-it`,
`ollama:qwen3.8`, and `openrouter:stealth/ox-alpha` — each read
**byte-identical contexts** under each method. The Gemma numbers
are the canonical `results-<lang>/{hybrid8,ceiling}.jsonl` runs; the qwen3.8
and `stealth/ox-alpha` hybrid8 runs replay `hits` and `expanded` straight from
`results-<lang>/hybrid8.jsonl`. So retrieval is not a variable *between the
models* either, and the ceiling → hybrid8 step is the price of answering from
a k=8 retrieved context instead of the gold one.

| Model | Method | English | Japanese |
| --- | --- | --- | --- |
| `google:gemma-4-31b-it` | ceiling | 97 (47/3/0) | 92 (42/8/0) |
| `google:gemma-4-31b-it` | hybrid8 | 87 (39/9/2) | 86 (37/12/1) |
| `ollama:qwen3.8` | ceiling | 96 (46/4/0) | 91 (42/7/1) |
| `ollama:qwen3.8` | hybrid8 | 94 (44/6/0) | 90 (41/8/1) |
| `openrouter:stealth/ox-alpha` | ceiling | 95 (45/5/0) | 96 (46/4/0) |
| `openrouter:stealth/ox-alpha` | hybrid8 | 95 (45/5/0) | 95 (45/5/0) |

- **qwen3.8 and `stealth/ox-alpha` pay almost nothing for retrieval.** In
  English qwen3.8 drops 0.020 (0.960 → 0.940) and `stealth/ox-alpha` not at
  all (0.950 → 0.950), even though the hybrid8 context misses gold chapters on
  5 of 50 questions; in Japanese both drop 0.010 (qwen3.8 0.910 → 0.900,
  `stealth/ox-alpha` 0.960 → 0.950).
- **Gemma pays the most in both languages.** It drops 0.100 in English
  (0.970 → 0.870) and 0.060 in Japanese (0.920 → 0.860), falling from the top
  of the three at ceiling in English to the bottom at hybrid8.
- **Small differences are within the noise.** Individual verdicts flip in both
  directions between the two methods: for qwen3.8 in Japanese, 6 questions get
  worse at hybrid8 and 5 get better, for a net change of one point. Only
  Gemma's drop (9 worse and 1 better in English, 7 and 1 in Japanese) is
  clearly beyond that.

### Hybrid8: every question any model missed

Includes every question graded `partial`/`incorrect` by any of the three
models, plus every question with a gold chapter absent from the k=8 context
even when all three models still answered correctly — a mechanical
retrieval-failure check independent of the judge verdicts. Table shows only
where things went wrong: `correct` verdicts are blanked to `-` so `partial`/
`incorrect` stand out; "missing" lists the gold chapter(s) not among the k=8
expanded hits.

| Lang | Q | type | Gemma 4 | qwen3.8 | ox-alpha | missing |
| --- | --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | - | - | — |
| en | 22 | single | - | partial | partial | — |
| en | 29 | cross | incorrect | - | - | — |
| en | 30 | cross | partial | - | - | — |
| en | **31** | cross | partial | partial | partial | **Ch22** |
| en | **32** | cross | partial | partial | partial | **Ch15** |
| en | 36 | cross | partial | partial | - | — |
| en | 37 | cross | partial | partial | - | — |
| en | **38** | cross | - | - | - | **Ch32** |
| en | **42** | cross | partial | - | - | **Ch23** |
| en | 46 | cross | partial | - | partial | — |
| en | 48 | cross | partial | - | - | — |
| en | **50** | cross | partial | partial | partial | **Ch23** |
| ja | **27** | cross | partial | partial | partial | **Ch33** |
| ja | 29 | cross | incorrect | incorrect | - | — |
| ja | 30 | cross | partial | partial | - | — |
| ja | 31 | cross | partial | - | - | — |
| ja | **32** | cross | partial | partial | partial | **Ch15** |
| ja | 34 | cross | partial | - | partial | — |
| ja | 35 | cross | partial | partial | - | — |
| ja | 36 | cross | partial | partial | partial | — |
| ja | 41 | cross | partial | - | - | — |
| ja | **42** | cross | - | partial | partial | **Ch23, Ch29** |
| ja | 43 | cross | partial | - | - | — |
| ja | 46 | cross | partial | partial | - | — |
| ja | 47 | cross | partial | partial | - | — |
| ja | 48 | cross | partial | - | - | — |

* **Cross-reference synthesis dominates the table.** Every row but two is
  `cross`; the `single` questions are en Q17, one of Gemma's misses, and en
  Q22, a partial for qwen3.8 and `stealth/ox-alpha`.
* **Eight rows are shared blind spots — gold chapters absent from the k=8
  context:** en Q31, en Q32, en Q38, en Q42, ja Q32, and ja Q42 (all six
  documented in
  [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots) — four for
  English at `k≤10`, two for Japanese), plus en Q50 and ja Q27 (the same
  failure mode at k=8, not among HYBRID.md's `k≤10` blind spots). Most of
  these are graded `partial` for all three models, and none is `incorrect`.
  The `correct` verdicts left there (en Q38 for all three, en Q42 for qwen3.8
  and `stealth/ox-alpha`, ja Q42 for Gemma) reflect prior knowledge or a
  lenient verdict, not reading comprehension. Restricting to the questions
  whose gold chapters are actually present — English n=45, Japanese n=47 —
  each model's correct/partial/incorrect becomes: Gemma 38/5/2 (en), 36/10/1
  (ja); qwen3.8 42/3/0 (en), 41/5/1 (ja); `stealth/ox-alpha` 43/2/0 (en),
  45/2/0 (ja). On the evidence actually supplied, `stealth/ox-alpha` scores
  0.978 (en) and 0.979 (ja), qwen3.8 0.967 and 0.926, and Gemma trails at
  0.900 and 0.872.
* **Most of the remaining rows are Gemma's partials on cross questions whose
  gold chapters are present**, the same incompleteness that drives the
  ceiling scores, made more frequent by the larger context.
* **Long-context distraction shows up on ja Q29.** Its gold chapters are in the
  k=8 context, yet at hybrid8 both Gemma and qwen3.8 answer it with an
  unrelated subplot (Surma's secret payments to the families of Sitaram and
  Bhagavat) and are graded `incorrect`. Gemma is `partial` there at ceiling;
  qwen3.8 is already `incorrect` at ceiling, where it gives the official order
  instead of the secret action. `stealth/ox-alpha` answers it correctly under
  both methods.

## Prompt ordering: the ROCm red herring

An early `ollama:qwen3.6` hybrid8 run appeared to lose the question entirely:
instead of answering, the model replied to the context as if it were a pasted
excerpt. The obvious reading was weak long-range attention over the ~10-24k
token hybrid8 context, so `answer_question` was restructured to send
`[context, preamble, question]` as separate parts — the RAG convention of
putting the question last, next to the answer position.

That diagnosis was wrong. The failure is specific to the **ROCm** backend; with
the **Vulkan** backend the original single merged prompt (question first,
context after) answers correctly on the same model and the same contexts. The
restructuring is therefore reverted, for two reasons beyond it being
unnecessary:

1. **Question-first is itself the more interesting test.** Putting the question
   last makes it harder to lose, which is precisely why it hides the failure
   mode worth measuring here — whether a model loses the *beginning* of a long
   prompt.
2. **Changing the prompt invalidates the existing answers.** Every result in
   `results-<lang>/` and in this directory was produced with the question-first
   prompt; a prompt change should come with a full re-run, not a silent mix of
   two prompt shapes in one table.

So the prompt shape stays as originally written, and backend choice — not
prompt engineering — is what to check when a local model appears to ignore the
question.

## Notes

- Both scripts are **resume-safe**: they append and skip question IDs already
  present in the output file, so an interrupted run is continued by re-running
  the same command.
- **Neither method needs the embedding index.** hybrid8 replays a stored
  retrieval and ceiling does none, so no run here loads
  `qa-eval/index-<lang>.safetensors`, builds a BM25 index, or calls the
  embedding model. The reference run `results-<lang>/hybrid8.jsonl` must exist;
  it is produced by the parent Makefile, not by this one.
- The replay resolves the reference `expanded` list against
  `all/<lang>-gemini.jsonl` and asserts every scene is found, so a reference run
  built on a different scene set fails loudly instead of silently answering a
  different context.
- The parent `report.py` does not scan this directory (its method discovery
  reads only `results-<lang>/hybrid<k>.jsonl`), so these runs never leak into
  the main table. `make report` here is the independent aggregation: it reuses
  the parent's `accuracy` / `retrieval` helpers but simply tallies every
  `judge/*.jsonl` present in this directory and writes `report.md`;
  `make report-jev` does the same over `jev/*.tsv` and writes `report-jev.md`.
- `report.md` and `report-jev.md` are generated — re-run `make report` and
  `make report-jev` after judging a new model rather than editing them by hand.
