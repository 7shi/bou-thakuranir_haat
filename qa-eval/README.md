# QA Evaluation

Tools for measuring the QA accuracy of local LLMs on the translations of
*Bou-Thakuranir Haat*, comparing **Vector RAG** against **Per-Chapter
Extraction** as retrieval strategies. See [PLAN.md](PLAN.md) for the full
design.

The retrieval unit is a **scene** (segment), not a paragraph or a chapter.

## Status

Answering and judging complete (English prototype; answers generated with
`google:gemma-4-31b-it`, judged with `ollama:qwen3.6`):

- `build_index.py` — scene embedding index → `index-en.safetensors`
- `answer_rag.py` — Vector RAG answering → `results/rag.jsonl`
- `answer_extract.py` — Per-chapter extraction answering → `results/extract.jsonl`
- `judge.py` — LLM grading of answers vs. gold → `results/judge-<stem>.jsonl`

Remaining: `report.py` (accuracy + chapter-recall comparison). See
[PLAN.md](PLAN.md).

## `build_index.py`

Embeds every scene of the English translation and stores the vectors in a
single `safetensors` file.

- **Inputs** (CLI-configurable):
  - `../all/en-gemini.jsonl` — one record per scene; the body is in
    `response.translation`. The `chapter=0, segment=0` title record (no
    `translation`) is skipped.
  - `../all/en-gemini.tsv` — scene titles, keyed by `(chapter, segment)`.
- **Embedding**: the `ollama` `embed()` API with the document prompt
  `title: {title} | text: {text}`. Default model `embeddinggemma` (768-dim).
- **Output**: `index-en.safetensors` — a `[N, dim]` float32 tensor named
  `embeddings`, plus metadata (`str -> str` only):
  - `embed_model` — the model used.
  - `count` — number of scenes.
  - `scenes` — JSON array of `{chapter, segment, title, text}`, in the same
    order as the matrix rows.

After saving, the script reads the file back and verifies the shape, count, and
restored metadata.

### Usage

```sh
uv run qa-eval/build_index.py            # defaults: en-gemini sources, index-en.safetensors
uv run qa-eval/build_index.py -e embeddinggemma
```

| Option | Default | Description |
| --- | --- | --- |
| `-e`, `--embed` | `embeddinggemma` | ollama embedding model |
| `-i`, `--input` | `../all/en-gemini.jsonl` | scenes JSONL |
| `-t`, `--tsv` | `../all/en-gemini.tsv` | scene titles TSV |
| `-o`, `--output` | `index-en.safetensors` | output safetensors path |

The script is parameterized so the same code can later index the Japanese
sources by pointing `-i`/`-t`/`-o` at the `ja` files.

## `answer_rag.py`

For each question in `questions-en.jsonl`, retrieves relevant scenes from the
index and asks an LLM to answer based solely on that context.

**Algorithm**

1. Embed the question with the query prompt `task: search result | query: {question}`.
2. Rank all scenes by cosine similarity and take the top-k hits.
3. Expand each hit by ±N scenes within the same chapter; merge overlapping
   ranges so no scene is included twice.
4. Build a context block with each scene labeled `[Chapter N, Scene M — Title]`.
5. Prompt the answer model to answer in English using only the provided context.

- **Input**: `questions-en.jsonl` (100 questions, ROOT-level)
- **Index**: `index-en.safetensors` (built by `build_index.py`)
- **Output**: `results/rag.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `hits` — top-k scenes as `{"chapter:segment": score}` dict
  - `expanded` — all scenes included in the context as `"chapter:segment"` strings
  - `answer` — the model's answer

Resume-safe: re-running skips question IDs already present in the output file.

### Usage

```sh
uv run qa-eval/answer_rag.py                      # defaults
uv run qa-eval/answer_rag.py -m ollama:qwen3:8b   # different model
```

| Option | Default | Description |
| --- | --- | --- |
| `-m`, `--model` | `ollama:gemma4:31b` | llm7shi model string |
| `-e`, `--embed` | `embeddinggemma` | ollama embedding model |
| `-k` | `5` | number of top scenes to retrieve |
| `-N` | `1` | context expansion window ±N scenes |
| `-i`, `--input` | `../questions-en.jsonl` | questions JSONL |
| `--index` | `index-en.safetensors` | scene index |
| `-o`, `--output` | `results/rag.jsonl` | output path |

## `answer_extract.py`

For each question in `questions-en.jsonl`, scans every chapter for relevant
content and synthesizes an answer from the collected excerpts.

**Algorithm**

Phase 1 — Extraction (37 chapters × 100 questions = 3,700 calls):

1. Outer loop iterates over chapters; inner loop iterates over questions. This
   keeps the same chapter text in the KV cache across all questions for that
   chapter.
2. For each (chapter, question) pair, pass the chapter text as context and ask
   the model to summarize relevant content, or output `None` if there is none.
3. Write the result immediately to the checkpoint file and flush.

Phase 2 — Answer (100 calls):

4. Collect all non-`None`, non-empty summaries for the question, labeled `[Chapter N]`.
5. Prompt the model to answer in English using only those excerpts.

- **Input**: `questions-en.jsonl` (100 questions, ROOT-level) and
  `../all/en-gemini.jsonl` (scenes)
- **Output**: `results/extract.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `expanded` — chapter numbers with relevant content, as `["5", "10", ...]` strings
  - `answer` — the model's synthesized answer
