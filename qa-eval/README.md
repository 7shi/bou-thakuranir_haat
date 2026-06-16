# QA Evaluation

Tools for measuring the QA accuracy of local LLMs on the translations of
*Bou-Thakuranir Haat*, comparing **Vector RAG** against **Per-Chapter
Extraction** as retrieval strategies. See [PLAN.md](PLAN.md) for the full
design.

The retrieval unit is a **scene** (segment), not a paragraph or a chapter.

## Languages

Every script takes `-l/--lang {en,ja}` (default `en`), which selects the
language-specific defaults in one switch: the gold questions
(`questions-<lang>.jsonl`), scene sources (`all/<lang>-gemini.jsonl` /
`all/<lang>-gemini.tsv`), the index (`index-<lang>.safetensors`), the output
directory (`results-<lang>/`), and the answer language. The individual path
options (`-i`/`-o`/`--index`/`--scenes`/`-t`) still override these defaults.

## Status

Answering and judging complete for **English** (`google:gemma-4-31b-it`
answers, judged with `ollama:qwen3.6`). The **Japanese** path runs the same
pipeline with `-l ja`.

- `build_index.py` — scene embedding index → `index-<lang>.safetensors`
- `answer_rag.py` — Vector RAG answering → `results-<lang>/rag.jsonl`
- `answer_extract.py` — Per-chapter extraction answering → `results-<lang>/extract.jsonl`
- `judge.py` — LLM grading of answers vs. gold → `results-<lang>/judge-<stem>.jsonl`
- `report.py` — accuracy + chapter retrieval comparison (terminal table)

Optional follow-up: `sweep_rag.py` (tune RAG's `-k`/`-N` from the gold chapter
labels). See [PLAN.md](PLAN.md).

## Pipeline (`Makefile`)

The [`Makefile`](Makefile) wires the five scripts into one dependency chain so
the whole evaluation runs with a single command. Models are left to each
script's default. Run it from this directory:

```sh
make            # full English pipeline (LANG=en, the default goal)
make ja         # full Japanese pipeline
make all        # both languages
make report     # build whatever is missing, then print the table
make LANG=ja rag judge   # individual steps for one language
make clean      # remove generated answers/judgements (keeps the index)
```

Each step's **output file is the real target**, with a `.PHONY` alias for
convenience:

| Alias | Output target | Depends on |
| --- | --- | --- |
| `index` | `index-<lang>.safetensors` | scenes, titles TSV |
| `rag` | `results-<lang>/rag.jsonl` | index, questions |
| `extract-parts` | `results-<lang>/extract-{1..4}.jsonl` | scenes, questions |
| `extract` | `results-<lang>/extract.jsonl` | the four part files, questions |
| `judge` | `results-<lang>/judge-{rag,extract}.jsonl` | the answer files, questions |
| `report` | (terminal table only) | `judge` |

Because the targets are real files, Make skips any step whose output is already
up to date and rebuilds only what is missing or stale — re-running `make` after
an interrupted run resumes from where it stopped (each script is also internally
resume-safe). Phase 1 of extraction uses a pattern rule (`extract-%.jsonl`, one
chapter group per part), so the parts can be built in parallel with `make -j`.

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
- **Output**: `index-<lang>.safetensors` — a `[N, dim]` float32 tensor named
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
uv run qa-eval/build_index.py -l ja      # ja-gemini sources, index-ja.safetensors
uv run qa-eval/build_index.py -e embeddinggemma
```

| Option | Default | Description |
| --- | --- | --- |
| `-l`, `--lang` | `en` | evaluation language (`en`/`ja`); selects the defaults below |
| `-e`, `--embed` | `embeddinggemma` | ollama embedding model |
| `-i`, `--input` | `../all/<lang>-gemini.jsonl` | scenes JSONL |
| `-t`, `--tsv` | `../all/<lang>-gemini.tsv` | scene titles TSV |
| `-o`, `--output` | `index-<lang>.safetensors` | output safetensors path |

The `-l ja` titles TSV (`all/ja-gemini.tsv`) is produced by `make titles`
(`scripts/generate_titles.py … --title-lang Japanese`).

## `answer_rag.py`

For each question in `questions-<lang>.jsonl`, retrieves relevant scenes from the
index and asks an LLM to answer based solely on that context.

**Algorithm**

1. Embed the question with the query prompt `task: search result | query: {question}`.
2. Rank all scenes by cosine similarity and take the top-k hits.
3. Expand each hit by ±N scenes within the same chapter; merge overlapping
   ranges so no scene is included twice.
4. Build a context block with each scene labeled `[Chapter N, Scene M — Title]`.
5. Prompt the answer model to answer in English using only the provided context.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level)
- **Index**: `index-<lang>.safetensors` (built by `build_index.py`)
- **Output**: `results-<lang>/rag.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `hits` — top-k scenes as `{"chapter:segment": score}` dict
  - `expanded` — all scenes included in the context as `"chapter:segment"` strings
  - `answer` — the model's answer

