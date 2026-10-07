# Are the gold answers' facts written in the Japanese text? Each English gold
# answer is split into claims, which are then checked against the cited
# chapters in English and in Japanese; compare.py relates the claims missing
# from the Japanese text only to the Japanese gap under Ternary (../ternary/).
#
# Usage:
#   make facts     # split the English gold answers into claims → facts.jsonl
#   make check     # check the claims against both texts → check-{en,ja}.jsonl
#   make compare   # print the tables

.PHONY: help facts check compare
.DEFAULT_GOAL := help

help:
	@echo "Usage: make facts | check | compare"

facts:
	uv run check_gold.py facts

check:
	uv run check_gold.py check -l en
	uv run check_gold.py check -l ja

compare:
	uv run compare.py
