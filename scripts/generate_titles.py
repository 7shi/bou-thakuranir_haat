import os
import json
import argparse
from typing import Optional
from llm7shi.compat import generate_with_schema


def load_segments_from_jsonl(translation_file: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Load the book title and per-scene segments from a translation JSONL.

    Each record carries its own ``chapter`` / ``segment`` numbers (real chapter
    numbers, 1-origin segments) and a ``response.translation`` field holding the
    scene text (paragraphs joined by newlines). The leading title record exposes
    ``response.translated_title`` instead of ``translation``; it is used for the
    book title and skipped as a scene.

    The translation JSONL is already segmented per scene, so the segment text is
    read directly from it without re-slicing the markdown by line numbers.
    """
    title = ""
    segments: list[tuple[int, int, str]] = []
    with open(translation_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            response = data.get('response', {})
            if 'translation' in response:
                text = response['translation'].strip()
                if text:
                    segments.append((data['chapter'], data['segment'], text))
            elif 'translated_title' in response:
                title = response['translated_title'].strip()
    return title, segments


def generate_scene_title(
    segment_text: str,
    model: str,
    show_params: bool,
    title_lang: str = "English",
) -> Optional[str]:
    prompt = f"""Read the following text segment and output a single concise {title_lang} title (5-10 words) that describes the main event or scene. Output the title only, with no explanation, commentary, or punctuation at the end.

{segment_text}"""
    # The model occasionally returns an empty title; retry up to 3 times
    # (4 attempts total), then give up rather than loop forever.
    max_retries = 3
    for attempt in range(max_retries + 1):
        response = generate_with_schema(
            [prompt],
            model=model,
            show_params=show_params,
        )
        if response and hasattr(response, 'text'):
            title = response.text.strip()
            if title:
                return title
        if attempt < max_retries:
            print(f"  generation failed — retrying ({attempt + 1}/{max_retries})")
        else:
            print(f"  generation still failed after {max_retries} retries — giving up")
    return None


def load_existing_titles(output_file: str) -> dict:
    existing = {}
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            next(f, None)  # skip header
            for line in f:
                if line.strip():
                    chapter, segment, title = line.rstrip('\n').split('\t', 2)
                    existing[(int(chapter), int(segment))] = title
    return existing


def ensure_header(output_file: str) -> None:
    if not os.path.exists(output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("chapter\tsegment\ttitle\n")


def main():
    parser = argparse.ArgumentParser(description='Generate scene titles for text segments',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('source', nargs='?', default='all/en-gemini.jsonl',
                        help='Translation JSONL file with per-segment text')
    parser.add_argument('-m', '--model', required=True,
                        help='LLM model string (e.g., ollama:qwen3:8b, google:gemini-2.5-flash)')
    parser.add_argument('-o', '--output',
                        help='Output TSV file (default: source path with .tsv extension)')
    parser.add_argument('--title-lang', default='English',
                        help='Language for the generated titles')
    parser.add_argument('--limit', type=int,
                        help='Limit number of chapters to process (for debugging)')
    args = parser.parse_args()

    output = args.output or os.path.splitext(args.source)[0] + '.tsv'
    ensure_header(output)
    print(f"Loading segments from {args.source}")
    title, segments = load_segments_from_jsonl(args.source)

    if args.limit:
        allowed = sorted({ch for ch, _, _ in segments})[:args.limit]
        allowed = set(allowed)
        segments = [s for s in segments if s[0] in allowed]
        print(f"Processing limited to {args.limit} chapters")

    existing = load_existing_titles(output)

    chapters = sorted({ch for ch, _, _ in segments})
    print(f"Title: {title}")
    print("Generating scene titles")
    print(f"Total chapters: {len(chapters)}, segments: {len(segments)}")
    print("=" * 60)

    current_chapter = None
    for chapter_num, segment_num, segment_text in segments:
        if chapter_num != current_chapter:
            current_chapter = chapter_num
            count = sum(1 for c, _, _ in segments if c == chapter_num)
            print(f"Chapter {chapter_num:2d}: {count} segments")

        key = (chapter_num, segment_num)
        if key in existing:
            print(f"  Segment {segment_num} → skipped")
            continue

        print(f"  Segment {segment_num} → generating...")
        print()
        generated_title = generate_scene_title(
            segment_text,
            args.model,
            bool(args.limit),
            args.title_lang,
        )

        if generated_title:
            with open(output, 'a', encoding='utf-8') as f:
                f.write(f"{chapter_num}\t{segment_num}\t{generated_title}\n")
            existing[key] = generated_title
            print(f"  Segment {segment_num} → {generated_title}")
        else:
            print(f"  Segment {segment_num} → failed")

    print(f"\nTitle generation completed!")
    print(f"Output saved to: {output}")
    return 0


if __name__ == "__main__":
    exit(main())
