# Per-model answerer runs — try different answerer models without touching the
# canonical results-<lang>/ trees.
#
# Two methods, both writing <METHOD>-<MODEL>-<LANG>.jsonl here in results/
# (":" and "/" in MODEL replaced by "_"), so the existing results stay as they
# are. Resume-safe: the answer scripts append to the output and skip
# already-answered question IDs.
#
#   hybrid8 — Hybrid k=8 (dense u BM25 union) context, replayed from the
#             canonical results-<lang>/hybrid8.jsonl so every model here gets a
#             byte-identical context (see REFERENCE below)
#   ceiling — no retrieval at all: the gold chapters as context. Retrieval is
#             model-independent, so hybrid8 feeds every model the same context;
#             ceiling isolates the same comprehension difference with a much
#             smaller context, which is cheaper and faster per question.
#
# Usage:
#   make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions -> hybrid8-<MODEL>-<LANG>.jsonl
#   make ceiling MODEL=... LANG={en,ja}   # answer 50 questions -> ceiling-<MODEL>-<LANG>.jsonl
#   make test    MODEL=... LANG={en,ja}   # answer question 1 only, both methods, no file output
#   make judge                            # opt-in: grade every ungraded answer file
#   make report                           # aggregate every judged run → report.md + MODELS.svg
#
#   MODEL — llm7shi model string of the answerer (e.g. google:gemini-4-31b-it)
#   LANG  — en | ja
#
# Example:
#   make ceiling MODEL=google:gemini-4-31b-it LANG=ja

# <(...) process substitution in the `test` target needs bash, not the
# POSIX-sh default.
SHELL := /bin/bash

MODEL ?=
LANG ?=
K := 8

# Fixed once per `make` invocation and passed to every `judge.py` call in the
# `judge` target below via --started-at, so the sequential per-file judge.py
# processes it launches show an overall-elapsed column spanning the whole run.
START_TIME := $(shell date +%s)

ROOT := ..
# hybrid8 replays this run's retrieval instead of recomputing it. Retrieval is
# supposed to be model-independent, but the dense side embeds the question at
# run time and that is not bit-stable across ollama backends (ROCm vs Vulkan
# moves cosines in the 4th decimal, enough to swap a chapter sitting near the
# top-8 cutoff). Pinning it to the canonical run makes the context identical for
# every model here, so a verdict difference is synthesis by construction.
REFERENCE := results-$(LANG)/hybrid$(K).jsonl
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

.PHONY: help check-args hybrid8 ceiling test judge report
.DEFAULT_GOAL := help

help:
	@echo "Usage: make hybrid8 MODEL=... LANG={en,ja}"
	@echo "       make ceiling MODEL=... LANG={en,ja}"
	@echo "       make test MODEL=... LANG={en,ja}"
	@echo "       make judge"
	@echo "       make report"

# Shared guard for the answering targets, which all need MODEL and LANG. The
# usage line names the goal actually invoked, so the message stays accurate for
# whichever target pulled this in.
#
# LANG must be checked against {en,ja} specifically, not just non-empty: make
# imports environment variables as make variables, and `LANG ?=` above does not
# override an already-set one — so a shell with LANG=ja_JP.UTF-8 (locale) set,
# which is the common case, silently leaks that value in when LANG= is omitted
# on the command line. A plain emptiness check would miss it.
check-args:
	@if [ -z "$(MODEL)" ] || { [ "$(LANG)" != "en" ] && [ "$(LANG)" != "ja" ]; }; then \
		echo "Usage: make $(firstword $(MAKECMDGOALS)) MODEL=... LANG={en,ja}"; \
		exit 2; \
	fi

hybrid8: check-args
	cd $(ROOT) && uv run answer_hybrid.py -l $(LANG) -m $(MODEL) \
		--retrieval $(REFERENCE) -o results/$(HYBRID_ANSWER)

# Perfect-retrieval ceiling: the gold chapters fed verbatim as context. No
# index needed — there is no retrieval step at all.
ceiling: check-args
	cd $(ROOT) && uv run answer_ceiling.py -l $(LANG) -m $(MODEL) -o results/$(CEILING_ANSWER)

# Quick smoke test for backend/model trouble (e.g. the ROCm prompt-ordering
# issue in the README) — runs question 1 only, under both methods, with no
# file left behind: -o /dev/null and -i a process-substituted one-line slice
# of the questions file, so nothing in results/ or elsewhere is touched.
# questions-<lang>.jsonl lives at the repo root, one level above $(ROOT)
# (qa-eval) — hence "../questions-..." once cd'd into $(ROOT).
test: check-args
	cd $(ROOT) && uv run answer_ceiling.py -l $(LANG) -m $(MODEL) \
		-i <(head -n 1 ../questions-$(LANG).jsonl) -o /dev/null
	cd $(ROOT) && uv run answer_hybrid.py -l $(LANG) -m $(MODEL) \
		--retrieval $(REFERENCE) -i <(head -n 1 ../questions-$(LANG).jsonl) -o /dev/null

# Opt-in: LLM grading (same default judge as the main pipeline). Scans every
# answer file here (*.jsonl not starting with "judge-"), skips the ones that
# already have a judge-<stem>.jsonl with as many lines as the answer file
# (a shorter judge file means a prior run was interrupted, so it's redone), and
# takes LANG from the filename's trailing field (<METHOD>-<MODEL>-<LANG>.jsonl)
# — no MODEL/LANG needed. Output lands next to the answer file via judge.py's
# default judge-<stem>.jsonl naming.
judge:
	@for f in *.jsonl; do \
		case "$$f" in judge-*) continue;; esac; \
		[ -e "$$f" ] || continue; \
		if [ -e "judge-$$f" ]; then \
			n=$$(wc -l < "$$f"); jn=$$(wc -l < "judge-$$f"); \
			[ "$$jn" -ge "$$n" ] && { echo "skip $$f (judge-$$f exists, $$jn/$$n lines)"; continue; }; \
			echo "resume $$f (judge-$$f incomplete, $$jn/$$n lines)"; \
		fi; \
		lang=$${f%.jsonl}; lang=$${lang##*-}; \
		case "$$lang" in en|ja) ;; *) echo "skip $$f (cannot infer LANG)"; continue;; esac; \
		echo "judge $$f (LANG=$$lang)"; \
		(cd $(ROOT) && uv run judge.py -l $$lang --started-at $(START_TIME) results/$$f) || exit $$?; \
	done

# Aggregate every <METHOD>-<MODEL>-<LANG>.jsonl that has a matching judge file
# into report.md (and print the same table to the terminal), then regenerate
# MODELS.svg from the same rows (via report.collect_rows), so the chart never
# drifts from report.md. Mechanical, no LLM and no MODEL/LANG needed — this
# directory's own report, independent of the parent report.py, which scans
# only results-<lang>/ and ignores these runs.
report:
	cd $(ROOT) && uv run results/report.py
	uv run generate_chart.py
