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
`(correct + 0.5·partial) / 50` in parentheses. **Vector** (`k=5`/`k=10`),
**Vector-line**, **V-hybrid**, **Filter2**, **Filter3**, and **Ceiling** have been
run for both languages; **Hybrid** is English only (BM25 tokenization is
English-only).

| Method | English | Japanese |
| --- | --- | --- |
| Vector k=5 | 39/50 (0.830) | 38/50 (0.810) |
| Vector k=10 | 44/50 (0.920) | 42/50 (0.890) |
| Vector-line k=5 | 35/50 (0.800) | 35/50 (0.790) |
| Vector-line k=10 | 41/50 (0.890) | 40/50 (0.840) |
| V-hybrid k=5 | 40/50 (0.890) | 42/50 (0.890) |
| V-hybrid k=10 | 43/50 (0.910) | 42/50 (0.880) |
| Hybrid k=5 | 43/50 (0.910) | — |
| Hybrid k=10 | 47/50 (0.960) | — |
| Extract | 39/50 (0.830) | 40/50 (0.850) |
| Filter2 | 36/50 (0.790) | 39/50 (0.820) |
| Filter3 | 45/50 (0.930) | 43/50 (0.880) |
| Ceiling | 49/50 (0.990) | 47/50 (0.970) |
| GraphRAG local | 28/50 (0.660) | — |
| GraphRAG global | 5/50 (0.170) | — |

The pipeline behind these rows — build the index, answer each question, grade,
aggregate (Filter and Ceiling are opt-in):

- `build_index.py` — scene embedding index → `index-<lang>.safetensors`
- `answer_vector.py` — Vector k=5/10, Vector-line (`--line`), and V-hybrid (`--hybrid`, segment ∪ line dense Union; see [VECTOR-HYBRID.md](VECTOR-HYBRID.md)) → `results-<lang>/vector[-line|-hybrid]<k>.jsonl`
- `answer_extract.py` — Extract → `results-<lang>/extract.jsonl`
- `answer_filter.py` — Filter2 / Filter3 (LLM as retriever; see [FILTER.md](FILTER.md)) → `results-<lang>/filter{2,3}.jsonl`
- `answer_hybrid.py` — Hybrid k=5/10 (dense ∪ BM25; see [HYBRID.md](HYBRID.md)) → `results-<lang>/hybrid<k>.jsonl`
- `answer_ceiling.py` — Ceiling, gold chapters as context → `results-<lang>/ceiling.jsonl`
- `judge.py` — LLM grading of answers vs. gold → `results-<lang>/judge-<stem>.jsonl`
- `report.py` — accuracy + chapter retrieval comparison + pairwise disagreement analysis (terminal table)

