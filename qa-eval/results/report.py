#!/usr/bin/env python3
"""Aggregate the judged runs in results/ into report.md.

Pure mechanical aggregation of existing files — no LLM calls. Independent of
the parent `report.py`, which scans only `results-<lang>/` and deliberately
ignores this directory.

Discovery is simply every `judge/*.jsonl` present (with --jev, every
`jev/*.tsv` from judge-jev.py, written to report-jev.md, each question
counting as its most probable verdict). The judge stem is split as
`<METHOD>-<MODEL>-<LANG>` (METHOD e.g. `hybrid8` or `ceiling`, LANG = en|ja,
MODEL is the filename-sanitized model string with ":" and "/" written as "_"),
so a new run appears here as soon as it is graded. The matching answer file
(`<stem>.jsonl`) supplies the retrieval columns when present. The default
answerer's canonical ceiling and hybrid8 runs (`results-<lang>/<method>.jsonl`
with their `judge/` or `jev/` verdicts) are added as `google_gemma-4-31b-it`
rows, so this report covers every model in the README tables.

Two axes, both computed the same way as the parent report:

1. Answer accuracy (from the judge file): correct / partial / incorrect counts
   plus a weighted score = (correct + 0.5*partial) / total.
2. Chapter retrieval (from `expanded` vs the gold `chapters` in
   questions-<lang>.jsonl): complete-coverage recall and mean precision. These
   depend only on the retrieval setting, not on the answerer, so they act as a
   sanity check that two rows are comparable.

Output: the summary table on the terminal and, unless `--stdout` is given, a
written `report.md` next to this script.
"""

import argparse
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
QA_EVAL = HERE.parent
ROOT = QA_EVAL.parent

# Loaded by explicit path, not `from report import ...`: this file is itself
# importable as `report` (by generate_chart.py, next to it), and that name
# would collide with the parent qa-eval/report.py it needs here.
_spec = importlib.util.spec_from_file_location("qa_eval_report", QA_EVAL / "report.py")
_qa_eval_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_qa_eval_report)
accuracy = _qa_eval_report.accuracy
load_gold = _qa_eval_report.load_gold
load_jsonl = _qa_eval_report.load_jsonl
retrieval = _qa_eval_report.retrieval
JUDGE_DIR = _qa_eval_report.JUDGE_DIR
JEV_DIR = _qa_eval_report.JEV_DIR
load_judge = _qa_eval_report.load_judge

# <METHOD>-<MODEL>-<LANG>: MODEL is the only field that may contain "-" (e.g.
# "google_gemma-4-31b-it"), so METHOD is everything up to the first "-" and LANG
# everything after the last one.
RUN_RE = re.compile(r"(?P<method>[^-]+)-(?P<model>.+)-(?P<lang>en|ja)")
LANGS = ("en", "ja")
# The default answerer (filename-sanitized) and the methods whose canonical
# results-<lang>/<method>.jsonl runs are aggregated alongside this directory's.
CANONICAL_MODEL = "google_gemma-4-31b-it"
CANONICAL_METHODS = ("ceiling", "hybrid8")
LANG_LABELS = {"en": "English", "ja": "Japanese"}


def verdict_glob(jev: bool = False) -> str:
    return f"{JEV_DIR}/*.tsv" if jev else f"{JUDGE_DIR}/*.jsonl"


def discover_runs(results: Path, jev: bool = False) -> list[dict]:
    """One record per judge/*.jsonl (or jev/*.tsv), sorted by (method, model, lang)."""
    found = []
    for judge in sorted(results.glob(verdict_glob(jev))):
        stem = judge.stem
        m = RUN_RE.fullmatch(stem)
        if not m:
            if judge.name != "MODELS.tsv":
                print(f"skipping {judge.parent.name}/{judge.name}: "
                      f"not <METHOD>-<MODEL>-<LANG>{judge.suffix}")
            continue
        answer = results / f"{stem}.jsonl"
        found.append({"model": m["model"], "lang": m["lang"],
                      "method": m["method"],
                      "judge_path": judge,
                      "answer_path": answer if answer.exists() else None})
    # The default answerer's runs of the same methods live in the canonical
    # results-<lang>/ trees, not here; they join the table as ordinary rows.
    for method in CANONICAL_METHODS:
        for lang in LANGS:
            tree = QA_EVAL / f"results-{lang}"
            judge = tree / (f"{JEV_DIR}/{method}.tsv" if jev
                            else f"{JUDGE_DIR}/{method}.jsonl")
            if not judge.exists():
                continue
            answer = tree / f"{method}.jsonl"
            found.append({"model": CANONICAL_MODEL, "lang": lang, "method": method,
                          "judge_path": judge,
                          "answer_path": answer if answer.exists() else None})
    return sorted(found, key=lambda r: (r["method"], r["model"],
                                        LANGS.index(r["lang"])))


def build_rows(runs: list[dict], golds) -> list[dict]:
    rows = []
    for run in runs:
        judge_records = load_judge(run["judge_path"])
        acc = accuracy(judge_records)
        ret = ({"recall": None, "precision": None} if run["answer_path"] is None
               else retrieval(load_jsonl(run["answer_path"]), golds[run["lang"]]))
        rows.append({**run, **acc, **ret, "judge_records": judge_records})
    return rows


