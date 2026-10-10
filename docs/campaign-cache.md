# Verified campaign member recovery and aggregation

`truemargin.campaign_cache` connects the existing registration-member receipts,
retention copier, read-only field cache and blockwise ensemble summarizer. It
does not launch registrations or access numerical landmarks.

Supply expected manifests and `registration-member-retention/1` receipts from
independently retained, reviewed producer records. Computing a new expected hash
from an untrusted copy does not authenticate that copy. Keep these records outside
the destination being checked.

```python
from pathlib import Path
from truemargin.campaign_cache import (
    RetainedMember,
    recover_campaign_member,
    summarize_campaign_group,
    verify_campaign_member,
)

member = RetainedMember(Path("retained/member"), expected_manifest, producer_receipt)
verify_campaign_member(member)
recovered = recover_campaign_member(member, Path("restored/member"))

# `members` contains the reviewed records for all nine configurations of one
# case and direction. Caller order does not change the frozen reduction order.
mean_field, spread = summarize_campaign_group(members)
```

Each member must match its independent receipt and embedded producer manifest.
Its field must be contiguous float64 `[3,Z,Y,X]`, match the prospective image
shape, be finite throughout, and pass the mean-displacement/physical-diagonal
gate. The latter is an integrity gate, not an accuracy guarantee. The scan uses
bounded spatial blocks; its magnitude sum may differ in last-place rounding
from a dense reduction.

Aggregation requires all nine promoted configurations, distinct member IDs,
the same case/direction/input identities, source identities, package versions
and physical spacing. It reorders by the existing frozen grid, verifies every
member and reuses the accepted blockwise mean/spread implementation. A missing,
failed, unverified or duplicate member rejects the group. There is no estimate
from surviving members alone.

Recovery uses the existing exclusive destination claim and copies completion
last. An interrupted copy remains on disk for inspection. Retrying into that
directory fails; recovering into a different destination copies files without
rerunning registration. Process silence is not proof that an original worker
failed. This API does not monitor workers or implement campaign slot scheduling.

Temporary aggregation memory is bounded by the spatial block size, but the
returned mean and spread still occupy four float64 values per voxel. The code
does not publish a durable summary artifact or evict source fields. Input files
must remain immutable during verification and mapping; concurrent mutation is
unsupported.

Integration tests exercise the actual producer, checkpoint and receipt schemas
with synthetic fields. They cover dense-summary parity, interrupted copy,
unavailable original, tampering, incomplete groups and mixed identities. Hosted
Linux/macOS tests do not establish real cross-host Case 7 recovery, power-loss
durability, full-campaign feasibility or scientific accuracy. Those remain
separate execution gates.

## Pinned transport and second-host readback

`python -m truemargin.member_transport pack --help` creates a bounded-memory ZIP
containing only the five completed producer files and the expected manifest and
receipt. It requires independently reviewed SHA-256 pins for both JSON records.
It does not include image archives, numerical landmarks or unrelated local files.
Never obtain the trusted pins from the packet being tested.

On another host, `python -m truemargin.member_transport recover --help` accepts
the same independent pins, strictly validates the packet allowlist and receipt
sizes, unpacks into a fresh staging directory and reuses `recover_campaign_member`
to copy into a separate fresh destination. It renames staging before repeating
the full verified readback, then writes an exclusive report. Two uncompressed
field copies plus the packet require storage. Interrupted or rejected attempts
are preserved. There is no automatic registration retry or deletion.

The report identifies consumer platform/Python, consumer module bytes, producer
source and field identity. Establish host distinctness against a separately
retained producer-host record; running this command twice on one host cannot
establish cross-host recovery. This transport is not a claim of convergence,
registration accuracy, clinical validation, campaign eligibility or power-loss
durability. Hosted transport tests remain synthetic.

## Outcome-blind grid feasibility diagnostics

`describe_campaign_group(members)` reuses the exact-nine, common-identity and
whole-field verification gates. It reads existing completion records and fields
without executing registration, opening images/landmarks or allocating a full
ensemble summary. It reports per-member optimizer records, registration wall/CPU
time, producer RSS when recorded, raw/summary payload arithmetic, and all 36
pairwise full-volume vector RMS/maximum differences. Output order is frozen.
`same_metric_bins` identifies the nine within-bin tolerance comparisons.

`iteration_cap_observed` only compares the reported index with the configured
cap. Neither a stop string, identical fields, nor field variation demonstrates
convergence or error accuracy. Unknown RSS remains null. Timing is one measured
case/direction grid, not a 180-member forecast. A missing or rejected member
prevents this complete-grid diagnostic; do not substitute a survivor estimate.
Prospective representative forward/reverse measurements and final source,
environment, storage, controller and study gates are still required. This helper
does not authorize launches or changes to the frozen grid.

The external-analysis aggregator also requires all comparator records before
returning `primary_not_assessable`. Comparator failures remain explicit nulls;
undefined target correlation is not permission to omit comparator evidence.
