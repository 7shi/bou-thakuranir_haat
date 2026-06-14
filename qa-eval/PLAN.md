# QA Evaluation Plan: Vector RAG vs. Per-Chapter Extraction

## Status / Next steps

Read this first to resume after a session reset.

**Done**

- `build_index.py` — English prototype that embeds all 82 scenes from
  `../all/en-gemini.jsonl` (+ titles from `../all/en-gemini.tsv`) with
  `embeddinggemma` and saves them to `index-en.safetensors` (`[82, 768]`
  float32 tensor `embeddings` + per-scene metadata JSON). See
  [README.md](README.md). `index-en.safetensors` is gitignored.
- Note the deviation from the original plan below: the prototype uses
  **English + safetensors**, not the Japanese JSONL pipeline. Scenes come
  straight from `en-gemini.jsonl`, so `split_chapters.py` was **not** needed
  for English.

**Next step**

1. Implement `answer_rag.py` against `index-en.safetensors`: load the tensor +
   metadata, embed each question (`task: search result | query: {q}`),
   top-k cosine search, ±N scene expansion, then answer with an `llm7shi`
   model. Use `questions-en.jsonl` for the English prototype. (See the
   `answer_rag.py` section below for the full spec.)

**Then** (in order): `answer_extract.py` → `judge.py` → `report.py`. The
Japanese path (`split_chapters.py` → `index-ja`) is deferred until the English
prototype works end to end.

## Goal

Measure and compare the QA accuracy of local LLMs on the Japanese translation
(`all/ja-gemini.md`, 37 chapters, ~1,100 paragraphs, ~400 KB) using the 100
evaluation questions in `questions-ja.jsonl`. The original text is Bengali, but
this evaluation targets Japanese reading comprehension, so the Japanese
translation is used as the source text.

The text is divided into **scenes** (segments) defined by `segmentations.jsonl`,
with English scene titles pre-generated in `segmentations.tsv`. The unit of
retrieval is a scene, not a paragraph.

Since the full text does not fit in a local LLM's context window, two retrieval
strategies are compared:

1. **Vector RAG**: Embed each scene into a vector index using EmbeddingGemma.
   For each question, retrieve the most similar scenes, expand them with
   surrounding context, and let the LLM answer from that context.
2. **Per-Chapter Extraction**: For each question, iterate over all 37 chapters
   and ask the LLM to extract relevant passages from each chapter. Finally,
   combine all extracted passages and let the LLM answer.

This contrasts vector search against brute-force reading comprehension.
Feeding the entire text into the context at once is intentionally out of scope.

## Decisions

- **LLM backends**: Both Ollama and OpenAI-compatible servers are supported.
  Model strings are passed verbatim to `llm7shi` using its vendor-prefix
  format: `ollama:qwen3:8b`, `openai:model@http://host:port/v1`,
  `google:gemini-2.5-flash`, etc.
- **Embeddings**: Use the `ollama` Python package (`embed()` function). The
  embedding model is a CLI argument (default candidate: `embeddinggemma`). See
  [README.md](README.md) for the working `build_index.py` implementation.
- **Judge**: The judge model is also specified as an `llm7shi` model string,
  so grading can be done by Gemini or by a local model.
- **Location**: All scripts and outputs live under `qa-eval/`.

## Data Preparation

### `split_chapters.py`

- Input: `../all/ja-gemini.md`
- Load scene boundaries from `../segmentations.jsonl` and scene titles from
  `../segmentations.tsv`.
- Split text into scenes per chapter: `{"chapter": N, "scene": M, "title": ..., "text": ...}`.
- Output: `scenes-ja.jsonl`, one record per scene.
- Scene ID: `(chapter, scene_index)` with `scene_index` 1-origin within the
  chapter, matching the indices in `segmentations.jsonl`.
- Question ID: the 1-origin line number in `questions-ja.jsonl`.

## Common Infrastructure

- **Model selection**: CLI option `-m/--model` taking an `llm7shi`
  vendor-prefixed model string, passed through unchanged.
- **Structured output**: Pydantic schemas with
  `llm7shi.compat.generate_with_schema`, following the existing pattern in
  `scripts/create_rag_questions.py`.
- **Resume support**: Every script that produces JSONL output skips entries
  already present in the output file (same incremental pattern as
  `scripts/create_rag_questions.py` and `scripts/translate_segments.py`).
  This is essential for Method 2 (see cost note below).
