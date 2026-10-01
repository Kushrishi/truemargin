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
        extract_patient_id("Training/ProstateDx-01-0006_correctedLabels.nrrd")
        == "ProstateDx-01-0006"
    )


def test_source_key_for_patient_id_maps_both_official_prefixes():
    source_key_for_patient_id = _function("source_key_for_patient_id")
    assert source_key_for_patient_id("Prostate3T-01-0001") == "prostate_3t"
    assert source_key_for_patient_id("ProstateDx-01-0001") == "prostate_diagnosis"
    with pytest.raises(ValueError, match="exactly one source"):
        source_key_for_patient_id("Unknown-01-0001")


def test_enumerate_labels_hashes_members_and_preserves_partition_and_source():
    enumerate_labels = _function("enumerate_labels")
    archive = _zip_bytes(
        {
            "Leaderboard/Prostate3T-01-0001.nrrd": b"three-t",
            "Leaderboard/ProstateDx-01-0002.nrrd": b"diagnosis",
            "Leaderboard/README.txt": b"ignored",
        }
    )
    labels = enumerate_labels(
        archive,
        partition="leaderboard",
        expected_subjects=2,
    )
    assert [record["patient_id"] for record in labels] == [
        "Prostate3T-01-0001",
        "ProstateDx-01-0002",
    ]
    assert [record["source_key"] for record in labels] == [
        "prostate_3t",
        "prostate_diagnosis",
    ]
    assert all(record["partition"] == "leaderboard" for record in labels)
    assert all(len(record["sha256"]) == 64 for record in labels)


def test_enumerate_labels_rejects_wrong_source_specific_training_archive():
    enumerate_labels = _function("enumerate_labels")
    archive = _zip_bytes({"Training/Prostate3T-01-0001.nrrd": b"wrong-source"})
    with pytest.raises(RuntimeError, match="expected source prostate_diagnosis"):
        enumerate_labels(
            archive,
            partition="training",
            expected_subjects=1,
            expected_source_key="prostate_diagnosis",
        )


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
            partition="training",
            expected_subjects=2,
        )


def test_build_label_index_rejects_cross_partition_duplicate_patient():
    build_label_index = _function("build_label_index")
    partitions = {
        "training": {
            "labels": [
                {
                    "patient_id": "Prostate3T-01-0001",
                    "partition": "training",
                    "source_key": "prostate_3t",
                }
            ]
        },
        "test": {
            "labels": [
                {
                    "patient_id": "Prostate3T-01-0001",
                    "partition": "test",
                    "source_key": "prostate_3t",
                }
            ]
        },
    }
    with pytest.raises(RuntimeError, match="multiple challenge partitions"):
        build_label_index(partitions)


def test_map_official_series_to_labels_pairs_exact_manifest_series():
    map_official_series_to_labels = _function("map_official_series_to_labels")
    label_index: dict[str, dict[str, Any]] = {
        "Prostate3T-01-0001": {
            "patient_id": "Prostate3T-01-0001",
            "partition": "training",
            "source_key": "prostate_3t",
        },
        "ProstateDx-01-0001": {
            "patient_id": "ProstateDx-01-0001",
            "partition": "test",
            "source_key": "prostate_diagnosis",
        },
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
    result = map_official_series_to_labels(label_index, uids, rows)
    assert result["missing_series_uids_in_idc"] == []
    assert result["missing_label_patient_ids"] == []
    assert result["source_collection_mismatches"] == []
    three_t = result["official_series_by_patient"]["Prostate3T-01-0001"]
    assert len(three_t) == 1
    assert three_t[0]["partition"] == "training"
    assert three_t[0]["series"]["SeriesInstanceUID"] == "1.2.3.4"
    assert "PrivateField" not in three_t[0]["series"]


def test_map_official_series_to_labels_reports_missing_uid_and_patient():
    map_official_series_to_labels = _function("map_official_series_to_labels")
    label_index: dict[str, dict[str, Any]] = {
        "Prostate3T-01-0001": {
            "patient_id": "Prostate3T-01-0001",
            "partition": "training",
            "source_key": "prostate_3t",
        }
    }
    result = map_official_series_to_labels(label_index, ["1.2.3.4"], [])
    assert result["missing_series_uids_in_idc"] == ["1.2.3.4"]
    assert result["missing_label_patient_ids"] == ["Prostate3T-01-0001"]


def test_validate_historical_training_conditions_requires_corrected_and_preserved_cases():
    validate = _function("validate_historical_training_conditions")
    label_index = {
        "ProstateDx-01-0006": {"corrected_label_filename": True},
        "ProstateDx-01-0055": {"corrected_label_filename": False},
        "ProstateDx-01-0035": {"corrected_label_filename": False},
    }
    result = validate(label_index)
    assert result["issues"] == []
