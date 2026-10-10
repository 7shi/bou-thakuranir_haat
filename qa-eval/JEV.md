# Re-grading with Jev

Every answer file in `results-en/` and `results-ja/` (15 methods × 50 questions
per language) was re-graded with TypeSafe's Jev and compared with the existing
`ollama:qwen3.6` verdicts. The qwen results and the analyses built on them
([README.md](README.md) and the linked documents) are left as they are; this
document records how the picture shifts under the stricter judge. Why Jev and
why a single Choice question: [jev/README.md](jev/README.md).

## Setup

- Judge: [judge-jev.py](judge-jev.py), `jev-1.13.0`, scheme `choice@19579e23`
  (both recorded per file in `results-<lang>/jev/MODELS.tsv`). Same inputs as
  `judge.py` — question, gold answer, rationale, candidate answer; no source
  text.
- Output: `results-<lang>/jev/<method>.tsv`, the probabilities of correct /
  partial / incorrect plus Jev's confidence.
- Aggregation: `uv run report.py -l <lang> --jev`. Each question counts as its
  most probable verdict, the stricter one on a tie (three ties: en Extract Q41
  and ja Vector k=10 Q27, both 0.5/0.5 correct/partial → partial, and ja
  Filter3 Q32, 0.5/0.5 partial/incorrect → incorrect).
- **Weighted** = (correct + 0.5·partial) / 50 as before. **E** = the mean of
  P(correct) + 0.5·P(partial), the same score taken over the probabilities
  instead of the verdicts.

## Cost

One `judge-jev.py` call per language (15 files × 50 questions = 750
requests each); token counts from llm7shi's `usage.jsonl`:

| Language | Requests | Input | Output | Input / request | Output / request |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 750 | 516,082 | 29,250 | 688 | 39 |
| Japanese | 750 | 676,351 | 29,250 | 902 | 39 |
| Total | 1,500 | 1,192,433 | 58,500 | 795 | 39 |

Billed $0.0501 in total, about $0.033 per 1,000 requests, in line with the
per-model runs in [results/JEV.md](results/JEV.md).

The Q7 and Q28 rows were graded in a second run: 30 requests per language
(15 files × 2 questions), 21,717 input / 1,170 output tokens for English and
27,559 / 1,170 for Japanese, about $0.002 at the same rate.

Wall time, estimated from the creation time of `results-<lang>/jev/` (made just
before the first request) to the last write in it (the final row of
`vector5.tsv`, matching the `usage.jsonl` timestamp):

| Language | Start | End | Elapsed | Per request |
| --- | --- | --- | ---: | ---: |
| English | 14:20:25 | 14:23:11 | 2m 46s | 0.22 s |
| Japanese | 14:25:16 | 14:28:07 | 2m 51s | 0.23 s |

About 5m 37s for both languages, excluding the gap between the two runs and
the few seconds of start-up before the directory is created.

## Results

