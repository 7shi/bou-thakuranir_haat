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

| Method | English | Japanese | Description |
| --- | --- | --- | --- |
| Vector k=5 | 39/50 (0.830) | 38/50 (0.810) | Standard dense vector search (k=5) |
| Vector k=10 | 44/50 (0.920) | 42/50 (0.890) | Standard dense vector search (k=10) |
| Vector-line k=5 | 35/50 (0.800) | 35/50 (0.790) | Line-level dense vector search (k=5) |
| Vector-line k=10 | 41/50 (0.890) | 40/50 (0.840) | Line-level dense vector search (k=10) |
| V-hybrid k=5 | 40/50 (0.890) | 42/50 (0.890) | Segment ∪ Line dense union (k=5) |
| V-hybrid k=10 | 43/50 (0.910) | 42/50 (0.880) | Segment ∪ Line dense union (k=10) |
| Hybrid k=5 | 43/50 (0.910) | — | Dense ∪ BM25 union (k=5) |
| Hybrid k=10 | 47/50 (0.960) | — | Dense ∪ BM25 union (k=10) |
| Extract | 39/50 (0.830) | 40/50 (0.850) | Per-chapter summarization-based extraction |
| Filter2 | 36/50 (0.790) | 39/50 (0.820) | LLM-as-retriever (binary: yes/no) |
| Filter3 | 45/50 (0.930) | 43/50 (0.880) | LLM-as-retriever (ternary: yes/maybe/no) |
| Ceiling | 49/50 (0.990) | 47/50 (0.970) | Perfect-retrieval upper bound (gold chapters directly) |
| GraphRAG local | 28/50 (0.660) | — | Microsoft GraphRAG (local entity search) |
| GraphRAG global | 5/50 (0.170) | — | Microsoft GraphRAG (global community search) |

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
(vector / extract / filter / ceiling / hybrid).

Both languages use the same answer model `google:gemma-4-31b-it`, the same
`embeddinggemma` index, and the same judge.

> [!IMPORTANT]
> **Practical Optimal Solution**
> For English, **Dense ∪ BM25 Union** (`Hybrid k=10`) is the best practical solution, achieving the highest accuracy (**0.960**).
> For Japanese, because BM25 tokenization is currently English-only, plain **Vector k=10** (or `V-hybrid k=5`) serves as the most practical optimal solution at **0.890**.

## Key Findings by Strategy

### Filter (LLM-as-Retriever) — [FILTER.md](FILTER.md)

Filter (LLM-as-retriever), English, at each variant's keep rule:

| method | strict recall |
|---|---:|
| Filter2 (keep yes) | 30 |
| Filter3 (keep ≠ no) | 44 |
| Filter10 (≥3) | 38 |
| Filter5d (sum ≥5) | 50 |

* **No Practical Advantage:** LLM-as-retriever does not justify its cost over Vector RAG.
* **Granularity and Floor Limits:** Single-axis variants (Filter2/3/10) leave a "gold floor" (8–12% of gold chapters unrecoverable due to wrong "no" verdicts). Multi-axis scoring (Filter5d) eliminates the floor but only by keeping ~14 chapters per question, destroying precision.
* **Inefficient Scaling:** The practical numerical variant, Filter10, only matches Vector k=10 recall but demands ~1,850 Phase 1 LLM calls per language vs. a single embedding pass—hundreds of times the runtime.

### Hybrid (Dense + BM25) — [HYBRID.md](HYBRID.md)

Dense ∪ BM25 (HYBRID), English:

| method | k=5 | k=10 |
|---|---:|---:|
| Dense | 36 | 42 |
| BM25 | 33 | 41 |
| RRF | 32 | 43 |
| Borda | 33 | 43 |
| CombSUM | 35 | 42 |
| **Union** | 40 | **46** |

