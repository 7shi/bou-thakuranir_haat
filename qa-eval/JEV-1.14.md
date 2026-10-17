# Jev 1.14.0

`jev-1.14.0` replaced `jev-1.13.0` as the default model of
[judge-jev.py](judge-jev.py). Every answer file already graded by 1.13.0 was
graded again with the same scheme (`choice@19579e23`), so the two versions
differ only in the model. The 1.13.0 verdicts are kept frozen in
`jev-1.13.0/` beside each `jev/` (`results-en/`, `results-ja/`, `results/`),
and the last `results/report-jev.md` they produced is kept as
[results/jev-1.13.0/report-jev.md](results/jev-1.13.0/report-jev.md).
`uv run report.py -l <lang> --tsv-dir jev-1.13.0` aggregates the archive.
The procedure and the reasons for this layout are in
[jev/MIGRATION.md](jev/MIGRATION.md).

## Run

| Set | Files | Requests | Input | Output | Input / request | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `results-en/` | 15 | 750 | 525,307 | 29,250 | 700 | 2m 28s |
| `results-ja/` | 15 | 750 | 692,671 | 29,250 | 924 | 2m 14s |
| `results/` en | 60 | 3,000 | 2,101,235 | 117,000 | 700 | 17m 55s (both) |
| `results/` ja | 60 | 3,000 | 2,817,749 | 117,000 | 939 | |
| Total | 150 | 7,500 | 6,136,962 | 292,500 | 818 | 22m 36s |

Billed $0.2578 in total; only input is billed, at $0.042 per million tokens
(about $0.034 per 1,000 requests). The inputs are byte-identical to the
1.13.0 runs, yet input tokens per request are about 2% higher (688 → 700 in
English, 902 → 924 in Japanese; see [JEV.md](JEV.md#cost)).

## Agreement with 1.13.0

| Set | Agreement | 1.13 correct → 1.14 partial | 1.13 partial → 1.14 correct | Other changes | Mean confidence |
| --- | ---: | ---: | ---: | ---: | --- |
| `results-en/` | 728/750 (97.1%) | 3 | 15 | 4 | 0.845 → 0.812 |
| `results-ja/` | 724/750 (96.5%) | 15 | 6 | 5 | 0.823 → 0.788 |
| `results/` en | 2,881/3,000 (96.0%) | 47 | 67 | 5 | |
| `results/` ja | 2,849/3,000 (95.0%) | 70 | 74 | 7 | |

"Other changes" are moves to or from *incorrect*, all between *partial* and
*incorrect*; no verdict moves between *correct* and *incorrect*. The mean
confidence is lower under 1.14.0 in every set (`results/` as a whole: 0.808 →
0.771).

- **Not uniformly stricter or more lenient.** Almost every change is a
  *correct* ↔ *partial* flip near the boundary, in both directions. On
  `results-en/` 1.14.0 is more lenient (15 upgrades against 3 downgrades), on
  `results-ja/` stricter (6 against 15); on the 120 `results/` files the two
  directions roughly cancel in both languages.
- **The incorrect column barely moves**, as between qwen and 1.13.0
  ([JEV.md](JEV.md#uniformly-stricter-almost-only-correct--partial)): the
  versions agree on what is wrong and differ on what is complete.

## Methods (`results-<lang>/`)

| Method | en 1.13 | en 1.14 | en Δ | ja 1.13 | ja 1.14 | ja Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vector k=5 | 0.720 | 0.730 | +0.010 | 0.760 | 0.750 | −0.010 |
| Vector k=10 | 0.840 | 0.840 | 0 | 0.820 | 0.830 | +0.010 |
| Vector-line k=5 | 0.750 | 0.740 | −0.010 | 0.750 | 0.730 | −0.020 |
| Vector-line k=10 | 0.800 | 0.810 | +0.010 | 0.790 | 0.790 | 0 |
| V-hybrid k=5 | 0.820 | 0.820 | 0 | 0.800 | 0.800 | 0 |
| V-hybrid k=10 | 0.860 | 0.850 | −0.010 | 0.810 | 0.810 | 0 |
| Hybrid k=5 | 0.840 | 0.840 | 0 | 0.840 | 0.850 | +0.010 |
| Hybrid k=8 | 0.840 | 0.870 | +0.030 | 0.830 | 0.810 | −0.020 |
| Hybrid k=10 | 0.900 | 0.890 | −0.010 | 0.860 | 0.860 | 0 |
| Extract | 0.780 | 0.810 | +0.030 | 0.770 | 0.770 | 0 |
| Filter2 | 0.770 | 0.780 | +0.010 | 0.740 | 0.740 | 0 |
| Filter3 | 0.880 | 0.890 | +0.010 | 0.840 | 0.830 | −0.010 |
| Ceiling | 0.930 | 0.960 | +0.030 | 0.900 | 0.880 | −0.020 |
| GraphRAG local | 0.550 | 0.570 | +0.020 | 0.560 | 0.550 | −0.010 |
| GraphRAG global | 0.130 | 0.130 | 0 | 0.210 | 0.220 | +0.010 |

Weighted scores, (correct + 0.5·partial) / 50. Every change is within ±0.03
(one or two questions). The English top is now a tie between Hybrid k=10 and
Filter3 (0.890), and Hybrid k=10 still leads Japanese (0.860); the practical
conclusion of [JEV.md](JEV.md#the-practical-ranking-tightens) is unchanged.
Since English mostly gains and Japanese mostly loses, the language gap widens
slightly: Ceiling 0.960 vs 0.880.

## Answerer models (`results/`)

Per-model scores move by −4 to +5 points, within the one-or-two-question noise
noted in [results/README.md](results/README.md#ceiling-comparing-answerer-models),
and the mean change is about zero (+0.25 points in English, +0.05 in
Japanese). The current table is in [results/README.md](results/README.md); the
per-model diff is that of `report-jev.md` against
[results/jev-1.13.0/report-jev.md](results/jev-1.13.0/report-jev.md).
