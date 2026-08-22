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

| Model | English | Japanese |
| --- | --- | --- |
| `google:gemma-4-31b-it` | 49/50 (0.990) — 49/1/0 | 47/50 (0.970) — 47/3/0 |
| `ollama:gemma4:26b-a4b-it-qat` | 46/50 (0.950) — 46/3/1 | 41/50 (0.900) — 41/8/1 |
| `ollama:qwen3.6` | 48/50 (0.980) — 48/2/0 | 47/50 (0.960) — 47/2/1 |
| `ollama:qwen3.8` | 49/50 (0.990) — 49/1/0 | 48/50 (0.970) — 48/1/1 |
| `ollama:muse-glimmer` | 48/50 (0.980) — 48/2/0 | 46/50 (0.960) — 46/4/0 |
| `openrouter:stealth/ox-alpha` | 48/50 (0.970) — 48/1/1 | 49/50 (0.990) — 49/1/0 |

(`correct`/50 with the weighted score in parentheses, then correct/partial/incorrect.
The Gemma 4 row is the canonical `results-<lang>/ceiling.jsonl` run; the other
five live in this directory and are aggregated in [report.md](report.md).)

* **The set is near-saturated in English for most models.** Five of the six
  land within 0.020 of each other (0.970–0.990), and within that band every
  miss is a `partial` except `stealth/ox-alpha`'s single outright error on Q22.
  Ceiling is a ceiling: it measures whether a model can read two or three
  chapters it has already been handed, and current models mostly can.
* **Japanese costs every model something except `stealth/ox-alpha`**, from
  0.020 (Gemma 4, muse-glimmer) to 0.050 (gemma4:26b-a4b). `stealth/ox-alpha`
  runs the other way, gaining 0.020 in Japanese. The English miss list has 6
  questions against Japanese's 11 — the same questions, the same gold, the
  same gold chapters.
* **`stealth/ox-alpha` is the one model that scores higher in Japanese than
  English.** Its 0.990 Japanese ceiling — a single `partial`, on the disputed
  Q48 — is the highest Japanese score of the six models, despite the model
  sitting mid-table in English. No other model reverses direction between
  languages.
