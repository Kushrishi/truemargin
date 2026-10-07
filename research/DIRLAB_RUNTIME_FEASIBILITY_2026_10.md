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

The current Work host exposes an 8-GiB memory ceiling and eight CPU-equivalent
quota cores. Protected originals/handoffs leave under one GiB free after the
three-project work. Stream images from original archives; do not extract all phases.
No safe multi-registration parallelism or full-field retention policy is established.
Default to one active registration until peak RSS is measured. Failed/timeout
attempts remain identified and preserved; retries must use unchanged settings,
fresh output names and declared budgets, never select a favorable run.

## Required next decision

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
