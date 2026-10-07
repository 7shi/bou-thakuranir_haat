#!/usr/bin/env python3
"""Translate Japanese answer files into English for cross-language grading.

Each input <stem>.jsonl (a Japanese answer file in results/) is written to
<stem>.jsonl in this directory with `answer` replaced by its English
translation and the original kept as `answer_ja`, so judge-ternary.py can grade
it against the English question and gold answer (-l en).

The translator sees the English question for the spelling of names, but not
the gold answer, and is told to translate without adding, dropping or
correcting anything. Thinking is off.

Resume-safe: skips question IDs already in the output. Token usage is printed
and, for metered models (openai:/gpt-, or --save-usage), appended to llm7shi's
shared usage.jsonl under the model name without an `openai:` prefix.
"""

import argparse
import json
from pathlib import Path

from llm7shi.compat import generate_with_schema
from llm7shi.statusline import StatusLine
from llm7shi.usage import append_usage, find_usage_file, print_today_totals

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent

DEFAULT_MODEL = "openai:gpt-6-luna"

SYSTEM_PROMPT = "\n".join([
    "Translate the Japanese answer into English. It answers a question about "
    "Rabindranath Tagore's novel Bou Thakuranir Haat; the English question is "
    "given only for the spelling of names.",
    "Translate faithfully: do not add, drop, correct or explain anything, and "
    "keep any Markdown formatting.",
    "Reply with the translation only.",
])


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="Japanese answer JSONL files")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL,
                        help=f"translator model (llm7shi string; default: {DEFAULT_MODEL})")
    parser.add_argument("--save-usage", action="store_true",
                        help="record token usage to usage.jsonl regardless of the model")
    args = parser.parse_args()

    usage_path = (find_usage_file() if args.model.startswith(("openai:", "gpt-")) or args.save_usage
                  else None)
    usage_name = args.model.removeprefix("openai:")
    questions = {i: q for i, q in enumerate(load_jsonl(ROOT / "questions-en.jsonl"), start=1)}
    print(f"Translator: {args.model}")

    ui = StatusLine()
    usages = []
    try:
        for file_no, input_str in enumerate(args.inputs, start=1):
            in_path = Path(input_str)
            out_path = HERE / in_path.name
            if out_path.resolve() == in_path.resolve():
                raise SystemExit(f"{in_path}: input and output are the same file")
            records = load_jsonl(in_path)
            done = {r["question_id"] for r in load_jsonl(out_path)} if out_path.exists() else set()
            label = f"{in_path.stem} ({file_no}/{len(args.inputs)})"
            print(f"# {in_path} → {out_path}  ({len(records)} answers, {len(done)} done)")

            with open(out_path, "a", encoding="utf-8") as out_f, \
                 ui.progress(len(records), start=len(done), label=label) as prog:
                n = len(done)
                for rec in records:
                    qid = rec["question_id"]
                    if qid in done:
                        continue
                    content = (f"Question: {questions[qid]['question']}\n\n"
                               f"Answer (Japanese):\n{rec['answer']}")
                    response = generate_with_schema([content], model=args.model,
                                                    system_prompt=SYSTEM_PROMPT,
                                                    include_thoughts=False,
                                                    show_params=False, file=ui.stream)
                    if response.usage is not None:
                        usages.append(response.usage)
                    out = {**rec, "answer": response.text.strip(), "answer_ja": rec["answer"]}
                    out_f.write(json.dumps(out, ensure_ascii=False) + "\n")
                    out_f.flush()
                    n += 1
                    prog.update(n)
            print(f"Done → {out_path}")
    finally:
        if usages and usage_path is not None:
            append_usage(sum(usages), usage_name, usage_path)

    if usages:
        print(f"\n--- Total Usage ---\n{len(usages)} request(s), {sum(usages)}")
        if usage_path is not None:
            print_today_totals(usage_path, models=[usage_name])


if __name__ == "__main__":
    main()
