# QA evaluation pipeline. Models are left to each script's default.
#
# Real file targets drive the dependency chain; .PHONY names wrap them as
# convenient aliases. Per-language flow (LANG=en|ja):
#   index -> vector + extract -> judge -> report
#
# Filter (per-chapter relevance) is OPT-IN: run `make filter2` (the two-level
# yes/no variant) or `make filter3` (the default three-level yes/maybe/no
# variant) after the default pipeline to add a per-chapter retrieval strategy
# to the comparison. Neither is part of `make`, `make all`, or `make <lang>`
# because Phase 1 costs ~1,850 LLM calls per language.
#
# Ceiling (gold chapters as context, no retrieval) is likewise OPT-IN: run
# `make ceiling` to establish a perfect-retrieval ceiling that isolates the
# answer model's reading comprehension. It costs only ~50 calls (no Phase 1),
# but is kept opt-in to match the experimental posture of Filter.
#
# Usage:
#   make                    # full English pipeline (LANG=en)
#   make ja                 # full Japanese pipeline
#   make all                # both languages
#   make report             # build whatever is missing, then print the table
#   make LANG=ja vector     # individual steps for one language
#   make filter2            # opt-in: per-chapter yes/no filter (Phase 1 + 2 + judge)
#   make filter3            # opt-in: per-chapter yes/maybe/no filter (Phase 1 + 2 + judge)
#   make filter10-tsv       # opt-in: per-chapter 0-10 score → filter10.tsv (Phase 1 only)
#   make filter100-tsv      # opt-in: per-chapter 0-100 score → filter100.tsv (Phase 1 only)
#   make filter5d-tsv       # opt-in: per-chapter five-axis 0-10 scores → filter5d.tsv (Phase 1 only)
#   make ceiling            # opt-in: gold-chapter context ceiling (answer + judge)
#   make sweep              # retrieval sweep (independent of the pipeline; no LLM)
#   make bm25               # BM25 sparse retrieval gold-coverage analysis (no LLM)
#   make hybrid             # dense ∪ BM25 union QA answering (English only; see hybrid-judge)
#   make hybrid-judge       # hybrid k=5 + k=10 answering + judging → rows in `make report`
#   make filter             # filter10 verdicts + score-distribution analysis (no LLM)
#   make filter SCALE=100   # filter100 occurrence count only (no LLM)
#   make filter5d           # five-axis verdicts + sum/per-axis/floor analysis (no LLM)

LANG    := en
ROOT    := ..
RESULTS := results-$(LANG)

QUESTIONS := $(ROOT)/questions-$(LANG).jsonl
SCENES    := $(ROOT)/all/$(LANG)-gemini.jsonl
TSV       := $(ROOT)/all/$(LANG)-gemini.tsv
# Set LINE=1 for line-level retrieval. It toggles the same `index` / `vector`
# targets (no separate targets): build_index.py --line writes
# index-line-<lang>.safetensors and answer_vector.py --line writes
# results-<lang>/vector-line<k>.jsonl. Unset (default) = segment-level.
#   make index LINE=1        → index-line-<lang>.safetensors
#   make vector LINE=1 K=10  → results-<lang>/vector-line10.jsonl
LINE ?=
ifeq ($(LINE),)
INDEX       := index-$(LANG).safetensors
LINE_FLAG   :=
VECTOR_STEM := vector
else
INDEX       := index-line-$(LANG).safetensors
LINE_FLAG   := --line
VECTOR_STEM := vector-line
endif

PARTS         := 1 2 3 4
EXTRACT_PARTS  := $(patsubst %,$(RESULTS)/extract-%.jsonl,$(PARTS))
# Filter verdict TSVs are single files (one per verdict granularity), not split
# by chapter group — they are small and fast to generate, so the part split that
# Extract uses is unnecessary here. Phase 1 writes filter{V}.tsv (all chapters).
FILTER2_TSV   := $(RESULTS)/filter2.tsv
FILTER3_TSV   := $(RESULTS)/filter3.tsv
FILTER10_TSV  := $(RESULTS)/filter10.tsv
FILTER100_TSV := $(RESULTS)/filter100.tsv
FILTER5D_TSV  := $(RESULTS)/filter5d.tsv

# Relevance scale for the `filter` analysis target: 10 reads filter10.tsv,
# 100 reads filter100.tsv. `make filter SCALE=100` builds filter100.tsv (if
# missing) then runs filter.py --scale 100.
SCALE := 10

