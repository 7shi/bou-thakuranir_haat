# Choosing the Judge Model

qa-eval has been graded by seven judges. This document compares them side by
side, sets out what kind of grading this evaluation wants, and records the
decision on which judge to use. The per-judge details are in the linked
documents.

| Judge | Model | Hosting | Document |
| :--- | :--- | :--- | :--- |
| Qwen | `ollama:qwen3.6`, reason then verdict ([judge.py](judge.py)) | Local (Ollama) | [README.md](README.md) |
| Jev | TypeSafe `jev-1.14.0` ([judge-jev.py](judge-jev.py)) | Cloud (TypeSafe) | [JEV.md](JEV.md), [JEV-1.14.md](JEV-1.14.md) |
| Nimble | Bespoke Labs `nimble` (Qwen 3.5 9B) | Local (Ollama) | [NIMBLE.md](NIMBLE.md) |
| Clef Flash | Cloudflare `clef-flash` (Qwen 3.5 9B) | Local (Ollama) | [CLEF-FLASH.md](CLEF-FLASH.md) |
| Clef | Cloudflare `clef` (Qwen 3.8 27B) | Local (Ollama) | [CLEF.md](CLEF.md) |
| OpenAI | `gpt-6-luna` via the Decisions API ([judge-openai.py](judge-openai.py)) | Cloud (OpenAI) | [OPENAI.md](OPENAI.md) |
| Ternary | `gpt-6-luna` replying with the verdict word ([judge-ternary.py](judge-ternary.py)) | Cloud (OpenAI) | [TERNARY.md](TERNARY.md) |

All but Qwen return probabilities over `correct` / `partial` / `incorrect`;
each question counts as its most probable verdict, the stricter one on a tie.
Jev, Nimble, Clef Flash and Clef share one scheme (`choice@19579e23`); OpenAI
and Ternary use the same rubric adapted to their APIs.

## The Rubric

```
correct:   The candidate answer captures the essential facts of the gold answer.
partial:   The candidate answer captures some but misses or distorts key facts.
incorrect: The candidate answer is wrong, irrelevant, or says no answer was found.
```

The rubric asks for the **essential** facts. It does not ask an answer to list
every element of the gold answer, so an answer that covers the essentials but
leaves out a secondary detail should be *correct*. What this evaluation wants
from a judge is therefore:

1. **Full marks for good answers**: an answer of sufficient quality gets
   *correct*, without enumerating the gold answer.
2. **No credit for errors**: a factual error or a refusal is never *correct*.
3. **Separation**: the scores still separate the models, rather than saturating
   at 100 the way Qwen does.

## Strictness

Over the 1,500 questions of `results-en/` and `results-ja/` (15 methods × 50
questions × 2 languages), and the mean Ceiling score over the 63 models × 2
languages in `results/`:

| Judge | Correct | Partial | Incorrect | Ceiling mean (126) | 100% in both languages |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Clef Flash | 1,216 (81.1%) | 155 | 129 | 96.3% | 6 models |
| Qwen | 1,137 (75.8%) | 183 | 180 | 94.9% | 13 models |
| Nimble | 1,075 (71.7%) | 261 | 164 | 92.2% | 0 |
| OpenAI | 1,000 (66.7%) | 346 | 154 | 89.6% | 1 model |
| Ternary | 968 (64.5%) | 343 | 189 | 88.2% | 0 |
| Jev | 947 (63.1%) | 381 | 172 | 87.8% | 0 |
| Clef | 914 (60.9%) | 423 | 163 | 85.4% | 0 |

The *incorrect* counts are similar (129–189); the judges differ mainly in where
they draw the line between *correct* and *partial*. The three cloud judges
(OpenAI, Ternary, Jev) cluster on the strict side, Nimble sits between them and
Qwen, and Clef Flash and Clef sit beyond the two ends.

## Closeness to Qwen and to Jev

