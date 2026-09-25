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
  most probable verdict, the stricter one on a tie (one tie: en Extract Q41,
  0.5/0.5 correct/partial → partial).
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
| Vector k=5 | 0.840 (40/4/6) | 0.730 (29/15/6) | −0.110 | 0.744 | 0.810 (38/5/7) | 0.750 (31/13/6) | −0.060 | 0.731 |
| Vector k=10 | 0.930 (45/3/2) | 0.840 (36/12/2) | −0.090 | 0.823 | 0.900 (43/4/3) | 0.810 (35/11/4) | −0.090 | 0.815 |
| Vector-line k=5 | 0.810 (36/9/5) | 0.740 (29/16/5) | −0.070 | 0.740 | 0.800 (36/8/6) | 0.720 (27/18/5) | −0.080 | 0.722 |
| Vector-line k=10 | 0.890 (41/7/2) | 0.800 (32/16/2) | −0.090 | 0.812 | 0.860 (41/4/5) | 0.760 (30/16/4) | −0.100 | 0.771 |
| V-hybrid k=5 | 0.880 (40/8/2) | 0.840 (36/12/2) | −0.040 | 0.821 | 0.890 (42/5/3) | 0.800 (33/14/3) | −0.090 | 0.789 |
| V-hybrid k=10 | 0.910 (43/5/2) | 0.830 (34/15/1) | −0.080 | 0.835 | 0.900 (43/4/3) | 0.810 (34/13/3) | −0.090 | 0.799 |
| Hybrid k=5 | 0.900 (42/6/2) | 0.840 (35/14/1) | −0.060 | 0.828 | 0.930 (45/3/2) | 0.820 (33/16/1) | −0.110 | 0.817 |
| Hybrid k=8 | 0.930 (45/3/2) | 0.860 (38/10/2) | −0.070 | 0.839 | 0.950 (46/3/1) | 0.840 (35/14/1) | −0.110 | 0.835 |
| Hybrid k=10 | 0.960 (47/2/1) | 0.860 (37/12/1) | −0.100 | 0.863 | 0.930 (45/3/2) | 0.830 (34/15/1) | −0.100 | 0.834 |
| Extract | 0.850 (40/5/5) | 0.780 (32/14/4) | −0.070 | 0.779 | 0.860 (41/4/5) | 0.770 (30/17/3) | −0.090 | 0.767 |
| Filter2 | 0.800 (36/8/6) | 0.760 (32/12/6) | −0.040 | 0.736 | 0.850 (41/3/6) | 0.730 (29/15/6) | −0.120 | 0.735 |
| Filter3 | 0.940 (46/2/2) | 0.880 (40/8/2) | −0.060 | 0.864 | 0.890 (43/3/4) | 0.840 (38/8/4) | −0.050 | 0.809 |
| Ceiling | 0.990 (49/1/0) | 0.960 (46/4/0) | −0.030 | 0.916 | 0.980 (48/2/0) | 0.900 (40/10/0) | −0.080 | 0.865 |
| GraphRAG local | 0.660 (28/10/12) | 0.560 (17/22/11) | −0.100 | 0.564 | 0.640 (28/8/14) | 0.540 (19/16/15) | −0.100 | 0.550 |
| GraphRAG global | 0.170 (5/7/38) | 0.130 (1/11/38) | −0.040 | 0.129 | 0.240 (8/8/34) | 0.190 (2/15/33) | −0.050 | 0.195 |

Cells read `weighted (correct/partial/incorrect)`.

### Uniformly stricter, almost only correct → partial

Every method scores lower under Jev, by 0.03–0.12. Verdict agreement is
632/750 (en) and 596/750 (ja), and the disagreements run one way:

| qwen \ Jev (en) | correct | partial | incorrect |
| --- | ---: | ---: | ---: |
| correct | 474 | 108 | 1 |
| partial | 0 | 78 | 2 |
| incorrect | 0 | 7 | 80 |

| qwen \ Jev (ja) | correct | partial | incorrect |
| --- | ---: | ---: | ---: |
| correct | 449 | 139 | 0 |
| partial | 1 | 62 | 4 |
| incorrect | 0 | 10 | 85 |

