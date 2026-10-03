# M6 Phase A DICOM input identity failure

Run `37078110203` completed preflight and centralized label staging. All 30 anatomy jobs subsequently failed the workflow's frozen-input validation step; nine also failed artifact upload. Aggregation was skipped. Available original artifacts remain diagnostic evidence and are ineligible for calibration fitting or milestone reporting.

The sampled job `111072689231` failed at the DICOM ZIP digest assertion after registration. Its patient ID, SeriesInstanceUID, label digest, and frozen geometry digest matched. Its DICOM ZIP digest was `d80ac0d79fe16fd962deb9b0c8bbebc4dd4bce45472927ceca765979c9317c58`, whereas the required digest is `ac120d49d221e5cf8d5cfc563a5e4a4bff817c3e2fa76eeec8e835c6ec91e5ce`.

Two fresh official downloads of the same calibration series had identical filenames and member bytes but different ZIP timestamps and archive digests. This establishes mutable transport metadata for those two current downloads. It does not prove equality with the historical frozen DICOM bytes. Matching geometry is insufficient to establish image identity.

The acquisition guard now checks the frozen label and DICOM ZIP digests before image decoding, synthetic-case construction, and registration. A mismatch remains a failure; no digest is refreshed, normalized, or substituted. The original input registry remains unchanged.

The next permitted work is to recover the original frozen archives or establish historical byte identity from retained provenance. No new calibration request is issued by this guard correction. Any later execution requires green source CI, a separate source-pinned request, and a uniform 30-anatomy run. Evaluation and Phase B remain sealed. Numerical calibration arrays, sigma/ICE scores, and HCP outcomes were not inspected to diagnose this failure.

## Subsequent exact recovery

On 2026-10-03 UTC, all 30 historical calibration ZIP digests were reproduced exactly from official payload bytes through a bounded timestamp-field search. See `m6_phase_a_input_recovery.md` and `research/M6_INPUT_RECOVERY_RESULT.json`. The original registry and digest guard remain unchanged. A new source-pinned request after green CI is still required before calibration.
