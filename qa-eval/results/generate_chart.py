"""Generate a bar chart comparing per-model ceiling scores (English vs. Japanese).

Reads scores through `report.collect_rows` (the same discovery/aggregation
code `make report` uses), so this chart and report.md can never disagree.
Run via `make report` (see Makefile), which regenerates both; `--jev`,
`--nimble` or `--openai` (via `make report-<dir>`) charts that judge's verdicts
into MODELS-<dir>.svg/png instead.
"""
# /// script
# dependencies = ["matplotlib"]
# ///
import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from report import LANGS, TSV_DIRS, TSV_JUDGES, collect_rows

# Fix the SVG element id salt so regenerating the chart doesn't churn
# unrelated ids in the diff.
matplotlib.rcParams["svg.hashsalt"] = "qa-eval-models-chart"

HERE = Path(__file__).parent


def weighted_pct(row: dict) -> int:
    return (2 * row["correct"] + row["partial"]) * 100 // (2 * row["total"])


def load_ceiling_scores(tsv_dir: str | None = None) -> list[tuple[str, int, int]]:
    by_model: dict[str, dict[str, dict]] = {}
    for row in collect_rows(HERE, tsv_dir):
        if row["method"] != "ceiling":
            continue
        by_model.setdefault(row["model"], {})[row["lang"]] = row

    scores = []
    for model, per_lang in by_model.items():
        if not all(lang in per_lang for lang in LANGS):
            continue
        scores.append((model, weighted_pct(per_lang["en"]), weighted_pct(per_lang["ja"])))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    for name in TSV_DIRS:
        group.add_argument(f"--{name}", dest="tsv_dir", action="store_const", const=name,
                           help=f"chart the {TSV_JUDGES[name][0]} verdicts ({name}/*.tsv) "
                                f"into MODELS-{name}.svg/png")
    args = parser.parse_args()
    suffix = f"-{args.tsv_dir}" if args.tsv_dir else ""
    output = HERE / f"MODELS{suffix}.svg"
    output_png = HERE / f"MODELS{suffix}.png"

    rows = load_ceiling_scores(args.tsv_dir)
    if not rows:
        print("No ceiling runs with both en and ja judged")
        return
    rows.sort(key=lambda row: (row[1] + row[2]) / 2, reverse=True)
    models = [row[0] for row in rows]
    en_scores = [row[1] for row in rows]
    ja_scores = [row[2] for row in rows]

    fig, ax = plt.subplots(figsize=(8, 8))
    y = range(len(models))
    height = 0.35
    # After invert_yaxis, a smaller offset sits higher on screen, so English
    # (listed first) goes above Japanese for each model.
    en_bars = ax.barh([i - height / 2 for i in y], en_scores, height=height, label="English")
    ja_bars = ax.barh([i + height / 2 for i in y], ja_scores, height=height, label="Japanese")
    # Each score just past its bar's end; the x-axis runs a little past 100
    # (below) so a 100 still has room for its label.
    for bars in (en_bars, ja_bars):
        ax.bar_label(bars, padding=2, fontsize=6)

    ax.set_yticks(list(y))
    ax.set_yticklabels(models, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Score (correct × 2 + partial, out of 50 questions)")
    title_suffix = f" ({TSV_JUDGES[args.tsv_dir][0]})" if args.tsv_dir else ""
    ax.set_title(f"Ceiling: per-model answerer comparison{title_suffix}")
    ax.set_xlim(0, 105)
    ax.set_xticks(range(0, 101, 20))
    ax.legend(loc="lower left")
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output)
    print(f"Saved: {output}")
    fig.savefig(output_png)
    print(f"Saved: {output_png}")


if __name__ == "__main__":
    main()