`answer.py` holds the shared helpers (`LANGS`, `PART_RANGES`, `load_questions`,
`load_chapters`, `answer_question`) imported by all five answer scripts
(vector / extract / filter / ceiling / hybrid). The standalone retrieval-analysis
scripts (no LLM) are indexed under [Retrieval analyses](#retrieval-analyses).

Both languages use the same answer model `google:gemma-4-31b-it`, the same
`embeddinggemma` index, and the same judge.

**Retrieval depth is the main lever; language barely matters.** At `k=5`,
Vector and Extract sit within two questions in both languages (English 0.830;
Japanese 0.810 vs 0.850). Bumping Vector to `k=10` lifts English 0.830 → 0.920
and Japanese 0.810 → 0.890 — most of the gain is simply deeper retrieval, as
[`sweep_vector.py`](sweep_vector.py) predicted. What `k=10` *cannot* fix is
**dense-retrieval blindness**: load-bearing cross-reference chapters that rank
outside the top-10 in the embedding at both depths.

**English — the dense ∪ BM25 union (Hybrid) is the practical best.** Running
dense and BM25 independently and taking the set-theoretic union of their top-k
chapters reaches **0.960** at `k=10`, recovering the lexically-distinctive
cross-reference chapters dense embedding alone cannot rank. Don't fuse the
rankings (RRF/Borda/CombSUM all underperform dense at `k=5`) — union. Full
retrieval analysis and per-question breakdown in [HYBRID.md](HYBRID.md) and
[results-en/README.md](results-en/README.md#hybrid-dense--bm25-union).

**The dense-only variants don't pay off.** `Vector-line` (one vector per line)
and `V-hybrid` (segment ∪ line dense union) both trade chapter precision for
recall and net out at or below segment Vector `k=10` in both languages — the
strict-recall gain over Vector `k=5` is a depth effect that single-index Vector
`k=10` reaches on its own, without the second index, and neither reaches the
dense-blind chapters that only the lexical Hybrid recovers. Details in
[VECTOR-HYBRID.md](VECTOR-HYBRID.md), with per-question breakdowns for
[Vector-line](results-en/README.md#vector-line-line-level-retrieval) and
[V-hybrid](results-en/README.md#v-hybrid-segment--line-dense-union)
([Japanese](results-ja/README.md#v-hybrid-segment--line-dense-union)).

**Filter (LLM-as-retriever) is impractical regardless of score.** Asking the
model to judge every chapter's relevance costs **~1,850 LLM calls per language**
in Phase 1 (37 chapters × 50 questions) against Vector's single embedding +
cosine pass — hundreds of times the runtime. English Filter3 posts a high 0.930
and Japanese 0.880, but it still trails English Hybrid `k=10` (0.960) and only
ties Vector `k=10` in Japanese, so the score never justifies the cost. Full
analysis and verdict in [FILTER.md](FILTER.md); per-question detail in the case
studies ([English](results-en/README.md) · [Japanese](results-ja/README.md)).

**Ceiling is a reference upper bound, not a usable method.** It feeds the gold
chapters verbatim as context — i.e. it works backwards from the known answer and
retrieves nothing, so it cannot run in production; its only purpose is to pin the
frontier. English **0.990** (49 correct, one partial, zero incorrect) and
Japanese **0.970** sit above every retrieval method, and the gap to each is the
pure cost of that method's retrieval. Because the model reads the gold chapters
nearly perfectly in both languages, **the frontier is retrieval, not
comprehension** (the lone English residual, Q48, is the single true synthesis
floor). See the
[Ceiling case study](results-en/README.md#ceiling-the-perfect-retrieval-upper-bound).

**GraphRAG (local/global) does not match the pipeline on this task overall.**
GraphRAG excels at structural queries ("how does this relationship evolve?");
questions here mostly require specific microdetail from individual chapters —
a granularity the entity/relationship graph abstracts away. GraphRAG local posts
0.660 (28/50) — below Filter2 (0.790). Entity-graph expansion pulls in most
chapters (recall 0.860), but precision collapses to 0.135 and the answerer
drowns in noise: **16 of its 21 losses to Ceiling are synthesis**. Where the
graph does help — questions about character arcs and narrative causality — it
sometimes answers correctly with zero chapters retrieved (pure graph traversal),
and it independently recovers the Class A questions Q31/Q49 that dense embedding
cannot rank. It never beats Hybrid k=10 overall. GraphRAG global (0.170, 5/50)
is non-functional: community summaries are too abstract for passage-level QA
(37 of 45 losses are missed context). See [graphrag/README.md](graphrag/README.md)
and the [GraphRAG section](results-en/README.md#graphrag) of the English case
study.

**Practical solution.** Setting aside Filter (too slow) and Ceiling (a
back-computed upper bound, not a real retriever), the realistic best is **Hybrid
(BM25 + Vector union) for English** and **Vector `k=10` for Japanese**: BM25
tokenization is English-only, so the union is unavailable in Japanese, and there
Vector `k=10` (0.890) ties the best Japanese retriever (V-hybrid `k=5`) at the
lowest cost and complexity — a single index, one embedding pass, no second
model.

## Retrieval analyses

Three standalone studies measure **retrieval strict recall** (gold ⊆ top-k, out
of 50 questions) — the upper bound on Phase 2 QA, since Ceiling = 0.990 means a
surfaced gold chapter almost always converts. All three share the same
**Vector / dense-segment baseline** (36 @ k=5, 42 @ k=10, English) and the same
**Ceiling** (50/50), so their tables line up on one axis.
[`sweep_vector.py`](sweep_vector.py) supplies that dense baseline (depth/threshold
sweep); each study below adds one retrieval idea on top of it.

Filter (LLM-as-retriever), English, at each variant's keep rule:

| method | strict recall |
|---|---:|
| Filter2 (keep yes) | 30 |
| Filter3 (keep ≠ no) | 44 |
| Filter10 (≥3) | 38 |
| Filter5d (sum ≥5) | 50 |

**[FILTER.md](FILTER.md)** — does the LLM judging each chapter's relevance beat
dense retrieval? **No practical advantage**: the floor-vs-excess trade-off is a
hard limit, and Filter3's 0.930 Phase 2 tops Vector k=10 (0.920) by one question
at ~1,850× the cost. (The answering script `answer_filter.py` is listed under
[Results](#results).)

- **[filter.py](filter.py)** — single-axis score-distribution / threshold-sweep
  / filter2-3-vs-filter10 crosstab. → scores bimodal (91% score 0), F1 peak at
  threshold 3, gold floor 7/86; one Filter10 run reproduces every variant.
- **[filter5d.py](filter5d.py)** — five-axis relevance decomposition. → floor
  eliminated (0/86) at sum ≥5, but ~14 chapters/question (precision 0.12):
  floor-0 and a tight keep set are mutually exclusive.

Dense ∪ BM25 (HYBRID), English:

| method | k=5 | k=10 |
|---|---:|---:|
| Dense | 36 | 42 |
| BM25 | 33 | 41 |
| RRF | 32 | 43 |
| Borda | 33 | 43 |
| CombSUM | 35 | 42 |
| **Union** | 40 | **46** |

**[HYBRID.md](HYBRID.md)** — does combining sparse lexical (BM25) and dense
semantic retrieval recover the chapters each alone drops? **Don't fuse — union**:
rank-fusion underperforms dense at k=5; the set-theoretic union wins (40/50 @ k=5,
46/50 @ k=10, +4 parameter-free). Four shared blind spots remain.

- **[bm25.py](bm25.py)** — Okapi BM25 sparse-lexical gold-coverage analysis
  (sibling of sweep_vector.py). → 33/50 → 41/50; recovers 6/7 dense misses at
  k≤5, 7/7 at k≤10 (orthogonal failures, the hybrid precondition).
- **[hybrid.py](hybrid.py)** — dense+BM25 fusion (RRF/Borda/CombSUM) vs. the
  union oracle. → no fusion beats dense at k=5 (RRF: 0 pure wins, 9
  suppressions); union is the robust winner.

Segment ∪ Line (VECTOR-HYBRID), en / ja:

| method | en k=5 | en k=10 | ja k=5 | ja k=10 |
|---|---:|---:|---:|---:|
| Segment (= Dense) | 36 | 42 | 36 | **45** |
| Line | 33 | 39 | 31 | 38 |
| Mix | 32 | 36 | 32 | 38 |
| **Union** | 38 | **45** | 41 | **45** |

**[VECTOR-HYBRID.md](VECTOR-HYBRID.md)** — does line-level retrieval recover the
chapters segment-level drops, using the same cosine? en + ja. **Union helps**
(en 38/50, ja 41/50 @ k=5 vs the 36 baseline); **mix-and-sort hurts**; line is
valuable only inside the union.

- **[hybrid-vector.py](hybrid-vector.py)** — segment vs line vs mix vs union
  gold-coverage measurement (print-only, en + ja). → Union(B) beats Segment at
  every k in both languages; Mix(A) drops below Segment (32/50); misses are
  orthogonal.

## Languages

Every script takes `-l/--lang {en,ja}` (default `en`), which selects the
language-specific defaults in one switch: the gold questions
(`questions-<lang>.jsonl`), scene sources (`all/<lang>-gemini.jsonl` /
`all/<lang>-gemini.tsv`), the index (`index-<lang>.safetensors`), the output
directory (`results-<lang>/`), and the answer language. The individual path
options (`-i`/`-o`/`--index`/`--scenes`/`-t`) still override these defaults.

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