* **Only the small MoE separates itself on magnitude.** `gemma4:26b-a4b-it-qat`
  activates 4B parameters per token and is the only model below 0.950; it loses
  0.050 from English to Japanese — more than double any other model's loss
  (0.020, aside from `stealth/ox-alpha`'s gain). Its failure mode is legible in
  the verdicts: 8 `partial` and 1 `incorrect` in Japanese, i.e. it finds the
  passage and drops one of the two or three elements the gold answer enumerates
  (ja Q34 gives the escape → death chain but not Rukmini's denunciation; ja Q44
  contrasts the jewellery with the plain clothes but not the beggar-woman
  impression; ja Q50 has Vibha waiting for Surma but not Rammohan's later
  remark).
* **The two outright ceiling errors are both single-hop misreadings of a
  supplied chapter, not incomplete synthesis.** gemma4:26b-a4b's en Q17
  answers "the entire night" against a gold "five days" for how long Mangala
  spends preparing the poison, though every other model gets it.
  `stealth/ox-alpha`'s en Q22 answers "Sitaram's own cloth" where the gold and
  every other model say Udayaditya's own cloth binds the guard. Different
  model, different question, same failure shape.
* **The judge is `ollama:qwen3.6`, one of the answerers.** A same-family
  preference cannot be ruled out from these runs, though qwen3.6 does not top
  either language — it sits mid-table behind Gemma 4 and qwen3.8 in English and
  behind `stealth/ox-alpha` in Japanese too — which is weak evidence against a
  strong self-preference rather than proof of none.

### Every question any model missed

| Q | type | ch. | gemma 4 (31b) | (26b-a4b) | qwen3.6 | qwen3.8 | muse-glimmer | ox-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| en 6 | single | 1 | correct | correct | partial | correct | partial | correct |
| en 17 | single | 1 | correct | **incorrect** | correct | correct | correct | correct |
| en 22 | single | 1 | correct | correct | correct | correct | correct | **incorrect** |
| en 33 | cross | 2 | correct | partial | correct | correct | correct | correct |
| en 35 | cross | 2 | correct | partial | correct | correct | correct | correct |
| en 48 † | cross | 2 | partial | partial | partial | partial | partial | partial |
| ja 29 | cross | 2 | partial | partial | partial | partial | correct | correct |
| ja 34 | cross | 3 | correct | partial | correct | correct | partial | correct |
| ja 35 | cross | 2 | correct | partial | correct | correct | partial | correct |
| ja 36 | cross | 3 | partial | correct | partial | correct | correct | correct |
| ja 37 | cross | 2 | correct | partial | correct | correct | correct | correct |
| ja 40 | cross | 2 | correct | partial | correct | correct | correct | correct |
| ja 43 | cross | 2 | correct | correct | correct | correct | partial | correct |
| ja 44 | cross | 3 | correct | partial | correct | correct | correct | correct |
| ja 46 | cross | 3 | correct | partial | correct | correct | correct | correct |
| ja 48 † | cross | 2 | partial | incorrect | incorrect | incorrect | partial | partial |
| ja 50 | cross | 3 | correct | partial | correct | correct | correct | correct |

† Q48's gold answer is disputed; its verdicts are held under reservation — see
[Q48](#q48-a-defect-in-the-question-not-in-the-models) below.

Ceiling doubles as a sanity check on the gold itself: with the gold chapters in
the context, a `correct` verdict says the question and its gold answer agree.
Only the 17 rows above need auditing — the other 44 English and 39 Japanese
questions are answered from the gold chapters by all six models — and of those
only Q48 turned out to be a question-side problem.

* **Q48 is the only universal miss**, in both languages and across all six
  models: 12 ceiling verdicts, none `correct`. That is the signature of a broken
  question rather than a hard one.
* **Nothing here is a missing-evidence failure** — the context is the gold
  annotation, so every miss is synthesis inside two or three chapters.
* **Multi-chapter `cross` questions carry the difficulty.** 14 of the 17 rows are
  `cross`, and the three `single` rows belong to en Q6 (a two-part answer where
  qwen3.6 and muse-glimmer name the broken strings but not the snatched mezrab),
  gemma4:26b-a4b's en Q17, and `stealth/ox-alpha`'s en Q22.
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
  and `stealth/ox-alpha` show it is not broken: four models miss it in
  Japanese, but the other two both reach Surma's death by the poison — 「スル
  マが毒を飲んで死に至ったこと」 (muse-glimmer) and 「この毒によってスルマは
  自らの手で毒を飲み、命を落とした」 (`stealth/ox-alpha`) — the scored fact
  the other four never reach. The gold is sound, both languages are
  answerable, and it separates models. It is worth keeping exactly as it is.
* **Q29's gold carries one imprecision, which does not change the reading.** It
  credits the commission to "the Mahishi's maid, Matangini", while chapter 17
  has the Rajmahishi as the principal — Matangini is only sent to fetch the
  medicine, and Mangala substitutes poison for it on her own initiative. Both
  language versions word it the same way, so nothing is asymmetric between them,
  and no verdict turns on it: the failing Japanese answers stop well short of
  that detail, on the poisoning itself. The gold is left as it is, along with
  Q48's.

## Hybrid8 vs. ceiling: what retrieval costs

Three models have been run under both methods — the default
`google:gemma-4-31b-it`, `ollama:qwen3.8`, and `openrouter:stealth/ox-alpha` —
and all three read **byte-identical contexts** under each. The Gemma numbers
are the canonical `results-<lang>/{hybrid8,ceiling}.jsonl` runs; the qwen3.8
and `stealth/ox-alpha` hybrid8 runs replay `hits` and `expanded` straight from
`results-<lang>/hybrid8.jsonl`. So retrieval is not a variable *between the
models* either, and the ceiling → hybrid8 step is the price of answering from
a k=8 retrieved context instead of the gold one.

| Model | Method | English | Japanese |
| --- | --- | --- | --- |
| `google:gemma-4-31b-it` | ceiling | 49/50 (0.990) — 49/1/0 | 47/50 (0.970) — 47/3/0 |
| `google:gemma-4-31b-it` | hybrid8 | 46/50 (0.940) — 46/2/2 | 45/50 (0.940) — 45/4/1 |
| `ollama:qwen3.8` | ceiling | 49/50 (0.990) — 49/1/0 | 48/50 (0.970) — 48/1/1 |
| `ollama:qwen3.8` | hybrid8 | 49/50 (0.990) — 49/1/0 | 46/50 (0.940) — 46/2/2 |
| `openrouter:stealth/ox-alpha` | ceiling | 48/50 (0.970) — 48/1/1 | 49/50 (0.990) — 49/1/0 |
| `openrouter:stealth/ox-alpha` | hybrid8 | 47/50 (0.970) — 47/3/0 | 48/50 (0.970) — 48/1/1 |

- **In English qwen3.8 pays nothing for retrieval.** Its hybrid8 verdicts are
  identical to its own ceiling verdicts on all 50 questions — same single
  `partial` (Q48), same 0.990 — even though the hybrid8 context misses gold
  chapters on 5 of 50 questions. Gemma drops 0.050 over the same step.
- **In Japanese both models pay.** Gemma drops 0.030 (0.970 → 0.940) and
  qwen3.8 drops the same 0.030 from a slightly different ceiling distribution
  (48/1/1 vs Gemma's 47/3/0 — equal weighted, more all-or-nothing), so the two
  end level at 0.940.
- **`stealth/ox-alpha`'s English score is unchanged by retrieval (0.970 →
  0.970), but this is not a verdict-for-verdict match like qwen3.8's.**
  Ceiling's shortfall was Q22 (`incorrect`) and Q48 (`partial`); hybrid8's is
  three different `partial`s (Q32, Q48, Q50). Q22 disappears once retrieval
  replaces the gold context, but two new partials appear elsewhere — a wash in
  score that hides two different failure sets.
- **In Japanese `stealth/ox-alpha` pays least of the three, and starts from
  the top.** It drops only 0.020 (0.990 → 0.970) against Gemma's and qwen3.8's
  0.030, and its ceiling score was already the highest of the six models in
  the wider comparison — the only one whose Japanese ceiling beats its own
  English (see [Ceiling](#ceiling-comparing-answerer-models) above).

### Hybrid8: every question any model missed

| Lang | Q | type | Gemma 4 | qwen3.8 | ox-alpha | gold in context |
| --- | --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | correct | correct | yes |
| en | 29 | cross | incorrect | correct | correct | yes |
| en | 32 | cross | partial | correct | partial | **no** |
| en | 48 † | cross | partial | partial | partial | yes |
| en | 50 | cross | correct | correct | partial | **no** |
| ja | 27 | cross | partial | partial | incorrect | **no** |
| ja | 29 | cross | incorrect | incorrect | correct | yes |
| ja | 36 | cross | partial | correct | correct | yes |
| ja | 42 | cross | correct | incorrect | correct | **no** |
| ja | 44 | cross | partial | correct | correct | yes |
| ja | 48 † | cross | partial | partial | partial | yes |

† Same reservation as the ceiling table.

* **Cross-reference synthesis dominates the table.** 10 of the 11 rows are
  `cross`; the lone `single` question, en Q17, is Gemma's only miss in this
  comparison — every other model gets it.
* **Four of the eleven rows are shared blind spots — gold chapters absent from
  the k=8 context — so a `correct` verdict there reflects prior knowledge or a
  lenient judge, not reading comprehension:** en Q32 and ja Q42 (both
  documented in [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)),
  plus en Q50 and ja Q27 (the same failure mode, not among HYBRID.md's four
  listed cases). Restricting to the questions whose gold chapters are actually
  present — English n=45, Japanese n=47 — each model's correct/partial/incorrect
  becomes: Gemma 42/1/2 (en), 43/3/1 (ja); qwen3.8 44/1/0 (en), 45/1/1 (ja);
  `stealth/ox-alpha` 44/1/0 (en), 46/1/0 (ja). On the evidence actually
  supplied, qwen3.8 and `stealth/ox-alpha` both reach a 0.989 weighted English
  score; in Japanese `stealth/ox-alpha` holds 0.989 while qwen3.8 drops to
  0.968. Gemma trails in both languages, at 0.944 (en) and 0.947 (ja).
* **ja Q27 shows the judge scoring identical honesty differently across
  models.** Gold chapters are absent from the context; Gemma and qwen3.8 both
  land `partial`, naming the failed assassination plan and leaving the
  successful method unaddressed. `stealth/ox-alpha` does the same — names the
  plan, then states the method cannot be confirmed from the context — but the
  judge marks it `incorrect`: explicitly saying "not found" counts as missing
  the required facts rather than as an honest partial answer. All three are
  `correct` at ceiling, so evidence is what every one of them lacks; the
  verdict split here is judge-boundary noise, not a difference in model
  behaviour.
* **ja Q29 is where more context hurts Gemma and qwen3.8 but not
  `stealth/ox-alpha`.** Gold chapters are in the k=8 context, yet both models
  drop from a `partial` ceiling verdict to `incorrect` at hybrid8, answering
  about an unrelated subplot once those same chapters sit inside the larger
  context — long-context distraction, not missing evidence.
  `stealth/ox-alpha` holds `correct` at both ceiling and hybrid8, unaffected by
  the added context here.
* **en Q50 is a fifth retrieval gap, not among HYBRID.md's four documented
  shared blind spots.** Its gold chapters are Ch8, Ch18, and Ch23; only Ch23
  fails to surface in either retriever's top-8, so the k=8 context carries 2 of
  the 3 gold chapters. Gemma and qwen3.8 both still reach `correct`, but
  `stealth/ox-alpha` lands `partial`, substituting a different Chapter 6 scene
  for the Chapter 23 detail — Rammohan citing Vibha's unbraided hair as proof
  of neglect — that the missing chapter would have supplied.

## Q48: a defect in the question, not in the models

Q48 asks how Ramchandra interprets "his brother-in-law's behavior" after the
midnight rescue, and the natural referent of *behavior* is the protective action
the same sentence names. That is what the models answer: Ramchandra found the
rescue "bound to happen" and credited it to Udayaditya's concern for his sister
Vibha rather than for him. The gold answer instead requires a separate aside in
chapter 19 — Ramchandra sees Udayaditya whisper to a servant and assumes a plot
to insult him — which sits in a list of anecdotes about the king's touchiness
and is not connected to the rescue at all.

* **All eighteen verdicts converge, and none is `correct`.** Six models at
  ceiling in two languages, plus three models × two languages under hybrid8,
  and no run mentions the whispering. Independent models agreeing against the
  gold points at the question, which ties the scored fact to a premise that
  does not lead to it.
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
  and in Japanese by two, so cross-language agreement is what separates a hard
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
