#!/usr/bin/env python3
"""Answer evaluation questions using a per-chapter relevance filter.

A trimmed variant of per-chapter extraction: instead of summarizing each
chapter, Phase 1 asks only "is this chapter relevant to the question?" and
emits a verdict. Phase 2 then answers from the full text of every kept
chapter. This puts Filter in the same role as Vector RAG — a retrieval step
that selects chapters — but uses the LLM itself as the retriever rather than
dense embeddings, giving a third retrieval strategy to compare against RAG
(vector) and Extract (summary).

The `--verdicts` switch selects the classification granularity. The two- and
three-level variants ultimately reduce Phase 2 to a binary keep/drop decision;
the difference is where the drop threshold sits:

  --verdicts 2: two-level verdict (`yes` / `no`). Phase 2 keeps only `yes`, so
           the model must be confident to include a chapter — a high bar that
           drops anything the model is not sure about.
  --verdicts 3 (default): three-level verdict (`yes` / `maybe` / `no`). Phase 2
           keeps every chapter whose verdict is not `no` (i.e., both `yes`
           and `maybe`), so uncertainty falls on the side of inclusion. The
           `maybe` label is a trick for shifting the threshold: by routing
           uncertain chapters through a middle verdict instead of forcing a
           yes/no call, the effective `no` bar rises and more chapters survive
           into Phase 2.
  --verdicts 10: eleven-level verdict (an integer 0-10). Phase 1 records the
           raw score per (chapter, question) pair so that the keep/drop
           threshold can be chosen *after* the distribution is observed — a
           single Phase 1 run feeds every threshold under test, instead of one
           run per threshold as with the 2- and 3-level variants. Phase 2 is
           intentionally NOT wired up for this variant yet: run only Phase 1
           (with --phase1) to produce filter10.tsv, inspect the score
           distribution, decide a threshold, then add the Phase 2 path.
  --verdicts 100: 101-level verdict (an integer 0-100), tried as a finer-grained
           counterpart of the 0-10 variant. It did not help: the model self-
           quantized to multiples of 10 (only 13 of 101 values used), so
           filter100 is filter10 scaled x10 with a worse gold-scored-0 floor
           (11 vs 7); filter.py --scale 100 prints only the occurrence count.
           See filter.md ("Filter100: filter10 x10"). Same Phase-1-only posture
           as --verdicts 10: run with --phase1 to produce filter100.tsv.

For each question in questions-<lang>.jsonl:
  Phase 1 (--phase1): For every chapter, ask the model whether the chapter is
           relevant to the question. CoT is disabled (include_thoughts=False)
           and the model replies with a single word (plain text, no structured
           schema).
           Output: results-<lang>/filter{V}.tsv (V = verdicts, e.g. filter3.tsv) — a TSV with
           a `chapter	question_id	verdict` header followed by one row per (chapter, question).
  Phase 2 (no --phase1): Concatenate the FULL chapter text of every kept chapter
           and ask the model to answer.
           Output: results-<lang>/filter{V}.jsonl (e.g. filter3.jsonl).

Resume-safe: skips question IDs already in the output; skips (qid, chapter)
pairs already in the verdict TSV.
"""

import argparse
import json
import re
from pathlib import Path

from answer import (
    ROOT, LANGS,
    load_chapters, load_questions, answer_question, print_banner, print_answer_banner,
)
from llm7shi.compat import generate_with_schema


# Phase 1 part files are simple three-column tables — one row per classified
# (chapter, question_id) pair — so they are stored as TSV rather than JSONL.
# The first line is this header, which the readers skip.
VERDICT_HEADER = "chapter	question_id	verdict"


def read_verdict_tsv(path: Path):
    """Yield (chapter, question_id, verdict) tuples from a part TSV.

    Skips the header row (first line whose first field is `chapter`) and blank
    lines, so the same loader works for both a fresh file and a resumed one.
    """
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\n")
            if not line:
                continue
            fields = line.split("	")
            if i == 0 and fields[0] == "chapter":
                continue  # header
            ch, qid, verdict = fields
            yield int(ch), int(qid), verdict


