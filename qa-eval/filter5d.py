#!/usr/bin/env python3
"""Analyze the five-axis (5d) relevance scores against gold chapters.

Standalone analysis, independent of the answering pipeline — no LLM, no answer
synthesis, no output file (terminal tables only, like ``filter.py`` and
``sweep_rag.py``). It reads the Phase 1 verdict TSV produced by
``answer_filter.py --verdicts 5d`` and the gold chapters from
``questions-<lang>.jsonl`` to answer the three questions posed in
[PLAN.md](PLAN.md) for the 5d variant:

   1. **The floor** — how many gold pairs land at sum=0 (all five axes zero)?
      This is the design goal: decomposition should collapse the gold-scored-0
      floor that single-axis variants (filter10: 7/86, filter100: 11/86) cannot
      reach.
   2. **Sum distribution** — does a threshold separate gold from non-gold, or
      does it binarize to "sum=0 vs sum>0"?
   3. **Per-axis distribution** — gold vs non-gold per axis: which axes carry
      the gold signal, and which are redundant?

Requires ``filter5d.tsv``. Run::

    make filter5d              # builds filter5d.tsv if missing, then runs this
    make filter5d LANG=ja      # Japanese

Note on "recall": ``report.py`` uses strict subset recall (1 iff gold ⊆ used).
This script reports both strict subset recall AND partial coverage (the fraction
of gold chapters kept) so the threshold trade-off is visible as a curve, and
also **excess** (non-gold chapters kept) since the design posture is "absence
is the failure, surfeit is not."
"""

import argparse
import itertools
import math
from collections import Counter
from pathlib import Path

from answer import ROOT, LANGS, load_questions
from answer_filter import read_verdict_5d_tsv, AXES

QA_EVAL = Path(__file__).resolve().parent


def load_5d_scores(lang: str) -> dict[tuple[int, int], dict[str, int]]:
    """Load filter5d.tsv into {(qid, chapter): {axis: int}}.

    Returns an empty dict if the file does not exist.
    """
    out: dict[tuple[int, int], dict[str, int]] = {}
    path = QA_EVAL / f"results-{lang}" / "filter5d.tsv"
    if path.exists():
        for ch, qid, scores in read_verdict_5d_tsv(path):
            out[(qid, ch)] = scores
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


def evaluate(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
    qids: list[int],
    keep_fn,
) -> dict[str, float]:
    """Retrieval metrics for an arbitrary keep rule.

    keep_fn(qid, ch, scores_dict) -> bool.

    strict    — fraction of questions where gold ⊆ kept.
    partial   — mean fraction of gold chapters kept (coverage curve).
    precision — mean |gold ∩ kept| / |kept|.
    avg_kept  — mean chapters kept per question.
    excess    — total non-gold chapters kept (sum over questions).
    """
    strict = 0
    partial_sum = 0.0
    kept_total = 0
    gold_kept = 0
    for qid in qids:
        gold = gold_by_qid[qid]
        kept = {ch for (q, ch), sc in scores.items()
                if q == qid and keep_fn(qid, ch, sc)}
        kept_total += len(kept)
        gold_kept += len(gold & kept)
        if gold and gold.issubset(kept):
            strict += 1
        if gold:
            partial_sum += len(gold & kept) / len(gold)
    n = len(qids)
    excess = kept_total - gold_kept
    return {
        "strict": strict / n if n else 0.0,
        "partial": partial_sum / n if n else 0.0,
        "precision": gold_kept / kept_total if kept_total else 0.0,
        "avg_kept": kept_total / n if n else 0.0,
        "excess": excess,
    }


def axis_sum(sc: dict[str, int]) -> int:
    return sum(sc.values())


# ---------------------------------------------------------------------------
# Table printers
# ---------------------------------------------------------------------------

