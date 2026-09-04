# Corrections found during review

A standing record of proper-noun corrections found while reviewing
`anchor-{hi,en,ja}.jsonl` against `normalized-bn.jsonl` and the source
text, and applied to the actual translations. `anchor-*.jsonl` itself is
a derived analysis file, not the fix target - the fix target is the
translation text in `all/aligned/{hi,en,ja}-*.jsonl`, reached via
`all/{en,hi,ja}-gemini.md` per `all/aligned/README.md`'s "Correcting the
published text". This file is kept as a log, not deleted when a pass
finishes - each section below is one review pass.

Two kinds of entries:

- **Bengali-side**: a name the survey/clustering got wrong or missed.
  Fixed via `cluster.py`'s `patch()` on `cluster-bn.jsonl`, then
  `normalized-bn.jsonl` and any `anchor-*.jsonl` rebuilt.
- **Target-language-local**: two spellings/forms in one language's
  translation that should be one, with no Bengali-side problem
  (`normalized-bn.jsonl` is already correct) - a manual edit to the
  translation text.

## Pass 1: hi/en/ja review against `normalized-bn.jsonl`

Review order: hi first, then en and ja (see `project-bengali-bv-no-distinction`
memory). ja turned up no target-language-local corrections.

Target-language-local, applied via `all/aligned/README.md`'s workflow,
committed in c00755d:

- hi ch1: উদয়াদিত্য rendered as `उदयदित्य` 7 times against `उदयादित्य`
  214 times elsewhere. Missed by the mechanical `review.py` pass because
  both forms were already tied to the same canonical within one chapter,
  so neither its "drift" nor its "unresolved" report catches it - found
  only by a direct follow-up question, not by the review process itself.
  Unified to `उदयादित्य`.
- en ch13: দাদা rendered as both "Grandson" and "Dada". Unified to "Dada".
- en ch7/ch24/ch26: মহারাজ rendered as both "Your Majesty" and "Maharaj".
  Unified to "Maharaj".
- en ch6: "Dadamahashay"/"Dada Mahashay" spacing, found while answering a
  follow-up question, not from the original `anchor-en.jsonl` review.
  Unified to "Dada Mahashay".

Bengali-side, fixed in `cluster-bn.jsonl`/`normalized-bn.jsonl` and
re-anchored, committed in a5f9b48:

- পিতা was missing its oblique form পিতার.

## Pass 2: multi-form sweep (MEMO's "Work remaining" item 1)

A pass over every entity with more than one string in `forms`, across
`anchor-{en,hi,ja}.jsonl`, looking for the same blind spot as pass 1's
উদয়াদিত্য case: forms already tied to one canonical within a chapter, so
invisible to `review.py`'s drift/unresolved reports. Person- and
place-kind entities were checked individually against the source text;
most multi-form spreads are ordinary inflection, honorifics, shortenings
or title-plus-name expansions and needed no fix. Title-kind entities with
a moderate, plausible-both-ways split (hi's साहब/साहेब, both valid Hindi
spellings of "sahib") were left alone - only clear majority-vs-rare-
outlier splits that read as slips were corrected.

Target-language-local, applied via `all/aligned/README.md`'s workflow
(`all/aligned fold-{en,hi,ja}` then `pack-{en,hi,ja}`, `make convert` to
confirm the round trip):

- hi ch33/34: প্রতাপাদিত্য's Pathan general মুক্তিয়ার খাঁ, introduced
  correctly as "मुक्तियार ख़ाँ" in ch31, drifted to "मुख़्तार"/"मुख़्तार
  ख़ान" for 45 occurrences across the ch33/34 abduction scene. Unified to
  "मुक्तियार" (kept "ख़ान" as its own separate, acceptable spelling). By
  far the largest of this pass's finds.
- en ch16: "Pratapditya" (missing the second "a") -> "Pratapaditya".
- en ch33/34: "Dada Mashay" (missing "ha"), 5 occurrences -> "Dada
  Mahashay".
- ja ch33/34: "ウダヤヤディティヤ" (duplicated mora), 2 occurrences ->
  "ウダヤディティヤ".
- The same sentence (ch24, রামচন্দ্র রায়'s jealousy of রমাই) dropped
  রমাই's first syllable independently in two languages: hi's "माई" ->
  "रमाई" (also fixed the verb's gender agreement, feminine -> masculine)
  and ja's "マイ" -> "ラマイ".

Confirmed as *not* errors, despite looking like outliers at first: hi's
"विभु"/en's "Vibhu"/ja's "ビブ" (all singular, ~1 occurrence against the
name's usual "विभा"/"Vibha"/"ビバ") are a deliberate pet-name the
Bengali source itself uses once, at ch32's "কোথায় পাঠাব বিভু" - all
three translations correctly preserved it.

No open items remain from either pass; the next thing this file needs is
a new section if a future pass (or `all.tsv` comparison work) turns up
more.

## Pass 3: `all.tsv` review against the English column

A spot review comparing `all.tsv`'s Japanese column against its English
column, looking for titles where the English is a translated word or
phrase but the Japanese had stayed a transliteration.

Target-language-local (Japanese only; `normalized-bn.jsonl` and the
en/hi columns were already correct), applied via `all/aligned/README.md`'s
workflow:

- ja: দিল্লীশ্বর, "Emperor of Delhi" in English, was "ディリーシュワル"
  (transliteration) - unified to "デリー皇帝" (10 occurrences).
- ja: ঈশ্বর, "God" in English, was "イーシュワル" (transliteration) in
  its two generic-noun uses (ch2 line 169, ch34 line 2161) - unified to
  "神". A third occurrence (ch2 line 123, দিল্লীশ্বর ত আমার ঈশ্বর নহেন)
  was already "神" and needed no change.
- ja: যশোহর-অধিপতি ("ジョソール君主") and যশোহর-পতি ("Lord of Jessore" in
  English, already "ジョソール王" in the one place it occurs, ch6 line
  589) name the same person and role - both refer to Pratapaditya,
  confirmed by reading ch1 line 9 and ch6 line 589 in `all/bn.md` -
  unified to "ジョソール王" (1 occurrence changed, ch1 line 9).
