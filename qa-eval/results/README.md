# Per-model Hybrid k=8 runs

This directory holds **Hybrid k=8** (dense ∪ BM25 union;
[HYBRID.md](../HYBRID.md)) runs with **answerer models other than the default**
`google:gemma-4-31b-it`, without touching the canonical `results-<lang>/`
trees — the existing per-strategy results stay as they are, and each new
(model, language) pair gets its own file here.

Filenames encode the model and language so multiple experiments coexist
("`:`" in the model string is replaced by "`_`"):

- `<MODEL>-<LANG>-hybrid8.jsonl` — answers (`answer_hybrid.py -k 8`), e.g.
  `google_gemini-4-31b-it-ja-hybrid8.jsonl`
- `judge-<MODEL>-<LANG>-hybrid8.jsonl` — verdicts (`judge.py`, opt-in)

`report.py` aggregates every judged pair in this directory into
[report.md](report.md).

Retrieval itself is model-independent (same `embeddinggemma` dense index +
BM25), so the only variable across these files is the answerer; the judge
stays the default `ollama:qwen3.6` for comparability with the main table in
[README.md](../README.md).

## Usage

Run via [Makefile](Makefile) (the directory's default target prints the usage
line):

```
make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions → <MODEL>-<LANG>-hybrid8.jsonl
make judge   MODEL=... LANG={en,ja}   # opt-in: grade → judge-<MODEL>-<LANG>-hybrid8.jsonl
make report                           # aggregate every judged run → report.md
```

- `MODEL` — llm7shi model string of the answerer (e.g.
  `google:gemini-4-31b-it`, `ollama:gemma4:31b-it-qat`)
- `LANG` — `en` | `ja` (selects the questions file and the index)

Example:

```
make hybrid8 MODEL=google:gemini-4-31b-it LANG=ja
```

## `ollama:qwen3.8` vs. the default `google:gemma-4-31b-it`

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

## Notes

- Both scripts are **resume-safe**: they append and skip question IDs already
  present in the output file, so an interrupted run is continued by re-running
  the same command.
- The embedding index is reused from `qa-eval/index-<lang>.safetensors` and
  built via the parent Makefile only if missing.
- The parent `report.py` does not scan this directory (its method discovery
  reads only `results-<lang>/hybrid<k>.jsonl`), so these runs never leak into
  the main table. `make report` here is the independent aggregation: it reuses
  the parent's `accuracy` / `retrieval` helpers but simply tallies every
  `judge-*.jsonl` present in this directory and writes `report.md`.
- `report.md` is generated — re-run `make report` after judging a new model
  rather than editing it by hand.
