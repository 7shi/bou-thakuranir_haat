# QA evaluation pipeline. Models are left to each script's default.
#
# Real file targets drive the dependency chain; .PHONY names wrap them as
# convenient aliases. Per-language flow (LANG=en|ja):
#   index -> rag + extract -> judge -> report
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
#   make            # full English pipeline (LANG=en)
#   make ja         # full Japanese pipeline
#   make all        # both languages
#   make report     # build whatever is missing, then print the table
#   make LANG=ja rag judge
#   make filter2    # opt-in: per-chapter yes/no filter (Phase 1 + 2 + judge)
#   make filter3    # opt-in: per-chapter yes/maybe/no filter (Phase 1 + 2 + judge)
#   make ceiling    # opt-in: gold-chapter context ceiling (answer + judge)
#   make sweep      # retrieval sweep (independent of the pipeline; no LLM)

LANG    := en
ROOT    := ..
RESULTS := results-$(LANG)

QUESTIONS := $(ROOT)/questions-$(LANG).jsonl
SCENES    := $(ROOT)/all/$(LANG)-gemini.jsonl
TSV       := $(ROOT)/all/$(LANG)-gemini.tsv
INDEX     := index-$(LANG).safetensors

PARTS         := 1 2 3 4
EXTRACT_PARTS  := $(patsubst %,$(RESULTS)/extract-%.jsonl,$(PARTS))
FILTER2_PARTS  := $(patsubst %,$(RESULTS)/filter2-%.tsv,$(PARTS))
FILTER3_PARTS  := $(patsubst %,$(RESULTS)/filter3-%.tsv,$(PARTS))

# Retrieval depth for the `rag` target. Empty (or unset) → default k=5, whose
# output is results-<lang>/rag.jsonl. Set K=10 → results-<lang>/rag-10.jsonl.
K ?=
RAG_FILE := $(RESULTS)/rag.jsonl
ifneq ($(K),)
RAG_FILE := $(RESULTS)/rag-$(K).jsonl
endif

.PHONY: en ja all pipeline index rag extract-parts extract filter2-parts filter2 filter3-parts filter3 ceiling judge report sweep clean
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
rag: $(RAG_FILE)
extract-parts: $(EXTRACT_PARTS)
extract: $(RESULTS)/extract.jsonl
filter2-parts: $(FILTER2_PARTS)
# `make filter2` runs the whole opt-in pipeline (Phase 1 + Phase 2 + judge) so
# that Filter2 appears in `make report` after a single command. judge-filter2
# depends on filter2.jsonl which depends on the four part files.
filter2: $(RESULTS)/judge-filter2.jsonl
filter3-parts: $(FILTER3_PARTS)
# `make filter3` mirrors `make filter2` for the three-level (yes/maybe/no)
# default variant: Phase 1 + Phase 2 + judge, surfacing Filter3 in `make report`.
filter3: $(RESULTS)/judge-filter3.jsonl
ceiling: $(RESULTS)/judge-ceiling.jsonl
judge: $(RESULTS)/judge-rag.jsonl $(RESULTS)/judge-extract.jsonl
sweep: $(INDEX) $(QUESTIONS)
	uv run sweep_rag.py -l $(LANG)

# Accuracy + chapter retrieval comparison table + pairwise disagreement
# analysis (terminal output only). Needs >= 2 judged methods for the pass.
report: judge
	uv run report.py -l $(LANG)

# --- file targets ---

# Scene embedding index.
$(INDEX): $(SCENES) $(TSV)
	uv run build_index.py -l $(LANG)

# Vector RAG answering.
#   make rag            → results-<lang>/rag.jsonl      (default k=5)
#   make rag K=10       → results-<lang>/rag-10.jsonl   (k=10)
# answer_rag.py derives the output filename from k, so the explicit -o is not
# needed; the pattern rule just passes -k $* (the stem, e.g. "10").
$(RESULTS)/rag.jsonl: $(INDEX) $(QUESTIONS)
	uv run answer_rag.py -l $(LANG)

$(RESULTS)/rag-%.jsonl: $(INDEX) $(QUESTIONS)
	uv run answer_rag.py -l $(LANG) -k $*

# Per-chapter extraction, Phase 1: one chapter group per part file.
$(RESULTS)/extract-%.jsonl: $(SCENES) $(QUESTIONS)
	uv run answer_extract.py -l $(LANG) -p $*

# Per-chapter extraction, Phase 2: synthesize answers from the part files.
$(RESULTS)/extract.jsonl: $(EXTRACT_PARTS) $(QUESTIONS)
	uv run answer_extract.py -l $(LANG)

# Per-chapter two-level relevance filter (yes/no), Phase 1: same pattern as
# extract-% but with `--verdicts 2`, which writes filter2-%.tsv (a TSV: a
# chapter/question_id/verdict header then one row per classified pair). A
# stricter bar than filter3 — Phase 2 keeps only "yes" verdicts, so uncertain
# chapters are dropped.
$(RESULTS)/filter2-%.tsv: $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) -p $* --verdicts 2

# Per-chapter two-level relevance filter, Phase 2: answer from the FULL text
# of every chapter marked "yes".
$(RESULTS)/filter2.jsonl: $(FILTER2_PARTS) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) --verdicts 2

# Per-chapter three-level relevance filter (yes/maybe/no), Phase 1: default
# --verdicts 3 (omitted), writes filter3-%.tsv. Mirrors the extract-% pattern
# but writes a `verdict` column (TSV) instead of a summary.
$(RESULTS)/filter3-%.tsv: $(SCENES) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG) -p $*

# Per-chapter three-level relevance filter, Phase 2: answer from the FULL text
# of every chapter whose verdict is not "no" (both "yes" and "maybe").
$(RESULTS)/filter3.jsonl: $(FILTER3_PARTS) $(QUESTIONS)
	uv run answer_filter.py -l $(LANG)

# Perfect-retrieval ceiling: the gold chapters fed verbatim as context, no
# retrieval. No Phase 1, so just one target — the answer file. Its judge target
# is defined below alongside the other opt-in judge rules.
$(RESULTS)/ceiling.jsonl: $(SCENES) $(QUESTIONS)
	uv run answer_ceiling.py -l $(LANG)

# LLM grading of each answer file.
$(RESULTS)/judge-rag.jsonl: $(RESULTS)/rag.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/rag.jsonl

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

# Remove generated answers/judgements (keeps the index). The rag-[0-9]* and
# judge-rag-[0-9]* globs catch the k-variant files (rag-10.jsonl, etc.); rm -f
# silently ignores them when no match exists.
clean:
	rm -f $(RESULTS)/rag.jsonl $(RESULTS)/rag-[0-9]*.jsonl \
	      $(RESULTS)/extract.jsonl \
	      $(RESULTS)/filter2.jsonl $(RESULTS)/filter3.jsonl \
	      $(RESULTS)/ceiling.jsonl \
	      $(EXTRACT_PARTS) \
	      $(FILTER2_PARTS) $(FILTER3_PARTS) \
	      $(RESULTS)/judge-rag.jsonl $(RESULTS)/judge-rag-[0-9]*.jsonl \
	      $(RESULTS)/judge-extract.jsonl \
	      $(RESULTS)/judge-filter2.jsonl $(RESULTS)/judge-filter3.jsonl \
	      $(RESULTS)/judge-ceiling.jsonl
