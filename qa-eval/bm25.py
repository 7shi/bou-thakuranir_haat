#!/usr/bin/env python3
"""BM25/lexical retrieval standalone analysis (complements sweep_vector.py).

Sibling of ``sweep_vector.py``: same shape of analysis, no LLM, no output file —
terminal tables only. Where ``sweep_vector.py`` ranks scenes by **cosine** on the
dense embedding index and asks "does dense retrieval surface the gold
chapters?", this script ranks the same scenes by **BM25** on the literal scene
text and asks the same question. Reading the two side by side answers the
question — does sparse lexical matching recover the chapters dense
retrieval drops (the signet ring, the Emperor of Delhi, Muktiyar Khan's
assassination — the low-frequency proper nouns that embeddings wash out)?

The retrieval unit is a **scene** (segment), identical to Vector RAG and
``sweep_vector.py``, so chapter coverage@k and the per-question first-gold-rank are
directly comparable across the two retrievers.

Per FILTER.md's Verdict, the Ceiling run scores 0.990 — once the gold chapters
reach the answerer the answer follows — so a retrieval method is judged on a
single axis: does it surface the gold chapters? No Phase 2 QA run is required,
which is why this script (like ``sweep_vector.py``) is pure ranking analysis.

The BM25 implementation is pure stdlib (``re`` + ``collections`` + ``math``),
no external dependency — BM25 is ~30 lines and understanding the algorithm is
part of the experimental goal. The ranking functions (``BM25Index``,
``rank_all_scenes``) are importable so ``hybrid.py`` (fusion analysis) and
``answer_hybrid.py`` (Phase 2 QA) reuse them without reimplementing.

Prints five terminal tables:
  1. Chapter coverage@k by scope (all/single/cross) — the headline metric.
  2. Per-question gold coverage at k=5 and k=10 (x/y form) — the row-level view
     of which questions each depth covers and which it drops.
  3. BM25-score threshold sweep with the best global tau*.
  4. Per-question gold ranks and separation gap.
  5. BM25 rank for the gold chapters in the known dense-retrieval misses
     (the dense-miss residual gap) — the direct "does BM25 recover what dense
     dropped?" view that motivates the hybrid.

Tokenization is English-only (lowercase + ``[a-z0-9]+`` + stopword removal);
no morphology. The ``tokenize()`` ``lang`` switch is a placeholder so a future
Japanese branch (with morphological analysis) can plug in without changing call
sites — Japanese is explicitly deferred per the current scope.
"""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from answer import ROOT, LANGS, load_questions

QA_EVAL = Path(__file__).resolve().parent

# k columns shown in the coverage table (last entry = whole index, always 1.0).
# Identical to sweep_vector.py so the coverage@k curves read side by side.
K_COLS = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 82]

# Questions where dense (cosine top-5) retrieval dropped a gold chapter in the
# English sweep_vector.py run — the six "genuine retrieval misses" from the
# results-en case study (Q27, Q28, Q31, Q36, Q43, Q45) plus Q49 (Ch22 missed,
# the Emperor of Delhi). Source: results-en/README.md "Both wrong" section and
# HYBRID.md. Table 4 cross-references BM25's rank for the gold chapters in
# these questions; this constant is analysis-only (no pipeline data dependency).
DENSE_MISSES = [27, 28, 31, 36, 43, 45, 49]

# Percentile grid used to choose BM25-score threshold ticks for Table 2. Unlike
# cosine, BM25 scores are unbounded and long-tailed (most scenes score 0, a few
# score high), so a fixed grid like sweep_vector.py's [0.25, 0.75] is meaningless;
# percentiles of the pooled score distribution give interpretable ticks. The
# best tau* is located separately on a fine linear grid.
TAU_PERCENTILES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]


# ---------------------------------------------------------------------------
# Scene loaders
# ---------------------------------------------------------------------------
# Copied from build_index.py rather than imported: build_index.py's module-level
# imports pull in ollama/tqdm/safetensors for the embedding pass, which BM25
# does not use. The same pattern (copy small helpers to avoid a heavy import)
# is used by filter.py (see its scopes_from_questions at filter.py:60).

