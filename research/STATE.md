# Current research state

**Updated:** 2026-10-03 UTC
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

M6 calibration and held-out evaluation are complete and accepted. All 30 primary evaluation anatomies completed against unchanged sealed thresholds. See `research/M6_PHASE_B_RESULT.json` and `docs/m6_phase_b_evaluation_result.md`.

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

The uniform rerun, `37075119713`, passed preflight but failed centralized legacy-host label staging. All anatomy and aggregate jobs were skipped. At that historical checkpoint, no complete Phase A calibration artifact or thresholds existed. Those failures are recorded in `M6_PHASE_A_DIAGNOSTIC_1.json` and `M6_PHASE_A_DIAGNOSTIC_2.json`.

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

### Historical input-identity failure

The current official label transport passed hosted preflight and the separately authorized run `37078110203`. All 30 anatomy jobs then failed the frozen-input validation step; nine also failed artifact upload. Aggregation was skipped. The sampled DICOM ZIP digest differed from the unchanged input registry while patient, series, label, and geometry identities matched. Two current official downloads had identical member bytes but mutable ZIP timestamps. Historical frozen image identity has not been established from that observation.

`M6_PHASE_A_DIAGNOSTIC_3.json` records the operational failure without analyzing numerical calibration outcomes. The guard correction in `docs/m6_phase_a_input_identity_failure.md` enforces original input digests before decoding or registration. That correction did not authorize a new calibration request. Exact recovery is recorded below.

### Exact historical input recovery

On 2026-10-03 UTC, all 30 calibration DICOM archives were recovered with exact equality to their original frozen SHA-256 digests. The source-pinned historical preflight artifact was independently retrieved and verified, and every registry digest agreed with that original record. A bounded ZIP timestamp search changed no member bytes and accepted only complete-archive digest equality. The unchanged input guard remains before decoding and registration.

See `research/M6_INPUT_RECOVERY_RESULT.json` and `docs/m6_phase_a_input_recovery.md`. No evaluation input or numerical calibration output was inspected. The input registry, statistical design, geometry, and scientific rules remain unchanged.

The exact-recovery implementation and a separate uniform request were merged in PRs 42 and 43. Run `37093645674` then encountered multiple anatomy failures; sampled operational failures were image-download timeouts. This attempt is incomplete and remains ineligible for aggregation. Partial numerical calibration outputs were not inspected to choose the next repair.

The workflow-local staging implementation was merged in PR 44 and passed merged-source CI run `37114568122` at source `59dddf5c045b75fe9ad3bb84866ae4bdc27ce30c`. PR 45 separately pinned that source and authorized a fresh uniform run of all 30 calibration anatomies. Run `37114827455` passed source authorization, frozen-registry validation, and pre-result tests. All 30 original archives were staged with exact frozen SHA-256 equality and zero unresolved inputs before anatomy computation began.

Run `37114827455` completed successfully. All 30 primary calibration anatomies are complete. The final artifact SHA-256, 33 manifest entries, five frozen blob pins, all input/geometry identities, numeric vector hashes, and complete-method ratio scores were verified. The aggregate replay is byte-identical, and its thresholds were independently recomputed with exact order statistics. See `research/M6_PHASE_A_RESULT.json`, `research/M6_PHASE_A_THRESHOLD_SEAL.json`, and `docs/m6_phase_a_calibration_result.md`. All four prior incomplete attempts remain ineligible. At that Phase A checkpoint, evaluation remained sealed.

Primary 90% sigma multipliers are **41.956170528034775** for `prostate_3t` and **52.08147866494837** for `prostate_diagnosis`. The 95% sentinel is positive infinity by the frozen K=15 rule. These are fitted calibration multipliers, not held-out coverage results.

ICE completed in 29 of 30 anatomies. `Prostate3T-01-0013` retains three reverse-member overlap failures; primary forward registration is complete. Under the frozen failure policy, ICE calibration is unassessable for `prostate_3t`, while `prostate_diagnosis` ICE calibration is assessable. No failed anatomy was dropped, rerun, or reinitialized.

