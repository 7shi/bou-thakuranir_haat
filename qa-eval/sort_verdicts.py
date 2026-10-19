#!/usr/bin/env python3
"""Sort the rows of every Jev verdict file by question ID.

judge-jev.py resuming after drop_verdicts.py appends the re-graded questions at
the end of each file; this puts them back in qid order. The TSV header line
stays first. A file with a duplicated question ID stops the run before anything
is written, as it means a question was graded twice. Files already in order are
not rewritten. Like drop_verdicts.py, it touches only jev/.
"""

import argparse
import sys

from drop_verdicts import SETS, row_qid, verdict_files


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--sets", nargs="+", default=SETS, choices=SETS)
    args = parser.parse_args()

    plans = []
    errors = []
    for path in verdict_files(args.sets):
        with open(path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        head, body = lines[:1], lines[1:]
        qids = [row_qid(l) for l in body]
        if len(set(qids)) != len(qids):
            dups = sorted({q for q in qids if qids.count(q) > 1})
            errors.append(f"{path}: duplicated qid {dups}")
            continue
        if qids != sorted(qids):
            plans.append((path, head + sorted(body, key=row_qid)))
    if errors:
        print("\n".join(errors))
        sys.exit("nothing sorted")
    for path, lines in plans:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sorted {len(plans)} file(s)")


if __name__ == "__main__":
    main()
