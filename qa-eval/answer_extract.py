#!/usr/bin/env python3
"""Answer evaluation questions using per-chapter extraction.

For each question in questions-en.jsonl:
  Phase 1 (--part 1-4): For chapters in the given range, ask the model to
           summarize relevant content or output "None" if there is none.
           Output saved to results-<lang>/extract-{N}.jsonl.
  Phase 2 (no --part): Concatenate relevant summaries from all 4 part files
           and ask the model to answer. Output: results-<lang>/extract.jsonl.

Chapter groups:
  Part 1: chapters 1-10
  Part 2: chapters 11-20
  Part 3: chapters 21-30
  Part 4: chapters 31-37

Phase 1 is 37 chapters × 50 questions = 1,850 calls; the outer loop iterates
chapters and the inner loop questions, so the same chapter text stays in the KV
cache across all questions for that chapter. The Phase 2 output record holds
`question_id`, `expanded` (chapter numbers with relevant content, as
`["5", "10", ...]`), and `answer`; each part file row holds `chapter`,
`question_id`, and `text` (the summary, or `"None"`).

Resume-safe: skips question IDs already in the output; skips (qid, chapter)
pairs already in the part file.

Its main failure mode is a Phase 1 false negative: a wrong `None` drops a gold
chapter unrecoverably, so Phase 2 never sees it (the missed-context losses
report.py attributes to Extract).
"""

import argparse
import json
from pathlib import Path

from answer import (
    ROOT, LANGS, PART_RANGES,
    load_chapters, load_questions, answer_question, print_banner, print_answer_banner,
)
from llm7shi.compat import generate_with_schema


def extract_chapter(question: str, chapter: int, chapter_text: str, model: str, lang_name: str) -> str:
    context = f"Chapter {chapter} text:\n{chapter_text}"
    prompt = (
        f"Read the chapter text provided above and summarize in {lang_name} any content relevant to the question below.\n"
        f"If there is no relevant content, output exactly: None\n\n"
        f"Question: {question}"
    )
    # An empty string means the model ignored the "output None" instruction;
    # retry up to 3 times (4 attempts total) before keeping the empty result.
    max_retries = 3
    text = ""
    for attempt in range(max_retries + 1):
        result = generate_with_schema([context, prompt], model=model, show_params=False)
        text = result.text.strip()
        if text:
            return text
        if attempt < max_retries:
            print(f"  empty extraction — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  extraction still empty after {max_retries} retries — keeping as is")
    return text


EXTRACT_PREAMBLE = (
    "Answer the following question in {lang_name} based ONLY on the chapter excerpts below.\n"
    "Do not use any outside knowledge.\n"
    "Reply with the answer only — no preamble, no reasoning, no closing remarks."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-o", "--output", default=None, help="output JSONL path (default: qa-eval/results-<lang>/extract.jsonl)")
    parser.add_argument("-p", "--part", default=None,
                        help="chapter group(s) to process: single (e.g. 2) or range (e.g. 1-4); omit to run Phase 2 only")
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.scenes = args.scenes or str(ROOT / "all" / f"{lang}-gemini.jsonl")

    parts: list[int] = []
    if args.part is not None:
        s = args.part
        if '-' in s:
            lo_s, hi_s = s.split('-', 1)
            parts = list(range(int(lo_s), int(hi_s) + 1))
        else:
            parts = [int(s)]
        invalid = [p for p in parts if p not in PART_RANGES]
        if invalid:
            parser.error(f"part values out of range (1-4): {invalid}")

    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / "extract.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(Path(args.input))
    total = len(questions)

    if parts:
        # Phase 1: extract chapters for each requested part
        print(f"Loading scenes from {args.scenes}")
        chapters = load_chapters(Path(args.scenes))
        all_chapter_ids = sorted(chapters.keys())
        print(f"Questions: {total}")

        for part in parts:
            part_path = output_path.with_name(output_path.stem + f"-{part}.jsonl")
            lo, hi = PART_RANGES[part]
            chapter_ids = [ch for ch in all_chapter_ids if lo <= ch <= hi]
            print(f"\nPart {part}: chapters {lo}-{hi} ({len(chapter_ids)} chapters)")

            # Resume: collect done (qid, chapter) pairs
            done_extractions: dict[tuple[int, int], str] = {}
            if part_path.exists():
                with open(part_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            done_extractions[(rec["question_id"], rec["chapter"])] = rec["text"]
            if done_extractions:
                print(f"Checkpoint: {len(done_extractions)} chapter extractions already done")

            with open(part_path, "a", encoding="utf-8") as ckpt_f:
                for ch in chapter_ids:
                    chapter_text = "\n\n".join(s["text"] for s in chapters[ch])
                    for qid, q in enumerate(questions, start=1):
                        if (qid, ch) in done_extractions:
                            continue

                        question_text = q["question"]
                        print_banner(f"[Ch{ch} Q{qid}/{total}] {question_text}")

                        text = extract_chapter(question_text, ch, chapter_text, args.model, lang_name)
                        done_extractions[(qid, ch)] = text
                        ckpt_f.write(json.dumps({"chapter": ch, "question_id": qid, "text": text}, ensure_ascii=False) + "\n")
                        ckpt_f.flush()

            print(f"Done → {part_path}")

    else:
        # Phase 2: synthesize answers from all 4 part files
        done_qids: set[int] = set()
        if output_path.exists():
            with open(output_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        done_qids.add(json.loads(line)["question_id"])
        if done_qids:
            print(f"Resuming: {len(done_qids)} questions already done")

        done_extractions: dict[tuple[int, int], str] = {}
        for p in range(1, 5):
            part_path = output_path.with_name(output_path.stem + f"-{p}.jsonl")
            if part_path.exists():
                with open(part_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            done_extractions[(rec["question_id"], rec["chapter"])] = rec["text"]
        print(f"Loaded {len(done_extractions)} chapter extractions from part files")

        all_chapter_ids = sorted({ch for _, ch in done_extractions})
        print(f"Questions: {total}")

        with open(output_path, "a", encoding="utf-8") as out_f:
            for qid, q in enumerate(questions, start=1):
                if qid in done_qids:
                    continue

                question_text = q["question"]
                relevant = {ch: done_extractions[(qid, ch)] for ch in all_chapter_ids
                            if done_extractions.get((qid, ch), "None").strip() not in ("None", "")}

                print_answer_banner(qid, total, sorted(relevant.keys()), question_text)

                if not relevant:
                    answer = "No relevant content found."
                    print(answer)
                else:
                    context = "\n\n".join(f"[Chapter {ch}]\n{text}" for ch, text in sorted(relevant.items()))
                    answer = answer_question(question_text, context, args.model, lang_name,
                                             preamble=EXTRACT_PREAMBLE)

                record = {
                    "question_id": qid,
                    "expanded": [str(ch) for ch in sorted(relevant.keys())],
                    "answer": answer,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()

        print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
