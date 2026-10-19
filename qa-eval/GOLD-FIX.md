# Fixing a Gold Answer

How to correct a gold answer in `questions-{en,ja}.jsonl` and bring the Jev
verdicts and reports in line with it, without answering any question again.
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

[gold-check/](gold-check/README.md) splits each English gold answer into
claims and checks them against the cited chapters in both languages. Redo it
for the edited questions only; their records are replaced in place:

```bash
make -C gold-check redo QIDS="22 34"
make -C gold-check claims
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

Only Jev, the default judge, is re-graded. The frozen judges keep the verdicts
they gave against the earlier gold answer: qwen in `judge/`, `nimble/`,
`clef-flash/`, `clef/`, `openai/` and `ternary/`, the Ternary runs of
[results/ja2en/](results/ja2en/README.md), and every archived `jev-<old>/`
(see [models/README.md](models/README.md)).

`judge-jev.py` skips a question that already has a verdict. Removing the Jev
verdicts of the edited questions and re-running Jev grades only those
questions.

```bash
QIDS="22 34"
uv run drop_verdicts.py $QIDS
```

[drop_verdicts.py](drop_verdicts.py) removes their rows from `jev/*.tsv` in
`results-en/`, `results-ja/` and `results/`, and touches nothing else.
`MODELS.tsv` is left as it is. `-s` limits it to some of the three sets, so
the question numbers go before it (`uv run drop_verdicts.py $QIDS -s results`).

No rule in the [Makefile](Makefile) depends on `questions-<lang>.jsonl`, and
the answer files are not rewritten, so the edit does not make anything answer
again.

### Run Jev

The root Makefile builds `jev/<stem>.tsv` from its answer file by timestamp,
and `drop_verdicts.py` has just rewritten the verdict files, so `make` takes
them as up to date. `results-<lang>/` is therefore graded by passing the
answer files of the existing Jev verdicts, one call per language. The
per-model runs in `results/` are graded by `make -C results judge`, which
resumes any verdict file with fewer rows than its answer file and does not
look at timestamps.

```bash
for l in en ja; do
  uv run judge-jev.py -l $l $(ls results-$l/jev/*.tsv | grep -v MODELS.tsv |
    sed 's|/jev/|/|; s|\.tsv$|.jsonl|') || break
done
make -C results judge
uv run sort_verdicts.py
```

`judge-jev.py` appends the re-graded rows at the end of each file.
[sort_verdicts.py](sort_verdicts.py) puts them back in question order and
stops without writing if a question was graded twice.

### Verify

- Every `jev/*.tsv` has one row per answered question, in question order.
- `git diff` touches only the rows of the edited questions, and only in `jev/`.
- `MODELS.tsv` files are unchanged.

## 4. Update the reports and documents

Regenerate the per-model report:

```bash
make -C results report
```

`make -C gold-check claims` prints the tables of
[gold-check/README.md](gold-check/README.md).

Then update every figure that quotes the changed Jev scores, including the
case studies that discuss an edited question:

- the Results tables and findings of [README.md](README.md) and [README-ja.md](README-ja.md)
- the case studies [results-en/README.md](results-en/README.md) and
  [results-ja/README.md](results-ja/README.md), and the scores quoted in
  [FILTER.md](FILTER.md) and [HYBRID.md](HYBRID.md)
- [results/README.md](results/README.md), rewritten from
  [results/report.md](results/report.md)
- [models/README.md](models/README.md) and [models/JEV-1.14.md](models/JEV-1.14.md)
- [gold-check/README.md](gold-check/README.md)

The documents of the frozen judges, and the scores they quote, describe those
judges as graded and are not updated.

The documents state the corrected results only, without the earlier figures.
The logs of finished experiments in [jev/](jev/README.md) are not re-graded.
