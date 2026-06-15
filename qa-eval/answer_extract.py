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

Resume-safe: skips question IDs already in the output; skips (qid, chapter)
pairs already in the part file.
"""

import argparse
import json
from pathlib import Path

from llm7shi.compat import generate_with_schema

ROOT = Path(__file__).resolve().parent.parent

LANGS = {"en": "English", "ja": "Japanese"}

PART_RANGES = {1: (1, 10), 2: (11, 20), 3: (21, 30), 4: (31, 37)}


def load_chapters(path: Path) -> dict[int, list[dict]]:
    chapters: dict[int, list[dict]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            ch, seg = rec.get("chapter", 0), rec.get("segment", 0)
            if ch == 0 or seg == 0:
                continue
            chapters.setdefault(ch, []).append({
                "chapter": ch,
                "segment": seg,
                "text": rec["response"]["translation"],
            })
    for scenes in chapters.values():
        scenes.sort(key=lambda s: s["segment"])
    return chapters


def load_questions(path: Path) -> list[dict]:
    questions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def extract_chapter(question: str, chapter: int, chapter_text: str, model: str, lang_name: str) -> str:
    context = f"Chapter {chapter} text:\n{chapter_text}"
    prompt = (
        f"Read the chapter text provided above and summarize in {lang_name} any content relevant to the question below.\n"
        f"If there is no relevant content, output exactly: None\n\n"
        f"Question: {question}"
    )
    result = generate_with_schema([context, prompt], model=model, show_params=False)
    return result.text.strip()


def answer_question(question: str, context: str, model: str, lang_name: str) -> str:
    prompt = (
        f"Answer the following question in {lang_name} based ONLY on the chapter excerpts below.\n"
        f"Do not use any outside knowledge.\n"
        f"Reply with the answer only — no preamble, no reasoning, no closing remarks.\n\n"
        f"Question: {question}\n\n"
        f"{context}"
    )
    result = generate_with_schema([prompt], model=model, show_params=False)
    return result.text.strip()


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
                        print(f"\n{'='*60}")
                        print(f"[Q{qid}/{total} Ch{ch}] {question_text[:80]}")
                        print('='*60)

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

                print(f"\n{'='*60}")
                print(f"[Q{qid}/{total} Answer] {len(relevant)} relevant chapters")
                print('='*60)

                if not relevant:
                    answer = "No relevant content found."
                else:
                    context = "\n\n".join(f"[Chapter {ch}]\n{text}" for ch, text in sorted(relevant.items()))
                    answer = answer_question(question_text, context, args.model, lang_name)

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
