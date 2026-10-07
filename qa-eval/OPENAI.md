# Re-grading with OpenAI Decisions

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language = 1,500 requests in total) was re-graded with OpenAI's
**Decisions API** (`gpt-6-luna`) and compared with the existing
**`ollama:qwen3.6`** verdicts, TypeSafe's **Jev** (`jev-1.13.0`, see
[JEV.md](JEV.md)) and Bespoke Labs' **Nimble** (see [NIMBLE.md](NIMBLE.md)).

## Setup

- **Model**: `gpt-6-luna` via `POST /decisions` (OpenAI Python SDK 3.26.0+), a
  model dedicated to classification, scoring and probability judgements.
- **Judge**: [judge-openai.py](judge-openai.py), a port of
  [judge-jev.py](judge-jev.py) with the same rubric: one Choice question over
  `correct` / `partial` / `incorrect`, with the same instruction and criterion
  wording. Two differences follow from the API:
  - The input is a string, so the state Jev receives as an object is sent as
    indented JSON.
  - A question has a single `instructions` string, so Jev's two instruction
    sentences are joined.

  The scheme is therefore `choice@849ecf1c` rather than Jev's
  `choice@19579e23` (recorded in `results-<lang>/openai/MODELS.tsv`).
- **Inputs**: Same contract as `judge.py`, `judge-jev.py` and `judge-nimble.py`
  — question, gold answer, rationale, candidate answer; **no** chapter source
  text.
- **Output**: `results-<lang>/openai/<method>.tsv`, holding the probabilities of
  `correct` / `partial` / `incorrect` and the model's confidence.
- **Aggregation**: `uv run report.py -l <lang> --openai`. Each question counts
  as its most probable verdict, with ties broken to the stricter verdict.
  - **Weighted** = `(correct + 0.5 · partial) / 50`
  - **E** = mean of `P(correct) + 0.5 · P(partial)` (continuous expectation
    over the output probabilities)

## Performance & Cost

| Metric | Jev (`judge-jev.py`) | Nimble (`judge-nimble.py`) | OpenAI (`judge-openai.py`) |
| :--- | :--- | :--- | :--- |
| **Hosting** | Cloud API (TypeSafe) | Local (Ollama) | **Cloud API (OpenAI)** |
| **API Cost** | $0.0501 / 1,500 req | $0.00 (Local) | **$0.0799 / 1,500 req** ($0.10 / 1M input tokens) |
| **Wall Time (en, 750 req)** | 2m 46s | 7m 46s | **3m 36s** (0.29 s / req) |
| **Wall Time (ja, 750 req)** | 2m 51s | 8m 10s | **3m 27s** (0.28 s / req) |
| **Total Wall Time (1,500 req)** | 5m 37s | 15m 56s | **7m 3s** (0.28 s / req) |
| **Input Tokens (en / ja)** | 516k / 676k | 380k / 417k | **345k / 454k (533 / req avg)** |
| **Output Tokens (total)** | 58,500 | 1,500 | **0** |

The Decisions API reports no output tokens at all: the verdict is returned as
probabilities, with nothing generated. The cost is therefore input tokens only:
798,930 tokens = $0.0799 for the whole run ($0.0345 en / $0.0454 ja), about 1.6×
Jev's.

Relative to Jev, Jev : OpenAI is about 1 : 1.26 in wall time (1 : 1.30 en,
1 : 1.21 ja) and 1 : 1.59 in cost. The per-model re-grading in `results/`
([results/OPENAI.md](results/OPENAI.md)) gives 1 : 1.11 and 1 : 1.60 per file:
the cost ratio holds across runs, while the time ratio varies with API
response times.

---

## Results

### Summary Table (All 15 Methods)

