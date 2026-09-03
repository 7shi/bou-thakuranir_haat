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
- `judge-<METHOD>-<MODEL>-<LANG>.jsonl` — verdicts (`judge.py`, opt-in)

The method leads so runs group by method, and the language trails so it can be
read straight off the filename — the model is the only field that may itself
contain "`-`".

`report.py` aggregates every judged pair in this directory into
[report.md](report.md).

The judge stays the default `ollama:qwen3.6` for comparability with the main
table in [README.md](../README.md).

## Usage

Run via [Makefile](Makefile) (the directory's default target prints the usage
line):

```
make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions → hybrid8-<MODEL>-<LANG>.jsonl
make ceiling MODEL=... LANG={en,ja}   # answer 50 questions → ceiling-<MODEL>-<LANG>.jsonl
make test    MODEL=... LANG={en,ja}   # answer question 1 only, both methods, no file output
make judge                            # opt-in: grade every ungraded answer file
make report                           # aggregate every judged run → report.md
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
no `judge-` counterpart yet and reads the language off each filename.

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

| Model | English | Japanese |
| --- | --- | --- |
| `google:gemini-2.5-flash` | 94 (45/4/1) | 95 (45/5/0) |
| `google:gemini-3-flash-preview` | 100 (50/0/0) | 97 (47/3/0) |
| `google:gemini-3.5-flash-lite` | 86 (41/4/5) | 86 (41/4/5) |
| `google:gemini-3.7-flash` | 97 (48/1/1) | 98 (49/0/1) |
| `google:gemini-3.8-flash` | 98 (49/0/1) | 97 (48/1/1) |
| `google:gemma-4-31b-it` | 99 (49/1/0) | 98 (48/2/0) |
| `google:gemma-4-26b-a4b-it` | 95 (46/3/1) | 94 (45/4/1) |
| `ollama:gemma4:26b-a4b-it-qat` | 95 (46/3/1) | 92 (42/8/0) |
| `ollama:qwen3.6` (35B-A3B) | 98 (48/2/0) | 97 (47/3/0) |
| `ollama:qwen3.8` (27B) | 100 (50/0/0) | 99 (49/1/0) |
| `ollama:muse-glimmer` (30B) | 99 (49/1/0) | 97 (47/3/0) |
| `openai:gpt-5.6-luna` | 100 (50/0/0) | 97 (47/3/0) |
| `openai:gpt-5.6-sol` | 100 (50/0/0) | 100 (50/0/0) |
| `openai:gpt-5.6-terra` | 96 (48/0/2) | 99 (49/1/0) |
| `opencode:mimo-v2.5-free` | 100 (50/0/0) | 96 (47/2/1) |
| `opencode:muse-spark-1.2-contributor-free` | 98 (49/0/1) | 100 (50/0/0) |
| `opencode:muse-spark-1.3-contributor-free` | 100 (50/0/0) | 100 (50/0/0) |
| `openrouter:stealth/ox-alpha` (320B-A18B) | 98 (49/0/1) | 100 (50/0/0) |
| `openrouter:poolside/laguna-s-2.1:free` | 89 (40/9/1) | 73 (31/11/8) |
| `openrouter:cohere/north-mini-code:free` | 93 (44/5/1) | 73 (29/15/6) |
| `openrouter:inclusionai/ling-3.0-flash-fin:free` | 97 (47/3/0) | 95 (45/5/0) |
| `openrouter:minimax/minimax-m2.7:free` | 96 (46/4/0) | 97 (47/3/0) |
| `openrouter:minimax/minimax-m3:free` | 98 (49/0/1) | 99 (49/1/0) |
| `openrouter:nvidia/nemotron-3-super-120b-a12b:free` | 93 (43/7/0) | 90 (41/8/1) |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | 99 (49/1/0) | 97 (47/3/0) |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 93 (43/7/0) | 86 (38/10/2) |

(Weighted score `(correct + 0.5×partial) / n`, as an integer percentage rounded
down, then correct/partial/incorrect out of 50 in parentheses. The
`gemma-4-31b-it` row is the canonical `results-<lang>/ceiling.jsonl` run; the
other rows live in this directory and are aggregated in [report.md](report.md).
The `opencode:*` rows are produced by a separate pipeline that drives the
`opencode` coding-agent CLI instead of the llm7shi-based `answer_ceiling.py`
used for every other row — see [opencode/README.md](../opencode/README.md).)

* **The top is crowded; the floor has widened.** Most models reach 0.960 or
  better in English, and several sit at 0.990 or 1.000 — `qwen3.8`,
  `gpt-5.6-luna`, `gpt-5.6-sol`, `gemini-3-flash-preview`,
  `mimo-v2.5-free` and `muse-spark-1.3-contributor-free` answer all 50 in
  English, and `gemma-4-31b-it`, `muse-glimmer` and
  `nemotron-3-ultra-550b-a55b:free` each drop a single `partial`.
  `gpt-5.6-sol` and `muse-spark-1.3-contributor-free` are the only models
  perfect in **both** languages — every other perfect English score drops at
  least one Japanese question, and
  `stealth/ox-alpha`'s perfect Japanese score comes with one English miss.
  Ceiling is still a ceiling for that group: it measures whether a model can
  read two or three chapters it has already been handed, and those models
  can. Below that line, with the gold chapters supplied: `gemini-3.5-flash-lite`
  at 0.860, `poolside/laguna-s-2.1:free` at 0.890,
  `cohere/north-mini-code:free`, `nemotron-3-super-120b-a12b:free` and
  `nemotron-3.5-lightning:free` tied at 0.930, `gemini-2.5-flash` at 0.940,
  and `gemma-4-26b-a4b-it` and `ollama:gemma4:26b-a4b-it-qat` tied at 0.950.
* **Japanese doesn't cost every model — a handful score higher there.**
  `gemini-2.5-flash`, `gemini-3.7-flash`, `gpt-5.6-terra`, `stealth/ox-alpha`,
  `minimax-m2.7:free`, `minimax-m3:free` and `muse-spark-1.2-contributor-free`
  all post a *better* Japanese score than English.
  Among the rest, losses run from 0.010 (`gemma-4-31b-it`, qwen3.8,
  `gemma-4-26b-a4b-it`, `qwen3.6`) to 0.200 (`cohere/north-mini-code:free`,
  the largest gap, ahead of `poolside/laguna-s-2.1:free`'s 0.160). Three
  models score identically in both languages: `gemini-3.5-flash-lite` at
  0.860 (the same 41/4/5 split, on largely different questions), and
  `gpt-5.6-sol` and `muse-spark-1.3-contributor-free` at 1.000 (50/0/0 in
  both) — the only models perfect in both. The Japanese miss list is
  markedly longer than the English one for most models — the same
  questions, the same gold, the same gold chapters.

### Every question any model missed

Question IDs, listed per model. Questions 1–25 are `single` (one gold chapter),
26–50 are `cross` (two or three).

| Model | en partial | en incorrect | ja partial | ja incorrect |
| --- | --- | --- | --- | --- |
| `google:gemini-2.5-flash` | 28, 30, 36, 41 | 17 | 28, **29**, 32, 35, 36 | — |
| `google:gemini-3-flash-preview` | — | — | 7, 33, 43 | — |
| `google:gemini-3.5-flash-lite` | 26, 28, 36, 48 | 17, 37, 40, 42, 47 | 28, **29**, 34, 40 | 35, 36, 39, 42, 50 |
| `google:gemini-3.7-flash` | 50 | 17 | — | **29** |
| `google:gemini-3.8-flash` | — | 17 | 37 | **29** |
| `google:gemma-4-31b-it` | 48 | — | **29**, 36 | — |
| `google:gemma-4-26b-a4b-it` | 34, 37, 50 | 17 | 27, 34, 35, 37 | **29** |
| `ollama:gemma4:26b-a4b-it-qat` | 31, 33, 35 | 17 | **29**, 34, 35, 37, 40, 44, 46, 50 | — |
| `ollama:qwen3.6` (35B-A3B) | 6, 31 | — | **29**, 36, 48 | — |
| `ollama:qwen3.8` (27B) | — | — | **29** | — |
| `ollama:muse-glimmer` (30B) | 6 | — | 34, 35, 43 | — |
| `openai:gpt-5.6-luna` | — | — | **29**, 35, 48 | — |
| `openai:gpt-5.6-sol` | — | — | — | — |
| `openai:gpt-5.6-terra` | — | 22, 49 | 43 | — |
| `opencode:mimo-v2.5-free` | — | — | 20, 37 | 38 |
| `opencode:muse-spark-1.2-contributor-free` | — | 22 | — | — |
| `opencode:muse-spark-1.3-contributor-free` | — | — | — | — |
| `openrouter:stealth/ox-alpha` (320B-A18B) | — | 22 | — | — |
| `openrouter:poolside/laguna-s-2.1:free` | 26, 28, 34, 37, 38, 39, 46, 48, 50 | 45 | 4, 27, **29**, 30, 32, 37, 39, 41, 43, 46, 50 | 2, 8, 12, 22, 34, 35, 42, 45 |
| `openrouter:cohere/north-mini-code:free` | 33, 36, 46, 49, 50 | 17 | 6, 26, 31, 32, 33, 34, 35, 37, 38, 39, 42, 47, 48, 49, 50 | 12, 16, 28, **29**, 36, 46 |
| `openrouter:inclusionai/ling-3.0-flash-fin:free` | 33, 45, 49 | — | 33, 35, 37, 38, 50 | — |
| `openrouter:minimax/minimax-m2.7:free` | 6, 31, 34, 37 | — | 36, 37, 47 | — |
| `openrouter:minimax/minimax-m3:free` | — | 22 | 50 | — |
| `openrouter:nvidia/nemotron-3-super-120b-a12b:free` | 6, 26, 28, 31, 34, 37, 49 | — | **29**, 31, 33, 34, 37, 46, 49, 50 | 36 |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | 31 | — | 37, 43, 44 | — |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 6, 28, 30, 31, 34, 36, 37 | — | 6, 27, 28, 33, 35, 36, 37, 40, 43, 50 | **29**, 45 |

Ceiling doubles as a sanity check on the gold itself: with the gold chapters in
the context, a `correct` verdict says the question and its gold answer agree.
The questions appearing above are the ones that need auditing — every question
absent from the table is answered from the gold chapters by every model.

* **No question is missed by every model.** The widest row is ja Q29, then ja
  Q35, then a cluster of `cross` questions behind them. A question that no model
  answers from the gold chapters in either language is the signature of a broken
  gold rather than a hard question, and the set does not contain one — ja Q29 included: every model
  answers it correctly in English, and several reach the scored fact in Japanese
  too, so the widest row is language ability rather than question quality.
* **Nothing here is a missing-evidence failure** — the context is the gold
  annotation, so every miss is synthesis inside two or three chapters.
* **Multi-chapter `cross` questions carry the difficulty.** Only a handful of
  the questions above are `single`; the rest are `cross`. In Japanese those
  `single` misses come almost entirely from the floor models, while in English
  they are spread thinly across otherwise strong ones.

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
| `google:gemma-4-31b-it` | ceiling | 99 (49/1/0) | 98 (48/2/0) |
| `google:gemma-4-31b-it` | hybrid8 | 93 (45/3/2) | 95 (46/3/1) |
| `ollama:qwen3.8` | ceiling | 100 (50/0/0) | 99 (49/1/0) |
| `ollama:qwen3.8` | hybrid8 | 99 (49/1/0) | 95 (47/1/2) |
| `openrouter:stealth/ox-alpha` | ceiling | 98 (49/0/1) | 100 (50/0/0) |
| `openrouter:stealth/ox-alpha` | hybrid8 | 97 (47/3/0) | 98 (49/0/1) |

- **In English every model pays something for retrieval, but qwen3.8 and
  `stealth/ox-alpha` pay almost nothing.** Both drop only 0.010 (qwen3.8:
  1.000 → 0.990; `stealth/ox-alpha`: 0.980 → 0.970) even though the hybrid8
  context misses gold chapters on 5 of 50 questions. Gemma pays the most,
  dropping 0.060 (0.990 → 0.930).
- **In Japanese every model pays.** qwen3.8 drops 0.040 (0.990 → 0.950), Gemma
  0.030 (0.980 → 0.950) from a slightly different ceiling distribution
  (48/2/0 vs qwen3.8's 49/1/0), so the two end level at 0.950 by different
  routes — Gemma with three partials, qwen3.8 with two outright errors.
- **`stealth/ox-alpha` pays least in Japanese, and starts from the top.** It
  drops only 0.020 (1.000 → 0.980) against Gemma's 0.030 and qwen3.8's 0.040,
  and its ceiling score was the only perfect Japanese run in the wider
  comparison (see [Ceiling](#ceiling-comparing-answerer-models) above).

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
| en | 29 | cross | incorrect | - | - | — |
| en | **31** | cross | partial | partial | partial | **Ch22** |
| en | **32** | cross | partial | - | partial | **Ch15** |
| en | **38** | cross | - | - | - | **Ch32** |
| en | **42** | cross | - | - | - | **Ch23** |
| en | 48 | cross | partial | - | - | — |
| en | **50** | cross | - | - | partial | **Ch23** |
| ja | **27** | cross | partial | partial | incorrect | **Ch33** |
| ja | 29 | cross | incorrect | incorrect | - | — |
| ja | **32** | cross | - | - | - | **Ch15** |
| ja | 36 | cross | partial | - | - | — |
| ja | **42** | cross | - | incorrect | - | **Ch23, Ch29** |
| ja | 44 | cross | partial | - | - | — |

* **Cross-reference synthesis dominates the table.** Every row but one is
  `cross`; the lone `single` question, en Q17, is one of Gemma's misses — the
  other models get it.
* **Eight rows are shared blind spots — gold chapters absent from
  the k=8 context — so a `correct` verdict there reflects prior knowledge or a
  lenient judge, not reading comprehension:** en Q31, en Q32, en Q38, en Q42,
  ja Q32, and ja Q42 (all six documented in
  [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots) — four for
  English at `k≤10`, two for Japanese), plus en Q50 and ja Q27 (the same
  failure mode at k=8, not among HYBRID.md's `k≤10` blind spots).
  Restricting to the questions whose gold chapters are actually
  present — English n=45, Japanese n=47 — each model's correct/partial/incorrect
  becomes: Gemma 42/1/2 (en), 44/2/1 (ja); qwen3.8 45/0/0 (en), 46/0/1 (ja);
  `stealth/ox-alpha` 45/0/0 (en), 47/0/0 (ja). On the evidence actually
  supplied, qwen3.8 and `stealth/ox-alpha` both answer every English question,
  and `stealth/ox-alpha` answers every Japanese one too while qwen3.8 drops to
  0.979. Gemma trails in both languages, at 0.944 (en) and 0.957 (ja).
* **Two effects account for the rest of the table, and neither is about
  retrieval recall.** One is the judge boundary: on a question whose evidence is
  absent, a model that names what it can and then says the rest cannot be
  confirmed from the context is scored `incorrect`, while models that simply
  leave the gap unaddressed are scored `partial` — the same honesty graded two
  ways. The other is long-context distraction: Gemma and qwen3.8 each lose a
  Japanese verdict at hybrid8 on a question whose gold chapters *are* in the k=8
  context, answering about an unrelated subplot once those chapters sit inside a
  larger one. `stealth/ox-alpha` is unaffected by the added context here.

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
  `judge-*.jsonl` present in this directory and writes `report.md`.
- `report.md` is generated — re-run `make report` after judging a new model
  rather than editing it by hand.
