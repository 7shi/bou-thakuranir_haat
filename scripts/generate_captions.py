"""Generate a caption per segment in bn/hi/en/ja as a matched set.

`all/<lang>-gemini-summary.md` holds one paragraph-length summary per segment,
written independently per language by `translate_segments.py`, so the four
summaries of a segment differ in detail and emphasis. That is fine where they
are read on their own, but a caption is an index key: the same scene must be
named the same way in every language, or the four embedding indexes stop
agreeing with each other.

So this script does not shorten each language's summary on its own. For each
segment it reads all four summaries and asks the model, in one structured-
output call, for the caption in all four languages at once: the Bengali caption
is written first from the Bengali summary (the source language, with the other
three as supporting context), and the Hindi, English and Japanese captions are
strict translations of it rather than independent captions.

Records are appended to `all/captions.jsonl` as they are produced. If
interrupted, re-running loads that file and skips the segments already done.
Segments whose summaries are missing in some language are skipped rather than
erroring, so this can be run while the summaries are still being filled in.

A caption is the same kind of short scene label `generate_titles.py` writes, but
that script titles each language separately from its own translation and covers
only English and Japanese; these are a matched set across all four.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from llm7shi import Client

LANGS = [
    ("bn", "Bengali"),
    ("hi", "Hindi"),
    ("en", "English"),
    ("ja", "Japanese"),
]

PIVOT = "bn"

CHAPTER_RE = re.compile(r"^## Chapter (\d+)$", re.MULTILINE)


class SegmentCaption(BaseModel):
    """A segment's caption, given in Bengali and as strict translations of it"""
    caption_bn: str = Field(
        description="Caption for this segment, in Bengali: a short phrase naming the "
        "scene, the way a scene title does - not a sentence summarizing it. "
        "No trailing punctuation, no line breaks."
    )
    caption_hi: str = Field(
        description="Strict Hindi translation of caption_bn: same content, same "
        "emphasis - not an independent caption. No trailing punctuation, no line breaks."
    )
    caption_en: str = Field(
        description="Strict English translation of caption_bn: same content, same "
        "emphasis - not an independent caption. 5-12 words, in title case. "
        "No trailing punctuation, no line breaks."
    )
    caption_ja: str = Field(
        description="Strict Japanese translation of caption_bn: same content, same "
        "emphasis - not an independent caption. Plain style (no ですます). "
        "No trailing punctuation, no line breaks."
    )


INSTRUCTIONS = """The messages above give this segment's summary in Bengali, Hindi, English and Japanese. They were written independently, one language per translation run, so they differ in length, detail and emphasis; they describe the same segment.

Write a caption for this segment in Bengali, Hindi, English and Japanese.

- A caption names the scene, the way the title of an illustration or of a chapter section does. It is a short phrase, not a sentence summarizing what happens.
- Keep the English caption to 5-12 words, and the others proportionate; write each as a noun phrase where the language allows one, and keep the Japanese in plain style (no ですます).
- Name the main character or two and the single event or situation the segment turns on; leave out everything else, including detail the summaries dwell on.
- Write the Bengali caption first, based on the Bengali summary and using the other three only where they make the scene clearer, then make the Hindi, English and Japanese captions strict translations of it: the same content, in the same order, not independent captions.
- Spell proper nouns as the summary of each language spells them.
- Capitalize the English caption in title case: capitalize the first and last words and every significant word, and leave articles, coordinating conjunctions and short prepositions lowercase.
- Keep the four captions equal in what they say: do not give a character a title, epithet or explanatory word in one language that the other three leave out.
- End each caption without a full stop, and keep it on one line."""


