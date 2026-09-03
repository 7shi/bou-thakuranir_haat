#!/usr/bin/env python3
"""
Build proper_nouns/survey/all.tsv from the survey/anchor pipeline.

normalized-bn.jsonl gives the Bengali canonical form and kind for every name
the book uses; anchor-{en,hi,ja}.jsonl tie each chapter's target-language
forms to one of those Bengali names. This joins the two: one row per Bengali
name, with the canonical spelling each language settled on, sourced from the
corpus as actually spelled rather than the one-off extraction behind the
existing proper_nouns/all.tsv. That file is left untouched so the two can be
compared.

A Bengali name can have more than one canonical spelling in a language
(review.py's "drift" report) without that being an error - দাদা's "Dada" vs
"Grandson" split by which character is speaking, not a typo (see
CORRECTIONS.md). Such cells list every canonical, most-used first, joined by
"; ".  A Bengali name no anchor ever ties a form to (untranslated, or the
translator dropped it) is left blank for that language.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
                         help="output TSV (default: all.tsv next to this script)")
    args = parser.parse_args()

    survey_dir = os.path.dirname(os.path.abspath(__file__))
    output = args.output or os.path.join(survey_dir, "all.tsv")
    rows = build_rows(survey_dir)

    with open(output, "w", encoding="utf-8") as f:
        for row in rows:
            f.write("\t".join(row) + "\n")
    print(f"Wrote {len(rows) - 1} names to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
