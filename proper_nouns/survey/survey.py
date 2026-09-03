#!/usr/bin/env python3
"""
Survey the proper nouns that actually appear in one language's translation.

Unlike extract.py, this never looks at the source text or the glossary: it
reads a target-language translation on its own terms and asks the model which
proper nouns appear on each line, exactly as spelled there. The result is a
surface-form census that can be compared against proper_nouns/extract/all.tsv,
or against itself to find spelling that drifts within the same translation (the
Bibha/Vibha and Udayaditya/Udayditya kind of finding, made by hand before this
script existed - see all/aligned/README.md).
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from llm7shi.compat import generate_with_schema
from llm7shi import create_json_descriptions_prompt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.append(ROOT)
from scripts.utils import load_chapter_blocks


class LineNouns(BaseModel):
    line: int = Field(description="Line number, matching the input numbering")
    proper_nouns: List[str] = Field(
        description="Proper nouns appearing verbatim in this line - personal names, "
                    "place names, and titles or forms of address used as a name "
                    "(e.g. 'Grand-uncle', 'Maharaj'). Reproduced exactly as spelled "
                    "on that line. Empty if the line has none."
    )


class ProperNounSurvey(BaseModel):
    lines: List[LineNouns] = Field(
        description="One entry per input line, covering every line in order, "
                    "including lines whose proper_nouns list is empty"
    )


# No source language and no glossary are sent - the point is what this
# translation actually says, read on its own, not what it was supposed to say.
INSTRUCTIONS = """The text above is {lang} prose, numbered one line per line.

Read it purely as {lang} text - do not assume or infer a source language, and do not translate, normalize or correct anything. For every line, list every proper noun that appears in it: personal names, place names, and titles or forms of address used as a name. Reproduce each one exactly as it is spelled on that line.

Cover every line from 1 to {count}, in order, even when a line has no proper noun - give it an empty list."""


def number_lines(text: str) -> str:
    return "\n".join(f"{i} {line}" for i, line in enumerate(text.split("\n"), 1))


def survey_segment(text: str, lang: str, model: str, show_params: bool) -> Optional[Dict]:
    line_count = len(text.split("\n"))
    prompt = INSTRUCTIONS.format(lang=lang, count=line_count)
    json_descriptions = create_json_descriptions_prompt(ProperNounSurvey)
    for attempt in range(5, 0, -1):
        response = generate_with_schema(
            [number_lines(text), prompt, json_descriptions],
            schema=ProperNounSurvey,
            model=model,
            show_params=show_params,
        )
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            print(f"  Error decoding JSON: {e}")
        if attempt > 1:
            print("  Retrying...")
    return None


def default_output(input_path: str) -> str:
    # "hi-gemini.jsonl" -> "hi", "bn.md" -> "bn", matching the all/*-gemini.jsonl
    # and all/bn.md naming conventions.
    stem = os.path.splitext(os.path.basename(input_path))[0]
    lang = stem.split("-")[0]
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{lang}.jsonl")


def load_targets(path: str, segmentation: str, lang: Optional[str]) -> List[Dict]:
    """Build a uniform (chapter, segment, text, lang) list from either input kind.

    A translation JSONL already has this structure per record. A source
    markdown file (e.g. all/bn.md) has none of it - translate_segments.py's own
    segmentation is reused via load_chapter_blocks so chapter/segment numbers
    line up with the translation JSONLs built from the same file.
    """
    if path.endswith(".md"):
        chapters = load_chapter_blocks(segmentation, path)["chapters"]
        return [
            {"chapter": c, "segment": s, "text": text, "lang": lang or "Bengali"}
            for c, segments in enumerate(chapters, 1)
            for s, text in enumerate(segments, 1)
        ]

    records = load_records(path)
    # Chapter 0 is the title record; it has no per-line translation to survey.
    return [
        {
            "chapter": r["chapter"],
            "segment": r["segment"],
            "text": r["response"]["translation"],
            "lang": lang or r["target_lang"],
        }
        for r in records
        if r["chapter"] > 0
    ]


def load_records(path: str) -> List[Dict]:
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        pass
    return records


def save_records(path: str, records: List[Dict]) -> None:
    # The whole file is rewritten rather than appended to, because -s has to be
    # able to replace a record in place.
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_segment_arg(value: str) -> List[Tuple[int, int]]:
    segments = []
    for item in value.split(","):
        m = re.fullmatch(r"(\d+):(\d+)", item.strip())
        if not m:
            raise argparse.ArgumentTypeError(
                "expected chapter:segment or a comma-separated list, e.g. 37:1 or 11:1,11:3"
            )
        segments.append((int(m.group(1)), int(m.group(2))))
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Survey the proper nouns actually used in a translation, line by line"
    )
    parser.add_argument("translations",
                        help="Translation JSONL (e.g. all/hi-gemini.jsonl) or a source "
                             "markdown file (e.g. all/bn.md) to survey directly")
    parser.add_argument("-m", "--model", required=True,
                        help="LLM model to use (e.g. openai:gpt-5.6-terra)")
    parser.add_argument("-o", "--output",
                        help="Output JSONL (default: survey/<lang>.jsonl, <lang> taken "
                             "from the input filename)")
    parser.add_argument("-l", "--lang",
                        help="Language name to tell the model (default: the JSONL's "
                             "target_lang, or 'Bengali' for a markdown input)")
    parser.add_argument("-s", "--segment", type=parse_segment_arg,
                        help="Process only these chapter:segment references, comma separated "
                             "(e.g. 37:1 or 11:1,11:3), overwriting any existing records")
    parser.add_argument("--segmentation", default=os.path.join(ROOT, "segmentations.jsonl"),
                        help="Segmentation JSONL file, only used for a markdown input "
                             "(default: segmentations.jsonl, relative to the repo root)")
    args = parser.parse_args()
    output = args.output or default_output(args.translations)

    targets = load_targets(args.translations, args.segmentation, args.lang)
    if args.segment:
        wanted = set(args.segment)
        targets = [t for t in targets if (t["chapter"], t["segment"]) in wanted]
        if missing := wanted - {(t["chapter"], t["segment"]) for t in targets}:
            for chapter, segment in sorted(missing):
                print(f"No such segment: {chapter}:{segment}", file=sys.stderr)
            return 1

    existing = load_records(output)
    index = {(r["chapter"], r["segment"]): i for i, r in enumerate(existing)}

    processed = 0
    for target in targets:
        chapter, segment = target["chapter"], target["segment"]
        key = (chapter, segment)

        if key in index and not args.segment:
            print(f"Chapter {chapter:2d} segment {segment} -> skipped (already surveyed)")
            continue

        text = target["text"]
        lang = target["lang"]
        line_count = len(text.split("\n"))
        print(f"\nChapter {chapter:2d} segment {segment} -> surveying ({line_count} lines)")

        result = survey_segment(text, lang, args.model, show_params=len(args.segment or []) == 1)
        if result is None:
            print("  failed")
            continue

        proper_nouns = {str(entry["line"]): entry["proper_nouns"] for entry in result["lines"]}
        if len(proper_nouns) != line_count:
            print(f"  warning: {len(proper_nouns)} lines returned, expected {line_count}")

        surveyed = {
            "chapter": chapter,
            "segment": segment,
            "target_lang": lang,
            "model": args.model,
            "proper_nouns": proper_nouns,
        }
        if key in index:
            existing[index[key]] = surveyed
        else:
            index[key] = len(existing)
            existing.append(surveyed)
        save_records(output, existing)
        processed += 1

    print(f"\nProcessed {processed} segments -> {output}")
    return 0


if __name__ == "__main__":
    exit(main())
