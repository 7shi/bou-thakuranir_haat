#!/usr/bin/env python3
"""Segment∪line dense gold-coverage analysis (measurement only, no LLM).

Companion to hybrid.py, which measured the dense∪BM25 hybrid. Here the two
retrievers are both dense and share the *same* embeddinggemma cosine:

- **Segment** — top-k over the segment index (index-<lang>.safetensors), the
  current Vector retriever.
- **Line** — top-k over the line index (index-line-<lang>.safetensors), the
  Vector-line retriever. A line maps directly to its chapter, so chapter-level
  coverage needs no line→segment resolution.

Two ways to combine them are measured against each retriever alone:

- **Union (approach B)** — the per-k set-theoretic oracle: a gold chapter is
  covered iff it is in the segment top-k OR the line top-k. Parameter-free and
  scale-immune; this is the retrieval *upper bound* PLAN.md cites
  (en 38/45, ja 41/43).
- **Mix (approach A)** — pool every segment unit and every line unit into one
  ranking and take the global top-k. Line cosines run systematically ~+0.04
  higher (see the score-scale diagnostic below), so a per-source normalization
  is swept (raw / z-score / min-max) to expose and correct that bias.

Like hybrid.py / sweep_vector.py this is print-only: no answer synthesis, no
output file. The gold label is chapter-level (q["chapters"]); every metric is
chapter coverage. Supports both en and ja — unlike hybrid.py there is no BM25,
hence no English-only restriction.

The coverage helpers (bm25.coverage_at_k / precision_at_k / scopes_from_questions)
read only rec["ranked"][:k] chapters and rec["gold_chapters"], so every
retriever — segment, line, and mix — is graded on identical axes.
"""

import argparse
from pathlib import Path

import numpy as np

from answer import ROOT, LANGS, load_questions
from answer_vector import load_index, load_line_index, embed_query
import sweep_vector
import hybrid
from bm25 import scopes_from_questions, coverage_at_k, precision_at_k

QA_EVAL = Path(__file__).resolve().parent

# k columns shown in the coverage table — identical to hybrid.py / sweep_vector.py
# so the curves read side by side. (Final 82 = whole segment index; for the Line
# row that depth is < the line count, so its k=82 is a curve point, not 1.0.)
K_COLS = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 82]

# Methods that produce a single ranking (Union is a per-k oracle, handled apart).
RANK_METHODS = ["Segment", "Line", "Mix"]

# approach A normalization variants swept in Table 3.
NORMS = ["raw", "z", "minmax"]


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def rank_all_lines(normed_line: np.ndarray, q_vec: np.ndarray,
                   lines: list[dict], gold: set[int]) -> dict:
    """Rank every line by cosine — the line analog of sweep_vector.rank_all_scenes.

    Same record shape; each ``ranked`` entry carries ``chapter`` (+ segment, line,
    score), so coverage_at_k / precision_at_k apply unchanged. Note the unit
    differs from the segment ranking: line top-k counts k **lines** (chapters may
    repeat), vs k **segments** — the fairness caveat in PLAN.md (compare Seg+Line
    k=5 against Segment k=10 for a like-for-like segment budget).
    """
    scores = normed_line @ q_vec
    order = np.argsort(scores)[::-1]
    ranked = []
    gold_best: dict[int, int] = {}
    for rank, idx in enumerate(order, start=1):
        ln = lines[idx]
        ch = ln["chapter"]
        ranked.append({
            "rank": rank,
            "chapter": ch,
            "segment": ln["segment"],
            "line": ln["line"],
            "score": float(scores[idx]),
        })
        if ch in gold and ch not in gold_best:
            gold_best[ch] = rank
    return {
        "ranked": ranked,
        "gold_chapter_best_rank": gold_best,
        "gold_first_rank": min(gold_best.values()) if gold_best else None,
    }


def _normalize(vals: list[float], norm: str) -> list[float]:
    """Per-source score normalization for approach A."""
    if norm == "raw":
        return list(vals)
    if norm == "minmax":
        return hybrid._minmax(vals)
    if norm == "z":
        arr = np.asarray(vals, dtype=float)
        std = arr.std()
        if std <= 1e-12:
            return [0.0] * len(vals)
        return ((arr - arr.mean()) / std).tolist()
    raise ValueError(f"unknown norm: {norm!r}")


