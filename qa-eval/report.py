#!/usr/bin/env python3
"""Aggregate and compare RAG vs. per-chapter extraction results.

Pure mechanical aggregation of existing files — no LLM calls. Prints one
comparison table to the terminal (methods as rows). Two independent axes:

1. Answer accuracy (from results-<lang>/judge-<method>.jsonl): raw correct / partial /
   incorrect counts plus a weighted score = (correct + 0.5*partial) / total.
   `partial` stays visible as its own column so the half-credit weighting never
   hides the raw distribution. See the convergent-validity caveat in README.md:
   the gold is the Gemini full-text baseline, so Extract >= RAG is expected.

2. Chapter retrieval (mechanical, from each method's `expanded` vs gold
   `chapters` in questions-<lang>.jsonl):
   - recall: per-question complete coverage — 1 if gold ⊆ used else 0, meaned.
   - precision: mean of |gold ∩ used| / |used| per question.

RAG `expanded` entries are "chapter:segment" strings (take the part before ':');
extract entries are bare "chapter" strings.

Both axes are broken down by the gold `type` field (single / cross), with an
`all` scope covering every question, so single-passage vs. cross-reference
performance can be compared side by side.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA_EVAL = Path(__file__).resolve().parent


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_gold(path: Path) -> dict[int, dict]:
    """1-origin line number = question_id → {"chapters": set[int], "type": str}."""
    gold: dict[int, dict] = {}
    with open(path, encoding="utf-8") as f:
        for qid, line in enumerate((l for l in f if l.strip()), start=1):
            rec = json.loads(line)
            gold[qid] = {"chapters": set(rec["chapters"]),
                         "type": rec.get("type", "all")}
    return gold


def used_chapters(expanded: list[str]) -> set[int]:
    """Reduce a method's `expanded` list to a set of chapter numbers.

    RAG entries look like "2:1" (chapter:segment); extract entries look like
    "2" (bare chapter). Splitting on ':' handles both.
    """
    return {int(e.split(":")[0]) for e in expanded}


def accuracy(judge: list[dict], subset: set[int] | None = None) -> dict:
    counts = {"correct": 0, "partial": 0, "incorrect": 0}
    for rec in judge:
        if subset is not None and rec["question_id"] not in subset:
            continue
        counts[rec["verdict"]] += 1
    total = sum(counts.values())
    weighted = (counts["correct"] + 0.5 * counts["partial"]) / total if total else 0.0
    return {**counts, "total": total, "weighted": weighted}


def retrieval(answers: list[dict], gold: dict[int, dict],
              subset: set[int] | None = None) -> dict:
    recall_sum = 0.0
    prec_sum = 0.0
    n = 0
    for rec in answers:
        if subset is not None and rec["question_id"] not in subset:
            continue
        g = gold[rec["question_id"]]["chapters"]
        used = used_chapters(rec["expanded"])
        recall_sum += 1.0 if g <= used else 0.0
        prec_sum += (len(g & used) / len(used)) if used else 0.0
        n += 1
    return {"recall": recall_sum / n if n else 0.0,
            "precision": prec_sum / n if n else 0.0}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=["en", "ja"],
                        help="evaluation language (selects default gold questions and results-<lang> dir)")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (gold standard; default: questions-<lang>.jsonl)")
    args = parser.parse_args()

    args.input = args.input or str(ROOT / f"questions-{args.lang}.jsonl")
    results = QA_EVAL / f"results-{args.lang}"

    gold = load_gold(Path(args.input))

    # Scopes: "all" plus each gold type, ordered by first appearance (single → cross).
    types_present = sorted({g["type"] for g in gold.values()},
                           key=lambda t: min(q for q, g in gold.items() if g["type"] == t))
    scopes: list[tuple[str, set[int] | None]] = [("all", None)]
    scopes += [(t, {qid for qid, g in gold.items() if g["type"] == t})
               for t in types_present]

    methods = {
        "RAG": ("rag.jsonl", "judge-rag.jsonl"),
        "Extract": ("extract.jsonl", "judge-extract.jsonl"),
    }

    loaded = {name: (load_jsonl(results / ans_file), load_jsonl(results / judge_file))
              for name, (ans_file, judge_file) in methods.items()}

    header = (f"{'scope':<8} {'method':<8} {'n':>3} {'correct':>7} {'partial':>7} "
              f"{'incorrect':>9} {'weighted':>9} {'ch.recall':>9} {'ch.prec':>8}")
    print(header)
    print("-" * len(header))
    for scope_name, subset in scopes:
        for name, (answers, judge) in loaded.items():
            acc = accuracy(judge, subset)
            ret = retrieval(answers, gold, subset)
            print(f"{scope_name:<8} {name:<8} {acc['total']:>3} "
                  f"{acc['correct']:>7} {acc['partial']:>7} {acc['incorrect']:>9} "
                  f"{acc['weighted']:>9.3f} {ret['recall']:>9.3f} {ret['precision']:>8.3f}")
        print()


if __name__ == "__main__":
    main()
