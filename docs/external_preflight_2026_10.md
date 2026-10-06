# Official lung archive resolution and operational preflight

Date: 2026-10-06. Prospective external outcomes remain unopened.

## Dataset unit resolved

| Official archive | MD5 verified | SHA-256 measured | Scan pairs / IDs |
| --- | --- | --- | --- |
| `training.zip`, [Zenodo 3835682](https://zenodo.org/records/3835682) | `cd4ef606641b915603a8a0f6a4664a6c` | `920e33e9cac0e99bacfee3243dc908ac0dd92c1ac781567c7c3328ddb0ae5f88` | 20: 001–020 |
| `testData.zip`, [Zenodo 4048761](https://zenodo.org/records/4048761) | `573c7f936e9af111fa536559238af172` | `45e2742d4fa675294e315bf2afac9f768aa78e2771d1326a9ffe96ff6377a215` | 10: 021–030 |

Training contains 20 expiration scans, 20 inspiration scans and 40 corresponding masks under `training/scans` and `training/lungMasks`. Test ZIP scan names identify ten complete expiration/inspiration pairs under `scans`; masks are under `lungMasks`. Archive metadata was inventoried without opening member payloads. Training scans/masks alone were extracted. Test archive payloads remain unextracted. Exact member names, sizes, CRCs and training extracted-file SHA-256 values are in the session evidence package.

The existing preflight's expected **20 complete training pairs is correct**. The challenge paper uses scan pairs; webpage case/volume wording should not be converted to ten training pairs. No expected count was adjusted to make a check pass. The prior ambiguity note is resolved by actual archive identity, not retrospective outcome fitting.

Records are publicly downloadable, but the existing protocol did not identify a permissive redistribution license. No medical image, archive or landmark payload is committed or included in the review package.

## Training-only geometry

Existing `scripts/preflight_external_lung.py` passed all twenty pairs unchanged. All fixed/moving grids match and intensities are finite. Example case 001: shape zyx 208×192×192, spacing xyz (1.75,1.25,1.75) mm, identity direction, shared nonzero origin. Geometry output preserves each case's origin/direction rather than assuming a zero-origin physical grid. Masks are present; landmark content is not required.

The new archive-inventory tests prohibit ZIP payload opening and reject mismatched checksums/unsafe member paths. Combined with existing geometry tests, eight focused tests pass. This is training geometry validation, not coordinate/interpolation validation for held-out manual landmarks.

## Unchanged-estimator operational probe

The first lexicographic training pair (001) was selected before outcomes. One forward member used frozen mesh=3, max iterations=15, bins=32, gradient tolerance=1e-4 and no centering. The supervising command declared a 180-second wall budget via `timeout 180`; SimpleITK 2.5.6 retained its default nine threads. No normalization, downsampling, cropping or estimator-parameter changes were made.

The invocation exceeded the budget and exited 124 before returning a displacement field. No member completion, optimizer-convergence outcome or output-geometry result is available. A live RSS sample near 138 seconds was 1,134,252 KiB; this is an observed sample, **not measured peak RSS**. No reverse member or additional ensemble member was launched. Empty redirected output is retained alongside an explicit timeout record.

This establishes only that the first member did not complete inside the bounded resource probe. It does NOT establish intrinsic estimator infeasibility or a scientific transfer failure. Full forward/reverse nine-member feasibility remains a gate. A later unchanged-estimator assessment may use an explicitly justified larger operational budget; it must not tune scientific parameters to rescue performance.

The historical array estimator preserves spacing but discards physical origin/direction in its internal image construction. Identity-direction/common-origin training grids permit this runtime-only probe; a tested conversion back to original physical coordinates remains required before landmark evaluation. No physical-coordinate correctness is claimed by this probe.

## External run identity — NOT frozen/authorized

### Autonomous continuation measurement

The same member completed under a prospectively extended 900-second envelope:
564.219 seconds, peak RSS 1,131,884 KiB, finite displacement and expected
[3,208,192,192] shape. Its scientific parameters and default nine ITK threads
were unchanged. An opt-in iteration observer exposes training objective and
elapsed time; a synthetic test compares observed/unobserved outputs at 1e-12
tolerance (multithreaded reductions need not be byte-identical).

This supersedes an interpretation of the 180-second budget as a feasibility
failure, while preserving that original diagnostic. Remaining forward members
and a reverse member are undergoing training-only runtime characterization.
No scheduling speedup or full-study feasibility is claimed from this one member.

`external_analysis.py` now has synthetic tests for original-origin/direction
physical XYZ conversion, scalar/vector trilinear interpolation, axis order,
out-of-bounds rejection, case-level Spearman, exact sign test, deterministic
10,000-case-bootstrap summaries and explicit undefined/comparator failures.
Prospective implementation seed is 20261006, percentile 95% intervals; it is
not an outcome-fitted choice. This is an analysis boundary, not a completed
external evaluator or pre-outcome run freeze.

Official MDL-UzL/L2R evaluation configuration independently names test IDs
0021–0030. A metadata-only tree audit found public validation landmark paths
for 0001–0003, but did not establish a downloadable source for the ten test
landmark files. Neither archive contains landmark payloads. No CSV was opened.
Authorized access to the exact test correspondences and their coordinate
conventions is still required; public three-case validation files must not be
substituted for the frozen ten-case cohort. See the official repository:
https://github.com/MDL-UzL/L2R/tree/main/evaluation.

Archive identities and candidate test IDs are now known. The result-bearing freeze is intentionally incomplete:

- repository/analysis script hashes: no accepted external evaluator exists yet;
- environment: current runtime measured, not an approved locked external environment;
- estimator: unchanged frozen parameters above;
- comparators: existing protocol requires forward/reverse ensemble-mean ICE, residual and Jacobian deviation;
- coordinates/interpolation: synthetic utility tests pass; actual landmark format/conventions and complete integration remain unverified;
- endpoints: existing case-level median rho, positive-case count, exact one-sided sign test, 10,000 case bootstraps; bootstrap seed/implementation identity must still be sealed;
- blind spots: frozen within-case error ≥ q75 and score ≤ q25;
- manual test landmarks: **not opened**;
- frozen-run manifest authorizing outcome access: **NOT CREATED**.

Do not label a document a completed freeze while hashes/tests/feasibility are missing. The next gate is adequate unchanged-estimator operational feasibility plus tested external coordinate/analysis tooling. Only then seal the full run and open manual test landmarks. No external association, comparator result or publication conclusion is available.
