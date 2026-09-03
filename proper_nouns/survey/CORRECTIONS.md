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

## Hindi

- ch10: "pitaaji" and "baba" both render Bengali "baba" (title, generic
  "father" - Ramapati addressing Ramchandra Ray, and Udayaditya addressing
  Pratapaditya). Target-language-local: unify to one spelling in the
  chapter 10 Hindi text.

## English

(not yet reviewed)

## Japanese

(not yet reviewed)
