#!/usr/bin/env python3
"""Embed each scene of the English translation and store the vectors in a
safetensors file (English RAG prototype).

The scene bodies come from ``all/en-gemini.jsonl`` (one record per scene,
``response.translation`` holding the text) and the scene titles from
``all/en-gemini.tsv``. Each scene is embedded with ollama using the document
prompt ``title: {title} | text: {text}``. The resulting ``[N, dim]`` float32
matrix is saved as a single ``embeddings`` tensor, with per-scene metadata
(chapter, segment, title, text) and the embedding model name stored as JSON in
the safetensors metadata (which only accepts str->str entries).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from ollama import embed
from safetensors import safe_open
from safetensors.numpy import save_file
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent

LANGS = {"en": "English", "ja": "Japanese"}


def load_titles(tsv_path):
    """Return {(chapter, segment): title} from a TSV with a header row."""
    titles = {}
    with open(tsv_path, encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            chapter, segment, title = line.split("\t", 2)
            titles[(int(chapter), int(segment))] = title
    return titles


def load_scenes(jsonl_path, titles):
    """Return an ordered list of scene dicts, skipping the title-only record."""
    scenes = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            chapter = rec["chapter"]
            segment = rec["segment"]
            text = rec.get("response", {}).get("translation")
            # Skip the chapter=0/segment=0 title record (no translation).
            if chapter == 0 or segment == 0 or not text:
                continue
            key = (chapter, segment)
            assert key in titles, f"no title for scene {key}"
            scenes.append(
                {
                    "chapter": chapter,
                    "segment": segment,
                    "title": titles[key],
                    "text": text,
                }
            )
    return scenes


def split_lines(scenes):
    """Return per-line entries from the segment list (line mode).

    Each segment's text is split on newlines; blank lines are dropped. The
    1-based index within the segment is recorded as ``line``.
    """
    lines = []
    for scene in scenes:
        for i, line in enumerate(
            (l for l in scene["text"].split("\n") if l.strip()), start=1
        ):
            lines.append(
                {
                    "chapter": scene["chapter"],
                    "segment": scene["segment"],
                    "line": i,
                    "text": line,
                }
            )
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-l", "--lang", default="en", choices=sorted(LANGS),
        help="evaluation language (selects default scenes/tsv/output paths)",
    )
    parser.add_argument(
        "-e", "--embed", default="embeddinggemma", help="embedding model"
    )
    parser.add_argument(
        "--line", action="store_true",
        help="embed one vector per line (default: index-line-<lang>.safetensors)",
    )
    parser.add_argument(
        "-i", "--input", default=None, help="scenes JSONL (default: all/<lang>-gemini.jsonl)"
    )
    parser.add_argument(
        "-t", "--tsv", default=None, help="scene titles TSV (default: all/<lang>-gemini.tsv)"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="output safetensors path (default: qa-eval/index[-line]-<lang>.safetensors)",
    )
    args = parser.parse_args()

    lang = args.lang
    args.input = args.input or str(ROOT / "all" / f"{lang}-gemini.jsonl")
    args.tsv = args.tsv or str(ROOT / "all" / f"{lang}-gemini.tsv")
    stem = "index-line" if args.line else "index"
    args.output = args.output or str(ROOT / "qa-eval" / f"{stem}-{lang}.safetensors")

    titles = load_titles(args.tsv)
    scenes = load_scenes(args.input, titles)
    print(f"Loaded {len(scenes)} scenes from {args.input}")

    if args.line:
        units = split_lines(scenes)
        print(f"Split into {len(units)} lines")
        prompts = [f'title: "none" | text: {u["text"]}' for u in units]
    else:
        units = scenes
        prompts = [f"title: {u['title']} | text: {u['text']}" for u in units]

    vectors = []
    for prompt in tqdm(prompts, desc="Embedding"):
        response = embed(model=args.embed, input=prompt)
        vectors.append(response["embeddings"][0])

    matrix = np.asarray(vectors, dtype=np.float32)
    print(f"Embeddings matrix: shape={matrix.shape} dtype={matrix.dtype}")

    metadata = {
        "embed_model": args.embed,
        "count": str(len(units)),
        "scenes": json.dumps(units, ensure_ascii=False),
    }
    # Line mode also stores the full segment list for segment-level context.
    if args.line:
        metadata["segments"] = json.dumps(scenes, ensure_ascii=False)
    save_file({"embeddings": matrix}, args.output, metadata=metadata)
    print(f"Saved {args.output}")

    # Read-back verification.
    with safe_open(args.output, framework="numpy") as f:
        loaded = f.get_tensor("embeddings")
        meta = f.metadata()
    restored = json.loads(meta["scenes"])

    print("--- verification ---")
    print(f"loaded shape: {loaded.shape}")
    print(f"embed_model: {meta['embed_model']}")
    print(f"metadata count: {meta['count']}")
    print(f"restored units: {len(restored)}")
    first = restored[0]
    extra = f" line={first['line']}" if args.line else ""
    print(
        f"first unit: chapter={first['chapter']} segment={first['segment']}{extra} "
        f"dim={loaded.shape[1]}"
    )
    if args.line:
        segs = json.loads(meta["segments"])
        print(f"restored segments: {len(segs)}")

    ok = (
        loaded.shape[0]
        == len(units)
        == int(meta["count"])
        == len(restored)
    )
    if not ok:
        print("VERIFICATION FAILED: count mismatch", file=sys.stderr)
        sys.exit(1)
    print("verification OK")


if __name__ == "__main__":
    main()
