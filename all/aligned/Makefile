# Build and maintain the aligned translations (see README.md).
#
# The plain *.jsonl files are gitignored - only the *.delta.jsonl files are
# committed. `unpack` regenerates the former from the latter, cheaply and
# deterministically, and is what `make convert` at the repo root depends on.
#
# `align`, `fold` and `pack` are opt-in: they cost LLM calls (align), rewrite
# the *.jsonl from a hand-edited all/<lang>-gemini.md (fold), or rewrite the
# committed delta (pack), so they are commands you run deliberately, not
# something any other target depends on.
#
# Usage:
#   make unpack           # regenerate *.jsonl from the committed deltas
#   make align-en         # re-run align_lines.py for one language (costs $)
#   make align            # ...for all four
#   make fold-en          # fold edits to ../en-gemini.md into en-gemini-terra.jsonl
#   make fold             # ...for all four
#   make pack-en          # re-derive en-gemini-terra.delta.jsonl from the jsonl
#   make pack             # ...for all four
#
# Correcting the published text (see README.md): edit all/<lang>-gemini.md,
# `make fold-<lang>`, `make pack-<lang>`, then `make convert` at the repo
# root to confirm the round trip.

ALL   := ..
MODEL := openai:gpt-5.6-terra

LANGS   := en ja bn hi
ALIGNED := $(patsubst %,%-gemini-terra.jsonl,$(LANGS))

.PHONY: unpack align fold pack $(patsubst %,align-%,$(LANGS)) $(patsubst %,fold-%,$(LANGS)) $(patsubst %,pack-%,$(LANGS))

unpack: $(ALIGNED)

%.jsonl: %.delta.jsonl
	uv run pack_aligned.py unpack $<

align: $(patsubst %,align-%,$(LANGS))

# align_lines.py resumes from whatever the output file already has, so a
# re-run only fills in missing segments rather than redoing the whole file.
align-en:
	uv run align_lines.py $(ALL)/en-gemini.jsonl -m $(MODEL) -o en-gemini-terra.jsonl
align-ja:
	uv run align_lines.py $(ALL)/ja-gemini.jsonl -m $(MODEL) -o ja-gemini-terra.jsonl
align-bn:
	uv run align_lines.py $(ALL)/bn-gemini.jsonl -m $(MODEL) -o bn-gemini-terra.jsonl
align-hi:
	uv run align_lines.py $(ALL)/hi-gemini.jsonl -m $(MODEL) -o hi-gemini-terra.jsonl

fold: $(patsubst %,fold-%,$(LANGS))

# md_to_aligned.py rewrites the *.jsonl from all/<lang>-gemini.md in place;
# it refuses to run if a paragraph was added, removed, split or merged
# instead of edited in place (see README.md and the script's own docstring).
fold-en:
	uv run md_to_aligned.py $(ALL)/en-gemini.md -a en-gemini-terra.jsonl
fold-ja:
	uv run md_to_aligned.py $(ALL)/ja-gemini.md -a ja-gemini-terra.jsonl
fold-bn:
	uv run md_to_aligned.py $(ALL)/bn-gemini.md -a bn-gemini-terra.jsonl
fold-hi:
	uv run md_to_aligned.py $(ALL)/hi-gemini.md -a hi-gemini-terra.jsonl

pack: $(patsubst %,pack-%,$(LANGS))

pack-en:
	uv run pack_aligned.py pack en-gemini-terra.jsonl
pack-ja:
	uv run pack_aligned.py pack ja-gemini-terra.jsonl
pack-bn:
	uv run pack_aligned.py pack bn-gemini-terra.jsonl
pack-hi:
	uv run pack_aligned.py pack hi-gemini-terra.jsonl
