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
| `google:gemini-3.5-flash-lite` | 41/50 (0.860) — 41/4/5 | 41/50 (0.860) — 41/4/5 |
| `google:gemini-3.7-flash` | 48/50 (0.970) — 48/1/1 | 49/50 (0.980) — 49/0/1 |
| `google:gemma-4-31b-it` | 49/50 (0.990) — 49/1/0 | 48/50 (0.980) — 48/2/0 |
| `ollama:gemma4:26b-a4b-it-qat` | 47/50 (0.960) — 47/2/1 | 42/50 (0.920) — 42/8/0 |
| `ollama:qwen3.6` (35B-A3B) | 49/50 (0.990) — 49/1/0 | 47/50 (0.970) — 47/3/0 |
| `ollama:qwen3.8` (27B) | 50/50 (1.000) — 50/0/0 | 49/50 (0.990) — 49/1/0 |
| `ollama:muse-glimmer` | 49/50 (0.990) — 49/1/0 | 47/50 (0.970) — 47/3/0 |
| `openai:gpt-5.6-luna` | 50/50 (1.000) — 50/0/0 | 47/50 (0.970) — 47/3/0 |
| `openai:gpt-5.6-terra` | 47/50 (0.950) — 47/1/2 | 49/50 (0.990) — 49/1/0 |
| `openrouter:stealth/ox-alpha` | 49/50 (0.980) — 49/0/1 | 50/50 (1.000) — 50/0/0 |
| `openrouter:poolside/laguna-s-2.1:free` | 39/50 (0.880) — 39/10/1 | 31/50 (0.730) — 31/11/8 |
| `openrouter:cohere/north-mini-code:free` | 44/50 (0.930) — 44/5/1 | 30/50 (0.740) — 30/14/6 |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | 50/50 (1.000) — 50/0/0 | 47/50 (0.970) — 47/3/0 |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 44/50 (0.940) — 44/6/0 | 38/50 (0.860) — 38/10/2 |

(`correct`/50 with the weighted score in parentheses, then correct/partial/incorrect.
The `gemma-4-31b-it` row is the canonical `results-<lang>/ceiling.jsonl` run; the
other twelve live in this directory and are aggregated in [report.md](report.md).)

* **The top is crowded; the floor has widened.** Nine of the fourteen models
  reach 0.960 or better in English, and six of those sit at 0.990 or 1.000 —
  `qwen3.8`, `gpt-5.6-luna` and `nemotron-3-ultra-550b-a55b:free` answer all 50,
  and `gemma-4-31b-it`, `qwen3.6` and `muse-glimmer` each drop a single
  `partial`. Ceiling is still a ceiling for that group: it measures whether a
  model can read two or three chapters it has already been handed, and those
  models can. Five models sit below that line, with the gold chapters supplied:
  `gemini-3.5-flash-lite` at 0.860, `poolside/laguna-s-2.1:free` at 0.880,
  `cohere/north-mini-code:free` at 0.930, `nemotron-3.5-lightning:free` at
  0.940, and `gpt-5.6-terra` at 0.950.
* **Japanese costs most models something, and the biggest loss changed hands.**
  The losses run from 0.010 (`gemma-4-31b-it`, qwen3.8) to 0.190
  (`cohere/north-mini-code:free`, which overtakes `poolside/laguna-s-2.1:free`'s
  0.150 as the largest gap). `gemini-3.5-flash-lite` is the only model that
  scores identically in both languages (0.860, the same 41/4/5 split, on
  largely different questions), and `stealth/ox-alpha`, `gemini-3.7-flash` and
  `gpt-5.6-terra` are the only three that run the other way and gain. The
  English miss list has 22 distinct questions against Japanese's 31 — the same
  questions, the same gold, the same gold chapters.
* **`stealth/ox-alpha` is still the strongest Japanese model.** Its 50/50 is the
  only perfect Japanese run of the fourteen, while in English it sits mid-table
  on a single outright error (Q22). `gemini-3.7-flash` reverses direction the
  same way but from lower down (0.970 → 0.980), and `gpt-5.6-terra` does too,
  more sharply (0.950 → 0.990).
