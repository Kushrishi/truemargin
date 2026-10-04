# TrueMargin

TrueMargin is a medical-image-computing research project asking a focused question:

> **When does local variability from deformable image registration contain useful information about true local spatial error?**

The project evaluates rank informativeness, failure modes, and numerical error bounds separately. It is research software, not a clinical product or medical device.

## Main findings

A controlled known-deformation study evaluated 30 cases across 10 held-out anatomies. The registration-hyperparameter ensemble produced a median anatomy-level Spearman association of **0.6841** with known local error, and all **10 of 10** anatomy-level associations were positive.

Direct comparator medians were:

| Signal | Median anatomy Spearman |
| --- | ---: |
| Ensemble spread | 0.6841 |
| Inverse-consistency error | 0.7203 |
| Same-modality residual | 0.2851 |
| Jacobian deviation | 0.1689 |

The study supports local rank informativeness for ensemble spread in this setting, but does **not** establish superiority over inverse-consistency error.

## Where it fails

The aggregate result is not uniform. Reanalysis of the same 1,500 pointwise observations found:

- 24 of 30 case-level spread/error associations were positive;
- 6 of 30 were negative;
- 39 of 1,500 observations met the high-error, low-spread blind-spot rule;
- blind spots appeared in 11 of 30 cases and 7 of 10 anatomies.

These failures are part of the result rather than cases removed after inspection.

## Held-out error bounds

A separate study used 30 calibration and 30 evaluation anatomies, stratified across two source regimes.

At nominal 90%:

- empirical equal-anatomy coverage was **97.73%** and **99.73%**;
- median anatomy radii were **3.93 mm** and **4.36 mm**;
- one evaluation anatomy had a **70.69 mm** median radius.

The resulting bounds are conservative, and the 95% thresholds are infinite under the study's finite-sample construction. The planned full-cohort calibrated comparison with inverse-consistency error was not assessable because of retained reverse-registration failures.

## Read the research

- [Technical report](docs/technical_report.md)
- [Known-ground-truth result](docs/hyperparameter_known_gt_result.md)
- [Failure characterization](docs/m5_informativeness_characterization.md)
- [Held-out calibration result](docs/m6_phase_b_evaluation_result.md)
- [Calibration failure diagnostics](docs/m6_failure_diagnostics.md)
- [Reproducible result records](research/)

The repository preserves protocols, machine-readable results, implementation history, and negative findings so the reported conclusions can be checked without rewriting the experimental record.

## Repository

- `src/` — reusable analysis code
- `scripts/` — experiment and verification entry points
- `tests/` — numerical and invariant checks
- `research/` — protocols and accepted result records
- `docs/` — reports, methods, and interpretation
- `results/` — retained derived outputs

For a development checkout with Python 3.12:

```bash
python -m pip install -e ".[dev]"
pytest
```

Some research workflows require optional dependencies and source data described in the corresponding protocol or reproduction document.

## Current direction

The completed studies show a useful but imperfect relationship between ensemble variability and true error. The next research decision is whether an adaptive error-scale model provides enough benefit over simpler constant or inverse-consistency-based alternatives to justify a fresh external validation study.

No new registration result is claimed by that development work.

## Limits

TrueMargin does not currently establish clinical validity, external-dataset validation, uniform reliability, superiority over inverse-consistency error, or a peer-reviewed publication.