def print_sum_distribution(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
) -> None:
    """Table 1 — 5-axis sum distribution (all chapter-question pairs)."""
    total = len(scores)
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))

    sum_gold: Counter = Counter()
    sum_nongold: Counter = Counter()
    for (qid, ch), sc in scores.items():
        s = axis_sum(sc)
        if ch in gold_by_qid.get(qid, set()):
            sum_gold[s] += 1
        else:
            sum_nongold[s] += 1

    max_sum = max((axis_sum(sc) for sc in scores.values()), default=0)

    print(f"Table 1 — 5-axis sum distribution ({total} pairs, {n_gold} gold, "
          f"{total - n_gold} non-gold)\n")
    print(f"  {'sum':>4}  {'count':>5}  {'pct':>5}  {'gold':>4}  {'ngold':>5}  "
          f"{'gold%':>6}  bar (gold=#, non-gold=:)")
    print(f"  {'—' * 64}")
    for s in range(0, max_sum + 1):
        g = sum_gold.get(s, 0)
        ng = sum_nongold.get(s, 0)
        cnt = g + ng
        pct = cnt / total * 100 if total else 0
        share = g / cnt * 100 if cnt else 0
        bar = "#" * g + (":" * min(ng, 50) if ng else "")
        if cnt:
            print(f"  {s:>4}  {cnt:>5}  {pct:4.1f}%  {g:>4}  {ng:>5}  "
                  f"{share:5.1f}%  {bar}")

    gold_sums = [axis_sum(sc) for (qid, ch), sc in scores.items()
                 if ch in gold_by_qid.get(qid, set())]
    ng_sums = [axis_sum(sc) for (qid, ch), sc in scores.items()
               if ch not in gold_by_qid.get(qid, set())]
    n_floor = sum(1 for s in gold_sums if s == 0)
    print(f"\n  gold:     min={min(gold_sums):>3}  max={max(gold_sums):>3}  "
          f"mean={sum(gold_sums) / len(gold_sums):.1f}  "
          f"({n_floor} gold pairs at sum=0)")
    print(f"  non-gold: min={min(ng_sums):>3}  max={max(ng_sums):>3}  "
          f"mean={sum(ng_sums) / len(ng_sums):.1f}")
    print()


def print_sum_sweep(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
    questions: list[dict],
    all_qids: list[int],
) -> None:
    """Table 2 — sum threshold sweep + Table 3 per-type breakdown."""
    scopes = scopes_from_questions(questions)
    thresholds = list(range(0, 22))

    print("Table 2 — sum threshold sweep: keep chapters with sum >= threshold")
    print(f"\n  {'thr':>4}  {'strict':>7}  {'partial':>8}  {'precision':>9}  "
          f"{'F1':>5}  {'avg_kept':>8}  {'excess':>6}")
    print(f"  {'—' * 58}")
    for thr in thresholds:
        m = evaluate(scores, gold_by_qid, all_qids,
                     lambda qid, ch, sc, t=thr: axis_sum(sc) >= t)
        denom = m["partial"] + m["precision"]
        f1 = 2 * m["partial"] * m["precision"] / denom if denom else 0.0
        print(f"  {thr:>4}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
              f"{m['precision']:9.3f}  {f1:5.3f}  {m['avg_kept']:8.1f}  "
              f"{m['excess']:>6}")
    print()

    print("Table 3 — strict subset recall by question type")
    for scope_name, subset in scopes:
        if subset is None:
            continue
        qids = sorted(subset)
        n = len(qids)
        if n == 0:
            continue
        print(f"\n  {scope_name} ({n} questions):")
        print(f"    {'thr':>4}  {'strict':>7}  {'partial':>8}  {'precision':>9}  "
              f"{'avg_kept':>8}  {'excess':>6}")
        print(f"    {'—' * 54}")
        for thr in thresholds:
            m = evaluate(scores, gold_by_qid, qids,
                         lambda qid, ch, sc, t=thr: axis_sum(sc) >= t)
            print(f"    {thr:>4}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
                  f"{m['precision']:9.3f}  {m['avg_kept']:8.1f}  {m['excess']:>6}")
    print()


