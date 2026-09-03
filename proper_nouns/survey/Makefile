# Proper-noun survey: reads each target-language translation on its own terms
# and asks the model which proper nouns appear on each line, exactly as
# spelled (see survey.py). Terra, not Luna, because Luna's accuracy drops
# on text this long and per-line calls would be too many (1,159 lines total).
#
# bn comes from the classical Bengali source (all/bn.md), not the Modern
# Bengali translation (all/bn-gemini.jsonl) - that one copies proper nouns
# verbatim and is out of scope. en/ja/hi come from the aligned translations
# (all/aligned/*-gemini-terra.jsonl), so line numbers correspond to source
# lines across languages, not the raw pre-alignment translations.
#
# cluster.py then groups one survey's surface forms by entity, per chapter
# (see cluster.py). Bengali only for now: it is the source language, and the
# other three are meant to be anchored to it rather than clustered in
# isolation.
#
# Usage:
#   make                       # all four languages
#   make hi.jsonl              # one language
#   make cluster-bn.jsonl      # cluster the Bengali survey by entity
#   make normalized-bn.jsonl   # fold those chapters into one corrected list

ROOT    := ../..
SURVEY  := survey.py
CLUSTER := cluster.py
MODEL   := openai:gpt-5.6-terra
ALIGNED := $(ROOT)/all/aligned
SEGMENTATION := $(ROOT)/segmentations.jsonl

.PHONY: all clean

all: bn.jsonl en.jsonl ja.jsonl hi.jsonl

bn.jsonl: $(ROOT)/all/bn.md $(SEGMENTATION)
	uv run $(SURVEY) $(ROOT)/all/bn.md -m $(MODEL) --segmentation $(SEGMENTATION)

en.jsonl: $(ALIGNED)/en-gemini-terra.jsonl
	uv run $(SURVEY) $(ALIGNED)/en-gemini-terra.jsonl -m $(MODEL)

ja.jsonl: $(ALIGNED)/ja-gemini-terra.jsonl
	uv run $(SURVEY) $(ALIGNED)/ja-gemini-terra.jsonl -m $(MODEL)

hi.jsonl: $(ALIGNED)/hi-gemini-terra.jsonl
	uv run $(SURVEY) $(ALIGNED)/hi-gemini-terra.jsonl -m $(MODEL)

cluster-bn.jsonl: bn.jsonl
	uv run $(CLUSTER) bn.jsonl -m $(MODEL)

normalized-bn.jsonl: cluster-bn.jsonl
	uv run $(CLUSTER) bn.jsonl -m $(MODEL) -N

clean:
	rm -f bn.jsonl en.jsonl ja.jsonl hi.jsonl cluster-bn.jsonl normalized-bn.jsonl
