# Are the gold answers' facts written in the Japanese text? Each English gold
# answer is split into claims, which are then checked against the cited
# chapters in English and in Japanese; claims.py summarizes which claims each
# text states. ../results/ja2en/gold_gap.py relates the claims missing from the
# Japanese text only to the Japanese gap under Ternary.
#
# Usage:
#   make facts     # split the English gold answers into claims → facts.jsonl
#   make check     # check the claims against both texts → check-{en,ja}.jsonl
#   make claims    # print the claim tables and lists
#   make redo QIDS="22 26"  # redo facts and both checks for these questions,
#                           # replacing their records (after a gold answer fix)

.PHONY: help facts check claims redo
.DEFAULT_GOAL := help

help:
	@echo "Usage: make facts | check | claims | redo QIDS=..."

facts:
	uv run check_gold.py facts

check:
	uv run check_gold.py check -l en
	uv run check_gold.py check -l ja

claims:
	uv run claims.py

redo:
	@[ -n "$(QIDS)" ] || { echo "Usage: make redo QIDS=..."; exit 2; }
	uv run check_gold.py facts --qids $(QIDS)
	uv run check_gold.py check -l en --qids $(QIDS)
	uv run check_gold.py check -l ja --qids $(QIDS)
