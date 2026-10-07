# Re-grading with a Plain LLM (Ternary)

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language = 1,500 requests in total) was re-graded by `gpt-6-luna` through
the **ordinary OpenAI API**, replying with the verdict word only, and compared
with the existing **`ollama:qwen3.6`** verdicts, TypeSafe's **Jev**
(`jev-1.13.0`, see [JEV.md](JEV.md)), Bespoke Labs' **Nimble** (see
[NIMBLE.md](NIMBLE.md)) and the same model through OpenAI's **Decisions API**
(see [OPENAI.md](OPENAI.md)).

## Setup

- **Model**: `openai:gpt-6-luna` via llm7shi (Responses API), with reasoning
  off (`include_thoughts=False`, which sends `reasoning.effort="none"`).
- **Judge**: [judge-ternary.py](judge-ternary.py), the plain-LLM counterpart of
  [judge-openai.py](judge-openai.py) with the same rubric: the same instruction
  and criterion wording and the same indented-JSON input, placed in a system
  prompt that ends with "Reply with exactly one word: correct, partial,
  incorrect." There is no structured output, no reason and no probability; the
  reply is matched against the three verdicts as whole words, and a reply
  naming none or several of them is retried. The scheme is `ternary@70c12cb1`
  (recorded in `results-<lang>/ternary/MODELS.tsv`).
- **Inputs**: Same contract as `judge.py`, `judge-jev.py`, `judge-nimble.py`
  and `judge-openai.py` — question, gold answer, rationale, candidate answer;
  **no** chapter source text.
- **Output**: `results-<lang>/ternary/<method>.tsv`, in judge-openai.py's
  columns with 1 for the chosen verdict, 0 for the others and an empty
  confidence.
- **Aggregation**: `uv run report.py -l <lang> --ternary`.
  - **Weighted** = `(correct + 0.5 · partial) / 50`

  OPENAI.md's probability expectation **E** is left out, since it equals
  Weighted when the probabilities are 1 and 0.

## Performance & Cost

| Metric | Jev (`judge-jev.py`) | OpenAI (`judge-openai.py`) | Ternary (`judge-ternary.py`) |
| :--- | :--- | :--- | :--- |
| **API** | TypeSafe System One | OpenAI Decisions | **OpenAI Responses** |
| **API Cost** | $0.0501 / 1,500 req | $0.0799 / 1,500 req | **$0.00** (within the free tier) |
| **Wall Time (en, 750 req)** | 2m 46s | 3m 36s | **15m 59s** (1.28 s / req) |
| **Wall Time (ja, 750 req)** | 2m 51s | 3m 27s | **19m 23s** (1.55 s / req) |
| **Total Wall Time (1,500 req)** | 5m 37s | 7m 3s | **35m 22s** (1.41 s / req) |
| **Input Tokens (en / ja)** | 516k / 676k | 345k / 454k | **290k / 398k (459 / req avg)** |
| **Output Tokens (total)** | 58,500 | 0 | **7,500** (5 / req) |
| **Reasoning Tokens** | — | — | **0** |

Every request used 5 output tokens and no reasoning tokens. The input is the
smallest of the three cloud judges (687,930 tokens), but each request takes
about five times as long as with the Decisions API (1 : 5.0 in total wall
time; Jev : Ternary is 1 : 6.3), so the same model is much slower when it
generates its verdict as text. The per-model re-grading in `results/`
([results/TERNARY.md](results/TERNARY.md)) gives 1 : 4.8 and 1 : 5.3 per
file, within the free tier as well.

---

## Results

### Summary Table (All 15 Methods)

