#!/usr/bin/env python3
"""Answer evaluation questions using hybrid retrieval (dense ∪ BM25 union).

Phase 2 QA for the Union approach proven in [HYBRID.md](HYBRID.md): the retrieval
analysis showed that fusing dense + BM25 into a single ranking (RRF/Borda/
CombSUM) underperforms dense alone at k=5, while taking the set-theoretic
**union** of the two retrievers' top-k chapter sets beats dense by +4 strict
recall at both k=5 (40/50) and k=10 (46/50), parameter-free. This script turns
that retrieval gain into an answer-accuracy measurement — does surfacing +4 gold
chapters actually improve the answer, or does the ~1.4× larger context cause
"lost in the middle" synthesis failures that offset it?

For each question in questions-en.jsonl:
  1. Embed the question (dense) and tokenize it (BM25).
  2. Retrieve dense top-k scenes and BM25 top-k scenes.
  3. **Union** the two hit sets (set-theoretic, deduped by scene).
  4. Expand each hit ±N scenes within its chapter and merge overlapping ranges
     (reusing `answer_vector.expand_and_merge`).
  5. Build a labeled context block and ask the model to answer (reusing
     `answer.answer_question` with the same preamble as Vector RAG).

Output: results-<lang>/hybrid<k>.jsonl (e.g. hybrid5.jsonl for the default k=5),
one record per question — `question_id`, `hits` (per-retriever top-k as
`{"dense": {...}, "bm25": {...}}`, kept separate because cosine and BM25 scores
are on incompatible scales), `expanded`, and `answer`. Resume-safe: skips
question IDs already present in the output file.

Pipeline: built into the default English pipeline via `make judge` (the
aggregate adds `judge-hybrid5/10.jsonl` only when `LANG=en`, so `make ja` is
unaffected); report.py auto-discovers `hybrid<k>.jsonl` into a `Hybrid k=<k>`
row beside the Vector variants. Run `make hybrid` (k=5) / `make hybrid K=10` for
the answer file, or `make hybrid-judge` for both depths plus judgements. The
retrieval coverage (40/50 @ k=5, 46/50 @ k=10) is the upper bound on Phase 2
accuracy; the gap to it is the synthesis cost of the ~1.4× larger context.

English only — BM25 tokenization is English-only (lowercase + `[a-z0-9]+` +
stopword removal, no morphology), so Japanese is deferred; passing `-l ja`
exits with an error, matching `hybrid.py`.

Tie-breaking: scene rankings use a stable sort (`sorted(range(n), ...,
reverse=True)`), matching `bm25.py` / `sweep_vector.py` / `hybrid.py` rather
than `answer_vector.top_k_search`'s `np.argsort()[::-1]` (non-stable). This is
load-bearing — the HYBRID.md strict-recall numbers (40/50, 46/50) were measured
under the stable tie-break, so the union hits must be selected the same way or
the +4 retrieval gain may not reproduce.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from ollama import embed

from answer import ROOT, LANGS, load_questions, answer_question, print_banner
from answer_vector import (
    load_index,
    embed_query,
    expand_and_merge,
    build_context,
    VECTOR_PREAMBLE,
)
from bm25 import BM25Index, tokenize, load_titles, load_scenes

DEFAULT_K = 5


def top_k_stable(scores, k: int):
    """Top-k scenes by score, ties broken in narrative (scene) order.

    Mirrors the ranking in ``bm25.rank_all_scenes`` / ``sweep_vector.py`` /
    ``hybrid.py`` (stable sort, reverse=True). ``answer_vector.top_k_search``
    uses ``np.argsort()[::-1]`` which is *not* stable; the HYBRID.md analysis
    (strict recall 40/50 @ k=5, 46/50 @ k=10) was measured under the stable
    tie-break, so the union hit set must be selected identically here.
    """
    order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
    return [(i, float(scores[i])) for i in order[:k]]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (BM25 is English-only; -l ja exits with an error)")
    parser.add_argument("-m", "--model", default="ollama:gemma4:31b-it-qat", help="llm7shi model string")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="top-k scenes to retrieve (per retriever)")
    parser.add_argument("-N", type=int, default=1, help="context expansion window ±N")
    parser.add_argument("-i", "--input", default=None, help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--index", default=None, help="index safetensors (default: qa-eval/index-<lang>.safetensors)")
    parser.add_argument("--scenes", default=None, help="scenes JSONL for BM25 (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-t", "--tsv", default=None, help="scene titles TSV (default: all/<lang>-gemini.tsv)")
    parser.add_argument("-o", "--output", default=None, help="output JSONL path (default: qa-eval/results-<lang>/hybrid<k>.jsonl)")
    args = parser.parse_args()

    lang = args.lang
    lang_name = LANGS[lang]
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.index = args.index or str(ROOT / "qa-eval" / f"index-{lang}.safetensors")
    args.scenes = args.scenes or str(ROOT / "all" / f"{lang}-gemini.jsonl")
    args.tsv = args.tsv or str(ROOT / "all" / f"{lang}-gemini.tsv")
    hybrid_name = f"hybrid{args.k}.jsonl"
    output_path = Path(args.output) if args.output else ROOT / "qa-eval" / f"results-{lang}" / hybrid_name
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

    # Dense side: embedding index (matches answer_vector.py / sweep_vector.py).
    print(f"Loading index from {args.index}")
    normed, dense_scenes = load_index(Path(args.index))
    print(f"Index: {normed.shape[0]} scenes, dim={normed.shape[1]}")

    # Sparse side: raw scene text (matches bm25.py).
    titles = load_titles(Path(args.tsv))
    bm25_scenes = load_scenes(Path(args.scenes), titles)
    print(f"Loaded {len(bm25_scenes)} scenes from {args.scenes}")

    # The two scene lists must be identical and in the same order, so that scene
    # index i refers to the same scene for the dense score array (normed row i)
    # and the BM25 score array (doc i). Same check as hybrid.py.
    assert len(dense_scenes) == len(bm25_scenes), (
        f"scene count mismatch: index={len(dense_scenes)} vs jsonl={len(bm25_scenes)}")
    for i, (d, b) in enumerate(zip(dense_scenes, bm25_scenes)):
        assert d["chapter"] == b["chapter"] and d["segment"] == b["segment"], (
            f"scene {i} mismatch: index={(d['chapter'], d['segment'])} "
            f"vs jsonl={(b['chapter'], b['segment'])}")
    scenes = dense_scenes  # common list, identical order

    # Build the BM25 index once (title + body document, matching bm25.py).
    docs = [tokenize(f"{s['title']} {s['text']}", lang=lang) for s in scenes]
    bm25 = BM25Index(docs)
    print(f"BM25 index: {bm25.n_docs} docs, avgdl={bm25.avgdl:.1f} tokens, vocab={len(bm25.idf)}")

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

            # Dense retrieval: cosine similarity against the embedding index.
            q_vec = embed_query(question_text, args.embed)
            dense_scores = normed @ q_vec
            dense_top = top_k_stable(dense_scores, args.k)

            # Sparse retrieval: BM25 on the literal scene text.
            q_tokens = tokenize(question_text, lang=lang)
            bm25_scores = bm25.score_query(q_tokens)
            bm25_top = top_k_stable(bm25_scores, args.k)

            # Union the two hit sets (deduped by scene index). expand_and_merge
            # ignores the score component of each (idx, score) pair, so 0.0 is
            # a placeholder — it ranks scenes only by position to expand.
            union_idx = sorted({i for i, _ in dense_top} | {i for i, _ in bm25_top})
            expanded = expand_and_merge([(i, 0.0) for i in union_idx], scenes, args.N)
            context = build_context(expanded, scenes)

            # Get answer (same preamble/context_prefix as Vector RAG so the only
            # difference from vector<k>.jsonl is the retrieved context itself).
            answer = answer_question(question_text, context, args.model, lang_name,
                                     preamble=VECTOR_PREAMBLE, context_prefix="Context:\n")

            # Build hit metadata. Scores are kept per-retriever because dense
            # (cosine, [-1,1]) and BM25 (unbounded) are on incompatible scales;
            # fusing them into one dict would be misleading. report.py reads
            # only `expanded` for chapter recall, so `hits` is informational.
            dense_hits = {
                f"{scenes[i]['chapter']}:{scenes[i]['segment']}": score
                for i, score in dense_top
            }
            bm25_hits = {
                f"{scenes[i]['chapter']}:{scenes[i]['segment']}": score
                for i, score in bm25_top
            }
            expanded_scenes = [
                f"{scenes[i]['chapter']}:{scenes[i]['segment']}"
                for i in expanded
            ]

            record = {
                "question_id": qid,
                "hits": {
                    "dense": dense_hits,
                    "bm25": bm25_hits,
                },
                "expanded": expanded_scenes,
                "answer": answer,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done → {output_path}")


if __name__ == "__main__":
    main()
