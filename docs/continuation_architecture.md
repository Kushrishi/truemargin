# TrueMargin continuation architecture

October 3, 2026. This plan preserves accepted M4–M6 evidence. It does not authorize a confirmatory claim from reused evaluation data.

## Current boundary

The nine-member classical registration ensemble has a positive but heterogeneous rank-information result. M6 coverage is conservative, with large radii, infinite 95% thresholds and incomplete ICE comparisons. The affine scale exploration in `m6_scale_development.md` is implemented and retained for all three fit blocks. It is ordinary calibration development, not a novel method or fresh test.

## Components and contracts

| Component | Input | Output / invariant |
| --- | --- | --- |
| Evidence reader | Accepted manifests, geometry pins, numeric-vector digests | Complete, identity-checked anatomy records; mismatches fail |
| Scale fit | Development anatomies with known errors and spread, in mm | Nonnegative intercept/slope; no validation anatomy in fit |
| Calibration | Separate whole anatomies, source-specific policy | Exact hierarchical order statistic; infinite thresholds retained |
| Assessment | Whole validation anatomies | Coverage, mean/median/tail radius and completion, reported together |
| Evidence report | All sources, folds and methods | Explicit evidence class and provenance; no clinical verdict |

Keep computation in Python and retained JSON artifacts. A diagnostic interface can consume the report later; it must not duplicate scientific arithmetic or manufacture an unknown error estimate for an arbitrary clinical pair.

## Next milestone: development validation only

Before output generation, freeze a leave-one-anatomy-out design using only the original 30 calibration anatomies. For each source and each of its 15 folds: hold out one anatomy; order the remaining identities by SHA-256; use the first four for affine fitting and the remaining ten for calibration. Preserve all 50 points per anatomy. Compare constant, spread-only and affine scales with identical calibration groups and the same nominal-90% HCP construction. Do not read original Phase-B records in this workflow. At ten calibration groups, retain the infinity atom and the exact rank rule rather than approximating the quantile.

All 30 validation folds must appear, including failures and infinite radii. Summaries use anatomy as the unit; report coverage and radius jointly and show source-level tails. Fold overlap makes these dependent development results, not 30 independent replications. Method selection has already been informed by observed M6 evaluation, so this exercise cannot become retrospective confirmation.

Acceptance tests: identity disjointness; missing/duplicate anatomy rejection; input digest failures; mm units; exact rank/infinity cases; independently checked fitting; and successful operation when Phase-B files are unavailable. No new registration is needed for this milestone.

## Gate to a fresh study

Continue only if development evidence supports a concrete spatial decision at a predeclared coverage requirement and useful radius/cost tradeoff against constant bounds. A fresh protocol must specify the decision, effect required, cohort/sample-size justification, feasible ICE comparison, failure treatment, computation cost, member displacement and optimizer diagnostics. Reserve new evaluation data before method choices. If the affine and constant models are practically equivalent, keep the diagnostic utility and bounded report rather than inventing novelty.

Licensing and clinical validity remain separate unresolved release gates. Do not change package rights or publish a package index release by assumption.
