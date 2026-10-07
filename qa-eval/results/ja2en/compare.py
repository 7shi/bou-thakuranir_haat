#!/usr/bin/env python3
"""Compare Ternary scores of the English, Japanese and cross-graded answers.

Per model (every model with a ternary/ or xling/ file here), in percent as
`(correct + 0.5 · partial) / 50`:

  en      ../ternary/<model>-en.tsv   English answer, English gold
  ja      ../ternary/<model>-ja.tsv   Japanese answer, Japanese gold
  xling   xling/<model>-ja.tsv        Japanese answer, English gold
  ja→en   ternary/<model>-ja.tsv      translated answer, English gold
  retest  retest/<model>-en.tsv       English answer graded again

The Japanese questions and gold answers are translations of the English ones,
so the English gold is the original. xling coming back to en puts the gap in
the Japanese gold; ja→en coming back puts it in grading Japanese text; both
staying at ja puts it in the answers. retest shows how far a second grading of
the same answers moves on its own.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
VERDICTS = ["correct", "partial", "incorrect"]
WEIGHT = {"correct": 2, "partial": 1, "incorrect": 0}
COLUMNS = {"en": "en", "ja": "ja", "xling": "xling", "ja2en": "ja→en", "retest": "retest"}


def load(path: Path) -> dict[int, str] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return {int(r["qid"]): max(VERDICTS, key=lambda v: float(r[v]))
                for r in csv.DictReader(f, delimiter="\t")}


def score(verdicts: dict[int, str] | None) -> int | None:
    if verdicts is None:
        return None
    return round(sum(WEIGHT[v] for v in verdicts.values()) * 100 / (2 * len(verdicts)))


def main():
    stems = sorted({p.stem.removesuffix("-ja")
                    for d in ("ternary", "xling") for p in (HERE / d).glob("*-ja.tsv")})
    rows = []
    for stem in stems:
        v = {"en": load(RESULTS / "ternary" / f"{stem}-en.tsv"),
             "ja": load(RESULTS / "ternary" / f"{stem}-ja.tsv"),
             "xling": load(HERE / "xling" / f"{stem}-ja.tsv"),
             "ja2en": load(HERE / "ternary" / f"{stem}-ja.tsv"),
             "retest": load(HERE / "retest" / f"{stem}-en.tsv")}
        rows.append((stem.removeprefix("ceiling-"), v))

    cols = [k for k in COLUMNS if any(v[k] is not None for _, v in rows)]
    diffs = [k for k in cols if k != "en"]
    print("| Model | " + " | ".join(COLUMNS[k] for k in cols) + " | "
          + " | ".join(f"{COLUMNS[k]} − en" for k in diffs) + " |")
    print("| :--- | " + " | ".join(["---:"] * (len(cols) + len(diffs))) + " |")
    scores = {k: [] for k in cols}
    sums = {k: [] for k in cols}
    for model, v in rows:
        s = {k: score(v[k]) for k in cols}
        for k in cols:
            if s[k] is not None:
                scores[k].append(s[k])
                sums[k].append(s[k] - s["en"])
        print(f"| `{model}` | " + " | ".join("—" if s[k] is None else str(s[k]) for k in cols) + " | "
              + " | ".join("—" if s[k] is None else f"{s[k] - s['en']:+d}" for k in diffs) + " |")
    print("| **Mean** | "
          + " | ".join(f"{sum(scores[k]) / len(scores[k]):.2f}" if scores[k] else "—" for k in cols) + " | "
          + " | ".join(f"{sum(sums[k]) / len(sums[k]):+.2f}" if sums[k] else "—" for k in diffs) + " |")

    for a, b in [("ja", "xling"), ("en", "xling"), ("ja", "ja2en"), ("en", "ja2en"), ("en", "retest")]:
        mat = {(x, y): 0 for x in VERDICTS for y in VERDICTS}
        for _, v in rows:
            if v[a] is None or v[b] is None:
                continue
            for qid, x in v[a].items():
                mat[x, v[b][qid]] += 1
        total = sum(mat.values())
        if not total:
            continue
        agree = sum(mat[x, x] for x in VERDICTS)
        print(f"\n| {COLUMNS[a]} \\ {COLUMNS[b]} | " + " | ".join(VERDICTS) + " |")
        print("| :--- | " + " | ".join(["---:"] * 3) + " |")
        for x in VERDICTS:
            print(f"| **{x}** | " + " | ".join(f"{mat[x, y]:,}" for y in VERDICTS) + " |")
        print(f"\n*Agreement: {agree:,} / {total:,} ({agree / total:.1%})*")


if __name__ == "__main__":
    main()
