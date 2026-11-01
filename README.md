# TrueMargin

Controlled experiments on uncertainty in deformable image registration.

**Question:** does variation between registrations help identify local alignment error?

The controlled studies are complete. Further external validation is deferred; no external landmark-based result is available. This is research software, not a clinical product.

[Technical report](docs/technical_report.md) · [Reproduction](docs/reproduction.md) · [Study records](research/README.md)

![Controlled associations, failure cases and calibrated error bounds](docs/figures/m4_m6_evidence.png)

## Findings

A fixed nine-setting registration ensemble was evaluated on 30 synthetic-deformation cases across 10 held-out anatomies. Analysis used anatomy-level summaries rather than treating all 1,500 sampled locations as independent subjects.

| Signal | Median anatomy-level Spearman correlation with known error |
| --- | ---: |
| Ensemble spread | 0.6841 |
| Inverse-consistency error | 0.7203 |
| Image residual | 0.2851 |
| Jacobian deviation | 0.1689 |

Ensemble spread contained useful rank information, but no advantage over inverse-consistency error was established. Six of 30 case-level associations were negative. The analysis retained 39 high-error, low-spread observations across 11 cases and seven anatomies.

A separate study used 30 calibration and 30 evaluation anatomies across two sources. At nominal 90% coverage, observed mean anatomy-level coverage was 97.73% and 99.73%, with median anatomy radii of 3.93 mm and 4.36 mm. One anatomy had a 70.69 mm median radius. The bounds were conservative; 95% thresholds were infinite under the finite-sample construction. Reverse-registration failures prevented the planned full-cohort calibrated comparison with inverse-consistency error.

These results do not establish clinical validity, external generalization or uniformly useful error bounds. A later calibration-only analysis found source-dependent effects, not a consistent improvement.

## Check the saved results

From a checkout with Python 3.12:

```bash
python scripts/verify_m6_phase_a_result.py results/m6_phase_a
python scripts/verify_m6_phase_b_result.py results/m6_phase_b
```

These standard-library checks verify saved records, identities and numerical summaries. They do not rerun the registrations and require no imaging data or landmark access.

For development:

```bash
python -m pip install -e ".[dev]"
pytest
```

Full experiments require the dependencies and source data documented in the [reproduction guide](docs/reproduction.md).

## Read the evidence

- [Known-error study and comparators](docs/hyperparameter_known_gt_result.md)
- [Failure analysis](docs/m5_informativeness_characterization.md)
- [Held-out calibration results](docs/m6_phase_b_evaluation_result.md) and [failure diagnostics](docs/m6_failure_diagnostics.md)
- [Calibration-only development analysis](docs/m6_calibration_only_scale_validation.md)
- [Retained outputs](results/README.md)

## Deferred external study

An independent lung-CT protocol and image-only preflight were prepared. Two retained Case7 fields were almost identical after a tolerance change, and both reached the configured iteration cap. This establishes neither convergence nor useful ensemble diversity. Numerical landmarks remain sealed.

The [external protocol](docs/external_lung_validation_protocol.md), [execution history](research/STATE.md) and [roadmap](research/ROADMAP.md) are retained for reproducibility. They describe prior work and conditional future steps, not a currently running campaign. No experiments or results were changed by this presentation update.

## Repository and licensing

`src/` contains analysis code; `scripts/` contains experiment and verification entry points; `tests/` contains numerical checks. Methods, protocols and results remain under `docs/`, `research/` and `results/`.

This public repository has no project-wide software licence grant. Third-party data and software retain their own terms. No peer-reviewed publication or clinical validation is claimed.