| Method | en Qwen | en Jev | en Nimble | en OpenAI | en Ternary | ja Qwen | ja Jev | ja Nimble | ja OpenAI | ja Ternary |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Vector k=5** | 0.840 (40/4/6) | 0.730 (29/15/6) | 0.800 (36/8/6) | 0.800 (35/10/5) | **0.770** (32/13/5) | 0.810 (38/5/7) | 0.760 (32/12/6) | 0.770 (33/11/6) | 0.770 (33/11/6) | **0.770** (33/11/6) |
| **Vector k=10** | 0.930 (45/3/2) | 0.850 (37/11/2) | 0.900 (42/6/2) | 0.880 (39/10/1) | **0.880** (39/10/1) | 0.900 (43/4/3) | 0.820 (36/10/4) | 0.870 (40/7/3) | 0.840 (38/8/4) | **0.810** (35/11/4) |
| **Vector-line k=5** | 0.800 (35/10/5) | 0.740 (29/16/5) | 0.780 (33/12/5) | 0.810 (34/13/3) | **0.780** (34/10/6) | 0.800 (36/8/6) | 0.740 (29/16/5) | 0.790 (33/13/4) | 0.740 (30/14/6) | **0.740** (31/12/7) |
| **Vector-line k=10** | 0.890 (41/7/2) | 0.810 (33/15/2) | 0.890 (41/7/2) | 0.870 (37/13/0) | **0.860** (37/12/1) | 0.860 (41/4/5) | 0.780 (32/14/4) | 0.840 (37/10/3) | 0.820 (35/12/3) | **0.780** (33/12/5) |
| **V-hybrid k=5** | 0.880 (40/8/2) | 0.850 (37/11/2) | 0.890 (41/7/2) | 0.880 (39/10/1) | **0.870** (38/11/1) | 0.890 (42/5/3) | 0.820 (35/12/3) | 0.840 (37/10/3) | 0.830 (36/11/3) | **0.830** (36/11/3) |
| **V-hybrid k=10** | 0.910 (43/5/2) | 0.840 (35/14/1) | 0.880 (39/10/1) | 0.880 (38/12/0) | **0.910** (41/9/0) | 0.910 (44/3/3) | 0.830 (36/11/3) | 0.880 (40/8/2) | 0.830 (36/11/3) | **0.800** (34/12/4) |
| **Hybrid k=5** | 0.900 (42/6/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | 0.860 (37/12/1) | **0.870** (38/11/1) | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.880 (39/10/1) | 0.860 (37/12/1) | **0.860** (38/10/2) |
| **Hybrid k=8** | 0.930 (45/3/2) | 0.870 (39/9/2) | 0.920 (44/4/2) | 0.880 (40/8/2) | **0.870** (39/9/2) | 0.950 (46/3/1) | 0.860 (37/12/1) | 0.910 (42/7/1) | 0.890 (40/9/1) | **0.890** (40/9/1) |
| **Hybrid k=10** | 0.960 (47/2/1) | 0.870 (38/11/1) | 0.910 (41/9/0) | 0.930 (43/7/0) | **0.910** (42/7/1) | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.890 (40/9/1) | 0.830 (34/15/1) | **0.850** (36/13/1) |
| **Extract** | 0.850 (40/5/5) | 0.780 (32/14/4) | 0.850 (39/7/4) | 0.810 (35/11/4) | **0.780** (34/10/6) | 0.860 (41/4/5) | 0.770 (30/17/3) | 0.800 (33/14/3) | 0.800 (33/14/3) | **0.790** (34/11/5) |
| **Filter2** | 0.790 (36/7/7) | 0.760 (32/12/6) | 0.770 (33/11/6) | 0.770 (33/11/6) | **0.770** (34/9/7) | 0.850 (41/3/6) | 0.740 (30/14/6) | 0.790 (35/9/6) | 0.730 (29/15/6) | **0.750** (31/13/6) |
| **Filter3** | 0.940 (46/2/2) | 0.890 (41/7/2) | 0.940 (46/2/2) | 0.910 (43/5/2) | **0.900** (42/6/2) | 0.890 (43/3/4) | 0.860 (40/6/4) | 0.910 (44/3/3) | 0.840 (37/10/3) | **0.830** (37/9/4) |
| **Ceiling** | 0.990 (49/1/0) | 0.970 (47/3/0) | 0.950 (45/5/0) | 0.960 (46/4/0) | **0.970** (47/3/0) | 0.980 (48/2/0) | 0.920 (42/8/0) | 0.960 (46/4/0) | 0.920 (42/8/0) | **0.900** (40/10/0) |
| **GraphRAG local** | 0.650 (27/11/12) | 0.560 (17/22/11) | 0.630 (23/17/10) | 0.560 (18/20/12) | **0.560** (19/18/13) | 0.640 (28/8/14) | 0.550 (20/15/15) | 0.610 (22/17/11) | 0.590 (20/19/11) | **0.520** (19/14/17) |
| **GraphRAG global** | 0.170 (5/7/38) | 0.130 (1/11/38) | 0.150 (2/11/37) | 0.140 (1/12/37) | **0.130** (1/11/38) | 0.240 (8/8/34) | 0.200 (3/14/33) | 0.230 (4/15/31) | 0.230 (4/15/31) | **0.140** (2/10/38) |

*Cells read `weighted (correct / partial / incorrect)`. OpenAI is the Decisions
API; Ternary is the same model replying with a word.*

---

## Analysis & Insights

### 1. Strictness: Close to OpenAI, More *Incorrect*

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Qwen 3.6** | 1,170 (78.0%) | 147 (9.8%) | 183 (12.2%) | 0.829 / 0.829 |
| **Nimble** | 1,068 (71.2%) | 273 (18.2%) | 159 (10.6%) | 0.808 / 0.798 |
| **OpenAI** | 1,002 (66.8%) | 342 (22.8%) | 156 (10.4%) | 0.796 / 0.768 |
| **Ternary** | **996 (66.4%)** | **317 (21.1%)** | **187 (12.5%)** | **0.789 / 0.751** |
| **Jev** | 954 (63.6%) | 374 (24.9%) | 172 (11.5%) | 0.766 / 0.755 |

Ternary calls about as many answers *correct* as the Decisions API does (996
vs 1,002), but moves part of the *partial* band to *incorrect*: it gives the
most *incorrect* verdicts of all five judges (187). Its weighted means fall
between OpenAI and Jev.

### 2. Disagreement & Agreement Rates

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **OpenAI vs Ternary**: **91.0%** (1,365 / 1,500) — *en: 92.9%, ja: 89.1%*
- **Jev vs Ternary**: **88.7%** (1,331 / 1,500) — *en: 88.5%, ja: 88.9%*
- **Nimble vs Ternary**: **86.5%** (1,298 / 1,500) — *en: 88.1%, ja: 84.9%*
- **Qwen vs Ternary**: **84.8%** (1,272 / 1,500) — *en: 87.5%, ja: 82.1%*

OpenAI vs Ternary is the highest of all ten pairs, above the previous highest,
Jev vs OpenAI (89.5%, see [OPENAI.md](OPENAI.md)): the same model agrees with
itself across the two APIs more than any two different judges do.

#### Combined Confusion Matrix (1,500 Questions)

```
OpenAI \ Ternary:
              correct   partial   incorrect
correct           947        55           0
partial            49       262          31
incorrect           0         0         156

Jev \ Ternary:
              correct   partial   incorrect
correct           906        48           0
partial            90       261          23
incorrect           0         8         164

Nimble \ Ternary:
              correct   partial   incorrect
correct           955       113           0
partial            41       194          38
incorrect           0        10         149

Qwen \ Ternary:
              correct   partial   incorrect
correct           985       182           3
partial            10       120          17
incorrect           1        15         167
```

### 3. Consensus on Incorrect Answers

Every one of OpenAI's 156 *incorrect* verdicts is also *incorrect* under
Ternary; the extra 31 come from OpenAI's *partial*. Ternary's 187 *incorrect*
verdicts are shared with Qwen in 167 cases, Jev in 164 and Nimble in 149. A
flat *correct* versus *incorrect* contradiction occurs only against Qwen (4
cases); with the three decision judges the disagreements stay at the
neighbouring verdict.

### 4. Language Consistency

Ternary shows the largest drop from English to Japanese of the five judges:

| Judge | ja − en (mean over 15 methods) | Methods dropped / rose |
| :--- | ---: | :---: |
| Qwen 3.6 | +0.001 | 7 / 6 |
| Nimble | −0.010 | 9 / 5 |
| Jev | −0.011 | 11 / 2 |
| OpenAI | −0.028 | 11 / 3 |
| **Ternary** | **−0.038** | **11 / 3** |

- **Ceiling**: en 0.970 → ja 0.900, the lowest Japanese Ceiling of the five
  judges.
- **Largest drops**: V-hybrid k=10 (en 0.910 → ja 0.800), Vector-line k=10
  (0.860 → 0.780), and Vector k=10, Filter3 and Ceiling (−0.070 each).
- **Method rankings**: In English, V-hybrid k=10 and Hybrid k=10 share second
  place after Ceiling (0.910), followed by Filter3 (0.900). In Japanese,
  Hybrid k=8 is second (0.890), followed by Hybrid k=5 (0.860) and Hybrid k=10
  (0.850).

The rubric is in English for every language, as with Jev and OpenAI; this run
does not isolate the cause of the drop.

---

## Conclusion

1. **Same Model, Same Verdicts**: Through the ordinary API, `gpt-6-luna`
   agrees with its own Decisions verdicts on 91.0% of questions, the closest
   pair of all judges.
2. **Slower, Free Here**: 5 output tokens and no reasoning per request, but
   ~1.41 s per decision, about five times the Decisions API; the run fit in the
   free tier.
3. **Stricter at the Bottom**: About as many *correct* verdicts as the
   Decisions API, but the most *incorrect* verdicts of all judges, and the
   largest Japanese drop (−0.038).