| Method | en qwen | en Jev | en Δ | en E | ja qwen | ja Jev | ja Δ | ja E |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: |
| Vector k=5 | 0.820 (38/6/6) | 0.720 (28/16/6) | −0.100 | 0.729 | 0.800 (37/6/7) | 0.760 (32/12/6) | −0.040 | 0.737 |
| Vector k=10 | 0.920 (44/4/2) | 0.840 (36/12/2) | −0.080 | 0.824 | 0.900 (43/4/3) | 0.820 (37/8/5) | −0.080 | 0.818 |
| Vector-line k=5 | 0.770 (33/11/6) | 0.750 (30/15/5) | −0.020 | 0.738 | 0.790 (34/11/5) | 0.750 (30/15/5) | −0.040 | 0.738 |
| Vector-line k=10 | 0.850 (38/9/3) | 0.800 (32/16/2) | −0.050 | 0.797 | 0.860 (41/4/5) | 0.790 (33/13/4) | −0.070 | 0.785 |
| V-hybrid k=5 | 0.870 (39/9/2) | 0.820 (34/14/2) | −0.050 | 0.814 | 0.890 (42/5/3) | 0.800 (34/12/4) | −0.090 | 0.806 |
| V-hybrid k=10 | 0.930 (44/5/1) | 0.860 (37/12/1) | −0.070 | 0.850 | 0.900 (43/4/3) | 0.810 (35/11/4) | −0.090 | 0.807 |
| Hybrid k=5 | 0.880 (40/8/2) | 0.840 (35/14/1) | −0.040 | 0.819 | 0.930 (45/3/2) | 0.840 (35/14/1) | −0.090 | 0.836 |
| Hybrid k=8 | 0.920 (44/4/2) | 0.840 (36/12/2) | −0.080 | 0.833 | 0.920 (43/6/1) | 0.830 (34/15/1) | −0.090 | 0.840 |
| Hybrid k=10 | 0.980 (48/2/0) | 0.900 (40/10/0) | −0.080 | 0.880 | 0.910 (42/7/1) | 0.860 (37/12/1) | −0.050 | 0.838 |
| Extract | 0.860 (40/6/4) | 0.780 (32/14/4) | −0.080 | 0.791 | 0.870 (41/5/4) | 0.770 (30/17/3) | −0.100 | 0.767 |
| Filter2 | 0.800 (37/6/7) | 0.770 (33/11/6) | −0.030 | 0.752 | 0.820 (38/6/6) | 0.740 (30/14/6) | −0.080 | 0.736 |
| Filter3 | 0.930 (45/3/2) | 0.880 (40/8/2) | −0.050 | 0.866 | 0.870 (41/5/4) | 0.840 (39/6/5) | −0.030 | 0.820 |
| Ceiling | 0.990 (49/1/0) | 0.930 (43/7/0) | −0.060 | 0.914 | 0.990 (49/1/0) | 0.900 (40/10/0) | −0.090 | 0.879 |
| GraphRAG local | 0.610 (24/13/13) | 0.550 (17/21/12) | −0.060 | 0.553 | 0.630 (26/11/13) | 0.560 (21/14/15) | −0.070 | 0.551 |
| GraphRAG global | 0.170 (3/11/36) | 0.130 (1/11/38) | −0.040 | 0.126 | 0.190 (6/7/37) | 0.210 (3/15/32) | +0.020 | 0.199 |

Cells read `weighted (correct/partial/incorrect)`.

### Uniformly stricter, almost only correct → partial

Every method but one scores lower under Jev, by 0.02–0.10; only Japanese
GraphRAG global scores higher, by 0.02. Verdict agreement is
650/750 (en) and 621/750 (ja), and the disagreements run one way:

| qwen \ Jev (en) | correct | partial | incorrect |
| --- | ---: | ---: | ---: |
| correct | 474 | 91 | 1 |
| partial | 0 | 96 | 2 |
| incorrect | 0 | 6 | 80 |

| qwen \ Jev (ja) | correct | partial | incorrect |
| --- | ---: | ---: | ---: |
| correct | 466 | 105 | 0 |
| partial | 4 | 72 | 9 |
| incorrect | 0 | 11 | 83 |

The few cases where Jev is more lenient are mostly qwen *incorrect* → Jev
*partial* with P(partial) 0.51–0.99, plus four *partial* → *correct* in
Japanese, all near the boundary (P(correct) 0.51–0.58). The incorrect column
barely moves: Jev and qwen agree on what is wrong and differ on what is
complete.

### The loss is in cross questions

Single-passage questions score essentially the same under both judges
(0.94–1.00 for every non-GraphRAG method). The whole drop is in cross
questions, e.g. en Hybrid k=10 cross 0.96 → 0.80, ja Hybrid k=5 cross
0.86 → 0.68. The questions downgraded most often across the 15 methods are
multi-part cross questions whose answers omit a component of the gold answer:
en Q46 (12 methods), Q47 (9), Q30, Q36 (8 each); ja Q41 (12), Q47, Q48, Q49
(10 each).

