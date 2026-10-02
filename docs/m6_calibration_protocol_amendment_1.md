# M6 calibration protocol amendment 1

**Status:** FROZEN after deformation-only preflight 1 and before any M6 estimator registration  
**Date:** 2026-10-02  
**Base protocol:** `docs/m6_calibration_protocol.md`  
**Reason:** pre-result sampling-rule incompatibility exposed by the first external-substrate deformation preflight  
**Observed M6 estimator outcomes at freeze:** none

This amendment changes only the spatial eligibility rule used to freeze the 50 pointwise evaluation locations per anatomy. The original M6 protocol remains in the repository unchanged. Where this amendment conflicts with Section 8 of the base protocol, this amendment governs.

## 1. Triggering preflight observation

The source-pinned deformation-only workflow run `37016774222`, attempt 2, executed on all 60 predeclared training anatomies before any M6 estimator registration.

The run completed deformation preflight for 56 anatomies and stopped on four predeclared Prostate-3T anatomies:

- `Prostate3T-01-0001`
- `Prostate3T-01-0008`
- `Prostate3T-01-0013`
- `Prostate3T-01-0028`

Each failure had the same cause:

```text
fixed ROI has only 0 eligible voxels after 8-voxel margin; need 50
```

All four source volumes have 15 axial slices at approximately 4 mm through-plane spacing. Under the frozen index-space rule, a candidate had to satisfy both `z >= 8` and `z < 15 - 8`, which is impossible. The failure therefore arises from the discrete crop-boundary rule, not from an empty prostate ROI or a failed topology check.

The failed preflight is preserved in `research/M6_DEFORMATION_PREFLIGHT_RESULT_1.json`.

### Information observed before this amendment

The deformation-only preflight exposed geometry-only information by design. For the 56 completed anatomies, it produced known-deformation geometry, topology checks, frozen-ROI geometry, point locations under the original rule, and true-displacement summaries. No forward registration, reverse registration, TrueMargin sigma, inverse-consistency error, registration error, conformal score, calibration threshold, coverage result, or evaluation endpoint existed when this amendment was frozen.

No rule in this amendment was selected using estimator performance or calibration behavior.

## 2. Why the 8-voxel rule should not be carried forward unchanged

The 8-voxel margin originated in the M4 synthetic protocol as a conservative crop-boundary safeguard for point sampling. M4 amendment 1 later narrowed the sampling population to a synthetically warped ROI but retained the same index-space margin.

For M6, the external substrate contains materially different acquisition geometries. Applying a fixed number of voxels independently to every axis makes the safety rule depend strongly on voxel anisotropy and slice count. In the four failed Prostate-3T anatomies, eight through-plane voxels correspond to roughly 32 mm on each side and eliminate the entire candidate population.

The scientific requirement is not an eight-index exclusion for its own sake. The requirement is that an evaluation point belong to the frozen fixed-domain prostate ROI and that its known transformed location be valid in the moving-source domain.

M6 can enforce that requirement directly.

## 3. Amended spatial eligibility rule

This section supersedes the candidate-voxel boundary-margin rule in Section 8 of `docs/m6_calibration_protocol.md`.

For every one of the 60 frozen M6 training anatomies:

1. construct the source image and source prostate ROI exactly as already frozen;
2. construct the same topology-safe known transform `T_known` from the same frozen deformation seed and backtracking rule;
3. construct the fixed-domain prostate ROI exactly as already frozen:

   ```text
   fixed_roi(x) = moving_roi(T_known(x))
   ```

4. define candidate locations as fixed-grid voxels satisfying both:
   - `fixed_roi > 0`; and
   - the exact known transformed physical point `T_known(x)` lies inside the moving-source image domain under the existing continuous-index containment convention;
5. require at least 50 eligible candidates;
6. sample exactly 50 unique candidates uniformly without replacement using the already frozen `points` seed for that anatomy;
7. recheck transformed-point containment for every selected location and fail closed on any violation.

There is no additional fixed voxel-count margin from the crop boundary.

The eligibility rule is applied identically to both source collections and to both frozen M6 roles. No anatomy-specific margin, source-specific exception, fallback margin, or outcome-dependent point removal is allowed.

## 4. Full preflight rerun requirement

The first preflight's 56 completed point sets are not retained for M6 analysis.

After this amendment is merged, rerun the deformation-only preflight from the beginning for all 60 anatomies using:

- the same anatomy identities;
- the same 30/30 calibration/evaluation role assignment;
- the same deformation seeds;
- the same noise seeds;
- the same point seeds;
- the same B-spline deformation distribution;
- the same topology-backtracking schedule;
- the same 50-point requirement; and
- the amended transform-safe ROI eligibility rule above.

Registration remains unauthorized unless the amended preflight completes for all 60 anatomies.

## 5. What does not change

This amendment does not change:

- the 60-anatomy M6 training cohort;
- the source-stratified 30 calibration / 30 evaluation split;
- the untouched leaderboard and test holdout for M7;
- crop construction or 15-voxel crop padding;
- the one-deformation-per-anatomy design;
- deformation coefficient distribution or mesh size;
- topology backtracking;
- the frozen nine-member TrueMargin estimator;
- same-ensemble ICE as the secondary calibrated comparator;
- 50 sampled locations per anatomy;
- deterministic seed identities;
- HCP with anatomy as the group;
- the 80%, 90%, and 95% coverage grid or 90% primary target;
- signal-zero abstention semantics;
- calibration/evaluation separation;
- the prohibition on changing rules after calibration outcomes are observed; or
- any completed M1-M5 result or claim.

## 6. Updated interpretation of the M6 spatial target

The M6 pointwise population is now explicitly:

> a uniformly sampled transform-safe fixed-domain prostate-ROI voxel under the frozen synthetic deformation design.

Any successful HCP statement remains source-specific and marginal over a new exchangeable anatomy and a sampled eligible ROI location. It is not simultaneous whole-volume coverage, conditional coverage at every fixed voxel, or a clinical guarantee.

## 7. Stop rule

If the amended full 60-anatomy deformation preflight still fails, stop again before registration. Preserve the failure and reassess the geometry-only design without inspecting estimator or calibration outcomes.
