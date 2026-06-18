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

A second pass then prints a pairwise **disagreement analysis** for every pair
of methods: a 3x3 verdict agreement matrix plus, for each question where one
method strictly beats the other, whether the loser actually had every gold
chapter in its context. A non-empty `dropped` set means the loser never saw that
chapter at all — a **missed-context** loss (for Extract this is a Phase 1 false
negative, for RAG a retrieval miss); an empty set means the loser held all the
evidence and still mis-synthesized — a **synthesis** loss. This isolates the
lever behind each off-diagonal cell: retrieval/filtering vs. answering.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA_EVAL = Path(__file__).resolve().parent

# Verdict ordering for display (best first) and ranking (higher = better). The
# agreement matrix is indexed [rank_a][rank_b]; "strictly better" is rank_a >
# rank_b.
VERDICTS = ("correct", "partial", "incorrect")
VERDICT_RANK = {"correct": 2, "partial": 1, "incorrect": 0}


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


def _by_qid(records: list[dict]) -> dict[int, dict]:
    """Index answer/judge records by their 1-origin `question_id`."""
    return {r["question_id"]: r for r in records}


def _fmt_chapters(xs) -> str:
    return "[" + ",".join(str(x) for x in xs) + "]" if xs else "[]"


def disagreement(label_a: str, ans_a: dict[int, dict], judge_a: dict[int, dict],
                 label_b: str, ans_b: dict[int, dict], judge_b: dict[int, dict],
                 gold: dict[int, dict]) -> dict:
    """Question-by-question verdict comparison between two methods.

    Iterates over the question ids shared by both methods' answers and judges.
    Returns:
      matrix    — 3x3 counts indexed [rank_a][rank_b] (rank from VERDICT_RANK).
      a_beats_b — per-question records where A is strictly better than B, each:
        {qid, type, gold (sorted list), vw, vl (winner/loser verdicts), dropped
        (sorted gold chapters missing from the *loser's* `expanded`)}.
      b_beats_a — symmetric, with `dropped` measured against A's context.

    A non-empty `dropped` marks a **missed-context** loss: the loser never had
    that gold chapter in context (for Extract, a Phase 1 false negative; for
    RAG, a retrieval miss). An empty `dropped` marks a **synthesis** loss: the
    loser held every gold chapter yet still mis-synthesized the answer.
    """
    common = sorted(set(judge_a) & set(judge_b) & set(ans_a) & set(ans_b))
    matrix = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    a_beats_b: list[dict] = []
    b_beats_a: list[dict] = []
    for qid in common:
        va, vb = judge_a[qid]["verdict"], judge_b[qid]["verdict"]
        matrix[VERDICT_RANK[va]][VERDICT_RANK[vb]] += 1
        ra, rb = VERDICT_RANK[va], VERDICT_RANK[vb]
        if ra == rb:
            continue
        g = gold[qid]["chapters"]
        if ra > rb:
            a_beats_b.append({
                "qid": qid, "type": gold[qid]["type"], "gold": sorted(g),
                "vw": va, "vl": vb,
                "dropped": sorted(g - used_chapters(ans_b[qid]["expanded"])),
            })
        else:
            b_beats_a.append({
                "qid": qid, "type": gold[qid]["type"], "gold": sorted(g),
                "vw": vb, "vl": va,
                "dropped": sorted(g - used_chapters(ans_a[qid]["expanded"])),
            })
    return {"matrix": matrix, "a_beats_b": a_beats_b, "b_beats_a": b_beats_a}


def _print_matrix(label_a: str, label_b: str, matrix: list[list[int]]) -> None:
    w = max(len(f"{lab}:{v}") for lab in (label_a, label_b) for v in VERDICTS)
    w = max(w, len(f"{label_b} total"), 7)
    print(f"Agreement matrix (rows = {label_a}, cols = {label_b}):")
    print(" " * w, end="")
    for v in VERDICTS:
        print(f"  {label_b + ':' + v:>{w}}", end="")
    print(f"  | {label_a} total")
    col_tot = [0, 0, 0]
    for va in VERDICTS:
        print(f"{label_a + ':' + va:<{w}}", end="")
        row = 0
        for vi, vb in enumerate(VERDICTS):
            c = matrix[VERDICT_RANK[va]][VERDICT_RANK[vb]]
            col_tot[vi] += c
            row += c
            print(f"  {c:>{w}}", end="")
        print(f"  | {row:>{w}}")
    print(f"{label_b + ' total':<{w}}", end="")
    for t in col_tot:
        print(f"  {t:>{w}}", end="")
    print(f"  | {sum(col_tot):>{w}}")


def _print_disagree_list(winner: str, loser: str,
                         recs: list[dict]) -> tuple[int, int]:
    """Print the questions where `winner` strictly beats `loser`.

    Returns (missed_context, synthesis) counts. `vw`/`vl` in each record are the
    winner/loser verdicts.
    """
    miss = sum(1 for r in recs if r["dropped"])
    synth = len(recs) - miss
    label = f"{winner} beats {loser} ({len(recs)})"
    if recs:
        label += f": {miss} missed-context, {synth} synthesis"
    print(label)
    for r in recs:
        g = _fmt_chapters(r["gold"])
        d = _fmt_chapters(r["dropped"]) if r["dropped"] else "—"
        cls = "missed context" if r["dropped"] else "synthesis"
        print(f"  Q{r['qid']:<3} {r['type']:<7} gold{g:<16} "
              f"{winner}:{r['vw']:<9} > {loser}:{r['vl']:<9} "
              f"dropped {d:<14} {cls}")
    return miss, synth


def print_disagreement(label_a: str, label_b: str, result: dict) -> None:
    print("=" * 78)
    print(f"Disagreement: {label_a} vs {label_b}")
    print("-" * 78)
    _print_matrix(label_a, label_b, result["matrix"])
    print()
    m1, s1 = _print_disagree_list(label_a, label_b, result["a_beats_b"])
    print()
    m2, s2 = _print_disagree_list(label_b, label_a, result["b_beats_a"])
    print()
    n1, n2 = len(result["a_beats_b"]), len(result["b_beats_a"])
    print(f"Summary: {label_a} beats {label_b} on {n1} "
          f"({m1} missed-context, {s1} synthesis); "
          f"{label_b} beats {label_a} on {n2} "
          f"({m2} missed-context, {s2} synthesis).")
    print()


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

    if len(loaded) >= 2:
        print("=" * 78)
        print("Pairwise disagreement (verdict agreement matrix + loss class)")
        print("=" * 78)
        print()
        print("Loss class: 'missed context' = the loser never had a gold chapter\n"
              "in its context — for Extract that is a Phase 1 false negative, for\n"
              "RAG a retrieval miss. 'synthesis' = the loser held all gold chapters\n"
              "yet still mis-synthesized.")
        print()
        ans_by = {label: _by_qid(a) for label, (a, _j) in loaded.items()}
        judge_by = {label: _by_qid(j) for label, (_a, j) in loaded.items()}
        labels = list(loaded.keys())
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                la, lb = labels[i], labels[j]
                result = disagreement(la, ans_by[la], judge_by[la],
                                      lb, ans_by[lb], judge_by[lb], gold)
                print_disagreement(la, lb, result)


if __name__ == "__main__":
    main()
