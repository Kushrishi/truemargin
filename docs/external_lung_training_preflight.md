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
