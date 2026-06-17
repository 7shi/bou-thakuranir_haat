#!/usr/bin/env python3
"""Tune RAG's retrieval depth (k) and cosine score threshold from the gold labels.

Standalone analysis, independent of report.py. Pure retrieval — no LLM, no
answer synthesis, no output file (like report.py, it just prints tables). It
re-embeds each question and scores it against the FULL scene index (all scenes,
not just top-5) so the full score distribution is available,
then answers two questions from PLAN.md:

  1. At what k does chapter recall saturate? Is the current k=5 tight or generous?
  2. Can a single global cosine threshold separate gold-chapter scenes from others?

The gold `chapters` field is the relevance label (chapter-level). Reuses
`load_index` / `embed_query` from answer_rag.py.

Three terminal tables:
  1. Chapter coverage@k by scope (all/single/cross).
  2. Cosine threshold sweep with the best global tau*.
  3. Per-question gold ranks and separation gap.

Note on "recall": report.py uses strict subset recall (1 iff gold ⊆ used). This
script instead reports partial coverage — the fraction of gold chapters with at
least one scene in the top-k — because the goal is the coverage-vs-k CURVE, not
a single pass/fail. The two notions agree only when coverage = 1.0.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from answer_rag import load_index, embed_query

ROOT = Path(__file__).resolve().parent.parent
QA_EVAL = Path(__file__).resolve().parent

LANGS = {"en": "English", "ja": "Japanese"}

# k columns shown in the coverage table (last entry = whole index, always 1.0).
K_COLS = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 82]
# Fine grid over which the best threshold (tau*) is located.
TAU_MIN, TAU_MAX, TAU_STEP = 0.20, 0.80, 0.02
# Coarser grid printed in the threshold table.
TAU_PRINT = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]


def load_questions(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def rank_all_scenes(normed: np.ndarray, q_vec: np.ndarray, scenes: list, gold: set[int]) -> dict:
    """Score the query against every scene and return a ranked record.

    `ranked` is the full list of scenes sorted by score descending, each with
    its rank, chapter, segment, and score. `gold_chapter_best_rank` maps each
    gold chapter to the rank of its highest-scoring scene; `gold_first_rank`
    is the minimum of those (the first scene the retriever would need to surface
    to cover any gold chapter at all).
    """
    scores = normed @ q_vec
    order = np.argsort(scores)[::-1]
    ranked = []
    gold_chapter_best: dict[int, int] = {}
    for rank, idx in enumerate(order, start=1):
        s = scenes[idx]
        chapter = s["chapter"]
        entry = {
            "rank": rank,
            "chapter": chapter,
            "segment": s["segment"],
            "score": float(scores[idx]),
        }
        ranked.append(entry)
        if chapter in gold and chapter not in gold_chapter_best:
            gold_chapter_best[chapter] = rank
    gold_first_rank = min(gold_chapter_best.values()) if gold_chapter_best else None
    return {
        "gold_chapter_best_rank": gold_chapter_best,
        "gold_first_rank": gold_first_rank,
        "ranked": ranked,
    }


def scopes_from_questions(questions: list[dict]) -> list[tuple[str, set[int] | None]]:
    """("all", None) plus one (typename, id-set) per gold type, in first-seen order."""
    by_type: dict[str, set[int]] = {}
    for qid, q in enumerate(questions, start=1):
        by_type.setdefault(q.get("type", "all"), set()).add(qid)
    scopes: list[tuple[str, set[int] | None]] = [("all", None)]
    scopes += [(t, ids) for t, ids in by_type.items()]
    return scopes


def coverage_at_k(rec: dict, k: int) -> float | None:
    """Fraction of gold chapters with at least one scene in the top-k (None if no gold)."""
    gold = set(rec["gold_chapters"])
    if not gold:
        return None
    top_chapters = {h["chapter"] for h in rec["ranked"][:k]}
    return len(top_chapters & gold) / len(gold)


def precision_at_k(rec: dict, k: int) -> float | None:
    """|gold ∩ top-k chapters| / |top-k chapters| (None if top-k empty)."""
    top = {h["chapter"] for h in rec["ranked"][:k]}
    if not top:
        return None
    gold = set(rec["gold_chapters"])
    return len(top & gold) / len(top)


def print_coverage_table(records: dict[int, dict], questions: list[dict]) -> None:
    scopes = scopes_from_questions(questions)
    ncols = len(K_COLS)
    header = f"{'scope':<8} {'n':>3} " + " ".join(f"k={k:<3}" for k in K_COLS)
    print("Table 1 — chapter coverage@k  (fraction of gold chapters with a scene in top-k)")
    print(header)
    print("-" * len(header))
    for scope_name, subset in scopes:
        recs = [r for qid, r in records.items() if subset is None or qid in subset]
        n = len(recs)
        row = f"{scope_name:<8} {n:>3} "
        for k in K_COLS:
            vals = [v for r in recs if (v := coverage_at_k(r, k)) is not None]
            mean = sum(vals) / len(vals) if vals else 0.0
            row += f"{mean:<5.2f} "
        print(row)
    print()
    # Tie-back to report.py: strict subset recall and precision at the current k=5.
    for scope_name, subset in scopes:
        recs = [r for qid, r in records.items() if subset is None or qid in subset]
        strict = sum(1 for r in recs if set(r["gold_chapters"]) <= {h["chapter"] for h in r["ranked"][:5]})
        cov = [v for r in recs if (v := coverage_at_k(r, 5)) is not None]
        prec = [v for r in recs if (v := precision_at_k(r, 5)) is not None]
        cov_mean = sum(cov) / len(cov) if cov else 0.0
        prec_mean = sum(prec) / len(prec) if prec else 0.0
        print(f"  k=5 [{scope_name:>5}]: strict-recall {strict}/{len(recs)} "
              f"(report.py notion), coverage {cov_mean:.3f}, precision {prec_mean:.3f}")
    print()


def print_threshold_table(records: dict[int, dict]) -> None:
    # Pool (score, is_gold) over every (question, scene) pair.
    pos: list[float] = []
    neg: list[float] = []
    for rec in records.values():
        gold = set(rec["gold_chapters"])
        for h in rec["ranked"]:
            (pos if h["chapter"] in gold else neg).append(h["score"])
    pos_arr = np.array(pos)
    neg_arr = np.array(neg)
    total_pos = len(pos_arr)
    total_neg = len(neg_arr)

    def prf(tau: float) -> tuple[float, float, float, int, int]:
        tp = int((pos_arr >= tau).sum())
        fp = int((neg_arr >= tau).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / total_pos if total_pos else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1, tp, fp

    print("Table 2 — cosine threshold sweep  (positive iff scene.chapter in gold)")
    print(f"  pool: {total_pos} positive, {total_neg} negative scene-pairs")
    print(f"{'tau':>5} {'precision':>9} {'recall':>7} {'F1':>5} {'tp':>5} {'fp':>5}")
    print("-" * 40)
    for tau in TAU_PRINT:
        p, r, f1, tp, fp = prf(tau)
        print(f"{tau:>5.2f} {p:>9.3f} {r:>7.3f} {f1:>5.2f} {tp:>5} {fp:>5}")

    taus = np.arange(TAU_MIN, TAU_MAX + 1e-9, TAU_STEP)
    best_tau, best_f1 = taus[0], -1.0
    for tau in taus:
        _, _, f1, _, _ = prf(float(tau))
        if f1 > best_f1:
            best_f1, best_tau = f1, float(tau)
    p, r, f1, tp, fp = prf(best_tau)
    print("-" * 40)
    print(f"best tau*={best_tau:.2f}  precision={p:.3f} recall={r:.3f} F1={f1:.2f} "
          f"(tp={tp}, fp={fp})")
    print()


def print_per_question_table(records: dict[int, dict]) -> None:
    print("Table 3 — per-question: first gold rank, best gold score, separation gap")
    print("  gap = (best gold-chapter score) − (best non-gold score ranked BELOW it)")
    print("  gap > 0  → a threshold could isolate the gold hit; gap < 0 → entangled.")
    print(f"{'qid':>3} {'type':<6} {'gold':<10} {'1stAu':>5} {'score':>6} {'gap':>7}   per-chapter best rank")
    print("-" * 78)
    for qid in sorted(records):
        rec = records[qid]
        ranked = rec["ranked"]
        gold = set(rec["gold_chapters"])
        first = rec["gold_first_rank"]
        if first is None:
            print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<10} "
                  f"{'-':>5} {'-':>6} {'-':>7}   {rec['gold_chapter_best_rank']}")
            continue
        best_gold_score = ranked[first - 1]["score"]
        # Best non-gold scene ranked strictly below the first gold hit.
        below_nongold = next((h["score"] for h in ranked[first:] if h["chapter"] not in gold), None)
        gap = best_gold_score - below_nongold if below_nongold is not None else None
        gap_s = f"{gap:>+7.3f}" if gap is not None else "     -"
        flag = " *" if (first is not None and first > 5) else ""
        print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<10} {first:>5} "
              f"{best_gold_score:>6.3f} {gap_s}   {rec['gold_chapter_best_rank']}{flag}")
    print("  (* = first gold hit outside current k=5 — a retrieval miss under the default setting)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/index paths)")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--index", default=None,
                        help="index safetensors (default: qa-eval/index-<lang>.safetensors)")
    args = parser.parse_args()

    lang = args.lang
    args.input = args.input or str(ROOT / f"questions-{lang}.jsonl")
    args.index = args.index or str(QA_EVAL / f"index-{lang}.safetensors")

    print(f"Loading index from {args.index}")
    normed, scenes = load_index(Path(args.index))
    print(f"Index: {normed.shape[0]} scenes, dim={normed.shape[1]}")

    questions = load_questions(Path(args.input))
    print(f"Questions: {len(questions)}")

    records: dict[int, dict] = {}
    total = len(questions)
    for qid, q in enumerate(questions, start=1):
        print(f"[{qid}/{total}] {q['question'][:70]}")
        q_vec = embed_query(q["question"], args.embed)
        rec = rank_all_scenes(normed, q_vec, scenes, set(q["chapters"]))
        rec = {
            "question_id": qid,
            "type": q.get("type", "all"),
            "gold_chapters": sorted(set(q["chapters"])),
            **rec,
        }
        records[qid] = rec

    print()
    print_coverage_table(records, questions)
    print_threshold_table(records)
    print_per_question_table(records)


if __name__ == "__main__":
    main()
