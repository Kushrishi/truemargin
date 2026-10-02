# M6 Phase A transport amendment 2

**Scope:** official label acquisition only

Run `37075119713` passed source authorization, frozen input-registry identity, focused tests, and calibration-matrix construction. Its centralized label-staging job then failed because both urllib and curl could not connect to `wiki.cancerimagingarchive.net`. All calibration anatomy jobs and aggregation were skipped. This attempt produced no registration, sigma, ICE, or calibration output.

The current official TCIA dataset page links the same training archive at:

`https://www.cancerimagingarchive.net/wp-content/uploads/NCI-ISBI-2013-Prostate-Challenge-Training.zip`

The acquired archive contains 286,501 bytes and has SHA-256:

`c3436559b474c60e78633ea98601241f39cb27e30fb9d48b1d29f2821bfbf047`

All 30 calibration label members match the existing frozen per-anatomy label digests. Only calibration label contents were inspected for this verification. No evaluation label was decompressed or parsed, and no evaluation image or result was accessed.

The amendment makes the current official URL primary and retains the legacy official URL as a bounded transport fallback. The staging script checks both the archive digest and all 30 frozen label digests before making a cache available. An identity mismatch stops execution; it does not trigger source switching. The new staging script is included in the source-pinned execution path.

The hosted transport preflight performs acquisition and byte-identity validation only. It does not authorize registration or calibration. After this implementation passes CI and hosted transport preflight on main, a separate request must pin the new source and authorize a uniform execution of all 30 calibration anatomies from scratch.

PatientIDs, SeriesInstanceUIDs, DICOM digests, label digests, geometry, points, seeds, split, estimator, ICE, HCP construction, and nominal coverages remain frozen. The evaluation cohort remains sealed.

Official source: [TCIA ISBI-MR-PROSTATE-2013](https://www.cancerimagingarchive.net/analysis-result/isbi-mr-prostate-2013/).