def print_floor_and_boundary(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
    questions: list[dict],
    n_boundary: int = 15,
) -> None:
    """Table 4 — floor (gold at sum=0) and boundary gold pairs (lowest sums)."""
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))
    floor = []
    gold_list = []
    for (qid, ch), sc in sorted(scores.items()):
        if ch not in gold_by_qid.get(qid, set()):
            continue
        s = axis_sum(sc)
        gold_list.append((s, qid, ch, sc, questions[qid - 1].get("type", "all")))
        if s == 0:
            floor.append((qid, ch, sc))

    print(f"Table 4 — floor and boundary gold pairs")
    print(f"  gold pairs at sum=0: {len(floor)} / {n_gold}\n")

    gold_list.sort()
    print(f"  {n_boundary} lowest-sum gold pairs:\n")
    print(f"  {'qid':>3}  {'ch':>3}  {'type':>6}  {'sum':>4}  "
          + "  ".join(f"{a[:4]:>4}" for a in AXES) + "  question")
    print(f"  {'—' * 80}")
    for s, qid, ch, sc, qt in gold_list[:n_boundary]:
        q = questions[qid - 1]["question"][:40]
        axes_str = "  ".join(f"{sc[a]:>4}" for a in AXES)
        print(f"  {qid:>3}  {ch:>3}  {qt:>6}  {s:>4}  {axes_str}  {q}")
    print()


def print_axis_distribution(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
) -> None:
    """Table 5 — per-axis score distribution (gold vs non-gold)."""
    print("Table 5 — per-axis score distribution (gold vs non-gold)\n")
    header = (f"  {'axis':>10}  {'side':>8}  "
              + "  ".join(f"{i:>4}" for i in range(11))
              + f"  {'g_min':>5}")
    print(header)
    print(f"  {'—' * 78}")
    for axis in AXES:
        for side, predicate in [("gold", True), ("non-gold", False)]:
            counter = Counter()
            for (qid, ch), sc in scores.items():
                is_gold = ch in gold_by_qid.get(qid, set())
                if is_gold == predicate:
                    counter[sc[axis]] += 1
            row = "  ".join(f"{counter[i]:>4}" for i in range(11))
            gmin = min(counter.elements()) if counter else "-"
            print(f"  {axis:>10}  {side:>8}  {row}  {gmin:>5}")
        print()


def print_axis_contribution(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
) -> None:
    """Table 6 — per-axis contribution to gold detection.

    For each axis:
    - gold_above0 / non-gold_above0: how many pairs have signal on this axis.
    - noise_ratio: fraction of the axis's total score going to non-gold.
    - single-axis survival: keep if axis > 0 → gold kept, gold lost, excess.
    - axis indispensability: gold pairs that fall to sum=0 if this axis removed.
    """
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))
    n_questions = len({qid for qid, _ in scores})

    print("Table 6 — per-axis contribution to gold detection\n")
    print(f"  {'axis':>10}  {'gold>0':>6}  {'ngold>0':>7}  {'noise':>5}  "
          f"{'if axis>0:':>9}  {'gold_kept':>9}  {'gold_lost':>9}  {'excess':>6}  "
          f"{'lost_if_dropped':>15}")
    print(f"  {'—' * 90}")

    for axis in AXES:
        gold_above0 = 0
        nongold_above0 = 0
        gold_total = 0
        nongold_total = 0
        for (qid, ch), sc in scores.items():
            is_gold = ch in gold_by_qid.get(qid, set())
            if sc[axis] > 0:
                if is_gold:
                    gold_above0 += 1
                else:
                    nongold_above0 += 1
            if is_gold:
                gold_total += sc[axis]
            else:
                nongold_total += sc[axis]
        noise = nongold_total / (gold_total + nongold_total) if (gold_total + nongold_total) else 0

        # Single-axis survival: keep if axis > 0
        kept_gold = gold_above0
        lost_gold = n_gold - gold_above0
        excess = nongold_above0

        # Indispensability: gold pairs that fall to sum=0 if this axis removed
        lost_if_dropped = 0
        for (qid, ch), sc in scores.items():
            if ch not in gold_by_qid.get(qid, set()):
                continue
            s_without = sum(v for a, v in sc.items() if a != axis)
            if axis_sum(sc) > 0 and s_without == 0:
                lost_if_dropped += 1

        print(f"  {axis:>10}  {gold_above0:>6}  {nongold_above0:>7}  "
              f"{noise:4.2f}  {'':>9}  {kept_gold:>9}  {lost_gold:>9}  "
              f"{excess:>6}  {lost_if_dropped:>15}")
    print()


