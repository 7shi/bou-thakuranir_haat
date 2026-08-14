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
```

- `MODEL` — llm7shi model string of the answerer (e.g.
  `google:gemini-4-31b-it`, `ollama:gemma4:31b-it-qat`)
- `LANG` — `en` | `ja` (selects the questions file and the index)

Example:

```
make hybrid8 MODEL=google:gemini-4-31b-it LANG=ja
```

## Notes

- Both scripts are **resume-safe**: they append and skip question IDs already
  present in the output file, so an interrupted run is continued by re-running
  the same command.
- The embedding index is reused from `qa-eval/index-<lang>.safetensors` and
  built via the parent Makefile only if missing.
- `report.py` does not scan this directory (method discovery reads only
  `results-<lang>/hybrid<k>.jsonl`), so these runs never leak into the main
  table. Tally a judge file with a one-liner instead, e.g.:
  `python -c "import json,collections;c=collections.Counter(json.loads(l)['verdict'] for l in open('judge-<MODEL>-<LANG>-hybrid8.jsonl'));print(c,(c['correct']+0.5*c['partial'])/50)"`
