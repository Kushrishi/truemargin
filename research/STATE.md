# Current research state

**Updated:** 2026-09-25  
**Status:** active public research program  
**Publication status:** no submitted, accepted, or published paper

This file is the canonical short-form state for TrueMargin.

## Research question

When a deformable image-registration method reports local uncertainty, under
what conditions does that signal contain useful information about true local
spatial registration error?

The current program separates:

1. operational variability;
2. pointwise error informativeness;
3. numerical calibration;
4. blind-spot/failure behavior;
5. generalization.

No one axis is treated as a substitute for the others.

## Historical evidence boundary

Earlier T2-to-DCE experiments used a zero-displacement reference assumption on
real data. That value is not independently verified pointwise registration
ground truth.

Historical real-data results may motivate hypotheses and operational checks,
but they must not be described as definitive pointwise error validation.

The older manuscript, product framing, and historical real-data narrative are
archived and are not the current paper.

## Prospective rebuild sequence

### 1. Corrected input-intensity perturbation ensemble

**Result:** failed prospective Gate A.

No tested nonzero relative-intensity perturbation satisfied the frozen
combination of completeness, non-inertness, and proxy-error degradation limits.

The perturbation grid was not widened after observing the result.

### 2. Registration convergence

**Result:** mesh 3 / 15 maximum iterations selected.

The prospectively specified convergence gate found 15 iterations to be the
smallest candidate budget passing the frozen global field-stability criterion.

This is a regime-specific operational result, not a universal convergence
claim.

### 3. Initialization-sensitivity ensemble

**Result:** failed prospective promotion.

No tested nonzero B-spline initialization perturbation strength passed the
frozen completeness/non-inertness rule.

The grid was not widened after observing the result.

### 4. Registration-hyperparameter ensemble

**Result:** passed operational promotion.

Frozen estimator:

- Mattes-MI bins: 32, 50, 64
- LBFGSB gradient tolerance: 1e-4, 1e-5, 1e-6
- Cartesian members: 9
- mesh size: 3
- maximum iterations: 15
- center_first: false

The mechanism completed all nine members in all five frozen sensitivity
patients and exceeded the predeclared repeatability/resolution floor in four of
five.

This result establishes **operational promotion only**.

It does not establish that sigma tracks true error, is calibrated, avoids blind
spots, or generalizes.

### 5. Hyperparameter known-ground-truth evaluation

**Status:** base protocol + Amendments 1 and 2 are frozen. The full amended geometry preflight passed 30/30 cases from all 10 frozen anatomies. Twenty-nine cases used topology scale 1.00; only `aaa0072`, replicate 1, seed 7001 used the prospectively frozen 0.95 backtracking scale, moving the evaluated minimum Jacobian from -0.0105857 to +0.0503618. No result-bearing estimator registration has run. The comparator protocol, direct-comparator implementation, and CD feasibility decision are frozen and tested; M3 is complete. A separate source-pinned result-bearing request is now frozen on this authorization branch; no result-bearing outcome existed when it was created.

Primary design:

- 10 anatomies not used for mechanism promotion;
- 3 deformation replicates per anatomy;
- 30 total synthetic cases;
- exact known B-spline transform direction;
- 9 estimator registrations per case;
- 270 total planned registrations;
- 50 spatial samples per case;
- per-case Spearman association between uncertainty and true error;
- anatomy-aware aggregation;
- exact one-sided anatomy-level sign test;
- 10,000-replicate anatomy bootstrap interval;
- strict failure and assessability rules.

The old synthetic harness is not treated as authoritative for this stage because
the new protocol explicitly corrects a transform-direction ambiguity.

## Current bottleneck

M1-M3 are complete.

The frozen direct local comparison now includes:

- the primary nine-member sigma target;
- ensemble-mean inverse-consistency error using the same nine-member grid in reverse;
- same-modality absolute post-registration residual;
- ensemble-mean Jacobian deviation.

Contrastive Discrepancy is prospectively excluded from the current confirmatory
study. The authors' current publication page links only an Anonymous-GitHub
snapshot; direct current/legacy API access returned HTTP 403 in clean hosted
runners and a real hosted Chrome session reached only Cloudflare security
verification. Without the released source, the public paper metadata does not
pin enough implementation detail to reproduce CD faithfully without inventing
choices. The exact pre-result decision is frozen in
`research/KNOWN_GT_CD_FEASIBILITY.json`.

M4 is now authorized prospectively by
`research/KNOWN_GT_RUN_REQUEST.json`, but no result-bearing registration has
run at the authorization freeze.

The request pins:

- implementation source `f52aee24b49327bf7989ae0746dbf2ad981510d1`;
- its green CI run `36184383591`;
- all protocol, geometry, acquisition, and CD-feasibility blobs;
- the exact execution/orchestration blobs;
- 10 frozen anatomy shards x 3 cases;
- **270 forward + 270 reverse = 540 planned registrations**;
- CD=false with zero CD registrations.

Execution is sharded only for infrastructure robustness. Each anatomy shard
produces the same canonical provenance checkpoints consumed by the unchanged
scientific runner; a final job refuses to aggregate unless all 30 checkpoints
are present.

The existing 30-case evaluation must not be retuned based on future results.
Scientific failures are retained and are not grounds for replacing cases,
members, seeds, or comparators.

## Current source-of-truth order

1. frozen prospective protocol/result files in `docs/`;
2. this file;
3. `research/CLAIMS.md`;
4. current README;
5. archived historical material.

Website and LinkedIn copy must never be stronger than this state.
