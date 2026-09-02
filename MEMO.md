# MEMO

## Handoff (2026-09-03)

The line-alignment pass is finished, documented, and wired into the build for
English and Japanese. [`all/aligned/README.md`](all/aligned/README.md) is the
full record - what the pass does and why, the recovered prompt of the discarded
first run, the model comparison, the checks, and decisions 1-8.
`scripts/README.md` describes every script by purpose. Nothing below repeats
them; this is only what is left.

Decision 8 is done: `scripts/jsonl_to_md.py` takes `-a`/`--aligned`, `make
convert` unpacks the deltas through a pattern rule and passes it for English and
Japanese, and `all/{en,ja}-gemini{,-full,-lines}.md` have been regenerated from
the aligned text. `make build` succeeds against them. Japanese is the same
characters with different line breaks; English differs slightly at the seams.

**Next step: align modern Bengali and Hindi.** `all/bn-gemini.jsonl` and
`all/hi-gemini.jsonl` have not been through the pass, so `make convert` still
converts them as before. The work is:

1. `uv run scripts/align_lines.py all/bn-gemini.jsonl -m openai:gpt-5.6-terra -o all/aligned/bn-gemini-terra.jsonl`
   and the same for `hi`, then `pack_aligned.py pack` each result.
   `all/aligned/.gitignore` already excludes `*-terra.jsonl`, so only the deltas
   get committed.
2. Add both to `ALIGNED` in the Makefile and give the two `convert` lines their
   `-a` arguments, then `make convert` and `make split`.
3. Update the Contents and Results tables in `all/aligned/README.md`, and its
   Open point that says only English needs this and both languages are
   processed. Drop the sentence in the root README that says modern Bengali and
   Hindi are not aligned yet.

**Then `make deploy`**, which is held until all five languages change over in
one deployment. The live site still serves the pre-alignment text.

Once that deployment is done this file has nothing left in it and is to be
deleted. Nothing links to it - the references that used to point here now point
at `all/aligned/README.md`, and `qa-eval/results/README.md`'s `../MEMO.md` is
`qa-eval/MEMO.md`, a different file.
