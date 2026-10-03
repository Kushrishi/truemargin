# M6 calibration protocol amendment 1

**Status:** FROZEN before any M6 registration, sigma, ICE, calibration fit, or evaluation  
**Date:** 2026-10-02  
**Base protocol:** `docs/m6_calibration_protocol.md`  
**Reason:** deformation-only geometry preflight exposed an infeasible voxel-index boundary rule on thin anisotropic source volumes  
**Observed result-bearing M6 outcomes at freeze:** none

This amendment changes only the fixed-domain ROI boundary-margin rule used to select the 50 frozen M6 spatial locations. The original protocol remains unchanged in repository history. Where this amendment conflicts with the base M6 protocol, this amendment governs.

## 1. Preflight evidence that triggered the amendment

The first source-pinned 60-anatomy deformation-only preflight ran under the frozen protocol before any M6 registration was authorized.

It completed geometry for 56 of 60 anatomies and stopped on four Prostate-3T anatomies:

- `Prostate3T-01-0001`
- `Prostate3T-01-0008`
- `Prostate3T-01-0013`
- `Prostate3T-01-0028`

Each failure occurred at the same point-selection gate:

```text
fixed ROI has only 0 eligible voxels after 8-voxel margin; need 50
```

The previously frozen training-geometry audit shows that each of these four anatomies has a 15-slice source image in the through-plane direction with approximately 4 mm slice spacing. Under the original index-space rule, a voxel must satisfy both:

```text
z >= 8
z < 15 - 8
```

No integer z index can satisfy those inequalities. The empty eligible set is therefore a deterministic consequence of applying an 8-voxel symmetric margin to a 15-slice axis. It is not a registration failure, an uncertainty result, a calibration result, or an unfavorable estimator outcome.

The first preflight is preserved in `research/M6_DEFORMATION_PREFLIGHT_RESULT_1.json` and is not overwritten or reinterpreted as a passing run.

## 2. Scientific rationale

The boundary margin exists to keep sampled spatial locations away from crop edges, where interpolation and out-of-domain behavior can make local error evaluation fragile.

A fixed voxel count does not represent a fixed spatial distance on anisotropic MRI. In the NCI-ISBI challenge training data, in-plane spacing is roughly 0.4 to 0.75 mm while through-plane spacing is roughly 3 to 4 mm. Eight voxels therefore represent only a few millimetres in-plane but roughly 24 to 32 mm through-plane.

For M6, the boundary safeguard is therefore expressed as one physical distance and converted back to an integer voxel margin on each axis.

## 3. Amended boundary rule

For each prepared anatomy, let the SimpleITK voxel spacing be:

```text
spacing_xyz = (sx, sy, sz)
```

Define the physical reference margin as:

```text
reference_margin_mm = 8 * min(sx, sy, sz)
```

For each physical axis, define:

```text
margin_axis_voxels = ceil(reference_margin_mm / spacing_axis_mm)
```

with a minimum of one voxel on every axis.

The numpy array uses z/y/x order, so the final integer margin vector is recorded as:

```text
margin_zyx = (margin_z, margin_y, margin_x)
```

A fixed-domain ROI voxel is eligible only if its index is at least `margin_zyx` from the low crop boundary and at least `margin_zyx` from the high crop boundary, componentwise.

This rule preserves the original eight-voxel margin on the finest-resolution axis or axes while preventing coarse through-plane spacing from creating a physically disproportionate exclusion zone.

## 4. What must be rerun

The deformation-only preflight must be rerun for all 60 training anatomies, not only the four failures.

The rerun must preserve:

- the exact 60 PatientIDs and SeriesInstanceUIDs;
- the frozen 30/30 calibration/evaluation split;
- the source-stratified 15/15 role balance within each source;
- one deformation realization per anatomy;
- every PatientID-derived deformation, noise, and point seed;
- mesh size 4;
- raw B-spline coefficient mean 0.0 and standard deviation 4.0;
- the frozen Amendment-2 topology-backtracking scale grid;
- 15-voxel crop padding, subject to source-image boundaries;
- the prostate ROI label union `{1, 2}`;
- exactly 50 unique points sampled uniformly without replacement from the amended eligible set;
- the requirement that every transformed point remains inside the moving-source physical domain.

No anatomy, seed, deformation, split role, or source identity may be replaced because of the first preflight failure.

## 5. Required amended-preflight record

For every complete anatomy, record at minimum:

- prepared crop shape in z/y/x order;
- voxel spacing in x/y/z millimetres;
- physical reference margin in millimetres;
- integer boundary margins in z/y/x voxel order;
- fixed-domain ROI voxel count;
- eligible fixed-domain ROI voxel count;
- sampled point coordinates;
- transformed point coordinates;
- true displacement vectors;
- raw and selected Jacobian minima;
- selected topology scale;
- all frozen random seeds and source hashes already required by the base preflight.

Any anatomy with fewer than 50 eligible locations under the amended rule remains a scientific preflight failure. Stop before registration and preserve the exact failure. Do not tune the margin again from that anatomy's estimator behavior, because no estimator behavior is authorized at this stage.

## 6. Authorization boundary

This amendment does not authorize:

- forward registration;
- reverse registration;
- TrueMargin sigma computation;
- ICE computation;
- conformal score computation;
- HCP threshold fitting;
- evaluation-set access;
- coverage analysis;
- leaderboard or test use;
- any M7 robustness analysis.

The first result-bearing M6 calibration phase remains separately unauthorized until a complete amended 60-anatomy deformation preflight is recorded and reviewed.

## 7. Interpretation boundary

This amendment is a geometry-feasibility correction made after observing only a non-result-bearing preflight failure. It does not modify M1 through M5, does not use M6 estimator outcomes, and does not improve or weaken any observed uncertainty result.
