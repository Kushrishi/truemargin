# Research roadmap

**Updated:** 2026-10-02  
**Active program:** known-ground-truth registration-uncertainty evaluation  
**Target:** a defensible comparative study of when local registration-uncertainty or quality surrogates are informative about true local spatial error

Frozen protocols, amendments, and result records remain authoritative for result-defining choices. This roadmap summarizes project-level state only.

## M1: Curated public research surface

**State:** complete

The public research question, claims, decision history, related work, protocol identities, implementation, and CI surface are separated from legacy product and manuscript history.

## M2: Geometry-only preflight

**State:** complete

The frozen synthetic geometry and provenance preflight passed across ten held-out anatomies before estimator registration. The amended full preflight completed 30 of 30 cases. This established geometry only, not uncertainty informativeness.

## M3: Comparator protocol freeze

**State:** complete

The frozen direct local comparator set is:

1. nine-member hyperparameter-ensemble sigma;
2. ensemble-mean inverse-consistency error;
3. same-modality absolute post-registration residual;
4. ensemble-mean Jacobian deviation `abs(J - 1)`.

Contrastive Discrepancy was audited and excluded from the confirmatory study because the authors' released snapshot could not be retrieved reproducibly from clean hosted runners. No bespoke analogue was substituted.

## M4: Primary known-ground-truth experiment

**State:** complete

The prospective study completed 30 of 30 cases across 10 held-out anatomies and 3 deformation replicates per anatomy.

Primary result:

- 10 of 10 anatomy-level associations were positive;
- median anatomy Spearman = **0.6841**;
- anatomy-bootstrap 95% interval = **[0.3048, 0.8284]**;
- exact one-sided anatomy sign-test **p = 0.0009766**.

Comparator context:

- ICE median anatomy Spearman = **0.7203**;
- residual = **0.2851**;
- Jacobian deviation = **0.1689**.

The target-minus-ICE bootstrap interval crossed zero, so M4 does not establish superiority over ICE.

## M5: Informativeness, comparator, and blind-spot analysis

**State:** complete

M5 used only frozen M4 artifacts. No registration was rerun and no new confirmatory winner statistic was introduced.

Key findings:

- all 1,500 frozen pointwise observations were recovered;
- 24 of 30 case-level sigma/error associations were positive and 6 of 30 were negative;
- 39 of 1,500 target-sigma blind-spot points were identified across 11 of 30 cases;
- persistent weak behavior was preserved for `aaa0069`;
- a severe replicate-specific inversion was preserved for `aaa0053` replicate 1;
- ICE remained a strong comparator.

M5 narrows the interpretation to positive but heterogeneous rank informativeness with real high-error, low-sigma failures.

## M6: Numerical calibration

**State:** active. Phase A execution has begun; incomplete attempts are preserved and input transport is being repaired.

The calibration design is prospectively frozen in `docs/m6_calibration_protocol.md`, `research/M6_PROTOCOL_FREEZE.json`, and `research/M6_SPLIT.json`.

Frozen design:

- 60 official NCI-ISBI training anatomies;
- 30 calibration anatomies and 30 sealed evaluation anatomies;
- 15 calibration and 15 evaluation anatomies within each source regime;
- one synthetic deformation per anatomy;
- 50 frozen ROI locations per anatomy;
- source-specific Hierarchical Conformal Prediction with anatomy as the group;
- primary signal: nine-member hyperparameter-ensemble sigma;
- secondary calibrated comparator: ensemble-mean ICE;
- primary nominal coverage: 90%;
- descriptive secondary level: 80%;
- 95% finite-sample sentinel retained even when the exact HCP threshold is infinite;
- no primary abstention rule;
- zero-signal handling frozen before outcomes.

Completed pre-result gates:

1. official 80-subject image and annotation identity audit completed;
2. all 60 training anatomies passed geometry eligibility;
3. M4-to-M6 DICOM identity audit found zero SeriesInstanceUID and zero StudyInstanceUID overlap;
4. deterministic source-stratified 30/30 calibration/evaluation split frozen;
5. full M6 calibration protocol frozen before estimator outcomes;
6. first deformation-only preflight preserved its four geometry failures;
7. a prospective physical-distance boundary amendment was applied uniformly to all 60 anatomies;
8. amended deformation-only preflight completed **60 of 60** anatomies with zero failures.

Phase A run `37065698410` is incomplete and ineligible for aggregation. Uniform rerun `37075119713` failed label staging before any anatomy job started. No complete Phase A thresholds have been established, and evaluation remains sealed. See the two Phase A diagnostic records.

### Next authorized operation

Validate the current-host official label transport amendment and main CI, then create a separate source-pinned Phase A request for a uniform execution of all 30 frozen calibration anatomies.

Phase A may run the frozen estimator and comparator, compute calibration scores, and fit the predeclared source-specific HCP thresholds. The 30 evaluation anatomies remain sealed until the Phase A artifact and exact thresholds are reviewed and committed under a separate evaluation authorization.

No threshold, split, ROI rule, deformation rule, score rule, estimator definition, or failure rule may change after Phase A outcomes are observed.

## M7: Robustness and generalization

**State:** downstream and contingent on M6

The 10 official leaderboard and 10 official test subjects remain untouched for a separately frozen robustness study. They belong to the same challenge and source collections and must not be described as an independent external-validation dataset.

Any broader external-generalization claim requires a genuinely independent substrate and a prospective protocol.

## M8: Paper and reproducibility release

**State:** contingent on evidence

Deliverables:

- final related-work and contribution audit;
- frozen claims ledger;
- exact protocol and implementation identities;
- anatomy-aware figures and tables;
- blind-spot and failure-case analysis;
- M6 calibration result if supported;
- reproduction instructions and acquisition provenance;
- manuscript or preprint;
- tagged public release.

## Stop and narrow rules

Narrow the paper claim rather than tune around unfavorable evidence if:

- M6 calibration does not support an interpretable numerical claim;
- ICE makes a method-superiority framing unsupported;
- a faithful broader comparator suite would require changing the scientific problem;
- robustness testing does not preserve the bounded informativeness claim; or
- contemporary work closes the intended contribution gap.

Negative or inefficient calibration is valid evidence. M4 and M5 must not be retuned to rescue M6.

## Repository roles

`Kushrishi/truemargin` is the active scientific source of truth.

The private `Kushrishi/truemargin-lab` repository is historical provenance only and must not resume active result-bearing development.

Website, GitHub profile, CV, and LinkedIn wording may summarize only completed evidence and must not exceed `research/CLAIMS.md`.
