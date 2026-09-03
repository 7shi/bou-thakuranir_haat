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

(review complete - see MEMO for the drift/elsewhere-linked/never-linked
breakdown. পিতা ("father") was missing its oblique form পিতার from
`cluster.py`'s `FORMS`/sweep, so ch10's "पिताजी" - Udayaditya referring to
Pratapaditya - went unresolved; fixed in `cluster-bn.jsonl`/
`normalized-bn.jsonl` and re-anchored, now resolved. No remaining
findings for hi.)

## English

- ch10: same পিতা gap as hi's - en's "Father"/"Uncle" (Udayaditya
  referring to Pratapaditya and to Basanta Ray) went unresolved for the
  same reason; fixed and re-anchored, now resolved.
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
- The rest of the "never linked" unresolved forms (31 total) were sampled
  across all four `kind`s and most of the involved chapters (Chakor/ch4,
  Kabuli/ch4, Agamani/ch9, Brahmastra/ch21 (idiom, "brought out her
  Brahmastra"), Brahmin/ch9, Sanskrit/ch29, "Tajbe Taj Naube Nau"/ch27 (a
  song refrain), Sire/ch3, Sister/ch15, He/ch4 (pronoun mistaken for a
  name inside a proverb quote), Her/ch11 (reverent capitalized pronoun for
  the Mother goddess), plus the ones already checked during hi's review
  under the same Bengali words: Pathan/ch4-5, Raag Hindol/ch6, Rahu/ch2+7,
  Subhadraharan/ch21, Ashvin/ch8, Nandan Kanan/ch32, Yamalaya/ch31,
  Raja-Maharaja/ch25, Rajadhiraj/ch8=King of Kings/ch8). All are
  mythological/religious/musical references, idioms, or generic titles -
  no further Bengali-side gaps found among them.

## Japanese

(not yet reviewed)
