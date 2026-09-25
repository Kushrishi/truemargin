# Prospective registration convergence sensitivity protocol

Date frozen: 2026-09-13

Design base: `052ba816f7ed91f7e8ee32fca5d67914a3c1a29d`

This protocol is frozen before any registration-convergence results are generated.
It follows the failed prospective ensemble Gate A recorded in
`docs/ensemble_gate_a_result.md`.

## Question

Is the 15-iteration, mesh-3 `fast_dev` registration regime stable enough that
later uncertainty experiments can treat changes in the registration output as
responses to the uncertainty mechanism rather than as ordinary optimizer
non-convergence or run-to-run numerical instability?

This study isolates the **iteration budget only**. It does not compare mesh
sizes, DCE phases, uncertainty methods, centering strategies, or calibration
methods.

## Cohort and data path

Use the same five patients frozen before the corrected ensemble Gate A:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

Use the same T2/DCE series identities as the Gate A runner, the deterministic
middle DCE phase, the HECaP/T2 grid assertion, a 15-voxel crop margin, physical
T2 spacing, seed 0 for deterministic landmark subsampling, and at most 75
HECaP-derived evaluation locations per patient.

Real-data error retains the existing zero-displacement proxy/reference
assumption. It is not independently verified pointwise T2-to-DCE ground truth.
Proxy error is descriptive only in this convergence study and is **not** a
selection criterion.

## Registration settings

Hold fixed:

- B-spline mesh size: 3
- `center_first`: false
- Mattes mutual information configuration: unchanged
- interpolation: unchanged
- physical spacing: patient T2 spacing
- input images: unperturbed fixed/moving pair

Test maximum iteration budgets:

- 15
- 30
- 60
- 100

Run five repeated registrations for every patient x iteration-budget cell.
The repeats intentionally use identical inputs. Gate A showed that the current
multi-threaded SimpleITK/LBFGSB path can exhibit run-to-run variation and
occasional failure, so repeatability is part of the convergence question rather
than noise to suppress after observing results.

Total planned registrations: `5 patients x 4 budgets x 5 repeats = 100`.

## Per-repeat failure policy

A repeat fails if any of the following occurs:

1. registration raises an exception;
2. the displacement field contains non-finite values;
3. the displacement field has the wrong shape; or
4. mean displacement magnitude exceeds the physical diagonal of the cropped
   image volume.

Continue the remaining repeats so failure frequency is measured rather than
hidden by early termination.

A patient x budget cell is **assessable** only when at least 4/5 repeats are
valid. Valid survivors may be summarized for convergence because repeat
failure rate is itself one of the stability criteria; failed repeats are never
silently discarded from the completion count.

## Landmark-space summaries

For each valid repeat, sample the displacement vector at the frozen evaluation
locations.

For each assessable patient x budget cell:

1. form a representative displacement at each evaluation location using the
   coordinate-wise median across valid repeats;
2. compute within-budget repeatability distances as the Euclidean distance
   between each valid repeat and that representative field at every evaluation
   location;
3. summarize repeatability by the pooled median and 90th percentile distance.

The 100-iteration cell is the reference for the same patient.

For each lower candidate budget (15, 30, 60), compare its representative field
with the 100-iteration representative field using pointwise Euclidean vector
difference, summarized by the median and 90th percentile.

## Predeclared patient-level convergence rule

The 100-iteration reference must first be assessable for at least 4/5 patients.
If fewer than four reference patients are assessable, stop: no lower iteration
budget is selected and the registration mechanism itself requires further
investigation before uncertainty work continues.

For a patient with both candidate and reference cells assessable, define two
reference tolerances from image resolution and intrinsic 100-iteration
repeatability:

- `median_tolerance_mm = max(min(spacing_xyz), 2 * reference_repeatability_median_mm)`
- `p90_tolerance_mm = max(0.5 * max(spacing_xyz), 2 * reference_repeatability_p90_mm)`

A lower iteration budget is converged for that patient only if all four checks
pass:

1. candidate-to-reference median displacement difference <= median tolerance;
2. candidate-to-reference p90 displacement difference <= p90 tolerance;
3. candidate within-budget repeatability median <= median tolerance; and
4. candidate within-budget repeatability p90 <= p90 tolerance.

The resolution floors prevent a numerically tiny 100-iteration repeatability
floor from imposing a physically meaningless sub-voxel requirement. The
repeatability terms prevent the tolerance from pretending the reference is
more precise than its own observed run-to-run behavior.

## Global selection rule

Evaluate candidate budgets in ascending order: 15, 30, 60.

A candidate is globally eligible only if:

- at least four patients have both candidate and 100-iteration cells
  assessable; and
- at least 4/5 patients satisfy the full patient-level convergence rule.

Select the smallest eligible iteration budget.

Possible outcomes:

- `15` selected: the current `fast_dev` iteration cap is validated for this
  mesh-3 sensitivity regime;
- `30` or `60` selected: use that budget, not 15, for subsequent mesh-3
  uncertainty-mechanism experiments;
- no lower budget selected: do not proceed by tuning this gate post hoc;
  treat 100 iterations as a reference only and revisit registration design
  before defining a replacement uncertainty ensemble.

The 100-iteration budget is never "selected" by this gate; it is the reference
used to decide whether a cheaper regime has stabilized.

## Diagnostics excluded from selection

The following are reported but must not affect iteration-budget selection:

- zero-displacement proxy error;
- whether a lower iteration budget happens to have smaller proxy error than
  100 iterations;
- uncertainty calibration metrics;
- sigma/error correlation or blind-spot metrics;
- runtime preferences after results are seen.

## After the gate

Only after this convergence gate is complete should TrueMargin freeze a new
uncertainty mechanism. If a lower mesh-3 iteration budget is validated, the
next design phase may compare scientifically justified optimization or
hyperparameter perturbations. If convergence fails, registration stability is
the upstream problem and must be addressed before attributing ensemble
variation to uncertainty.