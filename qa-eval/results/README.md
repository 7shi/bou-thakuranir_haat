# Per-model answerer runs

This directory holds runs with **answerer models other than the default**
`google:gemma-4-31b-it`, without touching the canonical `results-<lang>/`
trees — the existing per-strategy results stay as they are, and each new
(method, model, language) triple gets its own file here.

Two methods are available:

- **hybrid8** — Hybrid k=8 (dense ∪ BM25 union; [HYBRID.md](../HYBRID.md))
  retrieval, then answer.
- **ceiling** — no retrieval at all: the gold chapters as context
  (`answer_ceiling.py`). Retrieval is model-independent, so hybrid8 hands every
  model the identical context and the whole difference is synthesis anyway;
  ceiling measures that same difference on a much smaller context, which is
  cheaper and faster per question.

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
- `LANG` — `en` | `ja` (selects the questions file and, for hybrid8, the index)

`make judge` needs neither: it scans this directory for answer files that have
no `judge-` counterpart yet and reads the language off each filename.

Example:

```
make ceiling MODEL=google:gemini-4-31b-it LANG=ja
```

## `ollama:qwen3.8` vs. the default `google:gemma-4-31b-it`

> **Provisional — re-run in progress.** The numbers in this section come from
> the earlier qwen3.8 hybrid8 runs, which are currently being redone. Treat the
> table, the flip list, and the commentary below as unconfirmed until the runs
> finish and `make report` is re-run; both this section and
> [report.md](report.md) are to be updated from the fresh verdicts.

Both answerers were run on the identical Hybrid k=8 context — the `expanded`
lists match on all 50 questions in both languages — so every difference below is
**synthesis**, not retrieval.

| Model | English | Japanese |
| --- | --- | --- |
| `google:gemma-4-31b-it` (main table) | 46/50 (0.940) — 46/2/2 | 45/50 (0.940) — 45/4/1 |
| `ollama:qwen3.8` | **48/50 (0.970)** — 48/1/1 | **47/50 (0.970)** — 47/3/0 |

(`correct`/50 with the weighted score in parentheses, then correct/partial/incorrect.)

qwen3.8 gains +0.030 in both languages, and drops to zero `incorrect` in
Japanese. For scale, Gemma 4's `Ceiling` run (gold chapters fed verbatim) scores
0.990 EN / 0.970 JA — qwen3.8 reaches the Japanese ceiling while still going
through retrieval.

Questions whose verdict flips:

| Lang | Q | type | Gemma 4 | qwen3.8 | gold in context |
| --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | correct | yes |
| en | 28 | cross | correct | partial | yes |
| en | 29 | cross | incorrect | correct | yes |
| en | 31 | cross | correct | incorrect | **no** |
| en | 32 | cross | partial | correct | **no** |
| en | 48 | cross | partial | correct | yes |
| ja | 28 | cross | correct | partial | yes |
| ja | 29 | cross | incorrect | correct | yes |
| ja | 36 | cross | partial | correct | yes |
| ja | 44 | cross | partial | correct | yes |

* **Cross-reference synthesis is the whole gap:** 8 of the 10 flips are `cross`
  questions, and most of qwen3.8's wins convert a Gemma `partial` (evidence
  present, elements dropped) into a `correct`.
* **Q28 is the one consistent Gemma win** (both languages): the "two distinct
  locations and disguises" enumeration, where qwen3.8 drops one of the pair.
  Exhaustive enumeration looks like its weak spot.
* **Q29 is the one consistent qwen3.8 win** (both languages): separating the
  decree's stated aim from the actual cause of Surma's departure, which Gemma 4
  misses in both languages.
* **Discount the English Q31/Q32 flips:** both are the known shared blind spots
  ([HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)) whose gold
  chapters are absent from the context, so a `correct` there reflects prior
  knowledge or a lenient judge rather than reading comprehension. Excluding
  them, English is 45 → 47 and the direction is unchanged.

Caveat: the judge is `ollama:qwen3.6`, the same family as the tested answerer.
A same-family preference cannot be ruled out from these runs alone.

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
- The embedding index is reused from `qa-eval/index-<lang>.safetensors` and
  built via the parent Makefile only if missing (hybrid8 only — ceiling does no
  retrieval).
- The parent `report.py` does not scan this directory (its method discovery
  reads only `results-<lang>/hybrid<k>.jsonl`), so these runs never leak into
  the main table. `make report` here is the independent aggregation: it reuses
  the parent's `accuracy` / `retrieval` helpers but simply tallies every
  `judge-*.jsonl` present in this directory and writes `report.md`.
- `report.md` is generated — re-run `make report` after judging a new model
  rather than editing it by hand.
