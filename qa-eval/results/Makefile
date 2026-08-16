# Per-model answerer runs — try different answerer models without touching the
# canonical results-<lang>/ trees.
#
# Two methods, both writing <METHOD>-<MODEL>-<LANG>.jsonl here in results/
# (":" and "/" in MODEL replaced by "_"), so the existing results stay as they
# are. Resume-safe: the answer scripts append to the output and skip
# already-answered question IDs.
#
#   hybrid8 — Hybrid k=8 (dense u BM25 union) retrieval, then answer
#   ceiling — no retrieval at all: the gold chapters as context. Retrieval is
#             model-independent, so hybrid8 feeds every model the same context;
#             ceiling isolates the same comprehension difference with a much
#             smaller context, which is cheaper and faster per question.
#
# Usage:
#   make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions -> hybrid8-<MODEL>-<LANG>.jsonl
#   make ceiling MODEL=... LANG={en,ja}   # answer 50 questions -> ceiling-<MODEL>-<LANG>.jsonl
#   make judge                            # opt-in: grade every ungraded answer file
#   make report                           # aggregate every judged run → report.md
#
#   MODEL — llm7shi model string of the answerer (e.g. google:gemini-4-31b-it)
#   LANG  — en | ja
#
# Example:
#   make ceiling MODEL=google:gemini-4-31b-it LANG=ja

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
# <METHOD>-<MODEL>-<LANG>: the method leads so runs group by method, and LANG
# trails so it can be read off the filename with a plain suffix split — MODEL is
# the only field that may itself contain "-".
HYBRID_ANSWER := hybrid$(K)-$(SAFE_MODEL)-$(LANG).jsonl
CEILING_ANSWER := ceiling-$(SAFE_MODEL)-$(LANG).jsonl

.PHONY: help check-args hybrid8 ceiling judge report
.DEFAULT_GOAL := help

help:
	@echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"
	@echo "       make ceiling MODEL=... LANG={en,ja}"
	@echo "       make judge"
	@echo "       make report"

# Shared guard for the answering targets, which all need MODEL and LANG. The
# usage line names the goal actually invoked, so the message stays accurate for
# whichever target pulled this in.
check-args:
	@if [ -z "$(MODEL)" ] || [ -z "$(LANG)" ]; then \
		echo "Usage: make $(firstword $(MAKECMDGOALS)) MODEL=... LANG={en,ja}"; \
		exit 2; \
	fi

hybrid8: check-args
	@test -f $(INDEX) || $(MAKE) -C .. LANG=$(LANG) index-$(LANG).safetensors
	cd $(ROOT) && uv run answer_hybrid.py -l $(LANG) -k $(K) -m $(MODEL) -o results/$(HYBRID_ANSWER)

# Perfect-retrieval ceiling: the gold chapters fed verbatim as context. No
# index needed — there is no retrieval step at all.
ceiling: check-args
	cd $(ROOT) && uv run answer_ceiling.py -l $(LANG) -m $(MODEL) -o results/$(CEILING_ANSWER)

# Opt-in: LLM grading (same default judge as the main pipeline). Scans every
# answer file here (*.jsonl not starting with "judge-"), skips the ones that
# already have a judge-<stem>.jsonl, and takes LANG from the filename's trailing
# field (<METHOD>-<MODEL>-<LANG>.jsonl) — no MODEL/LANG needed. Output lands
# next to the answer file via judge.py's default judge-<stem>.jsonl naming.
judge:
	@for f in *.jsonl; do \
		case "$$f" in judge-*) continue;; esac; \
		[ -e "$$f" ] || continue; \
		[ -e "judge-$$f" ] && { echo "skip $$f (judge-$$f exists)"; continue; }; \
		lang=$${f%.jsonl}; lang=$${lang##*-}; \
		case "$$lang" in en|ja) ;; *) echo "skip $$f (cannot infer LANG)"; continue;; esac; \
		echo "judge $$f (LANG=$$lang)"; \
		(cd $(ROOT) && uv run judge.py -l $$lang results/$$f) || exit $$?; \
	done

# Aggregate every <METHOD>-<MODEL>-<LANG>.jsonl that has a matching judge file
# into report.md (and print the same table to the terminal). Mechanical, no LLM
# and no MODEL/LANG needed — this directory's own report, independent of the
# parent report.py, which scans only results-<lang>/ and ignores these runs.
report:
	cd $(ROOT) && uv run results/report.py
