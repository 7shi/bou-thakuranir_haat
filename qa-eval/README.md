# QA Evaluation

Tools for measuring the QA accuracy of local LLMs on the translations of
*Bou-Thakuranir Haat*, comparing **Vector RAG** against two per-chapter
retrieval strategies — **Extraction** (summarize) and **Filter** (yes/maybe/no
relevance) — as alternative ways to surface the chapters the answerer sees,
with a **Ceiling** run (gold chapters fed directly as context) to establish a
perfect-retrieval upper bound that isolates the answer model's reading
comprehension.

The retrieval unit is a **scene** (segment), not a paragraph or a chapter.

## Results

50 questions per language, judged against a Gemini full-text gold standard
with `ollama:qwen3.6`. The table reports `correct`/50 with the weighted score
`(correct + 0.5·partial) / 50` in parentheses. **Vector-line** has been run for
both languages; Vector `k=10`, **Hybrid**, **Filter2**, **Filter3**, and
**Ceiling** are English only (Japanese pending).

| Method | English | Japanese |
| --- | --- | --- |
| Vector k=5 | 39/50 (0.830) | 38/50 (0.810) |
| Vector k=10 | 44/50 (0.920) | — |
| Vector-line k=5 | 35/50 (0.800) | 35/50 (0.790) |
| Vector-line k=10 | 41/50 (0.890) | 40/50 (0.840) |
| Hybrid k=5 | 43/50 (0.910) | — |
| Hybrid k=10 | 47/50 (0.960) | — |
| Extract | 39/50 (0.830) | 40/50 (0.850) |
| Filter2 | 36/50 (0.790) | — |
| Filter3 | 45/50 (0.930) | — |
| Ceiling | 49/50 (0.990) | — |

Both languages use the same answer model `google:gemma-4-31b-it`, the same
`embeddinggemma` index, and the same judge.

