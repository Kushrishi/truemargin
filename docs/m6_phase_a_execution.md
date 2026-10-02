# M6 Phase A execution boundary

**Status:** pre-result execution specification  
**Milestone:** M6 numerical calibration  
**Authorized cohort:** 30 frozen calibration anatomies only

Phase A implements the calibration half of the frozen M6 protocol. It does not authorize or access the 30 evaluation anatomies.

## Execution structure

Each calibration anatomy runs as an independent hosted job. Before registration, the job must verify:

- the patient belongs to the frozen calibration role;
- the exact SeriesInstanceUID matches the Phase A input freeze;
- the reacquired DICOM archive and official label match their preflight SHA-256 digests;
- the amended deformation geometry reproduces the frozen geometry hash; and
- every pinned source file matches the Git blob identity in the Phase A request.

Only after those checks may the job run the frozen nine-member forward estimator and the frozen nine-member reverse estimator used for ICE.

The aggregation job requires the exact 30-case calibration set. It fits source-specific HCP thresholds at the prospectively frozen 80%, 90%, and 95% nominal levels. It does not load an evaluation anatomy.

## Near-zero diagnostic

For reporting only, Phase A defines a positive signal as near zero when:

```text
0 < signal_mm <= 1e-6 mm
```

This threshold has no effect on calibration scores, interval radii, method validity, zero handling, case inclusion, or HCP fitting. Exact zero handling remains the rule frozen in `docs/m6_calibration_protocol.md`.

## Failure discipline

A primary forward failure is preserved as a primary case failure. The anatomy is not replaced and the source-specific primary calibration claim is incomplete.

An ICE failure is preserved as a secondary method failure and does not alter the primary sigma cohort. A formal source-specific ICE threshold is fitted only when all 15 calibration anatomies in that source have valid ICE.

Infrastructure failures may be retried only with the same source-pinned request and scientific inputs.

## Phase B boundary

Phase A does not authorize Phase B. The complete Phase A artifact and exact thresholds must be reviewed and committed under a separate evaluation authorization before any of the 30 evaluation anatomies can run.
