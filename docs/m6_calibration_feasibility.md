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

Most importantly, the sampled ROI points within an anatomy are spatially dependent. A confirmatory M6 analysis must not obtain an artificially large calibration sample by treating pointwise observations as independent exchangeable units.

## Related-work boundary

Calibration itself is not a novelty claim.

- Gheiji et al., **CONReg: Uncertainty-Aware Medical Image Registration Using Conformal Prediction** (2026), DOI `10.1007/s10278-026-01878-3`, already applies conformal prediction to medical image registration.
- Dunn, Wasserman, and Ramdas, **Distribution-Free Prediction Sets for Two-Layer Hierarchical Models** (JASA 2023), DOI `10.1080/01621459.2022.2060112`, addresses conformal prediction when observations are nested within exchangeable groups rather than i.i.d.

TrueMargin therefore must not claim to introduce conformal prediction for registration. A defensible contribution is narrower: test whether a prospectively frozen registration-sensitivity signal can support useful numerical error intervals while respecting anatomy-level dependence, and keep calibration separate from the already-established rank-informativeness and blind-spot results.

## Preferred independent substrate

The preferred feasibility target is the public **NCI-ISBI 2013 Challenge: Automated Segmentation of Prostate Structures** data hosted by The Cancer Imaging Archive, DOI `10.7937/K9/TCIA.2015.zF0vlOPv`.

The official challenge surface contains **80 labeled subjects**:

- 60 training subjects;
- 10 leaderboard subjects;
- 10 test subjects.

For all three challenge partitions, TCIA currently exposes the corresponding source-image manifests and segmentation archives. The source images were drawn from **PROSTATE-DIAGNOSIS** and **Prostate-3T**, spanning materially different acquisition regimes: 1.5 T Philips Achieva imaging with an endorectal receiver coil and 3 T Siemens TIM imaging with a surface coil.

This challenge is a different TCIA analysis substrate from the Prostate Fused-MRI-Pathology collection used by M4. Before any paper-level wording calls it an external dataset, M6 must still verify that no patient or series identity overlaps the M4 substrate.

## Why the first identity audit must cover all 80 subjects

The earlier feasibility sketch considered only the 60 training subjects and proposed a provisional `20 / 20 / 20` calibration/evaluation/reserve split. That split is **not frozen** and should not be preserved merely because it was written first.

Because the official challenge additionally exposes 20 labeled leaderboard/test subjects, the first metadata-only feasibility audit should inventory the complete 80-subject surface before any M6 roles are assigned. The audit must preserve:

- official challenge partition identity;
- exact official image-series identity;
- exact segmentation identity and hashes;
- source collection;
- scanner/acquisition metadata needed to assess source balance;
- known TCIA correction/mismatch cases.

The audit must not assign calibration, evaluation, or reserve roles.

## Candidate M6 architecture

This remains a feasibility design, **not yet a frozen protocol**.

### Unit of independence

The primary exchangeability unit should be the **anatomy**, not the ROI point.

Any conformal procedure must explicitly match the nested structure of spatial locations within anatomies. The current `conformal_radius()` helper in `src/truemargin/calibration.py` is a generic exchangeable-score primitive and is **not authorized** as the confirmatory M6 method by itself.

The final protocol must state precisely what coverage guarantee is targeted. In particular, a marginal guarantee for a random location in a new exchangeable anatomy must not be described as simultaneous whole-volume coverage or guaranteed per-anatomy 90% coverage.

### Cohort roles remain provisional

Do **not** freeze a split until the complete 80-subject identity and geometry audit is reviewed and the exact hierarchical conformal method is selected.

Plausible designs to compare prospectively include:

- use all 60 official training subjects for M6 calibration and confirmatory evaluation, while preserving the 10 leaderboard and 10 test subjects untouched for M7 robustness;
- within the 60 training subjects, use a balanced `30 / 30` calibration/evaluation design if eligibility and the chosen method support it;
- retain a small training-side contingency/eligibility reserve only if the geometry audit shows that a deterministic replacement rule is genuinely necessary.

The official leaderboard/test partitions are a stronger prospective robustness reserve than an arbitrary training-side holdout, but they remain part of the same challenge and source collections. They must not be described as a separate external-dataset validation set.

### Source/acquisition balance

