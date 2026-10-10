#!/usr/bin/env python3
"""Summarize the gold-answer check: which claims each text states.

A claim is "ja-only missing" when the English text states it and the Japanese
text does not (missing or contradicted), and "missing in both texts" when
neither states it. Prints the en × ja verdict matrix, a per-question table of
the claims' verdicts in both texts, and both claim lists. No LLM calls.

ja_only_missing() is the one place that defines these sets;
../results/ja2en/gold_gap.py imports it to relate them to the Japanese gap.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VERDICTS = ["stated", "missing", "contradicted"]


def load_jsonl(path: Path) -> dict[int, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["question_id"]: r for r in map(json.loads, filter(str.strip, f))}


def load() -> tuple[list[dict], dict[int, dict], dict[str, dict[int, dict]]]:
    questions = [json.loads(l) for l in open(ROOT / "questions-en.jsonl", encoding="utf-8")]
    facts = load_jsonl(HERE / "facts.jsonl")
    check = {lang: load_jsonl(HERE / f"check-{lang}.jsonl") for lang in ("en", "ja")}
    return questions, facts, check


def verdicts(check: dict[str, dict[int, dict]], qid: int, lang: str) -> dict[int, str]:
    return {c["id"]: c["verdict"] for c in check[lang][qid]["claims"]}


def ja_only_missing(check: dict[str, dict[int, dict]]) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    """Per question checked in both languages: the claim ids stated in the
    English text only, and those stated in neither."""
    ja_only: dict[int, list[int]] = {}
    both_missing: dict[int, list[int]] = {}
    for qid in sorted(check["en"]):
        if qid not in check["ja"]:
            continue
        en_c, ja_c = verdicts(check, qid, "en"), verdicts(check, qid, "ja")
        ja_only[qid] = [i for i in en_c if en_c[i] == "stated" and ja_c[i] != "stated"]
        both_missing[qid] = [i for i in en_c if en_c[i] != "stated" and ja_c[i] != "stated"]
    return ja_only, both_missing


def main():
    questions, facts, check = load()
    ja_only, both_missing = ja_only_missing(check)

    def counts(claims):
        return "/".join(str(sum(c["verdict"] == v for c in claims)) for v in VERDICTS)

    matrix = {(a, b): 0 for a in VERDICTS for b in VERDICTS}
    for qid in ja_only:
        ja_c = verdicts(check, qid, "ja")
        for i, v in verdicts(check, qid, "en").items():
            matrix[v, ja_c[i]] += 1
    print("| en \\ ja | " + " | ".join(VERDICTS) + " |")
    print("| :--- | " + " | ".join(["---:"] * 3) + " |")
    for a in VERDICTS:
        print(f"| **{a}** | " + " | ".join(str(matrix[a, b]) for b in VERDICTS) + " |")

    print("\n| Q | Type | Claims | en (s/m/c) | ja (s/m/c) | ja-only missing |")
    print("| ---: | :--- | ---: | :--- | :--- | :--- |")
    for qid in ja_only:
        print(f"| {qid} | {questions[qid - 1]['type']} | {len(facts[qid]['facts'])} "
              f"| {counts(check['en'][qid]['claims'])} | {counts(check['ja'][qid]['claims'])} "
              f"| {', '.join(map(str, ja_only[qid])) or '—'} |")
    print(f"\nQuestions checked: {len(ja_only)}; claims: {sum(matrix.values())}")

    for title, table in (("ja-only missing", ja_only), ("Missing in both texts", both_missing)):
        rows = [(q, i) for q in sorted(table) for i in table[q]]
        print(f"\n### {title} ({len(rows)} claims)\n")
        for q, i in rows:
            ja_claim = next(c for c in check["ja"][q]["claims"] if c["id"] == i)
            print(f"- Q{q}.{i} [{ja_claim['verdict']}] {facts[q]['facts'][i - 1]}")
            print(f"  - ja: {ja_claim['reason']}")


if __name__ == "__main__":
    main()
