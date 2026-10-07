# Research status

Updated October 7, 2026.

The controlled known-deformation study and held-out calibration study are complete. Further scale development has produced source-dependent results. An external lung-CT validation protocol and training-image preflight are implemented, but that study has not run. The original Learn2Reg outcome path stopped at unresolved authoritative landmark access/provenance. All ten authorized DIR-Lab fallback packets are acquired with landmarks sealed; image-only decoding is qualified. Operational feasibility and a prospective replacement amendment remain open. No paper has been submitted or published.

## Question

When does variability across deformable image registrations help predict the true local alignment error?

The project measures ranking, calibrated error bounds and failure behavior separately. A signal can rank error well while producing impractically large bounds or missing individual failures.

## Completed findings

The frozen estimator varies Mattes-MI bins (32, 50, 64) and LBFGSB gradient tolerance (1e-4, 1e-5, 1e-6), producing nine registrations with mesh size 3 and at most 15 iterations. Earlier intensity-perturbation and initialization-sensitivity ensembles failed their prospective tests; their results are retained.

### Known-deformation study

Thirty cases across ten held-out anatomies provided 1,500 sampled locations with known deformation error.

- Median anatomy-level Spearman association between spread and error: 0.6840816.
- Positive anatomy-level associations: 10 of 10.
- Anatomy-bootstrap 95% interval: [0.3047779, 0.8283794].
- Inverse-consistency error (ICE) median association: 0.7203.
- Paired spread-minus-ICE interval: [-0.0903, 0.0736].

Spread was informative in this setting, but superiority over ICE was not established. At the individual case level, six of thirty associations were negative. Thirty-nine sampled points met the study's high-error, low-spread definition, across eleven cases and seven anatomies.

See the [known-error result](../docs/hyperparameter_known_gt_result.md) and [failure analysis](../docs/m5_informativeness_characterization.md).

### Held-out calibration

The source-stratified design used thirty calibration and thirty evaluation anatomies, with fifteen from each source in each cohort. Each anatomy contributed one synthetic deformation and fifty fixed ROI locations. Source-specific hierarchical conformal thresholds were fitted on calibration records and sealed before evaluation.

| Source | Nominal coverage | Observed coverage | Median anatomy radius |
| --- | ---: | ---: | ---: |
| Prostate-3T | 90% | 97.73% | 3.93 mm |
| Prostate-Diagnosis | 90% | 99.73% | 4.36 mm |

One evaluation anatomy had a 70.69 mm median radius. The 95% thresholds are infinite under the finite-sample construction. Reverse-registration failures prevented the planned full-cohort calibrated ICE comparison.

The [calibration report](../docs/m6_phase_a_calibration_result.md), [evaluation report](../docs/m6_phase_b_evaluation_result.md) and result records retain the exact thresholds, identities and failed attempts. Input recovery restored exact frozen archive digests before the completed runs; no failed anatomy was removed to improve the results.

## Further analysis

An exploratory constant-radius comparison found smaller radii with different achieved coverage. Because it was chosen after evaluation, it does not establish confirmatory superiority.

A later leave-one-anatomy-out analysis read only the original calibration cohort. For Prostate-3T, the constant radius averaged 2.31 mm at 96.8% coverage; the affine radius averaged 2.66 mm at 98.0%. For Prostate-Diagnosis, the constant radius averaged 4.01 mm at 98.9%; the affine radius averaged 3.15 mm at 95.5%.

These overlapping development folds suggest source dependence, rather than a uniform adaptive advantage. See the [calibration-only analysis](../docs/m6_calibration_only_scale_validation.md).

## Next study

The [external lung-CT protocol](../docs/external_lung_validation_protocol.md) specifies a new-data validation. The [training-image preflight](../docs/external_lung_training_preflight.md) checks image geometry without reading landmarks. The [DIR-Lab source/decoder audit](DIRLAB_DECODER_AUDIT_2026_10.md) qualifies a prospective fallback without opening landmarks. The [largest-case runtime probe](DIRLAB_RUNTIME_FEASIBILITY_2026_10.md) exceeded its 600-second cap; full campaign compute/storage is not authorized. The original protocol remains historical and no final replacement amendment is frozen. There are no external-validation results yet.

The useful research question is whether the fixed uncertainty signal and scale remain informative and efficient outside the prostate synthetic-deformation setting. A paper can report a well-supported limitation or positive result; its contribution and venue suitability still require assessment.

## Limits and records

The work does not establish clinical usefulness, arbitrary-population coverage or external generalization. Earlier real-data experiments used an unverified zero-displacement reference and are historical context rather than current ground-truth validation.

The [technical report](../docs/technical_report.md) summarizes the completed studies. Frozen protocols, amendments and result records define their methods and outcomes. The [claims summary](CLAIMS.md) records the evidence supporting public descriptions.
