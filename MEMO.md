# MEMO

## Handoff (2026-09-03)

The line-alignment pass is finished, documented, and wired into the build for
all four languages. [`all/aligned/README.md`](all/aligned/README.md) is the
full record - what the pass does and why, the recovered prompt of the discarded
first run, the model comparisons, the checks, and decisions 1-8.
`scripts/README.md` describes every script by purpose. Nothing below repeats
them; this is only what is left.

Decision 8 is done for all four languages: `scripts/jsonl_to_md.py` takes
`-a`/`--aligned`, `make convert` unpacks the deltas through a pattern rule and
passes it for English, Japanese, modern Bengali and Hindi, and
`all/{en,ja,bn,hi}-gemini{,-full,-lines}.md` have been regenerated from the
aligned text. `make build` succeeds against them.

**Next step: `make deploy`**, which was held until all four languages changed
over in one deployment. That is now the case - the live site still serves the
pre-alignment text and this is the only remaining step.

Once that deployment is done this file has nothing left in it and is to be
deleted. Nothing links to it - the references that used to point here now point
at `all/aligned/README.md`, and `qa-eval/results/README.md`'s `../MEMO.md` is
`qa-eval/MEMO.md`, a different file.
