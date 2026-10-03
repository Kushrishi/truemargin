# Error-scale continuation assessment

October 3, 2026. Exploratory development after observing M6 outcomes; no new
registration, accepted threshold change, clinical claim or confirmatory result.

## Question

Can a nonzero baseline error term reduce the instability of error/spread scores,
and is spatial adaptation useful compared with constant bounds?

The candidate scale is `intercept + slope * spread`. Both coefficients are
nonnegative and fit by least squares to known errors. This ordinary calibration
model is not proposed as a novel method.

For each acquisition source, calibration patient IDs are ordered by SHA-256 of
the ID. Five anatomies fit the scale and the other ten calibrate all three
models: constant, spread-only and affine. Each anatomy retains all 50 points.
The 90% hierarchical threshold is score rank 495 of 500, retaining the new-group
infinity atom. Evaluation uses the original fifteen evaluation anatomies per
source. They were previously observed; separation from fitting does not turn
this into a fresh confirmatory test.

Block 0 was examined first. Blocks 1 and 2 subsequently use the other contiguous
five-anatomy fit groups as descriptive split sensitivity. All results are
retained. These repeat the same evaluation cohort, not independent replications.

## Results

Each entry reports empirical coverage / equal-anatomy mean radius in mm.

| Source | Fit block | Constant | Spread-only | Affine |
| --- | ---: | --- | --- | --- |
| 3T | 0 | 95.60% / 2.322 | 99.33% / 7.566 | 98.00% / 2.711 |
| 3T | 1 | 98.40% / 2.910 | 98.80% / 6.235 | 98.53% / 2.780 |
| 3T | 2 | 98.40% / 2.910 | 99.33% / 7.400 | 98.53% / 2.870 |
| Diagnosis | 0 | 96.80% / 3.924 | 98.80% / 7.962 | 95.60% / 2.600 |
| Diagnosis | 1 | 96.53% / 3.629 | 100.00% / 27.295 | 99.87% / 3.485 |
| Diagnosis | 2 | 96.80% / 4.106 | 100.00% / 27.295 | 98.40% / 3.137 |

Affine mean radius is smaller than spread-only in all six source/block settings,
with different achieved coverage. It is smaller than constant in five settings
and larger in one. Some constant comparisons remain very close. These are not
coverage-matched comparisons or statistical superiority evidence. All three
models exceed nominal coverage here; no population or clinical guarantee follows.

## Decision

Continue bounded development of the error-scale question. Do not claim a new
method, select the most favorable block or change the accepted M6 estimator.
The original conclusion remains intact. This exploration shows that the current
spread-only mapping is not the only feasible approach, but does not yet establish
that spatial adaptation is worth its registration cost.

Before new expensive registration: assess whether the benefit survives a
development-only anatomy-level validation design, define the practical radius or
error-detection decision, and freeze the comparison and failure policy. A fresh
evaluation must include constant bounds and feasible ICE comparisons, retain
member-level displacement and optimizer diagnostics, and report coverage,
radius tails, completion and computation cost. Existing evaluation results must
not select the primary endpoint or its required improvement.

## Reproduction and checks

```sh
python scripts/m6_scale_development.py .
python scripts/m6_scale_development.py . --fit-block 1
python scripts/m6_scale_development.py . --fit-block 2
pytest tests/test_m6_scale_development.py
```

Numerical records are retained in `results/m6_exploratory/scale_development*.json`.
The existing diagnostic validates all M6 identities and vector digests before
analysis. Tests cover known affine coefficients, constrained fitting, hierarchical
quantiles and evaluation-error isolation. A separate numerical cross-check against
SciPy NNLS agreed on thirty fixed-seed random inputs; that checks arithmetic, not
scientific validity. No raw medical images are added.
