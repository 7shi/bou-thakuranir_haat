#!/usr/bin/env python3
"""Aggregate and compare Vector vs. per-chapter extraction results.

Pure mechanical aggregation of existing files — no LLM calls. Prints one
comparison table to the terminal (methods as rows). Two independent axes:

1. Answer accuracy (from results-<lang>/judge-<method>.jsonl): raw correct / partial /
   incorrect counts plus a weighted score = (correct + 0.5*partial) / total.
   `partial` stays visible as its own column so the half-credit weighting never
   hides the raw distribution. See the convergent-validity caveat in README.md:
   the gold is the Gemini full-text baseline, so Extract >= Vector is expected.

2. Chapter retrieval (mechanical, from each method's `expanded` vs gold
   `chapters` in questions-<lang>.jsonl):
   - recall: per-question complete coverage — 1 if gold ⊆ used else 0, meaned.
   - precision: mean of |gold ∩ used| / |used| per question.

Vector `expanded` entries are "chapter:segment" strings (take the part before ':');
extract entries are bare "chapter" strings.

Both axes are broken down by the gold `type` field (single / cross), with an
`all` scope covering every question, so single-passage vs. cross-reference
performance can be compared side by side.

**Method discovery** is automatic from the results directory, so a newly judged
depth or method appears with no code change. Each `vector<k>.jsonl` with a
matching `judge-vector<k>.jsonl` becomes a `Vector k=<k>` row, each
`hybrid<k>.jsonl` a `Hybrid k=<k>` row; then Extract, Filter2, Filter3, and
Ceiling are appended when their files exist. Rows are ordered `Vector k=5`,
remaining `Vector k=<k>` by ascending k, `Hybrid k=<k>` by ascending k, Extract,
Filter2, Filter3, Ceiling — so the union sits beside its dense-only Vector peer,
the stricter filter ahead of the looser one, and Ceiling anchors the table last
as the perfect-retrieval upper bound.

A second pass then prints a pairwise **disagreement analysis** for every pair
of methods: a 3x3 verdict agreement matrix plus, for each question where one
method strictly beats the other, whether the loser actually had every gold
chapter in its context. A non-empty `dropped` set means the loser never saw that
chapter at all — a **missed-context** loss (for Extract this is a Phase 1 false
negative, for Filter a wrong `no` verdict, for Vector a retrieval miss); an
empty set means the loser held all the evidence and still mis-synthesized — a
**synthesis** loss. This isolates the lever behind each off-diagonal cell:
retrieval/filtering vs. answering.
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

    Vector entries look like "2:1" (chapter:segment); extract entries look like
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
    Filter, a wrong `no` verdict; for Vector, a retrieval miss). An empty
    `dropped` marks a **synthesis** loss: the loser held every gold chapter yet
    still mis-synthesized the answer.
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

    Vector variants are discovered from results-<lang>/vector<k>.jsonl answer
    files (e.g. vector5.jsonl → "Vector k=5", vector10.jsonl → "Vector k=10").
    A variant is included only when its judge-vector<k>.jsonl also exists, so a
    not-yet-judged vector15.jsonl simply doesn't appear. Hybrid variants
    (dense ∪ BM25 union, the Phase 2 QA of the HYBRID.md Union approach) are
    discovered the same way from hybrid<k>.jsonl → "Hybrid k=<k>". Extract
    (per-chapter summary) and Filter (per-chapter relevance) are appended when
    both their answer and judge files exist. Filter has two verdict
    granularities: filter2.jsonl (yes/no) and filter3.jsonl (yes/maybe/no, the
    default), and both are appended when present. Order: Vector k=5 first, then
    Vector k=<k> by ascending k, then Hybrid k=<k> by ascending k, then
    Extract, then Filter2, then Filter3, then Ceiling (perfect-retrieval
    ceiling) — so the k=5 baseline sits beside its deeper-retrieval variants,
    the hybrid union sits beside its Vector peers as a direct retrieval
    comparison, the per-chapter methods sit next to each other for direct
    comparison, the stricter two-level filter sits ahead of its looser
    three-level counterpart, and Ceiling anchors the table as the upper bound
    that strips out retrieval entirely.
    """
    def vector_key(stem: str) -> int:
        m = re.fullmatch(r"vector(\d+)", stem)
        return int(m.group(1)) if m else (1 << 30)

    found: list[tuple[str, str, str]] = []
    vector_files = [p for p in results.glob("vector*.jsonl")
                    if re.fullmatch(r"vector\d+", p.stem)]
    for ans in sorted(vector_files, key=lambda p: vector_key(p.stem)):
        stem = ans.stem
        k = int(re.fullmatch(r"vector(\d+)", stem).group(1))
        label = f"Vector k={k}"  # vector5 → "Vector k=5", vector10 → "Vector k=10"
        judge = f"judge-{stem}.jsonl"
        if (results / judge).exists():
            found.append((label, ans.name, judge))

    # Vector-line: line-level retrieval (build_index.py --line / answer_vector.py
    # --line). Same discovery shape as Vector — vector-line<k>.jsonl with a
    # matching judge — grouped right after the segment Vector variants.
    line_files = [p for p in results.glob("vector-line*.jsonl")
                  if re.fullmatch(r"vector-line\d+", p.stem)]
    for ans in sorted(line_files, key=lambda p: int(re.fullmatch(r"vector-line(\d+)", p.stem).group(1))):
        stem = ans.stem
        k = int(re.fullmatch(r"vector-line(\d+)", stem).group(1))
        label = f"Vector-line k={k}"  # vector-line5 → "Vector-line k=5"
        judge = f"judge-{stem}.jsonl"
        if (results / judge).exists():
            found.append((label, ans.name, judge))

    # Hybrid: dense ∪ BM25 union (Phase 2 QA of the HYBRID.md Union approach).
    # Same discovery shape as Vector — hybrid<k>.jsonl with a matching judge.
    # English only (BM25 is English-only), so no Japanese results are expected.
    hybrid_files = [p for p in results.glob("hybrid*.jsonl")
                    if re.fullmatch(r"hybrid\d+", p.stem)]
    for ans in sorted(hybrid_files, key=lambda p: int(re.fullmatch(r"hybrid(\d+)", p.stem).group(1))):
        stem = ans.stem
        k = int(re.fullmatch(r"hybrid(\d+)", stem).group(1))
        label = f"Hybrid k={k}"  # hybrid5 → "Hybrid k=5", hybrid10 → "Hybrid k=10"
        judge = f"judge-{stem}.jsonl"
        if (results / judge).exists():
            found.append((label, ans.name, judge))

    if (results / "extract.jsonl").exists() and (results / "judge-extract.jsonl").exists():
        found.append(("Extract", "extract.jsonl", "judge-extract.jsonl"))
    # Filter2 (yes/no) first, then Filter3 (yes/maybe/no, default). Each is
    # included only when both its answer file and its judge file exist.
    for stem, label in [("filter2", "Filter2"), ("filter3", "Filter3")]:
        ans = f"{stem}.jsonl"
        judge = f"judge-{stem}.jsonl"
        if (results / ans).exists() and (results / judge).exists():
            found.append((label, ans, judge))
    # Ceiling: the gold chapters fed verbatim as context (no retrieval). A
    # perfect-retrieval ceiling appended last, since its losses are all
    # synthesis by definition — it isolates reading comprehension, not
    # retrieval, and sits below the retrieval strategies as the upper bound
    # they chase.
    if (results / "ceiling.jsonl").exists() and (results / "judge-ceiling.jsonl").exists():
        found.append(("Ceiling", "ceiling.jsonl", "judge-ceiling.jsonl"))
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

    # label → (answers, judge); insertion order = Vector k=5, Vector k=<k>…, Extract.
    loaded = {label: (load_jsonl(results / ans_file), load_jsonl(results / judge_file))
              for label, ans_file, judge_file in methods}

    header = (f"{'scope':<8} {'method':<16} {'n':>3} {'correct':>7} {'partial':>7} "
              f"{'incorrect':>9} {'weighted':>9} {'ch.recall':>9} {'ch.prec':>8}")
    print(header)
    print("-" * len(header))
    for scope_name, subset in scopes:
        for name, (answers, judge) in loaded.items():
            acc = accuracy(judge, subset)
            ret = retrieval(answers, gold, subset)
            print(f"{scope_name:<8} {name:<16} {acc['total']:>3} "
                  f"{acc['correct']:>7} {acc['partial']:>7} {acc['incorrect']:>9} "
                  f"{acc['weighted']:>9.3f} {ret['recall']:>9.3f} {ret['precision']:>8.3f}")
        print()

    if len(loaded) >= 2:
        print("=" * 78)
        print("Pairwise disagreement (verdict agreement matrix + loss class)")
        print("=" * 78)
        print()
        print("Loss class: 'missed context' = the loser never had a gold chapter\n"
              "in its context — for Extract that is a Phase 1 false negative (a\n"
              "wrong `None`), for Filter a wrong `no` verdict, for Vector a\n"
              "retrieval miss. 'synthesis' = the loser held all gold chapters yet\n"
              "still mis-synthesized.")
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
