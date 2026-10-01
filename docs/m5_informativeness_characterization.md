# M5 informativeness, comparator, and blind-spot characterization

**Completed:** 2026-10-01  
**Analysis class:** post-primary descriptive characterization of frozen M4 outputs  
**Result-bearing registrations added:** 0

## Purpose

M5 characterizes the completed M4 known-ground-truth result without changing the estimator,
cohort, synthetic deformations, sampled ROI locations, comparator definitions, primary statistic,
or any M4 inference.

The source data are the canonical M4 artifact and the ten patient shard artifacts from workflow
run `36188222836`, execution Git SHA
`9add89e5055ba45eb6c6b93c42da38615891a225`. Every downloaded archive was verified against its
GitHub-recorded SHA-256 digest before analysis. The durable artifact identity list is recorded in
`research/M5_SOURCE_ARTIFACTS.json`.

The M5 implementation then reconstructed all case-level Spearman, quartile-enrichment, and
blind-spot summaries from the pointwise shard checkpoints and required exact agreement with the
frozen M4 case table. No registration was rerun.

## Frozen blind-spot rule

M5 reuses the M4 rule exactly. Within each 50-point case, a location is a blind spot for a method
when both conditions hold:

1. known registration error is at or above that case's 75th percentile; and
2. the method score is at or below that case's 25th percentile.

For the target method, the score is hyperparameter-ensemble sigma. The same direction is used for
the direct quality-surrogate comparators because larger scores are intended to indicate larger
error/concern.

This is a within-case descriptive failure definition. M5 does not introduce a new threshold,
clinical risk threshold, or confirmatory hypothesis test.

## M4 result retained

The primary M4 result is unchanged:

- 30 / 30 complete cases across 10 held-out anatomies;
- 10 / 10 positive anatomy-level sigma/error associations;
- median anatomy Spearman `0.6841`;
- anatomy-bootstrap 95% interval `[0.3048, 0.8284]`;
- exact one-sided anatomy sign-test `p = 0.0009766`.

M5 therefore interprets an already-positive primary result; it does not replace or re-test it.

## Case-level heterogeneity

The anatomy-level result is not uniform across deformation replicates.

Across the 30 frozen cases:

- 24 case-level sigma/error Spearman associations were positive;
- 6 were negative;
- median case-level Spearman was `0.6465`;
- 7 cases had non-positive high-vs-low sigma quartile error enrichment.

Two patterns are particularly important for interpretation:

- `aaa0069` was persistently weak across all three deformations (`0.0334`, `-0.0242`, `0.1896`),
  giving the weakest anatomy-level median (`0.0334`).
- `aaa0053` had two strong positive cases but one severe inversion: replicate 1 had Spearman
  `-0.9020` with 10 / 50 target blind-spot locations. Its anatomy-level median remained `0.8902`.
  This shows why an anatomy median must not be interpreted as evidence that every deformation
  regime is reliable.

The result is therefore best stated as positive anatomy-level rank informativeness with meaningful
case-level heterogeneity, not uniformly reliable pointwise ranking.

## Pointwise blind spots

The shard checkpoints preserve all 50 sampled locations for every case, yielding 1,500 frozen
pointwise observations.

Under the frozen M4 definition:

- 39 / 1,500 target-sigma points were blind spots (`2.6%`);
- 11 / 30 cases contained at least one target blind spot;
- 7 / 10 anatomies contained at least one target blind spot across their three deformations;
- the worst single case was `aaa0053` replicate 1 with 10 / 50 blind spots (`20%`).

The zero **median anatomy** blind-spot rate reported in M4 is therefore compatible with real
case-level failures. It must not be paraphrased as "no blind spots."

## Strongest comparator boundary

Inverse-consistency error remains a strong constraint on the contribution claim.

At the frozen anatomy level, ICE had median Spearman `0.7203` versus `0.6841` for target sigma, and
the pre-specified paired target-minus-ICE bootstrap interval crossed zero. M5 does not introduce a
post-hoc superiority statistic.

The pointwise failure patterns are also not identical. Across the 27 cases where ICE was valid:

- ICE had 34 blind-spot points among 1,350 assessable points;
- only 12 of the 39 target-sigma blind spots were also ICE blind spots.

This overlap is descriptive only. It does not establish complementarity, an ensemble benefit, or a
new combined method. Any future combination of signals would require a prospective protocol.

## Comparator operational failures

The frozen method-specific failure rules remain intact:

- ICE was invalid in 3 / 30 cases;
- same-modality residual was invalid in the same 3 / 30 cases;
- Jacobian deviation was valid in 30 / 30 cases.

The retained failure reason for ICE and residual in those cases is
`sample point lies outside the image domain`. Invalid cases are not imputed or silently removed.
All direct methods remained assessable at the anatomy level under the pre-specified minimum-case
rule.

## Contribution boundary after M5

M5 narrows, rather than broadens, the intended paper claim.

Supported framing:

> In one prospectively frozen synthetic known-deformation study, a promoted registration-
> hyperparameter ensemble produced a local spread signal with positive anatomy-level rank
> informativeness about true spatial error, while case-level inversions and high-error/low-sigma
> blind spots remained. A strong inverse-consistency baseline performed comparably at the anatomy
> level and exhibited a partly different failure pattern.

Not established:

- superiority over ICE;
- absence of blind spots;
- numerical calibration or probabilistic coverage;
- robustness outside the frozen deformation design;
- external-dataset generalization;
- clinical validity or usefulness.

## Durable M5 outputs

`results/m5/` contains compact reviewed evidence:

- `m5_sigma_blind_spots.csv` — the 39 target-sigma blind-spot locations under the frozen rule;
- `m5_case_characterization.csv` — all 30 cases;
- `m5_case_failure_table.csv` — cases meeting at least one M5 failure/weakness condition;
- `m5_anatomy_comparator_table.csv` — anatomy-aware target/comparator summaries.

`research/M5_CHARACTERIZATION.json` is the machine-readable result record. The analysis code
reconstructs the complete 1,500-location pointwise state from the ten hash-pinned source artifacts
and generates anatomy-comparator and case-heterogeneity SVG figures in its requested output
directory. Those larger derived outputs are intentionally not versioned. The implementation lives
in `src/truemargin/m5_characterization.py` with the CLI entry point
`scripts/21_known_gt_m5_characterization.py`.

M5 is complete. M6 may now address numerical calibration as a separate question; any later
robustness or signal-combination study must be frozen before result-bearing execution.