**Retrieval strategy is the lever; language barely is.** At `k=5`, Vector and
Extract tie on English (0.830) and sit within two questions on Japanese (0.810
vs 0.850) — the language makes almost no difference. The main lever is
retrieval depth: **bumping Vector to `k=10`** (English) lifts 0.830 → 0.920,
exactly what [`sweep_vector.py`](#sweep_vectorpy) predicted (`k=5` was tight; deeper
retrieval surfaces the chapters the top-5 missed). What `k=10` *cannot* fix is
dense-retrieval blindness — load-bearing chapters that rank outside the top-10
at both depths. The **Hybrid** (dense ∪ BM25 union) breaks through that
frontier: at `k=10` it reaches **0.960**, recovering the three
lexically-distinctive cross-reference chapters that dense embedding cannot rank
— see [HYBRID.md](HYBRID.md) for the retrieval analysis and
[results-en/README.md](results-en/README.md#hybrid-dense--bm25-union) for the
per-question breakdown.

**Line-level retrieval trades recall for precision and nets out below segment
Vector.** `Vector-line` embeds one vector per line (rather than per scene) and
resolves each line hit back to its containing segment for context; it scores
0.800 (k=5) and 0.890 (k=10), below the segment-level 0.830 / 0.920 at both
depths. The finer unit raises chapter precision (k=5 0.34→0.40, k=10 0.21→0.27)
but lowers recall (k=5 0.72→0.66, k=10 0.84→0.78): single-passage saturates to
1.000 at both depths (above segment k=5's 0.960), while every loss is a
cross-reference retrieval miss where a gold chapter's relevant content is too
diffuse for a single line to rank. The misses are *orthogonal* to segment
Vector's — line granularity recovers a few chapters segment search drops (Q49
Ch22, Q34 Ch31) while dropping others — but the net is negative, so segment-level
retrieval remains the stronger dense baseline. **Japanese replicates the
pattern**: line k=5 (0.790) sits just below segment k=5 (0.810) with the same
precision-up / recall-down trade, and the orthogonal recoveries are even more
pronounced (union strict recall lifts the segment k=5 baseline from 36/50 to
41/50 at line k=5, 43/50 at line k=10). See
[results-en/README.md](results-en/README.md#vector-line-line-level-retrieval) and
[results-ja/README.md](results-ja/README.md#vector-line-line-level-retrieval) for
the per-question breakdowns.

The **Filter** rows use the LLM itself as the retriever (per-chapter relevance,
answer from the full text of the kept chapters). Filter3 posts the best
per-chapter score (0.930) but at hundreds of times Vector's cost and trailing
Hybrid k=10 (0.960) — see [FILTER.md](FILTER.md) for the full analysis and
verdict. The per-question
detail is in the case studies:
[English](results-en/README.md) · [Japanese](results-ja/README.md).

**Ceiling pins the frontier to retrieval, not comprehension.** Feeding the
gold chapters verbatim as context (no retrieval at all) lands at **0.990** —
49 correct, one partial (Q48), zero incorrect — with chapter recall and
precision both 1.000 by construction. No method ever beats Ceiling: its lead
over each is the pure cost of that method's retrieval, and the gradient tracks
retrieval quality exactly — Ceiling beats Filter2 on 14, Extract on 11, Vector k=5
on 10, Hybrid k=5 on 6, Vector k=10 on 5, Filter3 on 4, and Hybrid k=10 on just 2.
**Hybrid k=10 is the closest retrieval method to Ceiling**: its two-question residual
is one synthesis regression (Q22, where the wider union context confuses the answerer
on a single-passage question) and one shared blind spot neither retriever can reach
(Q32, Ch15). The lone Ceiling loss
(Q48, partial) is a pure synthesis failure — the paranoid "whisper-to-servant
= insult plot" detail is *in* Chapter 19's text, yet the model reads it as
"acting for his sister's sake," confirming that Q48's resistance is an
answering-model limit, not a retrieval one. See the
[Ceiling case study](results-en/README.md#ceiling-the-perfect-retrieval-upper-bound).

## Languages

Every script takes `-l/--lang {en,ja}` (default `en`), which selects the
language-specific defaults in one switch: the gold questions
(`questions-<lang>.jsonl`), scene sources (`all/<lang>-gemini.jsonl` /
`all/<lang>-gemini.tsv`), the index (`index-<lang>.safetensors`), the output
directory (`results-<lang>/`), and the answer language. The individual path
options (`-i`/`-o`/`--index`/`--scenes`/`-t`) still override these defaults.

## Status

Answering and judging complete for both languages for Vector and Extract (see
[Results](#results) above). Both filter variants (Filter2 and Filter3) and
Ceiling are wired into the pipeline and have been run for English (Japanese
pending); run [`make filter2`](#pipeline-makefile) /
[`make filter3`](#pipeline-makefile) / [`make ceiling`](#pipeline-makefile)
with `-l ja` to fill the Japanese rows. **Hybrid** (dense ∪ BM25 union)
answering and judging complete for English at k=5 and k=10 (built into the
default `make` via `make judge` for `LANG=en`; BM25 is English-only so Japanese
is deferred);
the BM25 and hybrid retrieval analyses remain standalone scripts
(`bm25.py` / `hybrid.py`, run directly) — see [HYBRID.md](HYBRID.md).

The scripts form the pipeline (Filter and Ceiling are opt-in):

- `build_index.py` — scene embedding index → `index-<lang>.safetensors`
- `answer_vector.py` — Vector RAG answering → `results-<lang>/vector5.jsonl`
- `answer_extract.py` — Per-chapter extraction answering → `results-<lang>/extract.jsonl`
- `answer_filter.py` — Per-chapter relevance filter, the LLM as retriever (yes/no, yes/maybe/no, integer 0–10/0–100, or five-axis); see [FILTER.md](FILTER.md) for details → `results-<lang>/filter2.jsonl`, `filter3.jsonl`, or `filter{V}.tsv` verdict files (opt-in)
- `answer_ceiling.py` — Gold-chapter context, no retrieval → `results-<lang>/ceiling.jsonl` (opt-in)
- `answer_hybrid.py` — dense ∪ BM25 union ([HYBRID.md](HYBRID.md) Union approach), Phase 2 QA → `results-<lang>/hybrid<k>.jsonl` (English only; built into `make judge` for `LANG=en`)
- `judge.py` — LLM grading of answers vs. gold → `results-<lang>/judge-<stem>.jsonl`
- `report.py` — accuracy + chapter retrieval comparison + pairwise disagreement analysis (terminal table)
- `sweep_vector.py` — retrieval-depth / threshold sweep vs. gold chapters
  (terminal tables only; no LLM, independent of the pipeline)
- `bm25.py` — BM25/lexical retrieval gold-coverage analysis vs. dense
  (terminal tables only; no LLM, independent of the pipeline);
  the sparse-retrieval sibling of sweep_vector.py; see [HYBRID.md](HYBRID.md)
- `hybrid.py` — dense+BM25 fusion (RRF/Borda/CombSUM) vs. union oracle
  (terminal tables only; no LLM, independent of the pipeline);
  see [HYBRID.md](HYBRID.md)
- `filter.py` — Filter10 score-distribution / threshold-sweep analysis and
  filter2/3 crosstab (terminal tables only; no LLM, independent of the
  pipeline); see [FILTER.md](FILTER.md)
- `filter5d.py` — Filter5d five-axis sum-distribution / threshold-sweep /
  per-axis analysis (terminal tables only; no LLM, independent of the
  pipeline); see [FILTER.md](FILTER.md)

`answer.py` holds the shared helpers (`LANGS`, `PART_RANGES`, `load_questions`,
`load_chapters`, `answer_question`) imported by all five answer scripts
(vector / extract / filter / ceiling / hybrid).

## Pipeline (`Makefile`)

The [`Makefile`](Makefile) wires the scripts into one dependency chain, so the
whole evaluation runs with a single command (models left to each script's
default). Run from this directory:

```sh
make                 # full English pipeline (LANG=en, the default goal; includes Hybrid k=5/10 via `make judge`)
make ja              # full Japanese pipeline (no Hybrid — BM25 is English-only)
make all             # both languages
make vector K=10     # Vector at k=10 → results-<lang>/vector10.jsonl
make vector LANG=ja  # individual steps for one language
make clean           # remove generated answers/judgements (keeps the index)
```

Standalone retrieval analyses (no LLM, independent of the pipeline):

```sh
make sweep              # dense retrieval depth/threshold sweep (needs ollama)
make bm25               # BM25 sparse retrieval gold-coverage analysis
uv run hybrid.py -l en  # dense+BM25 fusion (RRF/Borda/CombSUM) vs. union oracle (needs ollama; no `make` alias — `make hybrid` drives the Phase 2 QA)
```

Each step's **output file is the real target**, so Make skips anything already
up to date and an interrupted `make` resumes where it stopped (each script is
also internally resume-safe). Extraction Phase 1 uses a pattern rule (one chapter
group per part), so the parts build in parallel with `make -j`. Filter writes a
single consolidated verdict TSV per variant instead (the files are small and
fast to generate, so the part split is unnecessary); it is **opt-in** (not in
`make`, `make all`, or `make <lang>`) because Phase 1 costs ~1,850 LLM calls
per language — run
`make filter2` (two-level, yes/no) or `make filter3` (three-level,
yes/maybe/no) after the default pipeline to add a per-chapter retrieval
strategy, or `make filter10-tsv` (eleven-level, integer 0–10) to collect raw
relevance scores whose keep/drop threshold is chosen afterwards (see
[FILTER.md](FILTER.md)). Ceiling is **opt-in** for a different reason — it is
not a retrieval method at all but a perfect-retrieval reference run, so it sits
outside the default retrieval comparison; run `make ceiling` to feed the gold
chapters directly as context and measure the answer model's reading
comprehension in isolation (~50 calls, no Phase 1).

## `build_index.py`

Embeds every scene into a single `index-<lang>.safetensors`.

- **Inputs**: `../all/<lang>-gemini.jsonl` (one record per scene; the
  `chapter=0, segment=0` title record is skipped) + `.tsv` scene titles.
- **Embedding**: ollama `embed()` with the document prompt
  `title: {title} | text: {text}` (768-dim `embeddinggemma`).
- **Output**: a `[N, dim]` float32 `embeddings` tensor plus metadata —
  `embed_model`, `count`, and `scenes` (JSON array of
  `{chapter, segment, title, text}` in row order).
- **`--line`**: embeds one vector per **non-blank line** (split on `\n`) instead
  of per scene, each with the document prompt `title: "none" | text: {line}` (a
  per-line title is more overhead than signal at this granularity). Output is
  `index-line-<lang>.safetensors`; `scenes` then holds the per-line entries
  (`{chapter, segment, line, text}`) and a new `segments` key holds the full
  segment list so [`answer_vector.py --line`](#answer_vectorpy) can build
  segment-level context from a line hit.

## `answer_vector.py`

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
- **Output**: `results-<lang>/vector<k>.jsonl` (e.g. `vector5.jsonl` for the
  default `k=5`, `vector10.jsonl` for `-k 10`) — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `hits` — top-k scenes as `{"chapter:segment": score}` dict
  - `expanded` — all scenes included in the context as `"chapter:segment"` strings
  - `answer` — the model's answer

Resume-safe: re-running skips question IDs already present in the output file.
The k-aware filename lets a deeper retrieval run (e.g. `-k 10`) coexist with the
`k=5` baseline rather than overwriting it; `judge.py` derives its output stem
from the input, so `judge-vector10.jsonl` follows automatically.

`--line` switches to **line-level** retrieval: it loads
`index-line-<lang>.safetensors` (one vector per line, built by
[`build_index.py --line`](#build_indexpy)), ranks lines instead of scenes, then
resolves each hit line back to its containing segment before the same ±N
expansion and answering. The only new step is the line→segment conversion;
everything after it reuses the segment path verbatim. Output goes to
`vector-line<k>.jsonl` (so it coexists with the segment-level `vector<k>.jsonl`),
with `hits` keyed `chapter:segment:line` to preserve line provenance.
Build/run with `make index LINE=1` / `make vector LINE=1`; plain `make judge`
grades any `vector-line<k>.jsonl` already present.

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
chapter unrecoverably, so Phase 2 never sees it. See the
[k=5 baseline section](results-en/README.md#k5-baseline-in-brief) of the case
study for the Vector-vs-Extract disagreement analysis.

## `answer_filter.py`

A per-chapter relevance filter that uses the LLM itself as the retriever:
instead of dense embeddings, it asks the model to judge each chapter's
relevance to each question, then answers from the **full text** of the kept
chapters. The `--verdicts {2,3,10,100,5d}` switch selects the classification
granularity — two-level (`yes`/`no` → Filter2), three-level
(`yes`/`maybe`/`no` → Filter3, the default), eleven-level (integer 0–10 →
Filter10, Phase 1 only), 101-level (integer 0–100 → Filter100, Phase 1 only),
or five-axis (five integers 0–10 → Filter5d, Phase 1 only). Full details — the
two-phase algorithm, I/O and verdict files, the failure-mode analysis, the
score-distribution / threshold-sweep findings, the multi-axis decomposition,
and the verdict on where the LLM-as-retriever lands relative to Vector RAG —
are in [FILTER.md](FILTER.md).

## `answer_ceiling.py`

Not a retrieval strategy at all — the gold `chapters` from
`questions-<lang>.jsonl` are fed verbatim as context, so there is no Phase 1,
no index, and no retrieval step. Every loss under Ceiling is a pure
**synthesis** loss (the model held the right chapters and still mis-read or
mis-synthesized), which makes it the **perfect-retrieval ceiling**: the upper
bound the retrieval strategies (Vector, Extract, Filter) chase, and the cleanest
measure of the answer model's reading comprehension in isolation from
retrieval quality.

Where the retrieval methods answer *"which chapters should the answerer
see?"*, Ceiling answers *"given the right chapters, how well does the model
read and synthesize?"* Its chapter recall and precision are both 1.0 by
construction (the context *is* the gold set), so any gap between Ceiling's
accuracy and a retrieval method's accuracy on the same question traces
entirely to that method's retrieval, not to the answer model.

**Algorithm**

1. Load the gold `chapters` for each question from `questions-<lang>.jsonl`.
2. Concatenate the **full chapter text** of those chapters with `[Chapter N]`
   labels (same context shape as Filter's Phase 2).
3. Prompt the model to answer in the target language using only that context.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level — supplies the
  gold `chapters`) and `../all/<lang>-gemini.jsonl` (scenes — the full chapter
  text).
- **Output**: `results-<lang>/ceiling.jsonl` — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `expanded` — the gold chapter numbers, as `["5", "10", ...]` strings
  - `answer` — the model's answer

Resume-safe: re-running skips question IDs already present in the output file.

### Relation to the disagreement analysis

The pairwise disagreement analysis in [`report.py`](#reportpy) splits each
off-diagonal loss into **missed context** (a gold chapter never reached the
answerer) vs. **synthesis** (the answerer held every gold chapter yet still
mis-synthesized). Ceiling's losses are synthesis by definition — its
`expanded` is always exactly the gold set — so comparing a retrieval method
against Ceiling directly exposes that method's retrieval misses: every
question where Ceiling wins and the loser's `dropped` set is non-empty is a
chapter the retrieval step failed to surface, while a Ceiling loss (Ceiling
`incorrect` but the retrieval method `correct`) would indicate the extra
context the retriever surfaced actually helped more than the gold set alone.

## `answer_hybrid.py`

The Phase 2 QA realization of the **Union** approach proven in
[HYBRID.md](HYBRID.md): the retrieval analysis showed fusing dense + BM25 into
a single ranking (RRF/Borda/CombSUM) underperforms dense alone at k=5, while
taking the set-theoretic **union** of the two retrievers' top-k chapter sets
beats dense by +4 strict recall at both k=5 (40/50) and k=10 (46/50),
parameter-free. This script turns that retrieval gain into an answer-accuracy
measurement — does surfacing +4 gold chapters actually improve the answer, or
does the ~1.4× larger context cause "lost in the middle" synthesis failures
that offset it?

It mirrors [`answer_vector.py`](#answer_vectorpy) almost exactly — the only
difference is the retrieval step runs **both** retrievers and unions their hits
before the same ±N expansion and answering:

1. Embed the question (dense) and tokenize it (BM25).
2. Retrieve dense top-k scenes and BM25 top-k scenes.
3. **Union** the two hit sets (set-theoretic, deduped by scene).
4. Expand each hit by ±N scenes within its chapter; merge overlapping ranges
   (reusing [`answer_vector.expand_and_merge`](#answer_vectorpy)).
5. Build a context block with `[Chapter N, Scene M — Title]` labels and answer
   (reusing [`answer.answer_question`](#answerpy) with Vector RAG's preamble,
   so the only difference from `vector<k>.jsonl` is the retrieved context).

**Tie-breaking matters.** Both retrievers rank scenes with a **stable** sort
(`sorted(range(n), ..., reverse=True)`), matching `bm25.py` / `sweep_vector.py`
/ `hybrid.py` rather than `answer_vector.top_k_search`'s non-stable
`np.argsort()[::-1]`. The [HYBRID.md](HYBRID.md) strict-recall numbers (40/50
@ k=5, 46/50 @ k=10) were measured under the stable tie-break, so the union hit
set must be selected identically here or the +4 retrieval gain may not
reproduce.

- **Input**: `questions-<lang>.jsonl` (50 questions, ROOT-level), the embedding
  index `index-<lang>.safetensors` (dense side), and the raw scene text
  `all/<lang>-gemini.jsonl` + `.tsv` (BM25 side).
- **Output**: `results-<lang>/hybrid<k>.jsonl` (e.g. `hybrid5.jsonl` for the
  default `k=5`, `hybrid10.jsonl` for `-k 10`) — one record per question:
  - `question_id` — 1-origin line number in the input file
  - `hits` — per-retriever top-k as `{"dense": {...}, "bm25": {...}}` (cosine
    and BM25 scores are on incompatible scales, so they are kept separate
    rather than fused into one dict)
  - `expanded` — all scenes included in the context as `"chapter:segment"` strings
  - `answer` — the model's answer
- **English only**: BM25 tokenization is English-only (lowercase + `[a-z0-9]+`
  + stopword removal, no morphology), so `-l ja` exits with an error, matching
  `hybrid.py`. Japanese is deferred.

Resume-safe: re-running skips question IDs already present in the output file.
The k-aware filename mirrors `vector<k>.jsonl` so the two depths coexist;
`judge-hybrid<k>.jsonl` follows automatically.

### Pipeline integration

Hybrid is built into the default English pipeline via `make judge` (the
aggregate conditionally adds `judge-hybrid5.jsonl` / `judge-hybrid10.jsonl`
when `LANG=en`, so `make ja` is unaffected). [`report.py`](#reportpy)
auto-discovers `hybrid<k>.jsonl` with a matching judge file into a `Hybrid k=<k>`
row, placed after the Vector variants and before Extract — so the union sits
beside its dense-only peer as a direct retrieval comparison. Run
`make hybrid` (k=5, the default) or `make hybrid K=10` to build just the answer
file, or `make hybrid-judge` for both depths plus their judgements.

### Relation to the retrieval analysis

The retrieval coverage (40/50 strict @ k=5, 46/50 @ k=10) is the upper bound on
what Hybrid Phase 2 can score — an answer cannot benefit from a chapter the
retriever surfaced if the answerer then mis-synthesizes it. The gap between
Hybrid's retrieval coverage and its Phase 2 accuracy is the **synthesis cost**
of the ~1.4× larger context (~24 expanded scenes vs dense's ~17 at k=10). Per
[FILTER.md](FILTER.md), Ceiling = 0.990 shows over-inclusion is harmless on the
*gold* set, but Hybrid feeds a 11-chapter union rather than the ~1.7
gold-chapter average — the Phase 2 run is the empirical test of whether that
larger non-gold context triggers "lost in the middle" failures. See
[HYBRID.md § Context size](HYBRID.md#context-size-with-±n-expansion) for the
expansion counts.

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
  `results-en/vector5.jsonl` → `results-en/judge-vector5.jsonl`), one record per question:
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

This still yields a useful inference. Vector structurally **blocks** any context
vector search deems irrelevant, whereas Extract reads every chapter — an
independent thorough-reading path, like the gold's full-context reading. So if
**Extract ≥ Vector**, two independent thorough readers agree with the gold, which
is convergent evidence that the gold answers are sound. If Extract < Vector, that
is a signal to suspect either the gold or the extraction.

Because both methods are judged against the *same* gold, any systematic gold
bias cancels in the relative comparison; it only distorts the rare case where a
method surfaces a true fact the gold omitted. Spot-check the `partial` /
`incorrect` verdicts (few in number) using the gold `rationale`'s chapter
citations.

## `report.py`

Aggregates the existing result files into one comparison table on the terminal,
then appends a pairwise disagreement analysis. Pure mechanical aggregation — no
LLM calls, no output file.

**Two independent axes**, one (method, scope) row each:

1. **Answer accuracy** (from `judge-<method>.jsonl`): raw
   `correct`/`partial`/`incorrect` counts + weighted score
   `(correct + 0.5·partial) / total`.
2. **Chapter retrieval** (each method's `expanded` vs the gold `chapters`):
   **recall** (1 if `gold ⊆ used` else 0, meaned) and **precision**
   (mean `|gold ∩ used| / |used|`). Vector entries are `"chapter:segment"`;
   Extract entries are bare `"chapter"`.

Both axes are broken down by gold `type` (`all` / `single` / `cross`).

**Method discovery**: rows are auto-discovered from the results directory. Each
`vector<k>.jsonl` with a matching `judge-vector<k>.jsonl` becomes a row —
labelled `Vector k=<k>` (e.g. `vector5.jsonl` → `Vector k=5`,
`vector10.jsonl` → `Vector k=10`) — and `hybrid<k>.jsonl` with a matching
`judge-hybrid<k>.jsonl` becomes `Hybrid k=<k>`. Then Extract, then Filter2,
then Filter3, then Ceiling, are appended when both their files exist. Rows are
ordered: `Vector k=5`, then `Vector k=<k>` by ascending `k`, then
`Hybrid k=<k>` by ascending `k`, then Extract, then Filter2, then Filter3,
then Ceiling — so a newly judged retrieval depth or a new per-chapter method
appears with no code change, the union sits beside its dense-only Vector peer,
the stricter two-level filter sits ahead of its looser three-level counterpart,
and Ceiling anchors the table last as the perfect-retrieval upper bound that
strips out retrieval entirely.

### Pairwise disagreement analysis

When at least two methods are available, a second pass compares **every pair**
of methods question-by-question. For each pair it prints a 3×3 verdict agreement
matrix and, for every question where one method is strictly better than the
other, the **loss class** of the loser:

- **missed context** — a gold chapter is absent from the loser's `expanded`, so
  it never reached the answerer at all. For Extract this is a **Phase 1 false
  negative** (a wrong `None` dropped the chapter); for Filter a **wrong
  `no` verdict** (same shape, different cause — see
   [`answer_filter.py`](#answer_filterpy)); for Vector it is a **retrieval miss**
  (the chapter ranked outside the top-k).
- **synthesis** — the loser held every gold chapter yet still mis-synthesized
  the answer.

This splits each off-diagonal loss into its true lever: retrieval/filtering vs.
answering. The summary line rolls the counts up, e.g. *"Vector k=10 beats
Extract on 10 (7 missed-context, 3 synthesis); Extract beats Vector k=10 on 3
(3 missed-context, 0 synthesis)."* See the case study's [Extract-vs-Vector-k=10
section](results-en/README.md#extract-vs-vector-k10-where-each-method-loses) for
the reading.

## `sweep_vector.py`

Standalone retrieval-tuning script (no LLM, no output file — terminal tables
only). It uses the gold `chapters` as a relevance label and re-embeds each
question against the **full** index (all scenes, not just top-5) to ask:
**at what rank/similarity do the gold chapters actually appear?** This is the
lever the [case study](results-en/README.md#both-wrong-what-k10-cannot-fix)
points to for the questions Vector still misses. Reuses `load_index` /
`embed_query` from `answer_vector.py`.

For each question it records the full cosine ranking and where each gold
chapter first appears, then prints three tables:

1. **Chapter coverage@k** — fraction of gold chapters with a scene in the
   top-k (k = 1…82), broken down by `type`. Shows whether `k=5` is generous or
   tight.
2. **Cosine threshold sweep** — pooling `scene.chapter ∈ gold` as positives,
   sweep τ ∈ [0.2, 0.8] for P/R/F1; best `τ*` tests whether a global cutoff
   can separate relevant from irrelevant scenes.
3. **Per-question ranks + separation gap** — first gold rank, best gold-chapter
   score, and the gap to the next non-gold hit. Questions whose first gold hit
   lands outside k=5 are flagged (`*`) — the retrieval misses behind Vector's
losses.

### Findings

English run (Japanese within ±0.02). The sweep reproduces report.py's
strict-recall at k=5 exactly (0.720 / 1.000 / 0.440) and pins down why cross is
the frontier:

- **k=5 is tight for cross.** Single coverage hits 1.00 at k=4; cross only
  reaches 0.71 at k=5, 0.86 at k=10, 0.93 at k=15 — bumping `-k` toward ~10–15
  would surface most dropped cross chapters.
- **A global cosine threshold is a poor lever.** Best `τ*≈0.50` (F1 0.38) —
  dense cosine barely separates gold scenes from topically-similar non-gold
  ones, so **rank (k), not score, is the lever.** Motivation for the BM25
  hybrid in [HYBRID.md](HYBRID.md).
- **Per-question gaps confirm the case study.** The 6 Vector retrieval misses
  (Q27, 28, 31, 36, 43, 45; plus Q49) all rank gold >5 with gaps of just
  +0.00–+0.07.

### Note on the two "recall" notions

`report.py` uses **strict subset recall** (1 iff `gold ⊆ used`) — a
per-question pass/fail. `sweep_vector.py` reports **partial coverage** — the
fraction of gold chapters in the top-k — because the goal is the coverage-vs-k
*curve*. The two agree only at coverage = 1.0.

## `bm25.py`

Standalone BM25/lexical retrieval script (no LLM, no output file — terminal
tables only). Sibling of [`sweep_vector.py`](#sweep_vectorpy): same scene unit, same
gold-coverage lens, but ranks scenes by **Okapi BM25** on the literal scene
text instead of cosine on the dense embedding index. Pure stdlib (`re` +
`collections` + `math`), k1=1.5, b=0.75 (standard Okapi defaults); English-only
tokenization (lowercase + `[a-z0-9]+` + stopword removal), so Japanese is
deferred. The ranking functions (`BM25Index`, `rank_all_scenes`, `tokenize`)
are importable so [`hybrid.py`](#hybridpy) reuses them without reimplementing.

Read alongside `sweep_vector.py` to answer the question —
does sparse lexical matching recover the chapters dense retrieval drops (the
low-frequency proper nouns embeddings wash out)? **It does:** BM25 recovers
6/7 of dense's top-5 misses at k≤5, 7/7 at k≤10 — the orthogonal-failure
precondition for a hybrid. But the two retrievers also share 4 blind spots
neither can reach. Full findings, the five-table breakdown, and the fusion
analysis are in [HYBRID.md](HYBRID.md).

## `hybrid.py`

Standalone fusion analysis script (no LLM, no output file — terminal tables
only). Fuses the dense (cosine) ranking from [`sweep_vector.py`](#sweep_vectorpy) and
the BM25 ranking from [`bm25.py`](#bm25py) via several strategies — **RRF**
(rank-blend, reciprocal decay), **Borda** (rank-blend, linear decay), and
**CombSUM** (normalized score-sum) — and compares against the per-k **Union
oracle** (the set-theoretic upper bound). Needs the dense index (ollama embed
for the query side) and the raw scene text (BM25 side); English only.

The verdict: **fusing into a single ranking does not beat dense alone at k=5**
(RRF suppresses more hits than it recovers), and the RRF parameter sweep's
gains are overfit to the 50-question test set. The robust win is the Union —
running both retrievers independently and taking the union of their top-k
chapters — which scores 40/50 (k=5) and 46/50 (k=10) with no tunable
parameters. Four questions remain unrecoverable by either retriever. Full
analysis in [HYBRID.md](HYBRID.md).

## Out of scope

Directions explicitly not pursued (see [HYBRID.md](HYBRID.md) and
[FILTER.md](FILTER.md) for the analyses behind these boundaries):

- **Whole-text-in-context baselines with cloud models.**
- **Opening the 4 shared blind spots** (Q31 Ch22, Q32 Ch15, Q38 Ch32, Q42 Ch23
  — gold chapters that both dense and BM25 rank outside the top-10; see
  [HYBRID.md § Shared blind spots](HYBRID.md#shared-blind-spots)). No blend of
  the two retrievers reaches them — opening them needs a different retrieval
  mechanism (query expansion or multi-query), not a better blend. The
  five-axis Filter does surface them but at a precision (0.120) that makes it
  impractical ([FILTER.md](FILTER.md)).

## `ref/`

Reference material kept for convenience, not part of the pipeline.

- [ref/example.py](ref/example.py) — minimal usage example of the ollama
  `embed()` API, with EmbeddingGemma prompt conventions noted in the comments.
