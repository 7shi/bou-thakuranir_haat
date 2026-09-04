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
# cluster-bn.jsonl's rule is for the initial build only. Once clustered, it
# is edited data - corrections go in with a cluster.py patch() one-liner (see
# the comment above FORMS in cluster.py), not by reclustering, which would
# call the model again and lose them. `make cluster-bn.jsonl` is a no-op once
# the file exists, same as any other target here, but don't `rm` it to force
# a rebuild - that's the one target in this file not meant to be regenerated.
#
# normalized-bn.jsonl and anchor-{en,ja,hi}.jsonl are joined into ../all.tsv
# by build_tsv.py (see below and ../README.md). ../all.tsv is hand-edited
# after that initial build (see ../CORRECTIONS.md), so `make all.tsv` is not
# part of the default `make` and must not be run as a routine step - it
# would overwrite those edits.
#
# Usage:
#   make                       # all four languages
#   make hi.jsonl              # one language
#   make cluster-bn.jsonl      # cluster the Bengali survey by entity (once)
#   make normalized-bn.jsonl   # fold cluster-bn.jsonl's chapters into one list
#   make anchor                # tie en/ja/hi to the Bengali names
#   make anchor-hi.jsonl       # one language
#   make all.tsv               # rebuild ../all.tsv - see the warning above

ROOT         := ../..
PROPER_NOUNS := ..
SURVEY       := survey.py
CLUSTER      := cluster.py
ANCHOR       := anchor.py
BUILD_TSV    := build_tsv.py
MODEL        := openai:gpt-5.6-terra
ALIGNED      := $(ROOT)/all/aligned
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

all.tsv: normalized-bn.jsonl anchor-en.jsonl anchor-ja.jsonl anchor-hi.jsonl
	uv run $(BUILD_TSV) -o $(PROPER_NOUNS)/all.tsv

clean:
	rm -f bn.jsonl en.jsonl ja.jsonl hi.jsonl normalized-bn.jsonl \
	      anchor-en.jsonl anchor-ja.jsonl anchor-hi.jsonl
