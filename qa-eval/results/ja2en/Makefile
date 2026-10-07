# Where does the Japanese gap come from? The Japanese Ceiling answers of the
# models below are graded by Ternary against the English question and gold
# answer (the originals the Japanese ones were translated from), as they are
# and translated into English, then compared with the same models' English and
# Japanese Ternary scores in ../ternary/.
#
# Usage:
#   make xling       # grade the Japanese answers against the English gold → xling/*.tsv
#   make translate   # ../ceiling-<MODEL>-ja.jsonl → ceiling-<MODEL>-ja.jsonl (English)
#   make judge       # grade the translations (-l en) → ternary/*.tsv
#   make retest      # grade the English answers again → retest/*.tsv
#   make compare     # print the comparison tables
#
# The models are the 11 outside the weakest five whose Japanese score falls
# furthest below English under OpenAI and Jev (mean ja − en ≤ −5.5), chosen
# without Ternary so that its own noise does not select them.
MODELS := \
	openrouter_stealth_space-bunny-alpha \
	opencode_longcat-2.5-preview-free \
	opencode_mimo-v2.6-flash-free \
	copilot_claude-haiku-4.5 \
	copilot_claude-sonnet-5 \
	openrouter_nvidia_nemotron-3.5-lightning_free \
	opencode_mimo-v2.5-free \
	openai_gpt-6.1-sol \
	copilot_mai-code-1.1-flash \
	ollama_gemma4_12b-it-qat \
	openai_gpt-6-sol

JUDGE := ../../judge-ternary.py
START_TIME := $(shell date +%s)

.PHONY: help xling translate judge retest compare
.DEFAULT_GOAL := help

help:
	@echo "Usage: make xling | translate | judge | retest | compare"

# --out-dir is relative to each input's directory (results/), hence ja2en/.
xling:
	uv run $(JUDGE) -l en --started-at $(START_TIME) -o ja2en/xling \
		$(foreach m,$(MODELS),../ceiling-$(m)-ja.jsonl)

translate:
	uv run translate.py $(foreach m,$(MODELS),../ceiling-$(m)-ja.jsonl)

judge:
	uv run $(JUDGE) -l en --started-at $(START_TIME) $(foreach m,$(MODELS),ceiling-$(m)-ja.jsonl)

retest:
	uv run $(JUDGE) -l en --started-at $(START_TIME) -o ja2en/retest \
		$(foreach m,$(MODELS),../ceiling-$(m)-en.jsonl)

compare:
	uv run compare.py
