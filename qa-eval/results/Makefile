# Per-model Hybrid k=8 (dense ∪ BM25 union) runs — try different answerer
# models without touching the canonical results-<lang>/ trees.
#
# Each run writes <MODEL>-<LANG>-hybrid8.jsonl here in results/ (":" and "/"
# in MODEL replaced by "_"), so the existing results stay as they are.
# Resume-safe: answer_hybrid.py appends to the output and skips
# already-answered question IDs.
#
# Usage:
#   make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions → <MODEL>-<LANG>-hybrid8.jsonl
#   make judge   MODEL=... LANG={en,ja}   # opt-in: grade → judge-<MODEL>-<LANG>-hybrid8.jsonl
#
#   MODEL — llm7shi model string of the answerer (e.g. google:gemini-4-31b-it)
#   LANG  — en | ja
#
# Example:
#   make hybrid8 MODEL=google:gemini-4-31b-it LANG=ja

MODEL ?=
LANG ?=
K := 8

ROOT := ..
INDEX := $(ROOT)/index-$(LANG).safetensors
# ":" and "/" in MODEL (e.g. "ollama:qwen3.6", "hf.co/unsloth/gemma-4") are not
# filename-safe — sanitized to "_" here, at the layer that defines this
# directory's naming convention. The scripts write exactly the path given by
# -o / derived from the input stem.
SAFE_MODEL := $(subst /,_,$(subst :,_,$(MODEL)))
ANSWER := $(SAFE_MODEL)-$(LANG)-hybrid$(K).jsonl

.PHONY: help hybrid8 judge
.DEFAULT_GOAL := help

help:
	@echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"

hybrid8:
	@if [ -z "$(MODEL)" ] || [ -z "$(LANG)" ]; then \
		echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"; \
		exit 2; \
	fi
	@test -f $(INDEX) || $(MAKE) -C .. LANG=$(LANG) index-$(LANG).safetensors
	cd $(ROOT) && uv run answer_hybrid.py -l $(LANG) -k $(K) -m $(MODEL) -o results/$(ANSWER)

# Opt-in: LLM grading of the hybrid8 answers (same default judge as the main
# pipeline) → judge-<MODEL>-<LANG>-hybrid8.jsonl next to the answer file
# (judge.py's default judge-<stem>.jsonl naming).
judge: hybrid8
	cd $(ROOT) && uv run judge.py -l $(LANG) results/$(ANSWER)
