# TrueMargin

TrueMargin studies uncertainty in deformable image registration:

> **When does local variability from deformable image registration contain useful information about true local spatial error?**

**Current result:** median anatomy-level Spearman correlation **0.6841**, with **6 of 30 case-level reversals** and **39 of 1,500 high-error, low-spread observations**. Useful information and meaningful failure modes coexist.

**Status:** controlled studies are complete. One real-image Case7 registration member completed and passed same-host retained-field readback and a read-only integrity audit. Cross-host restoration, full-campaign feasibility and external landmark validation remain unverified; numerical held-out landmarks are sealed.

The project evaluates rank informativeness, failure modes, and numerical error bounds separately. It is research software, not a clinical product or medical device.

[Visual study](https://kushrishi.com/research/truemargin) · [Technical report](docs/technical_report.md) · [Reproduction](docs/reproduction.md) · [Roadmap](research/ROADMAP.md)

![TrueMargin controlled association, blind spots and calibrated bounds](docs/figures/m4_m6_evidence.png)

## Check the retained results

From a checkout, using Python 3.12:

```bash
python scripts/verify_m6_phase_a_result.py results/m6_phase_a
python scripts/verify_m6_phase_b_result.py results/m6_phase_b
```

These standard-library checks need no imaging data, registration run or landmark
access. They verify the saved calibration and evaluation records, including
hashes, cohort identity and numerical summaries. A mismatch exits nonzero.
They do not reproduce the original registrations.

[Full reproduction guide](docs/reproduction.md) ·
[Retained outputs](results/README.md)

## Reading the results

Registration spread measures how much nine registrations disagree about a point’s displacement. A positive rank correlation means points with more disagreement tend to have larger known errors; it does not mean the disagreement equals the error. Coverage is the fraction of sampled errors inside a calibrated bound. Radius is the size of that bound in millimetres: high coverage can still require bounds too large to be useful. Here, patient-level summaries prevent spatial samples from being counted as independent patients.

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
- [Research evidence guide](research/README.md)
- [Failure characterization](docs/m5_informativeness_characterization.md)
- [Held-out calibration result](docs/m6_phase_b_evaluation_result.md)
- [Calibration failure diagnostics](docs/m6_failure_diagnostics.md)
- [Reproducible result records](research/)

The repository preserves protocols, machine-readable results, implementation history, and negative findings so the reported conclusions can be checked without rewriting the experimental record.

## Method

1. Register each image pair with nine fixed hyperparameter settings.
2. Measure local variation in the displacement fields.
3. Compare that spread with known error and independent signals.
4. Analyze blind spots and calibrated bounds separately.

## Repository

- `src/`: analysis code
- `scripts/`: experiment and verification entry points
- `tests/`: numerical and invariant checks
- `research/`: protocols and accepted result records
- `docs/`: reports, methods, and interpretation
- `results/`: retained derived outputs

For a development checkout with Python 3.12:

```bash
python -m pip install -e ".[dev]"
pytest
```

Some research workflows require optional dependencies and source data described in the corresponding protocol or reproduction document.

## Calibration-only development check

A leave-one-anatomy-out development analysis used only the original Phase-A calibration cohort; it did not open the previously observed Phase-B evaluation records.

At nominal 90%, the result was source-dependent:

| Source | Scale | Mean coverage | Mean radius |
| --- | --- | ---: | ---: |
| Prostate-3T | constant | 96.8% | 2.31 mm |
| Prostate-3T | affine | 98.0% | 2.66 mm |
| Prostate-Diagnosis | constant | 98.9% | 4.01 mm |
| Prostate-Diagnosis | affine | 95.5% | 3.15 mm |

The affine scale is therefore not a uniform improvement: the simple constant radius is smaller in the 3T development folds, while the affine scale is smaller in the Diagnosis folds and still exceeds 90% mean coverage. The overlapping folds are development evidence, not an independent confirmation.

[Read the calibration-only analysis](docs/m6_calibration_only_scale_validation.md)

## Next study

Evaluate whether the unchanged sensitivity signal ranks measured registration
error on independent lung CT cases, against inverse consistency, image residual
and Jacobian signals. External calibration is a separate question.

Image-only decoding is qualified. One Case7 registration member completed on a
persistent Mac worker (33.88 minutes, 2.235 GiB peak RSS), with a full-field
integrity audit and separate-process readback on the same host. The optimizer
reached its configured 15-iteration cap; convergence and alignment accuracy
are not established. Earlier Colab attempts remain separately recorded,
including unknown terminal outcomes.

Next, verify real cross-host restoration of this exact retained field, assess
optimizer stopping and configuration diversity without numerical landmark
outcomes, and qualify representative case/direction resource requirements
before any 180-member campaign decision. The prospective external protocol
and source/environment identities still require review. No external
landmark-based result exists; numerical landmarks remain sealed. The
[Case7 completion audit](https://github.com/Kushrishi/research-execution)
is retained in the private execution repository.

[Current status](research/STATE.md) · [External protocol](docs/external_lung_validation_protocol.md) · [Retention design](research/DIRLAB_BOUNDED_RETENTION_DESIGN_2026_10_09.md)

## Limits

TrueMargin does not currently establish clinical validity, external-dataset validation, uniform reliability, superiority over inverse-consistency error, or a peer-reviewed publication.

## Source distribution

This public repository has no open-source license grant. Source distribution
licensing must be resolved before a reusable package release; third-party data
and software retain their own terms.
