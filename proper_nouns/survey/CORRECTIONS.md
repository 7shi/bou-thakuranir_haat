# Corrections found during review

Tally only, per MEMO's step 2: these are found while reviewing
`anchor-{hi,en,ja}.jsonl` against `normalized-bn.jsonl` and the source
text, but not yet applied to the actual translations. `anchor-*.jsonl`
itself is a derived analysis file and is not the fix target - the fix
target is the translation text in `all/aligned/{hi,en,ja}-*.jsonl`.

Two kinds of entries:

- **Bengali-side**: a name the survey/clustering got wrong or missed.
  Fixed via `cluster.py`'s `patch()` on `cluster-bn.jsonl`, then
  `normalized-bn.jsonl` and any `anchor-*.jsonl` are rebuilt. Listed here
  only until that's done; once fixed, remove the entry.
- **Target-language-local**: two spellings/forms in one language's
  translation of the same chapter that should be one, with no Bengali-side
  problem (`normalized-bn.jsonl` is already correct). No mechanism exists
  yet to apply these automatically - each one becomes a manual edit to the
  translation text once the review for that language is complete.

Review order: hi first, then en and ja (see MEMO / `project-bengali-bv-no-distinction`).

Review status: hi, en, and ja have all been reviewed (see MEMO). All
findings have been applied or resolved - ja turned up no
target-language-local corrections; en's three (ch13 দাদা
"Grandson"/"Dada", ch7/ch24/ch26 মহারাজ "Your Majesty"/"Maharaj",
and "Dadamahashay"/"Dada Mahashay" spacing found while answering a
follow-up question, not from the original anchor-en.jsonl review) were
unified to "Dada", "Maharaj" and "Dada Mahashay" respectively; hi's one
(ch1 উদয়াদিত্য rendered as उदयदित्य 7 times against उदयादित्य 214 times
elsewhere - the exact drift MEMO's Goal names as the motivating example,
missed by the mechanical `review.py` pass because both forms already tied
to the same canonical within one chapter, so neither its "drift" nor its
"unresolved" report catches it; found only by a direct follow-up
question) was unified to उदयादित्य. All via the workflow in
`all/aligned/README.md` ("Correcting the published text"). The
Bengali-side gap found during review (পিতা missing its oblique form
পিতার) is already fixed in `cluster-bn.jsonl`/`normalized-bn.jsonl` and
re-anchored. No open items remain.
