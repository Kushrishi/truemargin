# Research status

Updated October 10, 2026 UTC. [Execution sequence and completion criteria](ROADMAP.md).

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

The [external lung-CT protocol](../docs/external_lung_validation_protocol.md) specifies a new-data validation. The [training-image preflight](../docs/external_lung_training_preflight.md) checks image geometry without reading landmarks. The [DIR-Lab source/decoder audit](DIRLAB_DECODER_AUDIT_2026_10.md) qualifies a prospective fallback without opening landmarks. The [largest-case runtime history](DIRLAB_RUNTIME_FEASIBILITY_2026_10.md) preserves the 600-second observation and isolated 2,700-second timeout. The later [three-hour Case 7 result and next resource gate](CASE7_RUNTIME_RESULT_AND_NEXT_GATE_2026_10_09.md) records an explicit supervisor timeout: 10,800.25 wall seconds, 18,376.05 CPU seconds and 1.62 GiB child peak RSS. No completion, optimizer stop or final field facts were saved. A later six-hour attempt last saved optimizer index 13 at 7,128.9363 registration seconds before runtime disconnection; no saved terminal result establishes completion or timeout. Its final wall/CPU/RSS, optimizer stop and field production remain unknown.

The completed-member producer and local copy/readback verification are implemented.
Field-size copy and hash readback after Drive unmount/remount were qualified
on 10 October. A separate retained Colab attempt last reported
18,738.8327 seconds and optimizer index 13 but left no verified terminal
record or complete field; its outcome remains unknown.

A subsequent **persistent Mac execution of one Case7 member completed** under
frozen source `fdaa8ae7b5aefa02e58c4f4acf4496835f7eaa3e`. The worker exited
successfully after 2,032.658 seconds (33.88 minutes), with 2.235 GiB peak RSS.
A retained float64 field of shape `[3,136,512,512]` passed whole-volume finite
and displacement-magnitude checks, original/retained hashes and
separate-process **same-host** readback. The field SHA-256 is
`076f1b42fa89f56a6aed7a19513b2f1589eaeaa87bbabb6392f39b63a4c46640`.
The original Mac completion and audit receipts are retained in the private
`research-execution/runs/case7-mac-completion-20261010/` directory. On October 10,
a consumer on Linux independently reconstructed the transferred packet, verified
the original manifest and retention-receipt hashes, recovered to a fresh directory,
and read all 106,954,752 float64 components in a separate process. The field hash
and full-volume displacement statistics matched the original audit exactly.
The Mac producer identity comes from the owner's separately retained execution
records; the Linux consumer identity is locally observed, not hardware-attested.
See the [cross-host recovery evidence](CASE7_CROSS_HOST_RECOVERY_2026_10_10.md).

The optimizer reported iteration 15 and
`LBFGSBOptimizerv4: User requested`. A separate small synthetic investigation
supports an iteration-cap interpretation, but does **not** prove convergence
or landmark accuracy. Cross-host byte recovery is now demonstrated for this one
member. Diversity/stopping assessment for the nine settings, representative
forward/reverse-case runtime study and
durable campaign controller remain open. This single member earns **no automatic
180-slot campaign credit**. Prospective source, environment, resource and
protocol gates precede additional campaign execution. Never infer a stalled
worker is dead, automatically restart it or overwrite its outputs. Held-out
numerical landmarks remain sealed; HELD-OUT ACCESS SAFE remains NO.

The external question is error ranking and failure behavior against the declared
comparators. A new calibration-efficiency study would require its own design.
There are no external-validation results yet.

## Limits and records

The work does not establish clinical usefulness, arbitrary-population coverage or external generalization. Earlier real-data experiments used an unverified zero-displacement reference and are historical context rather than current ground-truth validation.

The [technical report](../docs/technical_report.md) summarizes the completed studies. Frozen protocols, amendments and result records define their methods and outcomes. The [claims summary](CLAIMS.md) records the evidence supporting public descriptions.
