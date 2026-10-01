# Current research state

**Updated:** 2026-10-01  
**Status:** active public research program  
**Publication status:** no submitted, accepted, or published paper

This file is the canonical short-form state for TrueMargin.

## Research question

When a deformable image-registration method reports local uncertainty, under what conditions does
that signal contain useful information about true local spatial registration error?

The program separates:

1. operational variability;
2. pointwise error informativeness;
3. numerical calibration;
4. blind-spot/failure behavior;
5. generalization.

No one axis is treated as a substitute for the others.

## Historical evidence boundary

Earlier T2-to-DCE experiments used a zero-displacement reference assumption on real data. That
value is not independently verified pointwise registration ground truth.

Historical real-data results may motivate hypotheses and operational checks, but they must not be
described as definitive pointwise error validation. The older manuscript, product framing, and
historical real-data narrative are archived and are not the current paper.

## Prospective rebuild sequence

### 1. Corrected input-intensity perturbation ensemble

**Result:** failed prospective Gate A.

No tested nonzero relative-intensity perturbation satisfied the frozen combination of completeness,
non-inertness, and proxy-error degradation limits. The grid was not widened after observing the
result.

### 2. Registration convergence

**Result:** mesh 3 / 15 maximum iterations selected.

The prospectively specified convergence gate found 15 iterations to be the smallest candidate
budget passing the frozen global field-stability criterion. This is a regime-specific operational
result, not a universal convergence claim.

### 3. Initialization-sensitivity ensemble

**Result:** failed prospective promotion.

No tested nonzero B-spline initialization perturbation strength passed the frozen
completeness/non-inertness rule. The grid was not widened after observing the result.

### 4. Registration-hyperparameter ensemble

**Result:** passed operational promotion.

Frozen estimator:

- Mattes-MI bins: 32, 50, 64
- LBFGSB gradient tolerance: 1e-4, 1e-5, 1e-6
- Cartesian members: 9
- mesh size: 3
- maximum iterations: 15
- center_first: false

The mechanism completed all nine members in all five frozen sensitivity patients and exceeded the
predeclared repeatability/resolution floor in four of five. This established operational promotion
only and did not itself establish pointwise informativeness.

### 5. M4 hyperparameter known-ground-truth evaluation

**Result:** completed successfully on 2026-09-26 under the frozen source-pinned authorization.

Result-bearing execution:

- workflow run: `36188222836`, successful attempt 3;
- execution Git SHA: `9add89e5055ba45eb6c6b93c42da38615891a225`;
- canonical artifact ID: `10896650804`;
- canonical artifact digest:
  `sha256:bd1f76e20c7e4591b5b3113c061c90534ec413bda0a242747625ed6d5f96b728`;
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

This supports the bounded claim that, in the frozen synthetic known-deformation study, the promoted
hyperparameter-ensemble sigma contains useful pointwise rank information about true local spatial
registration error.

Direct comparator context:

- inverse-consistency error median anatomy Spearman: **0.7203**;
- same-modality residual: **0.2851**;
- Jacobian deviation: **0.1689**.

The paired target-minus-comparator anatomy bootstrap interval is wholly positive for residual and
Jacobian deviation. The target-minus-ICE interval is **[-0.0903, 0.0736]**, so superiority over
inverse-consistency error is not established.

Durable M4 records:

- `docs/hyperparameter_known_gt_result.md`;
- `research/KNOWN_GT_M4_RESULT.json`.

### 6. M5 informativeness, comparator, and blind-spot characterization

**Result:** complete on 2026-10-01 using only frozen M4 artifacts; no registrations rerun.

All ten patient shard archive SHA-256 digests were verified against the original GitHub Actions
artifact records. Their 30 checkpoint files preserved the 50 fixed-domain ROI locations per case,
for 1,500 pointwise observations. Recomputed case-level rank, quartile-enrichment, and blind-spot
metrics were required to agree with the canonical M4 case table.

Post-primary descriptive findings:

- 24 / 30 case-level sigma/error Spearman associations were positive and 6 / 30 were negative;
- median case-level Spearman was **0.6465**;
- 39 / 1,500 target-sigma locations met the frozen high-error / low-sigma blind-spot rule;
- blind spots occurred in 11 / 30 cases and 7 / 10 anatomies;
- `aaa0069` was persistently weak across all three deformation replicates, with anatomy median
  Spearman **0.0334**;
- `aaa0053` replicate 1 had Spearman **-0.9020** and 10 / 50 target blind spots despite that
  anatomy's strong median across replicates;
- ICE had 34 blind-spot points among 1,350 points from its 27 valid cases;
- 12 of the 39 target-sigma blind spots were also ICE blind spots;
- ICE and same-modality residual each retained 3 / 30 method-invalid cases due to sampled points
  outside the image domain; Jacobian deviation remained valid in 30 / 30 cases.

These findings do not alter the M4 inference. They establish that the positive anatomy-level result
is heterogeneous across deformation instances and has real high-error/low-sigma failure locations.
They do not establish sigma superiority over ICE or a benefit from combining signals.

Durable M5 records:

- `docs/m5_informativeness_characterization.md`;
- `research/M5_CHARACTERIZATION.json`;
- `research/M5_SOURCE_ARTIFACTS.json`;
- `results/m5/`.

## Current bottleneck

M1-M5 are complete. M6 is the next active design milestone.

The next scientific question is **numerical calibration**, kept separate from ranking
informativeness. Before any new result-bearing calibration or robustness execution:

1. define what numerical scale or interval the target sigma is allowed to claim;
2. freeze calibration metrics, coverage targets, fitting/evaluation separation, and any
   held-out/calibration partition prospectively;
3. do not use M4-M5 failures to retune the completed estimator or sampled cases;
4. keep robustness/generalization as a later, separately frozen milestone.

The completed M4 estimator definition, comparator definitions, cohort, seeds, cases, ROI rule,
primary statistic, and M5 descriptive failure record must not be retuned based on the observed
results.

## Current source-of-truth order

1. frozen prospective protocols, amendments, and completed M4/M5 result records in `docs/` and
   `research/`;
2. this file;
3. `research/CLAIMS.md`;
4. current README;
5. archived historical material.

Website, GitHub profile, CV, and LinkedIn wording must never be stronger than this state.
