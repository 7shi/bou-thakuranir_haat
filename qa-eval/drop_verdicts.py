#!/usr/bin/env python3
"""Remove the Jev verdicts of selected questions so that Jev grades them again.

judge-jev.py is resume-safe by question ID: it skips a question that already
has a verdict. After a gold answer is corrected, removing its verdicts and
re-running the usual Jev commands grades only those questions, appended at the
end of each file; sort_verdicts.py then puts the rows back in qid order.

Verdict files: jev/<stem>.tsv next to each answer file in results-en/,
results-ja/ and results/, after a header line.

Only jev/ is touched. The frozen judges (judge/ for qwen, nimble/, clef-flash/,
clef/, openai/, ternary/, results/ja2en/, and every jev-<old>/) keep their
verdicts as graded; see models/README.md.

MODELS.tsv is left as it is, so the re-run must use the recorded model and
scheme. Files without any of the questions are not rewritten.
"""

import argparse
from pathlib import Path

QA_EVAL = Path(__file__).resolve().parent
SETS = ["results-en", "results-ja", "results"]
JEV_DIR = "jev"


def verdict_files(sets: list[str]) -> list[Path]:
    files = []
    for s in sets:
        files += sorted(p for p in (QA_EVAL / s / JEV_DIR).glob("*.tsv")
                        if p.name != "MODELS.tsv")
    return files


def row_qid(line: str) -> int:
    return int(line.split("\t", 1)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("qids", nargs="+", type=int, help="question IDs to re-grade")
    parser.add_argument("-s", "--sets", nargs="+", default=SETS, choices=SETS)
    args = parser.parse_args()

    qids = set(args.qids)
    changed = rows = 0
    for path in verdict_files(args.sets):
        with open(path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        head, body = lines[:1], lines[1:]
        kept = [l for l in body if row_qid(l) not in qids]
        if len(kept) == len(body):
            continue
        path.write_text("\n".join(head + kept) + "\n", encoding="utf-8")
        changed += 1
        rows += len(body) - len(kept)
    print(f"removed {rows} row(s) from {changed} file(s)")


if __name__ == "__main__":
    main()
