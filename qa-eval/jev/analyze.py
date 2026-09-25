#!/usr/bin/env python3
"""Reproduce the tables in README.md from the --debug logs in this directory.

Reads every jev-*.jsonl written by `judge-jev.py --debug` (the raw response,
holding the Choice `verdict` and the Noul `correct`) and pairs it with the
judge.py (qwen) verdicts in the matching qa-eval result directory:
  results-en/jev-<stem>.jsonl ↔ ../results-en/judge-<stem>.jsonl
  results/jev-<stem>.jsonl    ↔ ../results/judge-<stem>.jsonl

A Noul verdict is derived with two thresholds on the yes probability `p`:
correct if p >= hi, partial if lo <= p < hi, incorrect otherwise.

Sets: "retrieval" is results-en/ (answers from the retrieval pipelines),
"ceiling" is results/ (Ceiling answers of several answerer models).
"""

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
QA_EVAL = HERE.parent

VERDICTS = ["correct", "partial", "incorrect"]
GRID = [i / 100 for i in range(101)]


def load_set(subdir: str) -> dict[str, list[dict]]:
    """{stem: [row]} with qwen, choice, P(choice), noul and usage per question."""
    sets = {}
    for path in sorted((HERE / subdir).glob("jev-*.jsonl")):
        stem = path.stem[len("jev-"):]
        with open(QA_EVAL / subdir / f"judge-{stem}.jsonl", encoding="utf-8") as f:
            qwen = {r["question_id"]: r["verdict"] for r in map(json.loads, f) if r}
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                answers = rec["response"]["answers"]
                rows.append({
                    "qwen": qwen[rec["question_id"]],
                    "choice": answers["verdict"]["choice"],
                    "noul": answers["correct"]["noul"],
                    "usage": rec["response"]["usage"],
                })
        sets[stem] = rows
    return sets


def by_noul(p: float, lo: float, hi: float) -> str:
    return "correct" if p >= hi else "partial" if p >= lo else "incorrect"


def weighted(verdicts: list[str]) -> float:
    return 100 * (verdicts.count("correct") + 0.5 * verdicts.count("partial")) / len(verdicts)


def counts(verdicts: list[str]) -> str:
    return "/".join(str(verdicts.count(v)) for v in VERDICTS)


def agree(a: list[str], b: list[str]) -> int:
    return sum(x == y for x, y in zip(a, b))


def best_thresholds(rows: list[dict], target: str) -> tuple[int, float, float]:
    """(agreements, lo, hi) maximizing agreement of the Noul verdict with `target`."""
    ref = [r[target] for r in rows]
    return max((agree([by_noul(r["noul"], lo, hi) for r in rows], ref), lo, hi)
               for lo in GRID for hi in GRID if hi >= lo)


def confusion(rows: list[dict], row_key: str, col: list[str], col_name: str) -> None:
    print(f"| {row_key} \\ {col_name} | " + " | ".join(VERDICTS) + " |")
    print("| --- | ---: | ---: | ---: |")
    for v in VERDICTS:
        cells = [sum(1 for r, c in zip(rows, col) if r[row_key] == v and c == w) for w in VERDICTS]
        print(f"| {v} | " + " | ".join(map(str, cells)) + " |")


def spread(values: list[float]) -> str:
    xs = sorted(values)
    if not xs:
        return "—"
    return f"{xs[0]:.2f} / {xs[len(xs) // 2]:.2f} / {xs[-1]:.2f}"


