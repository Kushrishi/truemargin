# Known-ground-truth geometry preflight result

**Status:** PASS  
**Date:** 2026-09-25  
**Workflow run:** `36172918233`  
**Source revision:** `7ad0299ef1a1ec1434e6519e9fda6100a60b1212`  
**Geometry artifact SHA-256:** `fbf0b60f50e8bd6af2af2af036fe94b4491ad0ffe4ab15863b0ce8f95515c2d2`

This record closes the geometry-only milestone for the frozen
known-ground-truth study. It does **not** contain an uncertainty-vs-error
scientific outcome and does not authorize result-bearing registration.

## Frozen inputs and provenance

The hosted run resolved and downloaded:

- 10 / 10 frozen held-out T2 series;
- 10 / 10 required HECaP masks;
- the exact DICOM identities frozen in
  `research/KNOWN_GT_SERIES_IDENTITY.json`.

The reviewed acquisition record is preserved in
`results/known_gt_data_acquisition.json`.

The run verified the base protocol, Amendment 1, Amendment 2, the historical
technical-retry records, and the amended geometry-only authorization before
execution.

## Geometry result

All **30 / 30** planned synthetic cases passed the amended geometry preflight.

Across all persisted case records:

- exactly 3 replicates were evaluated for each of 10 anatomies;
- exactly 50 fixed-domain ROI landmarks were sampled per case;
- every persisted `all_landmarks_in_fixed_roi` flag is true;
- all persisted displacement summaries and minimum Jacobians are finite;
- every selected transform has minimum evaluated-grid Jacobian strictly above
  zero;
- the smallest eligible fixed-domain ROI contains 562 voxels.

Twenty-nine cases used the original raw transform at topology scale `1.00`.

Exactly one case required the prospectively frozen Amendment-2 backtracking
rule:

- patient: `aaa0072`;
- replicate: `1`;
- case seed: `7001`;
- raw minimum evaluated Jacobian: `-0.010585743635341259`;
- selected topology scale: `0.95`;
- final minimum evaluated Jacobian: `0.05036175275237062`;
- median true landmark displacement after selection:
  `1.4153497816746015 mm`.

No anatomy, seed, raw coefficient direction, ROI rule, landmark count,
estimator, endpoint, or inferential rule was replaced in response to the failed
29 / 30 preflight.

## Evidence files

- `results/hyperparameter_known_gt_geometry_preflight.json`
  - Git blob: `fb90f421c6d11dcaff407d9f8267503925dd4aaa`
  - original uploaded-file SHA-256:
    `fbf0b60f50e8bd6af2af2af036fe94b4491ad0ffe4ab15863b0ce8f95515c2d2`
- `results/known_gt_data_acquisition.json`
  - Git blob: `7481390f2565fbe49aff8faf00f1e59ca0f82c9c`
- GitHub Actions artifact:
  `truemargin-known-gt-geometry-preflight`, artifact ID `10880678315`

## Interpretation boundary

This result establishes only that the frozen known-ground-truth cohort can be
constructed under the reviewed protocol and Amendment 2 while satisfying the
project's geometry-only validity checks.

It does **not** establish that the promoted hyperparameter ensemble:

- tracks true pointwise registration error;
- is calibrated;
- avoids high-error / low-uncertainty blind spots;
- outperforms any comparator;
- generalizes outside this source collection.

Zero result-bearing estimator registrations were used to choose Amendment 2.

The next scientific gate is the prospective comparator-protocol freeze. The
270 planned estimator registrations remain unauthorized until the reviewed
geometry record and comparator protocol are pinned by a separate result-bearing
run request.
