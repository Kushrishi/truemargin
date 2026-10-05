# External LungCT training preflight

This preflight is the implementation boundary immediately after the frozen
external-validation protocol.

It inspects **training images only**. The module contains no landmark parser and
does not read the keypoints directory.

Expected extracted training layout:

```text
<root>/
  scans/
    case_001_exp.nii.gz
    case_001_insp.nii.gz
    ...
  lungMasks/
    case_001_exp.nii.gz
    case_001_insp.nii.gz
    ...
  keypoints/
    ...
```

For each discovered pair it checks:

- expiration is fixed and inspiration is moving;
- both images are 3-D;
- fixed/moving array sizes match;
- spacing, origin, and direction agree;
- image values are finite;
- physical spacing is finite and positive.

It records the physical grid diagonal required by the unchanged nine-member
estimator. If the challenge-preprocessed pair does not share the geometry that
the current estimator assumes, preflight fails before registration.

Run after downloading/extracting the official training archive:

```bash
python scripts/preflight_external_lung.py /path/to/extracted/training
```

The command expects 20 complete training pairs by default and emits JSON with
"landmarks_accessed": false.

This step does not establish estimator feasibility. The next step, after archive
identity and geometry pass, is an operational estimator-only training preflight.
Held-out manual test landmarks remain outside that step.

## Dataset-count check before the external run

The validation protocol describes 20 training volumes and 10 test volumes, while this command defaults to 20 complete training pairs. A volume count and a pair count are different units. Before registration, inspect the official archive manifest, document the actual pair identities and reconcile the protocol wording with the preflight expectation. The Zenodo record verifies the archive checksum but does not resolve the count in its page description. Do not change the expected count simply to make a failed preflight pass.

This check is outstanding. No external validation result should be inferred from the existence of the preflight command.