def classify_chapter(question: str, chapter: int, chapter_text: str, model: str,
                     levels: int = 3) -> str:
    context = f"Chapter {chapter} text:\n{chapter_text}"
    if levels == 2:
        options = (
            "Reply with `yes` or `no` — nothing else.\n"
            "  - `yes`: contains relevant information.\n"
            "  - `no`: contains nothing relevant.\n"
        )
        # Inclusion-side default on an unparseable reply keeps the chapter,
        # mirroring the three-level variant's `maybe` fallback. With only two
        # verdicts the inclusion side is `yes`, so an unclear reply falls on
        # the side of keeping the chapter rather than dropping it.
        default = "yes"
        accept = ("y", "n")
    else:
        options = (
            "Reply with `yes`, `maybe`, or `no` — nothing else.\n"
            "  - `yes`: clearly contains relevant information.\n"
            "  - `maybe`: might contain relevant information (partial, indirect, or uncertain).\n"
            "  - `no`: contains nothing relevant.\n"
        )
        # Defaulting ambiguous replies to `maybe` makes an unparseable answer
        # fall on the side of keeping the chapter rather than dropping it.
        default = "maybe"
        accept = ("y", "m", "n")
    prompt = (
        f"Does the chapter text above contain any information relevant to "
        f"answering the question below?\n"
        f"{options}\n"
        f"Question: {question}"
    )
    # include_thoughts=False disables the model's thinking channel (Ollama
    # think=False), so the verdict is a pure classification with no CoT — the
    # whole point of this method versus Extract's summarization. The model is
    # expected to reply with a single word; if it produces something whose
    # first letter is not in `accept`, retry up to 3 times then default.
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
        if levels == 3 and text.startswith("m"):
            return "maybe"
        if attempt < max_retries:
            accepted = "/".join(repr(a) for a in accept)
            print(f"  unclear verdict ({raw!r}, expected {accepted}) — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  still unclear after {max_retries} retries — defaulting to {default} ({raw!r})")
    return default


def classify_chapter_score(question: str, chapter: int, chapter_text: str,
                           model: str, scale_max: int = 10) -> int:
    """Rate a chapter's relevance on a 0-`scale_max` integer scale.

    Unlike `classify_chapter`, which collapses relevance onto a small label
    set, this returns the raw score so the keep/drop threshold can be chosen
    after the distribution is observed — one Phase 1 run feeds every
    threshold under test. `scale_max` is 10 for the `--verdicts 10` variant
    and 100 for `--verdicts 100` (the finer-grained variant, motivated by the
    filter10 run's bimodal collapse onto 0 and 10).

    The reply is parsed for the first integer token in [0, scale_max]; on an
    unclear reply it retries up to 3 times, then defaults to `scale_max // 2`
    (mid-scale: 5 for scale 10, 50 for scale 100) so an unparseable answer
    lands in the middle rather than silently dropping or keeping the chapter.
    """
    context = f"Chapter {chapter} text:\n{chapter_text}"
    options = (
        f"Reply with a single integer from 0 to {scale_max} — nothing else.\n"
        f"  - 0: completely irrelevant to the question.\n"
        f"  - {scale_max}: directly and fully answers the question.\n"
        f"  - Use intermediate values for partial or indirect relevance.\n"
    )
    prompt = (
        f"Rate how relevant the chapter text above is to answering the "
        f"question below, on an integer scale from 0 to {scale_max}.\n"
        f"{options}\n"
        f"Question: {question}"
    )
    max_retries = 3
    default = scale_max // 2
    for attempt in range(max_retries + 1):
        result = generate_with_schema(
            [context, prompt], model=model,
            include_thoughts=False, show_params=False,
        )
        raw = result.text.strip()
        m = re.search(r"\b(\d{1,3})\b", raw)
        if m:
            score = int(m.group(1))
            if 0 <= score <= scale_max:
                return score
        if attempt < max_retries:
            print(f"  unclear score ({raw!r}, expected 0-{scale_max}) — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  still unclear after {max_retries} retries — defaulting to {default} ({raw!r})")
    return default


