#!/usr/bin/env python3
"""Answer evaluation questions using the gold chapters directly as context.

No retrieval at all: the gold `chapters` from questions-<lang>.jsonl are fed
verbatim as context, so every loss is a pure synthesis (reading comprehension)
loss. This puts Ceiling in a different role from RAG/Extract/Filter — a
perfect-retrieval ceiling that isolates the answer model's comprehension from
retrieval quality. Where the other methods answer "which chapters should the
answerer see?", Ceiling answers "given the right chapters, how well does the
model read and synthesize?" — the upper bound the retrieval strategies chase.
Because Ceiling's `expanded` is always exactly the gold set, report.py's pairwise
disagreement analysis classifies all its losses as synthesis, and every question
where Ceiling beats a retrieval method with a non-empty `dropped` set exposes a
chapter that method failed to surface.

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
  - usage — token usage summed over this question's attempts (Usage.to_dict();
    omitted when the provider reported none)

Resume-safe: re-running skips question IDs already present in the output file.

Token usage: each question's usage is printed after its answer, and the run
total is printed at the end. For metered models (openai: / gpt- prefixes, or
--save-usage) the run total is also appended to llm7shi's shared usage.jsonl,
followed by today's total for the model. When interrupted, the total is still
appended silently, without printing either total.
"""

import argparse
import json
from pathlib import Path

from llm7shi.statusline import StatusLine
from llm7shi.usage import append_usage, find_usage_file, print_today_totals

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

# Set to a path to record usage; None means "don't record"
USAGE_PATH = None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-o", "--output", default=None,
                        help="output JSONL path (default: qa-eval/results-<lang>/ceiling.jsonl)")
    parser.add_argument("-c", "--count", type=int, default=None,
                        help="stop after answering this many questions")
    parser.add_argument("--no-think", action="store_true",
                        help="disable the model's thinking channel (Ollama think=False) — "
                             "for small models whose CoT can run away and never terminate")
    parser.add_argument("--save-usage", action="store_true",
                        help="record token usage to usage.jsonl regardless of the model")
    args = parser.parse_args()

    global USAGE_PATH
    if args.model.startswith(("openai:", "gpt-")) or args.save_usage:
        USAGE_PATH = find_usage_file()

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

    label = f"{args.model} {lang}"
    ui = StatusLine()
    answered = 0
    # Every call's Usage in this run (including empty-answer retries). A run
    # can take long and be interrupted, so the total is recorded in `finally`.
    usages = []
    try:
        with open(output_path, "a", encoding="utf-8") as out_f, \
             ui.progress(total, start=len(done_qids), label=label) as prog:
            for qid, q in enumerate(questions, start=1):
                if qid in done_qids:
                    continue
                if args.count is not None and answered >= args.count:
                    ui.stream.print(f"Stopping after {answered} question(s) (--count {args.count})")
                    break

                question_text = q["question"]
                # The gold `chapters` are the context by definition — no retrieval,
                # no filtering, no verdict map. Any chapter missing from the scenes
                # file is skipped with a notice rather than crashing.
                selected_chapters = sorted(ch for ch in q["chapters"] if ch in chapters)
                missing = sorted(ch for ch in q["chapters"] if ch not in chapters)
                if missing:
                    ui.stream.print(f"  note: gold chapters {missing} not found in scenes — excluded")

                print_answer_banner(qid, total, selected_chapters, question_text, log=ui.stream.print)

                q_usages = []
                if not selected_chapters:
                    answer = "No relevant content found."
                    ui.stream.print(answer)
                else:
                    context = "\n\n".join(
                        f"[Chapter {ch}]\n" + "\n\n".join(s["text"] for s in chapters[ch])
                        for ch in selected_chapters
                    )
                    answer = answer_question(
                        question_text, context, args.model, lang_name,
                        preamble=CEILING_PREAMBLE, context_prefix="Context:\n",
                        no_think=args.no_think, usages=q_usages,
                        file=ui.stream, log=ui.stream.print,
                    )
                usages.extend(q_usages)

                record = {
                    "question_id": qid,
                    "expanded": [str(ch) for ch in selected_chapters],
                    "answer": answer,
                }
                if q_usages:
                    q_usage = sum(q_usages)
                    ui.stream.print(repr(q_usage))
                    record["usage"] = q_usage.to_dict()
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                answered += 1
                prog.update(len(done_qids) + answered)
    finally:
        # Record silently so an interrupted run still logs what it consumed;
        # the report below is printed only on normal completion.
        if usages and USAGE_PATH is not None:
            append_usage(sum(usages), args.model, USAGE_PATH)

    if usages:
        print(f"\n--- Total Usage ---\n{sum(usages)}")
        if USAGE_PATH is not None:
            print("")
            print_today_totals(USAGE_PATH, models=[args.model])

    print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
