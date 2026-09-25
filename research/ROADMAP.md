# Research roadmap

**Updated:** 2026-09-25  
**Active program:** known-ground-truth registration-uncertainty evaluation  
**Target:** a defensible comparative study of when local registration-uncertainty
or quality surrogates are informative about true local spatial error

Frozen protocols and amendments remain authoritative for result-defining
choices. This roadmap defines project-level milestones only.

## M1 — Curated public research surface

**State:** complete

Completed requirements:

- public repository separated from legacy product/manuscript history;
- current research question, claims, decisions, and related work recorded;
- known-ground-truth protocol + pre-result Amendment 1 preserved;
- public protocol contents self-verifying against immutable Git blob identity;
- current implementation aligned;
- Ruff, Black, mypy, and the full test suite green.

## M2 — Geometry-only preflight

**State:** complete — amended full preflight passed 30 / 30 and reviewed evidence is preserved

Goal: validate the frozen 30 synthetic cases before any estimator registration.

Required checks:

- all 10 held-out anatomies resolve to the frozen T2 series;
- required HECaP masks resolve with recorded provenance;
- 3 deformation replicates exist per anatomy;
- transform direction matches the frozen protocol;
- warped fixed-domain ROI is valid;
- exactly 50 unique eligible points are sampled per case;
- sampled points remain in the intended source/fixed domain;
- no prohibited folding or invalid geometry occurs;
- acquisition and geometry evidence are preserved and reviewed.

This milestone authorizes geometry only. It does not authorize any of the 270
planned estimator registrations.

## M3 — Comparator protocol freeze

**State:** protocol frozen; implementation and CD feasibility preflight active

Goal: define and implement the paper-level comparator set before comparator outcomes or the
primary known-GT outcome can influence method selection.

Frozen direct local set:

1. the frozen nine-member hyperparameter-ensemble sigma target;
2. ensemble-mean inverse-consistency error;
3. same-modality absolute post-registration residual;
4. ensemble-mean Jacobian deviation `abs(J - 1)`.

Contrastive Discrepancy is frozen as a separate case-level model-selection
comparator only if a non-result-bearing audit can reproduce its released method
faithfully. Transformation-equivariance UQ and CONReg remain related work rather
than forced direct baselines because their demonstrated model/training setting
does not match the classical B-spline study.

M3 completes only when implementation identities, tests, and the CD feasibility
decision are pinned before result-bearing execution.

## M4 — Primary known-ground-truth experiment

**State:** unauthorized

Frozen primary design:

- 10 held-out anatomies;
- 3 deformation replicates per anatomy;
- 30 cases;
- 9 hyperparameter-ensemble registrations per case;
- 270 total planned registrations;
- 50 frozen fixed-domain ROI locations per case;
- per-case Spearman association between local uncertainty and known error;
- anatomy-level aggregation;
- exact one-sided anatomy-level sign test;
- 10,000-replicate anatomy bootstrap interval.

Authorization requires the reviewed M2 geometry record, completed M3 comparator
implementation preflight, exact protocol/implementation identities, and final
registration budget to be pinned by a separate run request. No primary
statistic, anatomy, seed, estimator, ROI rule, or comparator definition may be
retuned after observing the result.

## M5 — Informativeness and blind-spot comparison

**State:** contingent on M3-M4

Evaluate methods on distinct questions rather than a single winner score:

- local rank informativeness;
- high-error enrichment at high reported uncertainty/quality;
- frequency and severity of high-error / low-uncertainty blind spots;
- operational failures and invalid registrations;
- anatomy-level variability.

Negative comparator results remain part of the study.

## M6 — Calibration

**State:** downstream

Calibration is evaluated separately from informativeness.

Only methods with a meaningful uncertainty scale or interval may make a
coverage/calibration claim. Good marginal calibration must not be presented as
proof of useful pointwise ranking.

## M7 — Robustness and generalization

**State:** contingent on earlier evidence

Prospectively freeze a small number of scientifically justified stress axes,
potentially including deformation magnitude, spatial extent, image degradation,
texture-poor regions, or optimizer instability.

Do not add stress regimes because they produce favorable rankings.

External-dataset generalization is a separate claim and requires a genuinely
independent substrate.

## M8 — Paper and reproducibility release

**State:** contingent on evidence

Deliverables:

- final related-work and contribution audit;
- frozen claims ledger;
- comparator protocol and exact implementation identities;
- anatomy-aware figures/tables;
- blind-spot and failure-case analysis;
- reproduction instructions and data-acquisition provenance;
- manuscript/preprint;
- tagged public release.

## Stop rules

Narrow or stop the paper hypothesis rather than tune around failure if:

- the promoted hyperparameter ensemble is not meaningfully informative about
  known local error;
- comparator methods already dominate the intended contribution under the same
  controlled setting;
- a faithful comparator suite cannot be implemented without changing the
  scientific problem; or
- contemporary work already establishes the same controlled multi-method
  known-ground-truth result.

## Repository roles

`Kushrishi/truemargin` is the active scientific source of truth.

The private `Kushrishi/truemargin-lab` repository is historical provenance
only and must not resume active result-bearing development.

Website, GitHub profile, CV, and LinkedIn wording may summarize only completed
milestones and must not exceed `research/CLAIMS.md`.