- **Embedding client**: Use the `ollama` Python package (`embed()` function).
  Document embeddings use the prompt
  `title: {scene_title} | text: {content}` where `scene_title` is loaded from
  `../segmentations.tsv`; query embeddings use
  `task: search result | query: {content}`.

### EmbeddingGemma facts (for the default embedding model)

EmbeddingGemma is a 300M-parameter multilingual (100+ languages) embedding
model from Google. Key constraints and conventions relevant here:

- **Output dimension**: 768 by default. Smaller sizes (512 / 256 / 128) are
  available via Matryoshka Representation Learning — truncate the 768-d vector
  and re-normalize. We use the full 768-d output.
- **Input limit**: maximum context length of **2K tokens**. Scenes longer than
  this will be silently truncated by the embedder; if long scenes hurt recall,
  consider splitting them or summarizing before embedding.
- **Prompt templates** (prepended to the input; both query and document sides
  must use the right form):
  - Query (retrieval): `task: search result | query: {content}`
  - Document (retrieval): `title: {title | "none"} | text: {content}` —
    providing a real title improves performance over `"none"`.
  - Alternative query task for QA: `task: question answering | query: {content}`
    (a candidate to compare against `search result` if retrieval is weak).

## Method 1: Vector RAG

> The scene index is already built. See [README.md](README.md) for
> `build_index.py`.

### `answer_rag.py`

For each question:

1. Embed the question text with the query prompt
   `task: search result | query: {question}`.
2. Retrieve the top-k scenes by cosine similarity (default `k=5`). With only
   ~82 scenes, brute-force cosine similarity with numpy is sufficient; no
   dedicated vector database is needed.
3. Expand each hit with ±N surrounding scenes within the same chapter
   (default `N=1`), then merge overlapping ranges.
4. Build a context block (with chapter numbers labeled) and ask the answer
   model to answer the question in Japanese based only on the context.

- Output: `results/rag-<model>.jsonl`, one record per question:
  question ID, retrieved hits (chapter, scene, score), the constructed
  context, and the model's answer.

## Method 2: Per-Chapter Extraction

### `answer_extract.py`

For each question, two phases:

1. **Extraction phase**: For each of the 37 chapters, pass the chapter text
   and the question, asking the model to quote passages relevant to the
   question (or report none). Structured output:
   `{"relevant": bool, "excerpts": [str, ...]}`.
2. **Answer phase**: Concatenate all excerpts (labeled with chapter numbers)
   and ask the model to answer the question in Japanese based on them.

- Cost note: 100 questions x 37 chapters = 3,700 extraction calls. Resume
  support and per-question checkpointing are mandatory. Intermediate
  per-chapter extraction results are stored so an interrupted run can
  continue without re-reading completed chapters.
- Output: `results/extract-<model>.jsonl`, one record per question:
  question ID, per-chapter extraction results, and the final answer.

## Evaluation

### `judge.py`

- Input: one or more result JSONL files (from either method).
- The judge model (any `llm7shi` model string, e.g. `google:gemini-2.5-pro`)
  compares each answer against the gold `answer` and `rationale` from
  `questions-ja.jsonl`.
- Structured output per question: verdict in `correct / partial / incorrect`
  plus a short reason.
- Output: `results/judge-<source>.jsonl`.

### Retrieval metric: chapter recall

Independently of answer grading, compute mechanically whether the context
actually used (RAG: chapters of expanded hits; Extraction: chapters with
non-empty excerpts) covers the gold `chapters` of each question. This
isolates retrieval quality from answering quality.

### `report.py`

- Aggregate per method x model: answer accuracy (correct / partial /
  incorrect counts) and chapter recall.
- Print a summary table comparing the two methods.

## Workflow

```sh
uv run qa-eval/split_chapters.py
# build_index.py is already done; see README.md
uv run qa-eval/answer_rag.py -m ollama:qwen3:8b
uv run qa-eval/answer_extract.py -m ollama:qwen3:8b
uv run qa-eval/judge.py -m google:gemini-2.5-pro results/*.jsonl
uv run qa-eval/report.py
```

Adding targets to the root `Makefile` will be considered during the
implementation phase.

## Out of Scope (for now)

- Implementation of the scripts above (this document is the plan only).
- Whole-text-in-context baselines with cloud models.
- Hybrid retrieval (BM25 + vectors) — possible future extension if vector
  recall turns out to be the bottleneck.
