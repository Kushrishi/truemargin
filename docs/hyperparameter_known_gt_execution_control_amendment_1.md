# Known-ground-truth execution-control amendment 1

**Status:** FROZEN after successful geometry-only preflight and comparator-protocol freeze, before any result-bearing known-GT estimator execution  
**Date:** 2026-09-25  
**Base execution control:** `docs/hyperparameter_known_gt_execution_control.md`  
**Observed result-bearing known-GT outcomes at freeze:** none

This amendment updates only the execution gate after geometry M2. The original
execution-control document remains preserved as the pre-geometry record.

## 1. Reviewed geometry prerequisite

Result-bearing execution may not begin unless the run request pins the reviewed
successful geometry evidence:

- path:
  `results/hyperparameter_known_gt_geometry_preflight.json`
- Git blob:
  `fb90f421c6d11dcaff407d9f8267503925dd4aaa`
- original uploaded-file SHA-256:
  `fbf0b60f50e8bd6af2af2af036fe94b4491ad0ffe4ab15863b0ce8f95515c2d2`
- reviewed workflow run:
  `36172918233`
- reviewed source revision:
  `7ad0299ef1a1ec1434e6519e9fda6100a60b1212`
- result:
  `30 / 30` amended geometry cases passed.

The run request must also pin the acquisition evidence path
`results/known_gt_data_acquisition.json`.

## 2. Scientific protocol identities

The result-bearing run request must pin all governing protocol identities:

- base protocol Git blob:
  `98a747c502a4aca6d8e65f8373bc4e62a8f1b7a0`;
- Amendment 1 Git blob:
  `1eafe77bb847b1a77229e267ef32e6bbedd27bc2`;
- Amendment 2 Git blob:
  `bcd0a6b970891724c755cde75111f56d6fad7492`;
- comparator protocol Git blob:
  `2d383d3bed7503e2ceaecf36f599e7965726a18d`.

The runner must verify these identities from repository contents before the
first result-bearing registration starts.

## 3. Frozen primary registration budget

The forward TrueMargin primary remains exactly:

```text
10 anatomies x 3 cases x 9 members = 270 forward registrations
```

No primary member may be dropped, replaced, or added.

## 4. Frozen direct-comparator budget

Inverse-consistency evaluation adds the same nine-member grid in the reverse
image direction:

```text
10 anatomies x 3 cases x 9 members = 270 reverse registrations
```

Therefore, before any optional Contrastive Discrepancy work, the frozen
result-bearing registration budget is:

```text
270 forward + 270 reverse = 540 registrations
```

The absolute-residual and Jacobian-deviation comparators reuse the forward
ensemble mean and add no registration members.

## 5. Contrastive Discrepancy feasibility gate

The comparator protocol requires a non-result-bearing implementation audit
before CD can be included.

The final result-bearing run request must contain exactly one of:

### 5.1 CD feasible

If faithful reproduction succeeds before known-GT outcomes are observed, the
run request must pin:

- `cd_feasible: true`;
- the released source snapshot/archive identity;
- the local adapter implementation identity;
- exact transformation/perturbation parameters;
- exact CD aggregation semantics;
- exact additional registration count;
- a passing non-result-bearing feasibility/test record.

The total planned registration count must include those additional runs.

### 5.2 CD not feasible

If faithful reproduction fails before known-GT outcomes are observed, the run
request must pin:

- `cd_feasible: false`;
- the reviewed feasibility record;
- the reason faithful reproduction is not valid for this classical setup;
- total planned registration count `540`.

Do not create a bespoke CD analogue after result-bearing outcomes are visible.

## 6. Result-bearing source revision

The final request must pin an exact Git source revision containing:

- the frozen forward estimator implementation;
- reverse-ensemble ICE implementation;
- residual and Jacobian comparators;
- comparator statistics;
- all required tests;
- the finalized CD feasibility decision;
- the run-authorization guard itself.

The request must not point to a floating branch name.

## 7. Required run-request fields

`research/KNOWN_GT_RUN_REQUEST.json` remains intentionally absent until
implementation preflight is complete.

When created, it must pin at least:

- schema version;
- study identity;
- `authorized_mode = "result-bearing"`;
- `result_bearing_authorized = true`;
- exact source Git SHA;
- 10 held-out anatomies in frozen order;
- 3 cases per anatomy;
- 9 forward members per case;
- 270 forward registrations;
- 270 reverse registrations;
- CD feasibility decision;
- exact total planned registrations;
- all protocol/amendment/comparator Git blobs;
- reviewed geometry Git blob and uploaded-file SHA-256;
- acquisition-evidence Git blob;
- comparator implementation/test record identities.

Any mismatch is a hard stop before registration.

## 8. Outcome isolation

Creating or reviewing the run request must not inspect:

- sigma/error associations;
- comparator/error associations;
- anatomy effects;
- sign-test p-values;
- bootstrap intervals;
- blind-spot rates;
- CD model-selection outcomes.

Those quantities may exist only after the final request is committed and the
authorized result-bearing run begins.

## 9. Failure discipline

Infrastructure failures may be retried only with the exact same committed
scientific request and source revision unless a new prospective amendment is
explicitly frozen before relevant outcomes are observed.

Scientific failures, incomplete registrations, weak correlations, unfavorable
comparator results, and negative primary evidence are not infrastructure
failures.

## Frozen markers

`KNOWN_GT_EXECUTION_CONTROL_AMENDMENT_1=FROZEN`

`KNOWN_GT_GEOMETRY_PREFLIGHT_STATUS_AT_FREEZE=30_PASS_0_FAIL`

`KNOWN_GT_COMPARATOR_PROTOCOL_FROZEN_AT_FREEZE=YES`

`KNOWN_GT_RESULT_BEARING_RUN_AT_FREEZE=NO`

`KNOWN_GT_ESTIMATOR_OUTCOME_OBSERVED_AT_FREEZE=NO`
