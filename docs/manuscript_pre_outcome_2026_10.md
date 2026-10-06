# Local registration variability versus local spatial error

**Pre-outcome manuscript skeleton, 2026-10-06. Not a submission or publication.**
External outcome fields are intentionally blank. The controlled evidence below is accepted prior evidence, not a new result. See the frozen protocols and claims ledger for exact identities and eligibility rules.

## Abstract structure

- Question: when does local registration variability rank true local spatial error, and which errors does it miss?
- Design: fixed nine-member hyperparameter ensemble; controlled known-deformation evaluation; prospective independent lung landmark study if operationally feasible.
- Controlled evidence: anatomy-aware association, direct comparators, deformation-specific blind spots and separate numerical-bound evaluation.
- External study: **[NOT RUN; outcome placeholder]**.
- Conclusion: **[TO BE WRITTEN ONLY AFTER THE PROSPECTIVE GATE/OUTCOME]**.

## Introduction

Registration QA needs signals about error without access to a true dense displacement field. Variation across optimizer configurations is not automatically spatial error, and a high aggregate association can conceal systematic missed errors. Ranking, numerical coverage and operational reliability are separate properties.

Hyperparameter ensembles, probabilistic registration, inverse consistency and conformal calibration all have substantial prior work. The contribution boundary is an empirical test of one fixed operational signal under explicit evaluation units and failure retention, not a new registration algorithm or uncertainty theorem. The [October review](external_prior_work_2026_10.md) distinguishes the proposed transfer question from CONReg, PULPo, ICE and prior ensemble work.

## Methods

### Frozen estimator

Nine B-spline members: mesh 3, maximum 15 iterations, no centering; mutual-information bins {32,50,64} crossed with gradient tolerances {1e-4,1e-5,1e-6}. All nine members are required. Preserve the exact executed implementation and protocol; do not change intensity handling, mesh, iterations or cropping to improve external feasibility.

### Controlled known-deformation study

Ten held-out anatomies, thirty deformation cases, fixed spatial sampling and prospective comparator definitions. Summarize at anatomy level, not as 1,500 independent landmark trials. Refer to accepted protocol amendments for geometry, budget and retained failures.

### Comparators

Inverse-consistency error requires the corresponding reverse registrations. Same-modality residual and Jacobian deviation have frozen definitions. Keep method-specific invalid outputs rather than selecting complete favorable cases. Rank association is not proof of a calibrated error radius.

### External study

Expiration is fixed, inspiration moving. Official preprocessed Learn2Reg lung archives, exact case identities and checksums must be verified. Training-only geometry and unchanged-estimator feasibility precede manual test landmark access. Test identifiers, coordinate conversion/interpolation, statistical endpoints and code/environment identities must be frozen before that access.

Primary unit: lung pair/case. Primary endpoint: median of ten case-level Spearman associations, positive-case count, exact one-sided sign test, 10,000-replicate case bootstrap for the median. Comparators use the same case statistic and paired differences. No new numerical-radius calibration on the ten test pairs.

### Failure characterization

Retain high-error/low-score locations using the frozen within-case quartile rule. Separate operational failure, undefined association, invalid comparator and substantive negative association. Report affected cases and counts; do not remove blind spots for a clean headline.

## Results

### Accepted controlled evidence

Median anatomy-level Spearman is 0.6841, positive in 10/10 anatomies, anatomy-bootstrap interval [0.3048,0.8284]. ICE median is 0.7203; paired spread-minus-ICE interval [-0.0903,0.0736] does not establish superiority. Six deformation cases have negative spread/error association; 39 blind-spot points occur across 11 cases and seven anatomies.

The separate held-out synthetic bound study retains conservative 90% coverage (97.73% / 99.73%), large multipliers and a 70.69 mm anatomy median-radius outlier. Its 95% bound is infinite at the frozen finite-sample hierarchy. Incomplete ICE calibration/evaluation prevents the planned full-cohort calibrated comparison. These are limitations, not successful precision claims.

### External outcomes

**[EMPTY: no test-landmark outcome accessed in this session]**

Tables to populate only after a valid frozen run: per-case association/member status; primary aggregate; paired comparators with failures; blind-spot counts/cases; runtime and memory.

## Discussion structure

- What transfers: **[outcome-dependent]**.
- What fails: **[outcome-dependent; retain operational failures too]**.
- Comparator interpretation: informative spread need not outperform ICE.
- Limits: estimator/domain specificity, sparse manual landmarks, case hierarchy, uncertainty/error distinction, no clinical validation.
- Practical meaning: a QA signal can support investigation without certifying alignment or providing a useful numerical error bound.

## Publication decision

No venue or submission is selected. After an external result or a documented pre-outcome operational failure, assess whether the bounded empirical/failure conclusion warrants a short paper, workshop artifact, technical report or research-software release. A second dataset is not automatic.
