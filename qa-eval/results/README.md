# Per-model answerer runs

This directory holds runs with **answerer models other than the default**
`google:gemma-4-31b-it`, without touching the canonical `results-<lang>/`
trees — the existing per-strategy results stay as they are, and each new
(method, model, language) triple gets its own file here.

Two methods are available:

- **hybrid8** — Hybrid k=8 (dense ∪ BM25 union; [HYBRID.md](../HYBRID.md))
  context, **replayed** from the canonical `results-<lang>/hybrid8.jsonl` via
  `answer_hybrid.py --retrieval` rather than recomputed. Retrieval is supposed to
  be model-independent, but the dense side embeds the question at run time and
  that is not bit-stable across ollama backends — ROCm vs Vulkan moves cosines in
  the 4th decimal, enough to swap a chapter sitting near the top-8 cutoff (see
  [MEMO.md](../MEMO.md)). Replaying pins `hits` and `expanded`, so every model
  here answers a byte-identical context and only the answer is generated.
- **ceiling** — no retrieval at all: the gold chapters as context
  (`answer_ceiling.py`). This is the cleaner model comparison: the context is
  fixed by the gold annotation, so it is byte-identical for every model and
  every run with nothing to pin, and the whole difference is synthesis. It is
  also much smaller than a hybrid8 context, hence cheaper and faster per
  question.

Filenames encode the method, model and language so multiple experiments coexist
("`:`" and "`/`" in the model string are replaced by "`_`"):

- `<METHOD>-<MODEL>-<LANG>.jsonl` — answers, e.g.
  `hybrid8-google_gemini-4-31b-it-ja.jsonl`
- `judge-<METHOD>-<MODEL>-<LANG>.jsonl` — verdicts (`judge.py`, opt-in)

The method leads so runs group by method, and the language trails so it can be
read straight off the filename — the model is the only field that may itself
contain "`-`".

`report.py` aggregates every judged pair in this directory into
[report.md](report.md).

The judge stays the default `ollama:qwen3.6` for comparability with the main
table in [README.md](../README.md).

## Usage

Run via [Makefile](Makefile) (the directory's default target prints the usage
line):

```
make hybrid8 MODEL=... LANG={en,ja}   # answer 50 questions → hybrid8-<MODEL>-<LANG>.jsonl
make ceiling MODEL=... LANG={en,ja}   # answer 50 questions → ceiling-<MODEL>-<LANG>.jsonl
make judge                            # opt-in: grade every ungraded answer file
make report                           # aggregate every judged run → report.md
```

- `MODEL` — llm7shi model string of the answerer (e.g.
  `google:gemini-4-31b-it`, `ollama:gemma4:31b-it-qat`)
- `LANG` — `en` | `ja` (selects the questions file and, for hybrid8, the
  reference run whose retrieval is replayed)

`make judge` needs neither: it scans this directory for answer files that have
no `judge-` counterpart yet and reads the language off each filename.

Example:

```
make ceiling MODEL=google:gemini-4-31b-it LANG=ja
```

## Ceiling: comparing answerer models

`ceiling` puts the gold chapters in the context and nothing else, so the context
is byte-identical for every model and every run, with nothing to pin. Retrieval
is not a variable at all here and the whole difference is **synthesis**, which
is what makes this the comparison worth growing: one more model costs 100
questions and no index.

| Answerer | Model | English | Japanese |
| --- | --- | --- | --- |
| `google:gemma-4-31b-it` | hosted (canonical run) | 49/50 (0.990) — 49/1/0 | 47/50 (0.970) — 47/3/0 |
| `ollama:qwen3.8` | 27.3B dense, Q4_K_M | 49/50 (0.990) — 49/1/0 | 48/50 (0.970) — 48/1/1 |
| `ollama:qwen3.6` | 36B MoE, Q4_K_M | 48/50 (0.980) — 48/2/0 | 47/50 (0.960) — 47/2/1 |
| `ollama:muse-glimmer` | 27.9B, Q4_K_M | 48/50 (0.980) — 48/2/0 | 46/50 (0.960) — 46/4/0 |
| `ollama:gemma4:26b-a4b-it-qat` | 25.2B MoE, 4B active, Q4_0 | 46/50 (0.950) — 46/3/1 | 41/50 (0.900) — 41/8/1 |

(`correct`/50 with the weighted score in parentheses, then correct/partial/incorrect.
The Gemma 4 row is the canonical `results-<lang>/ceiling.jsonl` run; the other
four live in this directory and are aggregated in [report.md](report.md).)