Resume-safe: re-running skips question IDs already present in the output file.

### Usage

```sh
uv run qa-eval/answer_rag.py                      # defaults (en)
uv run qa-eval/answer_rag.py -l ja                # Japanese
uv run qa-eval/answer_rag.py -m ollama:qwen3:8b   # different model
```

| Option | Default | Description |
| --- | --- | --- |
| `-l`, `--lang` | `en` | evaluation language (`en`/`ja`); also sets the answer language |
| `-m`, `--model` | `ollama:gemma4:31b-it-qat` | llm7shi model string |
| `-e`, `--embed` | `embeddinggemma` | ollama embedding model |
| `-k` | `5` | number of top scenes to retrieve |
| `-N` | `1` | context expansion window ±N scenes |
| `-i`, `--input` | `../questions-<lang>.jsonl` | questions JSONL |
| `--index` | `index-<lang>.safetensors` | scene index |
| `-o`, `--output` | `results-<lang>/rag.jsonl` | output path |

## `answer_extract.py`

For each question in `questions-<lang>.jsonl`, scans every chapter for relevant
content and synthesizes an answer from the collected excerpts.

**Algorithm**

Phase 1 — Extraction (37 chapters × 50 questions = 1,850 calls):

1. Outer loop iterates over chapters; inner loop iterates over questions. This
   keeps the same chapter text in the KV cache across all questions for that
   chapter.
2. For each (chapter, question) pair, pass the chapter text as context and ask
   the model to summarize relevant content, or output `None` if there is none.
3. Write the result immediately to the checkpoint file and flush.

Phase 2 — Answer (50 calls):

4. Collect all non-`None`, non-empty summaries for the question, labeled `[Chapter N]`.
5. Prompt the model to answer in English using only those excerpts.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level) and
  `../all/<lang>-gemini.jsonl` (scenes)
- **Output**: `results-<lang>/extract.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `expanded` — chapter numbers with relevant content, as `["5", "10", ...]` strings
  - `answer` — the model's synthesized answer
- **Part files**: `results-<lang>/extract-{N}.jsonl` (N = 1–4) — one record per
  completed `(chapter, question_id)` pair for each chapter group:
  - `chapter` — chapter number
  - `question_id` — 1-origin line number in the input file
  - `text` — extracted summary, or `"None"` if not relevant
  - Part 1: chapters 1–10 · Part 2: chapters 11–20 · Part 3: chapters 21–30 · Part 4: chapters 31–37

Resume-safe at two levels: question IDs already in the output file are skipped
entirely; `(question_id, chapter)` pairs already in the part file are skipped
in Phase 1.

Its main failure mode is a Phase 1 false negative: a wrong `None` drops a gold
chapter unrecoverably, so Phase 2 never sees it. See
[results-en/README.md](results-en/README.md#2-rag-correct--extract-not-correct-8-questions)
for worked examples and the RAG-vs-Extract disagreement analysis.

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

# Japanese: pass -l ja to every invocation above
uv run qa-eval/answer_extract.py -l ja -p 1-4
uv run qa-eval/answer_extract.py -l ja
```

| Option | Default | Description |
| --- | --- | --- |
| `-l`, `--lang` | `en` | evaluation language (`en`/`ja`); also sets the answer language |
| `-m`, `--model` | `ollama:gemma4:31b-it-qat` | llm7shi model string |
| `-p`, `--part` | — | chapter group(s): single (`2`) or range (`1-4`); omit for Phase 2 |
| `-i`, `--input` | `../questions-<lang>.jsonl` | questions JSONL |
| `--scenes` | `../all/<lang>-gemini.jsonl` | scenes JSONL |
| `-o`, `--output` | `results-<lang>/extract.jsonl` | output path (Phase 2 result) |

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

