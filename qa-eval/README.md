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
`(correct + 0.5·partial) / 50` in parentheses. **Vector-line** and **V-hybrid**
have been run for both languages; Vector `k=10`, **Hybrid**, **Filter2**,
**Filter3**, and **Ceiling** are English only (Japanese pending).

| Method | English | Japanese |
| --- | --- | --- |
| Vector k=5 | 39/50 (0.830) | 38/50 (0.810) |
| Vector k=10 | 44/50 (0.920) | — |
| Vector-line k=5 | 35/50 (0.800) | 35/50 (0.790) |
| Vector-line k=10 | 41/50 (0.890) | 40/50 (0.840) |
| V-hybrid k=5 | 40/50 (0.890) | 42/50 (0.890) |
| V-hybrid k=10 | 43/50 (0.910) | 42/50 (0.880) |
| Hybrid k=5 | 43/50 (0.910) | — |
| Hybrid k=10 | 47/50 (0.960) | — |
| Extract | 39/50 (0.830) | 40/50 (0.850) |
| Filter2 | 36/50 (0.790) | — |
| Filter3 | 45/50 (0.930) | — |
| Ceiling | 49/50 (0.990) | — |

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

**Retrieval strategy is the lever; language barely is.** At `k=5`, Vector and
Extract tie on English (0.830) and sit within two questions on Japanese (0.810
vs 0.850) — the language makes almost no difference. The main lever is
retrieval depth: **bumping Vector to `k=10`** (English) lifts 0.830 → 0.920,
exactly what [`sweep_vector.py`](sweep_vector.py) predicted (`k=5` was tight; deeper
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

**The segment ∪ line dense union (`V-hybrid`) converts that orthogonality into
accuracy — and is the top *Japanese* method.** Unioning the segment and line
top-k (`answer_vector.py --hybrid`; the same union idea as Hybrid, but two
same-model cosines instead of dense + BM25, so no second model and both
languages) scores 0.890 / 0.910 (English) and 0.890 / 0.880 (Japanese). In
English it nearly eliminates wrong answers (k=5: 1 incorrect vs Vector k=5's 6)
and lifts cross-reference chapter recall to 0.800 at k=10, but lands between
segment Vector k=10 (the wider union context costs two synthesis losses) and the
lexical Hybrid (which alone reaches the dense-blind [Class
A](results-en/README.md#both-wrong-what-k10-cannot-fix) chapters that no dense
granularity can rank). In **Japanese**, where no BM25 hybrid exists, V-hybrid k=5
(0.890) is the strongest retriever outright — above Extract (0.850) and every
Vector variant — because the larger Japanese union gain (+5 / +7 strict recall)
converts directly to answers. See [VECTOR-HYBRID.md](VECTOR-HYBRID.md) and the
per-question breakdowns:
[English](results-en/README.md#v-hybrid-segment--line-dense-union) ·
[Japanese](results-ja/README.md#v-hybrid-segment--line-dense-union).

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
