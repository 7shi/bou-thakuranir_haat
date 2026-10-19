# Re-grading with Clef Flash

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language = 1,500 requests in total) was re-graded with Cloudflare's
**[Clef Flash](https://ollama.com/library/clef-flash)** (hosted locally via
Ollama) and compared with the existing **`ollama:qwen3.6`**, TypeSafe **Jev**
(`jev-1.14.0`) and Bespoke Labs **Nimble** verdicts. For the multi-model
comparison across 63 models in `results/`, see
[results/clef-flash/README.md](../results/clef-flash/README.md).

Clef Flash is the second System One model on Ollama after Nimble, and the two
are fine-tuned from the same base (Qwen 3.5 9B), so the main comparison is with
Nimble ([NIMBLE.md](NIMBLE.md)).

## Setup

- **Model**: [Clef Flash](https://ollama.com/library/clef-flash) (`clef-flash`),
  a 9B multimodal decision model from Cloudflare fine-tuned from Qwen 3.5 9B
  (Apache 2.0), served by Ollama 0.35.1+ through the `/v1/systemone` endpoint
  like Nimble. Only text is used here.
- **Judge**: [judge-clef-flash.py](../judge-clef-flash.py), a wrapper around
  [ollama_systemone.py](../ollama_systemone.py) shared with
  [judge-nimble.py](../judge-nimble.py); only the model differs. The scheme is
  `choice@19579e23` (the same rubric and scheme ID as Jev and Nimble, recorded
  in `results-<lang>/clef-flash/MODELS.tsv`).
- **Inputs**: Same contract as `judge.py`, `judge-jev.py` and `judge-nimble.py`:
  question, gold answer, rationale, candidate answer; **no** chapter source text.
- **Output**: `results-<lang>/clef-flash/<method>.tsv`, holding the
  probabilities of `correct` / `partial` / `incorrect` and Clef Flash's
  confidence.
- **Aggregation**: Each question counts as its most probable verdict, with ties
  broken to the stricter verdict.
  - **Weighted** = `(correct + 0.5 · partial) / 50`
  - **E** = mean of `P(correct) + 0.5 · P(partial)` (continuous expectation
    over the output probabilities)

## Performance

Like Nimble, Clef Flash runs locally at no API cost and returns probabilities
without generating text.

| Metric | Nimble (`judge-nimble.py`) | Clef Flash (`judge-clef-flash.py`) |
| :--- | :--- | :--- |
| **Wall Time (en, 750 req)** | 7m 46s (0.62 s / req) | **7m 11s** (0.58 s / req) |
| **Wall Time (ja, 750 req)** | 8m 10s (0.65 s / req) | **7m 49s** (0.63 s / req) |
| **Total Wall Time (1,500 req)** | 15m 56s (0.64 s / req) | **15m 0s** (0.60 s / req) |
| **Input Tokens (en / ja)** | 380k / 417k | **367k / 408k** (489 / 544 per req) |
| **Output Tokens (total)** | 1,500 (1 / req) | **0** |

Both share the same base model and input, so speed and input tokens are close;
Clef Flash is about 6% faster. It reports no output tokens, where Nimble
reports one per request.

---

## Results

### Summary Table (All 15 Methods)

| Method | en Qwen | en Jev | en Nimble | en Clef | en E | ja Qwen | ja Jev | ja Nimble | ja Clef | ja E |
| :--- | :---: | :---: | :---: | :---: | ---: | :---: | :---: | :---: | :---: | ---: |
| **Vector k=5** | 0.820 (38/6/6) | 0.730 (28/17/5) | 0.790 (35/9/6) | **0.830** (38/7/5) | 0.775 | 0.800 (37/6/7) | 0.750 (31/13/6) | 0.760 (32/12/6) | **0.830** (38/7/5) | 0.770 |
| **Vector k=10** | 0.920 (44/4/2) | 0.840 (36/12/2) | 0.890 (41/7/2) | **0.930** (45/3/2) | 0.842 | 0.900 (43/4/3) | 0.830 (36/11/3) | 0.880 (41/6/3) | **0.900** (43/4/3) | 0.810 |
| **Vector-line k=5** | 0.770 (33/11/6) | 0.740 (30/14/6) | 0.800 (35/10/5) | **0.840** (38/8/4) | 0.787 | 0.790 (34/11/5) | 0.730 (28/17/5) | 0.780 (33/12/5) | **0.850** (37/11/2) | 0.755 |
| **Vector-line k=10** | 0.850 (38/9/3) | 0.810 (33/15/2) | 0.890 (41/7/2) | **0.950** (45/5/0) | 0.844 | 0.860 (41/4/5) | 0.790 (33/13/4) | 0.850 (38/9/3) | **0.900** (42/6/2) | 0.795 |
| **V-hybrid k=5** | 0.870 (39/9/2) | 0.820 (34/14/2) | 0.880 (40/8/2) | **0.950** (46/3/1) | 0.846 | 0.890 (42/5/3) | 0.800 (34/12/4) | 0.840 (38/8/4) | **0.900** (42/6/2) | 0.803 |
| **V-hybrid k=10** | 0.930 (44/5/1) | 0.850 (36/13/1) | 0.900 (41/8/1) | **0.950** (46/3/1) | 0.867 | 0.900 (43/4/3) | 0.810 (35/11/4) | 0.860 (39/8/3) | **0.910** (43/5/2) | 0.804 |
| **Hybrid k=5** | 0.880 (40/8/2) | 0.840 (35/14/1) | 0.860 (38/10/2) | **0.950** (45/5/0) | 0.847 | 0.930 (45/3/2) | 0.850 (36/13/1) | 0.910 (42/7/1) | **0.930** (44/5/1) | 0.829 |
| **Hybrid k=8** | 0.920 (44/4/2) | 0.870 (39/9/2) | 0.910 (43/5/2) | **0.930** (45/3/2) | 0.839 | 0.920 (43/6/1) | 0.810 (32/17/1) | 0.910 (42/7/1) | **0.960** (47/2/1) | 0.839 |
| **Hybrid k=10** | 0.980 (48/2/0) | 0.890 (39/11/0) | 0.930 (43/7/0) | **0.980** (48/2/0) | 0.881 | 0.910 (42/7/1) | 0.860 (37/12/1) | 0.890 (40/9/1) | **0.960** (47/2/1) | 0.837 |
| **Extract** | 0.860 (40/6/4) | 0.810 (35/11/4) | 0.850 (39/7/4) | **0.910** (44/3/3) | 0.824 | 0.870 (41/5/4) | 0.770 (31/15/4) | 0.830 (36/11/3) | **0.910** (43/5/2) | 0.800 |
| **Filter2** | 0.800 (37/6/7) | 0.780 (34/10/6) | 0.800 (36/8/6) | **0.840** (40/4/6) | 0.767 | 0.820 (38/6/6) | 0.740 (30/14/6) | 0.800 (36/8/6) | **0.870** (42/3/5) | 0.763 |
| **Filter3** | 0.930 (45/3/2) | 0.890 (41/7/2) | 0.920 (44/4/2) | **0.930** (45/3/2) | 0.853 | 0.870 (41/5/4) | 0.830 (37/9/4) | 0.900 (43/4/3) | **0.930** (45/3/2) | 0.820 |
| **Ceiling** | 0.990 (49/1/0) | 0.960 (46/4/0) | 0.960 (46/4/0) | **0.960** (46/4/0) | 0.869 | 0.990 (49/1/0) | 0.880 (38/12/0) | 0.950 (45/5/0) | **0.980** (48/2/0) | 0.852 |
| **GraphRAG local** | 0.610 (24/13/13) | 0.570 (19/19/12) | 0.610 (22/17/11) | **0.720** (32/8/10) | 0.672 | 0.630 (26/11/13) | 0.550 (20/15/15) | 0.610 (22/17/11) | **0.680** (28/12/10) | 0.662 |
| **GraphRAG global** | 0.170 (3/11/36) | 0.130 (1/11/38) | 0.140 (1/12/37) | **0.240** (7/10/33) | 0.329 | 0.190 (6/7/37) | 0.220 (3/16/31) | 0.210 (3/15/32) | **0.450** (17/11/22) | 0.443 |

*Cells read `weighted (correct / partial / incorrect)`. `E` is the probability
expectation of Clef Flash. Jev is the current `jev-1.14.0`; the Qwen and
Nimble columns are those of [NIMBLE.md](NIMBLE.md).*

---

## Analysis

### 1. The Most Lenient of the Four

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Clef Flash** | **1,216 (81.1%)** | **155 (10.3%)** | **129 (8.6%)** | **0.861 / 0.864** |
| Qwen 3.6 | 1,137 (75.8%) | 183 (12.2%) | 180 (12.0%) | 0.820 / 0.818 |
| Nimble | 1,075 (71.7%) | 261 (17.4%) | 164 (10.9%) | 0.809 / 0.799 |
| Jev | 947 (63.1%) | 381 (25.4%) | 172 (11.5%) | 0.769 / 0.748 |

Clef Flash gives more *correct* and fewer *partial* and *incorrect* verdicts
than any other judge, including Qwen. It scores 28 of the 30 method × language
cells at or above Qwen (all but Ceiling), and ties or tops Jev and Nimble in
every cell. The
weighted score rises most where the answers are weakest: GraphRAG local
(+0.11 en / +0.07 ja over Nimble) and GraphRAG global (+0.10 en / +0.24 ja).

### 2. Agreement

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **Qwen vs Clef**: **88.3%** (1,325 / 1,500): *en 87.3%, ja 89.3%*
- **Nimble vs Clef**: **86.5%** (1,297 / 1,500): *en 87.3%, ja 85.6%*
- **Jev vs Clef**: **78.3%** (1,174 / 1,500): *en 79.7%, ja 76.8%*

For reference, Qwen vs Nimble is 89.8%, Jev vs Nimble 86.9% and Qwen vs Jev
85.3%. Clef Flash agrees most with Qwen, and its agreement with Jev is the
lowest of any pair.

#### Combined Confusion Matrices (1,500 Questions)

```
Qwen \ Clef:
              correct   partial   incorrect
correct          1106        30           1
partial            92        91           0
incorrect          18        34         128

Nimble \ Clef:
              correct   partial   incorrect
correct          1054        21           0
partial           145       115           1
incorrect          17        19         128

Jev \ Clef:
              correct   partial   incorrect
correct           932        15           0
partial           268       113           0
incorrect          16        27         129
```

Against Nimble, the main shift is Nimble *partial* → Clef *correct* (145, vs.
21 the other way). Clef Flash accepts a multi-part answer that misses part of
the gold answer as *correct* where Nimble, its sibling on the same base model,
marks it *partial*.

### 3. "No Answer" Graded Correct

Unlike the other three judges, Clef Flash does not reliably treat a refusal as
*incorrect*, although the rubric names that case explicitly ("says no answer
was found"). GraphRAG global answers 60 questions (34 en, 26 ja) with the same
fixed sentence, *"I am sorry but I am unable to answer this question given the
provided data."*:

| Judge | en (34) | ja (26) | Mean P(correct) (en / ja) |
| :--- | :--- | :--- | :---: |
| Qwen | 33 incorrect, 1 correct | 26 incorrect | — |
| Jev | 34 incorrect | 26 incorrect | 0.00 / 0.00 |
| Nimble | 34 incorrect | 26 incorrect | 0.00 / 0.00 |
| **Clef Flash** | **31 incorrect, 3 correct** | **19 incorrect, 7 correct** | **0.16 / 0.29** |

The 7 Japanese refusals graded *correct* account for most of Japanese GraphRAG
global's 0.450. More broadly, 16 of the 18 answers that Qwen grades *incorrect*
and Clef Flash *correct* say that the information is not in the context
(the fixed sentence above, or variants such as "The provided text does not
mention a signet ring"); one of the remaining two is a plain factual error
("the entire night" for the gold "Five days", Hybrid k=5 Q17). These verdicts
are rarely confident (P(correct) 0.39–0.80), but they are the most probable
verdict, so they count.

### 4. Less Decisive Probabilities

Clef Flash spreads its probability more than Nimble: the most probable verdict
gets 0.777 on average (median 0.818), against Nimble's 0.942 (median 0.998), and
it falls below 0.6 on 181 questions against Nimble's 46. As a result its **E**
sits below its weighted score on every method but one (Ceiling en 0.869 vs.
0.960). The exception is English GraphRAG global (0.329 vs. 0.240), where most
answers are refusals and each still carries some probability of *correct*.

### 5. Language Consistency

- **Ceiling**: en 0.960 vs ja 0.980.
- **Average delta**: ja − en averages **+0.003** over the 15 methods, with
  Japanese lower in 7 of them. Without GraphRAG global (+0.21, see above),
  the average is **−0.011**, about the same as Nimble (−0.010) and smaller than
  Jev (−0.021).
- **Method rankings**: Hybrid k=10 leads in English (0.980) and Hybrid k=8 / k=10
  in Japanese (0.960). GraphRAG aside, the methods span 0.15 in each language
  (0.830–0.980), narrower than under Qwen (0.22 / 0.20) and Nimble
  (0.17 / 0.19).

---

## Conclusion

Clef Flash runs the same way as Nimble (local, free, ~0.6 s per decision) and
is a drop-in judge through the shared [ollama_systemone.py](../ollama_systemone.py),
but its verdicts are the most lenient of the four judges compared here:

1. **Lenient on omissions**: multi-part answers that Nimble and Jev mark
   *partial* are mostly *correct*, so scores approach or exceed Qwen's.
2. **Refusals are not always incorrect**: it grades some "cannot answer"
   replies *correct*, against an explicit rule of the rubric, which inflates the
   weakest methods (GraphRAG) the most.
3. **Less decisive**: its probabilities are spread more than Nimble's, so the
   expectation E and the weighted score diverge.

For this evaluation, Nimble remains the better local judge; Clef Flash's
verdicts are kept in `clef-flash/` for comparison. The larger Clef is compared
in [CLEF.md](CLEF.md).