- **Inputs**: one or more `results-<lang>/*.jsonl` files (positional), plus
  `questions-<lang>.jsonl` for the gold standard.
- **Output**: `judge-<input-stem>.jsonl` next to each input (e.g.
  `results-en/rag.jsonl` → `results-en/judge-rag.jsonl`), one record per question:
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
uv run qa-eval/judge.py qa-eval/results-en/rag.jsonl qa-eval/results-en/extract.jsonl
uv run qa-eval/judge.py -l ja qa-eval/results-ja/rag.jsonl qa-eval/results-ja/extract.jsonl
uv run qa-eval/judge.py qa-eval/results-en/rag.jsonl -m ollama:qwen3:8b
```

| Option | Default | Description |
| --- | --- | --- |
| `inputs` (positional) | — | result JSONL files to judge (one or more) |
| `-l`, `--lang` | `en` | evaluation language (`en`/`ja`); selects the gold questions file |
| `-m`, `--model` | `ollama:qwen3.6` | judge model (llm7shi string) |
| `-i`, `--input` | `../questions-<lang>.jsonl` | questions JSONL (gold standard) |

## `report.py`

Aggregates the existing result files into one comparison table on the terminal.
Pure mechanical aggregation — no LLM calls, no output file.

**Two independent axes**, with one (method, scope) row each:

1. **Answer accuracy** (from `results-<lang>/judge-<method>.jsonl`): raw `correct` /
   `partial` / `incorrect` counts plus a weighted score =
   `(correct + 0.5*partial) / total`. `partial` stays its own column so the
   half-credit weighting never hides the raw distribution.
2. **Chapter retrieval** (mechanical, each method's `expanded` vs the gold
   `chapters` in `questions-<lang>.jsonl`):
   - **recall** — per-question complete coverage: 1 if `gold ⊆ used` else 0,
     meaned over the questions in scope.
   - **precision** — mean of `|gold ∩ used| / |used|` per question.

   RAG `expanded` entries are `"chapter:segment"` (the part before `:` is the
   chapter); Extract entries are bare `"chapter"` strings.

Both axes are broken down by the gold `type` field: the `all` scope covers every
question, then one scope per type (`single` / `cross`), so single-passage vs.
cross-reference performance can be read side by side. The `n` column is the
number of questions in each scope.

Read the accuracy axis alongside the convergent-validity caveat above: the gold
is the Gemini full-text baseline, so **Extract ≥ RAG** is evidence the gold is
sound.

**Output format** (one row per method × scope; `n` is the question count). The
English run (answers `google:gemma-4-31b-it`, judge `ollama:qwen3.6`):

```
scope    method     n correct partial incorrect  weighted ch.recall  ch.prec
----------------------------------------------------------------------------
all      RAG       50      39       5         6     0.830     0.720    0.337
all      Extract   50      39       5         6     0.830     0.740    0.843
single   RAG       25      24       0         1     0.960     1.000    0.263
single   Extract   25      24       0         1     0.960     1.000    1.000
cross    RAG       25      15       5         5     0.700     0.440    0.411
cross    Extract   25      15       5         5     0.700     0.480    0.686
```

The two methods tie on accuracy (39/50 correct, weighted 0.830) yet split sharply
on the **single** vs. **cross** axis: both score 24/25 on single-passage questions
but only 15/25 on cross-reference ones, so the cross set is where retrieval and
synthesis actually get tested. Extract matches or beats RAG on chapter recall
(0.740 vs 0.720) at far higher precision (it keeps only the chapters it judges
relevant), so **Extract ≥ RAG** holds — convergent evidence the gold is sound. The
per-question [disagreement case study](results-en/README.md) walks through every
split verdict.

### Usage

```sh
uv run qa-eval/report.py          # English (results-en)
uv run qa-eval/report.py -l ja    # Japanese (results-ja)
```

| Option | Default | Description |
| --- | --- | --- |
| `-l`, `--lang` | `en` | evaluation language (`en`/`ja`); selects the gold questions and `results-<lang>` dir |
| `-i`, `--input` | `../questions-<lang>.jsonl` | questions JSONL (gold standard) |

## `ref/`

Reference material kept for convenience, not part of the pipeline.

- [ref/example.py](ref/example.py) — minimal usage example of the ollama
  `embed()` API, with EmbeddingGemma prompt conventions noted in the comments.