def fuse_mix(seg_rec: dict, line_rec: dict, gold: set[int], norm: str) -> dict:
    """approach A — pool segment units and line units into one global ranking.

    Each retriever's scores are normalized among themselves (``norm``), the two
    pools are concatenated and sorted descending, and a ranked record is built so
    a mixed top-k keeps only the strongest units regardless of granularity. Ties
    keep the source/narrative order via a stable sort.
    """
    seg = seg_rec["ranked"]
    line = line_rec["ranked"]
    seg_n = _normalize([e["score"] for e in seg], norm)
    line_n = _normalize([e["score"] for e in line], norm)
    pooled = [(s, e["chapter"]) for s, e in zip(seg_n, seg)]
    pooled += [(s, e["chapter"]) for s, e in zip(line_n, line)]
    # Stable sort by score desc (negate for stability over reverse=True ties).
    order = sorted(range(len(pooled)), key=lambda i: -pooled[i][0])
    ranked = []
    gold_best: dict[int, int] = {}
    for rank, i in enumerate(order, start=1):
        score, ch = pooled[i]
        ranked.append({"rank": rank, "chapter": ch, "score": score})
        if ch in gold and ch not in gold_best:
            gold_best[ch] = rank
    return {
        "ranked": ranked,
        "gold_chapter_best_rank": gold_best,
        "gold_first_rank": min(gold_best.values()) if gold_best else None,
    }


# ---------------------------------------------------------------------------
# Small aggregation helpers
# ---------------------------------------------------------------------------

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _subset(records: dict[int, dict], subset: set[int] | None) -> list[dict]:
    return [r for qid, r in records.items() if subset is None or qid in subset]


def _strict_count(recs: list[dict], k: int) -> int:
    """Number of questions with gold ⊆ top-k chapters (report.py's strict recall)."""
    return sum(1 for r in recs
               if set(r["gold_chapters"]) <= {h["chapter"] for h in r["ranked"][:k]})


def _union_recs(seg_recs, line_recs, subset, fn, k):
    """Apply a hybrid union_* helper over a question subset, dropping Nones."""
    out = []
    for qid in seg_recs:
        if subset is not None and qid not in subset:
            continue
        v = fn(seg_recs[qid], line_recs[qid], k)
        if v is not None:
            out.append(v)
    return out


def _union_strict_count(seg_recs, line_recs, subset, k):
    return sum(1 for qid in seg_recs
               if (subset is None or qid in subset)
               and hybrid.union_strict(seg_recs[qid], line_recs[qid], k))


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def print_score_scale(seg_recs, line_recs, k: int = 10) -> None:
    """Diagnostic — segment vs line top-k cosine means (the ~+0.04 line bias)."""
    seg_topk, seg_top1, line_topk, line_top1 = [], [], [], []
    for qid in seg_recs:
        s = [h["score"] for h in seg_recs[qid]["ranked"][:k]]
        l = [h["score"] for h in line_recs[qid]["ranked"][:k]]
        seg_topk += s; line_topk += l
        seg_top1.append(s[0]); line_top1.append(l[0])
    print(f"Score scale (cosine, top-{k}):")
    print(f"  segment: mean={_mean(seg_topk):.3f}  per-question top-1 mean={_mean(seg_top1):.3f}")
    print(f"  line:    mean={_mean(line_topk):.3f}  per-question top-1 mean={_mean(line_top1):.3f}")
    print(f"  line−segment top-k mean gap = {_mean(line_topk) - _mean(seg_topk):+.3f}")
    print()


def print_coverage_table(method_recs, seg_recs, line_recs, questions) -> None:
    """Table 1 — chapter coverage@k by scope, one row per method + Union oracle."""
    scopes = scopes_from_questions(questions)
    header = f"{'method':<9} {'scope':<7} {'n':>3} " + " ".join(f"k={k:<3}" for k in K_COLS)
    print("Table 1 — chapter coverage@k  (fraction of gold chapters with a hit in top-k)")
    print(header)
    print("-" * len(header))
    for scope_name, subset in scopes:
        for method in RANK_METHODS:
            recs = _subset(method_recs[method], subset)
            row = f"{method:<9} {scope_name:<7} {len(recs):>3} "
            for k in K_COLS:
                vals = [v for r in recs if (v := coverage_at_k(r, k)) is not None]
                row += f"{_mean(vals):<5.2f} "
            print(row)
        # Union oracle row
        recs = _subset(seg_recs, subset)
        row = f"{'Union':<9} {scope_name:<7} {len(recs):>3} "
        for k in K_COLS:
            row += f"{_mean(_union_recs(seg_recs, line_recs, subset, hybrid.union_coverage, k)):<5.2f} "
        print(row)
        print()