# Retrieval depth for the `vector` / `hybrid` targets. Defaults to k=5, whose
# outputs are results-<lang>/vector5.jsonl / hybrid5.jsonl. Set K=10 for the
# k=10 variants.
K ?= 5
VECTOR_FILE := $(RESULTS)/$(VECTOR_STEM)$(K).jsonl
HYBRID_FILE := $(RESULTS)/hybrid$(K).jsonl

.PHONY: en ja all pipeline index vector hybrid vector-hybrid vector-hybrid-judge extract-parts extract filter2-tsv filter2 filter3-tsv filter3 filter10-tsv filter100-tsv filter5d-tsv filter filter5d ceiling judge hybrid-judge report sweep bm25 clean
.DEFAULT_GOAL := en

en:
	$(MAKE) LANG=en pipeline

ja:
	$(MAKE) LANG=ja pipeline

all: en ja

# Full pipeline for one language (report pulls in the whole chain).
pipeline: report

# --- .PHONY aliases for the file targets below ---
index: $(INDEX)
vector: $(VECTOR_FILE)
# Hybrid retrieval (dense ∪ BM25 union) answering — Phase 2 QA of the HYBRID.md
# Union approach. Mirrors `make vector`: the pattern rule derives the output
# filename from k, so `make hybrid` → results-<lang>/hybrid5.jsonl,
# `make hybrid K=10` → results-<lang>/hybrid10.jsonl. English only (BM25
# tokenization is English-only — passing LANG=ja exits with an error from
# answer_hybrid.py). Not part of the default pipeline / `judge` aggregate.
# Note: `make hybrid` previously drove the standalone fusion analysis
# (hybrid.py); that script is now run directly via `uv run hybrid.py -l en`.
hybrid: $(HYBRID_FILE)
# `make hybrid-judge` runs answering at k=5 and k=10 then judges both, so
# Hybrid k=5 / Hybrid k=10 appear in `make report` after a single command.
hybrid-judge: $(RESULTS)/judge-hybrid5.jsonl $(RESULTS)/judge-hybrid10.jsonl
# Segment ∪ line dense Union answering (answer_vector.py --hybrid). Mirrors
# `make vector`: the pattern rule derives the filename from k. Both languages.
# Not part of the default pipeline; plain `make judge` grades any present
# vector-hybrid<k>.jsonl via the wildcard pickup below.
vector-hybrid: $(RESULTS)/vector-hybrid$(K).jsonl
# `make vector-hybrid-judge` answers k=5 and k=10 then judges both, so
# V-hybrid k=5 / V-hybrid k=10 appear in `make report` after a single command.
vector-hybrid-judge: $(RESULTS)/judge-vector-hybrid5.jsonl $(RESULTS)/judge-vector-hybrid10.jsonl
extract-parts: $(EXTRACT_PARTS)
extract: $(RESULTS)/extract.jsonl
filter2-tsv: $(FILTER2_TSV)
# `make filter2` runs the whole opt-in pipeline (Phase 1 + Phase 2 + judge) so
# that Filter2 appears in `make report` after a single command. judge-filter2
# depends on filter2.jsonl which depends on the verdict TSV (filter2.tsv).
filter2: $(RESULTS)/judge-filter2.jsonl
filter3-tsv: $(FILTER3_TSV)
# `make filter3` mirrors `make filter2` for the three-level (yes/maybe/no)
# default variant: Phase 1 + Phase 2 + judge, surfacing Filter3 in `make report`.
filter3: $(RESULTS)/judge-filter3.jsonl
filter10-tsv: $(FILTER10_TSV)
filter100-tsv: $(FILTER100_TSV)
filter5d-tsv: $(FILTER5D_TSV)
ceiling: $(RESULTS)/judge-ceiling.jsonl
# `judge` aggregates the judged answer files for the default pipeline. Hybrid
# (dense ∪ BM25 union) is English-only — answer_hybrid.py exits with an error
# under LANG=ja — so its k=5/k=10 judge files are added to the aggregate only
# when LANG=en. `make` (LANG=en, the default) thus builds Hybrid rows into
# `make report`; `make ja` skips them. `make hybrid-judge` remains a standalone
# alias for the two hybrid judge files.
# The canonical aggregate is the segment vector5 baseline plus extract (and
# Hybrid under LANG=en). It is LINE-independent: `make judge` always grades
# vector5, regardless of LINE.
JUDGE_FILES := $(RESULTS)/judge-vector5.jsonl $(RESULTS)/judge-extract.jsonl
ifeq ($(LANG),en)
JUDGE_FILES += $(RESULTS)/judge-hybrid5.jsonl $(RESULTS)/judge-hybrid10.jsonl
JUDGE_FILES += $(patsubst $(RESULTS)/%.jsonl,$(RESULTS)/judge-%.jsonl,$(wildcard $(RESULTS)/graphrag-*.jsonl))
endif
# Also grade any line-mode answers already produced by `make vector LINE=1`
# (vector-line<k>.jsonl → judge-vector-line<k>.jsonl, via the judge-vector%
# pattern rule). wildcard only matches files already present, so plain
# `make judge` picks them up without needing LINE=1.
JUDGE_FILES += $(patsubst $(RESULTS)/%.jsonl,$(RESULTS)/judge-%.jsonl,$(wildcard $(RESULTS)/vector-line*.jsonl))
# Same wildcard pickup for the segment ∪ line Union (vector-hybrid<k>.jsonl →
# judge-vector-hybrid<k>.jsonl, via the judge-vector% pattern rule). Works for
# both languages; plain `make judge` grades any present without forcing creation.
JUDGE_FILES += $(patsubst $(RESULTS)/%.jsonl,$(RESULTS)/judge-%.jsonl,$(wildcard $(RESULTS)/vector-hybrid*.jsonl))
# Same depth-agnostic pickup for plain segment Vector at non-default depths
# (vector10.jsonl etc.). vector5 duplicates the hardcoded entry above (make
# dedups); the [0-9] right after "vector" excludes vector-line/vector-hybrid.
JUDGE_FILES += $(patsubst $(RESULTS)/%.jsonl,$(RESULTS)/judge-%.jsonl,$(wildcard $(RESULTS)/vector[0-9]*.jsonl))
judge: $(JUDGE_FILES)
sweep: $(INDEX) $(QUESTIONS)
	uv run sweep_vector.py -l $(LANG)