def print_axis_redundancy(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
) -> None:
    """Table 7 — axis redundancy: drop one axis, recompute floor + excess.

    For each dropped axis, recompute the sum over the remaining four axes and
    check whether the floor (gold at sum=0) or the sum>=5 threshold changes.
    Reveals which axes are structurally redundant for the keep decision.
    """
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))

    print("Table 7 — axis redundancy: drop one axis from the sum\n")
    print(f"  {'dropped':>10}  {'floor':>5}  {'gold<5':>6}  "
          f"{'excess(sum>0)':>13}  {'excess(sum>=5)':>14}")
    print(f"  {'—' * 54}")

    # Baseline: full 5-axis sum
    floor = sum(1 for (qid, ch), sc in scores.items()
                if ch in gold_by_qid.get(qid, set()) and axis_sum(sc) == 0)
    gold_lt5 = sum(1 for (qid, ch), sc in scores.items()
                   if ch in gold_by_qid.get(qid, set()) and axis_sum(sc) < 5)
    exc_gt0 = sum(1 for (qid, ch), sc in scores.items()
                  if ch not in gold_by_qid.get(qid, set()) and axis_sum(sc) > 0)
    exc_ge5 = sum(1 for (qid, ch), sc in scores.items()
                  if ch not in gold_by_qid.get(qid, set()) and axis_sum(sc) >= 5)
    print(f"  {'(none)':>10}  {floor:>5}  {gold_lt5:>6}  "
          f"{exc_gt0:>13}  {exc_ge5:>14}")

    for drop in AXES:
        kept = [a for a in AXES if a != drop]
        floor = 0
        gold_lt5 = 0
        exc_gt0 = 0
        exc_ge5 = 0
        for (qid, ch), sc in scores.items():
            s = sum(sc[a] for a in kept)
            is_gold = ch in gold_by_qid.get(qid, set())
            if is_gold:
                if s == 0:
                    floor += 1
                if s < 5:
                    gold_lt5 += 1
            else:
                if s > 0:
                    exc_gt0 += 1
                if s >= 5:
                    exc_ge5 += 1
        print(f"  {drop:>10}  {floor:>5}  {gold_lt5:>6}  "
              f"{exc_gt0:>13}  {exc_ge5:>14}")
    print()


def print_alt_rules(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
    all_qids: list[int],
) -> None:
    """Table 8 — alternative keep rules: max(axis) and non-zero-axis count."""
    print("Table 8 — alternative keep rules\n")

    print("  max(axis) >= threshold (any one axis fires):")
    print(f"    {'thr':>4}  {'strict':>7}  {'partial':>8}  {'precision':>9}  "
          f"{'avg_kept':>8}  {'excess':>6}")
    print(f"    {'—' * 54}")
    for thr in range(1, 6):
        m = evaluate(scores, gold_by_qid, all_qids,
                     lambda qid, ch, sc, t=thr: max(sc.values()) >= t)
        print(f"    {thr:>4}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
              f"{m['precision']:9.3f}  {m['avg_kept']:8.1f}  {m['excess']:>6}")
    print()

    print("  non-zero-axis count >= n (majority vote):")
    print(f"    {'n':>4}  {'strict':>7}  {'partial':>8}  {'precision':>9}  "
          f"{'avg_kept':>8}  {'excess':>6}")
    print(f"    {'—' * 54}")
    for n in range(1, 6):
        m = evaluate(scores, gold_by_qid, all_qids,
                     lambda qid, ch, sc, n=n: sum(1 for v in sc.values() if v > 0) >= n)
        print(f"    {n:>4}  {m['strict']:7.3f}  {m['partial']:8.3f}  "
              f"{m['precision']:9.3f}  {m['avg_kept']:8.1f}  {m['excess']:>6}")
    print()


