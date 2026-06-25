# GraphRAG Evaluation

Runs the 50 English QA questions through [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
and saves the answers for comparison with the retrieval methods in the parent `qa-eval` pipeline.

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
2. Symlinks `input/en-gemini.txt` → `../../../all/en-gemini.md` (the source text)
3. `graphrag prompt-tune --language English` — tunes prompts to the corpus
4. `graphrag index` — builds the knowledge graph and LanceDB vector store under `output/`

### `make run` steps

1. `run_queries.sh` reads `../../questions-en.jsonl` and for each question runs:

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
   ../results-en/graphrag-local.jsonl
   ../results-en/graphrag-global.jsonl
   ```

### Measured runtime (EVO-X2 / Ryzen AI Max+ 395)

| Command | Step | Time |
|---|---|---|
| `make init` | `graphrag init` | ~2s |
| | `prompt-tune` | 17m 22s |
| | `index` | 4h 5m 40s |
| | **total** | **4h 23m 4s** |
| `make run` | queries (local + global × 50) | 8h 42m 33s |
| **`make init run`** | | **13h 5m 37s** |

## Output layout

```
local/01.txt … local/50.txt         # local-search answers
global/01.txt … global/50.txt       # global-search answers
logs/query-{local,global}-NN.log
rawlogs/
  1-tune/     # prompt-tune raw logs
  2-index/    # index raw logs
  3-query/    # per-question query raw logs
../results-en/graphrag-local.jsonl   # built by build_jsonl.py
../results-en/graphrag-global.jsonl
```
