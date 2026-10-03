# Stage frozen inputs before calibration

The uniform Phase A attempt `37093645674` remains incomplete and ineligible for aggregation. Hosted job metadata confirms multiple anatomy failures; sampled operational failures reviewed before this change were image-download timeouts. No partial numerical calibration outputs were used to select this repair.

The workflow now acquires all 30 calibration archives in the existing input-staging job, before any anatomy job can begin. The acquisition script retains the original whole-archive SHA-256 identities. Its recovery record is uploaded even when staging fails. A failed acquisition prevents all anatomy jobs from starting; it does not reduce the cohort or authorize selective retries.

Successful staging produces one workflow-local artifact containing the verified labels and all original frozen image archives. Each anatomy job reads its image from that artifact and enforces its original full SHA-256 before decoding. Missing or altered cached bytes fail immediately. Cached execution performs neither image download nor archive recovery. Standalone acquisition retains the existing bounded historical ZIP recovery, without changing the input registry.

The acquisition script is included in the source-pinned execution identity. The workflow's pre-result tests cover exact cached bytes, absent archives, altered archives, wrong series, altered labels, and wrong observed patient identity. Tests use synthetic byte fixtures and perform no image registration or evaluation-cohort access.

This is a transport change only. The estimator, comparator, split, geometry, statistical rules, and failure policy are unchanged. Implementation CI is required before a separate request can pin the merged source and authorize a fresh uniform 30-anatomy run. The previous request must not be reused; partial numerical shards remain ineligible. Evaluation stays sealed.
