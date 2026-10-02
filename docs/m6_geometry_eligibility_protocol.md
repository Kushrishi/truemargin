# M6 training geometry and eligibility audit

**Date:** 2026-10-01  
**State:** prospective geometry-only gate  
**Result-bearing M6 authorized:** **no**

## Purpose

Establish, before any M6 cohort assignment or registration outcome exists, which of the 60 official
NCI-ISBI challenge training anatomies can support the frozen M6 image/ROI geometry pipeline.

This gate is intentionally separate from calibration. It may acquire the already identified source
DICOM series and official training NRRD labels, but it must not generate M6 deformations, run the
registration estimator, compute ensemble sigma or ICE, assign calibration/evaluation roles, or fit a
calibration transform.

The successful external-input identity audit on workflow run `36944145013` is the prerequisite for
this gate. That audit resolved all 80 official challenge image/annotation identities and found the
training partition to contain exactly 30 `Prostate-3T` and 30 `PROSTATE-DIAGNOSIS` anatomies.

## Why geometry precedes the split

Calibration/evaluation roles must not be assigned until objective geometry eligibility is known.
Otherwise a later exclusion could force outcome-aware replacement or source imbalance.

The preferred architecture remains a source-balanced `30 / 30` calibration/evaluation split of the
60 training anatomies if all 60 pass this gate. The official 10-case leaderboard and 10-case test
partitions remain untouched for M7 robustness. This document does **not** assign any of those roles.

## Frozen eligibility principles

Eligibility uses only source identity, DICOM/NRRD geometry, and label semantics.

A case is eligible only if:

1. the official training series resolves to exactly one training PatientID;
2. the source DICOM series and official NRRD segmentation are both readable as 3D volumes;
3. the NRRD contains only the challenge label values `0`, `1`, and `2`;
4. the CG/PZ foreground is non-empty;
5. every foreground label-voxel centre lies inside the DICOM image physical domain, allowing only a
   half-voxel image-boundary convention plus numerical tolerance;
6. identity nearest-neighbour resampling of the label onto the DICOM grid retains non-empty
   foreground and does not invent label values.

No registration-error, uncertainty, ICE, calibration, or deformation outcome can affect eligibility.

## Dimension mismatch policy

Raw array-size equality is **not** an eligibility requirement.

The official challenge record documents `ProstateDx-01-0055` with a `400 x 400 x 23` segmentation
and a `400 x 400 x 34` DICOM series while stating that the labels are properly spatially placed.
Therefore `ProstateDx-01-0055` receives no exception and no automatic exclusion: it is evaluated by
the same physical-space containment and resampling rules as every other anatomy.

This policy is frozen before the hosted geometry audit is run.

## Outputs

The hosted audit must record, for every training anatomy:

- PatientID and SeriesInstanceUID;
- source collection;
- image and label size, spacing, origin, and direction;
- observed label values;
- foreground voxel count;
- foreground voxels outside the image physical domain;
- nearest-neighbour resampled foreground count and label values;
- whether image/label array sizes are equal;
- the final geometry-only eligibility decision;
- SHA-256 identities for the downloaded DICOM-series archive and NRRD label.

The aggregate record must contain the exact source composition, eligible/ineligible counts, the
full `ProstateDx-01-0055` record, source manifest/label-archive hashes, workflow/source provenance,
and a closed result-bearing authorization boundary.

## Decision rule after the audit

- **60 / 60 eligible:** proceed to a separate PR that freezes the deterministic source-stratified
  calibration/evaluation assignment and the HCP calibration protocol.
- **Any ineligible anatomy:** do not assign roles. Review only the geometry evidence, define any
  scientifically necessary deterministic handling or reduced-cohort rule prospectively, and rerun
  this geometry gate before exposing M6 registration outcomes.

No training-side reserve or replacement rule is created merely to preserve a desired sample size.

## Downstream statistical boundary

The leading calibration method remains Hierarchical Conformal Prediction (HCP), with anatomy as the
group and sampled ROI locations nested within anatomy. Its intended claim is marginal coverage for a
new location in a new exchangeable anatomy, not simultaneous whole-volume coverage or guaranteed
coverage within every individual anatomy.

The exact HCP score, coverage levels, sigma/ICE comparator policy, ROI sampling rule, deformation
rule, and deterministic cohort IDs remain downstream protocol-freeze decisions.

**No result-bearing M6 execution is authorized by this document.**
