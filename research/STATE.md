# Current research state

**Updated:** 2026-10-01  
**Status:** active public research program  
**Publication status:** no submitted, accepted, or published paper

This file is the canonical short-form state for TrueMargin.

## Research question

When a deformable image-registration method reports local uncertainty, under what conditions does that signal contain useful information about true local spatial registration error?

The program separates:

1. operational variability;
2. pointwise error informativeness;
3. numerical calibration;
4. blind-spot/failure behavior;
5. generalization.

No one axis is treated as a substitute for the others.

## Historical evidence boundary

Earlier T2-to-DCE experiments used a zero-displacement reference assumption on real data. That value is not independently verified pointwise registration ground truth.

Historical real-data results may motivate hypotheses and operational checks, but they must not be described as definitive pointwise error validation. The older manuscript, product framing, and historical real-data narrative are archived and are not the current paper.

## Prospective rebuild sequence

### 1. Corrected input-intensity perturbation ensemble

**Result:** failed prospective Gate A.

No tested nonzero relative-intensity perturbation satisfied the frozen combination of completeness, non-inertness, and proxy-error degradation limits. The grid was not widened after observing the result.

### 2. Registration convergence

**Result:** mesh 3 / 15 maximum iterations selected.

The prospectively specified convergence gate found 15 iterations to be the smallest candidate budget passing the frozen global field-stability criterion. This is a regime-specific operational result, not a universal convergence claim.

### 3. Initialization-sensitivity ensemble

**Result:** failed prospective promotion.

No tested nonzero B-spline initialization perturbation strength passed the frozen completeness/non-inertness rule. The grid was not widened after observing the result.

### 4. Registration-hyperparameter ensemble

**Result:** passed operational promotion.

Frozen estimator:

- Mattes-MI bins: 32, 50, 64
- LBFGSB gradient tolerance: 1e-4, 1e-5, 1e-6
- Cartesian members: 9
- mesh size: 3
- maximum iterations: 15
- center_first: false

The mechanism completed all nine members in all five frozen sensitivity patients and exceeded the predeclared repeatability/resolution floor in four of five. This established operational promotion only and did not itself establish pointwise informativeness.

### 5. Hyperparameter known-ground-truth evaluation

**Result:** M4 completed successfully on 2026-09-26 under the frozen source-pinned authorization.

The amended geometry preflight had previously passed all 30 cases across 10 frozen held-out anatomies. The paper-level direct comparator suite and failure rules were frozen before result-bearing outcomes.

Result-bearing execution:

- workflow run: `36188222836`, successful attempt 3;
- execution Git SHA: `9add89e5055ba45eb6c6b93c42da38615891a225`;
- final artifact ID: `10896650804`;
- artifact digest: `sha256:bd1f76e20c7e4591b5b3113c061c90534ec413bda0a242747625ed6d5f96b728`;
- 10 held-out anatomies;
- 3 deformation replicates per anatomy;
- 30 / 30 complete primary cases;
- 270 planned forward + 270 planned reverse registrations;
- 50 frozen fixed-domain ROI locations per case.

Primary anatomy-level result:

- positive anatomy-level associations: **10 / 10**;
- median Spearman association: **0.6840816**;
- 10,000-replicate anatomy bootstrap 95% interval: **[0.3047779, 0.8283794]**;
- exact one-sided anatomy sign-test: **p = 0.0009765625**;
- median anatomy blind-spot rate under the frozen definition: **0.0**;
- median high-vs-low uncertainty known-error delta: **1.7120 mm**.

This supports the bounded claim that, in the frozen synthetic known-deformation study, the promoted hyperparameter-ensemble sigma contains useful pointwise rank information about true local spatial registration error.

Direct comparator context:

- inverse-consistency error median anatomy Spearman: **0.7203**;
- same-modality residual: **0.2851**;
- Jacobian deviation: **0.1689**.

The paired target-minus-comparator anatomy bootstrap interval is wholly positive for residual and Jacobian deviation, supporting stronger rank informativeness of the target sigma than those two comparators in this study. The target-minus-ICE interval is **[-0.0903, 0.0736]**, so superiority over inverse-consistency error is not established.

Method-specific invalid comparator cases were retained under the frozen failure rules. All direct methods remained assessable at the anatomy level across all ten anatomies.

The durable result records are:

- `docs/hyperparameter_known_gt_result.md`;
- `research/KNOWN_GT_M4_RESULT.json`.

## Current bottleneck

M1-M4 are complete. M5 is active.

The immediate research work is no longer to determine whether the promoted estimator has any known-ground-truth signal. That question has a positive result within the frozen study.

The next work is to characterize the result without broadening it post hoc:

1. preserve and analyze method-specific failures and high-error / low-reported-uncertainty blind spots;
2. produce anatomy-aware comparator and failure-case figures/tables from frozen outputs;
3. distinguish ranking informativeness from numerical calibration;
4. update the related-work and contribution boundary around the observed comparator result, especially the strong inverse-consistency baseline;
5. prospectively freeze any robustness study before result-bearing execution.

The completed M4 estimator definition, comparator definitions, cohort, seeds, cases, ROI rule, and primary statistic must not be retuned based on the result.

## Current source-of-truth order

1. frozen prospective protocols, amendments, and completed result record in `docs/` and `research/`;
2. this file;
3. `research/CLAIMS.md`;
4. current README;
5. archived historical material.

Website, GitHub profile, CV, and LinkedIn wording must never be stronger than this state.
