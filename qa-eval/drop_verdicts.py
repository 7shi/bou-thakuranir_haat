#!/usr/bin/env python3
"""Remove the verdicts of selected questions so that the judges grade them again.

The judges are resume-safe by question ID: they skip a question that already
has a verdict. After a gold answer is corrected, removing its verdicts and
re-running the usual judge commands grades only those questions, appended at
the end of each file; sort_verdicts.py then puts the rows back in qid order.

Verdict files, next to each answer file in results-en/, results-ja/ and
results/:

  judge/<stem>.jsonl                          judge.py, one JSON record per line
  {ternary,openai,jev,nimble}/<stem>.tsv      the TSV judges, after a header line

MODELS.tsv is left as it is, so the re-run must use the recorded model and
scheme. Files without any of the questions are not rewritten.
"""

import argparse
import json
from pathlib import Path

QA_EVAL = Path(__file__).resolve().parent
SETS = ["results-en", "results-ja", "results"]
JUDGES = ["judge", "ternary", "openai", "jev", "nimble"]


def verdict_files(sets: list[str], judges: list[str]) -> list[Path]:
    files = []
    for s in sets:
        for judge in judges:
            if judge == "judge":
                files += sorted((QA_EVAL / s / judge).glob("*.jsonl"))
            else:
                files += sorted(p for p in (QA_EVAL / s / judge).glob("*.tsv")
                                if p.name != "MODELS.tsv")
    return files


def row_qid(line: str, path: Path) -> int:
    if path.suffix == ".jsonl":
        return json.loads(line)["question_id"]
    return int(line.split("\t", 1)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("qids", nargs="+", type=int, help="question IDs to re-grade")
    parser.add_argument("-s", "--sets", nargs="+", default=SETS, choices=SETS)
    parser.add_argument("-j", "--judges", nargs="+", default=JUDGES, choices=JUDGES)
    args = parser.parse_args()

    qids = set(args.qids)
    changed = rows = 0
    for path in verdict_files(args.sets, args.judges):
        with open(path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        head = lines[:1] if path.suffix == ".tsv" else []
        body = lines[len(head):]
        kept = [l for l in body if row_qid(l, path) not in qids]
        if len(kept) == len(body):
            continue
        path.write_text("\n".join(head + kept) + "\n", encoding="utf-8")
        changed += 1
        rows += len(body) - len(kept)
    print(f"removed {rows} row(s) from {changed} file(s)")


if __name__ == "__main__":
    main()
