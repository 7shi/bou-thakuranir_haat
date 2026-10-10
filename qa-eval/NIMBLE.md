# Re-grading with Nimble

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language = 1,500 requests in total) was re-graded with Bespoke Labs'
**[Nimble](https://ollama.com/library/nimble)** (hosted locally via Ollama) and
compared with the existing **`ollama:qwen3.6`** verdicts and TypeSafe's **Jev**
(`jev-1.13.0`). For the multi-model comparison across 40 models in `results/`,
see [results/NIMBLE.md](results/NIMBLE.md).

Why Nimble and System One decision models: see
[systemone_overview.md](~/.gemini/antigravity-cli/brain/849cad52-8525-48f2-b302-77d6403bb0f2/systemone_overview.md),
[jev/README.md](jev/README.md), and the official model page at
[ollama.com/library/nimble](https://ollama.com/library/nimble).

## Setup

- **Model**: [Nimble](https://ollama.com/library/nimble) (`nimble` / `nimble:9b`),
  a 9B open-weights decision model from Bespoke Labs fine-tuned from Qwen 3.5 9B
  (Apache 2.0, 256K context window). Supported in Ollama 0.35+ via the
  `/v1/systemone` endpoint (following TypeSafe's Jev API).
- **Judge**: [judge-nimble.py](judge-nimble.py), model `nimble` via Ollama,
  scheme `choice@19579e23` (identical rubric and scheme ID as Jev, recorded
  in `results-<lang>/nimble/MODELS.tsv`).
- **Inputs**: Same contract as `judge.py` and `judge-jev.py` — question, gold
  answer, rationale, candidate answer; **no** chapter source text.
- **Output**: `results-<lang>/nimble/<method>.tsv`, holding the probabilities of
  `correct` / `partial` / `incorrect` and Nimble's confidence.
- **Aggregation**: Each question counts as its most probable verdict, with ties
  broken to the stricter verdict.
  - **Weighted** = `(correct + 0.5 · partial) / 50`
  - **E** = mean of `P(correct) + 0.5 · P(partial)` (continuous expectation
    over the output probabilities)

## Performance & Cost

Nimble is an open-weights System One decision model (fine-tuned on Qwen 3.5 9B)
running locally in Ollama. Unlike traditional autoregressive LLMs (Qwen 3.6)
that generate prose justifications before a structured verdict, Nimble reads the
prompt once and scores answer tokens directly in a single forward pass without
a separate reasoning generation step. Unlike Jev, it runs on local hardware at
**zero API cost**.

| Metric | Qwen 3.6 (`judge.py`) | Jev (`judge-jev.py`) | Nimble (`judge-nimble.py`) |
| :--- | :--- | :--- | :--- |
| **Hosting** | Local (Ollama) | Cloud API (TypeSafe) | **Local (Ollama)** |
| **Architecture** | Autoregressive (System 2) | System One (Decision Model) | **System One (Qwen 3.5 9B LoRA)** |
| **API Cost** | **$0.00** (Local) | $0.0501 / 1,500 req (paid) | **$0.00 (Local / Free)** |
| **Wall Time (en, 750 req)** | ~10–15 min (estimated) | 2m 46s | **7m 46s** (0.62 s / req) |
| **Wall Time (ja, 750 req)** | ~10–15 min (estimated) | 2m 51s | **8m 10s** (0.65 s / req) |
| **Total Wall Time (1,500 req)**| ~20–30 min | 5m 37s | **15m 56s** (0.64 s / req) |
| **Input Tokens (en / ja)** | ~500k / ~600k | 516k / 676k (795 / req avg) | **380k / 417k (531.4 / req avg)** |
| **Output Tokens (total)** | ~60k–100k (reason + JSON) | 58,500 (39 / req) | **1,500 (strictly 1.0 / req)** |

Because Nimble produces its verdict in a single pass without token-by-token text
generation, its output is strictly 1 token per question, eliminating decoding
overhead and KV-cache expansion. (A larger 4,100-request evaluation across 40
models was similarly completed in 46m 24s; see [results/NIMBLE.md](results/NIMBLE.md)).

---

## Results

### Summary Table (All 15 Methods)

| Method | en Qwen | en Jev | en Nimble | en E | ja Qwen | ja Jev | ja Nimble | ja E |
| :--- | :---: | :---: | :---: | ---: | :---: | :---: | :---: | ---: |
| **Vector k=5** | 0.820 (38/6/6) | 0.720 (28/16/6) | **0.790** (35/9/6) | 0.779 | 0.800 (37/6/7) | 0.760 (32/12/6) | **0.760** (32/12/6) | 0.767 |
| **Vector k=10** | 0.920 (44/4/2) | 0.840 (36/12/2) | **0.890** (41/7/2) | 0.889 | 0.900 (43/4/3) | 0.820 (37/8/5) | **0.880** (41/6/3) | 0.868 |
| **Vector-line k=5** | 0.770 (33/11/6) | 0.750 (30/15/5) | **0.800** (35/10/5) | 0.787 | 0.790 (34/11/5) | 0.750 (30/15/5) | **0.780** (33/12/5) | 0.784 |
| **Vector-line k=10** | 0.850 (38/9/3) | 0.800 (32/16/2) | **0.890** (41/7/2) | 0.877 | 0.860 (41/4/5) | 0.790 (33/13/4) | **0.850** (38/9/3) | 0.838 |
| **V-hybrid k=5** | 0.870 (39/9/2) | 0.820 (34/14/2) | **0.880** (40/8/2) | 0.864 | 0.890 (42/5/3) | 0.800 (34/12/4) | **0.840** (38/8/4) | 0.836 |
| **V-hybrid k=10** | 0.930 (44/5/1) | 0.860 (37/12/1) | **0.900** (41/8/1) | 0.891 | 0.900 (43/4/3) | 0.810 (35/11/4) | **0.860** (39/8/3) | 0.861 |
| **Hybrid k=5** | 0.880 (40/8/2) | 0.840 (35/14/1) | **0.860** (38/10/2) | 0.864 | 0.930 (45/3/2) | 0.840 (35/14/1) | **0.910** (42/7/1) | 0.884 |
| **Hybrid k=8** | 0.920 (44/4/2) | 0.840 (36/12/2) | **0.910** (43/5/2) | 0.903 | 0.920 (43/6/1) | 0.830 (34/15/1) | **0.910** (42/7/1) | 0.901 |
| **Hybrid k=10** | 0.980 (48/2/0) | 0.900 (40/10/0) | **0.930** (43/7/0) | 0.921 | 0.910 (42/7/1) | 0.860 (37/12/1) | **0.890** (40/9/1) | 0.888 |
| **Extract** | 0.860 (40/6/4) | 0.780 (32/14/4) | **0.850** (39/7/4) | 0.835 | 0.870 (41/5/4) | 0.770 (30/17/3) | **0.830** (36/11/3) | 0.809 |
| **Filter2** | 0.800 (37/6/7) | 0.770 (33/11/6) | **0.800** (36/8/6) | 0.801 | 0.820 (38/6/6) | 0.740 (30/14/6) | **0.800** (36/8/6) | 0.800 |
| **Filter3** | 0.930 (45/3/2) | 0.880 (40/8/2) | **0.920** (44/4/2) | 0.918 | 0.870 (41/5/4) | 0.840 (39/6/5) | **0.900** (43/4/3) | 0.881 |
| **Ceiling** | 0.990 (49/1/0) | 0.930 (43/7/0) | **0.960** (46/4/0) | 0.956 | 0.990 (49/1/0) | 0.900 (40/10/0) | **0.950** (45/5/0) | 0.948 |
| **GraphRAG local** | 0.610 (24/13/13) | 0.550 (17/21/12) | **0.610** (22/17/11) | 0.616 | 0.630 (26/11/13) | 0.560 (21/14/15) | **0.610** (22/17/11) | 0.612 |
| **GraphRAG global**| 0.170 (3/11/36) | 0.130 (1/11/38) | **0.140** (1/12/37) | 0.147 | 0.190 (6/7/37) | 0.210 (3/15/32) | **0.210** (3/15/32) | 0.219 |

*Cells read `weighted (correct / partial / incorrect)`. `E` is probability expectation.*

---

## Analysis & Insights

### 1. The Strictness Spectrum: Nimble Hits the Sweet Spot

Across both languages (1,500 total judgements), the distribution of verdicts
clearly illustrates the strictness hierarchy:

```mermaid
flowchart LR
    Qwen["Qwen 3.6 (Lenient)<br/>1,137 correct / 183 partial"] --> Nimble["Nimble (Balanced)<br/>1,075 correct / 261 partial"]
    Nimble --> Jev["Jev (Strict)<br/>944 correct / 381 partial"]
```

| Judge | Correct | Partial | Incorrect | Mean Weighted (en / ja) |
| :--- | ---: | ---: | ---: | :---: |
| **Qwen 3.6** | 1,137 (75.8%) | 183 (12.2%) | 180 (12.0%) | 0.820 / 0.818 |
| **Nimble** | **1,075 (71.7%)** | **261 (17.4%)** | **164 (10.9%)** | **0.809 / 0.799** |
| **Jev** | 944 (62.9%) | 381 (25.4%) | 175 (11.7%) | 0.761 / 0.752 |

- **Qwen 3.6** is overly lenient, frequently awarding full credit (*correct*) to
  answers that omit supporting details.
- **Jev** is aggressive in penalizing any omitted detail as *partial*, scoring
  every method but one 0.02–0.10 below Qwen (0.059 en / 0.066 ja on average).
- **Nimble** occupies the sweet spot: stricter than Qwen on multi-part omissions
  without Jev's tendency to over-penalize.

### 2. Disagreement & Agreement Rates

Pairwise agreement across all 1,500 questions (750 en + 750 ja):

- **Qwen vs Nimble**: **89.8%** (1,347 / 1,500) — *en: 90.7%, ja: 88.9%*
- **Jev vs Nimble**: **86.4%** (1,296 / 1,500) — *en: 86.1%, ja: 86.7%*
- **Qwen vs Jev**: **84.7%** (1,271 / 1,500) — *en: 86.7%, ja: 82.8%*

Nimble achieves higher agreement with both Qwen and Jev than they achieve with
each other, serving as a robust bridge between the two evaluation regimes.

#### Combined Confusion Matrix (1,500 Questions)

```
Qwen \ Nimble:
              correct   partial   incorrect
correct          1043        93           1
partial            32       146           5
incorrect           0        22         158

Jev \ Nimble:
              correct   partial   incorrect
correct           920        24           0
partial           155       219           7
incorrect           0        18         157
```

### 3. Solid Consensus on Incorrect Answers

All three judges show exceptional agreement on *incorrect* answers:
- Qwen: 180 incorrect
- Jev: 175 incorrect
- Nimble: 164 incorrect

Out of Nimble's 164 *incorrect* verdicts, 158 are shared with Qwen and 157 with
Jev. In all three models, "what is wrong" is essentially unanimous; the only
variation across judges is the boundary between *correct* and *partial*.

### 4. Language Consistency

In Jev, Japanese scores dropped across 10 of 15 methods (average −0.009, with
Ceiling dropping 0.930 → 0.900); whether Jev's reading of Japanese text against
English rubric instructions plays a part is not separated.

In Nimble:
- **Ceiling**: en 0.960 vs ja 0.950 (consistent and non-saturated in both languages).
- **Average delta**: Japanese is lower for 10 of the 15 methods, and the ja − en
  difference averages **−0.010** (half a question).
- **Method rankings**: Hybrid and Filter3 lead in both languages (en Hybrid
  k=10 0.930, Filter3 0.920, Hybrid k=8 0.910; ja Hybrid k=5 and k=8 0.910,
  Filter3 0.900).

Nimble's language gap is as small as Jev's: both grade Japanese answers about
half a question lower on average.

---

## Conclusion

Bespoke Labs' **Nimble** is a highly effective, production-ready local judge:

1. **Zero Cost & Completely Local**: Runs within Ollama (`ollama pull nimble`)
   with zero cloud dependencies or API charges.
2. **Speed & Efficiency**: ~0.64 s per decision on local GPUs, generating exactly
   1 output token per question without autoregressive text overhead.
3. **Calibrated Judgment**: Balances Qwen's leniency and Jev's strictness,
   producing reliable and discriminative rankings across both English and Japanese.
