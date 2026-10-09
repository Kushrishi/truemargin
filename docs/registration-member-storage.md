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