### Ceiling is no longer near-perfect

| | qwen | Jev | Jev non-correct |
| --- | --- | --- | --- |
| en | 0.990 | 0.930 | Q26, Q34, Q39, Q42, Q46, Q47, Q48 — all cross |
| ja | 0.990 | 0.900 | Q29, Q32, Q34, Q36, Q37, Q41, Q46, Q47, Q48, Q49 — all cross |

Under qwen the Ceiling run supports "given the right chapters, comprehension is
near-perfect". Under Jev that holds for single questions, but even with every
gold chapter in context the answerer drops components of multi-part cross
answers, noticeably more often in Japanese. Retrieval is still the larger
lever (Ceiling still leads every retrieval method), but synthesis
completeness on cross questions is not negligible.

### The practical ranking tightens

| | qwen best | Jev best | E best |
| --- | --- | --- | --- |
| en | Hybrid k=10 0.980, Filter3 / V-hybrid k=10 0.930 | Hybrid k=10 0.900, Filter3 0.880 | Hybrid k=10 0.880, Filter3 0.866 |
| ja | Hybrid k=5 0.930, Hybrid k=8 0.920 | Hybrid k=10 0.860, Hybrid k=5 = Filter3 0.840 | Hybrid k=8 0.840, Hybrid k=10 0.838 |

Under Jev the top of the table is within one question (0.02) in both
languages: Hybrid k=10 leads Filter3 in English by one question (E 0.880 vs
0.866), and leads Hybrid k=5 and Filter3 in Japanese by one, while by E the
three Hybrid depths are within 0.004 of each other (Filter3 0.820). Hybrid
stays on top in both languages, but its best depth in Japanese depends on the
judge (k=5 under qwen, k=10 under Jev, k=8 by E). Since Filter3 pays an LLM
call per chapter per question ([FILTER.md](FILTER.md)), Dense ∪ BM25 Hybrid
remains the practical choice.

### The language gap widens slightly

Under qwen the two languages trade places (Japanese is higher for 8 of the 15
methods) and average out to nearly the same score (−0.002). Under Jev, Japanese
is lower for 10 of the 15 methods, by 0.01 on average (half a question) and by
0.05 at most (V-hybrid k=10, 0.860 vs 0.810); Vector-line k=5 and Hybrid k=5
are level, and Vector k=5 and both GraphRAG modes are higher in Japanese. The shift is small, and whether it comes from the answerer or from
Jev reading Japanese answers against English instructions is not separated
here: the Jev experiment ([jev/README.md](jev/README.md)) validated English
only.

## Caveat: extra facts beyond the gold answer

Jev, like qwen, sees only the gold answer and its rationale, not the source.
It treats an answer that adds a fact the gold answer lacks as incomplete or
distorted, even when the fact is true, so where a question admits such an
addition the rationale has to say so. Q7 (what the thief asks for after the
burglary) is such a question:

- Gold: 「タバコ一服。」 (a pipeful of tobacco).
- The source continues: after smoking, the thief also asks for the lamp to be
  lit (「タバコを吸い終えた泥棒は言いました。『旦那様、もし明かりを点けていただけると
  助かるのですが。」).
- The rationale adds that this later request is not something to be given, so
  mentioning it alongside the tobacco is not wrong.
- 12 of the 15 Japanese answers mention the lamp. All 15 are *correct*, the 12
  with P(correct) 0.77–1.00.

Q28's rationale likewise states that the king's room in the Chandradwip palace
is the place of the second incident and that Ramai is undisguised there, so
answers that say so are not read as contradicting the gold. The rationale is
where the tolerance of a question is set; without it, a partial on a question
like this would be a gold-coverage issue, not an answerer error.