def load_titles(tsv_path: Path) -> dict[tuple[int, int], str]:
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


def load_scenes(jsonl_path: Path, titles) -> list[dict]:
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


# ---------------------------------------------------------------------------
# Tokenization (English-only; no morphology)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Compact English stopword list — the high-frequency function words that BM25's
# IDF already down-weights heavily. Removing them speeds scoring a little and
# sharpens the signal on content words (named entities, objects) that this
# experiment cares about. Toggle off with --no-stopwords for ablation.
STOPWORDS = frozenset("""
a an and are as at be but by for from had has have he her here him his how i
if in into is it its no not of on or our so such than that the their them then
there these they this to was we were what when where which who will with would
you your
""".split())


_nlp_ja = None


def get_nlp_ja():
    global _nlp_ja
    if _nlp_ja is None:
        import spacy
        _nlp_ja = spacy.load("ja_core_news_sm")
    return _nlp_ja


def tokenize(text: str, lang: str = "en", remove_stop: bool = True) -> list[str]:
    """Lowercase + alphanumeric token extraction.

    Japanese morphological analysis uses spaCy (ja_core_news_sm).
    """
    if lang == "ja":
        nlp = get_nlp_ja()
        doc = nlp(text)
        # Extract nouns, proper nouns, verbs, adjectives, and adverbs
        allowed_pos = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
        tokens = [t.text.lower() for t in doc if t.pos_ in allowed_pos]
        if remove_stop:
            # Simple cleanup for Japanese tokens
            tokens = [t for t in tokens if not t.isspace()]
        return tokens
    elif lang == "en":
        tokens = _TOKEN_RE.findall(text.lower())
        if remove_stop:
            tokens = [t for t in tokens if t not in STOPWORDS]
        return tokens
    else:
        raise NotImplementedError(
            f"tokenize: lang={lang!r} not implemented")


# ---------------------------------------------------------------------------
# BM25 (pure stdlib)
# ---------------------------------------------------------------------------

class BM25Index:
    """Okapi BM25 over a fixed corpus of tokenized documents.

    Built once from the scene corpus; ``score_query`` returns a BM25 score for
    every document against the query (higher = more relevant). Uses the
    Lucene/Elasticsearch IDF variant — ``ln(1 + (N - n + 0.5) / (n + 0.5))`` —
    so IDF (and hence scores) are always non-negative even for terms that
    appear in nearly every document.

    Parameters k1 and b are the standard Okapi defaults (1.5, 0.75): k1 caps
    term-frequency saturation, b controls length normalization (0 = none,
    1 = full).
    """

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.n_docs = len(docs)
        self.doc_len = [len(d) for d in docs]
        self.avgdl = (sum(self.doc_len) / self.n_docs) if self.n_docs else 0.0
        self.tf: list[Counter] = [Counter(d) for d in docs]
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        self.idf: dict[str, float] = {
            t: math.log(1.0 + (self.n_docs - n + 0.5) / (n + 0.5))
            for t, n in df.items()
        }

    def score_query(self, query_tokens: list[str]) -> list[float]:
        """Return a BM25 score for every document, in corpus order."""
        q_counts = Counter(query_tokens)
        scores = [0.0] * self.n_docs
        for term in q_counts:
            idf = self.idf.get(term)
            if idf is None:
                continue  # term absent from the corpus contributes 0
            k1 = self.k1
            b = self.b
            avgdl = self.avgdl
            for i in range(self.n_docs):
                f = self.tf[i].get(term, 0)
                if f == 0:
                    continue
                denom = f + k1 * (1.0 - b + b * self.doc_len[i] / avgdl)
                scores[i] += idf * (f * (k1 + 1.0)) / denom
        return scores


# ---------------------------------------------------------------------------
# Ranking record (mirrors sweep_vector.py:rank_all_scenes)
# ---------------------------------------------------------------------------

