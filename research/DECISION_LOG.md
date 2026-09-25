# Decision log

This file records research decisions that materially constrain interpretation.
Detailed frozen protocols and result records remain authoritative.

## 2026-09-24 — Preserve failed relative-intensity perturbation gate

The prospectively tested relative-intensity perturbation grid did not satisfy
the frozen promotion rule. The grid was not widened after observing the result.

Decision: retain the negative result and move to a distinct mechanism rather
than retuning the failed estimator.

## 2026-09-24 — Freeze mesh 3 / 15-iteration registration regime

The registration-convergence study selected mesh 3 with a maximum of 15
iterations under the predeclared field-stability rule.

Decision: treat this as a regime-specific operational setting, not a general
convergence claim.

## 2026-09-24 — Preserve failed initialization-sensitivity gate

No tested nonzero initialization perturbation passed the frozen promotion rule.

Decision: retain the negative result and do not widen the perturbation grid
post hoc.

## 2026-09-24 — Promote nine-member hyperparameter ensemble operationally

The 3 x 3 Mattes-MI-bin / LBFGSB-tolerance grid was complete in all five
promotion anatomies and met the frozen non-inertness rule in four of five.

Decision: promote the mechanism only to known-ground-truth evaluation. Do not
claim that its scalar spread tracks error, is calibrated, or is clinically
useful.

## 2026-09-24 — Amend known-GT sampling and inference before outcomes

Before any known-GT geometry or registration outcome was observed, Amendment 1
changed the primary spatial domain to the warped fixed-domain HECaP ROI and
replaced landmark-level permutation inference with an exact one-sided
anatomy-level sign test.

Decision: the amendment governs where it conflicts with the base protocol.

## 2026-09-25 — Separate geometry preflight from result-bearing execution

Before any known-GT geometry or registration outcome was observed, the runner
was changed to require an explicit execution mode. Geometry-only validation may
run without scientific authorization; the 270 result-bearing registrations may
run only after a reviewed geometry record is pinned by a committed run request.

Decision: accidental script invocation must not cross the prospective
geometry/result boundary.

## 2026-09-25 — Establish curated public research surface

The public repository was initialized from the reviewed private research state
without importing the private Git history, legacy manuscript, product framing,
debug scripts, or internal orchestration.

Decision: private history remains provenance; this repository is the
reader-facing, reproducible scientific surface.
