#!/usr/bin/env python3
"""Sort the rows of every verdict file by question ID.

A judge resuming after drop_verdicts.py appends the re-graded questions at the
end of each file; this puts them back in qid order. The TSV header line stays
first. A file with a duplicated question ID stops the run before anything is
written, as it means a question was graded twice. Files already in order are
not rewritten.
"""

import argparse
import sys

from drop_verdicts import JUDGES, SETS, row_qid, verdict_files


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--sets", nargs="+", default=SETS, choices=SETS)
    parser.add_argument("-j", "--judges", nargs="+", default=JUDGES, choices=JUDGES)
    args = parser.parse_args()

    plans = []
    errors = []
    for path in verdict_files(args.sets, args.judges):
        with open(path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        head = lines[:1] if path.suffix == ".tsv" else []
        body = lines[len(head):]
        qids = [row_qid(l, path) for l in body]
        if len(set(qids)) != len(qids):
            dups = sorted({q for q in qids if qids.count(q) > 1})
            errors.append(f"{path}: duplicated qid {dups}")
            continue
        if qids != sorted(qids):
            plans.append((path, head + sorted(body, key=lambda l: row_qid(l, path))))
    if errors:
        print("\n".join(errors))
        sys.exit("nothing sorted")
    for path, lines in plans:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sorted {len(plans)} file(s)")


if __name__ == "__main__":
    main()
