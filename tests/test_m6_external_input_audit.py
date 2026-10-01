"""Unit tests for the metadata-only M6 external-input audit."""

from __future__ import annotations

import io
import runpy
import zipfile
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_m6_external_inputs.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH), run_name="m6_external_input_audit_test")


def _function(name: str):
    return SCRIPT[name]


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def test_extract_patient_id_accepts_corrected_label_filename():
    extract_patient_id = _function("extract_patient_id")
    assert (
        extract_patient_id(
            "Training/ProstateDx-01-0006_correctedLabels.nrrd", "ProstateDx-01-"
        )
        == "ProstateDx-01-0006"
    )


def test_extract_patient_id_rejects_wrong_source_prefix():
    extract_patient_id = _function("extract_patient_id")
    with pytest.raises(ValueError, match="unexpected source PatientID"):
        extract_patient_id("Training/Prostate3T-01-0001.nrrd", "ProstateDx-01-")


def test_enumerate_labels_hashes_members_and_preserves_original_name():
    enumerate_labels = _function("enumerate_labels")
    archive = _zip_bytes(
        {
            "Training/ProstateDx-01-0006_correctedLabels.nrrd": b"corrected-label",
            "Training/ProstateDx-01-0055.nrrd": b"dimension-mismatch-case",
            "Training/README.txt": b"ignored",
        }
    )
    labels = enumerate_labels(
        archive,
        expected_prefix="ProstateDx-01-",
        expected_subjects=2,
    )
    assert [record["patient_id"] for record in labels] == [
        "ProstateDx-01-0006",
        "ProstateDx-01-0055",
    ]
    assert labels[0]["corrected_label_filename"] is True
    assert labels[0]["archive_member"].endswith("_correctedLabels.nrrd")
    assert labels[1]["corrected_label_filename"] is False
    assert all(len(record["sha256"]) == 64 for record in labels)


def test_enumerate_labels_rejects_duplicate_patient_ids():
    enumerate_labels = _function("enumerate_labels")
    archive = _zip_bytes(
        {
            "a/Prostate3T-01-0001.nrrd": b"one",
            "b/Prostate3T-01-0001_copy.nrrd": b"two",
        }
    )
    with pytest.raises(RuntimeError, match="Duplicate NRRD PatientIDs"):
        enumerate_labels(
            archive,
            expected_prefix="Prostate3T-01-",
            expected_subjects=2,
        )


def test_group_candidate_series_reports_missing_and_unexpected_patients():
    group_candidate_series = _function("group_candidate_series")
    rows: list[dict[str, Any]] = [
        {
            "PatientID": "ProstateDx-01-0001",
            "StudyInstanceUID": "1.2.3",
            "SeriesInstanceUID": "1.2.3.2",
            "SeriesDescription": "T2W_TSE_AX",
            "Modality": "MR",
            "instanceCount": 28,
            "PrivateField": "must not leak into the audit",
        },
        {
            "PatientID": "unexpected-patient",
            "StudyInstanceUID": "9.9",
            "SeriesInstanceUID": "9.9.1",
        },
    ]
    grouped, missing, unexpected = group_candidate_series(
        ["ProstateDx-01-0001", "ProstateDx-01-0002"], rows
    )
    assert len(grouped["ProstateDx-01-0001"]) == 1
    assert "PrivateField" not in grouped["ProstateDx-01-0001"][0]
    assert missing == ["ProstateDx-01-0002"]
    assert unexpected == ["unexpected-patient"]
