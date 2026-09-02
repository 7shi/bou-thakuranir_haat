#!/usr/bin/env python3
"""Convert tmp/<model-name>-<lang>/<NN>.txt (opencode ceiling answers, written
by ceiling.sh) into a results-style JSONL: results/ceiling-<safe-model>-<lang>.jsonl.

Mirrors answer_ceiling.py's output shape — one record per question:
  question_id — 1-origin question number (matches <NN>.txt)
  expanded    — the gold chapter numbers, as ["5", ...] (Ceiling's context is
                always exactly the gold chapters, no retrieval)
  answer      — the tmp/<model-name>-<lang>/<NN>.txt content, stripped

":" and "/" in --model are replaced with "_" for the output filename, matching
the naming convention in ../results/ (see ../results/README.md).

Called as the last step of ceiling.sh (see make_ceiling.py) after every
question has been answered; can also be run standalone to rebuild the JSONL
from whatever tmp/<model-name>-<lang>/*.txt currently exist.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer import ROOT, LANGS, load_questions


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions file)")
    parser.add_argument("-m", "--model", required=True,
                        help="opencode model string, e.g. opencode/muse-spark-1.2-contributor-free")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("-o", "--output", default=None,
                        help="output JSONL path (default: ../results/ceiling-<safe-model>-<lang>.jsonl)")
    args = parser.parse_args()

    lang = args.lang
    input_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"
    model_dir = args.model.split("/", 1)[-1]
    tmp_dir = Path(__file__).resolve().parent / "tmp" / f"{model_dir}-{lang}"

    safe_model = args.model.replace(":", "_").replace("/", "_")
    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / "results" / f"ceiling-{safe_model}-{lang}.jsonl"

    questions = load_questions(input_path)

    rows = []
    missing = []
    for qid, q in enumerate(questions, start=1):
        txt_path = tmp_dir / f"{qid:02d}.txt"
        if not txt_path.exists():
            missing.append(qid)
            continue
        rows.append({
            "question_id": qid,
            "expanded": [str(ch) for ch in sorted(q["chapters"])],
            "answer": txt_path.read_text(encoding="utf-8").strip(),
        })

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"{len(rows)} questions -> {output_path}")
    if missing:
        print(f"  missing (no {tmp_dir}/NN.txt): {missing}")


if __name__ == "__main__":
    main()
