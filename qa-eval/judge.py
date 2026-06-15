#!/usr/bin/env python3
"""Grade candidate answers against the gold standard with a judge LLM.

For each result file (e.g. results/rag.jsonl, results/extract.jsonl), compare
every candidate answer against the gold `answer` and `rationale` from
questions-en.jsonl. The judge emits a one-sentence reason and a verdict of
correct / partial / incorrect.

The `reason` field is declared before `verdict` in the schema so the model
writes its justification first and the verdict follows from it, rather than
being a post-hoc rationalization.

Output: results/judge-<input-stem>.jsonl (e.g. judge-rag.jsonl), one record per
question. Resume-safe: skips question IDs already present in the output file.

Retrieval quality (chapter recall) is computed mechanically by report.py, not
here; this script only produces the LLM verdict.
"""

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from llm7shi.compat import generate_with_schema

ROOT = Path(__file__).resolve().parent.parent


class Judgement(BaseModel):
    reason: str = Field(
        ..., description="One short sentence justifying the verdict."
    )
    verdict: Literal["correct", "partial", "incorrect"] = Field(
        ..., description="How well the candidate answer matches the gold answer."
    )


def load_questions(path: Path) -> dict[int, dict]:
    questions: dict[int, dict] = {}
    with open(path, encoding="utf-8") as f:
        for qid, line in enumerate((l for l in f if l.strip()), start=1):
            questions[qid] = json.loads(line)
    return questions


def judge_answer(question: str, gold: str, rationale: str, candidate: str, model: str) -> Judgement:
    prompt = (
        f"You are grading a candidate answer against the gold-standard answer for a "
        f"reading-comprehension question about a novel.\n"
        f"Grade only on factual content overlap with the gold answer, not on wording, "
        f"length, or style. Use the rationale as supporting evidence.\n"
        f"  - correct: captures the essential facts of the gold answer.\n"
        f"  - partial: captures some but misses or distorts key facts.\n"
        f"  - incorrect: wrong, irrelevant, or says no answer was found.\n\n"
        f"Question:\n{question}\n\n"
        f"Gold answer:\n{gold}\n\n"
        f"Rationale (evidence):\n{rationale}\n\n"
        f"Candidate answer:\n{candidate}"
    )
    # The model occasionally emits a too-short reason (blank, or just echoing
    # the verdict like "correct"); retry up to 3 times (4 attempts total), then
    # accept it rather than loop forever.
    max_retries = 3
    judgement = None
    for attempt in range(max_retries + 1):
        result = generate_with_schema([prompt], Judgement, model=model, show_params=False)
        judgement = Judgement(**json.loads(result.text))
        if len(judgement.reason.strip()) >= 20:
            break
        if attempt < max_retries:
            print(f"  reason too short ({len(judgement.reason.strip())} chars) — "
                  f"retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  reason still too short after {max_retries} retries — keeping as is")
    return judgement


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="result JSONL files to judge")
    parser.add_argument("-m", "--model", default="ollama:qwen3.6",
                        help="judge model (llm7shi string); Gemma 4 is weak at structured output")
    parser.add_argument("-i", "--input", default=str(ROOT / "questions-en.jsonl"),
                        help="questions JSONL (gold standard)")
    args = parser.parse_args()

    questions = load_questions(Path(args.input))
    print(f"Gold questions: {len(questions)}")

    for input_str in args.inputs:
        in_path = Path(input_str)
        out_path = in_path.with_name(f"judge-{in_path.stem}.jsonl")

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

        print(f"\n{'#'*60}")
        print(f"# {in_path} → {out_path}  ({len(records)} answers)")
        if done_ids:
            print(f"# Resuming: {len(done_ids)} already done")
        print('#'*60)

        total = len(records)
        with open(out_path, "a", encoding="utf-8") as out_f:
            for i, rec in enumerate(records, start=1):
                qid = rec["question_id"]
                if qid in done_ids:
                    continue

                q = questions[qid]
                print(f"\n[{i}/{total}] Q{qid}")
                judgement = judge_answer(
                    q["question"], q["answer"], q["rationale"], rec["answer"], args.model
                )

                out_f.write(json.dumps({
                    "question_id": qid,
                    "verdict": judgement.verdict,
                    "reason": judgement.reason,
                }, ensure_ascii=False) + "\n")
                out_f.flush()

        print(f"Done → {out_path}")


if __name__ == "__main__":
    main()
