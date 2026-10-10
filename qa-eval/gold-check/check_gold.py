#!/usr/bin/env python3
"""Check whether each gold answer's facts are written in the cited chapters.

The questions and gold answers were written from the English text and
translated into Japanese, but nothing checked that the Japanese text, a
separate translation of the Bengali original, carries every detail a gold
answer asks for. A detail missing there is one a Japanese answer cannot give.

Two steps, both with the same model:

  facts    Split each English gold answer (the original) into short factual
           claims → facts.jsonl. Both texts are checked against this one list,
           so a claim's verdicts can be compared across the languages.
  check    For each question, give the model the full text of its gold
           `chapters` in one language (as Ceiling does) and the claims, and
           ask for each claim whether the text states it → check-<lang>.jsonl.

Records:

  facts.jsonl        {"question_id", "facts": [str, ...]}
  check-<lang>.jsonl {"question_id", "claims": [{"id", "evidence", "reason",
                      "verdict"}, ...]}, verdict one of stated / missing /
                      contradicted, `id` the 1-origin index into facts

Each record also carries the model and reasoning effort. Resume-safe: question
IDs already in the output are skipped. A reply whose claim ids do not match
the facts is retried. With --qids, only those questions are run, whether done
or not, and each new record replaces the question's old one in place (after a
gold answer is corrected, `facts` then `check` for both languages).

Token usage: each request's usage is printed, and the run total at the end.
For metered models (openai:/gpt-, or --save-usage) the run total is appended to
llm7shi's usage.jsonl (also when interrupted) under the model name without an
`openai:` prefix, followed by today's total for it.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from llm7shi.compat import generate_with_schema
from llm7shi.statusline import StatusLine
from llm7shi.usage import append_usage, find_usage_file, print_today_totals

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from answer import ROOT, LANGS, load_chapters, load_questions  # noqa: E402

DEFAULT_MODEL = "gpt-6-astra"
FACTS_FILE = HERE / "facts.jsonl"

FACTS_PROMPT = (
    "Split the gold answer to a reading-comprehension question about a novel "
    "into short factual claims, one fact each, so that every claim can be "
    "checked against the novel on its own. Keep names, numbers and specific "
    "details as the gold answer gives them, and resolve pronouns to names. "
    "Cover everything the gold answer states, and add nothing it does not."
)

CHECK_PROMPT = (
    "Below are chapters of a novel in {lang_name}, a question about them, and "
    "numbered claims in English taken from the question's gold answer. For "
    "each claim, decide whether the chapters state it.\n"
    "- stated: the chapters say it, in any wording, or it follows directly "
    "from what they say (also by combining chapters).\n"
    "- missing: the chapters do not say it; the detail is absent or only "
    "vaguer than the claim.\n"
    "- contradicted: the chapters say something incompatible with it.\n"
    "Names may be spelled differently in {lang_name}. Judge only against the "
    "chapters below, not against outside knowledge of the novel. As evidence, "
    "quote the shortest passage of the chapters that bears on the claim, "
    "verbatim in {lang_name}, or leave it empty if there is none."
)


class Facts(BaseModel):
    facts: list[str] = Field(..., description="The gold answer's factual claims, one fact each.")


class Claim(BaseModel):
    id: int = Field(..., description="The claim's number.")
    evidence: str = Field(..., description="Verbatim quote from the chapters, or empty.")
    reason: str = Field(..., description="One short sentence justifying the verdict.")
    verdict: Literal["stated", "missing", "contradicted"]


class Check(BaseModel):
    claims: list[Claim]


USAGE_PATH = None


def read_done(path: Path) -> set[int]:
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(l)["question_id"] for l in f if l.strip()}


def write_record(path: Path, record: dict, replace: bool, out_f) -> None:
    """Append `record`, or with `replace`, put it in place of the question's
    old record, keeping the other records and their order."""
    line = json.dumps(record, ensure_ascii=False)
    if not replace:
        out_f.write(line + "\n")
        out_f.flush()
        return
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    qid = record["question_id"]
    lines = [line if json.loads(l)["question_id"] == qid else l for l in lines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def todo(args, n: int, done: set[int]) -> set[int]:
    """Question IDs to run: --qids if given (all of them must be done already,
    so that each has a record to replace), otherwise those not done."""
    if not args.qids:
        return set(range(1, n + 1)) - done
    if missing := set(args.qids) - done:
        raise SystemExit(f"--qids {sorted(missing)} have no record to replace")
    return set(args.qids)


def load_facts() -> dict[int, list[str]]:
    with open(FACTS_FILE, encoding="utf-8") as f:
        return {r["question_id"]: r["facts"] for r in map(json.loads, filter(str.strip, f))}


def request(contents: str, schema, system_prompt: str, args, ui, usages: list):
    response = generate_with_schema([contents], schema, model=args.model,
                                    system_prompt=system_prompt,
                                    include_thoughts=args.effort != "none",
                                    reasoning_effort=args.effort,
                                    show_params=False, file=ui.stream)
    if response.usage is not None:
        usages.append(response.usage)
        ui.stream.print(f"  {response.usage!r}")
    return schema(**json.loads(response.text))


def run_facts(args, questions, ui, usages, prog):
    run = todo(args, len(questions), read_done(FACTS_FILE))
    finished = 0 if args.qids else len(questions) - len(run)
    with open(FACTS_FILE, "a", encoding="utf-8") as out_f:
        for qid, q in enumerate(questions, start=1):
            if qid not in run:
                continue
            ui.stream.print(f"\n[Q{qid}] {q['answer']}")
            contents = f"Question:\n{q['question']}\n\nGold answer:\n{q['answer']}"
            facts = request(contents, Facts, FACTS_PROMPT, args, ui, usages).facts
            for i, fact in enumerate(facts, start=1):
                ui.stream.print(f"  {i}. {fact}")
            record = {"question_id": qid, "facts": facts,
                      "model": args.model, "effort": args.effort}
            write_record(FACTS_FILE, record, bool(args.qids), out_f)
            finished += 1
            prog.update(finished)


def run_check(args, questions, ui, usages, prog):
    lang = args.lang
    facts = load_facts()
    chapters = load_chapters(ROOT / "all" / f"{lang}-gemini.jsonl")
    out_path = HERE / f"check-{lang}.jsonl"
    system_prompt = CHECK_PROMPT.format(lang_name=LANGS[lang])
    run = todo(args, len(questions), read_done(out_path))
    finished = 0 if args.qids else len(questions) - len(run)
    with open(out_path, "a", encoding="utf-8") as out_f:
        for qid, q in enumerate(questions, start=1):
            if qid not in run:
                continue
            claims = facts[qid]
            context = "\n\n".join(
                f"[Chapter {ch}]\n" + "\n\n".join(s["text"] for s in chapters[ch])
                for ch in sorted(q["chapters"]))
            contents = (f"Chapters:\n{context}\n\nQuestion:\n{q['question']}\n\nClaims:\n"
                        + "\n".join(f"{i}. {c}" for i, c in enumerate(claims, start=1)))
            ui.stream.print(f"\n[Q{qid}: {', '.join(map(str, sorted(q['chapters'])))}] {q['question']}")
            for attempt in range(1, args.attempts + 1):
                result = request(contents, Check, system_prompt, args, ui, usages)
                if sorted(c.id for c in result.claims) == list(range(1, len(claims) + 1)):
                    break
                ui.stream.print(f"  attempt {attempt}/{args.attempts}: claim ids "
                                f"{[c.id for c in result.claims]} do not match {len(claims)} facts")
            else:
                raise SystemExit(f"GIVING UP on Q{qid} after {args.attempts} attempts")
            result.claims.sort(key=lambda c: c.id)
            for c in result.claims:
                ui.stream.print(f"  {c.id}. {c.verdict}: {claims[c.id - 1]}")
            record = {"question_id": qid, "claims": [c.model_dump() for c in result.claims],
                      "model": args.model, "effort": args.effort}
            write_record(out_path, record, bool(args.qids), out_f)
            finished += 1
            prog.update(finished)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["facts", "check"])
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="check: language of the chapter text")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="llm7shi model string")
    parser.add_argument("--effort", default="medium",
                        help="reasoning effort; none turns reasoning off")
    parser.add_argument("--attempts", type=int, default=3, help="check: attempts per question")
    parser.add_argument("--save-usage", action="store_true",
                        help="record token usage to usage.jsonl regardless of the model")
    parser.add_argument("--qids", nargs="+", type=int, default=[],
                        help="redo these questions, replacing their records")
    args = parser.parse_args()

    global USAGE_PATH
    if args.model.startswith(("openai:", "gpt-")) or args.save_usage:
        USAGE_PATH = find_usage_file()
    usage_name = args.model.removeprefix("openai:")

    # The English questions for both languages: the claims are English, and
    # only the chapter text changes between the two checks.
    questions = load_questions(ROOT / "questions-en.jsonl")
    label = args.step if args.step == "facts" else f"check {args.lang}"
    done = read_done(FACTS_FILE if args.step == "facts" else HERE / f"check-{args.lang}.jsonl")

    ui = StatusLine()
    usages = []
    try:
        total, start = (len(args.qids), 0) if args.qids else (len(questions), len(done))
        with ui.progress(total, start=start, label=label) as prog:
            (run_facts if args.step == "facts" else run_check)(args, questions, ui, usages, prog)
    finally:
        if usages and USAGE_PATH is not None:
            append_usage(sum(usages), usage_name, USAGE_PATH)

    if usages:
        print(f"\n--- Total Usage ---\n{len(usages)} request(s), {sum(usages)}")
        if USAGE_PATH is not None:
            print("")
            print_today_totals(USAGE_PATH, models=[usage_name])


if __name__ == "__main__":
    main()
