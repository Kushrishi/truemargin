# Research roadmap

**Updated:** 2026-10-01  
**Active program:** known-ground-truth registration-uncertainty evaluation  
**Target:** a defensible comparative study of when local registration-uncertainty or quality surrogates are informative about true local spatial error

Frozen protocols and amendments remain authoritative for result-defining choices. This roadmap defines project-level milestones only.

## M1 — Curated public research surface

**State:** complete

Completed requirements:

- public repository separated from legacy product/manuscript history;
- current research question, claims, decisions, and related work recorded;
- known-ground-truth protocol and pre-result amendments preserved;
- public protocol contents self-verifying against immutable Git blob identity;
- current implementation aligned;
- Ruff, Black, mypy, and the full test suite green.

## M2 — Geometry-only preflight

**State:** complete — amended full preflight passed 30 / 30 and reviewed evidence is preserved

The frozen 30 synthetic cases across ten held-out anatomies passed the amended geometry/provenance preflight before estimator registration.

This milestone validated geometry only and did not establish uncertainty informativeness.

## M3 — Comparator protocol freeze

**State:** complete

The prospectively frozen direct local set is:

1. nine-member hyperparameter-ensemble sigma;
2. ensemble-mean inverse-consistency error;
3. same-modality absolute post-registration residual;
4. ensemble-mean Jacobian deviation `abs(J - 1)`.

Contrastive Discrepancy was prospectively audited and excluded from the current confirmatory study because the authors' released code snapshot could not be retrieved reproducibly from clean hosted runners. No bespoke analogue was substituted.

The direct-comparator primitives, method-specific failure handling, anatomy aggregation, multiplicity handling for secondary sign tests, paired bootstrap summaries, execution orchestration, and result-bearing authorization guard were implemented before outcomes. The frozen result-bearing budget was 540 registrations.

## M4 — Primary known-ground-truth experiment

**State:** complete — primary pointwise informativeness result positive within the frozen study

The source-pinned result-bearing workflow completed on 2026-09-26.

Frozen design:

- 10 held-out anatomies;
- 3 deformation replicates per anatomy;
- 30 cases;
- 9 hyperparameter-ensemble registrations per case;
- 270 forward registrations;
- 270 reverse registrations for the ICE comparator;
- 50 frozen fixed-domain ROI locations per case;
- per-case Spearman association between uncertainty and known error;
- anatomy-level aggregation;
- exact one-sided anatomy-level sign test;
- 10,000-replicate anatomy bootstrap interval.

Primary result:

- 30 / 30 primary cases complete;
- 10 / 10 anatomy-level associations positive;
- median anatomy Spearman = **0.6841**;
- anatomy-bootstrap 95% interval = **[0.3048, 0.8284]**;
- exact one-sided anatomy sign-test **p = 0.0009766**;
- median anatomy blind-spot rate = **0.0** under the frozen definition.

Comparator context:

- ICE median anatomy Spearman = **0.7203**;
- residual = **0.2851**;
- Jacobian deviation = **0.1689**.

Paired target-minus-comparator bootstrap intervals were positive for residual and Jacobian deviation, but the target-minus-ICE interval crossed zero. M4 therefore supports pointwise rank informativeness of the promoted sigma but does not establish superiority over ICE.

Durable records:

- `docs/hyperparameter_known_gt_result.md`;
- `research/KNOWN_GT_M4_RESULT.json`.

No completed M4 statistic, anatomy, seed, estimator member, ROI rule, comparator definition, or case may be retuned after observing the result.

## M5 — Informativeness, comparator, and blind-spot analysis

**State:** active

Goal: turn the completed M4 outputs into paper-level interpretation without introducing a post-hoc winner metric.

Required work:

- preserve method-specific invalid cases and operational failures;
- characterize high-error / low-reported-uncertainty blind spots by anatomy and case;
- produce anatomy-aware comparator figures and tables from frozen outputs;
- report high-vs-low uncertainty error enrichment separately from rank association;
- identify anatomies/regimes where the primary signal is weak;
- treat the strong ICE result as a contribution-boundary constraint rather than tuning around it.

Negative and null comparator findings remain part of the study.

## M6 — Calibration

**State:** downstream

Calibration is evaluated separately from informativeness.

Only methods with a meaningful uncertainty scale or interval may make a coverage/calibration claim. Good pointwise ranking must not be presented as numerical calibration, and good marginal calibration would not by itself prove useful ranking.

## M7 — Robustness and generalization

**State:** contingent on M5-M6

Prospectively freeze a small number of scientifically justified stress axes, potentially including deformation magnitude, spatial extent, image degradation, texture-poor regions, or optimizer instability.

Do not add stress regimes because they produce favorable rankings.

External-dataset generalization is a separate claim and requires a genuinely independent substrate.

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

## Stop / narrow rules

Narrow the paper claim rather than tune around unfavorable evidence if:

- M5 shows the apparent primary result is dominated by a small subset of anatomies or unacceptable blind spots;
- the strong ICE comparator makes a proposed method-superiority framing unsupported;
- a faithful broader comparator suite would require changing the scientific problem;
- robustness testing does not preserve the bounded informativeness claim; or
- contemporary work closes the intended contribution gap.

The completed positive M4 result is not a reason to widen claims beyond the frozen study.

## Repository roles

`Kushrishi/truemargin` is the active scientific source of truth.

The private `Kushrishi/truemargin-lab` repository is historical provenance only and must not resume active result-bearing development.

Website, GitHub profile, CV, and LinkedIn wording may summarize only completed milestones and must not exceed `research/CLAIMS.md`.
