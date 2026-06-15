#!/usr/bin/env python3
"""Aggregate and compare RAG vs. per-chapter extraction results.

Pure mechanical aggregation of existing files — no LLM calls. Prints one
comparison table to the terminal (methods as rows). Two independent axes:

1. Answer accuracy (from results/judge-<method>.jsonl): raw correct / partial /
   incorrect counts plus a weighted score = (correct + 0.5*partial) / total.
   `partial` stays visible as its own column so the half-credit weighting never
   hides the raw distribution. See the convergent-validity caveat in README.md:
   the gold is the Gemini full-text baseline, so Extract >= RAG is expected.

2. Chapter retrieval (mechanical, from each method's `expanded` vs gold
   `chapters` in questions-en.jsonl):
   - recall: per-question complete coverage — 1 if gold ⊆ used else 0, meaned.
   - precision: mean of |gold ∩ used| / |used| per question.

RAG `expanded` entries are "chapter:segment" strings (take the part before ':');
extract entries are bare "chapter" strings.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).resolve().parent / "results"


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_gold_chapters(path: Path) -> dict[int, set[int]]:
    """1-origin line number = question_id → set of gold chapter numbers."""
    gold: dict[int, set[int]] = {}
    with open(path, encoding="utf-8") as f:
        for qid, line in enumerate((l for l in f if l.strip()), start=1):
            gold[qid] = set(json.loads(line)["chapters"])
    return gold


def used_chapters(expanded: list[str]) -> set[int]:
    """Reduce a method's `expanded` list to a set of chapter numbers.

    RAG entries look like "2:1" (chapter:segment); extract entries look like
    "2" (bare chapter). Splitting on ':' handles both.
    """
    return {int(e.split(":")[0]) for e in expanded}


def accuracy(judge: list[dict]) -> dict:
    counts = {"correct": 0, "partial": 0, "incorrect": 0}
    for rec in judge:
        counts[rec["verdict"]] += 1
    total = len(judge)
    weighted = (counts["correct"] + 0.5 * counts["partial"]) / total if total else 0.0
    return {**counts, "total": total, "weighted": weighted}


def retrieval(answers: list[dict], gold: dict[int, set[int]]) -> dict:
    recall_sum = 0.0
    prec_sum = 0.0
    n = len(answers)
    for rec in answers:
        g = gold[rec["question_id"]]
        used = used_chapters(rec["expanded"])
        recall_sum += 1.0 if g <= used else 0.0
        prec_sum += (len(g & used) / len(used)) if used else 0.0
    return {"recall": recall_sum / n if n else 0.0,
            "precision": prec_sum / n if n else 0.0}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input", default=str(ROOT / "questions-en.jsonl"),
                        help="questions JSONL (gold standard)")
    args = parser.parse_args()

    gold = load_gold_chapters(Path(args.input))

    methods = {
        "RAG": ("rag.jsonl", "judge-rag.jsonl"),
        "Extract": ("extract.jsonl", "judge-extract.jsonl"),
    }

    rows = {}
    for name, (ans_file, judge_file) in methods.items():
        acc = accuracy(load_jsonl(RESULTS / judge_file))
        ret = retrieval(load_jsonl(RESULTS / ans_file), gold)
        rows[name] = {**acc, **ret}

    header = (f"{'method':<8} {'correct':>7} {'partial':>7} {'incorrect':>9} "
              f"{'weighted':>9} {'ch.recall':>9} {'ch.prec':>8}")
    print(header)
    print("-" * len(header))
    for name, r in rows.items():
        print(f"{name:<8} {r['correct']:>7} {r['partial']:>7} {r['incorrect']:>9} "
              f"{r['weighted']:>9.3f} {r['recall']:>9.3f} {r['precision']:>8.3f}")


if __name__ == "__main__":
    main()
