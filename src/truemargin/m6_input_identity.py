"""Reject unpinned calibration inputs before decoding or registration."""

from __future__ import annotations

import hashlib


def assert_frozen_digest(
    payload: bytes,
    expected_sha256: str,
    *,
    patient_id: str,
    input_kind: str,
) -> str:
    if input_kind not in {"dicom_zip", "label"}:
        raise ValueError("unsupported frozen input kind")
    if len(expected_sha256) != 64 or any(
        value not in "0123456789abcdef" for value in expected_sha256
    ):
        raise ValueError("expected input digest must be a full SHA256")
    observed = hashlib.sha256(payload).hexdigest()
    if observed != expected_sha256:
        raise RuntimeError(
            f"frozen {input_kind} identity mismatch for {patient_id}: "
            f"observed={observed} expected={expected_sha256}; "
            "registration remains blocked"
        )
    return observed
