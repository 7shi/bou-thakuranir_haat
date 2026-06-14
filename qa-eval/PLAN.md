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
  End-to-end run with `ollama:gemma4:31b` completed on 2026-06-14.

**Next step**

Implement `answer_extract.py` (see spec below).

**Then** (in order): `judge.py` → `report.py`. The Japanese path
(`split_chapters.py` → `index-ja`) is deferred until the English prototype
works end to end.

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
  without a schema. Streams to stdout; print a separator before each item.
- **Resume support**: load done IDs from existing output, open in append mode,
  flush after each record. Mandatory for `answer_extract.py` (3,700 calls).
- **Default model**: `ollama:gemma4:31b`.

## Method 2: Per-Chapter Extraction

### `answer_extract.py`

Input: `../all/en-gemini.jsonl` (scenes) + `questions-en.jsonl` (100 questions).
The chapter text is reconstructed by concatenating all scenes for that chapter.

For each question, two phases:

**Phase 1 — Extraction** (37 chapters × 100 questions = 3,700 calls):

For each chapter, pass the chapter text and the question, asking the model to
quote passages relevant to the question (or report none). Structured output via
`generate_with_schema` with a Pydantic schema:

```python
class ChapterExtraction(BaseModel):
    relevant: bool
    excerpts: list[str]
```

Separator + `[Q{qid} Ch{ch}]` header before each call so streaming is readable.

Intermediate results are checkpointed per `(question_id, chapter)` so an
interrupted run can skip completed pairs.

**Phase 2 — Answer** (100 calls):

Concatenate all excerpts from relevant chapters (labeled `[Chapter N]`) and
ask the model to answer the question in English based only on them. Plain-text
generation (no schema).

Output: `results/extract-<slug>.jsonl`, one record per question:

```json
{
  "question_id": 1,
  "question": "...",
  "extractions": [
    {"chapter": 2, "relevant": true, "excerpts": ["..."]},
    {"chapter": 3, "relevant": false, "excerpts": []}
  ],
  "answer": "..."
}
```

Resume logic: a question is done when its record appears in the output file.
Within a question, a chapter is done when its entry appears in `extractions`.

## Evaluation

### `judge.py`

- Input: one or more result JSONL files (`results/*.jsonl`).
- For each answer, compare against the gold `answer` and `rationale` from
  `questions-en.jsonl` using a judge model.
- Plain-text structured output per question: `correct / partial / incorrect`
  plus a short reason.
- Output: `results/judge-<source-slug>.jsonl`.

### Retrieval metric: chapter recall

Compute mechanically whether the chapters used (RAG: `expanded_scenes`;
Extraction: chapters where `relevant=true`) cover the gold `chapters` field.
This isolates retrieval quality from answering quality.

### `report.py`

Aggregate per method × model: accuracy counts and chapter recall. Print a
comparison table.

## Workflow

```sh
# build_index.py and answer_rag.py already done
uv run qa-eval/answer_extract.py
uv run qa-eval/judge.py results/rag-ollama-gemma4-31b.jsonl results/extract-ollama-gemma4-31b.jsonl
uv run qa-eval/report.py
```

## Out of Scope (for now)

- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors).
- Japanese-language evaluation (`split_chapters.py` → `index-ja`).
