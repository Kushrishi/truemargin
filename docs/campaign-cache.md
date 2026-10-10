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

The external-analysis aggregator also requires all comparator records before
returning `primary_not_assessable`. Comparator failures remain explicit nulls;
undefined target correlation is not permission to omit comparator evidence.
