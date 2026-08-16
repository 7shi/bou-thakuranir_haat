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
#   make judge                            # opt-in: grade every ungraded answer file
#   make report                           # aggregate every judged run → report.md
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

.PHONY: help hybrid8 judge report
.DEFAULT_GOAL := help

help:
	@echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"
	@echo "       make judge"
	@echo "       make report"

hybrid8:
	@if [ -z "$(MODEL)" ] || [ -z "$(LANG)" ]; then \
		echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"; \
		exit 2; \
	fi
	@test -f $(INDEX) || $(MAKE) -C .. LANG=$(LANG) index-$(LANG).safetensors
	cd $(ROOT) && uv run answer_hybrid.py -l $(LANG) -k $(K) -m $(MODEL) -o results/$(ANSWER)

# Opt-in: LLM grading (same default judge as the main pipeline). Scans every
# answer file here (*.jsonl not starting with "judge-"), skips the ones that
# already have a judge-<stem>.jsonl, and takes LANG from the filename itself
# (<MODEL>-<LANG>-hybrid<k>.jsonl) — no MODEL/LANG needed. Output lands next to
# the answer file via judge.py's default judge-<stem>.jsonl naming.
judge:
	@for f in *.jsonl; do \
		case "$$f" in judge-*) continue;; esac; \
		[ -e "$$f" ] || continue; \
		[ -e "judge-$$f" ] && { echo "skip $$f (judge-$$f exists)"; continue; }; \
		lang=$$(echo "$${f%.jsonl}" | sed -n 's/.*-\([a-z][a-z]\)-hybrid[0-9]*$$/\1/p'); \
		if [ -z "$$lang" ]; then echo "skip $$f (cannot infer LANG)"; continue; fi; \
		echo "judge $$f (LANG=$$lang)"; \
		(cd $(ROOT) && uv run judge.py -l $$lang results/$$f) || exit $$?; \
	done

# Aggregate every <MODEL>-<LANG>-hybrid<k>.jsonl that has a matching judge file
# into report.md (and print the same table to the terminal). Mechanical, no LLM
# and no MODEL/LANG needed — this directory's own report, independent of the
# parent report.py, which scans only results-<lang>/ and ignores these runs.
report:
	cd $(ROOT) && uv run results/report.py
