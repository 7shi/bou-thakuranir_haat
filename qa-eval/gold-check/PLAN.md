# Plan: move the gold-answer check out of results/

The gold-answer check lives in `qa-eval/results/gold-check/`, but most of it
does not depend on any model's results: it checks the gold answers in
`questions-en.jsonl` against the frozen texts (`all/<lang>-gemini.jsonl`), and
[GOLD-FIX.md](../GOLD-FIX.md) uses it right after a gold answer is edited.
Only part of `compare.py` reads model results (`results/ternary/`). This plan
moves the check here and leaves the analysis of the Japanese gap with the
results.

## When

After the re-grade of the current gold answer fix (Q22, 26, 29, 31, 32, 33, 34,
37, 38, 39, 40, 42, 43, 44, 45, 46, 47, 49, 50) has finished and been sorted.
The gap tables and their README text have to be rewritten with the new
verdicts anyway, so the README split is done in the same pass.

## Current state

- `results/gold-check/check_gold.py`: `facts`, `check` and `--qids` (LLM calls).
  Reads only the questions and the texts. Imports `answer` from `qa-eval/`
  through `sys.path.insert(0, str(HERE.parent.parent))`.
- `results/gold-check/compare.py`: no LLM. Mixes two functions:
  1. per-claim verdicts from `facts.jsonl` and `check-{en,ja}.jsonl`: the
     per-question table (Q, Type, Claims, en/ja s/m/c, ja-only missing) and
     the "ja-only missing" and "Missing in both texts" lists;
  2. the ja − en gap: the per-question "ja − en" column and the
     All/single/cross tables with the sign test, from
     `results/ternary/ceiling-*-{en,ja}.tsv` (`compare.py:62`).
- `results/gold-check/Makefile`: `facts`, `check`, `compare`, `redo QIDS=...`.
- `results/gold-check/README.md`: sections Setup, Results (with "The ja-only
  missing claims are differences of wording" and "Removing them leaves the
  gap"), "Gold answers that the text does not support", Caveats. It opens as
  the follow-up to `results/ja2en/`.
- `facts.jsonl`, `check-en.jsonl` and `check-ja.jsonl` are modified for the
  current fix and not yet committed; they move with the directory.

## Steps

1. `git mv qa-eval/results/gold-check/* qa-eval/gold-check/` (tracked files
   only; `__pycache__` is untracked), keeping this PLAN.md until the end.
2. `check_gold.py`: `sys.path.insert(0, str(HERE.parent))`, since `answer.py`
   is now one level up.
3. Split `compare.py`:
   - **A, here** (name it `claims.py`, not `report.py`, which would clash with
     `qa-eval/report.py` on `sys.path`; a separate file rather than a
     `check_gold.py` subcommand, so that importing it does not load llm7shi):
     loading of facts and checks, a function returning the ja-only missing
     claims per question (en *stated*, ja not *stated*) and the
     both-missing ones, and a `main` printing the per-question table without
     the ja − en column and the two claim lists.
   - **B, with the results** (proposed: `results/ja2en/`, as it answers the
     question ja2en left open; otherwise a new directory under `results/`
     whose name cannot be confused with gold-check): imports A's function,
     reads `results/ternary/`, prints per question Q / ja-only missing /
     ja − en, and the All/single/cross gap tables with the sign test.
   - Keep the criterion for "ja-only missing" in A only; B must not parse
     A's Markdown output.
4. Makefiles: here, `make compare` becomes `make claims` (runs A); `facts`,
   `check` and `redo` stay. Add a target for B in its directory's Makefile.
5. Split the README:
   - here: Setup, the review of differing verdicts (`"revised"`), the claim
     table and lists, "The ja-only missing claims are differences of
     wording", "Gold answers that the text does not support", the caveats
     about the checker;
   - with B: the gap tables, "Removing them leaves the gap", the caveats about
     the gap. In `results/ja2en/README.md` this becomes a section continuing
     its open question.
   - Write the corrected state only, with the figures from the new verdicts.
6. Update links and paths:
   - `GOLD-FIX.md`: `results/gold-check/` → `gold-check/` (three places), and
     step 2 runs `make -C gold-check claims`; step 4 regenerates B.
   - `results/ja2en/README.md:186`: `../gold-check/` → `../../gold-check/`.
   - links inside the moved README (`../ja2en/` → `../results/ja2en/`,
     `../TERNARY.md` → `../results/TERNARY.md`, and so on).
   - `grep -rn "gold-check" qa-eval` for anything else.
7. Verify without any API call: A's table and lists, plus B's tables,
   together match the output of the old `compare.py` on the same data.
8. Delete this PLAN.md. Commit the move and split apart from the gold answer
   data (`questions-*.jsonl`, the verdict files, `facts.jsonl`,
   `check-*.jsonl`). `git mv` renames the committed content in the index and
   leaves the uncommitted edits of the data files unstaged, so the move can
   be committed with the data unchanged and the data committed afterwards.
