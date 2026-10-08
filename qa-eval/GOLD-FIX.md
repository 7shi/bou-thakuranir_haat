# Fixing a Gold Answer

How to correct a gold answer in `questions-{en,ja}.jsonl` and bring every
verdict and report in line with it, without answering any question again.
Commands after step 1 run in `qa-eval/`.

## What may change

- **May change:** `answer` and `rationale`.
- **Must not change:** `question`, `chapters`, `type` and the line order. The
  answers were generated from them, and some answer models can no longer be
  run, so a changed question could not be answered again.
- **The texts stay frozen:** `all/<lang>-gemini.jsonl` is what the answer
  models read, so a gold answer is checked against it, not against the
  corrected `.md`.
- **The Japanese gold answer** is a translation of the English one. It follows
  the proper-noun dictionary in `scripts/translate_questions.py` and the
  wording of the Japanese text.

## 1. Edit the gold answers

Edit the `answer` (and the `rationale` where it states the same error) of both
files. Then check, from the repository root, that the frozen fields are
unchanged against `HEAD`:

```bash
python3 - <<'EOF'
import json, subprocess
for l in ["en", "ja"]:
    old = [json.loads(x) for x in subprocess.run(
        ["git", "show", f"HEAD:questions-{l}.jsonl"],
        capture_output=True, text=True).stdout.splitlines()]
    new = [json.loads(x) for x in open(f"questions-{l}.jsonl")]
    key = lambda r: (r["question"], r["chapters"], r["type"])
    assert len(old) == len(new)
    print(l, "changed:", [i for i, (a, b) in enumerate(zip(old, new), 1) if a != b],
          "frozen fields changed:",
          [i for i, (a, b) in enumerate(zip(old, new), 1) if key(a) != key(b)])
EOF
```

## 2. Check the new claims against the texts

[results/gold-check/](results/gold-check/README.md) splits each English gold
answer into claims and checks them against the cited chapters in both
languages. Redo it for the edited questions only; their records are replaced
in place:

```bash
make -C results/gold-check redo QIDS="22 34"
make -C results/gold-check compare
```

- A claim that neither text states (*missing* or *contradicted* in both) is
  usually a further error in the gold answer: fix it and redo the question.
- A claim that only the Japanese text lacks may be a real difference between
  the translations. Read the passage in both texts and in the Bengali original
  (`all/bn.md`). When the texts say the same thing, set the verdict to the same
  value in both files, add `"revised": true` and rewrite the reason. Otherwise
  leave it: it is a *ja-only missing* claim.
- `make redo` replaces the records, so a `"revised"` flag set earlier on a
  redone question is gone and has to be reviewed again.

## 3. Re-grade the edited questions

The judges skip a question that already has a verdict. Removing the verdicts
of the edited questions and re-running the usual judge commands grades only
those questions.

```bash
QIDS="22 34"
uv run drop_verdicts.py $QIDS
```

[drop_verdicts.py](drop_verdicts.py) removes their rows from
`results-en/`, `results-ja/` and `results/`: `judge/*.jsonl` and
`{ternary,openai,jev,nimble}/*.tsv`. `MODELS.tsv` is left as it is.

### Mark the verdict files out of date

No rule in the [Makefile](Makefile) depends on `questions-<lang>.jsonl`, so
the edit does not make anything answer again. But `drop_verdicts.py` has just
rewritten the verdict files, which are now newer than the answer files, so
`make` would take them as up to date. Touch the answer files:

```bash
touch results-{en,ja}/extract.jsonl results-{en,ja}/[cfghv]*.jsonl
make -n LANG=en judge ceiling filter2 filter3 | grep answer_   # must print nothing
make -n LANG=ja judge ceiling filter2 filter3 | grep answer_   # must print nothing
```

The per-model runs in `results/` are graded by `make -C results judge*`, which
resumes any verdict file with fewer rows than its answer file and does not
look at timestamps.

### Run the judges

```bash
make LANG=en judge ceiling filter2 filter3
make LANG=ja judge ceiling filter2 filter3
make -C results judge
for j in ternary openai jev nimble; do
  for l in en ja; do
    uv run judge-$j.py -l $l results-$l/extract.jsonl results-$l/[cfghv]*.jsonl || break 2
  done
  make -C results judge-$j || break
done
uv run sort_verdicts.py
```

The judges append the re-graded rows at the end of each file.
[sort_verdicts.py](sort_verdicts.py) puts them back in question order and
stops without writing if a question was graded twice.

### Verify

- Every verdict file has one row per answered question, in question order.
- `git diff` touches only the rows of the edited questions.
- `MODELS.tsv` files are unchanged.

## 4. Update the reports and documents

Regenerate the per-model reports:

```bash
make -C results report report-ternary report-openai report-jev report-nimble
```

Then update every figure that quotes the changed scores, including the
case studies that discuss an edited question:

- [README.md](README.md) and [README-ja.md](README-ja.md)
- [results-en/README.md](results-en/README.md) and [results-ja/README.md](results-ja/README.md)
- [results/README.md](results/README.md), [results/ja2en/](results/ja2en/README.md)
  and [results/gold-check/](results/gold-check/README.md)
- [TERNARY.md](TERNARY.md), [OPENAI.md](OPENAI.md), [JEV.md](JEV.md),
  [NIMBLE.md](NIMBLE.md), their counterparts in `results/`, and
  [FILTER.md](FILTER.md)

The documents state the corrected results only, without the earlier figures.
The logs of finished experiments in [jev/](jev/README.md) are not re-graded.