def _num(value, fmt: str, dash: str = "—") -> str:
    return dash if value is None else format(value, fmt)


def print_table(rows: list[dict]) -> None:
    w = max([len("model")] + [len(r["model"]) for r in rows])
    wm = max([len("method")] + [len(r["method"]) for r in rows])
    header = (f"{'model':<{w}} {'method':<{wm}} {'lang':<4} {'n':>3} "
              f"{'correct':>7} {'partial':>7} {'incorrect':>9} {'weighted':>9} "
              f"{'ch.recall':>9} {'ch.prec':>8}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['model']:<{w}} {r['method']:<{wm}} {r['lang']:<4} "
              f"{r['total']:>3} {r['correct']:>7} {r['partial']:>7} "
              f"{r['incorrect']:>9} {r['weighted']:>9.3f} "
              f"{_num(r['recall'], '9.3f'):>9} {_num(r['precision'], '8.3f'):>8}")


def render_markdown(rows: list[dict], jev: bool = False) -> str:
    # (method, model) → lang → row, preserving the discovery order.
    by_run: dict[tuple[str, str], dict[str, dict]] = {}
    for r in rows:
        by_run.setdefault((r["method"], r["model"]), {})[r["lang"]] = r

    out = [
        "# Per-model report" + (" (Jev)" if jev else ""),
        "",
        ("Generated by `make report-jev` (`report.py --jev`) — do not edit by hand."
         if jev else "Generated by `make report` (`report.py`) — do not edit by hand."),
        "",
    ]
    if jev:
        out += [
            "Graded by TypeSafe Jev (`judge-jev.py`, `jev/*.tsv`) instead of the qwen",
            "judge; each question counts as its most probable verdict, the stricter",
            "one on a tie. See [jev/README.md](../jev/README.md) for why.",
            "",
        ]
    out += [
        "Every judged run in this directory, plus the default answerer's canonical",
        "`results-<lang>/{ceiling,hybrid8}.jsonl` runs as `google_gemma-4-31b-it`,",
        "aggregated independently of the main table in [qa-eval/README.md](../README.md).",
        "Cells read `weighted% (correct/partial/incorrect)`, matching the tables",
        "[README.md](README.md) copies rows from",
        "([Ceiling](README.md#ceiling-comparing-answerer-models),",
        "[Hybrid8 vs. ceiling](README.md#hybrid8-vs-ceiling-what-retrieval-costs)).",
        "Model names are the filename-sanitized llm7shi strings (\":\" and \"/\" written",
        'as "_").',
        "",
        "| Model | Method | " + " | ".join(LANG_LABELS[l] for l in LANGS) + " |",
        "| --- | --- | " + " | ".join("---" for _ in LANGS) + " |",
    ]
    for (method, model), per_lang in by_run.items():
        cells = []
        for lang in LANGS:
            r = per_lang.get(lang)
            pct = (2 * r["correct"] + r["partial"]) * 100 // (2 * r["total"]) if r else None
            cells.append(f"{pct} ({r['correct']}/{r['partial']}/{r['incorrect']})"
                         if r else "—")
        out.append(f"| `{model}` | {method} | " + " | ".join(cells) + " |")

    out += [
        "",
        "## Every question any model missed",
        "",
        "Question IDs graded `partial` or `incorrect`, per (method, model,",
        "language). A question absent from every column of a row was graded",
        "`correct` by every judged run of that (method, model).",
        "",
        "| Model | Method | en partial | en incorrect | ja partial | ja incorrect |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for (method, model), per_lang in by_run.items():
        cells = []
        for lang in LANGS:
            r = per_lang.get(lang)
            if r is None:
                cells += ["—", "—"]
                continue
            partial = sorted(rec["question_id"] for rec in r["judge_records"]
                             if rec["verdict"] == "partial")
            incorrect = sorted(rec["question_id"] for rec in r["judge_records"]
                               if rec["verdict"] == "incorrect")
            cells.append(", ".join(map(str, partial)) or "—")
            cells.append(", ".join(map(str, incorrect)) or "—")
        out.append(f"| `{model}` | {method} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def collect_rows(results: Path = HERE, jev: bool = False) -> list[dict]:
    """Discover every judged run under `results` and build its score rows.

    Shared by this file's report generation and generate_chart.py, both
    invoked by `make report`, so both read scores through the same
    discovery/aggregation code instead of each parsing report.md.
    """
    runs = discover_runs(results, jev)
    golds = {lang: load_gold(ROOT / f"questions-{lang}.jsonl") for lang in LANGS}
    return build_rows(runs, golds)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=None,
                        help="markdown output path (default: report.md, or report-jev.md "
                             "with --jev)")
    parser.add_argument("--stdout", action="store_true",
                        help="print the markdown instead of writing the file")
    parser.add_argument("--jev", action="store_true",
                        help="read Jev verdicts (jev/*.tsv, most probable verdict) "
                             "instead of judge/*.jsonl")
    args = parser.parse_args()
    args.output = args.output or str(HERE / ("report-jev.md" if args.jev else "report.md"))

    rows = collect_rows(HERE, args.jev)
    if not rows:
        print(f"No {verdict_glob(args.jev)} found in {HERE}")
        return

    print_table(rows)
    md = render_markdown(rows, args.jev)
    if args.stdout:
        print()
        print(md, end="")
    else:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
