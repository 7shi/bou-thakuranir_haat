#!/usr/bin/env python3
"""
Summarize one anchor-<lang>.jsonl across all chapters, for manual review.

anchor.py resolves each chapter on its own, so a name's canonical spelling can
disagree from one chapter to the next, and an unresolved form in one chapter
may be the very name another chapter already tied to a Bengali name. Both are
invisible chapter by chapter and only show up once the chapters are collapsed
into one view - which is what this script does. It makes no model calls.

Two reports, corpus-wide:

- Drift: a Bengali name whose chapters chose more than one canonical
  spelling for it. These are the closest thing to a settled answer this
  script can offer - the split is visible without judgment.
- Unresolved: entries with no Bengali name, grouped by canonical form and
  split into "elsewhere linked" (that exact canonical string is tied to a
  Bengali name in some other chapter - most likely a chapter cluster.py's
  sweep should have caught but didn't) and "never linked" (a translator's
  addition, a common noun the survey mistook for a name, or a title the
  Bengali leaves implicit).
"""

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cluster import load_records


def collect_by_bengali(records: List[Dict]) -> Dict[str, Dict[str, Dict]]:
    """bengali -> canonical -> {kind, chapters, forms}"""
    by_bengali: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for record in sorted(records, key=lambda r: r["chapter"]):
        for entity in record["entities"]:
            if not entity["bengali"]:
                continue
            slot = by_bengali[entity["bengali"]].setdefault(
                entity["canonical"],
                {"kind": entity["kind"], "chapters": [], "forms": set()})
            slot["chapters"].append(record["chapter"])
            slot["forms"].update(entity["forms"])
    return by_bengali


def collect_unresolved(records: List[Dict]) -> Dict[str, Dict]:
    """canonical -> {kind, chapters, forms}, entries with no bengali."""
    unresolved: Dict[str, Dict] = {}
    for record in sorted(records, key=lambda r: r["chapter"]):
        for entity in record["entities"]:
            if entity["bengali"]:
                continue
            slot = unresolved.setdefault(
                entity["canonical"],
                {"kind": entity["kind"], "chapters": [], "forms": set()})
            slot["chapters"].append(record["chapter"])
            slot["forms"].update(entity["forms"])
    return unresolved


def report_drift(by_bengali: Dict[str, Dict[str, Dict]]) -> None:
    drift = {b: c for b, c in by_bengali.items() if len(c) > 1}
    print(f"## Drift: {len(drift)} Bengali name(s) with more than one canonical spelling\n")
    for bengali, canonicals in sorted(drift.items()):
        print(f"{bengali}")
        for canonical, info in sorted(canonicals.items()):
            chapters = ",".join(str(c) for c in info["chapters"])
            forms = ", ".join(sorted(info["forms"]))
            print(f"  {canonical}\t({info['kind']})\tch {chapters}\t{forms}")
        print()


def report_unresolved(unresolved: Dict[str, Dict], by_bengali: Dict[str, Dict[str, Dict]]) -> None:
    linked_canonicals = {c for canonicals in by_bengali.values() for c in canonicals}
    elsewhere = {c: i for c, i in unresolved.items() if c in linked_canonicals}
    never = {c: i for c, i in unresolved.items() if c not in linked_canonicals}

    print(f"## Unresolved, elsewhere linked: {len(elsewhere)} canonical form(s)\n")
    print("# Same canonical form is tied to a Bengali name in some other chapter -")
    print("# likely a sweep miss rather than a real gap.\n")
    for canonical, info in sorted(elsewhere.items()):
        chapters = ",".join(str(c) for c in info["chapters"])
        forms = ", ".join(sorted(info["forms"]))
        print(f"{canonical}\t({info['kind']})\tch {chapters}\t{forms}")
    print()

    print(f"## Unresolved, never linked: {len(never)} canonical form(s)\n")
    by_kind: Dict[str, List[str]] = defaultdict(list)
    for canonical, info in never.items():
        by_kind[info["kind"]].append(canonical)
    for kind in sorted(by_kind):
        canonicals = sorted(by_kind[kind])
        print(f"# {kind} ({len(canonicals)})")
        for canonical in canonicals:
            info = never[canonical]
            chapters = ",".join(str(c) for c in info["chapters"])
            forms = ", ".join(sorted(info["forms"]))
            print(f"{canonical}\tch {chapters}\t{forms}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("anchor", help="anchor-<lang>.jsonl to summarize")
    args = parser.parse_args()

    records = load_records(args.anchor)
    by_bengali = collect_by_bengali(records)
    unresolved = collect_unresolved(records)

    report_drift(by_bengali)
    report_unresolved(unresolved, by_bengali)
    return 0


if __name__ == "__main__":
    sys.exit(main())
