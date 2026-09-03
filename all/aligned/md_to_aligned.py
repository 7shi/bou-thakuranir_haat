#!/usr/bin/env python3
"""
Fold hand edits made to all/<lang>-gemini.md back into an aligned JSONL.

jsonl_to_md.py --mode translation is the forward direction: one blank-line-
separated paragraph per line of the aligned translation, chapters marked by
"## Chapter N", the whole document a straight rendering of the aligned
JSONL's response.translation fields with no other markup. This is exactly
that transform inverted - it does not touch structure, only the words within
each existing line, because the aligned JSONL's line count per segment is
load-bearing (align_lines.py's line-for-line pairing with the source, see
all/aligned/README.md's acceptance criterion). Adding, removing or merging a
paragraph in the Markdown is therefore an error, not a silent restructuring.

    uv run all/aligned/md_to_aligned.py all/en-gemini.md -a all/aligned/en-gemini-terra.jsonl

Rewrites the aligned JSONL named by -a in place (or -o instead). Follow with
pack_aligned.py pack to fold the change into the delta. See all/aligned/
README.md's "Correcting the published text" for the full workflow.
"""

import argparse
import re
import sys
from typing import Dict, List, Tuple

from align_lines import load_records, save_records

CHAPTER_RE = re.compile(r"^## Chapter (\d+)\s*$", re.MULTILINE)


def parse_chapters(md_text: str) -> Dict[int, List[str]]:
    """Chapter number -> its paragraphs, in document order.

    Mirrors jsonl_to_md.py's format_translation_text: paragraphs are
    separated by one blank line, and a paragraph is one translation line
    with its own leading/trailing whitespace stripped.
    """
    chapters: Dict[int, List[str]] = {}
    matches = list(CHAPTER_RE.finditer(md_text))
    for i, m in enumerate(matches):
        chapter = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body)]
        chapters[chapter] = [p for p in paragraphs if p]
    return chapters


def apply_edits(records: List[Dict], chapters: Dict[int, List[str]]) -> List[Dict]:
    by_chapter: Dict[int, List[Dict]] = {}
    for r in records:
        by_chapter.setdefault(r["chapter"], []).append(r)
    for recs in by_chapter.values():
        recs.sort(key=lambda r: r["segment"])

    if missing := sorted(by_chapter.keys() - chapters.keys()):
        raise ValueError(f"Chapters missing from the Markdown: {missing}")
    if extra := sorted(chapters.keys() - by_chapter.keys()):
        raise ValueError(f"Chapters in the Markdown but not the JSONL: {extra}")

    for chapter, recs in by_chapter.items():
        paragraphs = chapters[chapter]
        pos = 0
        for r in recs:
            lines = r["response"]["translation"].split("\n")
            n = len(lines)
            segment_paragraphs = paragraphs[pos:pos + n]
            if len(segment_paragraphs) != n:
                raise ValueError(
                    f"Chapter {chapter} ran out of paragraphs at segment "
                    f"{r['segment']} (expected {n} more, {len(paragraphs) - pos} left) "
                    "- a paragraph was added, removed or merged across a segment "
                    "boundary, which this script cannot place"
                )
            r["response"]["translation"] = "\n".join(segment_paragraphs)
            pos += n
        if pos != len(paragraphs):
            raise ValueError(
                f"Chapter {chapter} has {len(paragraphs) - pos} extra paragraph(s) "
                "after its last segment - a paragraph was added without removing "
                "another, which changes the line count align_lines.py relied on"
            )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fold edits to all/<lang>-gemini.md back into its aligned JSONL"
    )
    parser.add_argument("markdown", help="The hand-edited all/<lang>-gemini.md")
    parser.add_argument("-a", "--aligned", required=True,
                         help="Aligned JSONL to read the chapter/segment/line "
                              "structure from (e.g. all/aligned/en-gemini-terra.jsonl)")
    parser.add_argument("-o", "--output",
                         help="Output path (default: overwrite --aligned in place)")
    args = parser.parse_args()

    with open(args.markdown, "r", encoding="utf-8") as f:
        md_text = f.read()

    records = load_records(args.aligned)
    if not records:
        print(f"No records in {args.aligned}", file=sys.stderr)
        return 1

    chapters = parse_chapters(md_text)
    if not chapters:
        print(f"No '## Chapter N' headings found in {args.markdown}", file=sys.stderr)
        return 1

    try:
        records = apply_edits(records, chapters)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    output = args.output or args.aligned
    save_records(output, records)
    print(f"{args.markdown} -> {output} ({len(records)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
