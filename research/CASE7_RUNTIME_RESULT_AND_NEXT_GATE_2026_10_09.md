# Case 7: terminal runtime evidence and next resource gate

## Saved result, 9 October 2026

Attempt `case7-colab-20261009T0443Z` reached its 10,800-second wall cap.
The supervisor explicitly saved `timed_out: true`, killed the worker (exit -9),
and exited 0 after reporting. Supervisor exit 0 does not mean registration
completed. No automatic retry occurred. The one-use authorization is consumed.

| Saved measurement | Value |
| --- | ---: |
| Whole-worker wall time | 10,800.251111557001 seconds |
| Process CPU time | 18,376.049598000005 seconds (5.10446 CPU-hours) |
| Child peak RSS | 1,698,280 KiB (1.61961 GiB) |
| Last progress record | iteration 11 at registration elapsed 10,571.62166729 seconds |
| Worker completion record | unavailable |

RSS is the supervisor-lifetime child high-water mark, not a measured full-field
completion peak. Progress records are allowlisted saved output; repeated
iteration numbers must not be counted as separate optimizer iterations. The
optimizer stop condition, final displacement-field allocation/finite check,
completed-registration time and campaign throughput remain unknown. No OOM,
Colab disconnection or scientific failure is inferred from the cap termination.

The [exact resource record](CASE7_COLAB_2026_10_09_RESOURCES.json) identifies the
source, archive and reviewed script hashes. Recovery read only the outputs of
the [saved notebook](https://drive.google.com/file/d/1dxBJIbf9Mo6rhTwJtfgPvufwAFrAilQF/view),
modified `2026-10-09T07:44:46.272Z`: 70,970 bytes, SHA-256
`2d3aace72c7620d29456587f806462953ad13bc234d464d86b3e79577b857711`.
No cells were executed and the full notebook is not republished.

## Proposed next decision — not authorization

Do not launch a full campaign on the basis of this censored measurement.
First identify an already-owned, persistent CPU host and its CPU, available RAM,
free disk, persistence and access constraints. Prefer that over another ephemeral
Colab attempt. No hardware purchase, paid allocation or credential request is
implied.

For an explicit owner decision, propose exactly one fresh, image-only Case 7
attempt, one worker, exactly two SimpleITK threads, a six-hour wall cap, no retry
and the same reviewed registration parameters/source. Six hours is a proposed
budget boundary, not a completion prediction; nominal exposure is 12 thread-hours.
Any supervisor cap change must be reviewed separately. Do not launch until host
and cap authorization are recorded. If this also times out, stop and reassess
feasibility rather than automatically extending the cap or changing parameters.

The current probe reports field facts only on completion; it does not save the
field bytes. A successful probe therefore would not implement campaign member
retention. RAM needed for completion is unmeasured. The known Case 7 float64 field
is 855,638,016 bytes, not an upper bound on working memory. The
[bounded-retention design](DIRLAB_BOUNDED_RETENTION_DESIGN_2026_10_09.md) estimates
about 20.6 GB for both summary directions plus active image cache, before
overhead; retaining all 180 float64 fields instead requires about 487 GB. These
are storage arithmetic, not measured campaign performance or a campaign approval.

HELD-OUT ACCESS SAFE remains **NO**. Numerical landmark access, ensemble/full
campaign execution and scientific claims remain unauthorized. ASL desktop
usability remains pending; MRF new training remains unauthorized.
