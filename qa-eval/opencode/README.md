# Ceiling Evaluation via opencode

Runs the Ceiling method (gold chapters fed verbatim as context, no retrieval)
through the [`opencode`](https://opencode.ai/) coding-agent CLI, as an
alternative to the llm7shi-based `../answer_ceiling.py`. `opencode` has no
Python API, so the pipeline here is generate-a-script-then-run-it rather than
`answer.py`'s direct-call loop.

## Files

- `extract.py` — splits `../../all/<lang>-gemini.jsonl` into per-chapter text
  files `<lang>/<NN>.txt` (e.g. `en/03.txt`), each headed `## Chapter N` /
  `## 第N章`, so `opencode run -f` has a file to point at per gold chapter.
  Lines are wrapped at 1800 columns: some English segments run past 4000
  characters on a single line, and opencode's file-attachment reader
  truncates (silently drops content past) any line over 2000 characters —
  see `../../MEMO.md`. Japanese never crosses 1800 chars, so Japanese
  chapters end up unwrapped.
- `make_ceiling.py` — generates `ceiling.sh`: one `opencode run` per question
  in `../../questions-<lang>.jsonl`, feeding it that question's gold chapter
  file(s) via `-f`, followed by a call to `build_jsonl.py`.
- `build_jsonl.py` — converts `tmp/<model-name>/<NN>.txt` into
  `../results/ceiling-<safe-model>-<lang>.jsonl`, the format `../results/`
  uses (`question_id` / `expanded` / `answer`), so `judge.py` and `report.py`
  there can pick it up like any other per-model run.

## Workflow

```sh
make extract                              # -> en/01.txt .. en/37.txt, ja/01.txt .. ja/37.txt
make ceiling.sh MODEL=... [LANG=en]       # -> ceiling.sh
./ceiling.sh
    # -> tmp/<model-name>/01.txt ..
    # -> ../results/ceiling-<safe-model>-<lang>.jsonl (last line of ceiling.sh)
```

`ceiling.sh` bakes in the model at generation time and is meant to be
regenerated per run — it's gitignored. Trying a different model means
`make ceiling.sh MODEL=...` again, not editing or re-running the old script.

## Notes

- **Resume-safe**: each question's line in `ceiling.sh` is guarded by a check
  for its `tmp/<model>/<NN>.txt` output, so a re-run only answers what's
  missing.
- **`-f` quirk**: `opencode run`'s `-f` option is yargs array-type — passed as
  `-f file1.txt file2.txt "prompt"` it swallows the prompt as a third file,
  leaving the actual message empty. `make_ceiling.py` avoids this by placing
  the prompt first (as the positional message) and appending every gold
  chapter's file after a single trailing `-f`, space-separated, rather than
  repeating `-f` per file.
- **Answer-only instruction**: `opencode` is a general coding-agent CLI, not a
  plain answer-only completion, so its replies tend to include extra framing
  beyond the bare answer — closing remarks, and citations of the attached
  file's name/path and line numbers, as if writing a code-review comment
  rather than answering a question. Each generated prompt appends a fixed
  instruction telling the model to reply with the answer only and without
  such citations, and not to make any tool call at all (left unconstrained, a
  coding-agent model may reach for a shell tool to inspect the attached file
  or this directory, which also stalls the run since `ceiling.sh` has no TTY
  to approve the resulting permission prompt). opencode's own leading
  `> build · <model>` banner still precedes the reply either way — that's not
  the model's text, so the prompt can't suppress it.
- **Output formatting**: each question's block in `ceiling.sh` starts with a
  blank line, a `===...` separator, and `[Qn/N]`, so a run's terminal output
  stays readable question-to-question.
