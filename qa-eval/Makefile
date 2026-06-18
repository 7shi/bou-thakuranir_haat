# QA evaluation pipeline. Models are left to each script's default.
#
# Real file targets drive the dependency chain; .PHONY names wrap them as
# convenient aliases. Per-language flow (LANG=en|ja):
#   index -> rag + extract -> judge -> report
#
# Usage:
#   make            # full English pipeline (LANG=en)
#   make ja         # full Japanese pipeline
#   make all        # both languages
#   make report     # build whatever is missing, then print the table
#   make LANG=ja rag judge
#   make sweep      # retrieval sweep (independent of the pipeline; no LLM)

LANG    := en
ROOT    := ..
RESULTS := results-$(LANG)

QUESTIONS := $(ROOT)/questions-$(LANG).jsonl
SCENES    := $(ROOT)/all/$(LANG)-gemini.jsonl
TSV       := $(ROOT)/all/$(LANG)-gemini.tsv
INDEX     := index-$(LANG).safetensors

PARTS         := 1 2 3 4
EXTRACT_PARTS := $(patsubst %,$(RESULTS)/extract-%.jsonl,$(PARTS))

# Retrieval depth for the `rag` target. Empty (or unset) → default k=5, whose
# output is results-<lang>/rag.jsonl. Set K=10 → results-<lang>/rag-10.jsonl.
K ?=
RAG_FILE := $(RESULTS)/rag.jsonl
ifneq ($(K),)
RAG_FILE := $(RESULTS)/rag-$(K).jsonl
endif

.PHONY: en ja all pipeline index rag extract-parts extract judge report sweep clean
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

# LLM grading of each answer file.
$(RESULTS)/judge-rag.jsonl: $(RESULTS)/rag.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/rag.jsonl

$(RESULTS)/judge-extract.jsonl: $(RESULTS)/extract.jsonl $(QUESTIONS)
	uv run judge.py -l $(LANG) $(RESULTS)/extract.jsonl

# Remove generated answers/judgements (keeps the index). The rag-[0-9]* and
# judge-rag-[0-9]* globs catch the k-variant files (rag-10.jsonl, etc.); rm -f
# silently ignores them when no match exists.
clean:
	rm -f $(RESULTS)/rag.jsonl $(RESULTS)/rag-[0-9]*.jsonl \
	      $(RESULTS)/extract.jsonl \
	      $(EXTRACT_PARTS) \
	      $(RESULTS)/judge-rag.jsonl $(RESULTS)/judge-rag-[0-9]*.jsonl \
	      $(RESULTS)/judge-extract.jsonl