# BM25/lexical retrieval gold-coverage analysis (independent of the pipeline;
# no LLM, no embedding index — reads the raw scene text directly). Ranks scenes
# by Okapi BM25 and reports the same coverage@k / threshold / per-question
# tables as sweep_vector.py, plus a cross-reference of BM25's rank on the known
# dense-retrieval misses. Side-by-side with `make sweep`, answers whether
# sparse lexical matching recovers the gold chapters dense retrieval drops —
# the dense-vs-BM25 question that motivates the hybrid analysis. See bm25.py.
bm25: $(SCENES) $(TSV) $(QUESTIONS)
	uv run bm25.py -l $(LANG)

# Standalone dense+BM25 fusion analysis (hybrid.py — RRF/Borda/CombSUM vs. union
# oracle, terminal tables only, no LLM output) has no `make` alias: `make hybrid`
# now drives the Phase 2 QA (answer_hybrid.py). Run the analysis directly with
# `uv run hybrid.py -l en` (needs the dense index + raw scene text; English only).

# filter{10,100} score-distribution / threshold-sweep analysis (terminal output
# only, no LLM). SCALE selects which verdict TSV to read: 10 → filter10.tsv
# (full eight-table analysis), 100 → filter100.tsv (occurrence count only —
# filter100 is filter10 x10). Depends on the matching target so
# `make filter SCALE=100` generates it if missing, then runs filter.py.
# filter2/3 TSVs are read opportunistically when present (for the crosstab
# tables) but are not required.
filter: filter$(SCALE)-tsv $(QUESTIONS)
	uv run filter.py -l $(LANG) --scale $(SCALE)

# Five-axis relevance score analysis (terminal output only, no LLM). Reads
# filter5d.tsv and prints the sum distribution, threshold sweep, per-axis
# breakdown, and the floor analysis. See FILTER.md.
filter5d: $(FILTER5D_TSV) $(QUESTIONS)
	uv run filter5d.py -l $(LANG)

# Accuracy + chapter retrieval comparison table + pairwise disagreement
# analysis (terminal output only). Needs >= 2 judged methods for the pass.
report: judge
	uv run report.py -l $(LANG)

# --- file targets ---

# Scene embedding indexes. Two explicit named rules (segment / line) rather than
# one $(LINE_FLAG)-parameterized rule, because `vector-hybrid` needs BOTH indexes
# present at once. `make index` still builds just $(INDEX) (segment, or line under
# LINE=1) via the alias above; the vector-hybrid answer rule depends on both.
index-$(LANG).safetensors: $(SCENES) $(TSV)
	uv run build_index.py -l $(LANG)

index-line-$(LANG).safetensors: $(SCENES) $(TSV)
	uv run build_index.py -l $(LANG) --line

# Vector RAG answering.
#   make vector         → results-<lang>/vector5.jsonl   (default k=5)
#   make vector K=10    → results-<lang>/vector10.jsonl  (k=10)
# answer_vector.py derives the output filename from k, so the explicit -o is
# not needed; the pattern rule just passes -k $* (the stem, e.g. "10").
$(RESULTS)/vector%.jsonl: $(INDEX) $(QUESTIONS)
	uv run answer_vector.py -l $(LANG) -k $*