The few cases where Jev is more lenient are mostly qwen *incorrect* → Jev
*partial* with P(partial) 0.5–0.99, plus one *partial* → *correct* (ja Hybrid
k=8 Q44, P(correct) 0.57). The incorrect column barely moves: Jev and qwen
agree on what is wrong and differ on what is complete.

### The loss is in cross questions

Single-passage questions score essentially the same under both judges
(0.92–1.00 for every non-GraphRAG method). The whole drop is in cross
questions, e.g. en Hybrid k=10 cross 0.96 → 0.76, ja Hybrid k=8 cross
0.90 → 0.70. The questions downgraded most often across the 15 methods are
multi-part cross questions whose answers omit a component of the gold answer:
en Q46 (12 methods), Q42 (11), Q28 (10); ja Q46 (13), Q41, Q28, Q47, Q48 (10
each).

### Ceiling is no longer near-perfect

| | qwen | Jev | Jev non-correct |
| --- | --- | --- | --- |
| en | 0.990 | 0.960 | Q28, Q34, Q42, Q48 — all cross |
| ja | 0.980 | 0.900 | Q7 (single); Q28, Q29, Q34, Q36, Q37, Q41, Q46, Q47, Q48 (cross) |

Under qwen the Ceiling run supports "given the right chapters, comprehension is
near-perfect". Under Jev that holds for single questions, but even with every
gold chapter in context the answerer drops components of multi-part cross
answers, noticeably more often in Japanese. Retrieval is still the larger
lever (Ceiling keeps a clear lead over every retrieval method), but synthesis
completeness on cross questions is not negligible.

### The practical ranking tightens

| | qwen best | Jev best | E best |
| --- | --- | --- | --- |
| en | Hybrid k=10 0.960, Filter3 0.940 | Filter3 0.880, Hybrid k=8/k=10 0.860 | Filter3 0.864, Hybrid k=10 0.863 |
| ja | Hybrid k=8 0.950, Hybrid k=5/k=10 0.930 | Hybrid k=8 0.840 = Filter3 0.840 | Hybrid k=8 0.835, Hybrid k=10 0.834 |

Under Jev the top of the table is within one question (0.02) in both
languages: Hybrid no longer leads Filter3 in English, and ties it in Japanese
by verdicts while leading it by E. Since Filter3 pays an LLM call per chapter
per question ([FILTER.md](FILTER.md)), Dense ∪ BM25 Hybrid remains the
practical choice; the qwen-era claim that it is the single most accurate
method is not supported by Jev in English.

### The language gap widens

Under qwen the two languages trade places (Japanese is higher for 6 of the 15
methods) and average out to the same score. Under Jev, Japanese is lower for 13
of the 15 methods, by 0.02 on average (one question) and by 0.06 at most
(Ceiling, 0.960 vs 0.900); only Vector k=5 and GraphRAG global are higher in
Japanese. The shift is small, and whether it comes from the answerer or from
Jev reading Japanese answers against English instructions is not separated
here: the Jev experiment ([jev/README.md](jev/README.md)) validated English
only.

## Caveat: extra facts beyond the gold answer

Jev, like qwen, sees only the gold answer and its rationale, not the source.
It treats an answer that adds a fact the gold answer lacks as incomplete or
distorted, even when the fact is true. ja Q7 (what the thief asks for after the
burglary) shows it cleanly:

- Gold: 「タバコ一服。」 (a pipeful of tobacco).
- The source continues: after smoking, the thief also asks for the lamp to be
  lit (「タバコを吸い終えた泥棒は言いました。『旦那様、もし明かりを点けていただけると
  助かるのですが。」).
- 12 of the 15 Japanese answers mention the lamp; 11 of them are *partial*
  with P(partial) 0.51–0.93, and graphrag-local stays *correct* (0.84). The 3 that say only tobacco get
  P(correct) 0.94–1.00.

qwen graded them *correct*. Part of Jev's strictness is therefore penalizing
answers that are more complete than the gold answer; a partial on a question
like this is a gold-coverage issue, not an answerer error.
