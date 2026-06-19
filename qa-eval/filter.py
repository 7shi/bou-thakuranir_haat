#!/usr/bin/env python3
"""Analyze filter10 relevance scores and cross-reference them against filter2/filter3.

Standalone analysis, independent of the answering pipeline — no LLM, no answer
synthesis, no output file (terminal tables only, like sweep_rag.py). It reads
the Phase 1 verdict TSVs produced by answer_filter.py and the gold chapters
from questions-<lang>.jsonl to answer:

  1. How are the 0-10 scores distributed, and do they separate gold from
     non-gold chapters?
  2. Which keep/drop threshold maximizes chapter recall / precision / F1,
     broken down by question type (single / cross)?
  3. How do the filter2 (yes/no) and filter3 (yes/maybe/no) verdicts map onto
     the 0-10 scale, and which filter10 threshold reproduces each variant's
     keep/drop boundary?

Requires the filter10 Phase 1 part TSVs (filter10-{1..4}.tsv). The filter2 and
filter3 crosstabs (Tables 5-8) are included only when those part TSVs also
exist.

Note on "recall": report.py uses strict subset recall (1 iff gold ⊆ used). This
script reports both strict subset recall AND partial coverage (the fraction of
gold chapters kept) so the threshold trade-off is visible as a curve.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from answer import ROOT, LANGS, load_questions
from answer_filter import read_verdict_tsv

QA_EVAL = Path(__file__).resolve().parent

SCORE_MAX = 10


def load_verdicts(lang: str, stem: str) -> dict[tuple[int, int], str]:
    """Load a filter{V}-{1..4}.tsv set into {(qid, chapter): verdict_str}.

    Returns an empty dict if no part files exist for the given stem.
    """
    out: dict[tuple[int, int], str] = {}
    for p in range(1, 5):
        path = QA_EVAL / f"results-{lang}" / f"{stem}-{p}.tsv"
        if not path.exists():
            continue
        for ch, qid, verdict in read_verdict_tsv(path):
            out[(qid, ch)] = verdict
    return out


def scopes_from_questions(
    questions: list[dict],
) -> list[tuple[str, set[int] | None]]:
    """("all", None) plus one (typename, id-set) per gold type, in first-seen order."""
    by_type: dict[str, set[int]] = {}
    for qid, q in enumerate(questions, start=1):
        by_type.setdefault(q.get("type", "all"), set()).add(qid)
    scopes: list[tuple[str, set[int] | None]] = [("all", None)]
    scopes += [(t, ids) for t, ids in by_type.items()]
    return scopes


def metrics(
    scores: dict[tuple[int, int], int],
    gold_by_qid: dict[int, set[int]],
    threshold: int,
    qids: list[int],
) -> dict[str, float]:
    """Retrieval metrics for "keep chapters with score >= threshold".

    strict    — fraction of questions where gold ⊆ kept (report.py notion).
    partial   — mean fraction of gold chapters kept (coverage curve).
    precision — mean |gold ∩ kept| / |kept|.
    avg_kept  — mean chapters kept per question.
    """
    strict = 0
    partial_sum = 0.0
    kept_total = 0
    gold_kept = 0
    for qid in qids:
        gold = gold_by_qid[qid]
        kept = {ch for (q, ch), sc in scores.items()
                if q == qid and sc >= threshold}
        kept_total += len(kept)
        gold_kept += len(gold & kept)
        if gold and gold.issubset(kept):
            strict += 1
        if gold:
            partial_sum += len(gold & kept) / len(gold)
    n = len(qids)
    return {
        "strict": strict / n if n else 0.0,
        "partial": partial_sum / n if n else 0.0,
        "precision": gold_kept / kept_total if kept_total else 0.0,
        "avg_kept": kept_total / n if n else 0.0,
    }


def metrics_keep(
    keep_map: dict[tuple[int, int], bool],
    gold_by_qid: dict[int, set[int]],
    qids: list[int],
) -> dict[str, float]:
    """Same metrics as `metrics()` but from an explicit keep/drop map.

    Used for the filter2/3 keep rules (which derive keep/drop from verdict
    labels, not from a numeric threshold).
    """
    strict = 0
    partial_sum = 0.0
    kept_total = 0
    gold_kept = 0
    for qid in qids:
        gold = gold_by_qid[qid]
        kept = {ch for (q, ch), keep in keep_map.items() if q == qid and keep}
        kept_total += len(kept)
        gold_kept += len(gold & kept)
        if gold and gold.issubset(kept):
            strict += 1
        if gold:
            partial_sum += len(gold & kept) / len(gold)
    n = len(qids)
    return {
        "strict": strict / n if n else 0.0,
        "partial": partial_sum / n if n else 0.0,
        "precision": gold_kept / kept_total if kept_total else 0.0,
        "avg_kept": kept_total / n if n else 0.0,
    }


# ---------------------------------------------------------------------------
# Table printers
# ---------------------------------------------------------------------------

def print_score_distribution(
    scores: dict[tuple[int, int], int],
    gold_by_qid: dict[int, set[int]],
) -> None:
    total = len(scores)
    dist = Counter(scores.values())
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))
    print("Table 1 — filter10 score distribution (all chapter-question pairs)")
    print(f"  {total} pairs total, {n_gold} gold, {total - n_gold} non-gold\n")
    print(f"  {'score':>5}  {'count':>5}  {'pct':>6}  {'gold':>5}  {'nongold':>7}  {'gold%':>6}  bar")
    print(f"  {'—'*70}")
    for s in range(SCORE_MAX + 1):
        g = sum(1 for (qid, ch), sc in scores.items()
                if sc == s and ch in gold_by_qid.get(qid, set()))
        ng = dist[s] - g
        pct = dist[s] / total * 100 if total else 0
        share = g / dist[s] * 100 if dist[s] else 0
        bar = "#" * (dist[s] // 5)
        print(f"  {s:5d}  {dist[s]:5d}  {pct:5.1f}%  {g:5d}  {ng:7d}  {share:5.1f}%  {bar}")
    print()


def print_threshold_sweep(
    scores: dict[tuple[int, int], int],
    gold_by_qid: dict[int, set[int]],
    questions: list[dict],
    all_qids: list[int],
) -> None:
    scopes = scopes_from_questions(questions)
    print("Table 2 — threshold sweep: keep chapters with score >= threshold")
    print(f"\n  {'thr':>3}  {'strict':>7}  {'partial':>8}  {'precision':>9}  {'F1':>5}  {'avg_kept':>8}")
    print(f"  {'—'*50}")
    for thr in range(0, SCORE_MAX + 2):
        m = metrics(scores, gold_by_qid, thr, all_qids)
        f1 = (2 * m["partial"] * m["precision"] / (m["partial"] + m["precision"])
              if (m["partial"] + m["precision"]) else 0.0)
        print(f"  {thr:3d}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
              f"{m['precision']:9.3f}  {f1:5.3f}  {m['avg_kept']:8.1f}")
    print()

    print("Table 3 — strict subset recall by question type")
    for scope_name, subset in scopes:
        if subset is None:
            continue  # "all" duplicates Table 2; show per-type scopes only
        qids = sorted(subset)
        n = len(qids)
        if n == 0:
            continue
        print(f"\n  {scope_name} ({n} questions):")
        print(f"    {'thr':>3}  {'strict':>7}  {'partial':>8}  {'precision':>9}  {'avg_kept':>8}")
        print(f"    {'—'*46}")
        for thr in range(0, SCORE_MAX + 2):
            m = metrics(scores, gold_by_qid, thr, qids)
            print(f"    {thr:3d}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
                  f"{m['precision']:9.3f}  {m['avg_kept']:8.1f}")
    print()


def print_low_score_gold(
    scores: dict[tuple[int, int], int],
    gold_by_qid: dict[int, set[int]],
    questions: list[dict],
    cutoff: int = 3,
) -> None:
    """Gold chapters scored at or below `cutoff` — unrecoverable retrieval risk."""
    rows = []
    n_gold = 0
    for (qid, ch), sc in sorted(scores.items()):
        if ch in gold_by_qid.get(qid, set()):
            n_gold += 1
            if sc <= cutoff:
                rows.append((qid, ch, sc, questions[qid - 1].get("type", "all")))
    print(f"Table 4 — gold chapters scored <= {cutoff} (retrieval risk)")
    print(f"  {len(rows)} of {n_gold} gold chapters are unrecoverable at any "
          f"threshold >= {cutoff + 1}\n")
    print(f"  {'qid':>3}  {'ch':>3}  {'score':>5}  {'type':<6}  question")
    print(f"  {'—'*64}")
    for qid, ch, sc, qtype in rows:
        q = questions[qid - 1]["question"][:60]
        print(f"  {qid:3d}  {ch:3d}  {sc:5d}  {qtype:<6}  {q}")
    print()


def print_crosstab(
    verdict_map: dict[tuple[int, int], str],
    scores: dict[tuple[int, int], int],
    labels: list[str],
    title: str,
    gold_by_qid: dict[int, set[int]],
) -> None:
    print(title)
    common = sorted(set(verdict_map) & set(scores))
    print(f"  ({len(common)} common pairs)\n")
    matrix: dict[str, Counter] = {label: Counter() for label in labels}
    for key in common:
        matrix[verdict_map[key]][scores[key]] += 1
    hdr = f"  {'verdict':>6}"
    for s in range(SCORE_MAX + 1):
        hdr += f" {s:4d}"
    hdr += "  total"
    print(hdr)
    print(f"  {'—' * (len(hdr) - 2)}")
    for label in labels:
        row = f"  {label:>6}"
        total = sum(matrix[label].values())
        for s in range(SCORE_MAX + 1):
            row += f" {matrix[label][s]:4d}"
        row += f" {total:5d}"
        print(row)
    # Gold-only breakdown.
    print("\n  gold chapters only:")
    gold_hdr = f"  {'verdict':>6}"
    for s in range(SCORE_MAX + 1):
        gold_hdr += f" {s:4d}"
    print(gold_hdr)
    print(f"  {'—' * (len(gold_hdr) - 2)}")
    for label in labels:
        counter = Counter()
        for key in common:
            if key[1] in gold_by_qid.get(key[0], set()) and verdict_map[key] == label:
                counter[scores[key]] += 1
        row = f"  {label:>6}"
        for s in range(SCORE_MAX + 1):
            row += f" {counter[s]:4d}"
        print(row)
    print()


def print_equivalence(
    f2: dict[tuple[int, int], str],
    f3: dict[tuple[int, int], str],
    f10i: dict[tuple[int, int], int],
    gold_by_qid: dict[int, set[int]],
    all_qids: list[int],
) -> None:
    print("Table 6 — retrieval metrics: filter2/3 keep rules vs filter10 thresholds")
    print("  (which filter10 threshold reproduces each filter variant?)\n")
    print(f"  {'rule':>22}  {'strict':>7}  {'partial':>8}  {'precision':>9}  {'avg_kept':>8}")
    print(f"  {'—'*60}")
    f2_keep = {k: v == "yes" for k, v in f2.items()}
    m2 = metrics_keep(f2_keep, gold_by_qid, all_qids)
    print(f"  {'filter2 (keep yes)':>22}  {m2['strict']:7.3f}  {m2['partial']:8.3f}  "
          f"{m2['precision']:9.3f}  {m2['avg_kept']:8.1f}")
    f3_keep = {k: v != "no" for k, v in f3.items()}
    m3 = metrics_keep(f3_keep, gold_by_qid, all_qids)
    print(f"  {'filter3 (keep != no)':>22}  {m3['strict']:7.3f}  {m3['partial']:8.3f}  "
          f"{m3['precision']:9.3f}  {m3['avg_kept']:8.1f}")
    for thr in range(0, SCORE_MAX + 2):
        m = metrics(f10i, gold_by_qid, thr, all_qids)
        print(f"  {'filter10 (>= %d)' % thr:>22}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
              f"{m['precision']:9.3f}  {m['avg_kept']:8.1f}")
    print()


def print_agreement(
    f2: dict[tuple[int, int], str],
    f3: dict[tuple[int, int], str],
    f10i: dict[tuple[int, int], int],
) -> None:
    def agreement(keep_a: dict, keep_b: dict) -> float:
        keys = sorted(set(keep_a) & set(keep_b))
        same = sum(1 for k in keys if keep_a[k] == keep_b[k])
        return same / len(keys) if keys else 0.0

    f2_keep = {k: v == "yes" for k, v in f2.items()}
    f3_keep = {k: v != "no" for k, v in f3.items()}
    print("Table 7 — agreement rate: filter10 keep/drop vs filter2/3 keep/drop")
    print("  (fraction of pairs where the two runs make the same keep/drop call)\n")
    print(f"  {'threshold':>22}  {'vs filter2':>10}  {'vs filter3':>10}")
    print(f"  {'—'*48}")
    for thr in range(0, SCORE_MAX + 2):
        f10_keep = {k: v >= thr for k, v in f10i.items()}
        a2 = agreement(f10_keep, f2_keep)
        a3 = agreement(f10_keep, f3_keep)
        print(f"  {'filter10 (>= %d)' % thr:>22}  {a2:10.3f}  {a3:10.3f}")
    print()


def print_score_summary(
    f2: dict[tuple[int, int], str],
    f3: dict[tuple[int, int], str],
    f10i: dict[tuple[int, int], int],
) -> None:
    common = sorted(set(f2) & set(f3) & set(f10i))

    def summary(verdict_map: dict, labels: list[str], title: str) -> None:
        print(f"  {title}:")
        for label in labels:
            vals = [f10i[k] for k in common if verdict_map[k] == label]
            vals_sorted = sorted(vals)
            n = len(vals)
            if n == 0:
                print(f"    {label:>6} (   0 pairs): (none)")
                continue
            median = vals_sorted[n // 2]
            mean = sum(vals) / n
            c = Counter(vals)
            mode = c.most_common(1)[0]
            print(f"    {label:>6} ({n:4d} pairs): mean={mean:5.2f}  "
                  f"median={median}  mode={mode[0]} (n={mode[1]})")

    print("Table 8 — filter10 score summary per filter2/3 verdict label\n")
    summary(f2, ["yes", "no"], "filter2 verdict → filter10 score")
    summary(f3, ["yes", "maybe", "no"], "filter3 verdict → filter10 score")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/results paths)")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (default: questions-<lang>.jsonl)")
    args = parser.parse_args()

    lang = args.lang
    questions_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"

    questions = load_questions(questions_path)
    gold_by_qid = {qid: set(q["chapters"]) for qid, q in enumerate(questions, start=1)}
    all_qids = list(range(1, len(questions) + 1))
    print(f"Questions: {len(questions)} ({questions_path})")

    # filter10 scores (required).
    f10 = load_verdicts(lang, "filter10")
    if not f10:
        parser.error(f"no filter10 part TSVs found in results-{lang}/ — "
                     f"run `make filter10-parts LANG={lang}` first.")
    f10i = {k: int(v) for k, v in f10.items()}
    total = len(f10i)
    n_chapters = len({ch for _, ch in f10i})
    print(f"filter10: {total} (chapter, question) pairs ({n_chapters} chapters)\n")

    # Tables 1-4: filter10 alone.
    print_score_distribution(f10i, gold_by_qid)
    print_threshold_sweep(f10i, gold_by_qid, questions, all_qids)
    print_low_score_gold(f10i, gold_by_qid, questions)

    # Tables 5-8: crosstabs against filter2/filter3 (if present).
    f2 = load_verdicts(lang, "filter2")
    f3 = load_verdicts(lang, "filter3")
    if not f2 and not f3:
        print("(filter2/filter3 part TSVs not found — skipping crosstabs Tables 5-8)\n")
        return

    if f2:
        print_crosstab(
            f2, f10i, ["yes", "no"],
            "Table 5a — filter2 verdict × filter10 score",
            gold_by_qid)
    if f3:
        print_crosstab(
            f3, f10i, ["yes", "maybe", "no"],
            "Table 5b — filter3 verdict × filter10 score",
            gold_by_qid)
    if f2 and f3:
        print_equivalence(f2, f3, f10i, gold_by_qid, all_qids)
        print_agreement(f2, f3, f10i)
        print_score_summary(f2, f3, f10i)


if __name__ == "__main__":
    main()
