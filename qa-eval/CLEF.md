# Re-grading with Clef

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language = 1,500 requests in total) was re-graded with Cloudflare's
**[Clef](https://ollama.com/library/clef)** (hosted locally via Ollama) and
compared with the existing **`ollama:qwen3.6`**, TypeSafe **Jev**
(`jev-1.14.0`), Bespoke Labs **Nimble** and Cloudflare **Clef Flash** verdicts.
For the multi-model comparison across 63 models in `results/`, see
[results/CLEF.md](results/CLEF.md).

Clef is the larger sibling of Clef Flash ([CLEF-FLASH.md](CLEF-FLASH.md)), so
the main question is whether the larger model fixes Clef Flash's leniency and
its handling of refusals.

## Setup

- **Model**: [Clef](https://ollama.com/library/clef) (`clef`), a 27B multimodal
  decision model from Cloudflare fine-tuned from Qwen 3.8 27B (Apache 2.0),
  served by Ollama 0.35.1+ through the `/v1/systemone` endpoint like Nimble and
  Clef Flash. Only text is used here.
- **Judge**: [judge-clef.py](judge-clef.py), a wrapper around
  [ollama_systemone.py](ollama_systemone.py) shared with
  [judge-nimble.py](judge-nimble.py) and
  [judge-clef-flash.py](judge-clef-flash.py); only the model differs. The
  scheme is `choice@19579e23` (the same rubric and scheme ID as Jev, Nimble and
  Clef Flash, recorded in `results-<lang>/clef/MODELS.tsv`).
- **Inputs**: Same contract as `judge.py` and the other TSV judges: question,
  gold answer, rationale, candidate answer; **no** chapter source text.
- **Output**: `results-<lang>/clef/<method>.tsv`, holding the probabilities of
  `correct` / `partial` / `incorrect` and Clef's confidence.
- **Aggregation**: Each question counts as its most probable verdict, with ties
  broken to the stricter verdict.
  - **Weighted** = `(correct + 0.5 · partial) / 50`
  - **E** = mean of `P(correct) + 0.5 · P(partial)` (continuous expectation
    over the output probabilities)

## Performance

Clef runs locally at no API cost and returns probabilities without generating
text, like the other two System One models on Ollama.

| Metric | Nimble | Clef Flash | Clef (`judge-clef.py`) |
| :--- | :--- | :--- | :--- |
| **Wall Time (en, 750 req)** | 7m 46s (0.62 s / req) | 7m 11s (0.58 s / req) | 21m 54s (1.75 s / req) |
| **Wall Time (ja, 750 req)** | 8m 10s (0.65 s / req) | 7m 49s (0.63 s / req) | 24m 2s (1.92 s / req) |
| **Total Wall Time (1,500 req)** | 15m 56s (0.64 s / req) | 15m 0s (0.60 s / req) | 45m 56s (1.84 s / req) |
| **Input Tokens (en / ja)** | 380k / 417k | 367k / 408k | 367k / 408k (489 / 544 per req) |
| **Output Tokens (total)** | 1,500 (1 / req) | 0 | 0 |

With three times the parameters of Clef Flash, Clef takes about three times as
long per request. The input token counts are identical to Clef Flash's.

---

## Results

### Summary Table (All 15 Methods)

| Method | en Qwen | en Jev | en Nimble | en Flash | en Clef | en E | ja Qwen | ja Jev | ja Nimble | ja Flash | ja Clef | ja E |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | :---: | :---: | :---: | :---: | :---: | ---: |
| **Vector k=5** | 0.820 (38/6/6) | 0.730 (28/17/5) | 0.790 (35/9/6) | 0.830 (38/7/5) | **0.770** (32/13/5) | 0.743 | 0.800 (37/6/7) | 0.750 (31/13/6) | 0.760 (32/12/6) | 0.830 (38/7/5) | **0.750** (30/15/5) | 0.723 |
| **Vector k=10** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.890 (41/7/2) | 0.930 (45/3/2) | **0.840** (36/12/2) | 0.811 | 0.900 (43/4/3) | 0.830 (36/11/3) | 0.880 (41/6/3) | 0.900 (43/4/3) | **0.810** (34/13/3) | 0.771 |
| **Vector-line k=5** | 0.770 (33/11/6) | 0.740 (30/14/6) | 0.800 (35/10/5) | 0.840 (38/8/4) | **0.750** (31/13/6) | 0.736 | 0.790 (34/11/5) | 0.730 (28/17/5) | 0.780 (33/12/5) | 0.850 (37/11/2) | **0.720** (25/22/3) | 0.710 |
| **Vector-line k=10** | 0.850 (38/9/3) | 0.810 (33/15/2) | 0.890 (41/7/2) | 0.950 (45/5/0) | **0.780** (31/16/3) | 0.773 | 0.860 (41/4/5) | 0.790 (33/13/4) | 0.850 (38/9/3) | 0.900 (42/6/2) | **0.780** (32/14/4) | 0.759 |
| **V-hybrid k=5** | 0.870 (39/9/2) | 0.820 (34/14/2) | 0.880 (40/8/2) | 0.950 (46/3/1) | **0.800** (33/14/3) | 0.787 | 0.890 (42/5/3) | 0.800 (34/12/4) | 0.840 (38/8/4) | 0.900 (42/6/2) | **0.790** (33/13/4) | 0.766 |
| **V-hybrid k=10** | 0.930 (44/5/1) | 0.850 (36/13/1) | 0.900 (41/8/1) | 0.950 (46/3/1) | **0.850** (36/13/1) | 0.816 | 0.900 (43/4/3) | 0.810 (35/11/4) | 0.860 (39/8/3) | 0.910 (43/5/2) | **0.780** (31/16/3) | 0.764 |
| **Hybrid k=5** | 0.880 (40/8/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | 0.950 (45/5/0) | **0.800** (33/14/3) | 0.797 | 0.930 (45/3/2) | 0.850 (36/13/1) | 0.910 (42/7/1) | 0.930 (44/5/1) | **0.810** (32/17/1) | 0.785 |
| **Hybrid k=8** | 0.920 (44/4/2) | 0.870 (39/9/2) | 0.910 (43/5/2) | 0.930 (45/3/2) | **0.850** (37/11/2) | 0.809 | 0.920 (43/6/1) | 0.810 (32/17/1) | 0.910 (42/7/1) | 0.960 (47/2/1) | **0.780** (29/20/1) | 0.793 |
| **Hybrid k=10** | 0.980 (48/2/0) | 0.890 (39/11/0) | 0.930 (43/7/0) | 0.980 (48/2/0) | **0.870** (37/13/0) | 0.844 | 0.910 (42/7/1) | 0.860 (37/12/1) | 0.890 (40/9/1) | 0.960 (47/2/1) | **0.820** (33/16/1) | 0.785 |
| **Extract** | 0.860 (40/6/4) | 0.810 (35/11/4) | 0.850 (39/7/4) | 0.910 (44/3/3) | **0.840** (38/8/4) | 0.799 | 0.870 (41/5/4) | 0.770 (31/15/4) | 0.830 (36/11/3) | 0.910 (43/5/2) | **0.790** (31/17/2) | 0.757 |
| **Filter2** | 0.800 (37/6/7) | 0.780 (34/10/6) | 0.800 (36/8/6) | 0.840 (40/4/6) | **0.760** (32/12/6) | 0.739 | 0.820 (38/6/6) | 0.740 (30/14/6) | 0.800 (36/8/6) | 0.870 (42/3/5) | **0.750** (30/15/5) | 0.720 |
| **Filter3** | 0.930 (45/3/2) | 0.890 (41/7/2) | 0.920 (44/4/2) | 0.930 (45/3/2) | **0.890** (41/7/2) | 0.827 | 0.870 (41/5/4) | 0.830 (37/9/4) | 0.900 (43/4/3) | 0.930 (45/3/2) | **0.830** (35/13/2) | 0.785 |
| **Ceiling** | 0.990 (49/1/0) | 0.960 (46/4/0) | 0.960 (46/4/0) | 0.960 (46/4/0) | **0.900** (40/10/0) | 0.862 | 0.990 (49/1/0) | 0.880 (38/12/0) | 0.950 (45/5/0) | 0.980 (48/2/0) | **0.840** (34/16/0) | 0.810 |
| **GraphRAG local** | 0.610 (24/13/13) | 0.570 (19/19/12) | 0.610 (22/17/11) | 0.720 (32/8/10) | **0.600** (21/18/11) | 0.583 | 0.630 (26/11/13) | 0.550 (20/15/15) | 0.610 (22/17/11) | 0.680 (28/12/10) | **0.600** (22/16/12) | 0.589 |
| **GraphRAG global** | 0.170 (3/11/36) | 0.130 (1/11/38) | 0.140 (1/12/37) | 0.240 (7/10/33) | **0.140** (1/12/37) | 0.154 | 0.190 (6/7/37) | 0.220 (3/16/31) | 0.210 (3/15/32) | 0.450 (17/11/22) | **0.220** (4/14/32) | 0.228 |

*Cells read `weighted (correct / partial / incorrect)`. `E` is the probability
expectation of Clef. "Flash" is Clef Flash; Jev is the current `jev-1.14.0`;
the Qwen, Jev, Nimble and Flash columns are those of
[CLEF-FLASH.md](CLEF-FLASH.md).*

---

## Analysis

### 1. The Strictest of the Five

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| Clef Flash | 1,216 (81.1%) | 155 (10.3%) | 129 (8.6%) | 0.861 / 0.864 |
| Qwen 3.6 | 1,137 (75.8%) | 183 (12.2%) | 180 (12.0%) | 0.820 / 0.818 |
| Nimble | 1,075 (71.7%) | 261 (17.4%) | 164 (10.9%) | 0.809 / 0.799 |
| Jev | 947 (63.1%) | 381 (25.4%) | 172 (11.5%) | 0.769 / 0.748 |
| **Clef** | **914 (60.9%)** | **423 (28.2%)** | **163 (10.9%)** | **0.763 / 0.738** |

Where Clef Flash is the most lenient judge, Clef is the strictest: it gives the
fewest *correct* and the most *partial* verdicts of the five, while its
*incorrect* count is about the same as Nimble's and Jev's. It scores below Qwen
in 29 of the 30 method × language cells (all but Japanese GraphRAG global),
below Nimble in 28 (it ties on English GraphRAG global and is higher on Japanese
GraphRAG global) and below Clef Flash in all 30. Against Jev it is higher in 8
cells, equal in 6 and lower in 16. Its Ceiling scores
(0.900 en / 0.840 ja) are the lowest of the five judges.

### 2. Agreement

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **Jev vs Clef**: **87.1%** (1,306 / 1,500): *en 88.9%, ja 85.2%*
- **Nimble vs Clef**: **83.1%** (1,246 / 1,500): *en 86.5%, ja 79.6%*
- **Qwen vs Clef**: **81.3%** (1,219 / 1,500): *en 84.9%, ja 77.6%*
- **Clef Flash vs Clef**: **77.3%** (1,159 / 1,500): *en 78.9%, ja 75.6%*

Clef agrees most with Jev, at about the same level as Jev vs Nimble (86.9%).
Its agreement with Clef Flash, its smaller sibling, is the lowest of all ten
pairs among the five judges.

#### Combined Confusion Matrices (1,500 Questions)

```
Qwen \ Clef:
              correct   partial   incorrect
correct           901       235           1
partial            13       163           7
incorrect           0        25         155

Jev \ Clef:
              correct   partial   incorrect
correct           846       101           0
partial            68       305           8
incorrect           0        17         155

Nimble \ Clef:
              correct   partial   incorrect
correct           879       196           0
partial            35       215          11
incorrect           0        12         152

Clef Flash \ Clef:
              correct   partial   incorrect
correct           903       296          17
partial            11       127          17
incorrect           0         0         129
```

The main shift is *correct* → Clef *partial*: 235 from Qwen (13 the other way),
196 from Nimble and 296 from Clef Flash. No judge's *incorrect* becomes a Clef
*correct*.

### 3. Partial for a Missing Detail

Of the 235 answers that Qwen grades *correct* and Clef *partial*, Jev also
marks 136 *partial*, Nimble 62 and Clef Flash 20; in 84 all four other judges
agree on *correct*. These are typically complete answers that leave out a
secondary detail of the gold answer. For example, on Ceiling Q39 (en), the
answer explains that the canal was blocked with Sal logs and that Rammohan's
men pulled the boat over them, but not that the guards were distracted; on
Ceiling Q30 (ja), it explains Ramchandra's remarriage and its consequence, but
not that Biva had refused to leave her grieving brother. Clef keeps some doubt
on these verdicts (mean P(correct) 0.27), but *partial* is the most probable.

### 4. Refusals and Factual Errors

Clef treats a refusal as *incorrect*, as the rubric requires. All 60 GraphRAG
global answers that consist of the fixed sentence *"I am sorry but I am unable
to answer this question given the provided data."* are graded *incorrect*:

| Judge | en (34) | ja (26) | Mean P(correct) (en / ja) |
| :--- | :--- | :--- | :---: |
| Qwen | 33 incorrect, 1 correct | 26 incorrect | — |
| Jev | 34 incorrect | 26 incorrect | 0.00 / 0.00 |
| Nimble | 34 incorrect | 26 incorrect | 0.00 / 0.00 |
| Clef Flash | 31 incorrect, 3 correct | 19 incorrect, 7 correct | 0.16 / 0.29 |
| **Clef** | **34 incorrect** | **26 incorrect** | **0.01 / 0.01** |

Clef also catches factual errors that the other local judges let through.
"The entire night" for the gold "Five days" (Hybrid k=5 Q17, en) is
*incorrect* with P = 0.87, where Clef Flash grades it *correct* and Nimble
*partial*. Clef's *incorrect* verdicts mostly agree with the other judges
(155 of Qwen's 180 *incorrect*); where Jev and Nimble settle for *partial*, it
penalizes a wrong key fact, such as "his own cloth" for the gold "Sitaram's own
cloth" (Vector-line k=10 Q22, en; Qwen also *incorrect*).

### 5. Decisiveness

Clef's most probable verdict gets 0.827 on average (median 0.879), between
Clef Flash (0.777 / 0.818) and Nimble (0.942 / 0.998), and slightly below Jev
(0.867 / 0.970). It falls below 0.6 on 176 questions, about as often as Jev
(170) and Clef Flash (181), against Nimble's 46. **E** sits below the weighted
score in 27 of the 30 cells; the exceptions are GraphRAG global in both
languages (0.154 vs. 0.140 en, 0.228 vs. 0.220 ja) and Japanese Hybrid k=8
(0.793 vs. 0.780).

### 6. Language Consistency

- **Ceiling**: en 0.900 vs ja 0.840.
- **Average delta**: ja − en averages **−0.025** over the 15 methods, with
  Japanese lower in 11 of them: the largest gap of the five judges (Jev −0.021,
  Nimble −0.010, Qwen −0.002, Clef Flash +0.003).
- **Method rankings**: Ceiling leads in both languages (0.900 / 0.840), followed
  by Filter3 (0.890 / 0.830). GraphRAG aside, the methods span 0.15 in English
  (0.750–0.900) and 0.12 in Japanese (0.720–0.840).

---

## Conclusion

Clef runs the same way as Nimble and Clef Flash (local and free) through the
shared [ollama_systemone.py](ollama_systemone.py), at about 1.8 s per decision.
Compared with Clef Flash:

1. **Refusals are fixed**: every fixed refusal sentence is *incorrect*, and
   factual errors that Clef Flash accepts are rejected.
2. **The leniency turns into strictness**: Clef is the strictest of the five
   judges, marking *partial* many answers that miss only a secondary detail,
   so its scores are the lowest even on Ceiling.
3. **Close to Jev**: its verdicts agree most with Jev (87.1%), and its
   Japanese scores fall below English by about as much as Jev's.

Clef is a usable local judge on the strict side, close to Jev, but it is three
times slower than Nimble, and across models its scores correlate with Qwen,
Nimble and Clef Flash ($r$ = 0.81–0.85) less than any two of the other four
judges do with each other (0.86–0.96; see
[results/CLEF.md](results/CLEF.md)). For this
evaluation, Nimble remains the default local judge; Clef's verdicts are kept in
`clef/` for comparison.
