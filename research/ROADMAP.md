# Research roadmap

**Updated:** 2026-10-01  
**Active program:** known-ground-truth registration-uncertainty evaluation  
**Target:** a defensible comparative study of when local registration-uncertainty or quality
surrogates are informative about true local spatial error

Frozen protocols and amendments remain authoritative for result-defining choices. This roadmap
defines project-level milestones only.

## M1 — Curated public research surface

**State:** complete

The public research question, claims, decision history, related work, protocol identities,
implementation, and CI surface are separated from legacy product/manuscript history.

## M2 — Geometry-only preflight

**State:** complete — amended full preflight passed 30 / 30

The frozen synthetic geometry/provenance preflight passed across ten held-out anatomies before
estimator registration. This established geometry only, not uncertainty informativeness.

## M3 — Comparator protocol freeze

**State:** complete

The prospectively frozen direct local set is:

1. nine-member hyperparameter-ensemble sigma;
2. ensemble-mean inverse-consistency error;
3. same-modality absolute post-registration residual;
4. ensemble-mean Jacobian deviation `abs(J - 1)`.

Contrastive Discrepancy was audited and excluded from the confirmatory study because the authors'
released snapshot could not be retrieved reproducibly from clean hosted runners. No bespoke
analogue was substituted.

The direct-comparator primitives, method-specific failure handling, anatomy aggregation,
multiplicity treatment, paired bootstrap summaries, orchestration, and result-bearing
authorization guard were frozen before outcomes. The result-bearing budget was 540 registrations.

## M4 — Primary known-ground-truth experiment

**State:** complete — primary pointwise informativeness result positive within the frozen study

Frozen design:

- 10 held-out anatomies;
- 3 deformation replicates per anatomy;
- 30 cases;
- 9 hyperparameter-ensemble registrations per case;
- 270 forward + 270 reverse registrations;
- 50 frozen fixed-domain ROI locations per case;
- per-case Spearman association between uncertainty and known error;
- anatomy-level aggregation;
- exact one-sided anatomy sign test;
- 10,000-replicate anatomy bootstrap interval.

Primary result:

- 30 / 30 primary cases complete;
- 10 / 10 anatomy-level associations positive;
- median anatomy Spearman = **0.6841**;
- anatomy-bootstrap 95% interval = **[0.3048, 0.8284]**;
- exact one-sided anatomy sign-test **p = 0.0009766**.

Comparator context:

- ICE median anatomy Spearman = **0.7203**;
- residual = **0.2851**;
- Jacobian deviation = **0.1689**.

Paired target-minus-comparator bootstrap intervals were positive for residual and Jacobian
deviation, but the target-minus-ICE interval crossed zero. M4 therefore supports pointwise rank
informativeness of the promoted sigma but does not establish superiority over ICE.

No completed M4 statistic, anatomy, seed, estimator member, ROI rule, comparator definition, or
case may be retuned after observing the result.

## M5 — Informativeness, comparator, and blind-spot analysis

**State:** complete

M5 used only the frozen M4 canonical and shard artifacts. No registration was rerun and no new
confirmatory winner statistic was introduced.

Completed outputs:

- all 1,500 frozen pointwise ROI observations recovered;
- exact M4 case metrics reconstructed from shard checkpoints and cross-checked against the
  canonical case table;
- 24 / 30 positive and 6 / 30 negative deformation-specific sigma/error rank associations;
- 39 / 1,500 target-sigma blind-spot points under the frozen rule, across 11 / 30 cases;
- persistent weak behavior identified for `aaa0069`;
- severe replicate-specific inversion preserved for `aaa0053` replicate 1;
- ICE/residual method-invalid cases retained rather than imputed;
- anatomy-aware target/comparator tables and reproducible figure generation produced;
- strong ICE performance retained as a contribution-boundary constraint.

M5 narrows the interpretation to positive but heterogeneous rank informativeness with real
high-error/low-sigma failures. It does not establish numerical calibration, signal complementarity,
or method superiority over ICE.

## M6 — Calibration

**State:** active — protocol design only; no result-bearing calibration run authorized

Calibration remains separate from informativeness.

Before execution, freeze:

- the quantity to be calibrated and its units/interpretation;
- fitting versus evaluation data separation;
- coverage/calibration metrics and tolerances;
- any transformation from ensemble spread to predicted error scale;
- failure handling and abstention;
- rerun policy and inference boundary.

Good pointwise ranking must not be presented as numerical calibration, and good marginal
calibration would not by itself prove useful local ranking.

## M7 — Robustness and generalization

**State:** downstream; contingent on M6 and a prospective protocol

Prospectively freeze a small number of scientifically justified stress axes, potentially including
deformation magnitude, spatial extent, image degradation, texture-poor regions, or optimizer
instability.

Do not add stress regimes because they produce favorable rankings. External-dataset
generalization is a separate claim and requires a genuinely independent substrate.

## M8 — Paper and reproducibility release

**State:** contingent on evidence

Deliverables:

- final related-work and contribution audit;
- frozen claims ledger;
- comparator protocol and exact implementation identities;
- anatomy-aware figures/tables;
- blind-spot and failure-case analysis;
- calibration result if M6 supports one;
- reproduction instructions and data-acquisition provenance;
- manuscript/preprint;
- tagged public release.

## Stop / narrow rules

Narrow the paper claim rather than tune around unfavorable evidence if:

- calibration does not support an interpretable numerical claim;
- the strong ICE comparator makes a proposed method-superiority framing unsupported;
- a faithful broader comparator suite would require changing the scientific problem;
- robustness testing does not preserve the bounded informativeness claim; or
- contemporary work closes the intended contribution gap.

The completed positive M4 result is not a reason to widen claims beyond the frozen study, and M5
failures are part of the result rather than defects to tune away.

## Repository roles

`Kushrishi/truemargin` is the active scientific source of truth.

The private `Kushrishi/truemargin-lab` repository is historical provenance only and must not resume
active result-bearing development.

Website, GitHub profile, CV, and LinkedIn wording may summarize only completed milestones and must
not exceed `research/CLAIMS.md`.
