# Ceiling evaluation via the `opencode` CLI. See README.md for the full
# pipeline description.

# make imports environment variables as make variables, so a shell with
# LANG=ja_JP.UTF-8 (locale) set — the common case — silently leaks that value
# in when LANG= is omitted on the command line. Fall back to "en" unless LANG
# is exactly "en" or "ja".
LANG := $(if $(filter en ja,$(LANG)),$(LANG),en)

.PHONY: help extract ceiling.sh

help:
	@echo "Usage: make extract"
	@echo "       make ceiling.sh MODEL=... [LANG=en]"

# -> en/01.txt .. en/37.txt, ja/01.txt .. ja/37.txt
extract:
	uv run extract.py

# -> ceiling.sh (gitignored, regenerate per run); then: ./ceiling.sh
ceiling.sh:
	@if [ -z "$(MODEL)" ]; then \
		echo "Usage: make ceiling.sh MODEL=... [LANG=en]"; \
		exit 2; \
	fi
	uv run make_ceiling.py -l $(LANG) -m $(MODEL)
