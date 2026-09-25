# Registration convergence gate result

**Result date:** 2026-09-13

## Status

The prospectively frozen mesh-3 registration-convergence sensitivity study
completed successfully.

The predeclared gate selected:

**15 iterations**

This is the smallest lower iteration budget that satisfied the frozen global
convergence criterion.

## Provenance

- Experiment: `real-prostate-registration-convergence-v1`
- Design base SHA: `052ba816f7ed91f7e8ee32fca5d67914a3c1a29d`
- Execution Git SHA: `b3cc372b3c9f5ebab0f4b2c0caacf6466a45dc62`
- Protocol: `docs/registration_convergence_protocol.md`
- Mesh size: 3
- Candidate iteration budgets: 15, 30, 60
- Reference iteration budget: 100
- Repeats per patient × budget: 5
- Minimum valid repeats for an assessable cell: 4
- Frozen patients:
  - `aaa0054`
  - `aaa0059`
  - `aaa0061`
  - `aaa0063`
  - `aaa0066`

All 100-iteration reference cells were assessable: **5/5 patients**.

The real-data zero-displacement quantity remains a proxy/reference assumption,
not independently verified pointwise ground truth. Proxy error was descriptive
only and was excluded from iteration selection.

## Predeclared selection rule

The 100-iteration reference first had to be assessable in at least 4/5
patients.

Candidate budgets were then evaluated in ascending order: 15, 30, 60.

A candidate was globally eligible only if:

1. at least 4 patients were assessable for both candidate and reference; and
2. at least 4/5 patients passed the frozen candidate-to-reference and
   within-budget median/p90 field-stability criteria.

The smallest eligible candidate was selected.

No proxy-error quantity was used for selection.

## Gate outcome

| Iteration budget | Shared assessable | Converged | Eligible |
| ---: | ---: | ---: | :---: |
| 15 | 5/5 | 4/5 | Yes |
| 30 | 5/5 | 4/5 | Yes |
| 60 | 5/5 | 2/5 | No |

Therefore:

`SELECTED_ITERATIONS=15`

## Patient-level outcome

### `aaa0054`

- 15 iterations: pass
- 30 iterations: pass
- 60 iterations: fail

At 60 iterations, the representative field differed from the 100-iteration
reference by a median of **5.206 mm**, above the frozen median tolerance of
**0.40625 mm**.

The 60-iteration within-budget repeatability itself remained within this
patient's frozen tolerances, so this failure was driven by disagreement with
the reference representative field rather than a failure of all repeatability
criteria.

### `aaa0059`

- 15 iterations: pass
- 30 iterations: pass
- 60 iterations: pass

All three candidate budgets were effectively identical to the reference at the
sampled landmarks within the frozen criteria.

### `aaa0061`

- 15 iterations: pass
- 30 iterations: fail
- 60 iterations: fail

The 30- and 60-iteration representative fields were very close to the
100-iteration representative field, but their within-budget p90 repeatability
was **47.944 mm** and **48.227 mm**, respectively.

The frozen p90 tolerance was approximately **1.995 mm**.

These failures were therefore driven by severe tail instability across repeats,
not by the representative candidate-to-reference displacement.

### `aaa0063`

- 15 iterations: fail
- 30 iterations: pass
- 60 iterations: fail

For 15 iterations:

- candidate-to-reference median difference: **2.021 mm**
- median tolerance: **0.40625 mm**
- candidate-to-reference p90 difference: **2.700 mm**
- p90 tolerance: approximately **1.995 mm**
- within-budget p90 repeatability: **4.154 mm**

Thus the 15-iteration candidate failed both reference-agreement and
within-budget tail-stability criteria for this patient.

For 30 iterations, all frozen criteria passed.

For 60 iterations:

- candidate-to-reference median difference: **1.061 mm**
- within-budget repeatability median: **1.016 mm**
- within-budget repeatability p90: **4.496 mm**

These exceeded their corresponding frozen tolerances, although the
candidate-to-reference p90 difference itself remained below the p90 tolerance.

### `aaa0066`

- 15 iterations: pass
- 30 iterations: pass
- 60 iterations: pass

All candidate budgets were effectively identical to the reference at the
sampled landmarks within the frozen criteria.

## Interpretation

The predeclared convergence gate supports retaining the existing
**15-iteration mesh-3 fast-development regime** for the downstream sensitivity
studies covered by this protocol.

This conclusion is deliberately bounded. It does not establish that 15
iterations is universally sufficient for B-spline registration, other mesh
sizes, other anatomies, other optimizers, or clinical deployment.

The result also shows that stability was not monotonic with the iteration
budget. Both 15 and 30 iterations met the global gate, whereas 60 iterations
did not. Individual failures arose through different mechanisms, including
candidate-to-reference disagreement and large within-budget tail instability.
Therefore iteration count alone should not be interpreted as a monotonic proxy
for registration stability in this regime.

The 100-iteration rows are reference cells. Their candidate
`converged_to_reference` field is not interpreted as a reference failure.

## Relationship to ensemble Gate A

The convergence result reduces concern that the failed relative-intensity
perturbation Gate A was simply caused by an obviously inadequate 15-iteration
registration budget: the same 15-iteration mesh-3 regime passed the separately
predeclared convergence gate in 4/5 frozen patients.

This does **not** prove why the Gate A uncertainty mechanism failed, nor does it
establish that all registration uncertainty mechanisms are uninformative.
Gate A remains a mechanism-specific prospective negative result.

## Next step

Do not tune the convergence gate after observing this result.

The next uncertainty mechanism should be specified prospectively under the
selected 15-iteration mesh-3 regime before generating its results.
