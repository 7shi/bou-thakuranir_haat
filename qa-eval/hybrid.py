#!/usr/bin/env python3
"""Hybrid retrieval (dense + BM25) gold-coverage analysis.

Standalone script in the ``sweep_vector.py`` / ``bm25.py`` lineage (no LLM output,
no answer file — terminal tables only). It fuses the two retrievers' rankings
and asks the question [PLAN.md](PLAN.md) poses: does a hybrid recover both
retrievers' misses *simultaneously* — i.e. does its covered set equal the
set-theoretic union of dense and BM25 coverage at each k?

Four fusion strategies are compared so the choice between rank-blending and
score-blending is empirical, not assumed:

- **RRF (Reciprocal Rank Fusion)** — blends ranks, not scores. The PLAN.md
  choice, because both retrievers' scores fail to separate gold (F1 ≈ 0.36–0.38)
  while rank (k) is the lever for both, and rank-blending sidesteps the
  unbounded-BM25 (≈ [0, 30]) vs. bounded-cosine ([-1, 1]) scale mismatch::

      RRF(scene) = w_d / (K + rank_dense) + w_b / (K + rank_bm25)

- **Borda Count** — the other classic rank-fusion method, with a linear decay
  ``(N - rank)`` instead of RRF's reciprocal ``1/(K + rank)``. Both are
  rank-based; Borda weights the top of the list more harshly. Including it
  isolates whether RRF's reciprocal shape (vs. any rank-blend) matters.

- **CombSUM** — min-max normalizes each retriever's scores to [0, 1] and sums
  them. The score-based baseline PLAN.md argues *against*: it inherits both
  retrievers' score-blindness, so it should underperform the rank-blends.
  Confirming that here is part of the comparison.

- **Union oracle** — the per-k set-theoretic upper bound: coverage if the
  hybrid kept every chapter *either* retriever surfaced in its top-k. Not a
  ranking (the kept set changes with k), but the ceiling any fusion could
  reach at depth k. RRF's goal is to match it from a single ranking.

Reuses ``sweep_vector.rank_all_scenes`` (dense) and ``bm25.rank_all_scenes``
(sparse), the scoring internals ``answer_vector.load_index`` / ``embed_query``
and
``bm25.BM25Index`` / ``tokenize``, and the analysis helpers
``bm25.coverage_at_k`` / ``precision_at_k`` / ``scopes_from_questions``. The
scene unit (segment; title + body document) and tokenization match ``bm25.py``
exactly, and the dense side uses the same embedding index as ``sweep_vector.py``,
so every retriever's coverage@k reads on identical axes.

Tokenization is English-only (BM25 is English-only); Japanese is deferred.
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

from answer import ROOT, LANGS, load_questions
from answer_vector import load_index, embed_query, expand_and_merge
import sweep_vector
import bm25
from bm25 import (
    BM25Index,
    tokenize,
    load_titles,
    load_scenes,
    scopes_from_questions,
    coverage_at_k,
    precision_at_k,
)

QA_EVAL = Path(__file__).resolve().parent

# k columns shown in the coverage table (last entry = whole index, always 1.0).
# Identical to sweep_vector.py / bm25.py so the curves read side by side.
K_COLS = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 82]

# RRF parameter sweep grid. K controls rank-decay sharpness (standard 60; the
# 82-scene corpus is small, so a smaller K may discriminate better). w_d/w_b
# biases toward either retriever (start equal-weight).
RRF_K_GRID = [5, 30, 60]
RRF_WEIGHT_GRID = [(1.0, 1.0), (0.7, 1.3), (1.3, 0.7)]

# The fusion strategies that produce a single ranking (Union is handled
# separately as a per-k oracle, not a ranking).
RANK_METHODS = ["Dense", "BM25", "RRF", "Borda", "CombSUM"]


# ---------------------------------------------------------------------------
# Fusion helpers
# ---------------------------------------------------------------------------

def _aligned_scores(rec: dict, scenes: list[dict]) -> list[float]:
    """Score per scene in ``scenes`` order, from a ranked record."""
    smap = {(e["chapter"], e["segment"]): e["score"] for e in rec["ranked"]}
    return [smap[(s["chapter"], s["segment"])] for s in scenes]


def _aligned_ranks(rec: dict, scenes: list[dict]) -> list[int]:
    """Rank (1-indexed) per scene in ``scenes`` order, from a ranked record."""
    rmap = {(e["chapter"], e["segment"]): e["rank"] for e in rec["ranked"]}
    return [rmap[(s["chapter"], s["segment"])] for s in scenes]


def _minmax(vals: list[float]) -> list[float]:
    """Map ``vals`` to [0, 1] via min-max (per-query normalization for CombSUM)."""
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 1e-12:
        return [0.0] * len(vals)
    return [(v - lo) / span for v in vals]


def rank_from_scores(scores: list[float], scenes: list[dict], gold: set[int]) -> dict:
    """Build the standard ranked record from a per-scene score list.

    Same record shape as ``sweep_vector.rank_all_scenes`` / ``bm25.rank_all_scenes``
    so ``coverage_at_k`` / ``precision_at_k`` operate uniformly on any
    retriever's output. Ties keep scene (narrative) order via a stable sort.
    """
    n = len(scenes)
    order = sorted(range(n), key=lambda i: float(scores[i]), reverse=True)
    ranked = []
    gold_best: dict[int, int] = {}
    for rank, idx in enumerate(order, start=1):
        s = scenes[idx]
        ch = s["chapter"]
        ranked.append({
            "rank": rank,
            "chapter": ch,
            "segment": s["segment"],
            "score": float(scores[idx]),
        })
        if ch in gold and ch not in gold_best:
            gold_best[ch] = rank
    return {
        "ranked": ranked,
        "gold_chapter_best_rank": gold_best,
        "gold_first_rank": min(gold_best.values()) if gold_best else None,
    }


def fuse_rrf(dense_rec: dict, bm25_rec: dict, scenes: list[dict], gold: set[int],
             K: float = 60.0, wd: float = 1.0, wb: float = 1.0) -> dict:
    """Reciprocal Rank Fusion: ``wd/(K+rank_d) + wb/(K+rank_b)`` per scene."""
    d_ranks = _aligned_ranks(dense_rec, scenes)
    b_ranks = _aligned_ranks(bm25_rec, scenes)
    fused = [wd / (K + d_ranks[i]) + wb / (K + b_ranks[i]) for i in range(len(scenes))]
    return rank_from_scores(fused, scenes, gold)


def fuse_borda(dense_rec: dict, bm25_rec: dict, scenes: list[dict], gold: set[int],
               wd: float = 1.0, wb: float = 1.0) -> dict:
    """Borda count: ``wd*(N - rank_d) + wb*(N - rank_b)`` per scene.

    Linear rank decay (vs. RRF's reciprocal) — weights the top of the list
    more heavily. Both methods are rank-based; including Borda isolates
    whether RRF's reciprocal shape matters vs. any rank-blend.
    """
    n = len(scenes)
    d_ranks = _aligned_ranks(dense_rec, scenes)
    b_ranks = _aligned_ranks(bm25_rec, scenes)
    fused = [wd * (n - d_ranks[i]) + wb * (n - b_ranks[i]) for i in range(n)]
    return rank_from_scores(fused, scenes, gold)


def fuse_combsum(dense_rec: dict, bm25_rec: dict, scenes: list[dict], gold: set[int],
                 wd: float = 1.0, wb: float = 1.0) -> dict:
    """CombSUM: min-max-normalized scores summed per scene.

    The score-based baseline: each retriever's scores are mapped to [0, 1]
    per query, then weighted-summed. Inherits both retrievers' score-blindness,
    so it is expected to trail the rank-blends.
    """
    d_n = _minmax(_aligned_scores(dense_rec, scenes))
    b_n = _minmax(_aligned_scores(bm25_rec, scenes))
    fused = [wd * d + wb * b for d, b in zip(d_n, b_n)]
    return rank_from_scores(fused, scenes, gold)


# ---------------------------------------------------------------------------
# Union oracle (per-k set, not a ranking)
# ---------------------------------------------------------------------------

def _union_top_chapters(dense_rec: dict, bm25_rec: dict, k: int) -> set[int]:
    """Union of dense top-k chapters and BM25 top-k chapters."""
    d_top = {h["chapter"] for h in dense_rec["ranked"][:k]}
    b_top = {h["chapter"] for h in bm25_rec["ranked"][:k]}
    return d_top | b_top


def union_coverage(dense_rec: dict, bm25_rec: dict, k: int) -> float | None:
    """Fraction of gold chapters in the union top-k (None if no gold)."""
    gold = set(dense_rec["gold_chapters"])
    if not gold:
        return None
    return len(_union_top_chapters(dense_rec, bm25_rec, k) & gold) / len(gold)


def union_precision(dense_rec: dict, bm25_rec: dict, k: int) -> float | None:
    """|gold ∩ union top-k| / |union top-k| (None if empty)."""
    top = _union_top_chapters(dense_rec, bm25_rec, k)
    if not top:
        return None
    return len(top & set(dense_rec["gold_chapters"])) / len(top)


def union_strict(dense_rec: dict, bm25_rec: dict, k: int) -> bool:
    """True iff gold ⊆ union top-k — the strict-recall oracle at depth k."""
    return set(dense_rec["gold_chapters"]) <= _union_top_chapters(dense_rec, bm25_rec, k)


# ---------------------------------------------------------------------------
# Aggregation helpers over a set of records
# ---------------------------------------------------------------------------

def _subset_recs(records: dict[int, dict], subset: set[int] | None) -> list[dict]:
    return [r for qid, r in records.items() if subset is None or qid in subset]


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _cov_vals(recs: list[dict], k: int) -> list[float]:
    return [v for r in recs if (v := coverage_at_k(r, k)) is not None]


def _prec_vals(recs: list[dict], k: int) -> list[float]:
    return [v for r in recs if (v := precision_at_k(r, k)) is not None]


def _strict_count(recs: list[dict], k: int) -> int:
    return sum(1 for r in recs
               if set(r["gold_chapters"]) <= {h["chapter"] for h in r["ranked"][:k]})


def _union_cov_vals(dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                    subset: set[int] | None, k: int) -> list[float]:
    vals = []
    for qid in dense_recs:
        if subset is not None and qid not in subset:
            continue
        v = union_coverage(dense_recs[qid], bm25_recs[qid], k)
        if v is not None:
            vals.append(v)
    return vals


def _union_prec_vals(dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                     subset: set[int] | None, k: int) -> list[float]:
    vals = []
    for qid in dense_recs:
        if subset is not None and qid not in subset:
            continue
        v = union_precision(dense_recs[qid], bm25_recs[qid], k)
        if v is not None:
            vals.append(v)
    return vals


def _union_strict_count(dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                        subset: set[int] | None, k: int) -> int:
    return sum(1 for qid in dense_recs
               if (subset is None or qid in subset)
               and union_strict(dense_recs[qid], bm25_recs[qid], k))


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def print_coverage_table(method_recs: dict[str, dict[int, dict]],
                         dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                         questions: list[dict]) -> None:
    """Table 1 — chapter coverage@k by scope, one row per method + Union oracle."""
    scopes = scopes_from_questions(questions)
    for scope_name, subset in scopes:
        n = len(_subset_recs(dense_recs, subset))
        print(f"Table 1 — chapter coverage@k  (scope: {scope_name}, n={n})")
        header = f"{'method':<9} " + " ".join(f"k={k:<3}" for k in K_COLS)
        print(header)
        print("-" * len(header))
        for method in RANK_METHODS:
            recs = _subset_recs(method_recs[method], subset)
            row = f"{method:<9} "
            for k in K_COLS:
                row += f"{_mean(_cov_vals(recs, k)):<5.2f} "
            print(row)
        # Union oracle row (per-k set, computed from dense + bm25 directly).
        row = f"{'Union':<9} "
        for k in K_COLS:
            row += f"{_mean(_union_cov_vals(dense_recs, bm25_recs, subset, k)):<5.2f} "
        print(row)
        print()


def print_summary_table(method_recs: dict[str, dict[int, dict]],
                        dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                        questions: list[dict]) -> None:
    """Table 2 — strict recall / coverage / precision at k=5 and k=10."""
    scopes = scopes_from_questions(questions)
    print("Table 2 — retrieval summary at k=5 / k=10  "
          "(strict recall = gold ⊆ top-k; coverage = mean |gold ∩ top-k| / |gold|)")
    print(f"{'method':<9} {'scope':<7} {'k=5 strict':>11} {'cov':>6} {'prec':>6} "
          f"{'k=10 strict':>12} {'cov':>6}")
    print("-" * 64)
    for scope_name, subset in scopes:
        for method in RANK_METHODS:
            recs = _subset_recs(method_recs[method], subset)
            s5 = _strict_count(recs, 5)
            c5 = _mean(_cov_vals(recs, 5))
            p5 = _mean(_prec_vals(recs, 5))
            s10 = _strict_count(recs, 10)
            c10 = _mean(_cov_vals(recs, 10))
            print(f"{method:<9} {scope_name:<7} {f'{s5}/{len(recs)}':>11} "
                  f"{c5:>6.3f} {p5:>6.3f} {f'{s10}/{len(recs)}':>12} {c10:>6.3f}")
        # Union row.
        d_sub = {qid: dense_recs[qid] for qid in dense_recs if subset is None or qid in subset}
        b_sub = {qid: bm25_recs[qid] for qid in bm25_recs if subset is None or qid in subset}
        nu = len(d_sub)
        us5 = _union_strict_count(d_sub, b_sub, None, 5)
        uc5 = _mean(_union_cov_vals(d_sub, b_sub, None, 5))
        up5 = _mean(_union_prec_vals(d_sub, b_sub, None, 5))
        us10 = _union_strict_count(d_sub, b_sub, None, 10)
        uc10 = _mean(_union_cov_vals(d_sub, b_sub, None, 10))
        print(f"{'Union':<9} {scope_name:<7} {f'{us5}/{nu}':>11} "
              f"{uc5:>6.3f} {up5:>6.3f} {f'{us10}/{nu}':>12} {uc10:>6.3f}")
    print()


def print_rrf_sweep(dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                    scenes: list[dict]) -> None:
    """Table 3 — RRF K × weight sweep (strict recall / coverage, scope: all)."""
    print("Table 3 — RRF parameter sweep  (strict recall / coverage, scope: all)")
    print(f"{'K':>4} {'w_d':>5} {'w_b':>5} {'k=5 strict':>11} {'k=5 cov':>8} "
          f"{'k=10 strict':>12} {'k=10 cov':>9}")
    print("-" * 60)
    n = len(dense_recs)
    for K in RRF_K_GRID:
        for wd, wb in RRF_WEIGHT_GRID:
            recs = []
            for qid in dense_recs:
                gold = set(dense_recs[qid]["gold_chapters"])
                fused = fuse_rrf(dense_recs[qid], bm25_recs[qid], scenes, gold,
                                 K=float(K), wd=wd, wb=wb)
                fused["gold_chapters"] = dense_recs[qid]["gold_chapters"]
                recs.append(fused)
            s5 = _strict_count(recs, 5)
            c5 = _mean(_cov_vals(recs, 5))
            s10 = _strict_count(recs, 10)
            c10 = _mean(_cov_vals(recs, 10))
            print(f"{K:>4} {wd:>5.1f} {wb:>5.1f} {f'{s5}/{n}':>11} {c5:>8.3f} "
                  f"{f'{s10}/{n}':>12} {c10:>9.3f}")
    print()


def print_provenance_table(method_recs: dict[str, dict[int, dict]],
                           dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                           questions: list[dict], k: int = 5) -> None:
    """Table 4 — per-question provenance: which retriever(s) surface each gold chapter.

    For each gold chapter, a three-letter code shows membership in the top-k
    of Dense (D), BM25 (B), and RRF (R); '·' means missed. The summary tallies
    the PLAN.md union property: does RRF's covered set equal dense ∪ BM25, or
    does the rank-blend suppress some union hits / recover some neither finds?
    """
    rrf_recs = method_recs["RRF"]
    print(f"Table 4 — provenance at k={k}  "
          f"(per gold chapter: D=dense B=bm25 R=rrf; · = outside top-{k})")
    print(f"{'qid':>3} {'type':<6} {'gold':<16} per-chapter coverage codes")
    print("-" * 70)
    rrf_beats_dense = 0   # R covers, D does not
    rrf_beats_bm25 = 0    # R covers, B does not
    rrf_pure_win = 0      # R covers, neither D nor B (the hybrid premium)
    rrf_loss = 0          # D or B covers, R does not (rank-blend suppression)
    for qid in sorted(dense_recs):
        d_top = {h["chapter"] for h in dense_recs[qid]["ranked"][:k]}
        b_top = {h["chapter"] for h in bm25_recs[qid]["ranked"][:k]}
        r_top = {h["chapter"] for h in rrf_recs[qid]["ranked"][:k]}
        gold = sorted(set(dense_recs[qid]["gold_chapters"]))
        codes = []
        for ch in gold:
            dc = "D" if ch in d_top else "·"
            bc = "B" if ch in b_top else "·"
            rc = "R" if ch in r_top else "·"
            codes.append(f"{ch}:{dc}{bc}{rc}")
            if ch in r_top and ch not in d_top:
                rrf_beats_dense += 1
            if ch in r_top and ch not in b_top:
                rrf_beats_bm25 += 1
            if ch in r_top and ch not in d_top and ch not in b_top:
                rrf_pure_win += 1
            if ch not in r_top and (ch in d_top or ch in b_top):
                rrf_loss += 1
        print(f"{qid:>3} {dense_recs[qid]['type']:<6} {str(gold):<16} {' '.join(codes)}")
    print()
    print(f"  RRF covers {rrf_beats_dense} gold-pair(s) Dense missed, "
          f"{rrf_beats_bm25} BM25 missed.")
    print(f"  RRF pure wins (neither Dense nor BM25 surfaced): {rrf_pure_win}")
    print(f"  RRF suppressions (Dense or BM25 surfaced, RRF dropped): {rrf_loss}")
    print()


def print_dense_miss_recovery(method_recs: dict[str, dict[int, dict]],
                              dense_recs: dict[int, dict],
                              bm25_recs: dict[int, dict]) -> None:
    """Table 5 — for the known dense-retrieval misses, where each hybrid lands.

    The seven questions (Q27, Q28, Q31, Q36, Q43, Q45, Q49) where dense top-5
    dropped a gold chapter, with each fusion's first-gold-rank and whether it
    recovers the miss at k≤5 / k≤10. Mirrors bm25.py's Table 5 for the
    three-way dense vs. BM25 vs. hybrid view.
    """
    DENSE_MISSES = [27, 28, 31, 36, 43, 45, 49]
    cols = ["Dense", "BM25", "RRF", "Borda", "CombSUM"]
    widths = {"Dense": 8, "BM25": 8, "RRF": 7, "Borda": 9, "CombSUM": 7}
    print("Table 5 — dense-retrieval miss recovery  "
          "(dense misses: Q27, Q28, Q31, Q36, Q43, Q45, Q49)")
    header = f"{'qid':>3} {'type':<6}"
    for m in cols:
        header += f" {'1st'+m:>{widths[m]}}"
    header += "   gold chapters"
    print(header)
    print("-" * len(header))
    for qid in DENSE_MISSES:
        gold = sorted(set(dense_recs[qid]["gold_chapters"]))
        line = f"{qid:>3} {dense_recs[qid]['type']:<6}"
        for m in cols:
            first = method_recs[m][qid]["gold_first_rank"]
            val = str(first) if first is not None else "-"
            line += f" {val:>{widths[m]}}"
        line += f"   {gold}"
        print(line)
    print()
    # Per-method recovery counts at k≤5 and k≤10.
    print(f"  recovery at k≤5 / k≤10 (of {len(DENSE_MISSES)} dense misses):")
    for m in ["BM25", "RRF", "Borda", "CombSUM"]:
        r5 = r10 = 0
        for qid in DENSE_MISSES:
            first = method_recs[m][qid]["gold_first_rank"]
            if first is None:
                continue
            if first <= 5:
                r5 += 1
            if first <= 10:
                r10 += 1
        print(f"    {m:<8} {r5}/{len(DENSE_MISSES)} at k≤5, "
              f"{r10}/{len(DENSE_MISSES)} at k≤10")
    print()


def print_context_size_table(dense_recs: dict[int, dict], bm25_recs: dict[int, dict],
                             scenes: list[dict], questions: list[dict], N: int = 1) -> None:
    """Table 6 — context size with ±N expansion: actual scenes the answerer sees.

    The retrieval unit is a **scene**; ``answer_vector.py`` expands each top-k hit
    by ±N scenes within the same chapter (``expand_and_merge``, default N=1) and
    merges overlaps before building the context. So the answerer does NOT see
    just the top-k scenes — it sees the expanded set, which is larger. This
    table applies the same ±N expansion to Dense, BM25, and the Union of their
    top-k hits, so the context sizes are directly comparable to what the real
    RAG pipeline feeds.

    Ceiling = 0.990 shows over-inclusion is harmless to accuracy, so the only
    cost of the Union's larger hit set is the token budget — measured here as
    expanded-scene counts and the chapters they span.
    """
    scopes = scopes_from_questions(questions)
    ks = (5, 10)

    # Map (chapter, segment) → position in the scenes list, to recover scene
    # indices from the ranked records (which carry chapter/segment, not index).
    pos = {(s["chapter"], s["segment"]): i for i, s in enumerate(scenes)}

    def _expanded_for(rec: dict, k: int) -> list[int]:
        """Scene indices after ±N expansion of rec's top-k hits."""
        hit_idx = [pos[(h["chapter"], h["segment"])] for h in rec["ranked"][:k]]
        return expand_and_merge([(i, 0.0) for i in hit_idx], scenes, N)

    def _expanded_union(k: int, qid: int) -> list[int]:
        """Expanded scene indices for the Union of dense + bm25 top-k hits."""
        d_idx = [pos[(h["chapter"], h["segment"])] for h in dense_recs[qid]["ranked"][:k]]
        b_idx = [pos[(h["chapter"], h["segment"])] for h in bm25_recs[qid]["ranked"][:k]]
        union_hits = sorted(set(d_idx) | set(b_idx))
        return expand_and_merge([(i, 0.0) for i in union_hits], scenes, N)

    # Per-question expanded-scene / chapter counts.
    counts: dict[int, dict] = {}
    for qid in dense_recs:
        gold = set(dense_recs[qid]["gold_chapters"])
        per_q: dict = {}
        for k in ks:
            d_exp = _expanded_for(dense_recs[qid], k)
            b_exp = _expanded_for(bm25_recs[qid], k)
            u_exp = _expanded_union(k, qid)
            u_chs = {scenes[i]["chapter"] for i in u_exp}
            per_q[k] = {
                "dense_sc": len(d_exp),
                "bm25_sc": len(b_exp),
                "union_sc": len(u_exp),
                "union_ch": len(u_chs),
                "gold_in_union": len(u_chs & gold),
                "n_gold": len(gold),
            }
        counts[qid] = per_q

    def _s(vals: list[int]) -> str:
        return (f"mean={statistics.mean(vals):4.1f}  "
                f"median={statistics.median(vals):4.1f}  "
                f"min={min(vals):>2}  max={max(vals):>2}  "
                f"stdev={statistics.pstdev(vals):.2f}")

    print(f"Table 6 — context size with ±{N} expansion  "
          f"(actual expanded scenes the answerer receives)")
    for scope_name, subset in scopes:
        qids = [qid for qid in counts if subset is None or qid in subset]
        print(f"  scope: {scope_name} (n={len(qids)})")
        for k in ks:
            print(f"    k={k:<2} Dense scenes: {_s([counts[q][k]['dense_sc'] for q in qids])}")
            print(f"        BM25  scenes: {_s([counts[q][k]['bm25_sc'] for q in qids])}")
            print(f"        Union scenes: {_s([counts[q][k]['union_sc'] for q in qids])}")
            print(f"        Union chapters: {_s([counts[q][k]['union_ch'] for q in qids])}")
        print()

    # Histogram of Union expanded-scene counts at k=10 (the headline depth).
    vals = [counts[qid][10]["union_sc"] for qid in counts]
    hist = Counter(vals)
    print(f"  Histogram — Union k=10 expanded-scene count (all, n={len(vals)}):")
    for n in sorted(hist):
        print(f"    {n:>2}sc  {hist[n]:>2}  {'#' * hist[n]}")
    print()

    # Per-question detail for cross (where the counts vary; single is stable).
    cross_qids = [qid for qid in sorted(counts)
                  if dense_recs[qid]["type"] == "cross"]
    print(f"  Per-question (cross, n={len(cross_qids)}, k=10, ±{N}):")
    print(f"    {'qid':>3} {'gold':<16} {'#g':>2} "
          f"{'Dsc':>4} {'Bsc':>4} {'Usc':>5} {'Uch':>4} {'gold⊂U':>6}")
    print("    " + "-" * 56)
    for qid in cross_qids:
        c = counts[qid][10]
        gold = sorted(set(dense_recs[qid]["gold_chapters"]))
        print(f"    {qid:>3} {str(gold):<16} {c['n_gold']:>2} "
              f"{c['dense_sc']:>4} {c['bm25_sc']:>4} {c['union_sc']:>5} "
              f"{c['union_ch']:>4} {c['gold_in_union']:>2}/{c['n_gold']:<3}")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (BM25 is English-only; "
                             "Japanese is deferred)")
    parser.add_argument("-e", "--embed", default="embeddinggemma",
                        help="embedding model (dense side)")
    parser.add_argument("--K", type=float, default=60.0,
                        help="RRF rank-smoothing constant (default 60)")
    parser.add_argument("--wd", type=float, default=1.0,
                        help="RRF dense weight (default 1.0)")
    parser.add_argument("--wb", type=float, default=1.0,
                        help="RRF BM25 weight (default 1.0)")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--index", default=None,
                        help="index safetensors (default: index-<lang>.safetensors)")
    parser.add_argument("--scenes", default=None,
                        help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-t", "--tsv", default=None,
                        help="scene titles TSV (default: all/<lang>-gemini.tsv)")
    args = parser.parse_args()

    lang = args.lang
    if lang != "en":
        raise SystemExit(
            f"hybrid.py: lang={lang!r} not supported (BM25 is English-only; "
            f"Japanese deferred — needs morphological analysis).")

    questions_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"
    index_path = Path(args.index) if args.index else QA_EVAL / f"index-{lang}.safetensors"
    scenes_path = Path(args.scenes) if args.scenes else ROOT / "all" / f"{lang}-gemini.jsonl"
    tsv_path = Path(args.tsv) if args.tsv else ROOT / "all" / f"{lang}-gemini.tsv"

    # Dense side: embedding index (matches sweep_vector.py).
    print(f"Loading index from {index_path}")
    normed, dense_scenes = load_index(index_path)
    print(f"Index: {normed.shape[0]} scenes, dim={normed.shape[1]}")

    # Sparse side: raw scene text (matches bm25.py).
    titles = load_titles(tsv_path)
    bm25_scenes = load_scenes(scenes_path, titles)
    print(f"Loaded {len(bm25_scenes)} scenes from {scenes_path}")

    # The two scene lists must be identical and in the same order, so that
    # scene index i refers to the same scene for the dense score array
    # (normed row i) and the BM25 score array (doc i).
    assert len(dense_scenes) == len(bm25_scenes), (
        f"scene count mismatch: index={len(dense_scenes)} vs jsonl={len(bm25_scenes)}")
    for i, (d, b) in enumerate(zip(dense_scenes, bm25_scenes)):
        assert d["chapter"] == b["chapter"] and d["segment"] == b["segment"], (
            f"scene {i} mismatch: index={(d['chapter'], d['segment'])} "
            f"vs jsonl={(b['chapter'], b['segment'])}")
    scenes = dense_scenes  # common list, identical order

    questions = load_questions(questions_path)
    print(f"Questions: {len(questions)}")

    # Build the BM25 index once (title + body document, matching bm25.py).
    docs = [tokenize(f"{s['title']} {s['text']}", lang=lang) for s in scenes]
    bm25_index = BM25Index(docs)
    print(f"BM25 index: {bm25_index.n_docs} docs, avgdl={bm25_index.avgdl:.1f} tokens, "
          f"vocab={len(bm25_index.idf)}")
    print()

    # Per-question base rankings from both retrievers. Each rank_all_scenes
    # returns {ranked, gold_chapter_best_rank, gold_first_rank}; the question
    # metadata (gold_chapters, type) is added here, matching sweep_vector.py /
    # bm25.py main(), so the analysis helpers find a uniform record shape.
    dense_recs: dict[int, dict] = {}
    bm25_recs: dict[int, dict] = {}
    total = len(questions)
    for qid, q in enumerate(questions, start=1):
        print(f"[{qid}/{total}] {q['question'][:70]}")
        gold = set(q["chapters"])
        meta = {
            "question_id": qid,
            "type": q.get("type", "all"),
            "gold_chapters": sorted(gold),
        }
        q_vec = embed_query(q["question"], args.embed)
        dense_recs[qid] = {**meta, **sweep_vector.rank_all_scenes(normed, q_vec, scenes, gold)}
        q_tokens = tokenize(q["question"], lang=lang)
        bm25_recs[qid] = {**meta, **bm25.rank_all_scenes(bm25_index, q_tokens, scenes, gold)}

    # Fuse with the default parameters for the main comparison tables.
    rrf_recs: dict[int, dict] = {}
    borda_recs: dict[int, dict] = {}
    combsum_recs: dict[int, dict] = {}
    for qid in dense_recs:
        meta = {
            "question_id": dense_recs[qid]["question_id"],
            "type": dense_recs[qid]["type"],
            "gold_chapters": dense_recs[qid]["gold_chapters"],
        }
        gold = set(dense_recs[qid]["gold_chapters"])
        rrf_recs[qid] = {**meta, **fuse_rrf(dense_recs[qid], bm25_recs[qid], scenes, gold,
                                            K=args.K, wd=args.wd, wb=args.wb)}
        borda_recs[qid] = {**meta, **fuse_borda(dense_recs[qid], bm25_recs[qid], scenes, gold)}
        combsum_recs[qid] = {**meta, **fuse_combsum(dense_recs[qid], bm25_recs[qid], scenes, gold)}

    method_recs = {
        "Dense": dense_recs,
        "BM25": bm25_recs,
        "RRF": rrf_recs,
        "Borda": borda_recs,
        "CombSUM": combsum_recs,
    }

    print()
    print(f"Default fusion: RRF K={args.K:g}, w_d={args.wd:g}, w_b={args.wb:g}; "
          f"Borda / CombSUM equal-weight.")
    print()
    print_coverage_table(method_recs, dense_recs, bm25_recs, questions)
    print_summary_table(method_recs, dense_recs, bm25_recs, questions)
    print_rrf_sweep(dense_recs, bm25_recs, scenes)
    print_provenance_table(method_recs, dense_recs, bm25_recs, questions, k=5)
    print_dense_miss_recovery(method_recs, dense_recs, bm25_recs)
    print_context_size_table(dense_recs, bm25_recs, scenes, questions)


if __name__ == "__main__":
    main()
