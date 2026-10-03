# Current research state

**Updated:** 2026-10-02  
**Status:** active public research program  
**Publication status:** no submitted, accepted, or published paper

This file is the canonical short-form state for TrueMargin. Frozen protocols, amendments, and completed result records remain authoritative for their own scientific choices and outcomes.

## Research question

When a deformable image-registration method reports local uncertainty, under what conditions does that signal contain useful information about true local spatial registration error?

The program separates five questions:

1. operational variability;
2. pointwise error informativeness;
3. numerical calibration;
4. blind-spot and failure behavior;
5. robustness and generalization.

No one axis is treated as a substitute for another.

## Historical evidence boundary

Earlier T2-to-DCE experiments used a zero-displacement reference assumption on real data. That value is not independently verified pointwise registration ground truth.

Historical real-data results may motivate hypotheses and operational checks, but they are not definitive pointwise error validation. The older manuscript, product framing, and historical real-data narrative are archived and are not the current paper.

## Completed estimator development

The prospective rebuild retained negative results rather than tuning around them.

- The corrected relative-intensity perturbation ensemble failed its frozen promotion gate.
- The mesh-3, 15-iteration registration regime passed its prospective field-stability gate.
- The initialization-sensitivity ensemble failed prospective promotion.
- The nine-member registration-hyperparameter ensemble passed operational promotion.

Frozen estimator:

- Mattes-MI bins: 32, 50, 64
- LBFGSB gradient tolerance: 1e-4, 1e-5, 1e-6
- Cartesian members: 9
- mesh size: 3
- maximum iterations: 15
- `center_first`: false

Operational promotion did not establish pointwise informativeness. That question was tested separately in M4.

## M4 known-ground-truth result

M4 completed successfully on 2026-09-26 under the frozen source-pinned authorization.

Design:

- 10 held-out anatomies;
- 3 deformation replicates per anatomy;
- 30 of 30 complete primary cases;
- 270 forward and 270 reverse registrations;
- 50 frozen fixed-domain ROI locations per case.

Primary anatomy-level result:

- positive anatomy-level associations: **10 of 10**;
- median Spearman association: **0.6840816**;
- 10,000-replicate anatomy bootstrap 95% interval: **[0.3047779, 0.8283794]**;
- exact one-sided anatomy sign-test: **p = 0.0009765625**;
- median high-versus-low uncertainty known-error delta: **1.7120 mm**.

This supports the bounded claim that the promoted hyperparameter-ensemble sigma contains useful pointwise rank information about true local spatial error in the frozen synthetic known-deformation study.

Direct comparator context:

- inverse-consistency error median anatomy Spearman: **0.7203**;
- same-modality residual: **0.2851**;
- Jacobian deviation: **0.1689**.

The paired target-minus-ICE bootstrap interval is **[-0.0903, 0.0736]**, so superiority over ICE is not established.

## M5 failure characterization

M5 completed on 2026-10-01 using only frozen M4 artifacts. No registration was rerun.

Post-primary findings:

- 24 of 30 case-level sigma/error associations were positive and 6 of 30 were negative;
- median case-level Spearman was **0.6465**;
- 39 of 1,500 target-sigma locations met the frozen high-error, low-sigma blind-spot rule;
- blind spots occurred in 11 of 30 cases and 7 of 10 anatomies;
- `aaa0069` was persistently weak across all three deformation replicates;
- `aaa0053` replicate 1 had Spearman **-0.9020** and 10 of 50 target blind spots;
- ICE had 34 blind-spot points among 1,350 points from its 27 valid cases;
- only 12 of the 39 target-sigma blind spots were also ICE blind spots.

These findings do not alter the M4 inference. They show that the positive anatomy-level result is heterogeneous across deformation instances and includes real high-error, low-sigma failures.

## M6 calibration state

M6 is active and has entered source-pinned Phase A calibration execution.

Completed before any M6 estimator outcome:

