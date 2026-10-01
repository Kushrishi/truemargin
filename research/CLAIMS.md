# Claims ledger

**Updated:** 2026-10-01

| Claim | Status | Current boundary |
| --- | --- | --- |
| Historical real-data zero-displacement values are verified pointwise registration ground truth. | **False** | They are a proxy/reference assumption and must be described as such. |
| The corrected relative-intensity perturbation ensemble passed its prospective promotion gate. | **False** | Gate A failed; no alpha was promoted. |
| The initialization-sensitivity ensemble passed its prospective promotion gate. | **False** | No nonzero initialization strength was promoted. |
| The mesh-3, 15-iteration regime passed the specified convergence gate. | **Supported** | Regime-specific prospective field-stability result; not universal convergence. |
| The nine-member registration-hyperparameter ensemble passed an operational promotion gate. | **Supported** | Complete in 5/5 promotion patients and non-inert in 4/5 under the frozen rule. |
| The known-ground-truth cohort passed its frozen geometry-only preflight. | **Supported** | 30 / 30 amended cases passed under the frozen base protocol + Amendments 1 and 2. |
| The paper-level direct comparator suite was frozen and implemented before known-GT outcomes. | **Supported** | Sigma, ICE, same-modality residual, and Jacobian deviation were pinned with method-specific validity/failure handling and anatomy-aware summaries before result-bearing execution. |
| The promoted hyperparameter-ensemble sigma contains useful pointwise rank information about true local registration error in the frozen known-GT study. | **Supported** | M4 completed 30 / 30 cases across 10 held-out anatomies. All 10 anatomy-level associations were positive; median anatomy Spearman = 0.6841, anatomy-bootstrap 95% interval [0.3048, 0.8284], exact one-sided sign-test p = 0.0009766. This is specific to the frozen synthetic known-deformation study. |
| The promoted sigma showed stronger anatomy-level rank informativeness than the same-modality residual and Jacobian-deviation comparators in the frozen study. | **Supported** | Paired target-minus-comparator bootstrap intervals were [0.0188, 0.4757] vs residual and [0.1695, 0.7144] vs Jacobian deviation. This is not a universal method-ranking claim. |
| The promoted sigma is superior to inverse-consistency error. | **Unsupported** | ICE median anatomy Spearman was 0.7203 versus 0.6841 for sigma; paired target-minus-ICE bootstrap interval [-0.0903, 0.0736] crosses zero. |
| The promoted estimator is numerically calibrated. | **Untested** | Calibration remains intentionally separate from ranking informativeness and is downstream of M4. |
| A zero median blind-spot rate proves the estimator never misses high-error locations. | **False** | The frozen median anatomy blind-spot rate was 0.0, but some anatomies/cases had nonzero blind spots; M5 must characterize their frequency and severity. |
| The promoted estimator is clinically useful or clinically validated. | **Unsupported** | No clinical-performance study supports this claim. |
| TrueMargin is externally validated. | **False** | Current known-GT design uses held-out anatomies from the same source collection and synthetic deformations. |
| Registration uncertainty generally predicts registration error. | **Unsupported** | The positive M4 result is conditional on one frozen estimator, registration regime, anatomy source, deformation design, and sampling rule. |
| TrueMargin has a completed paper, preprint, or peer-reviewed publication. | **False** | No current manuscript/preprint has been completed or submitted. Historical drafts are superseded. |

## Rule

A public, manuscript, CV, website, or LinkedIn claim may not exceed the strongest wording supported here.