def main():
    retrieval = load_set("results-en")
    ceiling = load_set("results")
    r_rows = [r for rows in retrieval.values() for r in rows]
    c_rows = [r for rows in ceiling.values() for r in rows]

    print(f"## Retrieval set: agreement with qwen (n={len(r_rows)})\n")
    qwen = [r["qwen"] for r in r_rows]
    print("| Judge | c/p/i | Weighted | Agree w/ qwen | Agree w/ Choice |")
    print("| --- | --- | ---: | ---: | ---: |")
    choice = [r["choice"] for r in r_rows]
    print(f"| qwen | {counts(qwen)} | {weighted(qwen):.1f} | — | {agree(qwen, choice)} |")
    print(f"| Choice | {counts(choice)} | {weighted(choice):.1f} | {agree(choice, qwen)} | — |")
    for hi in (0.35, 0.6, 0.8):
        noul = [by_noul(r["noul"], 0.1, hi) for r in r_rows]
        print(f"| Noul 0.1/{hi} | {counts(noul)} | {weighted(noul):.1f} | "
              f"{agree(noul, qwen)} | {agree(noul, choice)} |")
    n, lo, hi = best_thresholds(r_rows, "qwen")
    print(f"\nBest Noul thresholds vs qwen: {lo}/{hi} → {n}/{len(r_rows)}")
    total = 0
    for stem in retrieval:
        train = [r for s, rows in retrieval.items() if s != stem for r in rows]
        _, lo, hi = best_thresholds(train, "qwen")
        test = retrieval[stem]
        a = agree([by_noul(r["noul"], lo, hi) for r in test], [r["qwen"] for r in test])
        total += a
    print(f"Leave-one-file-out vs qwen: {total}/{len(r_rows)}\n")
    confusion(r_rows, "qwen", choice, "Choice")
    print("\nNoul yes probability by qwen verdict (min / median / max):\n")
    for v in VERDICTS:
        xs = [r["noul"] for r in r_rows if r["qwen"] == v]
        print(f"- {v} (n={len(xs)}): {spread(xs)}")

    print(f"\n## Ceiling set: weighted score per answerer model (n={len(c_rows)})\n")
    print("| Model | qwen | Choice | Noul 0.1/0.6 | Noul 0.1/0.8 | Mean Noul |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for stem, rows in sorted(ceiling.items(), key=lambda kv: -weighted([r["choice"] for r in kv[1]])):
        model = stem.removeprefix("ceiling-").removesuffix("-en").removesuffix("-ja")
        cells = [weighted([r["qwen"] for r in rows]), weighted([r["choice"] for r in rows]),
                 weighted([by_noul(r["noul"], 0.1, 0.6) for r in rows]),
                 weighted([by_noul(r["noul"], 0.1, 0.8) for r in rows])]
        mean = statistics.mean(r["noul"] for r in rows)
        print(f"| `{model}` | " + " | ".join(f"{c:.0f}" for c in cells) + f" | {mean:.3f} |")

    print("\n## Noul thresholds reproducing the Choice\n")
    print("| Set | Noul 0.1/0.8 | Best | Best thresholds |")
    print("| --- | ---: | ---: | --- |")
    for name, rows in (("retrieval", r_rows), ("ceiling", c_rows)):
        ref = [r["choice"] for r in rows]
        a = agree([by_noul(r["noul"], 0.1, 0.8) for r in rows], ref)
        n, lo, hi = best_thresholds(rows, "choice")
        print(f"| {name} | {a}/{len(rows)} | {n}/{len(rows)} | {lo}/{hi} |")
    print("\nNoul yes probability by Choice verdict (min / median / max):\n")
    print("| Choice | retrieval | ceiling |")
    print("| --- | --- | --- |")
    for v in VERDICTS:
        cells = [spread([r["noul"] for r in rows if r["choice"] == v]) for rows in (r_rows, c_rows)]
        print(f"| {v} | " + " | ".join(cells) + " |")

    print("\n## Token usage (Choice + Noul in one request)\n")
    print("| Set | Requests | Input total | Input / request | Output / request |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for name, rows in (("retrieval", r_rows), ("ceiling", c_rows)):
        inp = [r["usage"]["input_tokens"] for r in rows]
        out = [r["usage"]["output_tokens"] for r in rows]
        print(f"| {name} | {len(rows)} | {sum(inp)} | {statistics.mean(inp):.0f} | "
              f"{statistics.mean(out):.0f} |")


if __name__ == "__main__":
    main()
