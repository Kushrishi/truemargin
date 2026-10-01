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


def _manifest_bytes(series_uids: list[str]) -> bytes:
    lines = [
        "downloadServerUrl=https://example.invalid",
        "includeAnnotation=false",
        "manifestVersion=3.0",
        "ListOfSeriesToDownload=",
        *series_uids,
    ]
    return ("\n".join(lines) + "\n").encode()


def test_parse_tcia_series_uids_returns_exact_manifest_order():
    parse_tcia_series_uids = _function("parse_tcia_series_uids")
    uids = ["1.2.3.4", "1.2.3.5"]
    assert parse_tcia_series_uids(_manifest_bytes(uids), expected_series=2) == uids


def test_parse_tcia_series_uids_rejects_duplicate_uid():
    parse_tcia_series_uids = _function("parse_tcia_series_uids")
    with pytest.raises(RuntimeError, match="duplicate SeriesInstanceUID"):
        parse_tcia_series_uids(
            _manifest_bytes(["1.2.3.4", "1.2.3.4"]),
            expected_series=2,
        )


def test_extract_patient_id_accepts_corrected_label_filename():
    extract_patient_id = _function("extract_patient_id")
    assert (
        extract_patient_id("Training/ProstateDx-01-0006_correctedLabels.nrrd", "ProstateDx-01-")
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


def test_map_official_series_to_labels_pairs_exact_manifest_series():
    map_official_series_to_labels = _function("map_official_series_to_labels")
    labels_by_source: dict[str, list[dict[str, Any]]] = {
        "prostate_3t": [{"patient_id": "Prostate3T-01-0001"}],
        "prostate_diagnosis": [{"patient_id": "ProstateDx-01-0001"}],
    }
    uids = ["1.2.3.4", "1.2.3.5"]
    rows: list[dict[str, Any]] = [
        {
            "PatientID": "Prostate3T-01-0001",
            "collection_id": "prostate_3t",
            "SeriesInstanceUID": "1.2.3.4",
            "StudyInstanceUID": "1.2.3",
            "Modality": "MR",
            "PrivateField": "must not leak into the audit",
        },
        {
            "PatientID": "ProstateDx-01-0001",
            "collection_id": "prostate_diagnosis",
            "SeriesInstanceUID": "1.2.3.5",
            "StudyInstanceUID": "1.2.4",
            "Modality": "MR",
        },
    ]
    result = map_official_series_to_labels(labels_by_source, uids, rows)
    assert result["missing_series_uids_in_idc"] == []
    assert result["missing_label_patient_ids"] == []
    assert result["source_collection_mismatches"] == []
    three_t = result["official_series_by_patient"]["Prostate3T-01-0001"]
    assert len(three_t) == 1
    assert three_t[0]["SeriesInstanceUID"] == "1.2.3.4"
    assert "PrivateField" not in three_t[0]


def test_map_official_series_to_labels_reports_missing_uid_and_patient():
    map_official_series_to_labels = _function("map_official_series_to_labels")
    labels_by_source: dict[str, list[dict[str, Any]]] = {
        "prostate_3t": [{"patient_id": "Prostate3T-01-0001"}],
        "prostate_diagnosis": [],
    }
    result = map_official_series_to_labels(labels_by_source, ["1.2.3.4"], [])
    assert result["missing_series_uids_in_idc"] == ["1.2.3.4"]
    assert result["missing_label_patient_ids"] == ["Prostate3T-01-0001"]
