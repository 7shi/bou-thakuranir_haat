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
# (see cluster.py). Bengali only: it is the source language, and the other
# three are anchored to its names by anchor.py rather than clustered in
# isolation, so anchor-{en,ja,hi}.jsonl depend on normalized-bn.jsonl.
#
# Usage:
#   make                       # all four languages
#   make hi.jsonl              # one language
#   make cluster-bn.jsonl      # cluster the Bengali survey by entity
#   make normalized-bn.jsonl   # fold those chapters into one corrected list
#   make anchor                # tie en/ja/hi to the Bengali names
#   make anchor-hi.jsonl       # one language

ROOT    := ../..
SURVEY  := survey.py
CLUSTER := cluster.py
ANCHOR  := anchor.py
MODEL   := openai:gpt-5.6-terra
ALIGNED := $(ROOT)/all/aligned
SEGMENTATION := $(ROOT)/segmentations.jsonl

.PHONY: all anchor clean

all: bn.jsonl en.jsonl ja.jsonl hi.jsonl

anchor: anchor-en.jsonl anchor-ja.jsonl anchor-hi.jsonl

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

# -S sweeps each chapter's source for the occurrences the survey missed.
normalized-bn.jsonl: cluster-bn.jsonl
	uv run $(CLUSTER) bn.jsonl -m $(MODEL) -N -S $(ROOT)/all/bn.md \
	    --segmentation $(SEGMENTATION)

anchor-en.jsonl: en.jsonl normalized-bn.jsonl
	uv run $(ANCHOR) en.jsonl -m $(MODEL)

anchor-ja.jsonl: ja.jsonl normalized-bn.jsonl
	uv run $(ANCHOR) ja.jsonl -m $(MODEL)

anchor-hi.jsonl: hi.jsonl normalized-bn.jsonl
	uv run $(ANCHOR) hi.jsonl -m $(MODEL)

clean:
	rm -f bn.jsonl en.jsonl ja.jsonl hi.jsonl cluster-bn.jsonl normalized-bn.jsonl \
	      anchor-en.jsonl anchor-ja.jsonl anchor-hi.jsonl
