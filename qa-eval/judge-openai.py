#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with OpenAI's Decisions API.

The OpenAI counterpart of judge-jev.py: the same single Choice over correct /
partial / incorrect, sent to `POST /decisions` (gpt-6-luna by default), which
returns a probability for each choice; there is no generated reason.

The grading contract is judge.py's: the judge sees the question, the gold
`answer` and `rationale`, and the candidate answer, but **not** the chapter
source text, and the criteria are judge.py's rubric. The metric is therefore
*agreement with the Gemini full-text baseline*, as with judge.py.

Decisions takes its evidence as a string, so the state judge-jev.py sends as an
object is sent here as indented JSON, and the two instruction strings are
joined into the question's single `instructions`.

Output: openai/<input-stem>.tsv in each input's directory (e.g.
results-en/vector5.jsonl → results-en/openai/vector5.tsv), one row per question:

  qid<TAB>correct<TAB>partial<TAB>incorrect<TAB>confidence

holding the three probabilities and the model's confidence. Turning them into a
verdict or a score is left to the reader.
Resume-safe: skips qids already present in the output file.

What produced a file is recorded once per file, not per row, in openai/MODELS.tsv:

  file<TAB>model<TAB>scheme      e.g. vector5.tsv  gpt-6-luna  choice@1a2b3c4d

`model` is the model the response reports; `scheme` is SCHEME_ID, a hash of
everything sent besides the per-question text (see scheme_id()). A file whose
recorded model or scheme differs from the current one stops the run, so a
resumed file never mixes versions or wordings.

Token usage: each question's usage is printed, and per-file and run totals are
printed at the end. The Decisions API is paid, so the run total is always
appended to llm7shi's shared usage.jsonl (also when interrupted), followed by
today's total for the model.

