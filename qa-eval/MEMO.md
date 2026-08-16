# Memo: retrieval-side questions from the per-model runs

A working note on two questions raised while comparing answerer models in
[results/README.md](results/README.md), both about retrieval rather than about
any model. Conclusions first:

- **How much of the gold coverage is won on the k=8 boundary?** A real but
  bounded amount — 5% en / 2% ja of covered gold chapters. Not enough to
  undermine an answerer comparison.
- **Would a finer segmentation help, given that the answerer degrades on larger
  contexts?** No change to segmentation. Recall is the binding constraint and
  finer units cost recall.

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

## How much gold coverage sits on the k=8 boundary

A separate worry about the same cutoff. Query embeddings are not bit-stable
across ollama backends — ROCm vs Vulkan moves cosines in the 4th decimal — and
that was enough to change four Japanese `expanded` lists, because the affected
chapters sat within ~0.0002 of the k=8 cutoff. Which raises the question of how
much gold coverage was won by that kind of margin in the first place. A gold
chapter held at rank 7-8 by a single retriever is in the context by a thin
accident of ranking, not because retrieval solidly found it.

Counting gold chapters that no retriever ranks above 7 and that only one
retriever surfaces at all:

| Lang | Q | gold ch. | held by |
| --- | --- | --- | --- |
| en | 27 | 33 | dense rank 7, BM25 absent |
| en | 41 | 5 | dense rank 8, BM25 absent |
| en | 42 | 29 | dense rank 7, BM25 absent |
| en | 48 | 11 | BM25 rank 8, dense absent |
| ja | 36 | 17 | BM25 rank 7, dense absent |
| ja | 43 | 37 | BM25 rank 8, dense absent |

Against 81 covered gold chapters in English and 82 in Japanese, that is **5% en
/ 2% ja** riding on one boundary slot. Most gold coverage has room to spare, so
the tail is a real but bounded fragility. Note also that only the three
dense-held English cases are exposed to embedding drift at all; the BM25 side is
bit-identical across runs in both languages.

Two responses, one adopted and one rejected:

- **Adopted: stop recomputing retrieval when the answerer is the variable.**
  `answer_hybrid.py --retrieval` replays a stored run's `hits` and `expanded`,
  which is what the per-model `make hybrid8` now does. The drift then cannot
  occur at all, and a ceiling run avoids the whole question by construction.
- **Rejected: raise `k` to give these cases margin.** It would work, but the
  cost is the k=10 regression above: a larger `k` only ever adds chapters, so
  the margin is bought with non-gold context that the answerer then has to
  survive.

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
