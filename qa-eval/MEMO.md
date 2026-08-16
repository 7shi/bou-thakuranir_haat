# Memo: chunk granularity, and why it stays as it is

A working note on a question that came up while comparing answerer models:
would a finer segmentation help, given that the answerer degrades on larger
contexts? Conclusion first: **no change to segmentation.** The evidence says
recall is the binding constraint and finer units cost recall.

## The observation that started it

Japanese Hybrid k=10 scores worse than k=8, which invites the reading that the
extra chapters confuse the model. That reading is correct, but the mechanism is
worth stating precisely, because it is *not* a retrieval failure:

| | gold recall k=8 | k=10 | questions losing coverage | mean context segments |
| --- | ---: | ---: | ---: | ---: |
| en | 45 | 46 | 0 | 19.6 → 23.6 |
| ja | 47 | 48 | 0 | 20.5 → 24.8 |

The union is monotone — top-8 ⊆ top-10 — so raising `k` can only add chapters,
and recall rises with it. No question loses gold coverage. The three Japanese
questions that regress at k=10 (Q32, Q34, Q37) all keep full gold coverage while
doing so. The damage is done by the *non-gold* chapters that come along: pure
synthesis degradation from a larger context.

## The hypothesis: units are too coarse

The retrieval unit is a scene (`chapter:segment`), 82 of them per language:

| | segments | mean chars | median | max | lines/segment |
| --- | ---: | ---: | ---: | ---: | ---: |
| en | 82 | 3,594 | 3,217 | 12,488 | 13.8 |
| ja | 82 | 1,658 | 1,517 | 5,324 | 13.8 |

A question is usually answered by a few lines inside that. So each hit drags in
a lot of unrelated text, and `ch.prec` of 0.17-0.18 in the per-model report says
the same thing from the other side. Halving the unit is the obvious idea.

## Why it was rejected

**1. Finer units have already been measured, and they lose recall.**
Line-granularity retrieval ([VECTOR-HYBRID.md](VECTOR-HYBRID.md)) is exactly the
single-scale finer experiment:

| | sr@5 | prec@5 |
| --- | ---: | ---: |
| en Segment | 36/50 | 0.34 |
| en Line | 33/50 | 0.40 |
| ja Segment | 36/50 | 0.33 |
| ja Line | 31/50 | 0.39 |

Precision improves and strict recall drops. With less text per unit the cosine
distribution turns peaky — line cosines run systematically higher (+0.04 mean)
and lines that match the question's surface wording crowd out the gold scene.
The same document records Mix (A) taking the highest precision of any method
(en prec@5 0.47) without that converting into coverage.

**2. Recall is the binding constraint, so that trade is the wrong direction.**
The Ceiling run establishes that comprehension is near-perfect once the right
chapters are present, which makes end-to-end QA quality almost equivalent to
retrieval recall. Buying precision with recall spends the scarce resource to get
the abundant one.

**3. A finer retrieval unit does not shrink the context by itself.** Retrieval
granularity and context granularity are separate choices: `answer_vector.py
--line` retrieves lines but still assembles context at segment level. To
actually reduce context size the context would have to be cut down too — which
reintroduces, on the synthesis side, the missing-surrounding-text weakness that
made line-only retrieval peaky in the first place.

Halving the segment (~7 lines, ~1.6k chars in English) is a genuinely untested
middle point between line and scene. But the direction of degradation is already
visible at the line end, so the expected outcome is a small precision gain with
recall flat at best.

## Methodological note: do not tune segmentation on gold

Gold chapters are per-question annotations, so any "share of the context that is
gold" figure is a property of the (question, retrieval) pair, not of the
segmentation. Choosing a chunk size to maximize it would be fitting the
segmentation to these 50 questions — the same error
[HYBRID.md](HYBRID.md) already calls out for the RRF parameter sweep, where the
best K and weights are post-hoc selections on the test set and the dense-bias
direction is itself learned from these questions.

The two uses have to stay separate:

- **Gold as an evaluation metric** — fine, and already in use (`ch.recall`,
  `ch.prec`), for reporting after the fact.
- **Gold as a design parameter** — not fine, for chunk size as much as for `k`.

Segmentation must be decided on question-independent grounds: target length,
scene and topic boundaries, the embedding model's effective input length. The
current `segmentations.jsonl` is derived from text structure and never sees the
questions, so that property holds today and should be preserved. Note that `k=8`
was itself chosen on these 50 questions, so comparisons against it already carry
that caveat.

## Where the k=10 problem actually belongs

Since gold coverage is monotone in `k` and the regressions keep their gold
chapters, the k=10 issue is not about how the text is divided. It is about **how
wide the union is** — how many non-gold chapters are admitted alongside the gold
ones. That is where to look for an improvement: a cutoff that admits fewer
non-gold chapters at equal recall, rather than a different segmentation.
