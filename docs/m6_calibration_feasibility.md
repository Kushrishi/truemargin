# M6 calibration feasibility gate

**Date:** 2026-10-01  
**State:** design decision only  
**Result-bearing calibration authorized:** **no**

## Question

Can the promoted nine-member hyperparameter-ensemble spread be converted into a numerically interpretable local error radius without reusing the completed M4 cohort as a new tuning/evaluation set or treating spatially clustered ROI points as i.i.d. calibration observations?

## Why the existing cohort is insufficient for a confirmatory calibration claim

The current annotated Prostate Fused-MRI-Pathology substrate contains 15 HECaP-annotated anatomies used by the active research program:

- 5 frozen mechanism-promotion anatomies;
- 10 different frozen M4 known-ground-truth evaluation anatomies;
- 0 unused annotated anatomies.

The M4 evaluation outcomes have already been observed. They therefore cannot be relabeled as a previously unseen confirmatory calibration test set after M5.

The 5 promotion anatomies are also not an adequate standalone confirmatory split-conformal calibration cohort at the anatomy level. For ordinary split conformal at nominal 90% coverage, the finite-sample order statistic is `ceil((n + 1) * 0.90)`; with `n = 5` this is 6, so no finite calibration radius can supply that guarantee.

Most importantly, the 50 ROI points within a case are spatially dependent and multiple deformation realizations share the same anatomy. A confirmatory M6 analysis must not obtain an artificially large calibration sample by treating all pointwise observations as independent exchangeable units.

## Related-work boundary

Calibration itself is not a novelty claim.

- Gheiji et al., **CONReg: Uncertainty-Aware Medical Image Registration Using Conformal Prediction** (2026), DOI `10.1007/s10278-026-01878-3`, already applies conformal calibration to medical image registration and reports voxel- and case-level uncertainty intervals.
- Dunn, Wasserman, and Ramdas, **Distribution-Free Prediction Sets for Two-Layer Hierarchical Models** (JASA 2023), DOI `10.1080/01621459.2022.2060112`, addresses conformal prediction when observations are nested within exchangeable groups rather than i.i.d.

TrueMargin therefore must not claim to introduce conformal prediction for registration. A defensible contribution would be narrower: test whether a prospectively frozen registration-ensemble spread can support useful numerical error intervals while respecting anatomy-level dependence, and keep calibration separate from the already-established rank-informativeness and blind-spot results.

## Preferred independent substrate

The preferred feasibility target is the public **NCI-ISBI 2013 Challenge: Automated Segmentation of Prostate Structures** data hosted by The Cancer Imaging Archive.

Relevant properties:

- 60 training subjects with axial T2-weighted prostate MRI;
- central-gland and peripheral-zone expert outlines suitable for defining a prostate ROI;
- source data drawn from 1.5 T and 3 T acquisitions;
- CC BY 3.0;
- data DOI `10.7937/K9/TCIA.2015.zF0vlOPv`.

This substrate is independent of the current Prostate Fused-MRI-Pathology cohort and is large enough to create calibration, confirmatory evaluation, and future-reserve anatomy sets before any result-bearing registration.

## Candidate M6 architecture

This is a feasibility design, **not yet a frozen protocol**.

### Unit of independence

The primary exchangeability unit should be the **anatomy**, not the ROI point.

Any conformal procedure must explicitly account for points nested within anatomies. The current `conformal_radius()` helper in `src/truemargin/calibration.py` is a generic i.i.d./exchangeable-score primitive and is **not authorized** as the confirmatory M6 method by itself.

### Prospective cohort roles

Subject to a clean metadata/geometry-only feasibility audit, a candidate split is:

- 20 anatomies: calibration;
- 20 anatomies: confirmatory evaluation;
- 20 anatomies: untouched reserve for later robustness/generalization work.

Assignment must be deterministic and frozen before registration outcomes. Eligibility and replacement rules must also be frozen before any estimator execution.

### Registration and estimator

To avoid turning M6 into estimator redevelopment:

- retain the M4 registration regime;
- retain the exact nine-member hyperparameter ensemble;
- retain the known-deformation generator unless a geometry-only audit establishes a necessary dataset-specific amendment;
- do not tune ensemble members, optimizer settings, or deformation parameters from calibration outcomes.

A single prospectively generated deformation realization per anatomy is preferred for the first confirmatory calibration design because it yields a clean two-level structure: anatomy -> sampled spatial locations. Additional within-anatomy deformation replicates would introduce another dependence layer and require a correspondingly more complex inferential design.

### Spatial sampling

Use a prostate ROI derived prospectively from the supplied zone segmentations. The exact union/resampling rule, landmark margin, number of sampled locations, and deterministic seed construction must be frozen before registration.

The existing M4 value of 50 sampled ROI locations per anatomy is a reasonable starting point for comparability, but M6 must freeze it independently rather than inherit it implicitly.

### Calibration target

The target quantity is the true local **error magnitude in millimetres**, not a probability attached directly to ensemble sigma.

A candidate nonconformity score is

`known_error_mm / ensemble_sigma_mm`.

Near-zero sigma cannot be silently discarded to improve coverage. M6 must prospectively choose one of two explicit semantics:

1. include degenerate/near-degenerate sigma values, allowing the calibration radius to become very large or infinite when warranted; or
2. define a deterministic abstention rule and make every coverage claim conditional on non-abstention while reporting the abstention rate and failure locations separately.

The first option is preferable as the primary analysis because it does not remove precisely the low-sigma/high-error failures M5 identified.

### Candidate coverage levels

A narrow prespecified family is sufficient:

- primary: 90% nominal marginal coverage;
- secondary descriptive levels: 80% and 95%.

No coverage level should be selected after seeing evaluation results.

### Required outputs

A confirmatory M6 result should report at least:

- empirical coverage on held-out anatomies, weighted equally by anatomy;
- distribution of per-anatomy coverage rather than only pooled point coverage;
- interval/radius efficiency in millimetres;
- zero/near-zero-sigma behavior;
- failures and abstentions, if any;
- uncalibrated reference coverage using the predeclared raw-sigma mapping;
- calibration/evaluation cohort identities and source hashes.

Coverage and informativeness must remain separate. A calibrated interval can be uninformative if it is excessively wide, and strong rank informativeness does not imply calibrated numerical scale.

## Stop rules before a result-bearing protocol

Do not authorize M6 result-bearing registration if any of the following remain unresolved:

- the external image/segmentation identities cannot be acquired reproducibly;
- the prostate ROI cannot be constructed deterministically across the intended cohort;
- fewer than the predeclared number of independent anatomies pass geometry-only eligibility;
- the chosen conformal procedure does not match the nested data structure;
- calibration and evaluation roles are assigned after observing registration outcomes;
- a proposed sigma exclusion/abstention rule is selected after viewing coverage;
- the method would require changing the frozen estimator based on calibration results.

## Next authorized work

Only the following work is authorized from this feasibility gate:

1. audit the external dataset acquisition and segmentation identities;
2. define anatomy-level eligibility and deterministic split rules;
3. audit the exact hierarchical conformal method and its finite-sample assumptions;
4. clean legacy calibration-module documentation so generic helper functions are not mistaken for an already validated M6 method;
5. write and review a prospective M6 protocol.

**No M6 result-bearing registration or calibration fit is authorized by this document.**
