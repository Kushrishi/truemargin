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

## 2026-09-25 — Correct idc-index manifest CLI before another geometry retry

The exact-series geometry attempt (workflow run `36165197037`, source
`b4d3970d95c0a8c54af2a790930c562cc4e52518`) passed both technical-retry
guards and reached the acquisition step with the frozen full DICOM identities.
It then stopped on the first anatomy before any DICOM transfer because
`idc-index==0.12.5` requires `--manifest-file` for
`download-from-manifest`; the implementation had supplied the manifest path
positionally.

Decision: correct only that CLI invocation and add a unit test for the exact
command contract before retrying geometry. The frozen series-identity file,
original geometry-request blob, cohort, seeds, deformation settings, ROI rules,
geometry checks, estimator configuration, and result-bearing authorization are
unchanged. No geometry or estimator registration has yet run in these failed
hosted attempts.

## 2026-09-25 — Preserve 29/30 geometry failure and freeze topology Amendment 2

The first hosted attempt to complete all scientific geometry checks (workflow
run `36167535578`, source
`bcd7099bca8d37f9f895227c386503610639bd03`) successfully acquired all ten
frozen T2 series and all ten HECaP masks, then evaluated all 30 predeclared
synthetic geometries.

Twenty-nine cases passed. `aaa0072`, replicate `1`, case seed `7001`
failed the existing topology criterion with minimum evaluated Jacobian
determinant `-0.0105857`.

No hyperparameter-ensemble registration ran. No sigma/error association,
anatomy effect, p-value, calibration statistic, or comparator result existed.

Decision:

- preserve the exact failed preflight in
  `research/KNOWN_GT_GEOMETRY_PREFLIGHT_RESULT_1.json`;
- do not replace anatomy `aaa0072`;
- do not replace seed `7001`;
- do not redraw its Gaussian B-spline coefficients;
- freeze `docs/hyperparameter_known_gt_protocol_amendment_2.md` before any
  estimator execution;
- apply the same deterministic topology-backtracking rule to all 30 cases;
- rerun the full geometry preflight, not only the failed case;
- keep all 270 result-bearing registrations unauthorized until a complete
  amended 30/30 geometry record is reviewed and separately pinned.

Amendment 2 keeps the original raw coefficient draw at standard deviation 4.0
and tests fixed scales `1.00, 0.95, ..., 0.50`, selecting the largest scale
with finite geometry and strictly positive evaluated-grid Jacobian. If no
predeclared scale passes, the study stops again rather than extending the grid
post hoc.

## 2026-09-25 — Accept amended 30 / 30 geometry preflight

The complete Amendment-2 geometry-only workflow (run `36172918233`, source
`7ad0299ef1a1ec1434e6519e9fda6100a60b1212`) passed its full authorization
history, acquired all 10 frozen T2 series and all 10 required HECaP masks, and
completed all 30 planned geometry cases successfully.

The reviewed machine-readable result contains 30 case records and zero
failures. Twenty-nine cases retained topology scale `1.00`. Only
`aaa0072`, replicate `1`, seed `7001` used the first predeclared
backtracking scale, `0.95`, moving the evaluated minimum Jacobian from
`-0.010585743635341259` to `0.05036175275237062`.

Every case records exactly 50 fixed-domain ROI landmarks and a strictly
positive final evaluated-grid minimum Jacobian. The smallest eligible ROI
contains 562 voxels.

Decision: mark geometry-only milestone M2 complete and preserve the reviewed
geometry and acquisition evidence under `results/`. This result validates the
cohort/provenance/geometry construction only. It does not establish
uncertainty-error informativeness, calibration, blind-spot behavior,
comparative performance, or generalization.

The next scientific gate is a prospective comparator-protocol freeze. The 270
planned result-bearing estimator registrations remain unauthorized until that
protocol and the successful geometry record are pinned by a separate committed
run request.

## 2026-09-25 — Freeze paper-level comparator semantics before estimator outcomes

After the successful 30 / 30 geometry milestone and before any result-bearing
known-GT registration, the comparator audit was completed and
`docs/hyperparameter_known_gt_comparator_protocol.md` was frozen.

Decision:

- retain the nine-member hyperparameter-ensemble sigma as the target method;
- include ensemble-mean inverse-consistency error as the strongest direct local
  comparator;
- include same-modality absolute post-registration residual as a deliberately
  simple local baseline;
- include ensemble-mean Jacobian deviation `abs(J - 1)` as a deformation
  plausibility baseline;
- evaluate every direct local method against the same frozen ensemble-mean
  known-error vector at the same 50 ROI landmarks;
- evaluate Contrastive Discrepancy only on its native case/model-selection axis
  if a pre-result faithful-reproduction audit succeeds;
- keep transformation-equivariance UQ and CONReg as related work rather than
  inventing classical adaptations;
- exclude historical curvature unless a separate pre-result audit recovers a
  complete stable method.

The existing TrueMargin primary anatomy-level sign test remains unchanged.
Comparator sign tests are secondary and Holm-corrected as one family. Paired
target-versus-comparator differences are effect-size summaries with anatomy
bootstrap intervals rather than post-hoc winner tests.

A post-geometry execution-control amendment now requires the final run request
to pin the reviewed geometry evidence, all protocol blobs, comparator protocol,
implementation identities, CD feasibility decision, exact source revision, and
registration budget before any result-bearing execution.

The direct frozen budget is 270 forward + 270 reverse registrations = 540
registrations before any feasible CD-specific additional work.

## 2026-09-25 — Freeze CD infeasible for the current confirmatory study

Before any result-bearing known-ground-truth registration, the prospective
Contrastive Discrepancy feasibility gate was completed.

The authors' current publication page links code only through
`https://anonymous.4open.science/r/dbc-B401/`. The public paper description
establishes CD as a label-free deformation-field discrepancy for testing-time
hyperparameter/model selection under transformed observations, but does not pin
the exact perturbation parameters and aggregation semantics required for a
faithful reproduction.

Three clean-hosted source-retrieval attempts were made before any estimator
outcome:

- workflow `36181998705`: historical Anonymous-GitHub API route -> HTTP 403;
- workflow `36182323709`: current public files route, confirmed against the
  current `tdurieux/anonymous_github` implementation -> HTTP 403;
- workflow `36182461898`: real headless Chrome on the public repository page
  -> Cloudflare security-verification page only.

Decision: set `CD_FEASIBLE=False` for this confirmatory study and preserve the
machine-readable audit in `research/KNOWN_GT_CD_FEASIBILITY.json`.

This is a reproducibility/implementation decision, not evidence against CD's
scientific validity. Do not implement a bespoke CD analogue from the abstract
or high-level description, and do not add a different case-level comparator
after seeing known-GT outcomes.

The frozen result-bearing budget is therefore exactly:

```text
270 forward registrations + 270 reverse registrations = 540 registrations
```

The result-bearing authorization guard is hard-locked to this CD decision and
budget. No primary or comparator known-GT outcome existed when this decision
was frozen.
