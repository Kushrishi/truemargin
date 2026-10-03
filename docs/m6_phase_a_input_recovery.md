# Exact historical M6 calibration input recovery

**Date:** 2026-10-03 UTC  
**Scope:** acquisition and provenance only; no result-bearing authorization

## Evidence

The original source-pinned deformation-only preflight artifact from run `37050507332` was retrieved and verified against archive SHA-256 `cebada652ad648afba98e79e88b06d9315d1e59f228a080a7656ad707486db68`. Its audit output matched SHA-256 `0b07544f3990ca47034641934238af56613d05ef6afeb71afca0de6f9df6c993`. All 30 calibration DICOM archive digests in that original artifact agree with the unchanged `M6_PHASE_A_INPUT_FREEZE.json`.

Fresh official downloads were acquired for the 30 calibration SeriesInstanceUIDs only. The server places acquisition-time DOS timestamps in local and central ZIP headers. A bounded search over the historical preflight interval reproduced **all 30 exact original frozen archive SHA-256 values**. Each recovered file was independently hashed again after preservation. The complete recovery record is `research/M6_INPUT_RECOVERY_RESULT.json`.

This establishes exact historical archive identity under the ordinary SHA-256 identity assumption. It is stronger than current-member agreement, matching geometry, or matching DICOM UIDs. No statistical result is inferred from this recovery.

## Recovery contract

`src/truemargin/m6_zip_recovery.py` changes only four timestamp bytes in each local ZIP header and its corresponding central-directory header. Compressed member bytes, names, CRCs, sizes, comments, compression parameters, extra fields, and every other archive byte remain unchanged.

The bounded procedure tests uniform timestamps and one ordered two-timestamp boundary with gaps of 2, 4, or 6 seconds. The historical UTC window is 2026-10-02 18:53:44 through 18:54:58, the pinned acquisition preflight interval.

A candidate is accepted only if the **entire archive** matches its original frozen SHA-256. There is no canonicalized archive hash, refreshed registry, member-only acceptance rule, or geometry-based fallback. If the original digest cannot be reproduced, execution remains blocked. An exact input passes through unchanged.

The Phase A loader now applies this recovery before the existing unchanged `assert_frozen_digest` guard. That guard still runs before image decoding, synthetic-case construction, or registration. The recovery module is added to the source-pinned result-defining path set. The protocol, input registry, geometry freeze, split, seeds, estimator, ICE definition, HCP construction, and failure policy are unchanged.

## Preservation and validation

The recovered original archives and acquisition record are preserved in `TrueMargin_M6_Frozen_Calibration_Inputs.zip`, SHA-256 `71f4bb27ec32670cf5914514a596dd39d3a63e235cfb55ac39214e9058315813`, size 110,173,833 bytes. The archives are not ordinary Git source files. They can also be reproduced from official downloads when exact digest recovery succeeds.

Twenty-two focused recovery, original-input-guard, label-transport, Phase A, and frozen-geometry tests passed. Tests prove byte-identical archive recovery, reject changed image member bytes and out-of-window identities, bound the search, and preserve exact inputs. Ruff, Black, and Mypy checks passed.

No evaluation anatomy was acquired by this recovery. No image was decoded, registration run, sigma or ICE computed, calibration fit performed, or partial numerical calibration outcome inspected.

## Execution gate

This recovery does not itself authorize calibration. After merged-source CI passes, a separate source-pinned request may authorize a fresh uniform execution of all 30 frozen calibration anatomies. All three earlier incomplete attempts remain preserved and ineligible for aggregation. No successful partial anatomy result is selected or reused.

Phase B remains sealed until the complete Phase A artifact and exact thresholds are reviewed and committed under a separate evaluation authorization.
