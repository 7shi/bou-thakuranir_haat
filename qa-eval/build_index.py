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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-e", "--embed", default="embeddinggemma", help="embedding model"
    )
    parser.add_argument(
        "-i",
        "--input",
        default=str(ROOT / "all" / "en-gemini.jsonl"),
        help="scenes JSONL",
    )
    parser.add_argument(
        "-t",
        "--tsv",
        default=str(ROOT / "all" / "en-gemini.tsv"),
        help="scene titles TSV",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT / "qa-eval" / "index-en.safetensors"),
        help="output safetensors path",
    )
    args = parser.parse_args()

    titles = load_titles(args.tsv)
    scenes = load_scenes(args.input, titles)
    print(f"Loaded {len(scenes)} scenes from {args.input}")

    vectors = []
    for scene in tqdm(scenes, desc="Embedding"):
        prompt = f"title: {scene['title']} | text: {scene['text']}"
        response = embed(model=args.embed, input=prompt)
        vectors.append(response["embeddings"][0])

    matrix = np.asarray(vectors, dtype=np.float32)
    print(f"Embeddings matrix: shape={matrix.shape} dtype={matrix.dtype}")

    metadata = {
        "embed_model": args.embed,
        "count": str(len(scenes)),
        "scenes": json.dumps(scenes, ensure_ascii=False),
    }
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
    print(f"restored scenes: {len(restored)}")
    first = restored[0]
    print(
        f"first scene: chapter={first['chapter']} segment={first['segment']} "
        f"dim={loaded.shape[1]}"
    )
    print(f"  title: {first['title']}")

    ok = (
        loaded.shape[0]
        == len(scenes)
        == int(meta["count"])
        == len(restored)
    )
    if not ok:
        print("VERIFICATION FAILED: count mismatch", file=sys.stderr)
        sys.exit(1)
    print("verification OK")


if __name__ == "__main__":
    main()
