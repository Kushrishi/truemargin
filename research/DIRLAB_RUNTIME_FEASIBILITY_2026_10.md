# Image-only runtime feasibility — 7 October 2026

**HELD-OUT ACCESS SAFE: NO.** Decoder qualification is merged in PR75 at
`468aca4430aa2771a229a7fa215032b7c5b16508`. No numerical landmark member was opened.
This is operational evidence, not an estimator outcome or scientific failure.

## Bounded probe selected before execution

Case 4DCT7 has the largest published geometry: 512 × 512 × 136 voxels. It was
selected from geometry alone, without visual inspection or landmark/error results.
T50 fixed/T00 moving, stored scalar values, qualified raw-order RL/AP/SI array,
spacing 0.97 × 0.97 × 2.5 mm, 3-D B-spline mesh 3, 15 iterations, no centering,
Mattes bins 50, LBFGSB tolerance 1e-5, two SimpleITK threads. This is one unchanged
member, not an ensemble or a search over settings. SimpleITK 2.5.6/NumPy 2.3.5.

The process was bounded at 600 seconds. Observation-only iteration callbacks
reported optimizer iteration 0 at 174.175 and 372.933 seconds, then iteration 1
at 523.488 seconds. LBFGSB callbacks may include multiple evaluations per optimizer
iteration; these events cannot be extrapolated as uniform per-iteration timings.
The outer timeout terminated the attempt with exit 124 before completion. No field
or registration outcome was accepted, cached or used to select a convention.

The historical 180-second Learn2Reg timeout and this operational timeout are not
estimator failures. No mesh, iterations, ensemble membership or preprocessing was
weakened to accelerate the probe.

## Campaign envelope and uncertainties

The intended full comparison is 90 forward registrations (10 cases × 9 members)
and potentially 90 reverse registrations for ICE: **180 total**. One largest-case
member already exceeds ten minutes; a trustworthy total-duration upper estimate
cannot be obtained from this unfinished probe. Two-seed MRF CPU work overlapped
part of the probe, so contention is another timing limitation. This measurement
must not be advertised as isolated-host performance.

Illustrative planning scenarios, **not predictions or bounds**: at 30 minutes or
90 minutes per registration, equal-duration 180-registration campaigns would take
90 or 270 serial wall-hours and nominally 180 or 540 two-thread CPU-hours. Smaller
geometries and member-specific stopping may change these substantially. These
scenarios show that casually launching the full campaign is unjustified.

Input geometry gives exact storage quantities independent of runtime: all 100 raw
phases total 4,030,464,000 bytes; only T00/T50 total 806,092,800 bytes. The largest
three-component float64 dense field requires 855,638,016 bytes. Both-direction
all-member fields across ten cases require 87,058,022,400 bytes before other outputs
if retained at float64. The existing `ensemble.summarize_fields` stacks all nine fields and creates
additional full-sized temporaries: even the largest-case field list plus stack
requires 15,401,484,288 bytes before mean/spread temporaries, exceeding the host
memory ceiling. A bounded spatial-block aggregation helper is now supplied for read-only memory
maps. It calls the unchanged mean/RMS formula per block; thirty-one synthetic
checks cover float32/float64, component-first/moved-vector/mapped layouts, malformed
inputs and exact output equality. An initial singleton-block test exposed NumPy
reduction-order roundoff; the implementation requires blocks of at least two and
pads a singleton tail before discarding its duplicate. Exact synthetic parity
passes, without online variance or a changed mathematical estimator. No real fields
were computed or reaggregated. This engineering path still needs sufficient local
field storage and a measured runtime/RSS campaign plan.
Full-retention storage and ensemble allocations need an
explicit implementation/memory audit before a campaign. Peak registration RSS and
actual process CPU time were not captured by this first timeout harness; do not
invent either from global host observations.

At the original checkpoint, the Work host exposed an 8-GiB memory ceiling and eight CPU-equivalent
quota cores. Protected originals/handoffs leave under one GiB free after the
three-project work. Stream images from original archives; do not extract all phases.
No safe multi-registration parallelism or full-field retention policy is established.
Default to one active registration until peak RSS is measured. Failed/timeout
attempts remain identified and preserved; retries must use unchanged settings,
fresh output names and declared budgets, never select a favorable run.

## Historical next-decision request (7 October)

Do not launch the 180-registration campaign. Authorize **one isolated largest-case
member follow-up** with the same settings/two threads, a 45-minute wall cap,
process CPU/RSS monitoring and no landmark access (maximum nominal 1.5 CPU-hours).
Alternatively use the user's stable local CPU host for that same bounded probe.
If it completes, estimate the campaign using measured completion/memory and an
explicit conservative geometry/member allowance; if not, return the lower-bound
and resource uncertainty. No automatic retry or full campaign follows.

Operational feasibility is unresolved. The prospective replacement amendment and
exact executable analysis freeze are not final. This is **not READY FOR OUTCOME
UNSEALING** and does not request unsealing authorization.

