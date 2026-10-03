# M6 Phase B execution

Phase B evaluates the unchanged estimator on the 30 previously separated evaluation anatomies. It consumes the accepted Phase A aggregate and exact threshold seal; it does not fit, pool, replace, or adjust calibration thresholds. This implementation document does not authorize execution. A separate `research/M6_PHASE_B_REQUEST.json` must pin the reviewed implementation and successful source CI before input staging or registration.

## Immutable inputs and computation

`research/M6_PHASE_B_INPUT_FREEZE.json` is derived from the original amended deformation-only preflight, run `37050507332`. The original JSON digest is `0b07544f3990ca47034641934238af56613d05ef6afeb71afca0de6f9df6c993`; its archive digest is `cebada652ad648afba98e79e88b06d9315d1e59f228a080a7656ad707486db68`. The registry selects exactly the 30 original `evaluation` records using the unchanged split. It preserves DICOM archive, label, series and geometry identities. No estimator outcome was used in deriving it.

The runner reproduces the Phase A case construction and estimator/comparator operations, changing the role and input registry only. The original Phase A implementation remains untouched so its execution provenance stays valid. An AST comparison checks equality of the core forward, known-error, sigma and reverse/ICE operations. Existing geometry and estimator tests remain required.

Before computation, the workflow stages the official training label archive and all 30 evaluation DICOM archives. Labels and complete DICOM archive digests must equal the original preflight values. The existing bounded timestamp recovery may reconstruct a mutable transport ZIP only when complete-archive SHA-256 equality is achieved; no member content changes or new accepted identity are permitted. A transport failure prevents the anatomy matrix from starting.

Each anatomy reads only its authorized label and exact cached image. Missing caches and altered bytes fail before image decoding; no network fallback occurs inside an anatomy job. Geometry is rebuilt under the unchanged role-independent seeds, deformation, point sampling and physical-distance amendment, and its original evaluation geometry hash must match before registration.

## Reporting and failures

For each source and method, the report includes all 15 anatomy identities and method failures. When the source is fully assessable, it reports the 80%, 90% and 95% sealed multipliers, every anatomy's empirical coverage, equal-anatomy mean coverage, continuous coverage gap, and radius summaries. The uncalibrated descriptive reference uses radius equal to the signal. Balanced coverage is reported only when both source-specific claims are assessable. Spatial points are never treated as independent anatomy trials.

The 3T ICE calibration is already unavailable after the retained Phase A reverse failure. Phase B still performs the planned reverse ensemble for each evaluation anatomy and retains its results. It may report an uncalibrated descriptive ICE reference when evaluation is fully complete, but it must not invent a 3T calibrated threshold or a balanced calibrated ICE claim.

A primary failure keeps its identity and reason and makes the corresponding source-specific primary result incomplete. A secondary failure does not change primary sigma results. Failed anatomies are neither replaced nor excluded to compute reduced-cohort confirmatory coverage. Incomplete transport/runner shard sets cannot be aggregated as complete evaluation.

Zero signals retain the exact frozen score rule. Infinite thresholds create infinite radii even at zero signals. Signal, score and radius diagnostics report zero and positive-infinity fractions. The additional descriptive near-zero diagnostic is declared before evaluation as `0 < value <= float64 epsilon` in each quantity's native units (millimeters for signals/radii, dimensionless for scores). It does not change scores, radii, inclusion, threshold fitting, failure status or abstention. No clipping or epsilon floor is applied.

## Authorization and reproducibility

The request pins protocol, amendment, split, evaluation input registry, threshold seal, and accepted calibration aggregate blobs. The execution guard also compares every result-defining implementation path with its pinned Git source. The request is deliberately absent from the implementation PR, so merging implementation cannot start result-bearing work.

After merged-source CI passes, a separate prospective request may authorize exactly 270 forward and 270 reverse evaluation registrations. Its merge triggers the dedicated workflow. All scientific rules remain fixed. Infrastructure retries may use only the same request and exact inputs; scientific failures are preserved rather than retried with different settings.

The final aggregate identifies implementation, request and seal provenance. Per-anatomy numerical records and point checkpoints are retained along with a SHA-256 manifest. The final aggregate downloads only anatomy artifacts; it excludes raw input cache archives. Results must be independently reviewed before any held-out coverage claim or public-facing summary is updated.
