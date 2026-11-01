# Research status

The controlled known-deformation study and held-out calibration study are complete. Further external validation is deferred. No external landmark-based result or peer-reviewed publication is available.

## Research question

When does variability between image registrations contain useful information about local alignment error?

The project evaluates error ranking, failure cases and calibrated bounds separately. Success on one measure does not establish success on the others.

## Completed findings

The frozen ensemble varies Mattes-MI bins and optimizer tolerance across nine settings, with a fixed mesh and iteration limit. Earlier unsuccessful ensemble designs remain documented.

### Known-deformation study

Thirty cases across ten held-out anatomies supplied 1,500 sampled locations. The median anatomy-level Spearman association between spread and known error was 0.6840816, with an anatomy-bootstrap 95% interval of [0.3047779, 0.8283794]. All ten anatomy-level associations were positive.

The inverse-consistency comparator had a median association of 0.7203. The paired spread-minus-comparator interval was [-0.0903, 0.0736]; superiority was not established. Six of thirty case-level associations were negative. Thirty-nine points met the study's high-error, low-spread definition.

[Known-error results](../docs/hyperparameter_known_gt_result.md) · [Failure analysis](../docs/m5_informativeness_characterization.md)

### Held-out calibration

The separate study used thirty calibration and thirty evaluation anatomies, with fifteen per source in each cohort.

| Source | Nominal coverage | Observed mean anatomy-level coverage | Median anatomy radius |
| --- | ---: | ---: | ---: |
| Prostate-3T | 90% | 97.73% | 3.93 mm |
| Prostate-Diagnosis | 90% | 99.73% | 4.36 mm |

One anatomy had a 70.69 mm median radius. The 95% thresholds were infinite under the finite-sample construction. Reverse-registration failures prevented the planned full-cohort calibrated comparison with inverse-consistency error.

A later calibration-only development analysis found source-dependent effects. Its overlapping folds do not provide independent confirmation or a uniform improvement.

[Calibration results](../docs/m6_phase_b_evaluation_result.md) · [Failure diagnostics](../docs/m6_failure_diagnostics.md) · [Development analysis](../docs/m6_calibration_only_scale_validation.md)

## Where external validation stopped

A lung-CT protocol, source audit and image-only preflight were prepared. The original Learn2Reg path had unresolved landmark access/provenance; ten DIR-Lab fallback archives were subsequently inventoried with numerical landmarks sealed.

Two Case7 image-only fields were retained. The first passed cross-host recovery. Changing tolerance produced only a microscopic field difference, while both runs reached the configured iteration cap. These checks establish recovery of the saved fields, not convergence, useful ensemble diversity or landmark accuracy. No complete external ensemble or landmark evaluation has been reported.

Earlier disconnected runs retain unknown terminal outcomes. Preserve their records rather than inferring completion or automatically restarting them.

[External protocol](../docs/external_lung_validation_protocol.md) · [Cross-host recovery](CASE7_CROSS_HOST_RECOVERY_2026_10_10.md) · [Retention design](DIRLAB_BOUNDED_RETENTION_DESIGN_2026_10_09.md)

## Scope and records

The work does not establish clinical usefulness, arbitrary-population coverage or external generalization. Earlier experiments using an unverified zero-displacement reference are historical context, not current ground-truth validation.

The [technical report](../docs/technical_report.md), [claims summary](CLAIMS.md) and frozen result records define the evidence. The [previous detailed execution status](https://github.com/Kushrishi/truemargin/blob/794aaaea9be60411c79dade6611a2f98201ca303/research/STATE.md) remains in repository history. Historical roadmap entries describe conditional research steps, not an active campaign.

No code, scientific protocol, numerical result or sealed landmark was changed by this presentation update.
