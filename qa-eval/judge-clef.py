#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with Cloudflare's Clef.

ollama_systemone.py run with model `clef`, writing clef/<input-stem>.tsv and
clef/MODELS.tsv; see ollama_systemone.py for the grading contract, the output
format and the options.
"""

from ollama_systemone import main

if __name__ == "__main__":
    main("clef", __doc__)