* **`gpt-5.6-terra` repeats `stealth/ox-alpha`'s exact English misreading of
  Q22.** Both name Sitaram instead of Udayaditya as the owner of the cloth used
  to bind the guard — `gpt-5.6-terra` flatly ("Sitaram's own cloth"),
  `stealth/ox-alpha` while visibly second-guessing itself ("His own cloth (i.e.,
  Udayaditya tied Sitaram up using Sitaram's own cloth)"). Two otherwise
  strong, unrelated models land on the same wrong antecedent from the same
  supplied chapter.
* **`cohere/north-mini-code:free` is the new floor, and its failures include
  degenerate answers that the others don't produce.** Its Japanese score
  (0.740) is now the second-lowest of the fourteen after
  `poolside/laguna-s-2.1:free`'s 0.730, but its language gap (−0.190) is the
  largest. Some of its errors are ordinary content mistakes — ja Q12 answers
  「母」 where the gold says 「ニカシャ様」, echoing `poolside`'s single-fact
  misses on the same kind of question — but ja Q46 simply echoes the question
  back verbatim with no answer content at all, a failure mode none of the other
  thirteen models exhibits.
* **`poolside/laguna-s-2.1:free`'s language gap changes shape across the two.**
  In English its shortfall is 10 `partial`s and one `incorrect`, every one of
  them on a `cross` question: it finds the passage and answers incompletely. In
  Japanese it produces 8 outright errors, four of them on `single` single-fact
  lookups that few other models miss in either language — 「ロープ」 where the
  gold says 「彼の衣服」 (Q22), 「ビバ」 where the gold says 「ニカシャ様」
  (Q12), 「パーン」 for the dried root handed over with the paan (Q8). The
  answers stay fluent and stop being about the text.
* **`gemini-3.5-flash-lite` fails by refusing.** Nine of its ten `incorrect`
  verdicts are the model reporting that the answer is not in the context, with
  the gold chapters in the context — en Q17, Q37, Q40, Q42, Q47 and ja Q35,
  Q36, Q42, Q50, i.e. Q42 refused in both languages. That is the judge boundary ja
  Q27 hits in the hybrid8 table below: an explicit "not found" is scored
  `incorrect` rather than `partial`, so this model's floor is partly a rubric
  effect — but the answers it declines to give are all present in the supplied
  chapters, which is the finding.
* **`nemotron-3.5-lightning:free` has one answer that is simply corrupted.** Its
  ja Q45 output is not a refusal or a content error but garbled English prose
  mixed with fragments of its own system instructions ("Here's a thinking
  process: 1. **Analyze User Request:** ..."), scored `incorrect` because there
  is no coherent Japanese answer to grade. Its other Japanese misses are
  ordinary `partial`s, so this one row is a generation failure rather than a
  comprehension one.
* **Only the small MoE separates itself among the local models.**
  `gemma4:26b-a4b-it-qat` activates 4B parameters per token and is the only
  ollama model below 0.950; it loses 0.040 from English to Japanese, twice any
  other local model's loss. Its failure mode is legible in the verdicts: 8
  `partial` and no outright error in Japanese, i.e. it finds the passage and
  drops one of the two or three elements the gold answer enumerates (ja Q34
  gives the escape → death chain but not Rukmini's denunciation; ja Q44
  contrasts the jewellery with the plain clothes but not the beggar-woman
  impression; ja Q50 has Vibha waiting for Surma but not Rammohan's later
  remark).
* **en Q17 is now the widest English row on its own: four models get it wrong,
  in three different ways.** gemma4:26b-a4b and `gemini-3.7-flash` both answer
  "the entire night" against a gold of "five days" for how long Mangala spends
  preparing the poison. `cohere/north-mini-code:free` answers "One day" — a
  different wrong number for the same fact. `gemini-3.5-flash-lite` instead
  refuses, pointing at a distinction the source itself draws — "It took five
  days to prepare the medicine. It does not take five days to prepare poison."
  — and concluding that no figure is given for the poison. All fourteen models
  answer the parallel Japanese question correctly, from the same gold chapter
  and the same sentence.
* **The outright errors on `single` questions are single-hop misreadings of a
  supplied chapter, not incomplete synthesis.** Beyond en Q17 and en Q22 (above),
  `poolside/laguna-s-2.1:free`'s four Japanese single-fact errors and
  `cohere/north-mini-code:free`'s ja Q12 are the same shape at greater volume.
  Different models, different questions, one failure mode.
* **The judge is `ollama:qwen3.6`, one of the answerers.** A same-family
  preference cannot be ruled out from these runs, though qwen3.6 does not top
  either language — in English it is behind `qwen3.8`, `gpt-5.6-luna` and
  `nemotron-3-ultra-550b-a55b:free` and level with `gemma-4-31b-it` and
  `muse-glimmer`; in Japanese it is behind five models (`stealth/ox-alpha`,
  `gemma-4-31b-it`, `gemini-3.7-flash`, `qwen3.8`, `gpt-5.6-terra`) and level
  with three more — which is weak evidence against a strong self-preference
  rather than proof of none.

### Every question any model missed

Question IDs, listed per model. Questions 1–25 are `single` (one gold chapter),
26–50 are `cross` (two or three).

| Model | en partial | en incorrect | ja partial | ja incorrect |
| --- | --- | --- | --- | --- |
| `google:gemini-3.5-flash-lite` | 26, 28, 36, **48** | 17, 37, 40, 42, 47 | 28, **29**, 34, 40 | 35, 36, 39, 42, 50 |
| `google:gemini-3.7-flash` | 50 | 17 | — | **29** |
| `google:gemma-4-31b-it` | **48** | — | **29**, 36 | — |
| `ollama:gemma4:26b-a4b-it-qat` | 33, 35 | 17 | **29**, 34, 35, 37, 40, 44, 46, 50 | — |
| `ollama:qwen3.6` (35B-A3B) | 6 | — | **29**, 36, **48** | — |
| `ollama:qwen3.8` (27B) | — | — | **29** | — |
| `ollama:muse-glimmer` | 6 | — | 34, 35, 43 | — |
| `openai:gpt-5.6-luna` | — | — | **29**, 35, **48** | — |
| `openai:gpt-5.6-terra` | 31 | 22, 49 | 43 | — |
| `openrouter:stealth/ox-alpha` | — | 22 | — | — |
| `openrouter:poolside/laguna-s-2.1:free` | 26, 28, 31, 34, 37, 38, 39, 46, **48**, 50 | 45 | 4, 27, **29**, 30, 32, 37, 39, 41, 43, 46, 50 | 2, 8, 12, 22, 34, 35, 42, 45 |
| `openrouter:cohere/north-mini-code:free` | 33, 36, 46, 49, 50 | 17 | 6, 26, 32, 33, 34, 35, 37, 38, 39, 42, 47, **48**, 49, 50 | 12, 16, 28, **29**, 36, 46 |
| `openrouter:nvidia/nemotron-3-ultra-550b-a55b:free` | — | — | 37, 43, 44 | — |
| `openrouter:nvidia/nemotron-3.5-lightning:free` | 6, 28, 30, 34, 36, 37 | — | 6, 27, 28, 33, 35, 36, 37, 40, 43, 50 | **29**, 45 |

Ceiling doubles as a sanity check on the gold itself: with the gold chapters in
the context, a `correct` verdict says the question and its gold answer agree.
22 English and 31 Japanese questions appear above and need auditing — the other
28 English and 19 Japanese questions are answered from the gold chapters by all
fourteen models.

* **No question is missed by every model.** The widest is ja Q29, missed by
  ten of the fourteen; then ja Q35 at seven, and a five-way tie — ja Q34, Q36,
  Q37, Q43, Q50 — at five each. A question that no model answers from the gold
  chapters in either language is the signature of a broken gold rather than a
  hard question, and the set does not contain one.
* **Nothing here is a missing-evidence failure** — the context is the gold
  annotation, so every miss is synthesis inside two or three chapters.
* **Multi-chapter `cross` questions carry the difficulty.** The English
  `single` misses are Q6 (a two-part answer where qwen3.6 and muse-glimmer name
  the broken strings but not the snatched mezrab), Q17 and Q22; the Japanese
  `single` misses — Q2, Q4, Q8, Q12, Q16, Q22 — are mostly
  `poolside/laguna-s-2.1:free` alone, with `cohere/north-mini-code:free` adding
  Q12 and Q16.
* **ja Q29 is language ability, not question quality.** It is parallel across
  languages — same question, same gold answer, same gold chapters — and all
  fourteen models answer it correctly in English. qwen3.8 is the clearest case:
  from the same two chapters, its English answer reaches the poisoning and
  Surma's death, while its Japanese answer stops at the public confrontation —
  the threat to imprison Udayaditya and the queen relaying it — and never
  reaches the errand the queen sends Matangini on or the poison Mangala brews
  from it. `gemma-4-31b-it` is the mildest form: its Japanese answer states the
  same facts as its English one but stops short of naming Surma's death, a
  completeness gap rather than a comprehension failure. `gemini-3.7-flash` and
  `nemotron-3.5-lightning:free` are the extreme form — both Japanese answers
  land on 「密かに給金を送っていたこと」 (secretly sending money), an unrelated
  subplot, the same wrong answer from two unrelated models; it is one of only
  three verdicts `gemini-3.7-flash` loses across both languages.
* **ja Q29 is the most discriminating question in the set**, and four models
  show it is not broken: ten of the fourteen miss it in Japanese, but
  muse-glimmer, `stealth/ox-alpha`, `gpt-5.6-terra` and
  `nemotron-3-ultra-550b-a55b:free` reach Surma's death by the poison —
  「スルマが毒を飲んで死に至ったこと」 (muse-glimmer), 「この毒によってスルマは
  自らの手で毒を飲み、命を落とした」 (`stealth/ox-alpha`), and equivalent
  phrasing from the other two — the scored fact the other ten never reach. The
  gold is sound, both languages are answerable, and it separates models. It is
  worth keeping exactly as it is.
* **Q29's gold carries one imprecision, which does not change the reading.** It
  credits the commission to "the Mahishi's maid, Matangini", while chapter 17
  has the Rajmahishi as the principal — Matangini is only sent to fetch the
  medicine, and Mangala substitutes poison for it on her own initiative. Both
  language versions word it the same way, so nothing is asymmetric between them,
  and no verdict turns on it: the failing Japanese answers stop well short of
  that detail, on the poisoning itself. The gold is left as it is.
* **Q48 asks a two-part question, and the judge enforces it by language.** The
  question asks how Ramchandra reads the rescue *in his own court*, so its gold
  has his private reading (he owes nothing; Udayaditya acted for his sister)
  *and* what he does with it in court (he joins the mockery of Udayaditya for
  being Pratapaditya's son). Among the original nine ceiling models, nine of
  the eighteen runs give both halves — six of the nine English runs against
  three of the nine Japanese ones. Of the nine runs that omit the court half,
  all three English ones are scored `partial` and five of the six Japanese ones
  are scored `correct`, qwen3.6 being the exception; `gemma4:26b-a4b`'s Japanese
  answer gives the sister motive alone and passes. The `partial`s are the
  correct reading of the gold, so Q48's Japanese row understates how many runs
  answer only half the question. The same pattern recurs among the five newer
  models: `gpt-5.6-luna`'s and `cohere/north-mini-code:free`'s Japanese answers
  both give the sister motive alone and are marked `partial` like qwen3.6's,
  rather than passing on the Japanese leniency most other omitters get.

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
| `google:gemma-4-31b-it` | ceiling | 49/50 (0.990) — 49/1/0 | 48/50 (0.980) — 48/2/0 |
| `google:gemma-4-31b-it` | hybrid8 | 46/50 (0.940) — 46/2/2 | 46/50 (0.950) — 46/3/1 |
| `ollama:qwen3.8` | ceiling | 50/50 (1.000) — 50/0/0 | 49/50 (0.990) — 49/1/0 |
| `ollama:qwen3.8` | hybrid8 | 50/50 (1.000) — 50/0/0 | 47/50 (0.950) — 47/1/2 |
| `openrouter:stealth/ox-alpha` | ceiling | 49/50 (0.980) — 49/0/1 | 50/50 (1.000) — 50/0/0 |
| `openrouter:stealth/ox-alpha` | hybrid8 | 48/50 (0.980) — 48/2/0 | 49/50 (0.980) — 49/0/1 |

- **In English qwen3.8 pays nothing for retrieval.** It answers all 50 under
  both methods, verdict for verdict, even though the hybrid8 context misses gold
  chapters on 5 of 50 questions. Gemma drops 0.050 over the same step.
- **In Japanese every model pays.** qwen3.8 drops 0.040 (0.990 → 0.950), Gemma
  0.030 (0.980 → 0.950) from a slightly different ceiling distribution
  (48/2/0 vs qwen3.8's 49/1/0), so the two end level at 0.950 by different
  routes — Gemma with three partials, qwen3.8 with two outright errors.
- **`stealth/ox-alpha`'s English score is unchanged by retrieval (0.980 →
  0.980), but this is not a verdict-for-verdict match like qwen3.8's.**
  Ceiling's shortfall was the single Q22 `incorrect`; hybrid8's is two different
  `partial`s (Q32, Q50). Q22 disappears once retrieval replaces the gold
  context, but two new partials appear elsewhere — a wash in score that hides
  two different failure sets.
- **In Japanese `stealth/ox-alpha` pays least of the three, and starts from
  the top.** It drops only 0.020 (1.000 → 0.980) against Gemma's 0.030 and
  qwen3.8's 0.040, and its ceiling score was the only perfect Japanese run of
  the fourteen models in the wider comparison, and one of only three whose
  Japanese ceiling beats its own English (see
  [Ceiling](#ceiling-comparing-answerer-models) above).

### Hybrid8: every question any model missed

| Lang | Q | type | Gemma 4 | qwen3.8 | ox-alpha | gold in context |
| --- | --- | --- | --- | --- | --- | --- |
| en | 17 | single | incorrect | correct | correct | yes |
| en | 29 | cross | incorrect | correct | correct | yes |
| en | **32** | cross | partial | correct | partial | **no** |
| en | 48 | cross | partial | correct | correct | yes |
| en | **50** | cross | correct | correct | partial | **no** |
| ja | **27** | cross | partial | partial | incorrect | **no** |
| ja | 29 | cross | incorrect | incorrect | correct | yes |
| ja | 36 | cross | partial | correct | correct | yes |
| ja | **42** | cross | correct | incorrect | correct | **no** |
| ja | 44 | cross | partial | correct | correct | yes |

* **Cross-reference synthesis dominates the table.** 9 of the 10 rows are
  `cross`; the lone `single` question, en Q17, is one of Gemma's misses — the
  other two models get it.
* **Four of the ten rows are shared blind spots — gold chapters absent from
  the k=8 context — so a `correct` verdict there reflects prior knowledge or a
  lenient judge, not reading comprehension:** en Q32 and ja Q42 (both
  documented in [HYBRID.md § Shared blind spots](../HYBRID.md#shared-blind-spots)),
  plus en Q50 and ja Q27 (the same failure mode, not among HYBRID.md's four
  listed cases). Restricting to the questions whose gold chapters are actually
  present — English n=45, Japanese n=47 — each model's correct/partial/incorrect
  becomes: Gemma 42/1/2 (en), 44/2/1 (ja); qwen3.8 45/0/0 (en), 46/0/1 (ja);
  `stealth/ox-alpha` 45/0/0 (en), 47/0/0 (ja). On the evidence actually
  supplied, qwen3.8 and `stealth/ox-alpha` both answer every English question,
  and `stealth/ox-alpha` answers every Japanese one too while qwen3.8 drops to
  0.979. Gemma trails in both languages, at 0.944 (en) and 0.957 (ja).
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
