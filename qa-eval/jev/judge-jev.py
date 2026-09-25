#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with TypeSafe's Jev.

Experiment script behind README.md in this directory, which records how the
Choice was settled on; a production judge is to be derived from it.

A port of judge.py to Jev, a System One model: instead of generating a reason
and a verdict as structured text, it answers typed questions and returns
probabilities. There is no prose, so records carry no `reason`.

The grading contract is judge.py's: the judge sees the question, the gold
`answer` and `rationale`, and the candidate answer, but **not** the chapter
source text, and the wording follows judge.py's rubric. The metric is
therefore still *agreement with the Gemini full-text baseline*, comparable
row by row with the judge.py verdicts.

The verdict comes from one Choice question over correct / partial / incorrect:
the most probable option.

--debug additionally asks one yes/no (Noul) question in the same request —
`correct`: does the candidate capture the essential facts of the gold answer?
Its criteria describe only correct (yes) and incorrect (no), so the yes
probability can be inspected for a middle band to use as partial; if no usable
threshold emerges, the Choice stays. One request keeps the state billed once;
the questions cannot see each other's answers. Its token usage is for both
questions together, so it is not the cost of a normal run.

Output goes under this directory, in a subdirectory named after the input's
directory (e.g. qa-eval/results-en/vector5.jsonl → results-en/ here), so the
experiment's logs stay out of the qa-eval result directories:
  - judge-jev-<stem>.jsonl, one record per question: question_id, verdict,
    confidence, probabilities, model, usage.
  - with --debug: jev-<stem>.jsonl instead, one record per question holding the
    raw API response body ({"question_id", "response"}) with the Choice and the
    Noul answers, and no verdict, for choosing thresholds offline.

Resume-safe: skips question IDs already present in the output file.

Token usage: each question's usage is printed and stored (in the record, or in
the raw response under --debug), and per-file and run totals are printed. Jev is
a paid API, so the run total is always appended to llm7shi's shared usage.jsonl
(also when interrupted), followed by today's total for the model.