# Line-mode variant (LINE=1). Same `make vector` target, but VECTOR_FILE becomes
# vector-line<k>.jsonl, which this rule builds with --line. Kept as its own
# pattern only because the filename prefix differs; the user-facing target is
# still just `vector`.
$(RESULTS)/vector-line%.jsonl: $(INDEX) $(QUESTIONS)
	uv run answer_vector.py -l $(LANG) --line -k $*

# Segment ∪ line dense Union answering (answer_vector.py --hybrid). Needs BOTH
# the segment and line indexes regardless of LINE, so it depends on the two named
# index files directly (not $(INDEX)). The longer `vector-hybrid%` stem takes
# precedence over `vector%` for vector-hybrid<k>.jsonl. Both languages.
#   make vector-hybrid       → results-<lang>/vector-hybrid5.jsonl   (default k=5)
#   make vector-hybrid K=10  → results-<lang>/vector-hybrid10.jsonl  (k=10)
$(RESULTS)/vector-hybrid%.jsonl: index-$(LANG).safetensors index-line-$(LANG).safetensors $(QUESTIONS)
	uv run answer_vector.py -l $(LANG) --hybrid -k $*

# Hybrid retrieval (dense ∪ BM25 union) answering. Mirrors the vector pattern
# rule: answer_hybrid.py derives the output filename from k, so the pattern
# rule just passes -k $* (the stem, e.g. "10"). Depends on the embedding INDEX
# (dense side) AND the raw SCENES + TSV (BM25 side), unlike vector which needs
# only the index. English only.
#   make hybrid         → results-<lang>/hybrid5.jsonl   (default k=5)
#   make hybrid K=10    → results-<lang>/hybrid10.jsonl  (k=10)
$(RESULTS)/hybrid%.jsonl: $(INDEX) $(SCENES) $(TSV) $(QUESTIONS)
	uv run answer_hybrid.py -l $(LANG) -k $*

# Per-chapter extraction, Phase 1: one chapter group per part file.
$(RESULTS)/extract-%.jsonl: $(SCENES) $(QUESTIONS)
	uv run answer_extract.py -l $(LANG) -p $*

# Per-chapter extraction, Phase 2: synthesize answers from the part files.
$(RESULTS)/extract.jsonl: $(EXTRACT_PARTS) $(QUESTIONS)
	uv run answer_extract.py -l $(LANG)

# Per-chapter two-level relevance filter (yes/no), Phase 1: writes a single
# filter2.tsv (a TSV: a chapter/question_id/verdict header then one row per
# classified pair, all chapters at once). A stricter bar than filter3 — Phase 2
# keeps only "yes" verdicts, so uncertain chapters are dropped.
$(FILTER2_TSV): $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --phase1 --verdicts 2

# Per-chapter two-level relevance filter, Phase 2: answer from the FULL text
# of every chapter marked "yes".
$(RESULTS)/filter2.jsonl: $(FILTER2_TSV) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --verdicts 2

# Per-chapter three-level relevance filter (yes/maybe/no), Phase 1: default
# --verdicts 3 (omitted), writes filter3.tsv. All chapters in one run.
$(FILTER3_TSV): $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --phase1

# Per-chapter three-level relevance filter, Phase 2: answer from the FULL text
# of every chapter whose verdict is not "no" (both "yes" and "maybe").
$(RESULTS)/filter3.jsonl: $(FILTER3_TSV) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG)

# Per-chapter eleven-level relevance filter (integer 0-10), Phase 1 ONLY. The
# keep/drop threshold is intentionally not fixed here: a single Phase 1 run
# records the raw score per (chapter, question) pair so the threshold can be
# chosen after inspecting the distribution. Phase 2 (and the filter10.jsonl /
# judge targets) are deferred until that decision is made.
$(FILTER10_TSV): $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --phase1 --verdicts 10

# Per-chapter 101-level relevance filter (integer 0-100), Phase 1 ONLY. Tried
# as a finer-grained filter10, but the model self-quantized to multiples of 10
# (13 of 101 values used) — filter100 is filter10 scaled x10, with a worse
# gold-scored-0 floor. `make filter SCALE=100` prints only the occurrence
# count; see FILTER.md. Phase 2 is not planned for this variant.
$(FILTER100_TSV): $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --phase1 --verdicts 100

