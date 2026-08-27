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
make judge                            # opt-in: grade every ungraded answer file
make report                           # aggregate every judged run → report.md
```

- `MODEL` — llm7shi model string of the answerer (e.g.
  `google:gemini-4-31b-it`, `ollama:gemma4:31b-it-qat`)
- `LANG` — `en` | `ja` (selects the questions file and, for hybrid8, the
  reference run whose retrieval is replayed)

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
| `google:gemini-3-flash-preview` | 99 (49/1/0) | 97 (47/3/0) |
| `google:gemini-3.5-flash-lite` | 86 (41/4/5) | 86 (41/4/5) |
| `google:gemini-3.7-flash` | 97 (48/1/1) | 98 (49/0/1) |
| `google:gemma-4-31b-it` | 99 (49/1/0) | 98 (48/2/0) |
| `google:gemma-4-26b-a4b-it` | 95 (46/3/1) | 94 (45/4/1) |
| `ollama:gemma4:26b-a4b-it-qat` | 96 (47/2/1) | 92 (42/8/0) |
| `ollama:qwen3.6` (35B-A3B) | 99 (49/1/0) | 97 (47/3/0) |
| `ollama:qwen3.8` (27B) | 100 (50/0/0) | 99 (49/1/0) |
| `ollama:muse-glimmer` (27B) | 99 (49/1/0) | 97 (47/3/0) |
| `openai:gpt-5.6-luna` | 100 (50/0/0) | 97 (47/3/0) |
| `openai:gpt-5.6-terra` | 95 (47/1/2) | 99 (49/1/0) |
| `openrouter:stealth/ox-alpha` (320B-A18B) | 98 (49/0/1) | 100 (50/0/0) |
| `openrouter:poolside/laguna-s-2.1:free` | 88 (39/10/1) | 73 (31/11/8) |
| `openrouter:cohere/north-mini-code:free` | 93 (44/5/1) | 74 (30/14/6) |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | 100 (50/0/0) | 97 (47/3/0) |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 94 (44/6/0) | 86 (38/10/2) |

(Weighted score `(correct + 0.5×partial) / n`, as an integer percentage rounded
down, then correct/partial/incorrect out of 50 in parentheses. The
`gemma-4-31b-it` row is the canonical `results-<lang>/ceiling.jsonl` run; the
other rows live in this directory and are aggregated in [report.md](report.md).)

* **The top is crowded; the floor has widened.** Most models reach 0.960 or
  better in English, and several sit at 0.990 or 1.000 — `qwen3.8`,
  `gpt-5.6-luna` and `nemotron-3-ultra-550b-a55b:free` answer all 50, and
  `gemma-4-31b-it`, `qwen3.6`, `muse-glimmer` and `gemini-3-flash-preview`
  each drop a single `partial`. Ceiling is still a ceiling for that group: it
  measures whether a model can read two or three chapters it has already been
  handed, and those models can. Below that line, with the gold chapters
  supplied: `gemini-3.5-flash-lite` at 0.860, `poolside/laguna-s-2.1:free` at
  0.880, `cohere/north-mini-code:free` at 0.930, `gemini-2.5-flash` and
  `nemotron-3.5-lightning:free` tied at 0.940, and `gpt-5.6-terra` and
  `gemma-4-26b-a4b-it` tied at 0.950.
* **Japanese costs most models something.** The losses run from 0.010
  (`gemma-4-31b-it`, qwen3.8, `gemma-4-26b-a4b-it`) to 0.190
  (`cohere/north-mini-code:free`, the largest gap, ahead of
  `poolside/laguna-s-2.1:free`'s 0.150).
  `gemini-3.5-flash-lite` is the only model that scores identically in both
  languages (0.860, the same 41/4/5 split, on largely different questions). The
  Japanese miss list is markedly longer than the English one — the same
  questions, the same gold, the same gold chapters.
* **`stealth/ox-alpha` is the strongest Japanese model, and one of the few that
  gain from English to Japanese.** Its 50/50 is the only perfect Japanese run in
  the table, while in English it sits mid-table on a single outright error.
  `gemini-3.7-flash` reverses direction the same way but from lower down
  (0.970 → 0.980), `gpt-5.6-terra` does too, more sharply (0.950 → 0.990), and
  `gemini-2.5-flash` joins them at the bottom of the table (0.940 → 0.950).
* **The floor models fail in different kinds, not just degrees.**
  `gemini-3.5-flash-lite` fails by refusing: nine of its ten `incorrect`
  verdicts report that the answer is not in the context, with the gold chapters
  in the context. `poolside/laguna-s-2.1:free` stays fluent and stops being
  about the text — in Japanese it produces 8 outright errors, several on
  single-fact lookups few other models miss. `cohere/north-mini-code:free` has
  the largest language gap in the table (−0.190) and one Japanese answer that
  echoes the question back with no answer content at all.
  `nemotron-3.5-lightning:free` loses one Japanese row to a corrupted
  generation — garbled English mixed with fragments of its own system
  instructions — rather than to a misreading. The last two failure modes appear
  in no other model here. `gemini-2.5-flash` ties `nemotron-3.5-lightning:free`'s
  English score from a different profile: its one outright error is a factual
  substitution — misstating a duration the gold answers correctly — rather than
  a refusal or a corrupted generation.
* **Only the small MoE separates itself among the local models.**
  `gemma4:26b-a4b-it-qat` activates 4B parameters per token and is the only
  ollama model below 0.950; it loses 0.040 from English to Japanese, twice any
  other local model's loss. Its failure mode is legible in the verdicts: 8
  `partial` and no outright error in Japanese, i.e. it finds the passage and
  drops one of the two or three elements the gold answer enumerates.
* **The 26B-A4B pair splits by host in Japanese, not English.**
  `google:gemma-4-26b-a4b-it` and `ollama:gemma4:26b-a4b-it-qat` are the same
  Gemma 4 26B-A4B model on different hosts, the API build and the QAT build,
  the same relationship as the `gemma-4-31b-it` pair elsewhere in this
  project. English is close either way (0.950 vs. 0.960), but Japanese is
  not (0.940 vs. 0.920): the Google-hosted run turns half of the ollama run's
  eight `partial`s into `correct` and trades one of them for a single
  outright error instead — a different failure shape, not simply a better
  score.
* **Above 0.960 the shortfall is completeness on `cross` questions; below it,
  single-hop misreadings appear as well.** An outright error on a `single`
  question means misreading a chapter already supplied, and the floor models
  produce most of them — but the strongest models are not immune: two of them
  lose their only English verdict exactly that way, on the same question, from
  the same chapter.
* **The judge is `ollama:qwen3.6`, one of the answerers.** A same-family
  preference cannot be ruled out from these runs, though qwen3.6 tops neither
  language — it trails several models in each — which is weak evidence against a
  strong self-preference rather than proof of none. The judge is also visibly
  more lenient in Japanese on multi-part questions: an answer giving only one of
  the two halves the gold requires is scored `partial` in English but often
  passes as `correct` in Japanese, so the Japanese column understates how many
  runs answer only half of such a question.

### Every question any model missed

Question IDs, listed per model. Questions 1–25 are `single` (one gold chapter),
26–50 are `cross` (two or three).

| Model | en partial | en incorrect | ja partial | ja incorrect |
| --- | --- | --- | --- | --- |
| `google:gemini-2.5-flash` | 28, 30, 36, 41 | 17 | 28, **29**, 32, 35, 36 | — |
| `google:gemini-3-flash-preview` | 31 | — | 7, 33, 43 | — |
| `google:gemini-3.5-flash-lite` | 26, 28, 36, 48 | 17, 37, 40, 42, 47 | 28, **29**, 34, 40 | 35, 36, 39, 42, 50 |
| `google:gemini-3.7-flash` | 50 | 17 | — | **29** |
| `google:gemma-4-31b-it` | 48 | — | **29**, 36 | — |
| `google:gemma-4-26b-a4b-it` | 34, 37, 50 | 17 | 27, 34, 35, 37 | **29** |
| `ollama:gemma4:26b-a4b-it-qat` | 33, 35 | 17 | **29**, 34, 35, 37, 40, 44, 46, 50 | — |
| `ollama:qwen3.6` (35B-A3B) | 6 | — | **29**, 36, 48 | — |
| `ollama:qwen3.8` (27B) | — | — | **29** | — |
| `ollama:muse-glimmer` | 6 | — | 34, 35, 43 | — |
| `openai:gpt-5.6-luna` | — | — | **29**, 35, 48 | — |
| `openai:gpt-5.6-terra` | 31 | 22, 49 | 43 | — |
| `openrouter:stealth/ox-alpha` | — | 22 | — | — |
| `openrouter:poolside/laguna-s-2.1:free` | 26, 28, 31, 34, 37, 38, 39, 46, 48, 50 | 45 | 4, 27, **29**, 30, 32, 37, 39, 41, 43, 46, 50 | 2, 8, 12, 22, 34, 35, 42, 45 |
| `openrouter:cohere/north-mini-code:free` | 33, 36, 46, 49, 50 | 17 | 6, 26, 32, 33, 34, 35, 37, 38, 39, 42, 47, 48, 49, 50 | 12, 16, 28, **29**, 36, 46 |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | — | — | 37, 43, 44 | — |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 6, 28, 30, 34, 36, 37 | — | 6, 27, 28, 33, 35, 36, 37, 40, 43, 50 | **29**, 45 |

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
| `google:gemma-4-31b-it` | hybrid8 | 94 (46/2/2) | 95 (46/3/1) |
| `ollama:qwen3.8` | ceiling | 100 (50/0/0) | 99 (49/1/0) |
| `ollama:qwen3.8` | hybrid8 | 100 (50/0/0) | 95 (47/1/2) |
| `openrouter:stealth/ox-alpha` | ceiling | 98 (49/0/1) | 100 (50/0/0) |
| `openrouter:stealth/ox-alpha` | hybrid8 | 98 (48/2/0) | 98 (49/0/1) |

- **In English qwen3.8 pays nothing for retrieval.** It answers all 50 under
  both methods, verdict for verdict, even though the hybrid8 context misses gold
  chapters on 5 of 50 questions. Gemma drops 0.050 over the same step.
  `stealth/ox-alpha`'s score is also unchanged (0.980 → 0.980), but not verdict
  for verdict: its ceiling shortfall was one `incorrect` and its hybrid8
  shortfall is two `partial`s elsewhere — a wash in score over two different
  failure sets.
- **In Japanese every model pays.** qwen3.8 drops 0.040 (0.990 → 0.950), Gemma
  0.030 (0.980 → 0.950) from a slightly different ceiling distribution
  (48/2/0 vs qwen3.8's 49/1/0), so the two end level at 0.950 by different
  routes — Gemma with three partials, qwen3.8 with two outright errors.
- **`stealth/ox-alpha` pays least in Japanese, and starts from the top.** It
  drops only 0.020 (1.000 → 0.980) against Gemma's 0.030 and qwen3.8's 0.040,
  and its ceiling score was the only perfect Japanese run in the wider
  comparison (see [Ceiling](#ceiling-comparing-answerer-models) above).

### Hybrid8: every question any model missed

| Lang | Q | type | Gemma 4 | qwen3.8 | ox-alpha | gold in context |
| --- | --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | correct | correct | yes |
| en | 29 | cross | incorrect | correct | correct | yes |
| en | **32** | cross | partial | correct | partial | **no** |
| en | 48 | cross | partial | correct | correct | yes |
| en | **50** | cross | correct | correct | partial | **no** |
| ja | **27** | cross | partial | partial | incorrect | **no** |
| ja | 29 | cross | incorrect | incorrect | correct | yes |
| ja | 36 | cross | partial | correct | correct | yes |
| ja | **42** | cross | correct | incorrect | correct | **no** |
| ja | 44 | cross | partial | correct | correct | yes |

* **Cross-reference synthesis dominates the table.** Every row but one is
  `cross`; the lone `single` question, en Q17, is one of Gemma's misses — the
  other models get it.
* **Four rows are shared blind spots — gold chapters absent from
  the k=8 context — so a `correct` verdict there reflects prior knowledge or a
  lenient judge, not reading comprehension:** en Q32 and ja Q42 (both
  documented in [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)),
  plus en Q50 and ja Q27 (the same failure mode, not among HYBRID.md's four
  listed cases). Restricting to the questions whose gold chapters are actually
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
