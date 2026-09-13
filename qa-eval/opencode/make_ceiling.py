#!/usr/bin/env python3
"""Generate ceiling.sh: shell commands that answer questions via the `opencode`
CLI, using the gold chapters' extracted text files (from extract.py) as context.

Regenerate-and-run-once, not a reusable script: --model is baked in at
generation time, so a new model means regenerating ceiling.sh (it's
gitignored). For each question in questions-<lang>.jsonl, it runs
`opencode run -m <model> "<question>" -f <lang>/<NN>.txt ...` for that
question's gold chapter file(s), and tees the output to
tmp/<model-name>-<lang>/<NN>.txt (NN = 1-origin question number, zero-padded;
the model directory drops any "<provider>/" prefix from --model and carries a
"-<lang>" suffix so different languages don't collide in the same directory).

With --copilot, it runs the `copilot` CLI instead:
`copilot --model <model> --add-dir <lang> -s -p "@<lang>/<NN>.txt ... <question>"`
(--add-dir grants copilot access to the gold chapter files, which live
outside its working directory; -s silences copilot's own tool-call chatter
from the reply). --model then takes a plain model name with no provider
prefix, so the model directory (and the model string handed to
build_jsonl.py) is tagged with a "copilot_" prefix to keep it from colliding
with an opencode run of a same-named model.

`-f` is yargs array-type: with `-f file1.txt file2.txt "prompt"` it swallows
the prompt as a third file and leaves the actual prompt (message) empty. The
prompt is therefore placed first (as the positional message) and every gold
chapter's file is appended after a single trailing `-f`, space-separated,
rather than repeating `-f` per file.

Because opencode is a general coding-agent CLI rather than a plain
answer-only completion, its replies tend to include extra framing beyond the
bare answer — closing remarks, and citations of the attached file's
name/path and line numbers (as if writing a code-review comment rather than
answering a question) — so the question is appended with a fixed
instruction telling the model to reply with the answer only and without
such citations, to keep tmp/<model>-<lang>/<NN>.txt close to a pure answer (opencode
itself still prints its own leading "> build · <model>" banner ahead of the
reply; that one isn't the model's text and isn't addressed by the prompt).
It is also told not to make any tool call at all — left unconstrained, a
coding-agent model may reach for a shell tool to inspect the attached file
or this directory (defeating the point of Ceiling, whose context must be
exactly the gold chapters), which also stalls the run since ceiling.sh has
no TTY to approve the resulting permission prompt.

copilot's `@file` reference doesn't attach the file's content the way
opencode's `-f` does — the model still has to read it via a tool call — so
its instruction (ANSWER_ONLY_COPILOT) can't forbid tool calls the way
opencode's does; doing so left the model unable to answer at all, replying
that it lacked tool access to the file's content.

Resume-safe: each generated block skips the question if its output file
already exists, so re-running ceiling.sh after an interruption only answers
what's missing. `set -o pipefail` makes a failing `opencode run` fail the
pipe too (`tee` itself always succeeds), and on that failure the block
removes its half-written output file before exiting, so the failed question
is retried — not skipped as done — on the next run.

The last line calls build_jsonl.py, which converts every tmp/<model>-<lang>/<NN>.txt
into results/ceiling-<safe-model>-<lang>.jsonl (the format ../results/ uses)
— it only runs once every question above it has succeeded, since `set -e`
stops the script at the first failure.
"""

import argparse
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer import ROOT, LANGS, load_questions

ANSWER_ONLY_OPENCODE = (
    "Do not make any tool call — answer using only the file(s) already "
    "attached above. Do not cite file names, paths, or line numbers. Reply "
    "with the answer only — no preamble, no reasoning, no closing remarks."
)

# Unlike opencode's `-f`, copilot's `@file` reference does not attach file
# content directly — the model must read it itself, so tool calls can't be
# forbidden here the way they are for opencode (that leaves the model unable
# to answer at all, replying that it lacks tool access to the file).
ANSWER_ONLY_COPILOT = (
    "Read the referenced file(s) above and answer using only their content. "
    "Do not cite file names, paths, or line numbers. Reply with the answer "
    "only — no preamble, no reasoning, no closing remarks."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions file and chapter-file directory)")
    parser.add_argument("-m", "--model", required=True,
                        help="opencode model string, e.g. opencode/muse-spark-1.2-contributor-free "
                             "(with --copilot, a plain model name with no provider prefix)")
    parser.add_argument("--copilot", action="store_true",
                        help="use the `copilot` CLI instead of `opencode run`; the model has no "
                             "provider prefix, so output paths are tagged with a copilot_ prefix "
                             "to keep them from colliding with opencode's")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("-o", "--output", default=None,
                        help="output shell script path (default: ceiling.sh, next to this script)")
    args = parser.parse_args()

    lang = args.lang
    input_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"
    output_path = Path(args.output) if args.output else Path(__file__).resolve().parent / "ceiling.sh"

    questions = load_questions(input_path)
    total = len(questions)
    model_dir = args.model.split("/", 1)[-1]
    build_jsonl_model = args.model
    if args.copilot:
        model_dir = f"copilot_{model_dir}"
        build_jsonl_model = model_dir
    out_dir = f"tmp/{model_dir}-{lang}"

    lines = [
        "#!/bin/bash",
        "set -e",
        "set -o pipefail",
        "",
        f"mkdir -p {shlex.quote(out_dir)}",
        "",
    ]
    for qid, q in enumerate(questions, start=1):
        out_file = shlex.quote(f"{out_dir}/{qid:02d}.txt")
        if args.copilot:
            prompt = f'{q["question"]}\n\n{ANSWER_ONLY_COPILOT}'
            file_list = " ".join(f"@{lang}/{ch:02d}.txt" for ch in sorted(q["chapters"]))
            cmd = f"copilot --model {args.model} --add-dir {shlex.quote(lang)} -s -p {shlex.quote(f'{file_list} {prompt}')} | tee {out_file}"
        else:
            prompt = f'{q["question"]}\n\n{ANSWER_ONLY_OPENCODE}'
            file_list = " ".join(f"{lang}/{ch:02d}.txt" for ch in sorted(q["chapters"]))
            files = f"-f {file_list}"
            cmd = f"opencode run -m {args.model} {shlex.quote(prompt)} {files} | tee {out_file}"
        if qid > 1:
            lines.append("echo")
        lines.append(f"echo '{'=' * 60}'")
        lines.append(f"echo '[Q{qid}/{total}]'")
        lines.append(f"if [ ! -f {out_file} ]; then")
        lines.append(f"  {cmd} || {{ rm -f {out_file}; exit 1; }}")
        lines.append("fi")
        lines.append("")

    lines.append(f"uv run build_jsonl.py -l {shlex.quote(lang)} -m {shlex.quote(build_jsonl_model)}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    output_path.chmod(0o755)
    print(f"{total} questions -> {output_path}")


if __name__ == "__main__":
    main()