def rank_all_scenes(
    bm25: BM25Index,
    query_tokens: list[str],
    scenes: list[dict],
    gold: set[int],
) -> dict:
    """Score the query against every scene and return a ranked record.

    Same record shape as ``sweep_vector.py:rank_all_scenes`` so the analysis
    helpers below operate uniformly on either retriever's output. ``ranked``
    is the full list of scenes sorted by score descending; ties keep scene
    order (stable sort), which for scenes in chapter/segment order means
    equal-score scenes break ties in narrative order.
    """
    scores = bm25.score_query(query_tokens)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
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


# ---------------------------------------------------------------------------
# Analysis helpers (copied from sweep_vector.py — see note at load_titles above)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

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
    # Tie-back to report.py: strict subset recall and precision at k=5 (same as
    # sweep_vector.py's k=5 tie-back, for direct dense-vs-BM25 comparison).
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
    pos_arr = [float(x) for x in pos]
    neg_arr = [float(x) for x in neg]
    all_arr = pos_arr + neg_arr
    total_pos = len(pos_arr)
    total_neg = len(neg_arr)

    def prf(tau: float) -> tuple[float, float, float, int, int]:
        tp = sum(1 for x in pos_arr if x >= tau)
        fp = sum(1 for x in neg_arr if x >= tau)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / total_pos if total_pos else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1, tp, fp

    all_sorted = sorted(all_arr)

    def pct(p: float) -> float:
        idx = int(p / 100.0 * (len(all_sorted) - 1))
        return all_sorted[idx]

    print("Table 3 — BM25 score threshold sweep  (positive iff scene.chapter in gold)")
    print(f"  pool: {total_pos} positive, {total_neg} negative scene-pairs")
    print(f"  ticks at percentiles of the pooled BM25-score distribution "
          f"(unbounded, long-tailed — not a fixed grid like cosine)")
    print(f"{'tau':>8} {'pct':>4} {'precision':>9} {'recall':>7} {'F1':>5} {'tp':>5} {'fp':>5}")
    print("-" * 46)
    display_taus = sorted({pct(p) for p in TAU_PERCENTILES})
    for tau in display_taus:
        p, r, f1, tp, fp = prf(tau)
        # find the percentile label for this tau (nearest grid point)
        pct_label = next((str(pt) for pt in TAU_PERCENTILES if pct(pt) == tau), "")
        print(f"{tau:>8.3f} {pct_label:>4} {p:>9.3f} {r:>7.3f} {f1:>5.2f} {tp:>5} {fp:>5}")

    # Fine linear grid for best tau* (F1).
    lo, hi = all_sorted[0], all_sorted[-1]
    best_tau, best_f1 = lo, -1.0
    step = (hi - lo) / 400 if hi > lo else 1.0
    tau = lo
    while tau <= hi:
        _, _, f1, _, _ = prf(tau)
        if f1 > best_f1:
            best_f1, best_tau = f1, tau
        tau += step
    p, r, f1, tp, fp = prf(best_tau)
    print("-" * 46)
    print(f"best tau*={best_tau:.3f}  precision={p:.3f} recall={r:.3f} F1={f1:.2f} "
          f"(tp={tp}, fp={fp})")
    print("  cf. sweep_vector.py cosine: best tau*≈0.50, F1≈0.38 (a global cosine "
          "threshold barely separates).")
    print()


