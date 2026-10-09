# Historical research status — 2 October 2026

This is a pre-result snapshot. For completed calibration results and current work,
read [Research status](STATE.md). The historical gate descriptions below do not
define the current execution state.

**Updated:** 2026-10-02  
**Active milestone:** M6 numerical calibration  
**Current gate:** Phase A calibration execution

## Completed evidence

M1 through M5 are complete and locked. M4 established positive but heterogeneous pointwise rank informativeness for the frozen hyperparameter-ensemble sigma under synthetic known deformation. M5 preserved blind spots and failure cases. ICE remains a strong comparator.

## M6 frozen state

The following pre-result gates are complete:

- the official 80-subject challenge identity audit;
- geometry eligibility for all 60 official training anatomies;
- zero StudyInstanceUID and SeriesInstanceUID overlap between the M4 cohort and the M6 challenge surface;
- a deterministic source-stratified split with 30 calibration and 30 evaluation anatomies;
- the source-specific HCP protocol with sigma primary and ICE secondary;
- a full 60-anatomy amended deformation preflight with zero failures;
- a durable registry of the exact 30 Phase A calibration SeriesInstanceUIDs and geometry hashes;
- tested implementation of the frozen hierarchical conformal primitives.

No M6 registration, sigma, ICE, conformal score, calibration threshold, or evaluation outcome had been observed when the Phase A execution implementation was prepared.

## Execution boundary

Phase A may run only after a separate source-pinned request is committed against a green implementation revision.

Phase A is limited to the 30 frozen calibration anatomies. It may run the frozen nine-member forward estimator and nine-member reverse ensemble, compute sigma and ICE calibration scores, and fit the predeclared source-specific 80%, 90%, and 95% HCP thresholds.

The 30 evaluation anatomies remain sealed. They require a separate authorization after the Phase A artifact and exact thresholds are reviewed and committed.

## Next actions

1. merge and CI-validate the Phase A execution implementation;
2. commit a source-pinned Phase A authorization request;
3. execute calibration-only CI and preserve the complete artifact;
4. review and seal the thresholds without modification;
5. authorize Phase B only if the frozen primary validity requirements are satisfied.

`M6_PHASE_A_IMPLEMENTATION=PRE_RESULT`

`M6_PHASE_A_RESULT_BEARING_AUTHORIZED=NO`

`M6_EVALUATION_AUTHORIZED=NO`
