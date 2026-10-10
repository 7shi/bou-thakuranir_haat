#!/usr/bin/env python3
"""Relate the gold-answer check to the Japanese gap under Ternary.

The claims stated in the English text only ("ja-only missing", defined in
../../gold-check/claims.py) are details a Japanese answer could not give. Per
question, the table lists those claims and the mean ja − en Ternary score over
every model in ../ternary/ (1 for correct, 0.5 for partial, 0 for incorrect,
in points out of 100 per question). The summary then measures the gap over
all models on the questions without a ja-only missing claim and on those with
one, with a two-sided sign test over the models.
"""

import csv
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
sys.path.insert(0, str(RESULTS.parent / "gold-check"))

from claims import load, ja_only_missing  # noqa: E402

VERDICTS = ["correct", "partial", "incorrect"]
WEIGHT = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def load_scores(path: Path) -> dict[int, float]:
    with open(path, encoding="utf-8") as f:
        return {int(r["qid"]): WEIGHT[max(VERDICTS, key=lambda v: float(r[v]))]
                for r in csv.DictReader(f, delimiter="\t")}


def sign_test(neg: int, pos: int) -> float:
    n = neg + pos
    k = min(neg, pos)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0


def gap_row(label: str, qids: set[int], models: dict[str, tuple[dict, dict]]) -> str:
    if not qids:
        return f"| {label} | 0 | — | — | — | — | — | — |"
    diffs = []
    for en, ja in models.values():
        diffs.append(sum(ja[q] - en[q] for q in qids) * 100 / len(qids))
    en_mean = sum(sum(en[q] for q in qids) * 100 / len(qids) for en, _ in models.values()) / len(models)
    ja_mean = sum(sum(ja[q] for q in qids) * 100 / len(qids) for _, ja in models.values()) / len(models)
    neg = sum(d < 0 for d in diffs)
    pos = sum(d > 0 for d in diffs)
    return (f"| {label} | {len(qids)} | {en_mean:.2f} | {ja_mean:.2f} | {ja_mean - en_mean:+.2f} "
            f"| {neg} | {pos} | {sign_test(neg, pos):.2g} |")


def main():
    questions, _, check = load()
    ja_only, _ = ja_only_missing(check)

    models = {}
    for p in sorted((RESULTS / "ternary").glob("ceiling-*-en.tsv")):
        ja = p.with_name(p.name.removesuffix("-en.tsv") + "-ja.tsv")
        if ja.exists():
            models[p.name.removesuffix("-en.tsv")] = (load_scores(p), load_scores(ja))

    print("| Q | Type | ja-only missing | ja − en |")
    print("| ---: | :--- | :--- | ---: |")
    for qid in ja_only:
        gap = sum(ja[qid] - en[qid] for en, ja in models.values()) * 100 / len(models)
        print(f"| {qid} | {questions[qid - 1]['type']} | {', '.join(map(str, ja_only[qid])) or '—'} "
              f"| {gap:+.1f} |")

    checked = set(ja_only)
    with_missing = {q for q in checked if ja_only[q]}
    print(f"\nModels: {len(models)}; questions checked: {len(checked)}")
    print("\n| Questions | n | en | ja | ja − en | ja < en | ja > en | Sign test |")
    print("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for qtype in (None, "single", "cross"):
        typed = {q for q in checked if qtype is None or questions[q - 1]["type"] == qtype}
        suffix = f" ({qtype})" if qtype else ""
        print(gap_row(f"All{suffix}", typed, models))
        print(gap_row(f"Without ja-only missing{suffix}", typed - with_missing, models))
        print(gap_row(f"With ja-only missing{suffix}", typed & with_missing, models))


if __name__ == "__main__":
    main()
