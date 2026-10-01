# Related work and contribution boundary

**Updated:** 2026-09-25  
**Status:** comparator boundary and implementation feasibility decisions frozen

The broad problem of medical image-registration uncertainty is mature. TrueMargin
must not claim novelty for uncertainty estimation, perturbation ensembles,
hyperparameter ensembles, calibration, inverse consistency, or test-time
quality estimation in isolation.

The current research opportunity is narrower:

> **Evaluate when local registration-uncertainty/quality surrogates actually
> contain information about known spatial registration error, and characterize
> calibration and blind spots separately under controlled deformation regimes.**

That is a working contribution boundary, not a novelty claim.

## Closest current work

| Work | Signal / method | Ground-truth relationship | Main relevance to TrueMargin |
| --- | --- | --- | --- |
| Meyer et al., *Deformable Image Registration Uncertainty-Encompassing Dose Accumulation for Adaptive Radiation Therapy* (2025) | Hyperparameter-perturbation ensemble of DVFs; voxelwise uncertainty ellipsoids | Clinical cohort lacks true DVF; paper explicitly distinguishes uncertainty from error | Direct evidence that hyperparameter perturbation is not novel. TrueMargin must test whether such variability is actually informative about known error. |
| Van der Heyden et al., *Inverse consistency error for validating deformable image registration* (2026) | Voxelwise inverse-consistency error | Computational phantoms with known deformation; reported strong GT error association and a failure mode for large homogeneous deformation | Strong comparator and proof that known-GT spatial validation can reveal both usefulness and blind spots. |
| Gheiji et al., *CONReg* (2026) | Quantile regression + conformal prediction for voxel/case uncertainty | Empirical coverage 0.92-0.98; uncertain groups had higher registration error | Calibration and informativeness are both already active research targets; TrueMargin cannot frame either as unexplored. |
| Tian, Hu & Iglesias, *Test-time Uncertainty Estimation ... via Transformation Equivariance* (2025/2026 preprint) | Transformation-equivariance discrepancy for pretrained registration models | Reports uncertainty/error correlation across models/anatomies | Important model-agnostic comparator concept; uncertainty can be estimated from transformation consistency rather than retraining an uncertainty model. |
| Li et al., *Contrastive Discrepancy* (Medical Image Analysis, 2026) | Label-free deformation-field discrepancy based on bias/variance and transformation groups | Performance curve reported to mirror gold-standard TRE across multiple model families/datasets | Very close to the broader question of whether a label-free registration signal tracks true error and supports hyperparameter selection. |
| Chen et al., medical image-registration survey (Medical Image Analysis, 2025) | Survey of modern registration, uncertainty, and evaluation | Review | Confirms uncertainty/evaluation is already a broad field; contribution must be specific and comparative. |
| Le Folgoc et al., sparse Bayesian registration uncertainty (TMI, 2017) | Bayesian posterior uncertainty | Evaluates approximate vs more exact posterior inference | Historical reminder that optimizer/model uncertainty has a substantial pre-deep-learning literature. |

## Consequences for the current rebuild

### Hyperparameter ensemble

The nine-member hyperparameter ensemble is **not** a novel uncertainty mechanism.

Its scientific value in TrueMargin is as a prospectively frozen candidate whose
operational variability can be separated from:

1. known-error informativeness;
2. calibration;
3. high-error / low-uncertainty blind spots; and
4. robustness to deformation/failure regime.

The current known-GT protocol remains useful because the 2025 clinical
hyperparameter-perturbation work explicitly notes that uncertainty does not
guarantee containment of the unknown true registration.

### Known-ground-truth evaluation

The current 30-case study should remain frozen and be run as specified once its
implementation/reproducibility checks are complete.

Do not modify its primary statistic, anatomy set, seeds, or nine-member
estimator based on comparator literature.

### Comparators

The paper-level comparator boundary is now prospectively frozen before any
result-bearing known-GT registration.

Direct local methods:

1. **hyperparameter-ensemble sigma** — frozen target method;
2. **inverse-consistency error (ICE)** — computed from forward/reverse
   nine-member ensemble means and evaluated against the same ensemble-mean
   known-error target;
3. **same-modality absolute post-registration residual** — intentionally simple
   local mismatch baseline for the synthetic T2 setting;
4. **Jacobian deviation `abs(J - 1)`** — deformation-plausibility baseline,
   explicitly not a probabilistic uncertainty estimate.

