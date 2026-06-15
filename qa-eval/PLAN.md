# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done**

- `build_index.py` — embeds all 82 scenes from `../all/en-gemini.jsonl` (+
  titles from `../all/en-gemini.tsv`) with `embeddinggemma` into
  `index-en.safetensors` (`[82, 768]` float32). See [README.md](README.md).
- `answer_rag.py` — Vector RAG over `index-en.safetensors`: top-k cosine
  search, ±N scene expansion within chapter, plain-text LLM answer via
  `llm7shi`. Output: `results/rag-<slug>.jsonl`. See [README.md](README.md).
  End-to-end run with `google:gemma-4-31b-it` completed on 2026-06-14. Output: `results/rag.jsonl`.
- `answer_extract.py` — Per-chapter extraction: Phase 1 scans all 37 chapters
  per question (outer=chapter, inner=question for KV-cache reuse), Phase 2
  synthesizes answers from relevant summaries. Phase 1 is split into 4 parts
  (`-p 1-4`) each writing `extract-{N}.jsonl`; Phase 2 reads all 4 and writes
  `extract.jsonl`. See [README.md](README.md).
  Phase 1 and Phase 2 complete as of 2026-06-15. Output: `results/extract.jsonl`
  (100 records, fields: `question_id`, `expanded`, `answer`).

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

## Common Infrastructure

- **Model selection**: `-m/--model` taking an `llm7shi` vendor-prefixed string
  (`ollama:gemma4:31b`, `google:gemini-2.5-flash`, etc.).
- **Plain-text generation**: `generate_with_schema` from `llm7shi.compat`
  without a schema. Streams to stdout; print a separator + header before each
  call. Prompt explicitly for plain text; avoid structured output (unstable
  with cloud models).
- **Resume support**: load done IDs from existing output, open in append mode,
  flush after each record. Mandatory for `answer_extract.py` (3,700 calls).
- **Default model**: `ollama:gemma4:31b`.

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
# build_index.py, answer_rag.py, answer_extract.py all done
uv run qa-eval/judge.py results/rag.jsonl results/extract.jsonl
uv run qa-eval/report.py
```

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors).
- Japanese-language evaluation (`split_chapters.py` → `index-ja`).
