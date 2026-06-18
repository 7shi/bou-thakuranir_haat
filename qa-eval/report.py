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
import re
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


def discover_methods(results: Path) -> list[tuple[str, str, str]]:
    """(label, answer_file, judge_file) triples for every available method.

    RAG variants are discovered from results-<lang>/rag*.jsonl answer files:
      rag.jsonl      → "RAG"        (the default k=5 baseline)
      rag-<k>.jsonl  → "RAG-<k>"    (e.g. rag-10.jsonl → "RAG-10")
    A variant is included only when its judge-<stem>.jsonl also exists, so a
    not-yet-judged rag-15.jsonl simply doesn't appear. Extract is appended last
    when both extract.jsonl and judge-extract.jsonl exist. Order: the default
    RAG first, then RAG-<k> by ascending k, then Extract — so the k=5 baseline
    sits beside its deeper-retrieval variants for direct comparison.
    """
    def rag_key(stem: str) -> tuple[int, int]:
        if stem == "rag":
            return (0, 0)
        m = re.fullmatch(r"rag-(\d+)", stem)
        return (1, int(m.group(1))) if m else (2, 0)

    found: list[tuple[str, str, str]] = []
    rag_files = [p for p in results.glob("rag*.jsonl")
                 if p.stem == "rag" or re.fullmatch(r"rag-\d+", p.stem)]
    for ans in sorted(rag_files, key=lambda p: rag_key(p.stem)):
        stem = ans.stem
        label = "RAG" if stem == "rag" else stem.upper()  # rag-10 → RAG-10
        judge = f"judge-{stem}.jsonl"
        if (results / judge).exists():
            found.append((label, ans.name, judge))

    if (results / "extract.jsonl").exists() and (results / "judge-extract.jsonl").exists():
        found.append(("Extract", "extract.jsonl", "judge-extract.jsonl"))
    return found


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

    methods = discover_methods(results)
    if not methods:
        print(f"No answer/judge pairs found in {results}")
        return

    # label → (answers, judge); insertion order = RAG, RAG-<k>…, Extract.
    loaded = {label: (load_jsonl(results / ans_file), load_jsonl(results / judge_file))
              for label, ans_file, judge_file in methods}

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