def print_per_question_table(records: dict[int, dict]) -> None:
    print("Table 4 — per-question: first gold rank, best gold score, separation gap")
    print("  gap = (best gold-chapter score) − (best non-gold score ranked BELOW it)")
    print("  gap > 0  → a threshold could isolate the gold hit; gap < 0 → entangled.")
    print(f"{'qid':>3} {'type':<6} {'gold':<10} {'1stAu':>5} {'score':>7} {'gap':>7}   per-chapter best rank")
    print("-" * 78)
    for qid in sorted(records):
        rec = records[qid]
        ranked = rec["ranked"]
        gold = set(rec["gold_chapters"])
        first = rec["gold_first_rank"]
        if first is None:
            print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<10} "
                  f"{'-':>5} {'-':>7} {'-':>7}   {rec['gold_chapter_best_rank']}")
            continue
        best_gold_score = ranked[first - 1]["score"]
        # Best non-gold scene ranked strictly below the first gold hit.
        below_nongold = next((h["score"] for h in ranked[first:] if h["chapter"] not in gold), None)
        gap = best_gold_score - below_nongold if below_nongold is not None else None
        gap_s = f"{gap:>+7.3f}" if gap is not None else "      -"
        flag = " *" if first > 5 else ""
        print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<10} {first:>5} "
              f"{best_gold_score:>7.3f} {gap_s}   {rec['gold_chapter_best_rank']}{flag}")
    print("  (* = first gold hit outside current k=5 — a BM25 retrieval miss under the default setting)")
    print()


def print_dense_miss_table(records: dict[int, dict], questions: list[dict]) -> None:
    print("Table 5 — BM25 rank for gold chapters dense (cosine) retrieval dropped")
    print("  dense misses from results-en sweep_vector.py: "
          + ", ".join(f"Q{q}" for q in DENSE_MISSES))
    print("  ✓ = BM25 surfaces the gold chapter at k≤5 (recovers dense's miss);")
    print("      k≤10 is the k=10 parity bar; beyond k=15 BM25 has not helped.")
    print(f"{'qid':>3} {'type':<6} {'gold':<10} {'1stAu':>5} {'recovered@':>11}   per-chapter best rank")
    print("-" * 78)
    n_recovered_5 = 0
    n_recovered_10 = 0
    for qid in DENSE_MISSES:
        rec = records[qid]
        gold = set(rec["gold_chapters"])
        first = rec["gold_first_rank"]
        if first is None:
            tag = "—"
        else:
            if first <= 5:
                tag = "k≤5 ✓"
                n_recovered_5 += 1
            elif first <= 10:
                tag = "k≤10"
                n_recovered_10 += 1
            elif first <= 15:
                tag = "k≤15"
            else:
                tag = f"k={first}"
        first_s = f"{first:>5}" if first is not None else f"{'-':>5}"
        q = questions[qid - 1]["question"][:46]
        print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<10} {first_s} "
              f"{tag:>11}   {rec['gold_chapter_best_rank']}   {q}")
    print()
    total = len(DENSE_MISSES)
    print(f"  BM25 recovers {n_recovered_5}/{total} dense misses at k≤5, "
          f"{n_recovered_5 + n_recovered_10}/{total} at k≤10.")
    print()


