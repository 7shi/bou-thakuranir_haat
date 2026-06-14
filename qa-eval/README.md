# QA Evaluation

Tools for measuring the QA accuracy of local LLMs on the translations of
*Bou-Thakuranir Haat*, comparing **Vector RAG** against **Per-Chapter
Extraction** as retrieval strategies. See [PLAN.md](PLAN.md) for the full
design.

The retrieval unit is a **scene** (segment), not a paragraph or a chapter.

## Status

Implemented scripts:

- `build_index.py` — scene embedding index
- `answer_rag.py` — Vector RAG answering

See [PLAN.md](PLAN.md) for the remaining pipeline and next steps.

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
- **Output**: `results/rag-<model-slug>.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `question` — question text
  - `hits` — top-k scenes as `{"chapter:segment": score}` dict
  - `expanded_scenes` — all scenes included in the context as `"chapter:segment"` strings
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
| `-o`, `--output` | `results/rag-<slug>.jsonl` | output path |

## `ref/`

Reference material kept for convenience, not part of the pipeline.

- [ref/example.py](ref/example.py) — minimal usage example of the ollama
  `embed()` API, with EmbeddingGemma prompt conventions noted in the comments.