**Contrastive Discrepancy (CD)** is assigned conceptually to a separate
case-level model-selection axis rather than forced into the pointwise local
table. The peer-reviewed 2026 paper's authors link released code only through
snapshot `anonymous.4open.science/r/dbc-B401`. Before any primary outcome,
three clean-hosted retrieval checks were performed: the historical API route
returned HTTP 403, the current service files route returned HTTP 403, and
headless Chrome received only Cloudflare security verification. The public
paper metadata establishes CD's transformation-consistency/model-selection
role but does not pin the exact transformation parameters and aggregation
semantics needed for a faithful reproduction. CD is therefore prospectively
excluded from the current confirmatory study; no bespoke analogue is
substituted.

**Transformation-equivariance UQ** remains related-work-only in the
confirmatory classical study: the authors' current publication page still
lists it as an arXiv preprint and the demonstrated implementations use
pretrained deep registration models. A classical-optimizer adaptation would be
a new method rather than a clean baseline.

**CONReg** remains related-work-only because it requires a learned
quantile-registration model and conformal calibration pipeline.

Historical curvature is excluded unless a separate pre-result audit recovers a
complete stable definition.

## Paper-level evaluation axes

A strong TrueMargin study should avoid a single "best uncertainty method"
headline. Each method should be evaluated on distinct axes:

### Informativeness

- within-case Spearman association between surrogate uncertainty/quality and
  known spatial error;
- anatomy-level aggregation and uncertainty;
- high-error enrichment in the highest-uncertainty region.

### Blind spots

- frequency and severity of high-error / low-uncertainty locations;
- deformation regimes where the surrogate fails;
- operational failures and invalid registrations.

### Calibration

- empirical coverage only for methods that define a meaningful scale/interval;
- calibration performed as a separate stage from informativeness;
- no claim that good marginal coverage implies useful local ranking.

### Robustness

Potential controlled axes include:

- deformation magnitude;
- local versus spatially broad deformation;
- image noise / contrast degradation;
- texture-poor regions;
- optimizer instability;
- registration hyperparameter regime.

Do not add a stress axis merely because it produces a favorable result.

## Current contribution hypothesis

A defensible contribution may be:

> **A prospective, anatomy-aware stress-test framework for determining when
> registration uncertainty and label-free quality surrogates are informative
> about known local spatial error, separating rank informativeness, calibration,
> and blind-spot behavior.**

The paper should be narrowed or stopped if contemporary work already evaluates
the same comparator families under an equivalently controlled, multi-regime,
known-ground-truth design.

## Sources

Primary/review sources currently driving this boundary:

- Meyer et al. (2025), *Deformable Image Registration
  Uncertainty-Encompassing Dose Accumulation for Adaptive Radiation Therapy*,
  International Journal of Radiation Oncology, Biology, Physics,
  DOI 10.1016/j.ijrobp.2025.04.004.
- *Inverse consistency error for validating deformable image registration: an
  explorative study on computational phantoms* (2026), Physics and Imaging in
  Radiation Oncology, DOI 10.1016/j.phro.2026.100916.
- Gheiji et al. (2026), *CONReg: Uncertainty-Aware Medical Image Registration
  Using Conformal Prediction*, DOI 10.1007/s10278-026-01878-3.
- Tian, Hu & Iglesias (2025/2026), *Test-time Uncertainty Estimation for Medical
  Image Registration via Transformation Equivariance*, arXiv:2509.23355.
- Li et al. (2026), *Contrastive Discrepancy: A label-free metric for deformable
  image registration supporting testing-time hyperparameter selection*,
  Medical Image Analysis 113:104210, DOI 10.1016/j.media.2026.104210.
- Chen et al. (2025), *A survey on deep learning in medical image registration:
  New technologies, uncertainty, evaluation metrics, and beyond*, Medical Image
  Analysis 100:103385.
- Le Folgoc et al. (2017), *Quantifying Registration Uncertainty With Sparse
  Bayesian Modelling*, IEEE Transactions on Medical Imaging 36(2):607-617.

## Comparator-freeze conclusions

The literature audit resolved the pre-freeze questions as follows:

1. known-GT validation of individual local surrogates exists, including recent
   ICE work, but the current contribution remains a prospective same-case,
   anatomy-aware comparison of distinct surrogate semantics and blind spots;
2. transformation-equivariance UQ is not used as a direct classical comparator;
3. Contrastive Discrepancy is not included in the current confirmatory study
   because the linked released snapshot is not reproducibly retrievable from a
   clean hosted environment and the available public description is
   insufficient to reproduce exact scoring semantics without invention;
4. ICE is defined prospectively through forward/reverse ensemble-mean cycle
   error in physical coordinates;
5. the confirmatory local suite is intentionally small: target sigma, ICE,
   residual, and Jacobian deviation;
6. the direct-comparator implementation and authorization invariants are frozen
   and tested before any result-bearing registration.
