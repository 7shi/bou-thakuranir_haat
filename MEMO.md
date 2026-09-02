# MEMO

## Handoff (2026-09-03)

The line-alignment pass is finished and documented.
[`all/aligned/README.md`](all/aligned/README.md) is the full record - what the
pass does and why, the recovered prompt of the discarded first run, the model
comparison, the checks, and decisions 1-7. `scripts/README.md` describes every
script by purpose. Nothing below repeats them; this is only what is left.

**Next step: decision 8**, the only one still open.
[`scripts/jsonl_to_md.py`](scripts/jsonl_to_md.py) has to take two files - the
original JSONL for structure, `summary` and `translation_notes`, and the aligned
JSONL to substitute in for the translations - before `all/*.md` can be
regenerated and the website build (`make convert`, `make build`, `make deploy`)
can move to the aligned text. That keeps `--mode summary` and `--mode full`
working. Its inputs are `all/aligned/{en,ja}-gemini-terra.delta.jsonl`, which
the build has to unpack first:

```
uv run scripts/pack_aligned.py unpack all/aligned/en-gemini-terra.delta.jsonl
```

Once the site serves the aligned text, drop the last line of the root README's
**Line alignment** section ("The published text still comes from the unaligned
files.").

**Also outstanding, unrelated.** `make questions` calls
`scripts/create_rag_questions.py`, which no longer exists -
`scripts/generate_questions.py` replaced it and takes different arguments. The
target is stale and was left alone; `scripts/README.md` notes it.
