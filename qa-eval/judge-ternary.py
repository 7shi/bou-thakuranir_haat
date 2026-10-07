#!/usr/bin/env python3
"""Grade candidate answers with a plain LLM that replies with the verdict word only.

The counterpart of judge-openai.py without a decision model: the same
instructions, criteria and JSON input, sent to any llm7shi model, which replies
with one of correct / partial / incorrect as plain text — no structured output,
no reason, no probabilities. Thinking is off unless --think is given
(llm7shi's include_thoughts, which stops the thinking itself on every
provider; Gemini 3 only reduces it).

The grading contract is judge.py's: the judge sees the question, the gold
`answer` and `rationale`, and the candidate answer, but **not** the chapter
source text. The metric is therefore *agreement with the Gemini full-text
baseline*, as with judge.py.

The reply is matched against the three verdicts as whole words, so
"incorrect" is never read as "correct"; a reply naming none or more than one
of them is retried.

Output: <out-dir>/<input-stem>.tsv in each input's directory (default out-dir
`ternary`, e.g. results-en/vector5.jsonl → results-en/ternary/vector5.tsv),
one row per question, in the same columns as judge-openai.py:

  qid<TAB>correct<TAB>partial<TAB>incorrect<TAB>confidence

with 1 for the chosen verdict, 0 for the others, and an empty confidence, so
report.py reads it like the probability judges. Grading with another model
needs its own --out-dir, since a file is never judged by two models.
Resume-safe: skips qids already present in the output file.

What produced a file is recorded once per file in <out-dir>/MODELS.tsv:

  file<TAB>model<TAB>scheme      e.g. vector5.tsv  openai:gpt-6-luna  ternary@1a2b3c4d

`model` is the llm7shi model string; `scheme` is SCHEME_ID, a hash of the
prompt and of whether thinking was on (see scheme_id()). A file whose recorded
model or scheme differs from the current one stops the run.

Token usage: each question's usage is printed, and the run total at the end.
For metered models (openai:/gpt-, or any model with --save-usage) the run total
is appended to llm7shi's shared usage.jsonl (also when interrupted) under the
model name without an `openai:` prefix, followed by today's total for it.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from llm7shi.compat import generate_with_schema
from llm7shi.statusline import StatusLine
from llm7shi.usage import Usage, append_usage, find_usage_file, print_today_totals

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "openai:gpt-6-luna"
DEFAULT_OUT_DIR = "ternary"

VERDICTS = ["correct", "partial", "incorrect"]

INSTRUCTIONS = {
    "judge": "How well does `candidate_answer` match `gold_answer` for `question`?",
    "basis": "Grade only on factual content overlap with `gold_answer`, not on "
             "wording, length, or style. Use `rationale` as supporting evidence.",
}

CRITERIA = {
    "correct": "The candidate answer captures the essential facts of the gold answer.",
    "partial": "The candidate answer captures some but misses or distorts key facts.",
    "incorrect": "The candidate answer is wrong, irrelevant, or says no answer was found.",
}

assert list(CRITERIA) == VERDICTS

SYSTEM_PROMPT = "\n".join([
    *INSTRUCTIONS.values(),
    "",
    *(f"- {v}: {d}" for v, d in CRITERIA.items()),
    "",
    "Reply with exactly one word: " + ", ".join(VERDICTS) + ".",
])

TASK = ("Grading a candidate answer against the gold-standard answer for a "
        "reading-comprehension question about a novel")

HEADER = "\t".join(["qid", *VERDICTS, "confidence"])
MODELS_FILE = "MODELS.tsv"
MODELS_HEADER = "file\tmodel\tscheme"

VERDICT_RE = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b")

USAGE_PATH = None


def load_questions(path: Path) -> dict[int, dict]:
    questions: dict[int, dict] = {}
    with open(path, encoding="utf-8") as f:
        for qid, line in enumerate((l for l in f if l.strip()), start=1):
            questions[qid] = json.loads(line)
    return questions


def build_state(question: str, gold: str, rationale: str, candidate: str) -> dict:
    return {
        "task": TASK,
        "question": question,
        "gold_answer": gold,
        "rationale": rationale,
        "candidate_answer": candidate,
    }


def format_input(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2)


def scheme_id(think: bool) -> str:
    """`ternary@<8 hex>` over everything that shapes the reply.

    That is the system prompt, the input rendered from an empty state (which
    fixes the key order, the `task` text and the JSON layout), and whether
    thinking was on; only the per-question values are left out.
    """
    parts = [SYSTEM_PROMPT, format_input(build_state("", "", "", "")), f"think={think}"]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"ternary@{digest[:8]}"


def parse_verdict(text: str) -> str:
    """The one verdict named in `text`; none or several raise ValueError."""
    found = set(VERDICT_RE.findall(text.lower()))
    if len(found) != 1:
        raise ValueError(f"unexpected reply: {text!r}")
    return found.pop()


def judge_answer(state: dict, model: str, think: bool, file) -> tuple[str, Usage | None]:
    """One request, returning (verdict, Usage or None)."""
    response = generate_with_schema([format_input(state)], model=model,
                                    system_prompt=SYSTEM_PROMPT, include_thoughts=think,
                                    show_params=False, file=file)
    # The tokens are spent even when the reply is then refused, so a parse
    # failure carries the usage for the caller to count.
    try:
        return parse_verdict(response.text), response.usage
    except ValueError as e:
        e.usage = response.usage
        raise


def read_models(path: Path) -> dict[str, tuple[str, str]]:
    """{TSV file name: (model, scheme)} from MODELS.tsv; a header other than
    MODELS_HEADER stops the run."""
    models: dict[str, tuple[str, str]] = {}
    if not path.exists():
        return models
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    if lines and lines[0] != MODELS_HEADER:
        raise SystemExit(f"{path}: unexpected header {lines[0]!r}")
    for line in lines[1:]:
        name, model, scheme = line.split("\t")
        models[name] = (model, scheme)
    return models


def check_run(path: Path, name: str, model: str, scheme: str, record: bool) -> None:
    """Check `name`'s entry in MODELS.tsv against `model` and `scheme`.

    A differing recorded model or scheme stops the run. With `record` and no
    entry yet, the entry is written; it is left out until the first answer, so
    a run that fails before any answer leaves no entry behind.
    """
    models = read_models(path)
    recorded = models.get(name)
    if recorded is not None:
        rec_model, rec_scheme = recorded
        if rec_scheme != scheme:
            raise SystemExit(f"{path}: {name} was judged on {rec_scheme}, this run is "
                             f"{scheme}; the run is abandoned rather than mixing wordings")
        if rec_model != model:
            raise SystemExit(f"{path}: {name} was judged by {rec_model}, this run is {model}; "
                             f"use another --out-dir for another model")
        return
    if not record:
        return
    models[name] = (model, scheme)
    lines = [MODELS_HEADER, *(f"{n}\t{m}\t{s}" for n, (m, s) in sorted(models.items()))]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_done(path: Path) -> set[int]:
    """qids already in the TSV; a header other than HEADER stops the run."""
    done: set[int] = set()
    if not path.exists():
        return done
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    if lines and lines[0] != HEADER:
        raise SystemExit(f"{path}: unexpected header {lines[0]!r}")
    for line in lines[1:]:
        done.add(int(line.split("\t", 1)[0]))
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="result JSONL files to judge")
    parser.add_argument("-l", "--lang", default="en", choices=["en", "ja"],
                        help="evaluation language (selects default gold questions file)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL,
                        help=f"judge model (llm7shi string; default: {DEFAULT_MODEL})")
    parser.add_argument("--think", action="store_true",
                        help="let the model think before replying (off by default)")
    parser.add_argument("-o", "--out-dir", default=DEFAULT_OUT_DIR,
                        help=f"output subdirectory name next to each input (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (gold standard; default: questions-<lang>.jsonl)")
    parser.add_argument("-n", "--count", type=int, default=None,
                        help="judge at most N new questions per input file, then stop")
    parser.add_argument("--attempts", type=int, default=3,
                        help="attempts per question (default: 3)")
    parser.add_argument("--started-at", type=float, default=None,
                        help="unix timestamp the batch started (enables an overall-elapsed "
                             "column spanning multiple invocations, as in judge.py)")
    parser.add_argument("--save-usage", action="store_true",
                        help="record token usage to usage.jsonl regardless of the model")
    args = parser.parse_args()

    global USAGE_PATH
    if args.model.startswith(("openai:", "gpt-")) or args.save_usage:
        USAGE_PATH = find_usage_file()
    # Recorded without the openai: prefix, so it totals with the same model's
    # other runs in usage.jsonl (Decisions requests are apart as decisions:<model>).
    usage_name = args.model.removeprefix("openai:")

    args.input = args.input or str(ROOT / f"questions-{args.lang}.jsonl")
    scheme = scheme_id(args.think)

    questions = load_questions(Path(args.input))
    print(f"Gold questions: {len(questions)}")
    print(f"Judge: {args.model} (think={args.think}, {scheme})")

    ui = StatusLine()
    usages = []

    try:
        for file_no, input_str in enumerate(args.inputs, start=1):
            in_path = Path(input_str)
            out_path = in_path.parent / args.out_dir / f"{in_path.stem}.tsv"
            out_path.parent.mkdir(exist_ok=True)
            label = in_path.stem
            # With several inputs, show which file of how many is running.
            progress_label = (f"{label} ({file_no}/{len(args.inputs)})"
                              if len(args.inputs) > 1 else label)

            # Both the model and the scheme are known up front, so a mismatch
            # stops the run here without spending tokens.
            models_path = out_path.parent / MODELS_FILE
            check_run(models_path, out_path.name, args.model, scheme, record=False)
            done_ids = read_done(out_path)

            records = []
            with open(in_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))

            print(f"# {in_path} → {out_path}  ({len(records)} answers)")
            if done_ids:
                print(f"# Resuming: {len(done_ids)} already done")

            total = len(records)
            answered = 0
            file_usages = []
            new_file = not out_path.exists() or out_path.stat().st_size == 0
            with open(out_path, "a", encoding="utf-8") as out_f, \
                 ui.progress(total, start=len(done_ids), label=progress_label,
                             started_at=args.started_at) as prog:
                if new_file:
                    out_f.write(HEADER + "\n")
                    out_f.flush()
                for i, rec in enumerate(records, start=1):
                    qid = rec["question_id"]
                    if qid in done_ids:
                        continue
                    if args.count is not None and answered >= args.count:
                        ui.stream.print(f"Stopping after {answered} question(s) (--count {args.count})")
                        break

                    q = questions[qid]
                    ui.stream.print(f"\n[Q{i}/{total}] {q['question']}")
                    ui.stream.print(f"=> {rec['answer']}")
                    ui.stream.print(f"  ({q['answer']})")

                    state = build_state(q["question"], q["answer"], q["rationale"], rec["answer"])
                    q_usages = []
                    for attempt in range(1, args.attempts + 1):
                        try:
                            verdict, usage = judge_answer(state, args.model, args.think, ui.stream)
                            if usage is not None:
                                q_usages.append(usage)
                            break
                        except ValueError as e:
                            if getattr(e, "usage", None) is not None:
                                q_usages.append(e.usage)
                            ui.stream.print(f"  attempt {attempt}/{args.attempts} failed: {e}")
                    else:
                        usages.extend(q_usages)
                        raise SystemExit(f"GIVING UP on Q{qid} after {args.attempts} attempts")

                    usages.extend(q_usages)
                    file_usages.extend(q_usages)
                    check_run(models_path, out_path.name, args.model, scheme, record=True)
                    ui.stream.print(f"  verdict={verdict}")
                    if q_usages:
                        ui.stream.print(f"  {sum(q_usages)!r}")

                    out_f.write("\t".join([str(qid), *("1" if v == verdict else "0" for v in VERDICTS),
                                           ""]) + "\n")
                    out_f.flush()
                    answered += 1
                    prog.update(len(done_ids) + answered)

            if file_usages:
                print(f"{label}: {len(file_usages)} request(s), {sum(file_usages)}")
            print(f"Done → {out_path}")
    finally:
        # Record silently so an interrupted run still logs what it consumed;
        # the report below is printed only on normal completion.
        if usages and USAGE_PATH is not None:
            append_usage(sum(usages), usage_name, USAGE_PATH)

    if usages:
        total_usage = sum(usages)
        print(f"\n--- Total Usage ---\n{len(usages)} request(s), {total_usage}")
        if total_usage.input_tokens is not None and total_usage.output_tokens is not None:
            print(f"Per request: {total_usage.input_tokens / len(usages):.1f} input, "
                  f"{total_usage.output_tokens / len(usages):.1f} output tokens")
        if USAGE_PATH is not None:
            print("")
            print_today_totals(USAGE_PATH, models=[usage_name])


if __name__ == "__main__":
    main()
