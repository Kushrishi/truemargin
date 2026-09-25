# Initialization-sensitivity ensemble gate result

**Result date:** 2026-09-13

## Status

The prospectively frozen B-spline initialization-sensitivity strength study completed successfully.

The predeclared gate selected:

**No nonzero initialization perturbation strength**

Therefore:

`SELECTED_INITIALIZATION_DELTA_MM=None`

Per the frozen protocol, this mechanism stops at the strength gate. The perturbation grid is not widened or tuned after observing the result, and the nested `n=5/10/20` ensemble-size stage is not run.

## Provenance

- Experiment: `real-prostate-initialization-ensemble-v1`
- Execution Git SHA: `9ecde7b9591fb8848f3232cbec6df4c7a65dfd67`
- Protocol main SHA: `aa30335335b1403381050407b472841b9c7fdd0f`
- Protocol: `docs/initialization_ensemble_protocol.md`
- Mesh size: `3`
- Maximum LBFGSB iterations: `15`
- `center_first=False`
- Base seed: `0`
- Ensemble members per patient × strength: `5`
- Frozen strengths: `0.0`, `0.5`, `1.0`, `2.0 mm`
- Frozen patients:
  - `aaa0054`
  - `aaa0059`
  - `aaa0061`
  - `aaa0063`
  - `aaa0066`
- Total planned and completed registrations: `100`

The real-data zero-displacement quantity remains a proxy/reference assumption, not independently verified pointwise ground truth. Proxy error and pointwise association metrics were descriptive only and were excluded from strength selection.

## Predeclared selection rule

The `delta_mm=0` repeatability-floor reference first had to have complete five-member cells in at least 4/5 patients.

For a patient with complete zero-strength and candidate cells, the frozen non-inertness threshold was:

```text
floor_p = median_sigma(delta=0)
resolution_floor_p = 0.25 * min(spacing_xyz_p)
required_signal_p = max(3 * floor_p, resolution_floor_p)
```

A candidate strength was non-inert for that patient only if:

```text
median_sigma(delta) >= required_signal_p
```

A nonzero strength was globally eligible only if:

1. at least 4/5 patients had complete cells for both `delta=0` and the candidate; and
2. at least four shared complete patients satisfied the non-inertness criterion.

The smallest eligible strength would have been selected in ascending order: `0.5`, `1.0`, `2.0 mm`.

No proxy-error, correlation, calibration, coverage, blind-spot, sharpness, or central-thesis metric was allowed to influence strength selection.

## Gate outcome

The `delta=0` repeatability-floor reference was assessable in all five frozen patients:

`delta=0 repeatability-floor complete: 5/5`

The nonzero-strength results were:

| Initialization half-range | Shared complete | Non-inert | Eligible |
| ---: | ---: | ---: | :---: |
| `0.5 mm` | 5/5 | 2/5 | No |
| `1.0 mm` | 4/5 | 2/5 | No |
| `2.0 mm` | 3/5 | 1/5 | No |

Therefore:

`SELECTED_INITIALIZATION_DELTA_MM=None`

## Interpretation

The prospectively specified initialization-sensitivity ensemble did not produce a perturbation strength that was both sufficiently complete and consistently distinguishable from the empirical repeatability/resolution floor across the frozen five-patient cohort.

The failure modes differed by strength:

- `0.5 mm` was operationally complete in all five patients, but the uncertainty signal exceeded the frozen non-inertness threshold in only 2/5 patients.
- `1.0 mm` retained the minimum required shared completeness at 4/5, but again exceeded the non-inertness threshold in only 2/5 patients.
- `2.0 mm` was incomplete in two patients, leaving only 3/5 shared complete cells, and exceeded the non-inertness threshold in only 1/5 patients.

This is a mechanism-specific negative result. It does not establish that initialization sensitivity is universally uninformative, that all registration ensembles fail, or that registration uncertainty itself is useless.

It does establish that this exact frozen construction — independent uniform B-spline coefficient offsets with half-ranges `0.5`, `1.0`, and `2.0 mm` under the convergence-validated mesh-3, 15-iteration regime — failed its prospective promotion gate.

## Relationship to previous gates

This result follows two earlier prospective findings:

1. the corrected relative-intensity perturbation ensemble failed its own Gate A because no nonzero perturbation strength satisfied the frozen promotion rule; and
2. the separate registration-convergence study selected the mesh-3, 15-iteration regime under its frozen field-stability criterion.

Together, these results reduce the risk that the two failed uncertainty mechanisms are being rejected simply because the nominal mesh-3 registration budget was never checked for convergence.

They do not identify a single universal reason why the uncertainty mechanisms failed.

## Next step

Do not widen or tune the initialization-strength grid after this result.

Do not run the initialization `n=5/10/20` ensemble-size study because no nonzero strength was selected.

The next independent uncertainty comparator should be specified prospectively before generating results. The previously deferred registration-hyperparameter ensemble remains the next planned mechanism.