| Method | en Qwen | en Jev | en Nimble | en OpenAI | en E | ja Qwen | ja Jev | ja Nimble | ja OpenAI | ja E |
| :--- | :---: | :---: | :---: | :---: | ---: | :---: | :---: | :---: | :---: | ---: |
| **Vector k=5** | 0.840 (40/4/6) | 0.730 (29/15/6) | 0.800 (36/8/6) | **0.800** (35/10/5) | 0.790 | 0.810 (38/5/7) | 0.760 (32/12/6) | 0.770 (33/11/6) | **0.770** (33/11/6) | 0.774 |
| **Vector k=10** | 0.930 (45/3/2) | 0.850 (37/11/2) | 0.900 (42/6/2) | **0.880** (39/10/1) | 0.885 | 0.900 (43/4/3) | 0.820 (36/10/4) | 0.870 (40/7/3) | **0.840** (38/8/4) | 0.833 |
| **Vector-line k=5** | 0.800 (35/10/5) | 0.740 (29/16/5) | 0.780 (33/12/5) | **0.810** (34/13/3) | 0.788 | 0.800 (36/8/6) | 0.740 (29/16/5) | 0.790 (33/13/4) | **0.740** (30/14/6) | 0.745 |
| **Vector-line k=10** | 0.890 (41/7/2) | 0.810 (33/15/2) | 0.890 (41/7/2) | **0.870** (37/13/0) | 0.861 | 0.860 (41/4/5) | 0.780 (32/14/4) | 0.840 (37/10/3) | **0.820** (35/12/3) | 0.815 |
| **V-hybrid k=5** | 0.880 (40/8/2) | 0.850 (37/11/2) | 0.890 (41/7/2) | **0.880** (39/10/1) | 0.872 | 0.890 (42/5/3) | 0.820 (35/12/3) | 0.840 (37/10/3) | **0.830** (36/11/3) | 0.827 |
| **V-hybrid k=10** | 0.910 (43/5/2) | 0.840 (35/14/1) | 0.880 (39/10/1) | **0.880** (38/12/0) | 0.877 | 0.910 (44/3/3) | 0.830 (36/11/3) | 0.880 (40/8/2) | **0.830** (36/11/3) | 0.831 |
| **Hybrid k=5** | 0.900 (42/6/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | **0.860** (37/12/1) | 0.855 | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.880 (39/10/1) | **0.860** (37/12/1) | 0.863 |
| **Hybrid k=8** | 0.930 (45/3/2) | 0.870 (39/9/2) | 0.920 (44/4/2) | **0.880** (40/8/2) | 0.880 | 0.950 (46/3/1) | 0.860 (37/12/1) | 0.910 (42/7/1) | **0.890** (40/9/1) | 0.875 |
| **Hybrid k=10** | 0.960 (47/2/1) | 0.870 (38/11/1) | 0.910 (41/9/0) | **0.930** (43/7/0) | 0.917 | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.890 (40/9/1) | **0.830** (34/15/1) | 0.845 |
| **Extract** | 0.850 (40/5/5) | 0.780 (32/14/4) | 0.850 (39/7/4) | **0.810** (35/11/4) | 0.805 | 0.860 (41/4/5) | 0.770 (30/17/3) | 0.800 (33/14/3) | **0.800** (33/14/3) | 0.788 |
| **Filter2** | 0.790 (36/7/7) | 0.760 (32/12/6) | 0.770 (33/11/6) | **0.770** (33/11/6) | 0.768 | 0.850 (41/3/6) | 0.740 (30/14/6) | 0.790 (35/9/6) | **0.730** (29/15/6) | 0.747 |
| **Filter3** | 0.940 (46/2/2) | 0.890 (41/7/2) | 0.940 (46/2/2) | **0.910** (43/5/2) | 0.904 | 0.890 (43/3/4) | 0.860 (40/6/4) | 0.910 (44/3/3) | **0.840** (37/10/3) | 0.857 |
| **Ceiling** | 0.990 (49/1/0) | 0.970 (47/3/0) | 0.950 (45/5/0) | **0.960** (46/4/0) | 0.956 | 0.980 (48/2/0) | 0.920 (42/8/0) | 0.960 (46/4/0) | **0.920** (42/8/0) | 0.909 |
| **GraphRAG local** | 0.650 (27/11/12) | 0.560 (17/22/11) | 0.630 (23/17/10) | **0.560** (18/20/12) | 0.569 | 0.640 (28/8/14) | 0.550 (20/15/15) | 0.610 (22/17/11) | **0.590** (20/19/11) | 0.591 |
| **GraphRAG global** | 0.170 (5/7/38) | 0.130 (1/11/38) | 0.150 (2/11/37) | **0.140** (1/12/37) | 0.140 | 0.240 (8/8/34) | 0.200 (3/14/33) | 0.230 (4/15/31) | **0.230** (4/15/31) | 0.226 |

*Cells read `weighted (correct / partial / incorrect)`. `E` is OpenAI's
probability expectation.*

---

## Analysis & Insights

### 1. Strictness: Between Nimble and Jev

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Qwen 3.6** | 1,170 (78.0%) | 147 (9.8%) | 183 (12.2%) | 0.829 / 0.829 |
| **Nimble** | 1,068 (71.2%) | 273 (18.2%) | 159 (10.6%) | 0.808 / 0.798 |
| **OpenAI** | **1,002 (66.8%)** | **342 (22.8%)** | **156 (10.4%)** | **0.796 / 0.768** |
| **Jev** | 954 (63.6%) | 374 (24.9%) | 172 (11.5%) | 0.766 / 0.755 |

OpenAI is stricter than Nimble and more lenient than Jev. The mean of E is
0.791 en / 0.768 ja, close to the weighted means.

### 2. Disagreement & Agreement Rates

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **Jev vs OpenAI**: **89.5%** (1,342 / 1,500) — *en: 89.5%, ja: 89.5%*
- **Nimble vs OpenAI**: **87.9%** (1,319 / 1,500) — *en: 89.6%, ja: 86.3%*
- **Qwen vs OpenAI**: **84.8%** (1,272 / 1,500) — *en: 87.5%, ja: 82.1%*

For reference, the other pairs are Qwen vs Nimble 88.2%, Jev vs Nimble 87.1%
and Qwen vs Jev 83.9% (see [NIMBLE.md](NIMBLE.md)). Jev vs OpenAI is the
highest of all six pairs overall.

#### Combined Confusion Matrix (1,500 Questions)

```
Qwen \ OpenAI:
              correct   partial   incorrect
correct           990       179           1
partial            12       131           4
incorrect           0        32         151

Jev \ OpenAI:
              correct   partial   incorrect
correct           911        43           0
partial            91       279           4
incorrect           0        20         152

Nimble \ OpenAI:
              correct   partial   incorrect
correct           957       111           0
partial            45       217          11
incorrect           0        14         145
```

### 3. Consensus on Incorrect Answers

OpenAI gives the fewest *incorrect* verdicts (156). Of them, 151 are shared with
Qwen, 152 with Jev and 145 with Nimble, and no answer is ever judged *correct*
by one side and *incorrect* by the other except a single Qwen case. As with the
other judges, the variation lies at the boundary between *correct* and
*partial*.

### 4. Language Consistency

OpenAI shows the largest drop from English to Japanese of the four judges:

| Judge | ja − en (mean over 15 methods) | Methods dropped / rose |
| :--- | ---: | :---: |
| Qwen 3.6 | +0.001 | 7 / 6 |
| Nimble | −0.010 | 9 / 5 |
| Jev | −0.011 | 11 / 2 |
| **OpenAI** | **−0.028** | **11 / 3** |

- **Ceiling**: en 0.960 → ja 0.920, the same Japanese score as Jev.
- **Largest drops**: Hybrid k=10 (en 0.930 → ja 0.830), Filter3 (0.910 →
  0.840) and Vector-line k=5 (0.810 → 0.740).
- **Method rankings**: In English, Hybrid k=10 is second only to Ceiling
  (0.930), followed by Filter3 (0.910). In Japanese, Hybrid k=8 is second
  (0.890), followed by Hybrid k=5 (0.860); Hybrid k=10 falls to 0.830.

The rubric is in English for every language, as with Jev, which may contribute
to the drop; this run does not isolate the cause.

---

## Conclusion

1. **Fast & Generation-Free**: ~0.28 s per decision, with no output tokens;
   $0.08 for all 1,500 decisions.
2. **Moderate Strictness**: Between Nimble and Jev, and the closest to Jev in
   verdicts (89.5% agreement).
3. **Language Sensitivity**: Japanese scores drop by 0.028 on average, about
   three times Jev's or Nimble's drop, which reshuffles the method ranking
   between languages.