* **Don't Fuse — Union:** Rank-fusion algorithms (RRF, Borda, CombSUM) suppress more hits than they recover, underperforming dense-only at k=5. Taking the set-theoretic union of independent dense and BM25 top-k sets is parameter-free, robust, and wins (+4 strict recall at both depths).
* **Dense-Blind Recovery:** BM25 lexical matching recovers nearly all proper-noun/distinctive terms (Class A misses like the signet ring or Delhi petition) that dense embedding fails to rank.
* **Shared Blind Spots:** Four cross-reference questions (Q31, Q32, Q38, Q42) remain unrecoverable by both retrievers, requiring query expansion or multi-query techniques instead of a better blend.

### Segment ∪ Line Dense Hybrid (`V-hybrid`) — [VECTOR-HYBRID.md](VECTOR-HYBRID.md)

Segment ∪ Line (VECTOR-HYBRID), en / ja:

| method | en k=5 | en k=10 | ja k=5 | ja k=10 |
|---|---:|---:|---:|---:|
| Segment (= Dense) | 36 | 42 | 36 | **45** |
| Line | 33 | 39 | 31 | 38 |
| Mix | 32 | 36 | 32 | 38 |
| **Union** | 38 | **45** | 41 | **45** |

* **Granularity Union:** Unioning segment-level and line-level dense retrieval improves strict recall. Line search recovers distinctive single lines, while segment search handles diffuse context.
* **Budget Trade-off:** However, at a matched context budget (V-hybrid k=5 vs Vector k=10), V-hybrid does not outperform the plain single-index retriever. The retrieval gains are offset by synthesis regressions ("lost in the middle") due to larger context.

### Case Studies & Language Comparison — [results-en/README.md](results-en/README.md) & [results-ja/README.md](results-ja/README.md)

* **Retrieval is the Frontier:** Single-passage QA is essentially solved. The remaining difficulty lies entirely in cross-reference questions.
* **Ceiling Verification:** The Ceiling run (gold chapters verbatim) scores 0.990 (en) and 0.970 (ja), proving that given the correct context, LLM comprehension is near-perfect. Q48 remains the lone synthesis floor.
* **Extract Failures:** Extract’s losses are predominantly Phase 1 false negatives (where the summary drops the gold chapter) rather than synthesis errors.
* **Language Invariance:** Language makes negligible difference to accuracy (EN and JA totals match within 1-2 questions). Retrieval misses are identical because they share the same embedding model.

### GraphRAG — [graphrag/README.md](graphrag/README.md)

* **Synthesis Collapse:** GraphRAG local (0.660) falls below flat retrieval. While recall is high (0.860), precision collapses (0.135), overloading the context and causing synthesis failure.
* **Structural Strengths:** It excels at answering entity-relationship arcs (answering Q26/Q28 with zero context passages) and resolves Class A questions through graph traversal.
* **Global Search Failure:** Global community summaries are too abstract (0.170) for passage-level QA.
* **Extreme Cost:** Building the graph and running queries takes over 13 hours—impractical compared to minutes for flat vector indexing.

## Overall Conclusions and Practical Takeaways

1. **Evaluation Collapses to Retrieval:** The `Ceiling` run proves that as long as the correct chapters are included in the context, the model can generate answers with high accuracy. Therefore, improving a QA system is almost entirely equivalent to improving retrieval recall.
2. **Don't Fuse — Union:** When combining different retrievers (e.g., Dense and BM25, or Segment and Line), algorithms that blend scores into a single ranking (like RRF) often push correct answers out. Taking the set-theoretic union of their individual top-k results is the safest and most effective approach.
3. **Divergence in Optimal Strategy by Language:**
   * **English:** `Hybrid k=10` (Dense ∪ BM25 Union) is the best approach, scoring 0.960. It effectively breaks the limitations of pure dense retrieval and comes closest to the Ceiling.
   * **Japanese:** Since BM25 sparse matching is not available, the optimal solution is the simpler **Vector k=10** (0.890). More complex methods like `V-hybrid` do not outperform plain `Vector k=10` under a matched context size budget.

## Pipeline (`Makefile`)

The build pipeline is wired via `Makefile`. For detailed target descriptions, usage, options (such as `LANG`, `LINE`, and `K`), and opt-in strategies, please refer directly to the comments in [Makefile](Makefile).

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