* **The set is near-saturated in English for everything above ~25B active
  parameters.** Four of the five models land within 0.010 of each other
  (0.980–0.990), and every English miss among them is a `partial`. Ceiling is a
  ceiling:
  it measures whether a model can read two or three chapters it has already been
  handed, and current models mostly can.
* **Japanese costs every model something**, from 0.020 (Gemma 4, muse-glimmer) to
  0.050 (gemma4:26b-a4b). No model scores higher in Japanese than in English, and
  the English miss list has 5 questions against Japanese's 11 — the same
  questions, the same gold, the same gold chapters.
* **Only the small MoE separates itself.** `gemma4:26b-a4b-it-qat` activates 4B
  parameters per token and is the only model below 0.950; it loses 0.050 from
  English to Japanese where every other model loses 0.020. Its failure mode is
  legible in the verdicts: 8 `partial` and 1 `incorrect` in Japanese, i.e. it finds the passage and drops
  one of the two or three elements the gold answer enumerates (ja Q34 gives the
  escape → death chain but not Rukmini's denunciation; ja Q44 contrasts the
  jewellery with the plain clothes but not the beggar-woman impression; ja Q50
  has Vibha waiting for Surma but not Rammohan's later remark).
* **Its one outright error is a single-hop lookup**, en Q17 — "how many days does
  Mangala spend preparing the poison" answered as "the entire night" against a
  gold "five days", with the chapter in the context. Every other model gets it.
  That is the one place in this table where a model reads a supplied chapter
  wrongly rather than incompletely.
* **The judge is `ollama:qwen3.6`, one of the answerers.** A same-family
  preference cannot be ruled out from these runs, though qwen3.6 does not top
  either language — it sits mid-table behind Gemma 4 and qwen3.8, which is weak
  evidence against a strong self-preference rather than proof of none.

### Every question any model missed

| Q | type | ch. | Gemma 4 | qwen3.8 | qwen3.6 | muse-glimmer | 26b-a4b |
| --- | --- | --- | --- | --- | --- | --- | --- |
| en 6 | single | 1 | correct | correct | partial | partial | correct |
| en 17 | single | 1 | correct | correct | correct | correct | **incorrect** |
| en 33 | cross | 2 | correct | correct | correct | correct | partial |
| en 35 | cross | 2 | correct | correct | correct | correct | partial |
| en 48 † | cross | 2 | partial | partial | partial | partial | partial |
| ja 29 | cross | 2 | partial | partial | partial | correct | partial |
| ja 34 | cross | 3 | correct | correct | correct | partial | partial |
| ja 35 | cross | 2 | correct | correct | correct | partial | partial |
| ja 36 | cross | 3 | partial | correct | partial | correct | correct |
| ja 37 | cross | 2 | correct | correct | correct | correct | partial |
| ja 40 | cross | 2 | correct | correct | correct | correct | partial |
| ja 43 | cross | 2 | correct | correct | correct | partial | correct |
| ja 44 | cross | 3 | correct | correct | correct | correct | partial |
| ja 46 | cross | 3 | correct | correct | correct | correct | partial |
| ja 48 † | cross | 2 | partial | incorrect | incorrect | partial | incorrect |
| ja 50 | cross | 3 | correct | correct | correct | correct | partial |

† Q48's gold answer is disputed; its verdicts are held under reservation — see
[Q48](#q48-a-defect-in-the-question-not-in-the-models) below.

Ceiling doubles as a sanity check on the gold itself: with the gold chapters in
the context, a `correct` verdict says the question and its gold answer agree.
Only the 16 rows above need auditing — the other 45 English and 39 Japanese
questions are answered from the gold chapters by all five models — and of those
only Q48 turned out to be a question-side problem.

* **Q48 is the only universal miss**, in both languages and across all five
  models: 10 ceiling verdicts, none `correct`. That is the signature of a broken
  question rather than a hard one.
* **Nothing here is a missing-evidence failure** — the context is the gold
  annotation, so every miss is synthesis inside two or three chapters.
* **Multi-chapter `cross` questions carry the difficulty.** 14 of the 16 rows are
  `cross`, and the two `single` rows belong to en Q6 (a two-part answer where
  qwen3.6 and muse-glimmer name the broken strings but not the snatched mezrab)
  and to gemma4:26b-a4b's en Q17.
* **ja Q29 and ja Q36 are language ability, not question quality.** Both are
  parallel across languages — same question, same gold answer, same gold
  chapters — and both are answered correctly in English by every model; every
  Japanese-only miss in the table is of this kind. qwen3.8 on Q29 is the clearest
  case: from the same two chapters, its English answer reaches the poisoning and
  Surma's death, while its Japanese answer stops at the public confrontation —
  the threat to imprison Udayaditya and the queen relaying it — and never reaches
  the errand the queen sends Matangini on or the poison Mangala brews from it.
  Gemma's Q29 is the mildest form: its Japanese answer states the same facts as
  its English one but stops short of naming Surma's death, a completeness gap
  rather than a comprehension failure.
* **ja Q29 is the most discriminating question in the set**, and muse-glimmer
  shows it is not broken: four models miss it in Japanese, and the fifth answers
  it in one sentence — 「スルマが毒を飲んで死に至ったこと」 — that names exactly
  the scored fact the other four never reach. The gold is sound, both languages
  are answerable, and it separates models. It is worth keeping exactly as it is.
* **Q29's gold carries one imprecision, which does not change the reading.** It
  credits the commission to "the Mahishi's maid, Matangini", while chapter 17
  has the Rajmahishi as the principal — Matangini is only sent to fetch the
  medicine, and Mangala substitutes poison for it on her own initiative. Both
  language versions word it the same way, so nothing is asymmetric between them,
  and no verdict turns on it: the failing Japanese answers stop well short of
  that detail, on the poisoning itself. The gold is left as it is, along with
  Q48's.

## Hybrid8 vs. ceiling: what retrieval costs

Two models have been run under both methods — the default
`google:gemma-4-31b-it` and `ollama:qwen3.8` — and both read **byte-identical
contexts** under each. The Gemma numbers are the canonical
`results-<lang>/{hybrid8,ceiling}.jsonl` runs; the qwen3.8 hybrid8 runs replay
`hits` and `expanded` straight from `results-<lang>/hybrid8.jsonl`. So retrieval
is not a variable *between the models* either, and the ceiling → hybrid8 step is
the price of answering from a k=8 retrieved context instead of the gold one.

| Language | Method | `google:gemma-4-31b-it` | `ollama:qwen3.8` |
| --- | --- | --- | --- |
| en | ceiling | 49/50 (0.990) — 49/1/0 | 49/50 (0.990) — 49/1/0 |
| en | hybrid8 | 46/50 (0.940) — 46/2/2 | 49/50 (0.990) — 49/1/0 |
| ja | ceiling | 47/50 (0.970) — 47/3/0 | 48/50 (0.970) — 48/1/1 |
| ja | hybrid8 | 45/50 (0.940) — 45/4/1 | 46/50 (0.940) — 46/2/2 |

- **In English qwen3.8 pays nothing for retrieval.** Its hybrid8 verdicts are
  identical to its own ceiling verdicts on all 50 questions — same single
  `partial` (Q48), same 0.990 — even though the hybrid8 context misses gold
  chapters on 5 of 50 questions. Gemma drops 0.050 over the same step.
- **In Japanese both models pay.** Gemma drops 0.030 (0.970 → 0.940) and
  qwen3.8 drops the same 0.030 from a slightly different ceiling distribution
  (48/1/1 vs Gemma's 47/3/0 — equal weighted, more all-or-nothing), so the two
  end level at 0.940.

### Hybrid8: every question either model missed

| Lang | Q | type | Gemma 4 | qwen3.8 | gold in context |
| --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | correct | yes |
| en | 29 | cross | incorrect | correct | yes |
| en | 32 | cross | partial | correct | **no** |
| en | 48 † | cross | partial | partial | yes |
| ja | 27 | cross | partial | partial | **no** |
| ja | 29 | cross | incorrect | incorrect | yes |
| ja | 36 | cross | partial | correct | yes |
| ja | 42 | cross | correct | incorrect | **no** |
| ja | 44 | cross | partial | correct | yes |
| ja | 48 † | cross | partial | partial | yes |

† Same reservation as the ceiling table.

* **Cross-reference synthesis is most of the gap:** 5 of the 6 questions the two
  models disagree on are `cross`, and qwen3.8's Japanese wins both convert a
  Gemma `partial` (evidence present, elements dropped) into a `correct`.
* **Two disagreements prove nothing either way.** en Q32 and ja Q42 — including
  qwen3.8's only regression — are shared blind spots ([HYBRID.md § Shared blind
  spots](../HYBRID.md#shared-blind-spots)) whose gold chapters are absent from
  the context, so a `correct` there reflects prior knowledge or a lenient judge
  rather than reading comprehension. Restricting to questions whose gold
  chapters are actually present, English (n=45) goes 42/1/2 → 44/1/0 and
  Japanese (n=47) 43/3/1 → 45/1/1: on the evidence it was actually given,
  qwen3.8 never misses an English question outright, and the direction is
  unchanged in Japanese.
* **ja Q27 is the good failure mode:** its gold chapters are not in the context
  and qwen3.8 says so outright — the answer names the failed assassination plan
  and states that the successful method is not described — rather than inventing
  one. Both blind-spot losses are `correct` at ceiling, so evidence is all it
  was missing.
* **ja Q29 is the one place where more context hurt.** qwen3.8 reaches `partial`
  with the gold chapters alone but answers about an unrelated subplot when those
  same chapters sit inside a k=8 context: long-context distraction, not missing
  evidence. Gemma misses it in both settings too.

## Q48: a defect in the question, not in the models

Q48 asks how Ramchandra interprets "his brother-in-law's behavior" after the
midnight rescue, and the natural referent of *behavior* is the protective action
the same sentence names. That is what the models answer: Ramchandra found the
rescue "bound to happen" and credited it to Udayaditya's concern for his sister
Vibha rather than for him. The gold answer instead requires a separate aside in
chapter 19 — Ramchandra sees Udayaditya whisper to a servant and assumes a plot
to insult him — which sits in a list of anecdotes about the king's touchiness
and is not connected to the rescue at all.

* **All fourteen verdicts converge, and none is `correct`.** Five models at
  ceiling in two languages, plus two models × two languages under hybrid8, and no
  run mentions the whispering. Independent models agreeing against the gold
  points at the question, which ties the scored fact to a premise that does not
  lead to it.
* **Evidence was never the issue.** Ceiling supplies the gold chapters by
  construction, and retrieval also succeeds on Q48 in both hybrid8 runs, so no
  run of either method ever lacked the passage. The gold is the only remaining
  explanation, and the verdicts are flat across methods — exactly what a
  question-side problem looks like.
* **The Japanese `incorrect`s at ceiling are judge variance on top of that.**
  English answers tend to add the court mockery scene where the Japanese ones
  stop at the two rationalizations, but the content gap is smaller than the
  verdict gap, and the same Japanese answer style scores `partial` under hybrid8.
* **Contrast with ja Q29,** which shows a similar "nearly everyone misses it"
  signature for the opposite reason: Q29 is answered in English by every model
  and in Japanese by one, so cross-language agreement is what separates a hard
  question from a broken one. A question models miss in one language is a
  finding; one they miss in both, in every model, deserves an audit of its gold.
* **The gold stays as it is** so these runs remain comparable with every earlier
  result, so every score in this document counts Q48 as scored. Every model would
  gain one verdict in every run if it were re-annotated or dropped.

## Prompt ordering: the ROCm red herring

An early `ollama:qwen3.6` hybrid8 run appeared to lose the question entirely:
instead of answering, the model replied to the context as if it were a pasted
excerpt. The obvious reading was weak long-range attention over the ~10-24k
token hybrid8 context, so `answer_question` was restructured to send
`[context, preamble, question]` as separate parts — the RAG convention of
putting the question last, next to the answer position.

That diagnosis was wrong. The failure is specific to the **ROCm** backend; with
the **Vulkan** backend the original single merged prompt (question first,
context after) answers correctly on the same model and the same contexts. The
restructuring is therefore reverted, for two reasons beyond it being
unnecessary:

1. **Question-first is itself the more interesting test.** Putting the question
   last makes it harder to lose, which is precisely why it hides the failure
   mode worth measuring here — whether a model loses the *beginning* of a long
   prompt.
2. **Changing the prompt invalidates the existing answers.** Every result in
   `results-<lang>/` and in this directory was produced with the question-first
   prompt; a prompt change should come with a full re-run, not a silent mix of
   two prompt shapes in one table.

So the prompt shape stays as originally written, and backend choice — not
prompt engineering — is what to check when a local model appears to ignore the
question.

## Notes

- Both scripts are **resume-safe**: they append and skip question IDs already
  present in the output file, so an interrupted run is continued by re-running
  the same command.
- **Neither method needs the embedding index.** hybrid8 replays a stored
  retrieval and ceiling does none, so no run here loads
  `qa-eval/index-<lang>.safetensors`, builds a BM25 index, or calls the
  embedding model. The reference run `results-<lang>/hybrid8.jsonl` must exist;
  it is produced by the parent Makefile, not by this one.
- The replay resolves the reference `expanded` list against
  `all/<lang>-gemini.jsonl` and asserts every scene is found, so a reference run
  built on a different scene set fails loudly instead of silently answering a
  different context.
- The parent `report.py` does not scan this directory (its method discovery
  reads only `results-<lang>/hybrid<k>.jsonl`), so these runs never leak into
  the main table. `make report` here is the independent aggregation: it reuses
  the parent's `accuracy` / `retrieval` helpers but simply tallies every
  `judge-*.jsonl` present in this directory and writes `report.md`.
- `report.md` is generated — re-run `make report` after judging a new model
  rather than editing it by hand.
