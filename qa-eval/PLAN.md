# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done** — see [README.md](README.md) for details.

- `build_index.py` — scene embedding index (`index-en.safetensors`)
- `answer_rag.py` — Vector RAG; run with `google:gemma-4-31b-it` on 2026-06-14 → `results/rag.jsonl`
- `answer_extract.py` — Per-chapter extraction; run with `google:gemma-4-31b-it` on 2026-06-15 → `results/extract.jsonl`
- `judge.py` — LLM grading of answers vs. gold (judge model `ollama:qwen3.6`) → `results/judge-<stem>.jsonl`

**Next step**

`report.py` — aggregate accuracy (from `results/judge-*.jsonl`) and chapter
recall comparison between RAG and extraction. The Japanese path
(`split_chapters.py` → `index-ja`) is deferred until the English prototype
works end to end.

## Goal

Compare two retrieval strategies for QA over the English translation of
*Bou-Thakuranir Haat* (100 questions in `questions-en.jsonl`):

1. **Vector RAG** — embed scenes, retrieve top-k, expand context, answer.
2. **Per-Chapter Extraction** — for each chapter, extract relevant passages,
   then answer from collected excerpts.

## Remaining work

### `report.py`

Aggregate per method (RAG vs. Extract): answer accuracy and chapter recall, and
print a comparison table.

- **Accuracy** — count `correct` / `partial` / `incorrect` per method from
  `results/judge-rag.jsonl` and `results/judge-extract.jsonl`. Decide how to
  score `partial` (e.g. half credit or a separate column).
- **Chapter recall** — compute mechanically whether the chapters used cover the
  gold `chapters` field in `questions-en.jsonl`. Both methods expose an
  `expanded` field: RAG entries are `"chapter:segment"` strings, Extract entries
  are `"chapter"` strings — reduce both to chapter numbers. This isolates
  retrieval quality from answering quality.

Read accuracy alongside the convergent-validity caveat documented in
[README.md](README.md#interpreting-the-scores-convergent-validity): the gold is
the Gemini full-text baseline, not ground truth, so **Extract ≥ RAG** is
evidence the gold is sound.

```sh
uv run qa-eval/report.py
```

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors).
- Japanese-language evaluation (`split_chapters.py` → `index-ja`).