Requires OPENAI_API_KEY in the environment.
"""

import argparse
import hashlib
import json
from pathlib import Path

from llm7shi.statusline import StatusLine
from llm7shi.usage import Usage, append_usage, find_usage_file, print_today_totals
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "gpt-6-luna"

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

QUESTIONS = [{
    "type": "choice",
    "name": "verdict",
    "instructions": " ".join(INSTRUCTIONS.values()),
    "choices": [{"value": v, "description": d} for v, d in CRITERIA.items()],
}]

TASK = ("Grading a candidate answer against the gold-standard answer for a "
        "reading-comprehension question about a novel")

HEADER = "\t".join(["qid", *VERDICTS, "confidence"])
MODELS_FILE = "MODELS.tsv"
MODELS_HEADER = "file\tmodel\tscheme"


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


def scheme_id() -> str:
    """`choice@<8 hex>` over everything that shapes the probabilities.

    That is the joined instructions, the choices (values and descriptions, in
    order), and the input rendered from an empty state, which fixes the key
    order, the `task` text and the JSON layout; only the per-question values
    are left out.
    """
    q = QUESTIONS[0]
    parts = [q["instructions"],
             *(f"{c['value']}={c['description']}" for c in q["choices"]),
             format_input(build_state("", "", "", ""))]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"choice@{digest[:8]}"


SCHEME_ID = scheme_id()


def judge_answer(client: OpenAI, state: dict, model: str, expect_model: str):
    """One request, returning ({verdict: probability}, confidence, Usage, served model).

    A model other than the expected one raises SystemExit so it aborts the
    run instead of being retried — the alias having moved is not transient.
    A refusal or a missing or malformed answer raises ValueError so it is retried.
    """
    response = client.decisions.create(model=model, input=format_input(state),
                                       questions=QUESTIONS)
    if expect_model and response.model != expect_model:
        raise SystemExit(f"requested {model} but {response.model} answered; "
                         f"the run is abandoned rather than mixing versions")
    answer = next((a for a in response.answers if a.name == "verdict"), None)
    if answer is None or answer.type != "choice":
        raise ValueError(f"unexpected answer: {answer!r}")
    probabilities = {p.value: float(p.probability) for p in answer.probabilities}
    if set(probabilities) != set(VERDICTS):
        raise ValueError(f"unexpected answer: {answer!r}")
    usage = Usage()
    if response.usage:
        usage = Usage(raw=response.usage.model_dump())
    return ({v: probabilities[v] for v in VERDICTS}, float(answer.confidence),
            usage, response.model)


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


def check_run(path: Path, name: str, model: str | None) -> None:
    """Check `name`'s entry in MODELS.tsv against SCHEME_ID and `model`.

    A differing recorded scheme, or a differing recorded model when `model` is
    given, stops the run. With `model` given and no entry yet, the entry is
    written. `model` is None for the check before any request, when only the
    scheme is known.
    """
    models = read_models(path)
    recorded = models.get(name)
    if recorded is not None:
        rec_model, rec_scheme = recorded
        if rec_scheme != SCHEME_ID:
            raise SystemExit(f"{path}: {name} was judged on {rec_scheme}, this run is "
                             f"{SCHEME_ID}; the run is abandoned rather than mixing wordings")
        if model is not None and rec_model != model:
            raise SystemExit(f"{path}: {name} was judged by {rec_model} but {model} answered; "
                             f"the run is abandoned rather than mixing versions")
        return
    if model is None:
        return
    models[name] = (model, SCHEME_ID)
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
                        help=f"OpenAI Decisions model (default: {DEFAULT_MODEL})")
    parser.add_argument("--expect-model",
                        help="model the response must report, if not --model itself; "
                             "empty accepts whatever answers, which an alias needs")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (gold standard; default: questions-<lang>.jsonl)")
    parser.add_argument("-n", "--count", type=int, default=None,
                        help="judge at most N new questions per input file, then stop")
    parser.add_argument("--attempts", type=int, default=3,
                        help="attempts per question (default: 3)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="per-request timeout in seconds (default: 120)")
    parser.add_argument("--started-at", type=float, default=None,
                        help="unix timestamp the batch started (enables an overall-elapsed "
                             "column spanning multiple invocations, as in judge.py)")
    args = parser.parse_args()

    args.input = args.input or str(ROOT / f"questions-{args.lang}.jsonl")
    # The requested name is its own pin; only an alias needs --expect-model spelled out.
    expect_model = args.model if args.expect_model is None else args.expect_model

    questions = load_questions(Path(args.input))
    print(f"Gold questions: {len(questions)}")

    ui = StatusLine()
    usage_path = find_usage_file()
    usages = []
    served_model = args.model

    try:
        with OpenAI(timeout=args.timeout) as client:
            for file_no, input_str in enumerate(args.inputs, start=1):
                in_path = Path(input_str)
                out_path = in_path.parent / "openai" / f"{in_path.stem}.tsv"
                out_path.parent.mkdir(exist_ok=True)
                label = in_path.stem
                # With several inputs, show which file of how many is running.
                progress_label = (f"{label} ({file_no}/{len(args.inputs)})"
                                  if len(args.inputs) > 1 else label)

                # The scheme is known before any request, so a mismatch stops the
                # run here without spending tokens; the model is checked per answer.
                models_path = out_path.parent / MODELS_FILE
                check_run(models_path, out_path.name, None)
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
                        for attempt in range(1, args.attempts + 1):
                            try:
                                probabilities, confidence, usage, served_model = judge_answer(
                                    client, state, args.model, expect_model)
                                break
                            except SystemExit:
                                raise
                            except Exception as e:
                                ui.stream.print(f"  attempt {attempt}/{args.attempts} failed: {e}")
                        else:
                            raise SystemExit(f"GIVING UP on Q{qid} after {args.attempts} attempts")

                        # Counted before the version check, since the tokens are spent
                        # even when the row is then refused.
                        usages.append(usage)
                        file_usages.append(usage)
                        check_run(models_path, out_path.name, served_model)
                        ui.stream.print("  " + " ".join(f"{v}={p:.2f}" for v, p in probabilities.items())
                                        + f" (confidence {confidence:.2f})")
                        ui.stream.print(f"  {usage!r}")

                        out_f.write("\t".join([str(qid), *(f"{probabilities[v]:g}" for v in VERDICTS),
                                               f"{confidence:g}"]) + "\n")
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