# Filter's Phase 2 reads full chapter text (not summaries), so the wording
# matches RAG's neutral "context provided" phrasing rather than Extract's
# "chapter excerpts below".
FILTER_PREAMBLE = (
    "Answer the following question in {lang_name} based ONLY on the context provided. "
    "Do not use any outside knowledge. "
    "Reply with the answer only — no preamble, no reasoning, no closing remarks."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-o", "--output", default=None,
                        help="output JSONL path (default: qa-eval/results-<lang>/filter{V}.jsonl where V = --verdicts)")
    parser.add_argument("-p", "--phase1", action="store_true",
                        help="run Phase 1 only: classify every (chapter, question) pair into filter{V}.tsv; "
                             "omit to run Phase 2 (answer from kept chapters)")
    parser.add_argument("--verdicts", type=int, default=3, choices=[2, 3, 10, 100],
                        help="relevance granularity: 3 = yes/maybe/no (keep yes+maybe), 2 = yes/no (keep yes only), 10 = integer 0-10 (Phase 1 only), 100 = integer 0-100 (Phase 1 only)")
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.scenes = args.scenes or str(ROOT / "all" / f"{lang}-gemini.jsonl")

    stem = f"filter{args.verdicts}"
    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / f"{stem}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(Path(args.input))
    total = len(questions)

    if args.phase1:
        # Phase 1: classify each (chapter, question) pair by relevance. All
        # chapters go into a single verdict TSV (filter{V}.tsv) — the files are
        # small and fast to generate, so there is no need to split by chapter
        # group the way extract does.
        print(f"Loading scenes from {args.scenes}")
        chapters = load_chapters(Path(args.scenes))
        all_chapter_ids = sorted(chapters.keys())
        print(f"Questions: {total}")

        verdict_path = output_path.with_name(output_path.stem + ".tsv")

        # Resume: collect done (qid, chapter) pairs as verdict strings.
        done: dict[tuple[int, int], str] = {}
        if verdict_path.exists():
            for ch, qid, verdict in read_verdict_tsv(verdict_path):
                done[(qid, ch)] = verdict
        if done:
            print(f"Checkpoint: {len(done)} chapter classifications already done")

        # Write the TSV header once when starting a fresh file so that resumed
        # appends do not duplicate it.
        if not verdict_path.exists():
            with open(verdict_path, "w", encoding="utf-8") as ckpt_f:
                ckpt_f.write(VERDICT_HEADER + "\n")

        with open(verdict_path, "a", encoding="utf-8") as ckpt_f:
            for ch in all_chapter_ids:
                chapter_text = "\n\n".join(s["text"] for s in chapters[ch])
                for qid, q in enumerate(questions, start=1):
                    if (qid, ch) in done:
                        continue

                    question_text = q["question"]
                    print_banner(f"[Ch{ch} Q{qid}/{total}] {question_text}")

                    if args.verdicts in (10, 100):
                        verdict = str(classify_chapter_score(
                            question_text, ch, chapter_text, args.model,
                            scale_max=args.verdicts))
                    else:
                        verdict = classify_chapter(question_text, ch, chapter_text, args.model,
                                                   levels=args.verdicts)
                    done[(qid, ch)] = verdict
                    ckpt_f.write(f"{ch}\t{qid}\t{verdict}\n")
                    ckpt_f.flush()

        print(f"Done → {verdict_path}")

    else:
        # Phase 2: answer each question from the full text of its relevant chapters.
        if args.verdicts in (10, 100):
            parser.error(
                f"Phase 2 is not wired up for --verdicts {args.verdicts} yet: "
                f"the keep/drop threshold must be chosen first. Run Phase 1 "
                f"only (with --phase1) to produce filter{args.verdicts}.tsv, "
                f"inspect the score distribution, then decide a threshold."
            )
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
        verdict_path = output_path.with_name(output_path.stem + ".tsv")
        if verdict_path.exists():
            for ch, qid, verdict in read_verdict_tsv(verdict_path):
                verdict_map[(qid, ch)] = verdict
        print(f"Loaded {len(verdict_map)} chapter classifications from {verdict_path.name}")

        print(f"Loading scenes from {args.scenes}")
        chapters = load_chapters(Path(args.scenes))
        print(f"Questions: {total}")

        with open(output_path, "a", encoding="utf-8") as out_f:
            for qid, q in enumerate(questions, start=1):
                if qid in done_qids:
                    continue

                question_text = q["question"]
                # Inclusion rule depends on the verdict granularity:
                #   3-value: keep every chapter whose verdict is not `no`
                #            (both `yes` and `maybe`), resolving uncertainty
                #            toward inclusion.
                #   2-value: keep only `yes` — a stricter bar, since there is
                #            no `maybe` to rescue uncertain-but-relevant
                #            chapters.
                if args.verdicts == 2:
                    selected_chapters = sorted(
                        ch for ch in chapters
                        if verdict_map.get((qid, ch), "no") == "yes"
                    )
                else:
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
