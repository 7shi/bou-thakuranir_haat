#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with Bespoke Labs' Nimble.

ollama_systemone.py run with model `nimble`, writing nimble/<input-stem>.tsv
and nimble/MODELS.tsv; see ollama_systemone.py for the grading contract, the
output format and the options.
"""

from ollama_systemone import main

if __name__ == "__main__":
    main("nimble", __doc__)
