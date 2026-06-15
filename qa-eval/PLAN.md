# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done** — see [README.md](README.md) for details.

- `build_index.py` — scene embedding index (`index-en.safetensors`)
- `answer_rag.py` — Vector RAG; run with `google:gemma-4-31b-it` on 2026-06-14 → `results/rag.jsonl`
- `answer_extract.py` — Per-chapter extraction; run with `google:gemma-4-31b-it` on 2026-06-15 → `results/extract.jsonl`

**Next step**

`judge.py` — evaluate answers from both methods against gold standard.

**Then**: `report.py` — aggregate accuracy and chapter recall comparison
between RAG and extraction. The Japanese path (`split_chapters.py` →
`index-ja`) is deferred until the English prototype works end to end.

## Goal

Compare two retrieval strategies for QA over the English translation of
*Bou-Thakuranir Haat* (100 questions in `questions-en.jsonl`):

1. **Vector RAG** — embed scenes, retrieve top-k, expand context, answer.
2. **Per-Chapter Extraction** — for each chapter, extract relevant passages,
   then answer from collected excerpts.

## Evaluation

### `judge.py`

- Input: one or more result JSONL files (`results/*.jsonl`).
- For each answer, compare against the gold `answer` and `rationale` from
  `questions-en.jsonl` using a judge model.
- Plain-text structured output per question: `correct / partial / incorrect`
  plus a short reason.
- Output: `results/judge-<source-slug>.jsonl`.

### Retrieval metric: chapter recall

Compute mechanically whether the chapters used (both methods: `expanded` field;
RAG entries are `"chapter:segment"` strings, Extract entries are `"chapter"` strings)
cover the gold `chapters` field.
This isolates retrieval quality from answering quality.

### `report.py`

Aggregate per method × model: accuracy counts and chapter recall. Print a
comparison table.

## Workflow

```sh
uv run qa-eval/judge.py results/rag.jsonl results/extract.jsonl
uv run qa-eval/report.py
```

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors).
- Japanese-language evaluation (`split_chapters.py` → `index-ja`).