Phase A is allowed to run the frozen forward estimator and reverse ICE comparator, compute the predeclared calibration scores, and fit source-specific HCP thresholds. It must not run any of the 30 evaluation anatomies.

The complete Phase A artifact has been reviewed and its exact thresholds sealed. Phase B implementation was merged in PR 48 at `ee4034c58435ded3e2f9c283e38fa70d78f1d792` and passed merged-source CI `37122250493` with 242 tests. The separate `research/M6_PHASE_B_REQUEST.json` pins that implementation, all scientific identities, the exact threshold seal, and the calibration-matched numerical runtime. It authorizes only the 30 frozen evaluation anatomies, with no threshold refitting or scientific configuration change. Execution and input-staging status is recorded in `research/M6_PHASE_B_EXECUTION_STATUS.json`. The complete evaluation aggregate has now passed independent verification and byte-identical replay. Primary 90% empirical coverage is 97.73% (3T) and 99.73% (Diagnosis), with median anatomy radii 3.93/4.36 mm. The retained Diagnosis outlier has a 70.69 mm median radius. The 95% radii are infinite. ICE completes in 29/30 evaluation anatomies; neither source supports a full-cohort calibrated ICE comparison.

The M4 estimator, M5 failure record, M6 split, ROI rule, deformation rule, score definition, zero-signal rule, and failure policy must not be changed in response to Phase A outcomes.

## Not established

TrueMargin does not currently establish:

- exact nominal calibration or unconditional probabilistic coverage beyond the frozen hierarchical assumptions;
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


## Completed M6 Phase B execution checkpoint

Run `37122716790` at execution commit `fd1070b1250e276ef0d17edc2d85622cb1e7a585` passed source authorization and pre-result tests. Its staging job verified all 30 evaluation DICOM archives against their original frozen SHA-256 digests, with zero unresolved inputs, and verified all 30 evaluation labels. The complete aggregate has been reviewed: 31 manifest entries, six frozen blob pins, all 30 JSON shards and all 30 numerical checkpoints agree, and source aggregation replays byte for byte. See `research/M6_PHASE_B_RESULT.json`, `research/M6_PHASE_B_EXECUTION_STATUS.json` and [the workflow](https://github.com/Kushrishi/truemargin/actions/runs/37122716790). The post-result contribution review recommends a bounded technical report before any new experiment; see `docs/m4_m6_contribution_review.md`.

## Post-result contribution decision

The October 3 review does not justify a new-method or method-superiority manuscript. A separately labeled, post-outcome constant-radius check finds no demonstrated adaptive-efficiency advantage: at nominal 90%, constant radii 2.21/2.84 mm cover 93.73%/95.20%, while sigma mean radii are 2.11/3.62 times larger with higher coverage. This is not a coverage-matched or confirmatory comparison. All primary M6 thresholds and results remain unchanged.

The concise M4–M6 technical report and four evidence panels are complete in `docs/technical_report.md`. Prioritize the bounded C++ inference/replay application next. M7 remains unfrozen and unexecuted. A future extension needs a distinct scientific claim and a decisive test, not an effort to improve already-observed outcomes. See `docs/m4_m6_contribution_review.md` and `results/m6_exploratory/constant_radius_comparison.json`.

## Retained-evidence failure analysis

The October 3 post-outcome diagnostic audit covers all 60 M6 primary anatomies without new registration, threshold refitting or exclusions. All 31 Diagnosis calibration scores at or above the sealed 90% cutoff belong to `ProstateDx-01-0082`, whose median spread is 0.01182 mm and median error is 0.75995 mm. The evaluation radius tail is a different behavior: `ProstateDx-01-0043` has a within-case rank correlation of 0.97455 but a mean calibrated radius of 79.46 mm, contributing 51.62% of the source radius sum.

The analysis checks retained vector digests and geometry identities, but missing member-level and optimizer records prevent identifying the mechanism. This is descriptive evidence, not a new confirmatory endpoint or a reason to delete either anatomy. The bounded diagnostic note is complete; M7 remains unexecuted. A fresh utility study is conditional on a distinct question and prospective design. See [the note](../docs/m6_failure_diagnostics.md) and `results/m6_exploratory/failure_diagnostics.json`.
