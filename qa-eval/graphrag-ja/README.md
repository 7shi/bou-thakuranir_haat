# GraphRAG Evaluation (Japanese)

Runs the 50 Japanese QA questions through a fork of Microsoft GraphRAG
with structured output support for Gemma 4:

* https://github.com/7shi/graphrag

Saves the answers for comparison with the retrieval methods in the parent `qa-eval` pipeline.

## Model and configuration

| Setting | Value |
|---|---|
| LLM (completion) | `ollama:gemma4:31b-it-qat` |
| Embedding | `ollama:embeddinggemma` |
| Chunk size | 1200 tokens (overlap 100) |
| Cluster size | 10 |
| Search modes | `local`, `global` |

Two YAML configs differ only in `call_args` on the completion model:

- **`settings-1.yaml`** (`make init`) — sets `timeout: 1200` and `reasoning_effort: none`
  to disable reasoning and prevent timeouts during the long prompt-tune / index runs.
- **`settings-2.yaml`** (`make run`) — `call_args` is commented out, so reasoning is
  enabled (default) for the actual queries.

Both configs use `extractor_type: syntactic_parser` (instead of `regex_english`) for
Japanese text.

### Environment

`OLLAMA_HOST` must point to the Ollama server (default `localhost`):

```sh
export OLLAMA_HOST=localhost   # or the remote host running Ollama
```

`GRAPHRAG_API_KEY` is a dummy value required by the Ollama provider; set it in
the `.env` file that `graphrag init` generates.

## Workflow

```sh
make init   # graphrag init → prompt-tune → index  (uses settings-1.yaml)
make run    # copy settings-2.yaml, run all 50 questions via run_queries.sh
make clean  # remove generated artifacts listed in .gitignore
```

### `make init` steps

1. `graphrag init` — scaffolds the project with `gemma4:31b-it-qat` and `embeddinggemma`
2. Symlinks `input/ja-gemini.txt` → `../../../all/ja-gemini.md` (the source text)
3. `graphrag prompt-tune --language Japanese` — tunes prompts to the corpus
4. `graphrag index` — builds the knowledge graph and LanceDB vector store under `output/`

### `make run` steps

1. `run_queries.sh` reads `../../questions-ja.jsonl` and for each question runs:

   ```
   graphrag query -r . -m local  "<question>"  → local/NN.txt
   graphrag query -r . -m global "<question>"  → global/NN.txt
   ```

   Existing non-empty output files are skipped (resume-safe). Per-query raw logs are
   written to `rawlogs/3-query/{local,global}-NN/`.

   To test a single question, pass its `anchor_id`:

   ```sh
   bash run_queries.sh 1
   ```

2. `build_jsonl.py` maps the `[Data: ...]` citation tags in each answer to chapter
   numbers and writes:

   ```
   ../results-ja/graphrag-local.jsonl
   ../results-ja/graphrag-global.jsonl
   ```

### Measured runtime (EVO-X2 / Ryzen AI Max+ 395)

| Command | Step | Time |
|---|---|---|
| `make init` | `prompt-tune` | 11m 53s |
| | `index` | 5h 35m 50s |
| | **total** | **5h 49m 34s** |
| `make run` | queries (local + global × 50) | 14h 28m 56s |
| **`make init run`** | | **20h 18m 30s** |

Compared to the [English run](../graphrag-en/README.md#measured-runtime-evo-x2--ryzen-ai-max-395),
`index` takes 1.37x longer and `run` takes 1.66x longer, even though per-LLM-call latency is
essentially the same in both languages (~45s/call during indexing). The gap traces back to a
higher LLM call count: 445 calls during `index` vs. 329 for English (1.35x), and 374 calls
across all 100 queries vs. 216 for English (1.73x). This in turn stems from the source text
splitting into more chunks under the same `chunk_size: 1200` (token-based) — the source text is
1.35x larger in UTF-8 bytes (407,473 vs. 302,316), and Gemma 4's tokenizer needs more tokens per
character of Japanese text, so the same content yields more chunks, entities, and communities,
which cascades into more LLM calls throughout indexing and querying.

## Output layout

```
local/01.txt … local/50.txt         # local-search answers
global/01.txt … global/50.txt       # global-search answers
logs/query-{local,global}-NN.log
rawlogs/
  1-tune/     # prompt-tune raw logs
  2-index/    # index raw logs
  3-query/    # per-question query raw logs
../results-ja/graphrag-local.jsonl   # built by build_jsonl.py
../results-ja/graphrag-global.jsonl
```
