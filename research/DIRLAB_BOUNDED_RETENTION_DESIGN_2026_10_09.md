# Bounded field-retention design — 9 October 2026

Status: synthetic software validation and execution-design proposal only.
**HELD-OUT ACCESS SAFE: NO.** No real registration, field aggregation, member
deletion or landmark-content access was performed for this record. This does not
resolve runtime feasibility or freeze the prospective external amendment.

## Existing implementation and new validation

`summarize_fields_blockwise` already applies the historical mean/RMS formula in
spatial blocks, including its singleton-tail reduction-order safeguard. This
record does not replace it with online variance, change precision, or alter any
registration configuration. The promoted registration runner still retains its
fields in memory; a campaign executor is not implemented by this update.

The new synthetic integration test writes nine float64 fields per direction,
reads them as immutable NPY memory maps, aggregates them with block sizes
2/13/47/1000, and saves/reopens the summaries. Means and forward spread match the
original in-memory calculation exactly. At analytically interior synthetic
points, sampled spread, ICE, absolute residual and Jacobian deviation also match
exactly. These tests use no real image or reference values and perform no
registration. They establish these exercised layouts, not universal bitwise
equivalence across platforms or arbitrary arrays.

The existing NPZ checkpoint writer now stages a file in the destination directory,
flushes and syncs it, then atomically replaces the destination. Synthetic failure
tests cover partial writes, disk-full errors, sync/replacement failures, truncated
archives and abrupt process exit. Failed saves preserve the previous checkpoint;
an abrupt exit can leave an ignored temporary file. This qualifies local NPZ
publication only. It does not implement NPY member retention, optimizer resume,
remote transfer verification or parent-directory durability after power loss.

`open_verified_field_cache` now reopens a complete NPY cache using caller-supplied
expected member identities and original SHA-256 digests. It rejects missing,
duplicate or unexpected members, damaged copies, wrong shapes/dtypes and unsupported
layouts before returning read-only maps in the declared order. A synthetic
nine-member copy/readback test reproduces the original mean/spread exactly.
Expected metadata must come from reviewed producer provenance, and mapped files
must remain immutable. This helper does not generate producer manifests, implement
member saving, or qualify a remote storage provider.

## Exact payload arithmetic from public geometry

For V voxels, a three-component float64 member has 24V bytes. Nine members have
216V bytes. A vector mean plus scalar spread has 32V bytes per direction. Keeping
both directional means and spreads conservatively retains 64V bytes; the reverse
spread is included rather than silently discarded.

| Payload | Bytes, excluding file headers and other artifacts |
| --- | ---: |
| All 180 member fields | 87,058,022,400 |
| All ten cases' means and spreads, both directions | 12,897,484,800 |
| Case 7 single member | 855,638,016 |
| Case 7 nine-member directional cache | 7,700,742,144 |
| Case 7 both directional summaries | 2,281,701,376 |
| Case 7 nine-member cache plus both summaries | 9,982,443,520 |

These are allocation arithmetic, not measured peak disk/RAM or compressed sizes.
All-case summaries plus an active Case 7 cache need about 20.6 GB decimal before
images, logs, headers, temporaries and duplicate transfer staging. A 14 GB runner
disk is therefore not established as sufficient. Keeping earlier summaries on a
separate durable private store could bound local use, but that transfer workflow
has not been qualified. Available disk must be measured, not inferred from a
runner label.

## Proposed sequence requiring review before real use

1. Execute and validate all nine forward members in their frozen order. Preserve
   every member identity, configuration, software/source identity, stop state,
   timing and failure record; do not summarize a survivor-only subset.
2. Aggregate immutable memory maps with the existing blockwise formula. Save
   mean/spread exclusively, verify hashes, geometry, dtype and readback.
3. Preserve member fields until the declared summary validation and durable
   checkpoint checks pass. Any subsequent deletion requires an explicitly
   approved retention policy; none is authorized or performed here.
4. If reverse ICE work is approved, execute and aggregate that direction under
   the same completeness and provenance requirements. Retain both summaries.
5. Keep image identities and both directional summary grids for later approved
   analysis. ICE needs reverse displacement at forward-warped locations; sampling
   reverse fields only at fixed points is not a valid shortcut. Residual requires
   the moving image; Jacobian requires spatial derivatives of the forward field.
   Keeping full summary grids preserves these inputs without opening outcomes.
6. Before the next case, verify durable private checkpoint transfer. Do not free
   the only copy of summaries or failure evidence to satisfy a disk target.

## Limits and next gate

Full-member eviction sacrifices later per-member reinspection and regeneration
without rerunning registrations. Hashes do not substitute for retained payloads.
The owner must weigh that reproducibility tradeoff; a separate large persistent
disk retaining all fields remains the conservative option. Summary parity does
not certify archive transfer, crash recovery, disk exhaustion handling, safe
parallelism or equivalent comparator behavior for every possible failed case.

No decision on retries, failure exclusions, analysis thresholds, bootstrap seed,
landmark interpolation amendment or campaign launch follows. The active approved
Case 7 probe remains separate and unchanged. Its eventual measured resources are
still needed for a defensible compute proposal.
