#!/usr/bin/env python3
"""Answer evaluation questions using vector RAG over the scene index.

For each question in questions-en.jsonl:
  1. Embed the question with the search-result query prompt.
  2. Retrieve top-k scenes by cosine similarity.
  3. Expand each hit ±N scenes within the same chapter and merge overlapping ranges.
  4. Build a labeled context block and ask the model to answer the question.

Output: results/rag-<model-slug>.jsonl, one record per question.
Resume-safe: skips question IDs already present in the output file.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from ollama import embed
from safetensors import safe_open

from llm7shi.compat import generate_with_schema

ROOT = Path(__file__).resolve().parent.parent


def load_index(index_path: Path):
    with safe_open(str(index_path), framework="numpy") as f:
        embeddings = f.get_tensor("embeddings").astype(np.float32)
        scenes = json.loads(f.metadata()["scenes"])
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.where(norms == 0, 1.0, norms)
    return normed, scenes


def embed_query(question: str, model: str) -> np.ndarray:
    prompt = f"task: search result | query: {question}"
    response = embed(model=model, input=prompt)
    vec = np.array(response["embeddings"][0], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def top_k_search(normed_embeddings: np.ndarray, query_vec: np.ndarray, k: int):
    scores = normed_embeddings @ query_vec
    idx = np.argsort(scores)[::-1][:k]
    return [(int(i), float(scores[i])) for i in idx]


def expand_and_merge(hits: list, scenes: list, N: int):
    """Expand each hit ±N within its chapter and merge overlapping ranges.

    Returns a sorted list of scene indices (into the scenes list).
    """
    # Group scene indices by chapter for boundary lookup
    chapter_indices: dict[int, list[int]] = {}
    for idx, scene in enumerate(scenes):
        chapter_indices.setdefault(scene["chapter"], []).append(idx)

    # Collect expanded ranges as (start, end) inclusive index pairs
    ranges: list[tuple[int, int]] = []
    for hit_idx, _ in hits:
        chapter = scenes[hit_idx]["chapter"]
        chapter_idx_list = chapter_indices[chapter]
        pos = chapter_idx_list.index(hit_idx)
        lo = chapter_idx_list[max(0, pos - N)]
        hi = chapter_idx_list[min(len(chapter_idx_list) - 1, pos + N)]
        ranges.append((lo, hi))

    # Merge overlapping ranges
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for lo, hi in ranges:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))

    result = []
    for lo, hi in merged:
        result.extend(range(lo, hi + 1))
    return result


def build_context(expanded_indices: list, scenes: list) -> str:
    parts = []
    for idx in expanded_indices:
        s = scenes[idx]
        parts.append(f"[Chapter {s['chapter']}, Scene {s['segment']} — {s['title']}]")
        parts.append(s["text"])
        parts.append("")
    return "\n".join(parts).strip()


def answer_question(question: str, context: str, model: str) -> str:
    prompt = (
        f"Answer the following question in English based ONLY on the context provided. "
        f"Do not use any outside knowledge. "
        f"Reply with the answer only — no preamble, no reasoning, no closing remarks.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}"
    )
    result = generate_with_schema([prompt], model=model, show_params=False)
    return result.text.strip()


def model_slug(model: str) -> str:
    return model.replace(":", "-").replace("/", "-").replace("@", "-")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b", help="llm7shi model string")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("-k", type=int, default=5, help="top-k scenes to retrieve")
    parser.add_argument("-N", type=int, default=1, help="context expansion window ±N")
    parser.add_argument(
        "-i", "--input",
        default=str(ROOT / "questions-en.jsonl"),
        help="questions JSONL",
    )
    parser.add_argument(
        "--index",
        default=str(ROOT / "qa-eval" / "index-en.safetensors"),
        help="index safetensors",
    )
    parser.add_argument("-o", "--output", default=None, help="output JSONL path")
    args = parser.parse_args()

    slug = model_slug(args.model)
    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / "results" / f"rag-{slug}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: collect already-done question IDs
    done_ids: set[int] = set()
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["question_id"])
    if done_ids:
        print(f"Resuming: {len(done_ids)} questions already done")

    # Load index
    print(f"Loading index from {args.index}")
    normed, scenes = load_index(Path(args.index))
    print(f"Index: {normed.shape[0]} scenes, dim={normed.shape[1]}")

    # Load questions
    questions = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    print(f"Questions: {len(questions)}")

    total = len(questions)
    with open(output_path, "a", encoding="utf-8") as out_f:
        for qid, q in enumerate(questions, start=1):
            if qid in done_ids:
                continue

            question_text = q["question"]
            print(f"\n{'='*60}")
            print(f"[{qid}/{total}] {question_text}")
            print('='*60)

            # Embed and search
            q_vec = embed_query(question_text, args.embed)
            hits = top_k_search(normed, q_vec, args.k)

            # Expand ±N and merge
            expanded = expand_and_merge(hits, scenes, args.N)
            context = build_context(expanded, scenes)

            # Get answer
            answer = answer_question(question_text, context, args.model)

            # Build hit metadata
            hit_records = {
                f"{scenes[i]['chapter']}:{scenes[i]['segment']}": score
                for i, score in hits
            }
            expanded_scenes = [
                f"{scenes[i]['chapter']}:{scenes[i]['segment']}"
                for i in expanded
            ]

            record = {
                "question_id": qid,
                "question": question_text,
                "hits": hit_records,
                "expanded_scenes": expanded_scenes,
                "answer": answer,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
