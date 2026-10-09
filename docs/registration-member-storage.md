# Saving one completed registration

`truemargin.registration_member.execute_registration_member` connects the existing
B-spline registration function to field publication. It runs exactly one requested
member. It does not start an ensemble, retry a failed attempt, resume an optimizer,
or read landmarks.

The caller supplies the two image arrays, explicit registration settings, image
identifiers, repository root and a new output directory. The producer hashes the
actual ordered image arrays and result-defining source files. All settings are
passed to the existing registration implementation without changing its estimator.
Thread configuration and process supervision remain the caller's responsibility.

The output directory contains:

| File | Meaning |
| --- | --- |
| `started.json` | Source, package, parameter and actual input identities |
| `progress.jsonl` | Synced optimizer callback observations; iteration indices can repeat |
| `field/field.npy` | Completed displacement array, original floating-point dtype |
| `field/checkpoint.npz` | Provenance and checksum for the field payload |
| `completed.json` | Optimizer stop, field identity, registration wall time and process CPU time |
| `failed.json` | Caught registration/publication failure, when the filesystem permits saving it |

An existing directory is refused, including one left by a failed attempt. An
abrupt process or runtime loss can prevent either terminal JSON file from being
written. A field checkpoint alone is not proof that the entire operation completed.
Readers must check the terminal record and verify the field checksum and provenance.
A finite returned field does not imply optimizer convergence.

The wall and process CPU measurements cover this call's registration stage, not
an independently supervised child. Peak RSS is explicitly unavailable. Local
flush/fsync does not establish remote retention or parent-directory power-loss
durability. Before using an ephemeral runtime, the operator must separately verify
a durable destination and read back retained bytes; this API does not do that.

Tests inject a synthetic backend to verify exact parameter forwarding, interleaved
field preservation, repeated progress observations, refused reruns, missing stop
evidence, bad geometry, nonfinite fields and failed publication. They do not run a
scientific registration or authorize an existing experiment to restart.

## Copy and recover a completed member

`member_retention.retain_registration_member(source, destination,
expected_manifest=manifest)` copies the five allowlisted producer files to a new
directory and returns a receipt containing their byte counts and SHA-256 digests.
The operator supplies independently known producer provenance. Keep that receipt
and expected manifest outside the destination being checked.

`verify_retained_member(destination, receipt=receipt,
expected_manifest=manifest)` verifies every file, then checks the field against
the terminal record and provenance checkpoint. It can run after the original
runtime/source is unavailable. No registration is executed by either operation.

The destination can be a local directory or operator-mounted storage. This API
does not authenticate a cloud provider, establish that a mount is durable, upload
through Drive, or qualify provider guarantees. An actual destination must pass
write/readback testing separately. Copy buffers are bounded to 1 MiB; fields are
memory-mapped for shape/dtype inspection.

The completion file is published last. Interrupted copies retain partial files
and cannot be mistaken for a completed transfer by the verifier. Neither failed
nor completed destinations are overwritten. Recovery must use a new destination
and the retained source; a copy failure is never a reason to rerun registration.
Symbolic-link source members are rejected, and unlisted files are not copied.