def print_summary_table(method_recs, seg_recs, line_recs, questions) -> None:
    """Table 2 — strict recall / coverage / precision at k=5 and k=10 (scope: all)."""
    n = len(seg_recs)
    print("Table 2 — strict recall / coverage / precision  (scope: all)")
    print("  (strict recall = gold ⊆ top-k; coverage = mean |gold ∩ top-k| / |gold|)")
    print(f"{'method':<9} {'sr@5':>6} {'cov@5':>6} {'prec@5':>7}   "
          f"{'sr@10':>6} {'cov@10':>6} {'prec@10':>8}")
    print("-" * 62)
    for method in RANK_METHODS:
        recs = list(method_recs[method].values())
        cells = []
        for k in (5, 10):
            sr = _strict_count(recs, k)
            cov = _mean([v for r in recs if (v := coverage_at_k(r, k)) is not None])
            prec = _mean([v for r in recs if (v := precision_at_k(r, k)) is not None])
            cells.append((sr, cov, prec))
        (s5, c5, p5), (s10, c10, p10) = cells
        print(f"{method:<9} {s5:>4}/{n:<2} {c5:>6.2f} {p5:>7.2f}   "
              f"{s10:>4}/{n:<2} {c10:>6.2f} {p10:>8.2f}")
    # Union oracle
    cells = []
    for k in (5, 10):
        sr = _union_strict_count(seg_recs, line_recs, None, k)
        cov = _mean(_union_recs(seg_recs, line_recs, None, hybrid.union_coverage, k))
        prec = _mean(_union_recs(seg_recs, line_recs, None, hybrid.union_precision, k))
        cells.append((sr, cov, prec))
    (s5, c5, p5), (s10, c10, p10) = cells
    print(f"{'Union':<9} {s5:>4}/{n:<2} {c5:>6.2f} {p5:>7.2f}   "
          f"{s10:>4}/{n:<2} {c10:>6.2f} {p10:>8.2f}")
    print()


def print_norm_sweep(seg_recs, line_recs) -> None:
    """Table 3 — approach A normalization sweep (strict recall / coverage @ k=5,10)."""
    n = len(seg_recs)
    print("Table 3 — Mix (approach A) normalization sweep  (scope: all)")
    print("  raw over-favors line (higher cosines); z / min-max remove the bias.")
    print(f"{'norm':<8} {'sr@5':>6} {'cov@5':>6}   {'sr@10':>6} {'cov@10':>6}")
    print("-" * 42)
    for norm in NORMS:
        recs = {qid: fuse_mix(seg_recs[qid], line_recs[qid],
                              set(seg_recs[qid]["gold_chapters"]), norm)
                for qid in seg_recs}
        for qid in recs:
            recs[qid]["gold_chapters"] = seg_recs[qid]["gold_chapters"]
        rl = list(recs.values())
        s5 = _strict_count(rl, 5); c5 = _mean([v for r in rl if (v := coverage_at_k(r, 5)) is not None])
        s10 = _strict_count(rl, 10); c10 = _mean([v for r in rl if (v := coverage_at_k(r, 10)) is not None])
        print(f"{norm:<8} {s5:>4}/{n:<2} {c5:>6.2f}   {s10:>4}/{n:<2} {c10:>6.2f}")
    print()