## Approved isolated follow-up — 8 October 2026 UTC

The owner subsequently authorized exactly one 45-minute image-only worker, then
explicitly authorized reacquisition of only official Case7 because the original
protected handoff was unavailable. Acquisition used Emory's official Dropbox link,
with manual owner password entry. The original archive matches 333,591,361 bytes
and SHA-256 `8154f7f84ad927a135df11e6c10d5db8d2f7a92d346cf17978ed8069a569389a`.
Only T50/T00 image members were read. Numerical landmark members remain sealed.

The unchanged reviewed script SHA-256 is
`42f7be3c0a4bfc4e10af34f8dc43b7834f8733e270a60767abd9a6acb7933d04`.
Scientific source was exactly `89f9c7415dddec39a4c2b1ed9f91df73c4e91d2f`.
Python 3.12.14, SimpleITK 2.5.6, NumPy 2.3.5, two SimpleITK threads, and the
originally specified Case7 geometry/representation/member settings were verified
before launch. No parallel registration, training, native build or inference ran;
lightweight provenance/file checks and dependency downloads continued.

### Measured facts

The worker **timed out**, and the reviewed parent killed and waited for it.
The parent exited successfully after preserving its report; that does not mean
registration completed. The attempt is consumed and was not retried.

| Observation | Measured value |
| --- | ---: |
| Configured worker wall cap | 2,700 s |
| Whole worker wall, including startup and teardown | 2,700.163710 s |
| Child process CPU time | 5,073.502990 s (1.4093 CPU-hours) |
| Peak child RSS | 1,691,268 KiB (1.6129 GiB) |
| Last observed optimizer iteration index | 4 |
| Last callback registration elapsed time | 2,546.514454 s |
| Callback count | 15, with repeated indices 0–4 |

The complete callback sequence and unchanged resource report are in the
[machine-readable evidence](DIRLAB_APPROVED_PROBE_2026_10_08.json).
CPU uses the reviewed parent's `RUSAGE_CHILDREN` sum (worker plus the negligible
Git source-check child); RSS is the largest child high-water mark. The controller
records a null worker exit code on timeout, rather than the terminal signal.
No explicit worker error was printed. There is no optimizer stop description,
completed field, measured field shape/dtype/bytes or finite-field result.
Registration wall is not separately finalized: 2,700 s is the worker budget,
whereas 2,546.514454 s is directly observed registration progress. Callback
indices do not establish a uniform iteration cost or convergence.

This is incomplete operational evidence, **not scientific estimator failure**.
The previous 600-second record is preserved, not replaced by an outcome claim.

### Planning assumptions and unknowns

The target remains 90 forward registrations, with a possible additional 90 reverse
registrations for ICE. One censored member supplies no defensible finite estimate
for either set's serial CPU-hours or completion wall time. In particular, its
45-minute budget must not be multiplied by 180 and called a measured campaign
lower bound: other cases, bins, tolerances and directions are unmeasured.
Largest geometry does not prove longest optimization. Completed-run peak memory,
field-generation overhead, safe concurrency and failure/retry costs remain unknown.
Use one active registration until completion memory is measured; no campaign or
reverse/member probe is authorized by this record.

Float64 storage facts remain independent of the timeout. Full retention needs
87,058,022,400 bytes before other outputs, exceeding this reconstructed workspace's
approximately 28 GiB free disk. The largest nine-field case cache is
7,700,742,144 bytes, plus 1,140,850,688 bytes for vector mean and scalar spread.
Keeping both directional member caches together requires 15,401,484,288 bytes
before summaries. The existing spatial-block helper is a candidate exact-formula
memory-map path; no real field aggregation, eviction policy or campaign executor
has been validated. No precision reduction or online replacement formula is used.
A per-case retention design would have to preserve identities/failure records and
validate means, spread and comparators before any declared field eviction.

### Current decision

Work has **not qualified as a full-campaign execution platform**: the approved
budget did not complete one member, full retention exceeds disk, scratch persistence
is insufficient for an uncheckpointed multi-day study, and completion memory and
runtime are unknown. No out-of-memory or scientific registration failure is inferred.

The smallest alternative is an existing owner-controlled personal CPU host with
persistent storage, pinned software and the unchanged estimator. Full retention
would need over 87 GB plus overhead; bounded per-case float64 retention is another
execution-design option requiring review and validation. No paid provider is
selected. A new completion-capable single-member budget/platform must be explicitly
authorized before another worker; the present one-shot approval is exhausted.
Do not authorize a material full campaign from these censored timings alone.
Only Case7 is currently restored locally; the other nine packets also need an
approved recovery/acquisition plan before campaign execution.

**HELD-OUT ACCESS SAFE: NO.** No landmark outcomes, full campaign, reverse
registrations, estimator change, provider contact or final prospective replacement
amendment followed. This is not READY FOR OUTCOME UNSEALING.
