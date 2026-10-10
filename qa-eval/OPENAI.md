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
| **Vector k=5** | 0.820 (38/6/6) | 0.720 (28/16/6) | 0.790 (35/9/6) | **0.770** (32/13/5) | 0.766 | 0.800 (37/6/7) | 0.760 (32/12/6) | 0.760 (32/12/6) | **0.770** (33/11/6) | 0.765 |
| **Vector k=10** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.890 (41/7/2) | **0.860** (37/12/1) | 0.869 | 0.900 (43/4/3) | 0.820 (37/8/5) | 0.880 (41/6/3) | **0.830** (37/9/4) | 0.835 |
| **Vector-line k=5** | 0.770 (33/11/6) | 0.750 (30/15/5) | 0.800 (35/10/5) | **0.790** (32/15/3) | 0.780 | 0.790 (34/11/5) | 0.750 (30/15/5) | 0.780 (33/12/5) | **0.730** (29/15/6) | 0.739 |
| **Vector-line k=10** | 0.850 (38/9/3) | 0.800 (32/16/2) | 0.890 (41/7/2) | **0.860** (37/12/1) | 0.845 | 0.860 (41/4/5) | 0.790 (33/13/4) | 0.850 (38/9/3) | **0.800** (33/14/3) | 0.798 |
| **V-hybrid k=5** | 0.870 (39/9/2) | 0.820 (34/14/2) | 0.880 (40/8/2) | **0.880** (39/10/1) | 0.866 | 0.890 (42/5/3) | 0.800 (34/12/4) | 0.840 (38/8/4) | **0.820** (35/12/3) | 0.822 |
| **V-hybrid k=10** | 0.930 (44/5/1) | 0.860 (37/12/1) | 0.900 (41/8/1) | **0.900** (40/10/0) | 0.894 | 0.900 (43/4/3) | 0.810 (35/11/4) | 0.860 (39/8/3) | **0.830** (36/11/3) | 0.820 |
| **Hybrid k=5** | 0.880 (40/8/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | **0.870** (38/11/1) | 0.856 | 0.930 (45/3/2) | 0.840 (35/14/1) | 0.910 (42/7/1) | **0.860** (37/12/1) | 0.862 |
| **Hybrid k=8** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.910 (43/5/2) | **0.870** (38/11/1) | 0.859 | 0.920 (43/6/1) | 0.830 (34/15/1) | 0.910 (42/7/1) | **0.880** (39/10/1) | 0.869 |
| **Hybrid k=10** | 0.980 (48/2/0) | 0.900 (40/10/0) | 0.930 (43/7/0) | **0.950** (45/5/0) | 0.928 | 0.910 (42/7/1) | 0.860 (37/12/1) | 0.890 (40/9/1) | **0.850** (36/13/1) | 0.848 |
| **Extract** | 0.860 (40/6/4) | 0.780 (32/14/4) | 0.850 (39/7/4) | **0.840** (38/8/4) | 0.826 | 0.870 (41/5/4) | 0.770 (30/17/3) | 0.830 (36/11/3) | **0.790** (33/13/4) | 0.784 |
| **Filter2** | 0.800 (37/6/7) | 0.770 (33/11/6) | 0.800 (36/8/6) | **0.790** (35/9/6) | 0.779 | 0.820 (38/6/6) | 0.740 (30/14/6) | 0.800 (36/8/6) | **0.740** (30/14/6) | 0.754 |
| **Filter3** | 0.930 (45/3/2) | 0.880 (40/8/2) | 0.920 (44/4/2) | **0.910** (43/5/2) | 0.900 | 0.870 (41/5/4) | 0.840 (39/6/5) | 0.900 (43/4/3) | **0.850** (38/9/3) | 0.852 |
| **Ceiling** | 0.990 (49/1/0) | 0.930 (43/7/0) | 0.960 (46/4/0) | **0.970** (47/3/0) | 0.954 | 0.990 (49/1/0) | 0.900 (40/10/0) | 0.950 (45/5/0) | **0.910** (41/9/0) | 0.897 |
| **GraphRAG local** | 0.610 (24/13/13) | 0.550 (17/21/12) | 0.610 (22/17/11) | **0.590** (19/21/10) | 0.581 | 0.630 (26/11/13) | 0.560 (21/14/15) | 0.610 (22/17/11) | **0.570** (18/21/11) | 0.581 |
| **GraphRAG global** | 0.170 (3/11/36) | 0.130 (1/11/38) | 0.140 (1/12/37) | **0.140** (1/12/37) | 0.140 | 0.190 (6/7/37) | 0.210 (3/15/32) | 0.210 (3/15/32) | **0.240** (4/16/30) | 0.233 |

*Cells read `weighted (correct / partial / incorrect)`. `E` is OpenAI's
probability expectation.*

---

## Analysis & Insights

### 1. Strictness: Between Nimble and Jev

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Qwen 3.6** | 1,137 (75.8%) | 183 (12.2%) | 180 (12.0%) | 0.820 / 0.818 |
| **Nimble** | 1,075 (71.7%) | 261 (17.4%) | 164 (10.9%) | 0.809 / 0.799 |
| **OpenAI** | **1,000 (66.7%)** | **346 (23.1%)** | **154 (10.3%)** | **0.799 / 0.765** |
| **Jev** | 944 (62.9%) | 381 (25.4%) | 175 (11.7%) | 0.761 / 0.752 |

OpenAI is stricter than Nimble and more lenient than Jev. The mean of E is
0.789 en / 0.764 ja, close to the weighted means.

### 2. Disagreement & Agreement Rates

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **Jev vs OpenAI**: **88.6%** (1,329 / 1,500) — *en: 89.3%, ja: 87.9%*
- **Nimble vs OpenAI**: **87.4%** (1,311 / 1,500) — *en: 89.1%, ja: 85.7%*
- **Qwen vs OpenAI**: **86.3%** (1,294 / 1,500) — *en: 89.1%, ja: 83.5%*

For reference, the other pairs are Qwen vs Nimble 89.8%, Jev vs Nimble 86.4%
and Qwen vs Jev 84.7% (see [NIMBLE.md](NIMBLE.md)). Jev vs OpenAI is the
second highest of the six pairs overall, after Qwen vs Nimble. The same
`gpt-6-luna` through the ordinary API, replying with the verdict word only,
agrees with OpenAI on 91.1% (see [TERNARY.md](TERNARY.md)).

#### Combined Confusion Matrix (1,500 Questions)

```
Qwen \ OpenAI:
              correct   partial   incorrect
correct           984       152           1
partial            16       162           5
incorrect           0        32         148

Jev \ OpenAI:
              correct   partial   incorrect
correct           902        42           0
partial            98       278           5
incorrect           0        26         149

Nimble \ OpenAI:
              correct   partial   incorrect
correct           957       118           0
partial            43       209           9
incorrect           0        19         145
```

### 3. Consensus on Incorrect Answers

OpenAI gives the fewest *incorrect* verdicts (154). Of them, 148 are shared with
Qwen, 149 with Jev and 145 with Nimble, and no answer is ever judged *correct*
by one side and *incorrect* by the other except a single Qwen case. As with the
other judges, the variation lies at the boundary between *correct* and
*partial*.

### 4. Language Consistency

OpenAI shows the largest drop from English to Japanese of the four judges:

| Judge | ja − en (mean over 15 methods) | Methods dropped / rose |
| :--- | ---: | :---: |
| Qwen 3.6 | −0.002 | 5 / 8 |
| Nimble | −0.010 | 10 / 2 |
| Jev | −0.009 | 10 / 3 |
| **OpenAI** | **−0.035** | **12 / 2** |

- **Ceiling**: en 0.970 → ja 0.910, close to Jev's Japanese score (0.900).
- **Largest drops**: Hybrid k=10 (en 0.950 → ja 0.850), V-hybrid k=10 (0.900
  → 0.830) and Filter3 (0.910 → 0.850).
- **Method rankings**: In English, Hybrid k=10 is second only to Ceiling
  (0.950), followed by Filter3 (0.910). In Japanese, Hybrid k=8 is second
  (0.880), followed by Hybrid k=5 (0.860); Hybrid k=10 falls to 0.850.

The rubric is in English for every language, as with Jev, which may contribute
to the drop; this run does not isolate the cause.

---

## Conclusion

1. **Fast & Generation-Free**: ~0.28 s per decision, with no output tokens;
   $0.08 for all 1,500 decisions.
2. **Moderate Strictness**: Between Nimble and Jev, and the closest to Jev in
   verdicts (88.6% agreement).
3. **Language Sensitivity**: Japanese scores drop by 0.035 on average, three
   to four times Jev's or Nimble's drop, which reshuffles the method ranking
   between languages.