# Per-chapter five-axis relevance filter (five integers 0-10: factual, entity,
# causal, reference, thematic), Phase 1 ONLY. Decomposes the relevance judgement
# across orthogonal axes so that an indirectly-relevant cross-reference chapter
# scores non-zero on at least one axis, attacking the gold-scored-0 floor that
# the single-axis 10/100 variants cannot reach (see FILTER.md). Phase 2 would keep
# a chapter when the five-axis sum is non-zero, but is deferred until the floor
# distribution from this Phase 1 run is inspected. Uses structured output (a
# pydantic schema) via create_json_descriptions_prompt, unlike the plain-text
# single-token replies of filter10/100.
$(FILTER5D_TSV): $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --phase1 --verdicts 5d

# Perfect-retrieval ceiling: the gold chapters fed verbatim as context, no
# retrieval. No Phase 1, so just one target — the answer file. Its judge target
# is defined below alongside the other opt-in judge rules.
$(RESULTS)/ceiling.jsonl: $(SCENES) $(QUESTIONS)
	uv run answer_ceiling.py -l $(LANG)

# LLM grading of each answer file. One pattern rule serves both modes: the `%`
# absorbs the whole stem, so judge-vector5.jsonl ← vector5.jsonl (segment) and
# judge-vector-line5.jsonl ← vector-line5.jsonl (LINE=1, % = "-line5").
$(RESULTS)/judge-vector%.jsonl: $(RESULTS)/vector%.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/vector$*.jsonl

$(RESULTS)/judge-extract.jsonl: $(RESULTS)/extract.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/extract.jsonl

# Opt-in: two-level filter judging. Run `make judge-filter2` (or `make
# filter2`) explicitly to grade the two-level filter answers.
$(RESULTS)/judge-filter2.jsonl: $(RESULTS)/filter2.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/filter2.jsonl

# Opt-in: not built by the default `judge` aggregate. Run `make judge-filter3`
# (or `make filter3`) explicitly to grade the three-level filter answers.
$(RESULTS)/judge-filter3.jsonl: $(RESULTS)/filter3.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/filter3.jsonl

# Opt-in: ceiling (gold-chapter context) judging. Run `make judge-ceiling`
# (or `make ceiling`) explicitly to grade the ceiling answers.
$(RESULTS)/judge-ceiling.jsonl: $(RESULTS)/ceiling.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/ceiling.jsonl

# Opt-in: hybrid (dense ∪ BM25 union) judging. Not built by the default `judge`
# aggregate (English only). Run `make hybrid-judge` (or `make judge-hybrid<k>`
# explicitly) to grade the hybrid answers; `make report` then shows the rows.
$(RESULTS)/judge-hybrid5.jsonl: $(RESULTS)/hybrid5.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/hybrid5.jsonl

$(RESULTS)/judge-hybrid10.jsonl: $(RESULTS)/hybrid10.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/hybrid10.jsonl

# GraphRAG (local / global search) judging. English only; included in the
# default `judge` aggregate via wildcard pickup when the answer files exist.
$(RESULTS)/judge-graphrag-%.jsonl: $(RESULTS)/graphrag-%.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/graphrag-$*.jsonl

# Remove generated answers/judgements (keeps the index). The vector[0-9]* and
# judge-vector[0-9]* globs catch the k-variant files (vector10.jsonl, etc.); the
# hybrid[0-9]* / judge-hybrid[0-9]* globs do the same for hybrid10.jsonl, etc.
# rm -f silently ignores them when no match exists.
clean:
	rm -f $(RESULTS)/vector[0-9]*.jsonl \
	      $(RESULTS)/vector-line[0-9]*.jsonl \
	      $(RESULTS)/vector-hybrid[0-9]*.jsonl \
	      $(RESULTS)/hybrid[0-9]*.jsonl \
	      $(RESULTS)/extract.jsonl \
	      $(RESULTS)/filter2.jsonl $(RESULTS)/filter3.jsonl \
	      $(RESULTS)/ceiling.jsonl \
	      $(EXTRACT_PARTS) \
	      $(FILTER2_TSV) $(FILTER3_TSV) $(FILTER10_TSV) $(FILTER100_TSV) $(FILTER5D_TSV) \
	      $(RESULTS)/judge-vector[0-9]*.jsonl \
	      $(RESULTS)/judge-vector-line[0-9]*.jsonl \
	      $(RESULTS)/judge-vector-hybrid[0-9]*.jsonl \
	      $(RESULTS)/judge-hybrid[0-9]*.jsonl \
	      $(RESULTS)/judge-extract.jsonl \
	      $(RESULTS)/judge-filter2.jsonl $(RESULTS)/judge-filter3.jsonl \
	      $(RESULTS)/judge-ceiling.jsonl
