# TrueMargin

TrueMargin is a medical-image-computing research project studying a narrow question:

> **When a deformable image-registration method reports local uncertainty, under what conditions does that signal contain useful information about true local spatial registration error?**

The project separates operational variability, pointwise informativeness, numerical calibration, blind spots, and generalization. These are evaluated independently rather than treated as interchangeable evidence.

TrueMargin is research software, not a clinical product or medical device.

**Status:** the M4–M6 study and retained-data diagnostics are complete. New registration experiments are paused; bounded retained-data error-scale development continues. The results support a bounded technical report, not a validated clinical uncertainty method or a published paper.

## Start here

| Reader goal | Link |
| --- | --- |
| Understand the findings and limitations | [Technical report](docs/technical_report.md) |
| Review the held-out calibration result | [M6 evaluation](docs/m6_phase_b_evaluation_result.md) |
| Understand the large radii and calibration tail | [Failure diagnostics](docs/m6_failure_diagnostics.md) |
| Check why new experiments are paused | [Contribution review](docs/m4_m6_contribution_review.md) |
| Check project state and public claim boundaries | [State](research/STATE.md) and [claims](research/CLAIMS.md) |

## Current evidence

The prospective rebuild produced both negative and positive results before the primary known-ground-truth study:

- a relative-intensity perturbation ensemble failed its frozen promotion gate;
- the mesh-3, 15-iteration registration regime passed its prospective field-stability gate;
- an initialization-sensitivity ensemble failed its frozen promotion gate;
- a frozen nine-member registration-hyperparameter ensemble passed operational promotion.

Operational promotion did not establish that the uncertainty signal tracked true error. M4 tested that question prospectively on synthetic known deformations in held-out anatomies.

## Primary known-ground-truth result

M4 completed 30 of 30 cases across 10 held-out anatomies under a frozen source-pinned protocol.

The promoted hyperparameter-ensemble sigma had a median anatomy-level Spearman association with known local error of **0.6841**. All **10 of 10** anatomy-level associations were positive. The exact one-sided anatomy sign-test gave **p = 0.0009766**, and the 10,000-replicate anatomy bootstrap interval for the median was **[0.3048, 0.8284]**.

Within this controlled study, the uncertainty signal therefore contains useful pointwise rank information about true local spatial error.

Direct comparator context:

- inverse-consistency error: median anatomy Spearman **0.7203**;
- same-modality residual: **0.2851**;
- Jacobian deviation: **0.1689**.

Paired anatomy-level bootstrap summaries support stronger rank informativeness for sigma than the residual and Jacobian-deviation comparators in this study. They do **not** establish superiority over inverse-consistency error because the target-minus-ICE interval crosses zero.

See `docs/hyperparameter_known_gt_result.md` and `research/KNOWN_GT_M4_RESULT.json` for the durable primary result.

## Failure characterization

M5 reanalyzed the exact frozen M4 outputs without rerunning registration or introducing a new confirmatory winner statistic.

Across all 1,500 frozen pointwise observations:

- 24 of 30 case-level sigma/error associations were positive and 6 of 30 were negative;
- 39 of 1,500 points met the frozen high-error, low-sigma blind-spot rule;
- blind spots occurred in 11 of 30 cases and 7 of 10 anatomies;
- `aaa0069` was persistently weak;
- `aaa0053` had one severe inverted replicate;
- ICE remained a strong comparator.

The M4 anatomy-level result is therefore positive but heterogeneous. It does not imply uniform reliability across deformation instances.

See `docs/m5_informativeness_characterization.md`, `research/M5_CHARACTERIZATION.json`, and `results/m5/` for the complete M5 evidence.

## M6 calibration

M6 separates fitting error-radius multipliers from testing their coverage on unseen anatomies. Its frozen design uses 30 calibration and 30 sealed evaluation anatomies, with 15 of each role per source, one synthetic deformation, and 50 frozen ROI locations per anatomy.

**Phase A is complete:** all 30 primary calibration anatomies completed in run `37114827455`. The complete artifact was verified, the aggregate replay matched byte for byte, and exact source-specific HCP thresholds were independently recomputed and sealed.

ICE completed 29 of 30 anatomies. The retained reverse-registration failure makes ICE calibration unassessable for the 3T source under the frozen policy; the diagnosis-source comparator remains assessable. The 95% HCP sentinel is positive infinity at 15 calibration groups.

**Phase B is complete and reviewed:** all 30 held-out primary anatomies completed. At nominal 90%, equal-anatomy coverage was 97.73% for Prostate-3T and 99.73% for Prostate-Diagnosis, with median anatomy radii of 3.93 mm and 4.36 mm. One diagnosis anatomy had a 70.69 mm median radius. These are conservative bounds in a frozen synthetic study, not evidence of clinical precision. The 95% thresholds are infinite; their 100% coverage is not useful finite-radius validation. ICE failures prevent the planned full-cohort calibrated comparison.

See [the held-out result](docs/m6_phase_b_evaluation_result.md), [accepted evidence](research/M6_PHASE_B_RESULT.json), and [threshold seal](research/M6_PHASE_A_THRESHOLD_SEAL.json). Read the [technical report](docs/technical_report.md) and [post-result contribution review](docs/m4_m6_contribution_review.md) before considering further experiments. An explicitly exploratory constant-radius check does not establish an adaptive-efficiency advantage; it leaves all accepted M6 results unchanged.

The [retained-data failure analysis](docs/m6_failure_diagnostics.md) distinguishes a concentrated small-spread calibration tail from an evaluation case with strong local ranking but very large radii. It does not identify a causal mechanism or change the accepted study.

## Exploratory continuation

An [affine error-scale analysis](docs/m6_scale_development.md) fits a nonnegative baseline error term plus ensemble spread. All three fit blocks are retained. Mean radii were smaller than spread-only in six source/block settings, with different achieved coverage; constant comparisons were close in some settings. These reuse observed evaluation anatomies and do not establish superiority. The next milestone is calibration-cohort-only development validation, before any fresh study. See the [architecture and gates](docs/continuation_architecture.md).

## Research discipline

Result-defining choices are frozen before the corresponding outcomes are observed. Negative results and scientific failures are preserved rather than repaired after seeing outcomes.

The program keeps separate:

- local rank informativeness;
- high-error, low-reported-uncertainty blind spots;
- operational failures;
- numerical calibration;
- robustness and external generalization.

See `research/STATE.md` for current project state, `research/CLAIMS.md` for public claim boundaries, and `research/ROADMAP.md` for milestone status.

## Current limits

TrueMargin does **not** currently establish:

- exact nominal calibration or unconditional probabilistic coverage beyond the frozen hierarchical assumptions;
- superiority over inverse-consistency error;
- uniform reliability across deformation instances;
- independent external-dataset validation;
- clinical validity or clinical usefulness;
- a completed manuscript, preprint, or peer-reviewed publication.