- **Part files**: `results/extract-{N}.jsonl` (N = 1–4) — one record per
  completed `(chapter, question_id)` pair for each chapter group:
  - `chapter` — chapter number
  - `question_id` — 1-origin line number in the input file
  - `text` — extracted summary, or `"None"` if not relevant
  - Part 1: chapters 1–10 · Part 2: chapters 11–20 · Part 3: chapters 21–30 · Part 4: chapters 31–37

Resume-safe at two levels: question IDs already in the output file are skipped
entirely; `(question_id, chapter)` pairs already in the part file are skipped
in Phase 1.

### Usage

```sh
# Phase 1: run parts in parallel (each writes its own extract-{N}.jsonl)
uv run qa-eval/answer_extract.py -p 1 &
uv run qa-eval/answer_extract.py -p 2 &
uv run qa-eval/answer_extract.py -p 3 &
uv run qa-eval/answer_extract.py -p 4 &
wait

# Or run all parts sequentially in one command:
uv run qa-eval/answer_extract.py -p 1-4

# Phase 2: synthesize answers from all 4 part files
uv run qa-eval/answer_extract.py
```

| Option | Default | Description |
| --- | --- | --- |
| `-m`, `--model` | `ollama:gemma4:31b` | llm7shi model string |
| `-p`, `--part` | — | chapter group(s): single (`2`) or range (`1-4`); omit for Phase 2 |
| `-i`, `--input` | `../questions-en.jsonl` | questions JSONL |
| `--scenes` | `../all/en-gemini.jsonl` | scenes JSONL |
| `-o`, `--output` | `results/extract.jsonl` | output path (Phase 2 result) |

## `judge.py`

Grades the candidate answers in one or more result files against the gold
standard, using a judge LLM. Retrieval quality (chapter recall) is computed
mechanically by `report.py`, not here.

**Algorithm**

For each answer record, build a prompt containing the question, the gold
`answer`, the gold `rationale` (as supporting evidence), and the candidate
`answer`, then ask the judge to grade factual content overlap (not wording) as
`correct` / `partial` / `incorrect` with a one-sentence reason.

The structured-output schema declares `reason` **before** `verdict`, so the
model writes its justification first and the verdict follows from it rather than
being a post-hoc rationalization. The default judge model is `ollama:qwen3.6`,
since Gemma 4 is weak at structured output.

A too-short `reason` (< 20 chars — i.e. blank, or just echoing the verdict like
`"correct"`) is retried up to 3 times (4 attempts total), printing a notice such
as `retrying (1/3)` each time; after that the short result is kept.

- **Inputs**: one or more `results/*.jsonl` files (positional), plus
  `questions-en.jsonl` for the gold standard.
- **Output**: `results/judge-<input-stem>.jsonl` (e.g. `results/rag.jsonl` →
  `results/judge-rag.jsonl`), one record per question:
  - `question_id` — 1-origin line number in the questions file
  - `verdict` — `correct` / `partial` / `incorrect`
  - `reason` — one-sentence justification

Resume-safe: re-running skips question IDs already present in the output file.

### Judge against the gold, not the source text

The judge compares only against the gold `answer`/`rationale`, **not** the
chapter source text. Feeding the source would give the judge two competing
authorities and muddy the verdict. Keeping it a pure gold-agreement check is
what makes the interpretation below valid.

### Interpreting the scores (convergent validity)

The gold answers are **not ground truth**: they were produced by Gemini 2.5 Pro
with the *whole text* in context (`scripts/create_rag_questions.py`), and huge
contexts can cause omissions ("lost in the middle"). So treat the metric as
*agreement with the Gemini full-text baseline*, not absolute accuracy.

This still yields a useful inference. RAG structurally **blocks** any context
vector search deems irrelevant, whereas Extract reads every chapter — an
independent thorough-reading path, like the gold's full-context reading. So if
**Extract ≥ RAG**, two independent thorough readers agree with the gold, which
is convergent evidence that the gold answers are sound. If Extract < RAG, that
is a signal to suspect either the gold or the extraction.

Because both methods are judged against the *same* gold, any systematic gold
bias cancels in the relative comparison; it only distorts the rare case where a
method surfaces a true fact the gold omitted. Spot-check the `partial` /
`incorrect` verdicts (few in number) using the gold `rationale`'s chapter
citations.

### Usage

```sh
uv run qa-eval/judge.py qa-eval/results/rag.jsonl qa-eval/results/extract.jsonl
uv run qa-eval/judge.py qa-eval/results/rag.jsonl -m ollama:qwen3:8b
```

| Option | Default | Description |
| --- | --- | --- |
| `inputs` (positional) | — | result JSONL files to judge (one or more) |
| `-m`, `--model` | `ollama:qwen3.6` | judge model (llm7shi string) |
| `-i`, `--input` | `../questions-en.jsonl` | questions JSONL (gold standard) |

## `ref/`

Reference material kept for convenience, not part of the pipeline.

- [ref/example.py](ref/example.py) — minimal usage example of the ollama
  `embed()` API, with EmbeddingGemma prompt conventions noted in the comments.
