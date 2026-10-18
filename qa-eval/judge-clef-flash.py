#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with Cloudflare's Clef Flash.

ollama_systemone.py run with model `clef-flash`, writing
clef-flash/<input-stem>.tsv and clef-flash/MODELS.tsv; see ollama_systemone.py
for the grading contract, the output format and the options.
"""

from ollama_systemone import main

if __name__ == "__main__":
    main("clef-flash", __doc__)
