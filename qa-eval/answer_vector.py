#!/usr/bin/env python3
"""Answer evaluation questions using vector RAG over the scene index.

For each question in questions-en.jsonl:
  1. Embed the question with the search-result query prompt.
  2. Retrieve top-k scenes by cosine similarity.
  3. Expand each hit ±N scenes within the same chapter and merge overlapping ranges.
  4. Build a labeled context block and ask the model to answer the question.

Output: results-<lang>/vector<k>.jsonl (e.g. vector5.jsonl for the default k=5),
one record per question — `question_id`, `hits` (top-k scenes as
`{"chapter:segment": score}`), `expanded` (all scenes in the context as
`"chapter:segment"` strings), and `answer`. Resume-safe: skips question IDs
already present in the output file. The k-aware filename lets a deeper run
(e.g. `-k 10`) coexist with the k=5 baseline; judge.py derives its stem from the
input, so `judge-vector10.jsonl` follows automatically.

`--line` switches to **line-level** retrieval: it loads
`index-line-<lang>.safetensors` (one vector per line, built by `build_index.py
--line`), ranks lines instead of scenes, then resolves each hit line back to its
containing segment before the same ±N expansion and answering. Output goes to
`vector-line<k>.jsonl`, with `hits` keyed `chapter:segment:line` to preserve line
provenance. Build/run with `make index LINE=1` / `make vector LINE=1`; plain
`make judge` grades any `vector-line<k>.jsonl` present.

`--hybrid` runs the **segment ∪ line** dense Union proven in
[VECTOR-HYBRID.md](VECTOR-HYBRID.md): it loads *both* indexes
(`index-<lang>.safetensors` and `index-line-<lang>.safetensors`), ranks each side
top-k, resolves the line hits to their segments, and takes the set-theoretic
**union** of the two segment sets before the identical ±N expansion and
answering. Output goes to `vector-hybrid<k>.jsonl`, with `hits` split per source
(`{"segment": {chapter:segment→score}, "line": {chapter:segment:line→score}}`).
This recovers gold chapters either granularity drops (+2/+3 strict recall en,
+5/+7 ja) — parameter-free and, unlike dense∪BM25, working in **both** languages
(no second model, same embeddinggemma cosine). Run with `make vector-hybrid` /
`make vector-hybrid K=10`; plain `make judge` grades any `vector-hybrid<k>.jsonl`
present. Mutually exclusive with `--line`.

The hybrid path ranks with a **stable** tie-break (`top_k_stable`), matching the
`hybrid-vector.py` measurement that produced the published numbers; the plain and
`--line` paths keep `top_k_search`'s `np.argsort` (non-stable) so their committed
results are unchanged. The distinction is load-bearing: strict recall flips 0↔1
when a score tie lands on the k-th slot, so the union must be selected the same
way it was measured.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from ollama import embed
from safetensors import safe_open

from answer import ROOT, LANGS, load_questions, answer_question, print_banner

DEFAULT_K = 5


def _normalize(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.where(norms == 0, 1.0, norms)


def load_index(index_path: Path):
    with safe_open(str(index_path), framework="numpy") as f:
        embeddings = f.get_tensor("embeddings").astype(np.float32)
        scenes = json.loads(f.metadata()["scenes"])
    return _normalize(embeddings), scenes


def load_line_index(index_path: Path):
    """Load a line-mode index: normalized line embeddings, the per-line entries
    (each with chapter/segment/line/text), and the full segment list used for
    segment-level context."""
    with safe_open(str(index_path), framework="numpy") as f:
        embeddings = f.get_tensor("embeddings").astype(np.float32)
        meta = f.metadata()
        lines = json.loads(meta["scenes"])
        segments = json.loads(meta["segments"])
    return _normalize(embeddings), lines, segments


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


def top_k_stable(scores: np.ndarray, k: int):
    """Top-k indices by score, ties broken in narrative (index) order.

    Mirrors the ranking in ``hybrid-vector.py`` / ``bm25.py`` / ``sweep_vector.py``
    / ``answer_hybrid.top_k_stable`` (stable sort, reverse=True). Used only by the
    ``--hybrid`` union path: the VECTOR-HYBRID.md strict-recall numbers were
    measured under this stable tie-break, so the union hit set must be selected
    identically. ``top_k_search`` (``np.argsort``) is *not* stable and is kept for
    the plain / ``--line`` paths to leave their committed results untouched.
    """
    order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
    return [(i, float(scores[i])) for i in order[:k]]


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


VECTOR_PREAMBLE = (
    "Answer the following question in {lang_name} based ONLY on the context provided. "
    "Do not use any outside knowledge. "
    "Reply with the answer only — no preamble, no reasoning, no closing remarks."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/index/output paths and answer language)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="top-k units to retrieve")
    parser.add_argument("-N", type=int, default=1, help="context expansion window ±N segments")
    parser.add_argument("--line", action="store_true",
                        help="retrieve at the line level (uses index-line-<lang>.safetensors; "
                             "hits resolve to segments for context)")
    parser.add_argument("--hybrid", action="store_true",
                        help="segment ∪ line dense Union: rank both indexes top-k, resolve line "
                             "hits to segments, union the segment sets (both languages; see "
                             "VECTOR-HYBRID.md). Mutually exclusive with --line.")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--index", default=None, help="segment index safetensors (default: qa-eval/index[-line]-<lang>.safetensors; in --hybrid this is the segment side)")
    parser.add_argument("--line-index", default=None, help="line index safetensors for --hybrid (default: qa-eval/index-line-<lang>.safetensors)")
    parser.add_argument("-o", "--output", default=None, help="output JSONL path (default: qa-eval/results-<lang>/vector[-line|-hybrid]<k>.jsonl)")
    args = parser.parse_args()

    if args.hybrid and args.line:
        raise SystemExit("answer_vector.py: --hybrid and --line are mutually exclusive "
                         "(--hybrid already unions segment + line retrieval).")

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    if args.hybrid:
        # Segment side from --index, line side from --line-index; both always loaded.
        args.index = args.index or str(ROOT / "qa-eval" / f"index-{lang}.safetensors")
        args.line_index = args.line_index or str(ROOT / "qa-eval" / f"index-line-{lang}.safetensors")
        vector_name = f"vector-hybrid{args.k}.jsonl"
    else:
        index_stem = "index-line" if args.line else "index"
        args.index = args.index or str(ROOT / "qa-eval" / f"{index_stem}-{lang}.safetensors")
        vector_name = f"vector-line{args.k}.jsonl" if args.line else f"vector{args.k}.jsonl"
    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / vector_name
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

    # Load index. In line mode the embeddings are per-line, while `scenes` (the
    # context units) is the full segment list; a (chapter, segment) map lets us
    # resolve each line hit back to its segment.
    print(f"Loading index from {args.index}")
    seg_pos: dict[tuple[int, int], int] = {}
    normed_line = None  # only set in hybrid mode (the line-side search matrix)
    if args.hybrid:
        # Load BOTH indexes. The segment list is the context unit on both sides;
        # `lines` is the per-line index used only to rank the line side.
        normed, scenes = load_index(Path(args.index))
        print(f"Index: {normed.shape[0]} segments, dim={normed.shape[1]}")
        normed_line, lines, line_segments = load_line_index(Path(args.line_index))
        print(f"Line index: {normed_line.shape[0]} lines, {len(line_segments)} segments, "
              f"dim={normed_line.shape[1]} (from {args.line_index})")
        # The two segment lists must be identical and in the same order so a
        # segment index means the same thing on both sides (same guard as
        # hybrid-vector.py / answer_hybrid.py).
        assert len(scenes) == len(line_segments), (
            f"segment count mismatch: index={len(scenes)} vs line-index={len(line_segments)}")
        for i, (a, b) in enumerate(zip(scenes, line_segments)):
            assert a["chapter"] == b["chapter"] and a["segment"] == b["segment"], (
                f"segment {i} mismatch: index={(a['chapter'], a['segment'])} "
                f"vs line-index={(b['chapter'], b['segment'])}")
        seg_pos = {(s["chapter"], s["segment"]): i for i, s in enumerate(scenes)}
    elif args.line:
        normed, lines, scenes = load_line_index(Path(args.index))
        seg_pos = {(s["chapter"], s["segment"]): i for i, s in enumerate(scenes)}
        print(f"Index: {normed.shape[0]} lines, {len(scenes)} segments, dim={normed.shape[1]}")
    else:
        normed, scenes = load_index(Path(args.index))
        lines = scenes
        print(f"Index: {normed.shape[0]} scenes, dim={normed.shape[1]}")

    # Load questions
    questions = load_questions(Path(args.input))
    print(f"Questions: {len(questions)}")

    total = len(questions)
    with open(output_path, "a", encoding="utf-8") as out_f:
        for qid, q in enumerate(questions, start=1):
            if qid in done_ids:
                continue

            question_text = q["question"]
            print_banner(f"[{qid}/{total}] {question_text}")

            # Embed once; reuse the query vector on both sides in hybrid mode.
            q_vec = embed_query(question_text, args.embed)

            if args.hybrid:
                # Segment ∪ line dense Union, stable tie-break on both sides so the
                # union reproduces the VECTOR-HYBRID.md numbers (see top_k_stable).
                seg_top = top_k_stable(normed @ q_vec, args.k)
                line_top = top_k_stable(normed_line @ q_vec, args.k)
                # Resolve each line hit to its segment, keeping each segment once.
                line_seg: list[tuple[int, float]] = []
                seen_line: set[int] = set()
                for li, score in line_top:
                    seg_idx = seg_pos[(lines[li]["chapter"], lines[li]["segment"])]
                    if seg_idx not in seen_line:
                        seen_line.add(seg_idx)
                        line_seg.append((seg_idx, score))
                # Union the two segment-index sets; expand_and_merge ignores the
                # score component, so 0.0 is a position-only placeholder.
                union_idx = sorted({i for i, _ in seg_top} | {i for i, _ in line_seg})
                seg_hits = [(i, 0.0) for i in union_idx]
            elif args.line:
                hits = top_k_search(normed, q_vec, args.k)
                # Resolve each line hit to its segment, keeping each segment once
                # at its best (first/highest) score, then expand at segment level.
                seg_hits = []
                seen: set[int] = set()
                for li, score in hits:
                    seg_idx = seg_pos[(lines[li]["chapter"], lines[li]["segment"])]
                    if seg_idx not in seen:
                        seen.add(seg_idx)
                        seg_hits.append((seg_idx, score))
            else:
                hits = top_k_search(normed, q_vec, args.k)
                seg_hits = hits

            # Expand ±N segments and merge
            expanded = expand_and_merge(seg_hits, scenes, args.N)
            context = build_context(expanded, scenes)

            # Get answer
            answer = answer_question(question_text, context, args.model, lang_name,
                                     preamble=VECTOR_PREAMBLE, context_prefix="Context:\n")

            # Build hit metadata: per-source dicts in hybrid mode, line-level in
            # line mode, scene-level otherwise.
            if args.hybrid:
                # Kept per-source (like answer_hybrid). Both are embeddinggemma
                # cosines so the scales are comparable, but splitting preserves
                # which retriever surfaced each hit. report.py reads only
                # `expanded`, so `hits` is informational.
                hit_records = {
                    "segment": {
                        f"{scenes[i]['chapter']}:{scenes[i]['segment']}": score
                        for i, score in seg_top
                    },
                    "line": {
                        f"{lines[i]['chapter']}:{lines[i]['segment']}:{lines[i]['line']}": score
                        for i, score in line_top
                    },
                }
            elif args.line:
                hit_records = {
                    f"{lines[i]['chapter']}:{lines[i]['segment']}:{lines[i]['line']}": score
                    for i, score in hits
                }
            else:
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
                "hits": hit_records,
                "expanded": expanded_scenes,
                "answer": answer,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