def print_per_question_coverage_table(records: dict[int, dict]) -> None:
    """Per-question gold coverage at k=5 and k=10 in x/y form.

    For each question: ``|gold ∩ top-k chapters| / |gold|`` at k=5 and k=10.
    ``✓`` marks questions where every gold chapter surfaced (strict recall —
    the report.py notion). This is the row-level view behind Table 1's means:
    which questions each depth fully covers, and which it drops.
    """
    print("Table 2 — per-question gold coverage at k=5 and k=10  (covered / total gold)")
    print(f"{'qid':>3} {'type':<6} {'gold':<16} {'k=5':>8} {'k=10':>8}")
    print("-" * 46)
    cov5_total = cov10_total = gold_total = 0
    strict5 = strict10 = 0
    for qid in sorted(records):
        rec = records[qid]
        gold = set(rec["gold_chapters"])
        n_gold = len(gold)
        gold_total += n_gold
        top5 = {h["chapter"] for h in rec["ranked"][:5]}
        top10 = {h["chapter"] for h in rec["ranked"][:10]}
        c5 = len(gold & top5)
        c10 = len(gold & top10)
        cov5_total += c5
        cov10_total += c10
        if c5 == n_gold:
            strict5 += 1
        if c10 == n_gold:
            strict10 += 1
        f5 = " ✓" if c5 == n_gold else ""
        f10 = " ✓" if c10 == n_gold else ""
        print(f"{qid:>3} {rec['type']:<6} {str(sorted(gold)):<16} "
              f"{f'{c5}/{n_gold}':>5}{f5:<2} {f'{c10}/{n_gold}':>5}{f10}")
    print("-" * 46)
    print(f"{'totals':>3} {'':6} {f'{gold_total} gold pairs':<16} "
          f"{f'{cov5_total}/{gold_total}':>5}    {f'{cov10_total}/{gold_total}':>5}")
    print()
    print(f"  global coverage (Σcovered / Σgold):  k=5 {cov5_total}/{gold_total} "
          f"= {cov5_total/gold_total:.3f},  k=10 {cov10_total}/{gold_total} "
          f"= {cov10_total/gold_total:.3f}")
    print(f"  strict recall    (gold ⊆ top-k):      k=5 {strict5}/50,  "
          f"k=10 {strict10}/50")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--lang", default="en", choices=sorted(LANGS),
                        help="evaluation language (selects default questions/scenes/tsv paths)")
    parser.add_argument("--k1", type=float, default=1.5,
                        help="BM25 k1 — term-frequency saturation (default 1.5)")
    parser.add_argument("--b", type=float, default=0.75,
                        help="BM25 b — length normalization, 0=none 1=full (default 0.75)")
    parser.add_argument("--no-stopwords", action="store_true",
                        help="disable English stopword removal (ablation)")
    parser.add_argument("-i", "--input", default=None,
                        help="questions JSONL (default: questions-<lang>.jsonl)")
    parser.add_argument("--scenes", default=None,
                        help="scenes JSONL (default: all/<lang>-gemini.jsonl)")
    parser.add_argument("-t", "--tsv", default=None,
                        help="scene titles TSV (default: all/<lang>-gemini.tsv)")
    args = parser.parse_args()

    lang = args.lang
    questions_path = Path(args.input) if args.input else ROOT / f"questions-{lang}.jsonl"
    scenes_path = Path(args.scenes) if args.scenes else ROOT / "all" / f"{lang}-gemini.jsonl"
    tsv_path = Path(args.tsv) if args.tsv else ROOT / "all" / f"{lang}-gemini.tsv"

    titles = load_titles(tsv_path)
    scenes = load_scenes(scenes_path, titles)
    print(f"Loaded {len(scenes)} scenes from {scenes_path}")

    questions = load_questions(questions_path)
    print(f"Questions: {len(questions)}")

    # Scene document = title + body, matching build_index.py's embed prompt
    # content (`title: {title} | text: {text}`) so the two retrievers see the
    # same lexical surface.
    remove_stop = not args.no_stopwords
    docs = [tokenize(f"{s['title']} {s['text']}", lang=lang, remove_stop=remove_stop)
            for s in scenes]
    bm25 = BM25Index(docs, k1=args.k1, b=args.b)
    print(f"BM25 index: {bm25.n_docs} docs, avgdl={bm25.avgdl:.1f} tokens, "
          f"vocab={len(bm25.idf)}, k1={args.k1}, b={args.b}, "
          f"stopwords={'off' if args.no_stopwords else 'on'}")
    print()

    records: dict[int, dict] = {}
    for qid, q in enumerate(questions, start=1):
        q_tokens = tokenize(q["question"], lang=lang, remove_stop=remove_stop)
        rec = rank_all_scenes(bm25, q_tokens, scenes, set(q["chapters"]))
        rec = {
            "question_id": qid,
            "type": q.get("type", "all"),
            "gold_chapters": sorted(set(q["chapters"])),
            **rec,
        }
        records[qid] = rec

    print_coverage_table(records, questions)
    print_per_question_coverage_table(records)
    print_threshold_table(records)
    print_per_question_table(records)
    print_dense_miss_table(records, questions)


if __name__ == "__main__":
    main()