def print_provenance_table(method_recs, questions, k: int) -> None:
    """Table 4 — per gold chapter, which retriever(s) surface it in the top-k.

    Code over S=Segment, L=Line, M=Mix; '·' = missed. The summary tallies the
    union property: does Mix's covered set equal Segment∪Line, where does Line
    recover a Segment miss (and vice-versa) — PLAN.md's "orthogonal misses".
    """
    seg, line, mix = method_recs["Segment"], method_recs["Line"], method_recs["Mix"]
    print(f"Table 4 — per-question provenance  (top-{k}; S=segment L=line M=mix, · = miss)")
    print(f"{'qid':>3} {'type':<6} {'gold':<16} per-chapter coverage codes")
    print("-" * 60)
    line_beats_seg = seg_beats_line = mix_loss = both_miss = 0
    for qid in sorted(seg):
        s_top = {h["chapter"] for h in seg[qid]["ranked"][:k]}
        l_top = {h["chapter"] for h in line[qid]["ranked"][:k]}
        m_top = {h["chapter"] for h in mix[qid]["ranked"][:k]}
        gold = sorted(set(seg[qid]["gold_chapters"]))
        codes = []
        for ch in gold:
            in_s, in_l, in_m = ch in s_top, ch in l_top, ch in m_top
            codes.append(f"{ch}:{'S' if in_s else '·'}{'L' if in_l else '·'}{'M' if in_m else '·'}")
            if in_l and not in_s:
                line_beats_seg += 1
            if in_s and not in_l:
                seg_beats_line += 1
            if (in_s or in_l) and not in_m:
                mix_loss += 1
            if not in_s and not in_l:
                both_miss += 1
        print(f"{qid:>3} {seg[qid]['type']:<6} {str(gold):<16} {' '.join(codes)}")
    print(f"  Line covers {line_beats_seg} gold chapter(s) Segment missed; "
          f"Segment covers {seg_beats_line} Line missed  (orthogonality).")
    print(f"  Mix suppressions (Segment or Line covered, Mix dropped): {mix_loss}")
    print(f"  Neither Segment nor Line covered (union ceiling misses): {both_miss}")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (en or ja — both supported, no BM25)")
    parser.add_argument("-e", "--embed", default="embeddinggemma", help="embedding model")
    parser.add_argument("--norm", default="minmax", choices=NORMS,
                        help="Mix (approach A) normalization for the Tables 1/2/4 rows")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--index", default=None,
                        help="segment index (default: index-<lang>.safetensors)")
    parser.add_argument("--line-index", default=None,
                        help="line index (default: index-line-<lang>.safetensors)")
    args = parser.parse_args()

    lang = args.lang
    questions_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"
    seg_path = Path(args.index) if args.index else QA_EVAL / f"index-{lang}.safetensors"
    line_path = Path(args.line_index) if args.line_index else QA_EVAL / f"index-line-{lang}.safetensors"

    print(f"Loading segment index from {seg_path}")
    normed_seg, seg_scenes = load_index(seg_path)
    print(f"  {normed_seg.shape[0]} segments, dim={normed_seg.shape[1]}")
    print(f"Loading line index from {line_path}")
    normed_line, lines, line_segments = load_line_index(line_path)
    print(f"  {normed_line.shape[0]} lines, {len(line_segments)} segments, dim={normed_line.shape[1]}")

    # The two segment lists must be identical and in the same order, so a chapter
    # means the same thing on both sides (same guard PLAN.md calls for).
    assert len(seg_scenes) == len(line_segments), (
        f"segment count mismatch: index={len(seg_scenes)} vs line-index={len(line_segments)}")
    for i, (a, b) in enumerate(zip(seg_scenes, line_segments)):
        assert a["chapter"] == b["chapter"] and a["segment"] == b["segment"], (
            f"segment {i} mismatch: {(a['chapter'], a['segment'])} vs {(b['chapter'], b['segment'])}")

    questions = load_questions(questions_path)
    print(f"Questions: {len(questions)}")
    print()

    # Per-question rankings. Each gets the {question_id, type, gold_chapters, **ranking}
    # shape the coverage helpers expect, matching hybrid.py / sweep_vector.py.
    seg_recs: dict[int, dict] = {}
    line_recs: dict[int, dict] = {}
    mix_recs: dict[int, dict] = {}
    total = len(questions)
    for qid, q in enumerate(questions, start=1):
        print(f"[{qid}/{total}] {q['question'][:70]}")
        gold = set(q["chapters"])
        meta = {"question_id": qid, "type": q.get("type", "all"),
                "gold_chapters": sorted(gold)}
        q_vec = embed_query(q["question"], args.embed)
        seg_recs[qid] = {**meta, **sweep_vector.rank_all_scenes(normed_seg, q_vec, seg_scenes, gold)}
        line_recs[qid] = {**meta, **rank_all_lines(normed_line, q_vec, lines, gold)}
        mix_recs[qid] = {**meta, **fuse_mix(seg_recs[qid], line_recs[qid], gold, args.norm)}

    method_recs = {"Segment": seg_recs, "Line": line_recs, "Mix": mix_recs}

    print()
    print(f"Mix (Tables 1/2/4) normalization: {args.norm}")
    print()
    print_score_scale(seg_recs, line_recs)
    print_coverage_table(method_recs, seg_recs, line_recs, questions)
    print_summary_table(method_recs, seg_recs, line_recs, questions)
    print_norm_sweep(seg_recs, line_recs)
    print_provenance_table(method_recs, questions, k=5)
    print_provenance_table(method_recs, questions, k=10)


if __name__ == "__main__":
    main()