Requires TYPESAFE_API_KEY in the environment.
"""

import argparse
import json
from pathlib import Path

from llm7shi.statusline import StatusLine
from llm7shi.usage import Usage, append_usage, find_usage_file, print_today_totals
from typesafe_sdk import Choice, Noul, NoulCriteria, TypeSafeClient

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# A version, not the `jev-latest` alias, so a model release cannot silently
# make later runs incomparable with the ones already on disk.
DEFAULT_MODEL = "jev-1.13.0"

VERDICTS = ["correct", "partial", "incorrect"]

BASIS = ("Grade only on factual content overlap with `gold_answer`, not on wording, "
         "length, or style. Use `rationale` as supporting evidence.")

CHOICE_QUESTIONS = {
    "verdict": Choice(
        instructions={
            "judge": "How well does `candidate_answer` match `gold_answer` for `question`?",
            "basis": BASIS,
        },
        criteria={
            "correct": "The candidate answer captures the essential facts of the gold answer.",
            "partial": "The candidate answer captures some but misses or distorts key facts.",
            "incorrect": "The candidate answer is wrong, irrelevant, or says no answer was found.",
        },
    ),
}

assert list(CHOICE_QUESTIONS["verdict"].criteria) == VERDICTS

# Only the two poles are described; partial is meant to land in between, where
# a threshold band on the yes probability picks it out.
NOUL_QUESTIONS = {
    "correct": Noul(
        instructions={
            "statement": "`candidate_answer` captures the essential facts of `gold_answer` "
                         "for `question`.",
            "basis": BASIS,
        },
        criteria=NoulCriteria(
            true="The candidate answer captures the essential facts of the gold answer.",
            false="The candidate answer is wrong, irrelevant, or says no answer was found.",
        ),
    ),
}


def load_questions(path: Path) -> dict[int, dict]:
    questions: dict[int, dict] = {}
    with open(path, encoding="utf-8") as f:
        for qid, line in enumerate((l for l in f if l.strip()), start=1):
            questions[qid] = json.loads(line)
    return questions


def build_state(question: str, gold: str, rationale: str, candidate: str) -> dict:
    return {
        "task": "Grading a candidate answer against the gold-standard answer for a "
                "reading-comprehension question about a novel",
        "question": question,
        "gold_answer": gold,
        "rationale": rationale,
        "candidate_answer": candidate,
    }


def ask(client, state: dict, questions: dict, model: str, expect_model: str):
    """One request, returning (response, Usage).

    A version other than the expected one raises SystemExit so it aborts the
    run instead of being retried — the alias having moved is not transient.
    Missing answers raise ValueError so they are retried.
    """
    response = client.system_one(state, questions, model=model)
    if expect_model and response.model != expect_model:
        raise SystemExit(f"requested {model} but {response.model} answered; "
                         f"the run is abandoned rather than mixing versions")
    missing = [key for key in questions if key not in response.answers]
    if missing:
        raise ValueError(f"no answer for {missing}")
    usage = Usage()
    if response.usage:
        usage = Usage(raw={"input_tokens": response.usage.input_tokens,
                           "output_tokens": response.usage.output_tokens})
    return response, usage


def choice_record(response) -> tuple[dict, str]:
    answer = response.choices["verdict"]
    probabilities = {v: round(float(answer.probabilities.get(v, 0.0)), 4) for v in VERDICTS}
    dist = " ".join(f"{v}={p:.2f}" for v, p in probabilities.items())
    record = {
        "verdict": answer.choice,
        "confidence": round(answer.confidence, 4),
        "probabilities": probabilities,
    }
    return record, f"{answer.choice} (confidence {answer.confidence:.2f}; {dist})"


def noul_summary(response) -> str:
    return " ".join(f"{key}={response.nouls[key].noul:.2f}" for key in NOUL_QUESTIONS)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="result JSONL files to judge")
    parser.add_argument("-l", "--lang", default="en", choices=["en", "ja"],
                        help="evaluation language (selects default gold questions file)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL,
                        help=f"TypeSafe model version (default: {DEFAULT_MODEL})")
    parser.add_argument("--expect-model",
                        help="version the response must report, if not --model itself; "
                             "empty accepts whatever answers, which an alias needs")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (gold standard; default: questions-<lang>.jsonl)")
    parser.add_argument("--debug", action="store_true",
                        help="ask the Choice and the Noul question together and write "
                             "the raw API response per question to jev-*.jsonl instead of "
                             "judge-jev-*.jsonl records")
    parser.add_argument("-n", "--count", type=int, default=None,
                        help="judge at most N new questions per input file, then stop "
                             "(for trial runs and token measurement)")
    parser.add_argument("--attempts", type=int, default=3,
                        help="attempts per question (default: 3)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="per-request timeout in seconds (default: 120)")
    args = parser.parse_args()

    args.input = args.input or str(ROOT / f"questions-{args.lang}.jsonl")
    # A version is its own pin; only an alias needs --expect-model spelled out.
    expect_model = args.model if args.expect_model is None else args.expect_model
    questions_sent = {**CHOICE_QUESTIONS, **NOUL_QUESTIONS} if args.debug else CHOICE_QUESTIONS
    prefix = "jev-" if args.debug else "judge-jev-"

    questions = load_questions(Path(args.input))
    print(f"Gold questions: {len(questions)}")

    ui = StatusLine()
    usage_path = find_usage_file()
    usages = []
    served_model = args.model

    try:
        with TypeSafeClient(timeout=args.timeout) as client:
            for input_str in args.inputs:
                in_path = Path(input_str)
                out_path = HERE / in_path.resolve().parent.name / f"{prefix}{in_path.stem}.jsonl"
                out_path.parent.mkdir(exist_ok=True)
                label = in_path.stem

                # Resume: collect already-done question IDs
                done_ids: set[int] = set()
                if out_path.exists():
                    with open(out_path, encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                done_ids.add(json.loads(line)["question_id"])

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
                with open(out_path, "a", encoding="utf-8") as out_f, \
                     ui.progress(total, start=len(done_ids), label=label) as prog:
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
                        for attempt in range(1, args.attempts + 1):
                            try:
                                response, usage = ask(client, state, questions_sent,
                                                      args.model, expect_model)
                                break
                            except SystemExit:
                                raise
                            except Exception as e:
                                ui.stream.print(f"  attempt {attempt}/{args.attempts} failed: {e}")
                        else:
                            raise SystemExit(f"GIVING UP on Q{qid} after {args.attempts} attempts")

                        served_model = response.model
                        usages.append(usage)
                        file_usages.append(usage)

                        record, summary = choice_record(response)
                        ui.stream.print(f"  {summary}")
                        if args.debug:
                            ui.stream.print(f"  {noul_summary(response)}")
                        ui.stream.print(f"  {usage!r}")

                        if args.debug:
                            out = {"question_id": qid,
                                   "response": json.loads(response.raw_http_response.content)}
                        else:
                            out = {"question_id": qid, **record, "model": served_model,
                                   "usage": usage.to_dict()}
                        out_f.write(json.dumps(out, ensure_ascii=False) + "\n")
                        out_f.flush()
                        answered += 1
                        prog.update(len(done_ids) + answered)

                if file_usages:
                    print(f"{label}: {len(file_usages)} question(s), {sum(file_usages)}")
                print(f"Done → {out_path}")
    finally:
        # Record silently so an interrupted run still logs what it consumed;
        # the report below is printed only on normal completion.
        if usages:
            append_usage(sum(usages), served_model, usage_path)

    if usages:
        total_usage = sum(usages)
        print(f"\n--- Total Usage ---\n{len(usages)} request(s), {total_usage}")
        if total_usage.input_tokens is not None and total_usage.output_tokens is not None:
            print(f"Per request: {total_usage.input_tokens / len(usages):.1f} input, "
                  f"{total_usage.output_tokens / len(usages):.1f} output tokens")
        print("")
        print_today_totals(usage_path, models=[served_model])


if __name__ == "__main__":
    main()
