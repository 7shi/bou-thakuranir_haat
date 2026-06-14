# QA Evaluation

Tools for measuring the QA accuracy of local LLMs on the translations of
*Bou-Thakuranir Haat*, comparing **Vector RAG** against **Per-Chapter
Extraction** as retrieval strategies. See [PLAN.md](PLAN.md) for the full
design.

The retrieval unit is a **scene** (segment), not a paragraph or a chapter.

## Status

An English prototype of the indexing step is implemented. The rest of the
pipeline described in [PLAN.md](PLAN.md) (answering, judging, reporting) is not
yet built.

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

## `ref/`

Reference material kept for convenience, not part of the pipeline.

- [ref/example.py](ref/example.py) — minimal usage example of the ollama
  `embed()` API, with EmbeddingGemma prompt conventions noted in the comments.
