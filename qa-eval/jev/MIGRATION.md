# Migrating to a new Jev version

How the default Jev version of [judge-jev.py](../judge-jev.py) is replaced
while the verdicts of the previous version are kept, and why it is done this
way. The procedure is version-independent; `<old>` and `<new>` stand for full
version strings such as `jev-1.13.0`. The first migration, `jev-1.13.0` →
`jev-1.14.0`, is given at the end as a worked example.

## Constraints

- **The output directory is fixed.** `judge-jev.py` writes
  `<results dir>/jev/<stem>.tsv`, and `report.py --jev`, `results/report.py
  --jev`, `results/Makefile` (`judge-jev`, `report-jev`), `drop_verdicts.py`
  and `sort_verdicts.py` all read `jev/`.
- **A version is pinned, and mixing is refused.** `DEFAULT_MODEL` is a version,
  not the `jev-latest` alias, and `jev/MODELS.tsv` records the model and scheme
  per file. A file recorded with another model stops the run. Changing only
  `DEFAULT_MODEL` therefore makes every existing file abort instead of being
  re-graded; the old verdicts have to move out of `jev/` first.

## Decisions

### `jev/` is always the current version; old versions move to `jev-<old>/`

Two layouts were considered:

- **A.** Leave `jev/` as it is and write the new version to `jev-<new>/`.
  Nothing moves, but making the new version the default means pointing every
  reader of `jev/` (both `report.py`s, the Makefile targets, the README tables)
  at `jev-<new>/`, and `jev/` keeps meaning an old version. The next migration
  needs the same repointing again.
- **B (adopted).** `git mv jev jev-<old>`, then grade the new version into a
  fresh `jev/`. One move per migration, and nothing that reads `jev/` changes:
  `make judge-jev`, `make report-jev`, `report-jev.md`, `MODELS-jev.svg` keep
  their names and simply follow the new version.

The directory name carries the full version string (`jev-1.13.0`, not
`jev113`), the same string `MODELS.tsv` records.

### The archived version is frozen

`jev-<old>/` is not graded again, not even after a gold-answer fix
([GOLD-FIX.md](../GOLD-FIX.md)). Reasons:

- It is a record of what `<old>` said; the comparison with `<new>` is made once,
  at migration time, on identical inputs.
- The old version may not stay available from the API.
- `drop_verdicts.py` and `sort_verdicts.py` only touch `jev/`, so freezing
  needs no code change and nothing can update the archive by accident.

No `--out-dir` option was added to `judge-jev.py` for the same reason: there is
no supported way to write into an archive.

The experiment logs in this directory (`jev/results*/`, its own
[judge-jev.py](judge-jev.py) pinned to `jev-1.13.0`) are a finished experiment
and are not migrated either.

### The last generated report is archived with the verdicts

`results/report-jev.md` and `results/MODELS-jev.{svg,png}` are regenerated from
`jev/`, so the old version's final copies would be lost. They are copied (not
moved, so `results/` stays consistent until the regeneration) into
`results/jev-<old>/`. The copy of `report-jev.md` gets its relative links
adjusted one level deeper and one line saying it is the archived `<old>`
version. PNGs stay untracked through the `results/*/MODELS*.png` rule in
`qa-eval/.gitignore`.

`results-<lang>/` has no generated report file; its numbers can be recomputed
from the archive at any time with `report.py --tsv-dir`.

### The README tables show only the new version

`results/README.md` (the Ceiling and Hybrid8 tables and every number derived
from them) is rewritten to the `<new>` state, without old values or
"changed from" notes. The comparison between versions goes to its own
document, `qa-eval/JEV-<new short>.md` (e.g. [JEV-1.14.md](../JEV-1.14.md)).
Documents that describe a past run under `<old>` (e.g.
[JEV.md](../JEV.md), [results/JEV.md](../results/JEV.md), the
[NIMBLE.md](../NIMBLE.md) / [OPENAI.md](../OPENAI.md) /
[TERNARY.md](../TERNARY.md) comparisons that name the version) stay as they
are, with paths into `jev/` corrected to `jev-<old>/`.

## Procedure

Run from `qa-eval/` unless noted. Commit after steps 3, 5 and 7.

1. **Check the API key.** `judge-jev.py` needs `TYPESAFE_API_KEY`; without it
   the run fails at client construction, before any directory is created.
2. **Archive.**
   ```
   for d in results-en results-ja results; do git mv $d/jev $d/jev-<old>; done
   cp -p results/report-jev.md results/MODELS-jev.svg results/MODELS-jev.png results/jev-<old>/
   ```
   Fix the relative links in `results/jev-<old>/report-jev.md` and add the
   archive note.
3. **Switch the default.** Set `DEFAULT_MODEL = "<new>"` in
   [judge-jev.py](../judge-jev.py) (and its example in the docstring). Correct
   paths in documents that describe the `<old>` runs. Check the archive still
   aggregates to the documented numbers:
   ```
   uv run report.py -l en --tsv-dir jev-<old>
   ```
4. **Grade `results-<lang>/`.** The root Makefile has no Jev target; pass the
   answer files that have a `judge/` counterpart, one call per language:
   ```
   uv run judge-jev.py -l en $(ls results-en/judge/*.jsonl | sed 's|/judge/|/|')
   uv run judge-jev.py -l ja $(ls results-ja/judge/*.jsonl | sed 's|/judge/|/|')
   ```
5. **Grade `results/` and regenerate its report.**
   ```
   make -C results judge-jev report-jev
   ```
   This is one `judge-jev.py` call per language, so it prints and logs two
   usage totals; both count toward the cost.
6. **Verify.**
   - Every TSV has 50 rows after the header, and every row of each
     `jev/MODELS.tsv` reads `<new>` with the unchanged scheme.
   - Recompute the cost from llm7shi's `usage.jsonl` (all `<new>` entries of
     the run) and check it against the bill.
7. **Document.**
   - Rewrite `results/README.md` from the new `report-jev.md`. The Hybrid8
     tables (per-question verdicts, flips between ceiling and hybrid8, counts
     restricted to questions whose gold chapters were retrieved) are not in
     the report and must be recomputed from the TSVs; first check that the
     script reproduces the current README from `jev-<old>/`, then run it on
     `jev/`.
   - Write `JEV-<new short>.md`: run cost and time, verdict agreement with
     `<old>` per set (a confusion matrix of most-probable verdicts), mean
     confidence, and the per-method table for `results-<lang>/`.
   - Add one bullet for the new version to the Jev section of
     [README.md](../README.md) and [README-ja.md](../README-ja.md), and a link
     to the comparison from `results/README.md`.

## Worked example: `jev-1.13.0` → `jev-1.14.0` (2026-10-17)

- Scheme unchanged: `choice@19579e23`.
- Graded: 15 + 15 files in `results-en/` and `results-ja/`, 120 in `results/`;
  7,500 requests, 6,136,962 input tokens, 22m 36s. Billed $0.2578 (input
  only, $0.042 per million tokens). The first cost estimate counted only the
  Japanese half of step 5 and missed the English call's usage, which the bill
  exposed; hence the note in step 5.
- The archive aggregated exactly to the numbers in JEV.md and
  results/README.md before anything was re-graded.
- Agreement with 1.13.0 was 95–97%, almost entirely *correct* ↔ *partial*
  flips in both directions; every method moved by at most 0.03. Details in
  [JEV-1.14.md](../JEV-1.14.md).
- Added for this migration: `report.py --tsv-dir`, the
  `results/*/MODELS*.png` ignore rule, `results/jev-1.13.0/report-jev.md`.
