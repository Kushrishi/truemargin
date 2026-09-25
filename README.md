# TrueMargin

TrueMargin is a medical-image-computing research project studying a narrow
question:

> **When a deformable image-registration method reports local uncertainty, under
> what conditions does that signal contain useful information about true local
> spatial registration error?**

The project separates four questions that are often conflated:

1. does an uncertainty mechanism vary at all?
2. does it rank true local error?
3. is it numerically calibrated?
4. where does it fail with high error and low reported uncertainty?

TrueMargin is research software, not a clinical product or medical device.

## Current evidence

The prospective development sequence has produced both negative and positive
operational results:

- a relative-intensity perturbation ensemble failed its frozen promotion gate;
- the mesh-3 / 15-iteration registration regime passed the specified
  field-stability gate;
- an initialization-sensitivity ensemble failed its frozen promotion gate;
- a nine-member registration-hyperparameter ensemble passed an operational
  promotion gate.

Operational promotion does **not** establish that the uncertainty signal tracks
true error.

The known-ground-truth program now has a reviewed **30 / 30 geometry-only
preflight** across ten held-out anatomies under the frozen base protocol and
Amendments 1 and 2. That result validates the prospective cohort, acquisition,
and synthetic-geometry construction only.

The paper-level comparator protocol and direct-comparator implementation are
now frozen before any result-bearing outcome. The local suite compares the
target sigma with inverse-consistency error, same-modality residual, and
Jacobian deviation under anatomy-aware statistics and failure handling.

Contrastive Discrepancy was prospectively excluded from this confirmatory study
because its authors' linked code snapshot could not be retrieved reproducibly
from clean hosted runners; no bespoke analogue is substituted.

The result-bearing known-ground-truth study has not been run. Its frozen budget
is **270 forward + 270 reverse = 540 registrations**, and execution remains
unauthorized until a separate reviewed run request pins the exact source and
evidence identities.

## Research discipline

Result-defining choices are frozen before the corresponding outcomes are
observed. Negative results are retained. The known-ground-truth study keeps the
official estimator fixed and evaluates:

- within-case rank association between uncertainty and known error;
- anatomy-level aggregation and inference;
- high-error / low-uncertainty blind spots;
- calibration only as a later, separate question.

See `research/STATE.md` and `research/CLAIMS.md` for the current evidence and
claim boundaries, and `research/ROADMAP.md` for the milestone plan.

## Scope

TrueMargin does not currently establish clinical validity, calibrated
probabilistic coverage, superiority over contemporary registration-uncertainty
methods, external-dataset generalization, or a completed paper/preprint.
