#!/usr/bin/env python3
"""Answer evaluation questions using a per-chapter yes/maybe/no relevance filter.

A trimmed variant of per-chapter extraction: instead of summarizing each
chapter, Phase 1 asks only "is this chapter relevant to the question?" and
emits a three-level verdict (`yes` / `maybe` / `no`). Phase 2 then answers
from the full text of every chapter whose verdict is not `no` — i.e., both
`yes` and `maybe` are kept, so uncertainty falls on the side of inclusion and
the filter only drops a chapter when the model is confident it is irrelevant.
This puts Filter in the same role as Vector RAG — a retrieval step that
selects chapters — but uses the LLM itself as the retriever rather than dense
embeddings, giving a third retrieval strategy to compare against RAG (vector)
and Extract (summary).

For each question in questions-<lang>.jsonl:
  Phase 1 (--part 1-4): For chapters in the given range, ask the model whether
           the chapter is relevant to the question. CoT is disabled
           (include_thoughts=False) and the model replies with the single word
           `yes`, `maybe`, or `no` (plain text, no structured schema).
           Output: results-<lang>/filter-{N}.jsonl.
  Phase 2 (no --part): Concatenate the FULL chapter text of every chapter
           whose verdict is not `no` and ask the model to answer.
           Output: results-<lang>/filter.jsonl.

Chapter groups (shared with answer_extract.py):
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

from answer import (
    ROOT, LANGS, PART_RANGES,
    load_chapters, load_questions, answer_question, print_banner, print_answer_banner,
)
from llm7shi.compat import generate_with_schema


def classify_chapter(question: str, chapter: int, chapter_text: str, model: str) -> str:
    context = f"Chapter {chapter} text:\n{chapter_text}"
    prompt = (
        f"Does the chapter text above contain any information relevant to "
        f"answering the question below?\n"
        f"Reply with `yes`, `maybe`, or `no` — nothing else.\n"
        f"  - `yes`: clearly contains relevant information.\n"
        f"  - `maybe`: might contain relevant information (partial, indirect, or uncertain).\n"
        f"  - `no`: contains nothing relevant.\n\n"
        f"Question: {question}"
    )
    # include_thoughts=False disables the model's thinking channel (Ollama
    # think=False), so the verdict is a pure classification with no CoT — the
    # whole point of this method versus Extract's summarization. The model is
    # expected to reply with a single word; if it produces something whose
    # first letter is not y/m/n, retry up to 3 times then default to `maybe`.
    # Phase 2 keeps any verdict that is not `no` (so both `yes` and `maybe`),
    # and defaulting ambiguous replies to `maybe` makes an unparseable answer
    # fall on the side of keeping the chapter rather than dropping it.
    max_retries = 3
    for attempt in range(max_retries + 1):
        result = generate_with_schema(
            [context, prompt], model=model,
            include_thoughts=False, show_params=False,
        )
        raw = result.text.strip()
        text = raw.lower()
        if text.startswith("y"):
            return "yes"
        if text.startswith("n"):
            return "no"
        if text.startswith("m"):
            return "maybe"
        if attempt < max_retries:
            print(f"  unclear yes/maybe/no ({raw!r}) — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  still unclear after {max_retries} retries — defaulting to maybe ({raw!r})")
    return "maybe"


# Filter's Phase 2 reads full chapter text (not summaries), so the wording
# matches RAG's neutral "context provided" phrasing rather than Extract's
# "chapter excerpts below".
FILTER_PREAMBLE = (
    "Answer the following question in {lang_name} based ONLY on the context provided. "
    "Do not use any outside knowledge. "
    "Reply with the answer only — no preamble, no reasoning, no closing remarks."
)


def parse_parts(arg: str, parser: argparse.ArgumentParser) -> list[int]:
    if arg is None:
        return []
    if "-" in arg:
        lo_s, hi_s = arg.split("-", 1)
        parts = list(range(int(lo_s), int(hi_s) + 1))
    else:
        parts = [int(arg)]
    invalid = [p for p in parts if p not in PART_RANGES]
    if invalid:
        parser.error(f"part values out of range (1-4): {invalid}")
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-o", "--output", default=None, help="output JSONL path (default: qa-eval/results-<lang>/filter.jsonl)")
    parser.add_argument("-p", "--part", default=None,
                        help="chapter group(s) to process: single (e.g. 2) or range (e.g. 1-4); omit to run Phase 2 only")
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.scenes = args.scenes or str(ROOT / "all" / f"{lang}-gemini.jsonl")

    parts = parse_parts(args.part, parser)

    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / "filter.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(Path(args.input))
    total = len(questions)

    if parts:
        # Phase 1: classify each (chapter, question) pair as yes/maybe/no.
        print(f"Loading scenes from {args.scenes}")
        chapters = load_chapters(Path(args.scenes))
        all_chapter_ids = sorted(chapters.keys())
        print(f"Questions: {total}")

        for part in parts:
            part_path = output_path.with_name(output_path.stem + f"-{part}.jsonl")
            lo, hi = PART_RANGES[part]
            chapter_ids = [ch for ch in all_chapter_ids if lo <= ch <= hi]
            print(f"\nPart {part}: chapters {lo}-{hi} ({len(chapter_ids)} chapters)")

            # Resume: collect done (qid, chapter) pairs as verdict strings.
            done: dict[tuple[int, int], str] = {}
            if part_path.exists():
                with open(part_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            done[(rec["question_id"], rec["chapter"])] = rec["verdict"]
            if done:
                print(f"Checkpoint: {len(done)} chapter classifications already done")

            with open(part_path, "a", encoding="utf-8") as ckpt_f:
                for ch in chapter_ids:
                    chapter_text = "\n\n".join(s["text"] for s in chapters[ch])
                    for qid, q in enumerate(questions, start=1):
                        if (qid, ch) in done:
                            continue

                        question_text = q["question"]
                        print_banner(f"[Ch{ch} Q{qid}/{total}] {question_text}")

                        verdict = classify_chapter(question_text, ch, chapter_text, args.model)
                        done[(qid, ch)] = verdict
                        ckpt_f.write(json.dumps(
                            {"chapter": ch, "question_id": qid, "verdict": verdict},
                            ensure_ascii=False,
                        ) + "\n")
                        ckpt_f.flush()

            print(f"Done → {part_path}")

    else:
        # Phase 2: answer each question from the full text of its relevant chapters.
        done_qids: set[int] = set()
        if output_path.exists():
            with open(output_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        done_qids.add(json.loads(line)["question_id"])
        if done_qids:
            print(f"Resuming: {len(done_qids)} questions already done")

        # Unlike extract, Phase 2 needs the chapter text (Phase 1 stored only
        # verdicts), so the scenes file is required here too.
        verdict_map: dict[tuple[int, int], str] = {}
        for p in range(1, 5):
            part_path = output_path.with_name(output_path.stem + f"-{p}.jsonl")
            if part_path.exists():
                with open(part_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            verdict_map[(rec["question_id"], rec["chapter"])] = rec["verdict"]
        print(f"Loaded {len(verdict_map)} chapter classifications from part files")

        print(f"Loading scenes from {args.scenes}")
        chapters = load_chapters(Path(args.scenes))
        print(f"Questions: {total}")

        with open(output_path, "a", encoding="utf-8") as out_f:
            for qid, q in enumerate(questions, start=1):
                if qid in done_qids:
                    continue

                question_text = q["question"]
                # Keep every chapter whose verdict is not `no` — both `yes`
                # and `maybe` count as relevant, so uncertainty is resolved in
                # favor of keeping the chapter rather than dropping it.
                selected_chapters = sorted(
                    ch for ch in chapters
                    if verdict_map.get((qid, ch), "no") != "no"
                )

                print_answer_banner(qid, total, selected_chapters, question_text)

                if not selected_chapters:
                    answer = "No relevant content found."
                    print(answer)
                else:
                    context = "\n\n".join(
                        f"[Chapter {ch}]\n" + "\n\n".join(s["text"] for s in chapters[ch])
                        for ch in selected_chapters
                    )
                    answer = answer_question(
                        question_text, context, args.model, lang_name,
                        preamble=FILTER_PREAMBLE, context_prefix="Context:\n",
                    )

                record = {
                    "question_id": qid,
                    "expanded": [str(ch) for ch in selected_chapters],
                    "answer": answer,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()

        print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
