#!/usr/bin/env python3
"""Relate the gold-answer check to the Japanese gap under Ternary.

A claim is "ja-only missing" when the English text states it and the Japanese
text does not (missing or contradicted). Per question, the table lists the
claims' verdicts in both texts and the mean ja − en Ternary score over every
model in ../ternary/ (1 for correct, 0.5 for partial, 0 for incorrect, in
points out of 100 per question). The summary then measures the gap over all
50 models on the questions without a ja-only missing claim and on those with
one, with a two-sided sign test over the models.
"""

import csv
import json
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
ROOT = RESULTS.parent.parent
VERDICTS = ["correct", "partial", "incorrect"]
WEIGHT = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def load_jsonl(path: Path) -> dict[int, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["question_id"]: r for r in map(json.loads, filter(str.strip, f))}


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
    questions = [json.loads(l) for l in open(ROOT / "questions-en.jsonl", encoding="utf-8")]
    facts = load_jsonl(HERE / "facts.jsonl")
    check = {lang: load_jsonl(HERE / f"check-{lang}.jsonl") for lang in ("en", "ja")}

    models = {}
    for p in sorted((RESULTS / "ternary").glob("ceiling-*-en.tsv")):
        ja = p.with_name(p.name.removesuffix("-en.tsv") + "-ja.tsv")
        if ja.exists():
            models[p.name.removesuffix("-en.tsv")] = (load_scores(p), load_scores(ja))

    def counts(claims):
        return "/".join(str(sum(c["verdict"] == v for c in claims))
                        for v in ("stated", "missing", "contradicted"))

    print("| Q | Type | Claims | en (s/m/c) | ja (s/m/c) | ja-only missing | ja − en |")
    print("| ---: | :--- | ---: | :--- | :--- | :--- | ---: |")
    ja_only: dict[int, list[int]] = {}
    both_missing: dict[int, list[int]] = {}
    for qid, q in enumerate(questions, start=1):
        if qid not in check["en"] or qid not in check["ja"]:
            continue
        en_c = {c["id"]: c["verdict"] for c in check["en"][qid]["claims"]}
        ja_c = {c["id"]: c["verdict"] for c in check["ja"][qid]["claims"]}
        ja_only[qid] = [i for i in en_c if en_c[i] == "stated" and ja_c[i] != "stated"]
        both_missing[qid] = [i for i in en_c if en_c[i] != "stated" and ja_c[i] != "stated"]
        gap = sum(ja[qid] - en[qid] for en, ja in models.values()) * 100 / len(models)
        print(f"| {qid} | {q['type']} | {len(facts[qid]['facts'])} | {counts(check['en'][qid]['claims'])} "
              f"| {counts(check['ja'][qid]['claims'])} | {', '.join(map(str, ja_only[qid])) or '—'} "
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

    for title, table in (("ja-only missing", ja_only), ("Missing in both texts", both_missing)):
        rows = [(q, i) for q in sorted(table) for i in table[q]]
        print(f"\n### {title} ({len(rows)} claims)\n")
        for q, i in rows:
            ja_claim = next(c for c in check["ja"][q]["claims"] if c["id"] == i)
            print(f"- Q{q}.{i} [{ja_claim['verdict']}] {facts[q]['facts'][i - 1]}")
            print(f"  - ja: {ja_claim['reason']}")


if __name__ == "__main__":
    main()