def print_or_search(
    scores: dict[tuple[int, int], dict[str, int]],
    gold_by_qid: dict[int, set[int]],
    all_qids: list[int],
    n_results: int = 10,
) -> None:
    """Table 9 — OR combination search: per-axis thresholds that keep all gold.

    Searches every combination of per-axis thresholds (each 1–5) for the OR
    rule "keep if ANY axis >= its threshold." Among combinations that preserve
    full gold inclusion (strict = 1.0), sorts by excess ascending.

    This is an upper-bound exploration, NOT a recommended rule: fitting five
    thresholds simultaneously to the 86-pair gold set is fitting the metric,
    not learning a generalizable rule. The results are reported so the reader
    can see the gap between the best possible OR rule and the simpler sum
    threshold. See filter5d.md ("OR combination: an upper bound, not a rule").
    """
    THRESHOLDS = list(range(1, 6))
    n_questions = len(all_qids)

    gold_keys = [(qid, ch) for (qid, ch) in scores
                 if ch in gold_by_qid.get(qid, set())]

    results = []
    for thresholds in itertools.product(THRESHOLDS, repeat=len(AXES)):
        all_gold_caught = True
        for (qid, ch) in gold_keys:
            sc = scores[(qid, ch)]
            if not any(sc[AXES[i]] >= thresholds[i] for i in range(len(AXES))):
                all_gold_caught = False
                break
        if not all_gold_caught:
            continue

        m = evaluate(
            scores, gold_by_qid, all_qids,
            lambda qid, ch, sc, t=thresholds:
                any(sc[AXES[i]] >= t[i] for i in range(len(AXES))),
        )
        results.append((m["excess"], m["avg_kept"], thresholds))

    results.sort(key=lambda x: (x[0], x[1]))

    print("Table 9 — OR combination search: per-axis thresholds (any axis fires)")
    print("  NOTE: fitting 5 thresholds to the known gold set is overfitting;")
    print("  this is an upper bound, not a recommended rule. See filter5d.md.\n")

    if not results:
        print("  (no combination with full gold inclusion found)\n")
        return

    print(f"  {len(results)} combinations preserve full gold (strict="
          f"{n_questions}); top {min(n_results, len(results))} by excess:\n")
    print(f"  {'rank':>4}  {'excess':>6}  {'avg_kept':>8}  "
          + "  ".join(f"{a[:4]:>4}" for a in AXES))
    print(f"  {'—' * 62}")
    for rank, (excess, avg_kept, thresholds) in enumerate(results[:n_results], 1):
        thr_str = "  ".join(f">={t:>3}" for t in thresholds)
        print(f"  {rank:>4}  {excess:>6}  {avg_kept:>8.1f}  {thr_str}")

    m5 = evaluate(scores, gold_by_qid, all_qids,
                  lambda qid, ch, sc: axis_sum(sc) >= 5)
    best_excess = results[0][0]
    improvement = (m5["excess"] - best_excess) / m5["excess"] * 100
    print(f"\n  Baseline sum >= 5: excess={m5['excess']}  avg_kept={m5['avg_kept']:.1f}")
    print(f"  Best OR rule:      excess={best_excess}  "
          f"({improvement:.1f}% less excess than sum >= 5)\n")


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

    scores = load_5d_scores(lang)
    if not scores:
        parser.error(f"no filter5d.tsv found in results-{lang}/ — "
                     f"run `make filter5d-tsv LANG={lang}` first.")

    total = len(scores)
    n_chapters = len({ch for _, ch in scores})
    n_gold = sum(1 for (qid, ch) in scores if ch in gold_by_qid.get(qid, set()))
    print(f"filter5d: {total} (chapter, question) pairs ({n_chapters} chapters, "
          f"{n_gold} gold)\n")

    print_sum_distribution(scores, gold_by_qid)
    print_sum_sweep(scores, gold_by_qid, questions, all_qids)
    print_floor_and_boundary(scores, gold_by_qid, questions)
    print_axis_distribution(scores, gold_by_qid)
    print_axis_contribution(scores, gold_by_qid)
    print_axis_redundancy(scores, gold_by_qid)
    print_alt_rules(scores, gold_by_qid, all_qids)
    print_or_search(scores, gold_by_qid, all_qids)


if __name__ == "__main__":
    main()
