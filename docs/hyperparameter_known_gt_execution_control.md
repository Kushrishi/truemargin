# Known-ground-truth execution control

**Status:** frozen before geometry preflight and result-bearing execution  
**Date:** 2026-09-25  
**Scientific protocol:** `docs/hyperparameter_known_gt_protocol.md` + Amendment 1  
**Observed known-GT outcomes at freeze:** none

This document adds an execution-safety boundary without changing the scientific
design.

## Modes

The known-ground-truth runner must be invoked explicitly in exactly one mode:

- `--geometry-only`: validate all 30 predeclared synthetic geometries and exit
  before any estimator registration;
- `--run-result-bearing`: proceed to the frozen nine-member estimator only
  after a reviewed run authorization exists.

A plain invocation is invalid.

## Geometry-first rule

The geometry-only preflight remains the first allowed execution. Its output must
be reviewed and preserved before result-bearing authorization.

The reviewed geometry record must establish the already-frozen requirements,
including:

- all 30 predeclared cases;
- finite transforms and displacement fields;
- no folding;
- sufficient fixed-domain HECaP ROI voxels;
- exactly 50 unique in-ROI landmarks per case;
- transformed landmarks inside the moving-source domain.

A failed geometry preflight does not authorize seed, anatomy, deformation, ROI,
or estimator substitution.

## Result-bearing authorization

`research/KNOWN_GT_RUN_REQUEST.json` is intentionally absent until the
geometry-only result has been reviewed.

When eventually created, it must pin:

- the exact study identity;
- the ten held-out anatomies;
- three replicates per anatomy;
- nine estimator members;
- 270 planned registrations;
- base-protocol and Amendment-1 freeze identifiers;
- the path and SHA-256 of the reviewed geometry-preflight record.

The runner verifies those fields and the reviewed record hash before any
result-bearing registration begins.

The authorization file may not change the frozen estimator, cohort, seeds,
statistics, assessability rules, or interpretation criteria.

## Failure discipline

Infrastructure failures may be diagnosed and rerun only without changing the
frozen scientific configuration. Unfavorable scientific outcomes are not
infrastructure failures.

No result-bearing run may be authorized merely because the geometry looks
favorable; geometry eligibility is a validity check, not an outcome-selection
criterion.

## Frozen markers

`KNOWN_GT_EXECUTION_CONTROL=FROZEN`

`KNOWN_GT_GEOMETRY_PREFLIGHT_RUN_AT_FREEZE=NO`

`KNOWN_GT_RESULT_BEARING_RUN_AT_FREEZE=NO`

`KNOWN_GT_RUN_REQUEST_PRESENT_AT_FREEZE=NO`