Any deterministic calibration/evaluation assignment must be frozen before registration outcomes and should be stratified by source/acquisition regime when possible. A purely hash-based split is not acceptable if it accidentally creates materially imbalanced 1.5 T versus 3 T cohorts.

The split design must therefore be based only on pre-outcome metadata such as:

- official partition;
- source collection;
- field strength;
- manufacturer/model;
- geometry/ROI eligibility.

No registration-error or uncertainty result may influence cohort assignment.

### Registration and estimator

To avoid turning M6 into estimator redevelopment:

- retain the M4 registration regime;
- retain the exact nine-member hyperparameter ensemble;
- retain the known-deformation generator unless a geometry-only audit establishes a necessary dataset-specific amendment;
- do not tune ensemble members, optimizer settings, or deformation parameters from calibration outcomes.

A single prospectively generated deformation realization per anatomy remains preferred for the first confirmatory calibration design because it yields a clean two-level structure: anatomy -> sampled spatial locations. Additional within-anatomy deformation replicates would introduce another dependence layer and require a correspondingly more complex inferential design.

### Spatial sampling

Use a prostate ROI derived prospectively from the supplied zone segmentations. The exact union/resampling rule, boundary margin, sampled-location count, and deterministic seed construction must be frozen before registration.

The M4 value of 50 sampled ROI locations per anatomy is a reasonable starting point for comparability, but M6 must freeze it independently rather than inherit it implicitly.

### Calibration target

The target quantity is true local **error magnitude in millimetres**, not a probability attached directly to ensemble sigma.

A candidate nonconformity score remains:

`known_error_mm / ensemble_sigma_mm`.

That ratio imposes a multiplicative, zero-intercept mapping from spread to error scale. If any alternative mapping is considered, the candidate family and model-selection rule must be frozen before confirmatory evaluation rather than chosen after seeing held-out coverage.

Near-zero sigma cannot be silently discarded to improve coverage. The primary preference remains to include such points, allowing the calibrated radius to become very large or infinite when warranted. Any abstention alternative must be prospectively defined, must report abstention rate and locations, and must make coverage claims explicitly conditional on non-abstention.

### Comparator calibration

M4 showed that inverse-consistency error (ICE) is a strong comparator and did not establish sigma superiority. Contemporary registration-validation literature also supports ICE as a serious error proxy.

Therefore the M6 protocol should, if computationally feasible, predeclare:

- **primary calibrated signal:** frozen TrueMargin ensemble sigma;
- **secondary calibrated comparator:** ICE, using the same calibration/evaluation cohort roles and reporting rules.

This comparison must be frozen before result-bearing execution. It is not authorized merely by this feasibility document. If reverse-registration cost makes ICE infeasible, that decision and rationale must be recorded prospectively rather than after seeing sigma results.

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
- the corresponding ICE-calibration result if prospectively authorized;
- an uncalibrated reference using the predeclared raw-signal mapping;
- calibration/evaluation cohort identities and source hashes;
- source/acquisition composition of each cohort.

Coverage and informativeness must remain separate. A calibrated interval can be uninformative if it is excessively wide, and strong rank informativeness does not imply calibrated numerical scale.

## Stop rules before a result-bearing protocol

Do not authorize M6 result-bearing registration if any of the following remain unresolved:

- the complete official image/segmentation identities cannot be acquired reproducibly;
- overlap with the prior M4 substrate has not been checked;
- the prostate ROI cannot be constructed deterministically across the intended cohort;
- fewer than the predeclared number of independent anatomies pass geometry-only eligibility;
- the chosen conformal procedure does not match the nested data structure;
- cohort roles are assigned after observing registration outcomes;
- source/acquisition imbalance is discovered after outcomes and then used to redesign the split;
- a proposed sigma exclusion/abstention rule is selected after viewing coverage;
- the method would require changing the frozen estimator based on calibration results.

## Next authorized work

Only the following work is authorized from this feasibility gate:

1. audit the complete 80-subject official challenge image/segmentation identity surface;
2. verify source/acquisition composition and prior-substrate identity non-overlap;
3. define anatomy-level geometry/ROI eligibility without running the estimator;
4. audit the exact hierarchical conformal method and finite-sample assumptions;
5. compare prospective cohort architectures using metadata and method constraints only;
6. decide prospectively whether ICE calibration is feasible as the secondary comparator;
7. write and review the frozen M6 protocol.

**No M6 result-bearing registration or calibration fit is authorized by this document.**