1. The official 80-subject NCI-ISBI image and annotation identity surface was audited successfully.
2. All 60 official training anatomies passed the frozen geometry-eligibility gate.
3. Exact identity comparison found zero SeriesInstanceUID and zero StudyInstanceUID overlap between the M4 cohort and the M6 challenge surface.
4. A deterministic source-stratified split was frozen: 30 calibration and 30 evaluation anatomies, with 15 of each role within each source regime.
5. The source-specific Hierarchical Conformal Prediction protocol was frozen prospectively.
6. Sigma was frozen as the primary calibrated signal and ensemble-mean ICE as the secondary calibrated comparator.
7. The first deformation-only preflight preserved four geometry failures caused by an infeasible inherited voxel-margin rule on thin through-plane images.
8. A prospective physical-distance boundary-margin amendment was applied uniformly to all 60 anatomies.
9. The amended deformation-only preflight completed **60 of 60** anatomies with zero failures.

The amended preflight is recorded in `research/M6_DEFORMATION_PREFLIGHT_AMENDMENT_1_RESULT.json` from workflow run `37050507332` and source SHA `a502466d4845be86780eb7a2306a96603ec4ab18`.

The first Phase A attempt, run `37065698410`, completed 26 anatomy jobs but remained incomplete after four pre-result label-transport failures. Its partial outputs are preserved and are not accepted for aggregation. Partial numerical outputs were not inspected to select the transport repair.

The uniform rerun, `37075119713`, passed preflight but failed centralized legacy-host label staging. All anatomy and aggregate jobs were skipped. No complete Phase A calibration artifact or thresholds have been established. Evaluation remains sealed. These failures are recorded in `M6_PHASE_A_DIAGNOSTIC_1.json` and `M6_PHASE_A_DIAGNOSTIC_2.json`.

### Frozen M6 design

- 60 official challenge training anatomies;
- 30 calibration and 30 sealed evaluation anatomies;
- 15 calibration and 15 evaluation anatomies per source regime;
- one synthetic deformation per anatomy;
- 50 frozen ROI points per anatomy;
- source-specific HCP with anatomy as the group;
- primary signal: nine-member hyperparameter-ensemble sigma;
- secondary calibrated comparator: ensemble-mean ICE;
- primary nominal coverage: 90%;
- descriptive secondary nominal coverage: 80%;
- 95% finite-sample sentinel retained even when its exact HCP threshold is infinite;
- no primary abstention rule;
- zero-signal handling frozen before outcomes.

### Current bottleneck

The current official label transport passed hosted preflight and the separately authorized run `37078110203`. All 30 anatomy jobs then failed the frozen-input validation step; nine also failed artifact upload. Aggregation was skipped. The sampled DICOM ZIP digest differed from the unchanged input registry while patient, series, label, and geometry identities matched. Two current official downloads had identical member bytes but mutable ZIP timestamps. Historical frozen image identity has not been established from that observation.

`M6_PHASE_A_DIAGNOSTIC_3.json` records the operational failure without analyzing numerical calibration outcomes. The guard correction in `docs/m6_phase_a_input_identity_failure.md` enforces original input digests before decoding or registration. The bottleneck is recovery or independent verification of the historical frozen DICOM bytes. No new calibration request is issued by this correction.

Phase A is allowed to run the frozen forward estimator and reverse ICE comparator, compute the predeclared calibration scores, and fit source-specific HCP thresholds. It must not run any of the 30 evaluation anatomies.

After Phase A, the complete calibration artifact and exact thresholds must be reviewed and sealed before a separate Phase B evaluation authorization can be created.

The M4 estimator, M5 failure record, M6 split, ROI rule, deformation rule, score definition, zero-signal rule, and failure policy must not be changed in response to Phase A outcomes.

## Not established

TrueMargin does not currently establish:

- numerical calibration or probabilistic coverage;
- superiority over inverse-consistency error;
- uniform reliability across deformation instances;
- external-dataset generalization;
- clinical validity or clinical usefulness;
- a completed manuscript, preprint, or peer-reviewed publication.

## Source-of-truth order

When documents disagree, use this order:

1. frozen prospective protocols, amendments, and completed result records;
2. this file for current project-level state;
3. `research/CLAIMS.md` for externally safe claim boundaries;
4. `README.md` for the public summary;
5. archived historical material.

Website, GitHub profile, CV, and LinkedIn wording must not exceed the evidence recorded here and in `research/CLAIMS.md`.