Four measures of closeness to a base judge: verdict agreement on the 1,500
questions of `results-<lang>/` and on the 6,600 questions of `results/` (63
models' Ceiling plus the Hybrid8 runs), and Pearson's $r$ and the mean
absolute difference of the 126 Ceiling scores (the signed mean difference in
parentheses; negative is stricter than the base). The overall rank averages the
four ranks.

### Qwen as the base

| Rank | Judge | Agreement (methods) | Agreement (models) | $r$ | \|diff\| (diff) |
| :---: | :--- | ---: | ---: | ---: | :---: |
| 1 | Nimble | 89.8% | 90.2% | 0.959 | 3.2 (−2.7) |
| 2 | Clef Flash | 88.3% | 92.5% | 0.932 | 2.5 (+1.5) |
| 3 | OpenAI | 86.3% | 87.1% | 0.916 | 5.5 (−5.3) |
| 4 | Ternary | 84.3% | 85.8% | 0.934 | 6.7 (−6.6) |
| 5 | Jev | 85.3% | 84.7% | 0.929 | 7.2 (−7.1) |
| 6 | Clef | 81.3% | 79.0% | 0.850 | 9.6 (−9.5) |

### Jev as the base

| Rank | Judge | Agreement (methods) | Agreement (models) | $r$ | \|diff\| (diff) |
| :---: | :--- | ---: | ---: | ---: | :---: |
| 1 | Ternary | 89.3% | 89.2% | 0.965 | 2.2 (+0.5) |
| 2 | OpenAI | 89.1% | 89.7% | 0.960 | 2.4 (+1.8) |
| 3 | Clef | 87.1% | 84.5% | 0.915 | 3.3 (−2.4) |
| 4 | Nimble | 86.9% | 86.5% | 0.911 | 4.6 (+4.5) |
| 5 | Qwen | 85.3% | 84.7% | 0.929 | 7.2 (+7.1) |
| 6 | Clef Flash | 78.3% | 80.5% | 0.859 | 8.6 (+8.6) |

- Jev, OpenAI and Ternary agree closely with one another ($r$ 0.96–0.97), so
  the strict cloud verdicts are consistent across vendors and APIs.
- Nimble is close to Qwen (first) and in the middle for Jev (fourth): slightly
  stricter than Qwen, clearly more lenient than Jev.
- Clef is not between Qwen and Jev; it is stricter than Jev.

## The Local Judges Against the Cloud Judges

Taking the majority verdict of Jev, OpenAI and Ternary (at least two of three
agreeing) as the reference over the 1,500 questions of `results-<lang>/`, the
local judges grade as follows:

| Judge | Ref. *correct* → *correct* | Ref. *partial* → *correct* | Ref. *incorrect* → *correct* / *partial* / *incorrect* |
| :--- | ---: | ---: | :---: |
| Qwen | 968 / 979 | 168 / 354 | 1 / 10 / 156 |
| Nimble | 947 / 979 | 128 / 354 | 0 / 17 / 150 |
| Clef Flash | 962 / 979 | 240 / 354 | 14 / 28 / 125 |
| Clef | 858 / 979 | 56 / 354 | 0 / 18 / 149 |

Because the reference is itself strict on omissions, *partial* → *correct* is
not necessarily an error; *incorrect* → *correct* is.

- **Qwen** meets the first two goals well (one error graded *correct*), but it
  saturates: 13 models score 100% in both languages, so it fails the third.
- **Clef Flash** is lenient in the wrong way: it grades 14 errors *correct*,
  including 10 fixed refusal sentences and "the entire night" for the gold
  "Five days".
- **Clef** handles errors and refusals reliably, but withholds *correct* from
  121 answers the cloud judges accept, typically answers that leave out a
  secondary detail. That reads the rubric more strictly than it is written.
- **Nimble** grades no error *correct*, drops fewer good answers than Clef
  (32), and does not saturate (no model at 100% in both languages). It is the
  best balance among the local judges, though it lets some factual errors off
  with *partial* rather than *incorrect*.

The cloud judges share Clef's strictness on omissions to a lesser degree: Jev
gives the fewest *correct* after Clef, which is how it separates the top models
that Qwen saturates (see [JEV.md](JEV.md)).

## Speed and Cost

For the 1,500 questions of `results-<lang>/`:

| Judge | Total wall time | Per request | API cost |
| :--- | ---: | ---: | ---: |
| Jev | 4m 42s | 0.19 s | $0.05 |
| OpenAI | 7m 3s | 0.28 s | $0.08 |
| Clef Flash | 15m 0s | 0.60 s | local |
| Nimble | 15m 56s | 0.64 s | local |
| Ternary | 35m 22s | 1.41 s | $0.00 (free tier) |
| Clef | 45m 56s | 1.84 s | local |

*The Jev row is the `jev-1.14.0` run ([JEV-1.14.md](JEV-1.14.md)): 2m 28s
(en) + 2m 14s (ja), with 1,217,978 input tokens at $0.042 per million.*

## Conclusion

For now, grading continues with **Jev (`jev-1.14.0`)**. It is consistent with
the two other cloud judges, handles refusals and errors reliably, separates the
top models, and is fast and cheap. Its strictness on secondary details is
known: it is stricter than the rubric's "essential facts" calls for, so its
scores are best read as a conservative ranking rather than an absolute
measure.

Among the local judges, Nimble is the closest to the grading wanted here and
the candidate if a local judge is needed; Clef is reliable on errors but too
strict, and Clef Flash is not usable because it grades refusals and errors
*correct*. Their verdicts are kept in `nimble/`, `clef/` and `clef-flash/` for
comparison.
