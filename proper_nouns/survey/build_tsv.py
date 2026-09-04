#!/usr/bin/env python3
"""
Build proper_nouns/all.tsv from the survey/anchor pipeline in this directory.

normalized-bn.jsonl gives the Bengali canonical form and kind for every name
the book uses; anchor-{en,hi,ja}.jsonl tie each chapter's target-language
forms to one of those Bengali names. This joins the two: one row per Bengali
name, with the canonical spelling each language settled on, sourced from the
corpus as actually spelled rather than the one-off extraction behind
proper_nouns/extract/all.tsv, which is left untouched so the two can be
compared.

A Bengali name can have more than one canonical spelling in a language
(review.py's "drift" report) without that being an error - দাদা's "Dada" vs
"Grandson" split by which character is speaking, not a typo (see
../CORRECTIONS.md). Such cells list every canonical, most-used first, joined
by "; ".  A Bengali name no anchor ever ties a form to (untranslated, or the
translator dropped it) is left blank for that language.

all.tsv lives one directory up (../all.tsv), not next to this script - it is
hand-edited after being built (see ../CORRECTIONS.md and ../README.md's
"Correcting a rendering found by inspection"), so re-running this script is
destructive: it overwrites those edits with whatever the survey/anchor
pipeline currently says. Only run it for the initial build or a deliberate
full rebuild, never as a routine step.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

SURVEY_DIR = os.path.dirname(os.path.abspath(__file__))
from cluster import load_records, collect_names

LANGS = [("en", "English"), ("hi", "Hindi"), ("ja", "Japanese")]


def anchor_by_bengali(records: List[Dict]) -> Dict[str, List[Tuple[str, int]]]:
    """bengali -> [(canonical, chapter count)], most-used canonical first."""
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        for entity in record["entities"]:
            if not entity["bengali"]:
                continue
            counts[entity["bengali"]][entity["canonical"]] += 1
    by_bengali = {}
    for bengali, canonicals in counts.items():
        by_bengali[bengali] = sorted(canonicals.items(), key=lambda kv: (-kv[1], kv[0]))
    return by_bengali


def build_rows(survey_dir: str) -> List[List[str]]:
    bn_names = collect_names(load_records(os.path.join(survey_dir, "normalized-bn.jsonl")))
    by_lang = {code: anchor_by_bengali(load_records(os.path.join(survey_dir, f"anchor-{code}.jsonl")))
               for code, _ in LANGS}

    rows = [["Bengali", "Kind"] + [name for _, name in LANGS]]
    for name in bn_names:
        row = [name["canonical"], name["kind"]]
        for code, _ in LANGS:
            canonicals = by_lang[code].get(name["canonical"], [])
            row.append("; ".join(c for c, _ in canonicals))
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=None,
                         help="output TSV (default: ../all.tsv)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output = args.output or os.path.join(script_dir, "..", "all.tsv")
    rows = build_rows(SURVEY_DIR)

    with open(output, "w", encoding="utf-8") as f:
        for row in rows:
            f.write("\t".join(row) + "\n")
    print(f"Wrote {len(rows) - 1} names to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
