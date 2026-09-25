# Registration-hyperparameter ensemble gate result

**Result date:** 2026-09-14  
**Status:** completed prospective gate; mechanism promoted for independent evaluation

## Outcome

The prospectively frozen registration-hyperparameter sensitivity experiment completed successfully under the exact nine-member Cartesian grid specified in `docs/hyperparameter_ensemble_protocol.md`.

The predeclared gate returned:

`HYPERPARAMETER_ENSEMBLE_ELIGIBLE=True`

The exact nine-member grid is therefore frozen for downstream independent evaluation.

Passing this gate establishes only that the mechanism was operationally complete and sufficiently non-inert across the frozen sensitivity cohort. It does **not** establish that the estimator is calibrated, clinically useful, or informative about true registration error.

## Provenance

- Experiment: `real-prostate-hyperparameter-ensemble-v1`
- Execution Git SHA: `04c1dc811f1c34eeefa22c43112559697a1f059c`
- Protocol main SHA: `7e7a33640ae082f748e7bd060f62bf05011bbcf8`
- Protocol: `docs/hyperparameter_ensemble_protocol.md`
- Registration regime: mesh size `3`, maximum iterations `15`, `center_first=False`
- Nominal repeatability floor: 5 registrations per patient at 50 Mattes-MI bins and LBFGSB gradient tolerance `1e-5`
- Hyperparameter ensemble: exact Cartesian product of Mattes-MI bins `(32, 50, 64)` and LBFGSB gradient tolerances `(1e-4, 1e-5, 1e-6)`
- Hyperparameter members per patient: 9
- Frozen patients:
  - `aaa0054`
  - `aaa0059`
  - `aaa0061`
  - `aaa0063`
  - `aaa0066`
- Planned registrations: 70
- Completed registrations: 70
- Finished: `2026-09-14T13:39:52-07:00`

The real-data error quantity remains error under the zero-displacement proxy/reference assumption and is not independently verified pointwise ground truth.

## Frozen promotion rule

For each patient with complete repeatability-floor and hyperparameter cells:

```text
floor_p = median_sigma(nominal five-repeat floor)
resolution_floor_p = 0.25 * min(spacing_xyz_p)
required_signal_p = max(3 * floor_p, resolution_floor_p)
```

The nine-member hyperparameter ensemble is non-inert for patient `p` if:

```text
median_sigma(hyperparameter grid) >= required_signal_p
```

Global eligibility required:

1. nominal repeatability-floor completeness in at least 4/5 patients;
2. shared floor/grid completeness in at least 4/5 patients; and
3. non-inertness in at least 4 of those shared complete patients.

Proxy error, sigma-error association, calibration, blind-spot, coverage, and sharpness metrics were explicitly excluded from promotion.

## Aggregate gate result

| Criterion | Result |
| --- | ---: |
| Nominal repeatability-floor complete | 5/5 |
| Hyperparameter grid shared complete | 5/5 |
| Hyperparameter grid non-inert | 4/5 |
| Mechanism eligible | **Yes** |

Therefore:

`HYPERPARAMETER_ENSEMBLE_ELIGIBLE=True`

## Patient-level gate quantities

| Patient | Floor median sigma (mm) | Grid median sigma (mm) | Required signal (mm) | Non-inert |
| --- | ---: | ---: | ---: | :---: |
| `aaa0054` | 1.20236 | 2.87428 | 3.60708 | No |
| `aaa0059` | 6.18099e-15 | 0.769255 | 0.1015625 | Yes |
| `aaa0061` | 9.54491e-10 | 16.619 | 0.1015625 | Yes |
| `aaa0063` | 1.18136 | 9.85917 | 3.54408 | Yes |
| `aaa0066` | 2.13755e-14 | 3.91811 | 0.109375 | Yes |

All five nominal-floor cells completed 5/5 registrations. All five nine-member hyperparameter cells completed 9/9 configurations.

### `aaa0054`

The hyperparameter grid was complete, but its median sigma of **2.87428 mm** did not exceed the frozen required signal of **3.60708 mm**. This patient therefore failed the non-inertness criterion.

### `aaa0059`

The nominal repeatability floor was effectively zero. The frozen physical-resolution floor therefore controlled the gate at **0.1015625 mm**. The hyperparameter-grid median sigma was **0.769255 mm**, so this patient passed non-inertness.

### `aaa0061`

The nominal repeatability floor was effectively zero and the frozen physical-resolution floor controlled the gate at **0.1015625 mm**. The hyperparameter-grid median sigma was **16.619 mm**, so this patient passed non-inertness.

### `aaa0063`

The nominal repeatability floor was non-negligible. Three times the floor median was **3.54408 mm**, which controlled the gate. The hyperparameter-grid median sigma was **9.85917 mm**, so this patient passed non-inertness.

### `aaa0066`

The nominal repeatability floor was effectively zero. The frozen physical-resolution floor therefore controlled the gate at **0.109375 mm**. The hyperparameter-grid median sigma was **3.91811 mm**, so this patient passed non-inertness.

## Descriptive proxy-error observations

The runner also reported the following median errors under the real-data zero-displacement proxy/reference assumption for the nine-member grid:

- `aaa0054`: 7.63334 mm
- `aaa0059`: 2.9198 mm
- `aaa0061`: 39.1157 mm
- `aaa0063`: 49.297 mm
- `aaa0066`: 16.9229 mm

These values are descriptive only. They were not used to promote the mechanism and must not be interpreted as independently verified registration ground truth.

In particular, the relatively large proxy-error values for some promoted patients do not establish that the uncertainty estimator is useful. They strengthen the need for the next independent evaluation stage rather than changing the already frozen estimator definition.

## Interpretation

This is the first prospectively tested ensemble mechanism in the current TrueMargin rebuild to pass its operational promotion gate.

The bounded conclusion is:

> Under the convergence-validated mesh-3, 15-iteration registration regime, the exact nine-member Mattes-MI histogram-bin × LBFGSB gradient-tolerance grid was operationally complete in all five frozen sensitivity patients and produced deformation-field spread above the predeclared repeatability/resolution floor in four of five patients.

This result supports promoting the exact nine-member mechanism to independent evaluation.

It does **not** establish:

- that uncertainty tracks true registration error point-by-point;
- that the estimator is calibrated;
- that larger sigma means larger error;
- that the estimator avoids high-error / low-uncertainty blind spots;
- that the mechanism generalizes beyond the current registration regime or anatomy; or
- that the mechanism is clinically validated.

The prior negative results remain valid: the scale-aware input-intensity perturbation ensemble and B-spline initialization-sensitivity ensemble did not pass their own frozen promotion gates. The present positive result should not be used to retrospectively modify those mechanisms or their thresholds.

## Frozen estimator definition after promotion

For all downstream evaluation, the promoted hyperparameter-sensitivity estimator is exactly the complete nine-member Cartesian grid:

```text
Mattes-MI bins:             32, 50, 64
LBFGSB gradient tolerance:  1e-4, 1e-5, 1e-6
mesh size:                  3
maximum iterations:         15
center_first:               False
members:                    9
```

Do not remove a configuration, add another configuration, change the scalarization, or choose a favorable subset based on downstream results.

## Next stage

Proceed to independent evaluation of the frozen estimator as specified prospectively in the protocol, beginning with synthetic known-deformation error association before using real-data proxy-error behavior to make claims about pointwise usefulness.

The independent evaluation must keep estimator definition and promotion criteria fixed. Calibration, informativeness, blind-spot behavior, and robustness should be treated as distinct evaluation axes rather than collapsed into a single success metric.
