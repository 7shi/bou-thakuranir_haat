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
| **Vector k=5** | 0.820 (38/6/6) | 0.720 (28/16/6) | 0.790 (35/9/6) | 0.770 (32/13/5) | **0.750** (30/15/5) | 0.800 (37/6/7) | 0.760 (32/12/6) | 0.760 (32/12/6) | 0.770 (33/11/6) | **0.760** (32/12/6) |
| **Vector k=10** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.890 (41/7/2) | 0.860 (37/12/1) | **0.860** (38/10/2) | 0.900 (43/4/3) | 0.820 (37/8/5) | 0.880 (41/6/3) | 0.830 (37/9/4) | **0.810** (36/9/5) |
| **Vector-line k=5** | 0.770 (33/11/6) | 0.750 (30/15/5) | 0.800 (35/10/5) | 0.790 (32/15/3) | **0.770** (33/11/6) | 0.790 (34/11/5) | 0.750 (30/15/5) | 0.780 (33/12/5) | 0.730 (29/15/6) | **0.720** (29/14/7) |
| **Vector-line k=10** | 0.850 (38/9/3) | 0.800 (32/16/2) | 0.890 (41/7/2) | 0.860 (37/12/1) | **0.820** (34/14/2) | 0.860 (41/4/5) | 0.790 (33/13/4) | 0.850 (38/9/3) | 0.800 (33/14/3) | **0.780** (32/14/4) |
| **V-hybrid k=5** | 0.870 (39/9/2) | 0.820 (34/14/2) | 0.880 (40/8/2) | 0.880 (39/10/1) | **0.860** (37/12/1) | 0.890 (42/5/3) | 0.800 (34/12/4) | 0.840 (38/8/4) | 0.820 (35/12/3) | **0.810** (35/11/4) |
| **V-hybrid k=10** | 0.930 (44/5/1) | 0.860 (37/12/1) | 0.900 (41/8/1) | 0.900 (40/10/0) | **0.900** (40/10/0) | 0.900 (43/4/3) | 0.810 (35/11/4) | 0.860 (39/8/3) | 0.830 (36/11/3) | **0.780** (33/12/5) |
| **Hybrid k=5** | 0.880 (40/8/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | 0.870 (38/11/1) | **0.850** (36/13/1) | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.910 (42/7/1) | 0.860 (37/12/1) | **0.830** (35/13/2) |
| **Hybrid k=8** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.910 (43/5/2) | 0.870 (38/11/1) | **0.860** (38/10/2) | 0.920 (43/6/1) | 0.830 (34/15/1) | 0.910 (42/7/1) | 0.880 (39/10/1) | **0.860** (37/12/1) |
| **Hybrid k=10** | 0.980 (48/2/0) | 0.900 (40/10/0) | 0.930 (43/7/0) | 0.950 (45/5/0) | **0.900** (40/10/0) | 0.910 (42/7/1) | 0.860 (37/12/1) | 0.890 (40/9/1) | 0.850 (36/13/1) | **0.820** (33/16/1) |
| **Extract** | 0.860 (40/6/4) | 0.780 (32/14/4) | 0.850 (39/7/4) | 0.840 (38/8/4) | **0.820** (37/8/5) | 0.870 (41/5/4) | 0.770 (30/17/3) | 0.830 (36/11/3) | 0.790 (33/13/4) | **0.750** (30/15/5) |
| **Filter2** | 0.800 (37/6/7) | 0.770 (33/11/6) | 0.800 (36/8/6) | 0.790 (35/9/6) | **0.790** (35/9/6) | 0.820 (38/6/6) | 0.740 (30/14/6) | 0.800 (36/8/6) | 0.740 (30/14/6) | **0.740** (31/12/7) |
| **Filter3** | 0.930 (45/3/2) | 0.880 (40/8/2) | 0.920 (44/4/2) | 0.910 (43/5/2) | **0.890** (41/7/2) | 0.870 (41/5/4) | 0.840 (39/6/5) | 0.900 (43/4/3) | 0.850 (38/9/3) | **0.820** (36/10/4) |
| **Ceiling** | 0.990 (49/1/0) | 0.930 (43/7/0) | 0.960 (46/4/0) | 0.970 (47/3/0) | **0.950** (45/5/0) | 0.990 (49/1/0) | 0.900 (40/10/0) | 0.950 (45/5/0) | 0.910 (41/9/0) | **0.920** (42/8/0) |
| **GraphRAG local** | 0.610 (24/13/13) | 0.550 (17/21/12) | 0.610 (22/17/11) | 0.590 (19/21/10) | **0.580** (20/18/12) | 0.630 (26/11/13) | 0.560 (21/14/15) | 0.610 (22/17/11) | 0.570 (18/21/11) | **0.520** (20/12/18) |
| **GraphRAG global** | 0.170 (3/11/36) | 0.130 (1/11/38) | 0.140 (1/12/37) | 0.140 (1/12/37) | **0.130** (1/11/38) | 0.190 (6/7/37) | 0.210 (3/15/32) | 0.210 (3/15/32) | 0.240 (4/16/30) | **0.140** (2/10/38) |

*Cells read `weighted (correct / partial / incorrect)`. OpenAI is the Decisions
API; Ternary is the same model replying with a word.*

---

## Analysis & Insights

### 1. Strictness: Close to OpenAI, More *Incorrect*

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Qwen 3.6** | 1,137 (75.8%) | 183 (12.2%) | 180 (12.0%) | 0.820 / 0.818 |
| **Nimble** | 1,075 (71.7%) | 261 (17.4%) | 164 (10.9%) | 0.809 / 0.799 |
| **OpenAI** | 1,000 (66.7%) | 346 (23.1%) | 154 (10.3%) | 0.799 / 0.765 |
| **Ternary** | **968 (64.5%)** | **343 (22.9%)** | **189 (12.6%)** | **0.782 / 0.737** |
| **Jev** | 944 (62.9%) | 381 (25.4%) | 175 (11.7%) | 0.761 / 0.752 |

Ternary calls slightly fewer answers *correct* than the Decisions API does (968
vs 1,000), and moves part of the *partial* band to *incorrect*: it gives the
most *incorrect* verdicts of all five judges (189). Its English weighted mean
falls between OpenAI and Jev; its Japanese one is the lowest of all five.

### 2. Disagreement & Agreement Rates

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **OpenAI vs Ternary**: **91.1%** (1,367 / 1,500) — *en: 93.1%, ja: 89.2%*
- **Jev vs Ternary**: **89.6%** (1,344 / 1,500) — *en: 90.9%, ja: 88.3%*
- **Nimble vs Ternary**: **85.6%** (1,284 / 1,500) — *en: 88.3%, ja: 82.9%*
- **Qwen vs Ternary**: **84.3%** (1,265 / 1,500) — *en: 87.5%, ja: 81.2%*

OpenAI vs Ternary is the highest of all ten pairs, above every pair of
different judges (the highest of those is Qwen vs Nimble, 89.8%, see
[NIMBLE.md](NIMBLE.md)): the same model agrees with itself across the two APIs
more than any two different judges do.

#### Combined Confusion Matrix (1,500 Questions)

```
OpenAI \ Ternary:
              correct   partial   incorrect
correct           936        64           0
partial            32       278          36
incorrect           0         1         153

Jev \ Ternary:
              correct   partial   incorrect
correct           896        48           0
partial            72       284          25
incorrect           0        11         164

Nimble \ Ternary:
              correct   partial   incorrect
correct           939       136           0
partial            29       194          38
incorrect           0        13         151

Qwen \ Ternary:
              correct   partial   incorrect
correct           956       178           3
partial            12       147          24
incorrect           0        18         162
```

### 3. Consensus on Incorrect Answers

153 of OpenAI's 154 *incorrect* verdicts are also *incorrect* under Ternary
(the other is *partial*); the extra 36 come from OpenAI's *partial*. Ternary's
189 *incorrect* verdicts are shared with Qwen in 162 cases, Jev in 164 and
Nimble in 151. A flat *correct* versus *incorrect* contradiction occurs only
against Qwen (3 cases); with the three decision judges the disagreements stay
at the neighbouring verdict.

### 4. Language Consistency

Ternary shows the largest drop from English to Japanese of the five judges:

| Judge | ja − en (mean over 15 methods) | Methods dropped / rose |
| :--- | ---: | :---: |
| Qwen 3.6 | −0.002 | 5 / 8 |
| Nimble | −0.010 | 10 / 2 |
| Jev | −0.009 | 10 / 3 |
| OpenAI | −0.035 | 12 / 2 |
| **Ternary** | **−0.045** | **12 / 2** |

- **Ceiling**: en 0.950 → ja 0.920.
- **Largest drops**: V-hybrid k=10 (en 0.900 → ja 0.780), Hybrid k=10
  (0.900 → 0.820), and Filter3 and Extract (−0.070 each).
- **Method rankings**: In English, V-hybrid k=10 and Hybrid k=10 share second
  place after Ceiling (0.900), followed by Filter3 (0.890). In Japanese,
  Hybrid k=8 is second (0.860), followed by Hybrid k=5 (0.830), and Hybrid
  k=10 and Filter3 (0.820).

The rubric is in English for every language, as with Jev and OpenAI; this run
does not isolate the cause of the drop.

---

## Conclusion

1. **Same Model, Same Verdicts**: Through the ordinary API, `gpt-6-luna`
   agrees with its own Decisions verdicts on 91.1% of questions, the closest
   pair of all judges.
2. **Slower, Free Here**: 5 output tokens and no reasoning per request, but
   ~1.41 s per decision, about five times the Decisions API; the run fit in the
   free tier.
3. **Stricter at the Bottom**: Slightly fewer *correct* verdicts than the
   Decisions API, the most *incorrect* verdicts of all judges, and the
   largest Japanese drop (−0.045).
