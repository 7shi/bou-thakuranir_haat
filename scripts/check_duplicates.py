#!/usr/bin/env python3
"""Detect semantically duplicate questions in a questions JSONL file.

Judgment phase — every question acts as a seed, independent of grouping:
  1. Embed all questions with the embedding model (no prefix — pure similarity).
  2. Sort all other questions by cosine similarity (descending).
  3. Judge each candidate from the top; a cached judgment (forward or reverse) is
     reused, otherwise the LLM is called. Stop after STOP consecutive "different".

Aggregation phase:
  4. Union-find over all "same" judgments builds the final duplicate groups.
  5. Report the groups and the effective unique question count.

Because every question is a seed and judgments are cached symmetrically, a question
missed by its natural seed is still caught when a sibling acts as seed; the final
union-find merges any overlapping chains into one group.

Cache format: TSV with header q1<TAB>q2<TAB>same (1-based, y/n).
Overwritten after each seed's judgments complete.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from ollama import embed

from llm7shi.compat import generate_with_schema

ROOT = Path(__file__).resolve().parent.parent


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        px, py = self.find(x), self.find(y)
        if px != py:
            self.parent[py] = px

    def groups(self, n: int) -> list[list[int]]:
        comps: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            comps[self.find(i)].append(i)
        return sorted([sorted(v) for v in comps.values() if len(v) > 1])


def embed_text(text: str, model: str) -> np.ndarray:
    response = embed(model=model, input=text)
    vec = np.array(response["embeddings"][0], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def judge_duplicate(q1: str, q2: str, model: str) -> str:
    prompt = (
        "Do these two questions ask about the same event and expect the same answer?\n"
        "Reply with exactly one word: same or different.\n\n"
        f"Question 1: {q1}\n"
        f"Question 2: {q2}"
    )
    max_retries = 3
    for attempt in range(max_retries + 1):
        result = generate_with_schema([prompt], model=model, include_thoughts=False, file=None, show_params=False)
        verdict = result.text.strip().lower()
        if verdict in ("same", "different"):
            return verdict
        if attempt < max_retries:
            print(f"  invalid verdict {verdict!r} — retrying ({attempt + 1}/{max_retries})")
        else:
            raise RuntimeError(f"invalid verdict after {max_retries} retries: {verdict!r}")


def write_tsv(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("q1\tq2\tsame\n")
        for r in records:
            f.write(f"{r['q1']}\t{r['q2']}\t{'y' if r['same'] else 'n'}\n")


def load_tsv(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8", newline="") as f:
        next(f)
        for line in f:
            if line.strip():
                q1, q2, same = line.rstrip("\n").split("\t")
                records.append({"q1": int(q1), "q2": int(q2), "same": same == "y"})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=["en", "ja"],
                        help="evaluation language (selects default questions file)")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("--stop", type=int, default=5, help="consecutive ungrouped misses before stopping")
    parser.add_argument("-c", "--cache", default=None,
                        help="cache TSV path (default: <input-stem>-cache.tsv next to input)")
    args = parser.parse_args()

    args.input = args.input or str(ROOT / f"questions-{args.lang}.jsonl")
    input_path = Path(args.input)
    cache_path = Path(args.cache) if args.cache else input_path.with_name(input_path.stem + "-cache.tsv")

    questions = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line)["question"])
    N = len(questions)
    print(f"Loaded {N} questions from {input_path}")

    records: list[dict] = []
    if cache_path.exists():
        records = load_tsv(cache_path)
        print(f"Cache: {len(records)} rows loaded from {cache_path}")

    # pair_cache[(q1_0, q2_0)] = is_same — symmetric lookups (forward or reverse)
    pair_cache: dict[tuple[int, int], bool] = {(r["q1"] - 1, r["q2"] - 1): r["same"] for r in records}

    # Seeds already fully processed
    done_seeds: set[int] = {r["q1"] - 1 for r in records}

    if done_seeds:
        print(f"Resumed: {len(done_seeds)} seeds done")

    print(f"Embedding {N} questions...")
    vecs = np.stack([embed_text(q, args.embed) for q in questions])
    sims = vecs @ vecs.T

    # --- Judgment phase: every question is a seed, independent of grouping ---
    for qid in range(N):
        if qid in done_seeds:
            continue

        order = np.argsort(sims[qid])[::-1]
        candidates = [(int(i), float(sims[qid][i])) for i in order if i != qid]

        new_recs: list[dict] = []
        consecutive_misses = 0
        header_printed = False

        for cand_qid, score in candidates:
            if (qid, cand_qid) in pair_cache:
                is_same = pair_cache[(qid, cand_qid)]
                cached_tag = " (cached)"
            elif (cand_qid, qid) in pair_cache:
                is_same = pair_cache[(cand_qid, qid)]
                cached_tag = " (reverse)"
            else:
                if not header_printed:
                    print(f"\n[Q{qid + 1}] {questions[qid][:80]}")
                    header_printed = True
                verdict = judge_duplicate(questions[qid], questions[cand_qid], args.model)
                is_same = verdict == "same"
                new_recs.append({"q1": qid + 1, "q2": cand_qid + 1, "same": is_same})
                pair_cache[(qid, cand_qid)] = is_same
                cached_tag = ""

            if not header_printed:
                print(f"\n[Q{qid + 1}] {questions[qid][:80]}")
                header_printed = True

            if is_same:
                print(f"  → Q{cand_qid + 1} ({score:.3f}) same{cached_tag}")
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                if consecutive_misses >= args.stop:
                    print(f"  → Q{cand_qid + 1} ({score:.3f}) different{cached_tag}  [stop: {args.stop} consecutive]")
                    break
                print(f"  → Q{cand_qid + 1} ({score:.3f}) different{cached_tag}")

        records.extend(new_recs)
        done_seeds.add(qid)
        write_tsv(cache_path, records)

    # --- Aggregation phase: union-find over all "same" judgments ---
    uf = UnionFind(N)
    for r in records:
        if r["same"]:
            uf.union(r["q1"] - 1, r["q2"] - 1)
    final_groups = uf.groups(N)

    print(f"\n{'='*60}")
    if not final_groups:
        print("No duplicate groups found.")
        print(f"Total: {N}  Unique: {N}")
        return

    for i, group in enumerate(final_groups, start=1):
        ids = ", ".join(f"Q{q + 1}" for q in group)
        print(f"\nGroup {i}: {ids}")
        for j, q in enumerate(group, start=1):
            print(f"  {j}. Q{q + 1}: {questions[q]}")

    duplicate_count = sum(len(g) - 1 for g in final_groups)
    unique_count = N - duplicate_count
    print(f"\n{len(final_groups)} group(s) found.")
    print(f"Total: {N}  Duplicates removed: {duplicate_count}  Unique: {unique_count}")


if __name__ == "__main__":
    main()
