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

The next primary study therefore evaluates the frozen nine-member estimator
against synthetic deformations with known spatial error across ten held-out
anatomies. Its base protocol and a pre-result amendment are frozen. The
result-bearing known-ground-truth study has not been run.

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
