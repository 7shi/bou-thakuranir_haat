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

LANG    := en
ROOT    := ..
RESULTS := results-$(LANG)

QUESTIONS := $(ROOT)/questions-$(LANG).jsonl
SCENES    := $(ROOT)/all/$(LANG)-gemini.jsonl
TSV       := $(ROOT)/all/$(LANG)-gemini.tsv
INDEX     := index-$(LANG).safetensors

PARTS         := 1 2 3 4
EXTRACT_PARTS := $(patsubst %,$(RESULTS)/extract-%.jsonl,$(PARTS))

.PHONY: en ja all pipeline index rag extract-parts extract judge report clean
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
rag: $(RESULTS)/rag.jsonl
extract-parts: $(EXTRACT_PARTS)
extract: $(RESULTS)/extract.jsonl
judge: $(RESULTS)/judge-rag.jsonl $(RESULTS)/judge-extract.jsonl

# Accuracy + chapter retrieval comparison table (terminal output only).
report: judge
	uv run report.py -l $(LANG)

# --- file targets ---

# Scene embedding index.
$(INDEX): $(SCENES) $(TSV)
	uv run build_index.py -l $(LANG)

# Vector RAG answering.
$(RESULTS)/rag.jsonl: $(INDEX) $(QUESTIONS)
	uv run answer_rag.py -l $(LANG)

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

# Remove generated answers/judgements (keeps the index).
clean:
	rm -f $(RESULTS)/rag.jsonl $(RESULTS)/extract.jsonl \
	      $(EXTRACT_PARTS) \
	      $(RESULTS)/judge-rag.jsonl $(RESULTS)/judge-extract.jsonl
