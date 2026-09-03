# all.tsv joins survey/normalized-bn.jsonl and survey/anchor-{en,ja,hi}.jsonl
# into one row per Bengali name (see build_tsv.py) - no model calls, so it
# always rebuilds. Those four files are themselves built by the survey/anchor
# pipeline in survey/ (see survey/Makefile and survey/README.md); this
# delegates to that Makefile for each one it needs.
#
# Usage:
#   make all.tsv

SURVEY    := survey
BUILD_TSV := build_tsv.py

all.tsv: $(SURVEY)/normalized-bn.jsonl $(SURVEY)/anchor-en.jsonl $(SURVEY)/anchor-ja.jsonl $(SURVEY)/anchor-hi.jsonl
	uv run $(BUILD_TSV)

$(SURVEY)/normalized-bn.jsonl $(SURVEY)/anchor-en.jsonl $(SURVEY)/anchor-ja.jsonl $(SURVEY)/anchor-hi.jsonl:
	$(MAKE) -C $(SURVEY) $(notdir $@)
