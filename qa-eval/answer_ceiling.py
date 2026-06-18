#!/usr/bin/env python3
"""Answer evaluation questions using the gold chapters directly as context.

No retrieval at all: the gold `chapters` from questions-<lang>.jsonl are fed
verbatim as context, so every loss is a pure synthesis (reading comprehension)
loss. This puts Ceiling in a different role from RAG/Extract/Filter — a
perfect-retrieval ceiling that isolates the answer model's comprehension from
retrieval quality. Where the other methods answer "which chapters should the
answerer see?", Ceiling answers "given the right chapters, how well does the
model read and synthesize?" — the upper bound the retrieval strategies chase.

For each question in questions-<lang>.jsonl:
  Load the full text of every chapter in the gold `chapters` field, concatenate
  with `[Chapter N]` labels, and ask the model to answer in the target language.

- Input: questions-<lang>.jsonl (50 questions, ROOT-level — supplies the gold
  `chapters`) and ../all/<lang>-gemini.jsonl (scenes — the full chapter text).
- Output: results-<lang>/ceiling.jsonl — one record per question:
  - question_id — 1-origin line number in the input file
  - expanded — the gold chapter numbers, as ["5", "10", ...] strings (always
    exactly the gold set, so report.py scores chapter recall/precision as 1.0)
  - answer — the model's answer

Resume-safe: re-running skips question IDs already present in the output file.
"""

import argparse
import json
from pathlib import Path

from answer import (
    ROOT, LANGS,
    load_chapters, load_questions, answer_question, print_answer_banner,
)


# Ceiling reads full chapter text (like Filter's Phase 2), so the wording
# matches the neutral "context provided" phrasing shared by RAG and Filter,
# rather than Extract's "chapter excerpts below".
CEILING_PREAMBLE = (
    "Answer the following question in {lang_name} based ONLY on the context provided. "
    "Do not use any outside knowledge. "
    "Reply with the answer only — no preamble, no reasoning, no closing remarks."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-o", "--output", default=None,
                        help="output JSONL path (default: qa-eval/results-<lang>/ceiling.jsonl)")
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.scenes = args.scenes or str(ROOT / "all" / f"{lang}-gemini.jsonl")

    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / "ceiling.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(Path(args.input))
    total = len(questions)

    # Resume: collect already-done question IDs.
    done_qids: set[int] = set()
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    done_qids.add(json.loads(line)["question_id"])
    if done_qids:
        print(f"Resuming: {len(done_qids)} questions already done")

    print(f"Loading scenes from {args.scenes}")
    chapters = load_chapters(Path(args.scenes))
    print(f"Questions: {total}")

    with open(output_path, "a", encoding="utf-8") as out_f:
        for qid, q in enumerate(questions, start=1):
            if qid in done_qids:
                continue

            question_text = q["question"]
            # The gold `chapters` are the context by definition — no retrieval,
            # no filtering, no verdict map. Any chapter missing from the scenes
            # file is skipped with a notice rather than crashing.
            selected_chapters = sorted(ch for ch in q["chapters"] if ch in chapters)
            missing = sorted(ch for ch in q["chapters"] if ch not in chapters)
            if missing:
                print(f"  note: gold chapters {missing} not found in scenes — excluded")

            print_answer_banner(qid, total, selected_chapters, question_text)

            if not selected_chapters:
                answer = "No relevant content found."
                print(answer)
            else:
                context = "\n\n".join(
                    f"[Chapter {ch}]\n" + "\n\n".join(s["text"] for s in chapters[ch])
                    for ch in selected_chapters
                )
                answer = answer_question(
                    question_text, context, args.model, lang_name,
                    preamble=CEILING_PREAMBLE, context_prefix="Context:\n",
                )

            record = {
                "question_id": qid,
                "expanded": [str(ch) for ch in selected_chapters],
                "answer": answer,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