def parse_summary_md(path: str) -> Dict[int, List[str]]:
    """chapter -> [segment 1 summary, segment 2 summary, ...] from a *-summary.md file.

    Returns {} if the file doesn't exist.
    """
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = CHAPTER_RE.split(text)[1:]
    return {
        int(chunks[i]): [p.strip() for p in re.split(r"\n\s*\n", chunks[i + 1].strip()) if p.strip()]
        for i in range(0, len(chunks), 2)
    }


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_messages(chapter: int, segment: int, summaries: Dict[str, str]) -> List[str]:
    return [
        f"[Chapter {chapter} segment {segment} summary, {name}]\n{summaries[code]}"
        for code, name in LANGS
    ] + [INSTRUCTIONS]


def load_existing(path: str) -> Dict[Tuple[int, int], dict]:
    existing = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    existing[(record["chapter"], record["segment"])] = record
    return existing


def get_summaries(
    chapters: Dict[str, Dict[int, List[str]]], chapter: int, segment: int
) -> Optional[Dict[str, str]]:
    """The four languages' summaries for one segment, or None if any is missing."""
    summaries = {}
    for code, _ in LANGS:
        paragraphs = chapters[code].get(chapter, [])
        if segment > len(paragraphs):
            return None
        summaries[code] = paragraphs[segment - 1]
    return summaries


def parse_segment_arg(value: str) -> Tuple[int, int]:
    m = re.fullmatch(r"(\d+):(\d+)", value.strip())
    if not m:
        raise argparse.ArgumentTypeError("expected chapter:segment, e.g. 1:2")
    return int(m.group(1)), int(m.group(2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate bn/hi/en/ja segment captions as a strict matched set",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-m", "--model", required=True,
                        help="LLM model to use (e.g. google:gemini-2.5-pro)")
    parser.add_argument("-i", "--input-dir", default="all",
                        help="Directory holding the <lang>-gemini-summary.md files")
    parser.add_argument("-o", "--output", default="all/captions.jsonl",
                        help="Output JSONL file")
    parser.add_argument("-s", "--segment", type=parse_segment_arg,
                        help="Debug: generate and print one chapter:segment (e.g. 1:2) "
                             "without touching any files")

    args = parser.parse_args()

    # Segments are captioned independently, so no turn is carried over into the next
    client = Client(model=args.model, show_params=args.segment is not None, keep_history=False)

    def caption(chapter: int, segment: int, summaries: Dict[str, str]) -> SegmentCaption:
        return client(build_messages(chapter, segment, summaries), schema=SegmentCaption).data

    chapters = {
        code: parse_summary_md(os.path.join(args.input_dir, f"{code}-gemini-summary.md"))
        for code, _ in LANGS
    }
    for code, _ in LANGS:
        if not chapters[code]:
            print(f"No summaries found for {code} in {args.input_dir}", file=sys.stderr)
            return 1

    if args.segment:
        chapter, segment = args.segment
        summaries = get_summaries(chapters, chapter, segment)
        if not summaries:
            print(f"Summaries not ready for {chapter}:{segment}", file=sys.stderr)
            return 1
        data = caption(chapter, segment, summaries)
        print()
        for code, _ in LANGS:
            print(f"{code}: {getattr(data, f'caption_{code}')}")
        return 0

    existing = load_existing(args.output)
    all_chapters = sorted(chapters[PIVOT])
    total_processed = 0

    print(f"{len(existing)} segments already done")

    for chapter in all_chapters:
        for segment in range(1, len(chapters[PIVOT][chapter]) + 1):
            if (chapter, segment) in existing:
                continue

            summaries = get_summaries(chapters, chapter, segment)
            if not summaries:
                print(f"{chapter:2d}:{segment} -> skipped (summaries not ready)")
                continue

            print(f"{chapter:2d}:{segment} -> ", end="", flush=True)
            data = caption(chapter, segment, summaries)

            record = {
                "chapter": chapter,
                "segment": segment,
                "captions": {
                    code: normalize(getattr(data, f"caption_{code}"))
                    for code, _ in LANGS
                },
            }
            with open(args.output, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()

            total_processed += 1
            print("done")

    print(f"\nProcessed {total_processed} segments")

    return 0


if __name__ == "__main__":
    exit(main())
