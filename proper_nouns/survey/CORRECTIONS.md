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

Review status: hi, en, and ja have all been reviewed (see MEMO). hi and ja
turned up no target-language-local corrections - hence no section for
them below. The Bengali-side gap found during review (পিতা missing its
oblique form পিতার) is already fixed in `cluster-bn.jsonl`/
`normalized-bn.jsonl` and re-anchored, so it's not listed here either.

## English

- ch13: দাদা - Basanta Ray's affectionate address to Udayaditya - renders
  as "Grandson" in segment 2 (both occurrences there) and as "Dada" in
  segment 10 (both occurrences there), same word, same speaker, same
  addressee, same chapter. Confirmed still present after the re-anchor.
  Target-language-local: unify to one spelling in the chapter 13 English
  text.
- ch7, ch24, ch26: মহারাজ/রাজা (direct address to a king) renders
  inconsistently as "Maharaj" vs "Your Majesty" within the same chapter -
  ch7 has Ramai say both "Your Majesty" (seg 4, 11, 39) and "Maharaj" (seg
  26, 28, 35, 44) to Ramchandra Ray; ch24 has Rammohan say both to
  Ramchandra Ray likewise (seg 5 "Your Majesty" vs seg 7/9/13/15
  "Maharaj"); ch26 has Rammohan say "Your Majesty" to Ramchandra Ray where
  every other chapter (26 of them) settles on "Maharaj" for direct address.
  Target-language-local: the corpus-wide convention is "Maharaj"
  (transliterated, not translated); ch7, ch24 and ch26's "Your Majesty"
  instances are the outliers.
