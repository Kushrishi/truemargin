# Claims ledger

**Updated:** 2026-10-03

| Claim | Status | Current boundary |
| --- | --- | --- |
| Historical real-data zero-displacement values are verified pointwise registration ground truth. | **False** | They are a proxy/reference assumption and must be described as such. |
| The corrected relative-intensity perturbation ensemble passed its prospective promotion gate. | **False** | Gate A failed; no alpha was promoted. |
| The initialization-sensitivity ensemble passed its prospective promotion gate. | **False** | No nonzero initialization strength was promoted. |
| The mesh-3, 15-iteration regime passed the specified convergence gate. | **Supported** | Regime-specific prospective field-stability result; not universal convergence. |
| The nine-member registration-hyperparameter ensemble passed an operational promotion gate. | **Supported** | Complete in 5 of 5 promotion patients and non-inert in 4 of 5 under the frozen rule. |
| The M4 known-ground-truth cohort passed its frozen geometry-only preflight. | **Supported** | 30 of 30 amended cases passed under the frozen base protocol plus Amendments 1 and 2. |
| The paper-level direct comparator suite was frozen and implemented before M4 known-ground-truth outcomes. | **Supported** | Sigma, ICE, same-modality residual, and Jacobian deviation were pinned with method-specific validity and failure handling before result-bearing execution. |
| The promoted hyperparameter-ensemble sigma contains useful pointwise rank information about true local registration error in the frozen M4 study. | **Supported** | M4 completed 30 of 30 cases across 10 held-out anatomies. All 10 anatomy-level associations were positive; median anatomy Spearman = 0.6841, anatomy-bootstrap 95% interval [0.3048, 0.8284], exact one-sided sign-test p = 0.0009766. This is specific to the frozen synthetic known-deformation study. |
| The promoted sigma showed stronger anatomy-level rank informativeness than the same-modality residual and Jacobian-deviation comparators in the frozen M4 study. | **Supported** | Paired target-minus-comparator bootstrap intervals were [0.0188, 0.4757] versus residual and [0.1695, 0.7144] versus Jacobian deviation. This is not a universal method-ranking claim. |
| The promoted sigma is superior to inverse-consistency error. | **Unsupported** | ICE median anatomy Spearman was 0.7203 versus 0.6841 for sigma; paired target-minus-ICE bootstrap interval [-0.0903, 0.0736] crosses zero. |
| Every deformation-specific case has positive sigma/error rank association. | **False** | M5 reconstructed all frozen pointwise outputs: 24 of 30 case-level associations were positive and 6 of 30 were negative. |
| A zero median anatomy blind-spot rate proves the estimator never misses high-error locations. | **False** | M5 found 39 of 1,500 target-sigma blind-spot points, spanning 11 of 30 cases and 7 of 10 anatomies. |
| Sigma and ICE have identical pointwise failure sets. | **False** | In post-primary M5 characterization, only 12 of 39 sigma blind-spot points were also ICE blind spots. This does not establish complementarity or justify a combined method. |
| The official M6 challenge image and annotation identity surface has been resolved prospectively. | **Supported** | The completed M6 identity audit establishes exact official partition identities before any M6 estimator, split, calibration, or evaluation outcome. |
| All 60 official M6 training anatomies passed the prospective geometry-eligibility gate. | **Supported** | All 60 passed the frozen physical-space eligibility criteria before role assignment or estimator execution. |
| The M6 training substrate is disjoint from the M4 cohort at recorded DICOM identity level. | **Supported** | The frozen overlap audit found 0 SeriesInstanceUID overlaps and 0 StudyInstanceUID overlaps. This is an identity-level non-overlap statement, not proof of broader population independence. |
| The M6 calibration/evaluation split and calibration method were frozen before M6 estimator outcomes. | **Supported** | The frozen design uses 30 calibration and 30 sealed evaluation anatomies, stratified 15/15 within each source, with source-specific HCP, sigma as primary signal, and ICE as the secondary calibrated comparator. |
| The amended M6 deformation-only preflight completed the full frozen cohort. | **Supported** | The physical-distance boundary amendment was applied uniformly to all 60 anatomies. The source-pinned amended preflight completed 60 of 60 with zero failures and no registration, sigma, ICE, calibration, or evaluation outcome. |
| Source-specific M6 calibration thresholds have been fitted and sealed. | **Supported** | Phase A completed all 30 primary calibration anatomies; provenance and exact thresholds were verified. ICE is unassessable for 3T after one retained reverse-registration failure. |
| The promoted estimator achieves the nominal coverage on held-out anatomies. | **Untested** | Calibration fitting does not establish held-out coverage. Phase B evaluation remains unopened. |
| The M6 calibration protocol guarantees 90% coverage for every anatomy or every voxel. | **False** | The frozen target is source-specific marginal coverage for a randomly sampled eligible ROI location in a new exchangeable anatomy under the stated hierarchical assumptions. It is not simultaneous whole-volume, arbitrary-voxel, or per-anatomy guaranteed coverage. |
| The 20 official leaderboard/test subjects constitute an independent external-validation dataset. | **False** | They belong to the same challenge and source collections. They remain untouched for a separately frozen M7 robustness study. |
| The promoted estimator is clinically useful or clinically validated. | **Unsupported** | No clinical-performance study supports this claim. |
| TrueMargin is externally validated. | **False** | M4 and the current M6 design do not establish independent external-dataset validation. |
| Registration uncertainty generally predicts registration error. | **Unsupported** | The positive M4 result is conditional on one frozen estimator, registration regime, anatomy source, deformation design, and sampling rule. M5 also shows deformation-specific inversions. |
| TrueMargin has a completed paper, preprint, or peer-reviewed publication. | **False** | No current manuscript or preprint has been completed or submitted. Historical drafts are superseded. |

## Public-use rule

A manuscript, README, website, CV, GitHub profile, or LinkedIn claim may not exceed the strongest wording supported here. Process gates such as identity resolution, eligibility, protocol freeze, and deformation preflight must not be described as calibration or validation outcomes.
