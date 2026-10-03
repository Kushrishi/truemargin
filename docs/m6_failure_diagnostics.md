# Why conservative coverage is not enough

**October 3, 2026 — post-outcome descriptive analysis**

This note investigates the retained M6 calibration tail and large evaluation
radii. It uses all 30 calibration and all 30 evaluation anatomies, with the
original 50 points per anatomy. No registration is rerun, threshold refitted,
patient excluded or primary result replaced. These questions were selected
after M6 outcomes were observed; the analysis is not confirmatory.

## Two different behaviors

The Diagnosis calibration source contains an anatomy with very small spread
despite nonzero registration error. A different evaluation anatomy has both
large spread and larger error. A single source-level multiplier links these
behaviors, producing very large radii in the latter case.

| Anatomy and role | Median spread, mm | Median error, mm | Within-case Spearman | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Diagnosis `0082`, calibration | 0.01182 | 0.75995 | −0.03577 | Low agreement between spread and error ranks; smallest median spread of its 15 calibration anatomies |
| Diagnosis `0043`, evaluation | 1.35738 | 3.80195 | 0.97455 | Strong local rank association, but very large calibrated radii; largest median spread of its 15 evaluation anatomies |

The large-radius case is therefore **not** an example of an inverted local
ranking. It illustrates a different problem: a signal can rank errors well
within one anatomy while a global calibration multiplier produces bounds too
large to establish numerical usefulness. No clinical radius tolerance has been
defined in this study.

## Calibration-tail concentration

With 15 equally weighted calibration groups and 50 points per group, each finite
score has mass 1/800 and the new-group infinity atom has mass 1/16. The sealed
90% multiplier is finite score rank 720 of 750. Scores are error divided by
spread; the diagnostic recomputes this equality and checks vector digests.

| Source | Sealed 90% multiplier | Points at or above cutoff | Anatomies represented in this tail | Anatomy at rank 720 |
| --- | ---: | ---: | ---: | --- |
| 3T | 41.95617 | 31 | 10 | `0024` |
| Diagnosis | 52.08148 | 31 | 1 | `0082` |

All 31 upper-tail Diagnosis points belong to `0082`. At the cutoff point, error
is 0.63826 mm and spread is 0.01226 mm. The multiplier is not large because that
point has an exceptionally large absolute error: its denominator is small.
This establishes arithmetic concentration, not the cause of the small spread
and not a justification to remove the anatomy. In 3T, the upper tail spans ten
anatomies; a single-case explanation would not cover both sources.

## Radius concentration and sensitivity

The following summaries average each anatomy's mean radius with equal anatomy
weight. They are not the median-of-anatomy-medians used in the primary report.

| Source | Full-cohort mean radius, mm | Largest anatomy mean radius, mm | Largest anatomy's share of radius sum | Leave-largest-out mean, mm |
| --- | ---: | ---: | ---: | ---: |
| 3T | 4.65697 | 9.95246 (`0019`) | 14.25% | 4.27872 |
| Diagnosis | 10.26172 | 79.45719 (`0043`) | 51.62% | 5.31918 |

The last column is a descriptive sensitivity calculation only. The primary
cohort remains complete and unchanged. Diagnosis's full-cohort mean is heavily
influenced by `0043`, but the remaining mean is still larger than the previously
reported exploratory constant radius of 2.83822 mm. Achieved coverage differs
between constructions, so this does not establish coverage-matched dominance.
The 79.46 mm mean and previously reported 70.69 mm median refer to the same
anatomy and must not be interchanged.

## All-case ranking context

| Source | Negative calibration case correlations | Negative evaluation case correlations |
| --- | ---: | ---: |
| 3T | 4 / 15 | 6 / 15 |
| Diagnosis | 2 / 15 | 6 / 15 |

These are descriptive counts from the retained M6 vectors, not a new primary
test or a pooled replication with M4/M5. No significance claim is made; the
sampled points are spatially dependent. The JSON record contains every anatomy's
correlation, spread, error, coverage, radius and ICE completion status.

The existing M5 record remains six negative cases out of 30 and 39 blind-spot
points in 11 cases across seven anatomies. M5 characterizes reused M4 outputs;
it is not an independent replication. Severe inversion in one M5 case and
strong local ranking with oversized radii in M6 `0043` are different failure
classes, not evidence of one shared mechanism.

## What the retained evidence can and cannot check

The diagnostic checks all 60 primary vector digests, patient/source/phase
identities, sealed-ratio arithmetic, complete nine-member forward status,
geometry hash and series identity. Evaluation image and label identities are
also checked against the frozen input record. The 90% order statistics match
the seal exactly. All inputs are identified by 66 SHA-256 file digests.

Both focal anatomies record nine forward members as `ok`. That means they passed
the existing validity checks, not that the optimizer converged, found a correct
solution or explored sufficiently different solutions. The ensemble checks
field validity and summarizes member displacements. M6's retained shards do not
contain member-level displacement vectors, loss histories or optimizer stop
descriptions. The evaluation numerical checkpoints contain sampled indices,
true displacements and summary vectors, not those missing optimizer diagnostics.
Calibration checkpoints and full image/geometry records are not part of the
curated Phase-A result directory inspected here; geometry hashes establish
identity, not anatomical explanation.

Diagnosis `0043` records all nine reverse members as `ok`, followed by an ICE
sampling failure: a sample point lies outside the image domain. This is distinct
from the 3T calibration reverse-member failure. Clamping, dropping points or
excluding these anatomies would change the accepted comparator policy. Neither
failure is repaired by this analysis.

No inspected record establishes that preprocessing, geometry, optimizer
convergence or a software defect caused the focal behaviors. A common optimizer
basin, insufficient ensemble diversity and anatomy/deformation effects remain
hypotheses. Evidence that runs agreed does not prove they agreed on the right
answer. A geometry identity match does not rule out a consistently applied
implementation error.

## Decision

The bounded retained-data audit is complete. It strengthens the case-study
explanation but does not establish a new method or a shared failure mechanism.
Do not refit the multiplier, clip the large radius or retrofit a spread floor
using these evaluation outcomes.

The strongest conditional next study would ask whether a prospectively defined
spread-based decision improves error detection or radius efficiency beyond
constant radii and ICE. It would need a distinct practical question, fresh
held-out anatomies, complete failure accounting and member-level diagnostics.
Development could examine a simple nonzero error-scale model, but that is
ordinary calibration machinery and must not be advertised as automatic novelty.
An outcome-selected abstention rule would not inherit the original marginal
coverage guarantee.

Until that study has a defensible contribution and design, keep M7 unexecuted
and prioritize the engineering application. The completed M4–M6 study remains
presentable; the research area is not declared exhausted.

## Reproduction

Run from the repository root with Python 3.12:

```sh
python scripts/m6_failure_diagnostics.py .
pytest tests/test_m6_failure_diagnostics.py
```

The output is retained in
[`failure_diagnostics.json`](../results/m6_exploratory/failure_diagnostics.json).
The script is standard-library only and reads numerical records, not images.
Tests cover retained-record replay, tied/constant rank signals, malformed rank
inputs and rejection of changed vectors or geometry identities. This is artifact
analysis, not an independent rerun of image registration.
