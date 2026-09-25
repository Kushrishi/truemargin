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

## 2026-09-25 — Make frozen protocol identity public and self-verifying

The curated public repository contains byte-identical copies of the known-GT
base protocol and Amendment 1 from their original private freeze commits.

Verified identities:

- base protocol: private freeze commit
  `44afb8653c8c90b33a438107481f7be4586b0e68`, Git blob
  `98a747c502a4aca6d8e65f8373bc4e62a8f1b7a0`;
- Amendment 1: private freeze commit
  `d37b5a4a7931fdd3947870ba651b097f712ebdb3`, Git blob
  `1eafe77bb847b1a77229e267ef32e6bbedd27bc2`.

Decision: public execution pins and verifies the immutable Git blob identities,
not inaccessible private commit objects. The private commit SHAs remain
historical provenance only. No protocol text, scientific endpoint, cohort,
seed, estimator setting, geometry rule, or inferential rule changed.

## 2026-09-25 — Authorize geometry-only public preflight

A dedicated request now authorizes only the 30 frozen synthetic geometry cases.
The public acquisition helper resolves each predeclared T2 series by its frozen
SeriesInstanceUID identity and fails on missing, ambiguous, or non-T2
resolution. It also retrieves the collection's fused
rad-path resource and copies only the ten required HECaP masks.

Decision: the hosted preflight may validate data identity, transform geometry,
ROI eligibility, folding, landmark uniqueness, and source-domain containment.
It may not execute any of the 270 estimator registrations. Data-resolution or
download failures are infrastructure failures and do not permit anatomy,
series, seed, ROI, deformation, or estimator substitution.

## 2026-09-25 — Retry geometry preflight after pre-geometry acquisition timeout

The first hosted geometry workflow (run `36160471644`, source
`5911ce404b1cc0f167aafb64b54aa95b8aebab0f`) passed its geometry-only
authorization guard and dependency installation, then timed out during the
first legacy NBIA metadata request. No anatomy was resolved, no synthetic
geometry was generated, and no estimator registration ran.

The original geometry request is unchanged and remains identified by Git blob
`a7bf7591850ed90f0cd7bd95ebae3552e77d32c7`.

Decision: authorize one technical acquisition retry with the same scientific
request. Replace the legacy NBIA transport with the current public Imaging Data
Commons interfaces:

- IDC REST v3 for collection/patient/series metadata and exact-series manifests;
- pinned `idc-index==0.12.5` only for anonymous transfer from the returned
  public manifest;
- exact collection `prostate_fused_mri_pathology`;
- the same ten patients and the same frozen final SeriesInstanceUID components;
- fail-closed resolution if a series is missing, ambiguous, wrong-modality, or
  not described as T2.

This is an infrastructure amendment only. It changes no anatomy, series target,
seed, deformation, ROI rule, estimator, endpoint, statistic, or result-bearing
authorization. A retry marker records the failed run and verifies that the
original geometry-request blob has not changed.

## 2026-09-25 — Freeze full DICOM identities before second technical retry

The first IDC-backed retry (workflow run `36162012654`, source
`f7fff7da11af7ce6db115b221c0e850efdd29d0b`) reached current IDC metadata
successfully and then stopped before any image download or geometry because the
implementation incorrectly required the final dot-separated UID component to
equal the historical five-digit Data Retriever folder name.

A metadata-only diagnostic was then run before any known-GT geometry result.
It established that, for every frozen anatomy, the historical five-digit folder
is the final five characters of the intended full `SeriesInstanceUID`. The
same diagnostic uniquely recovered the `T2 AXIAL SM FOV` full UID for all ten
held-out anatomies. No alternative anatomy or series was chosen.

Decision: freeze those ten full DICOM `StudyInstanceUID` /
`SeriesInstanceUID` pairs in `research/KNOWN_GT_SERIES_IDENTITY.json` and
require exact UID equality during acquisition. The historical five-digit folder
remains a compatibility alias and must match the final five UID characters.

This is a provenance clarification and implementation correction, not a change
to the frozen scientific cohort. The original geometry authorization blob,
anatomies, image series, seeds, deformation settings, ROI rules, estimator, and
result-bearing authorization are unchanged.
