"""Unit tests for the metadata-only M6 external-input identity audit."""

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
        "ListOfSeriesToDownload=",
        *series_uids,
    ]
    return ("\n".join(lines) + "\n").encode()


def test_exact_uids_accepts_list_and_wrapped_v4_payloads():
    exact_uids = _function("exact_uids")
    payloads = [
        [
            {"seriesInstanceUID": "1.2.3.4"},
            {"SeriesInstanceUID": "1.2.3.5"},
        ],
        {
            "Series": [
                {"SeriesInstanceUID": "1.2.3.4"},
                {"SeriesInstanceUID": "1.2.3.5"},
            ]
        },
    ]
    for payload in payloads:
        uids, rows = exact_uids(payload, 2, "synthetic")
        assert uids == ["1.2.3.4", "1.2.3.5"]
        assert len(rows) == 2


def test_exact_uids_rejects_duplicate_series():
    exact_uids = _function("exact_uids")
    with pytest.raises(RuntimeError, match="Duplicate SeriesInstanceUID"):
        exact_uids(
            [
                {"SeriesInstanceUID": "1.2.3.4"},
                {"SeriesInstanceUID": "1.2.3.4"},
            ],
            2,
            "synthetic",
        )


def test_validate_partitions_requires_exact_disjoint_60_10_10():
    validate_partitions = _function("validate_partitions")
    all_uids = [f"1.2.840.{index}" for index in range(80)]
    result = validate_partitions(all_uids[:60], all_uids[60:70], all_uids[70:])
    assert set(result) == {"training", "leaderboard", "test"}
    assert sum(len(values) for values in result.values()) == 80


def test_validate_partitions_rejects_cross_partition_overlap():
    validate_partitions = _function("validate_partitions")
    all_uids = [f"1.2.840.{index}" for index in range(80)]
    with pytest.raises(RuntimeError, match="overlap"):
        validate_partitions(
            all_uids[:60],
            all_uids[60:70],
            [all_uids[0], *all_uids[71:80]],
        )


def test_manifest_uids_returns_exact_official_membership():
    manifest_uids = _function("manifest_uids")
    uids = ["1.2.3.4", "1.2.3.5"]
    assert manifest_uids(_manifest_bytes(uids), 2) == uids


def test_manifest_uids_rejects_duplicate_series():
    manifest_uids = _function("manifest_uids")
    with pytest.raises(RuntimeError, match="duplicate SeriesInstanceUID"):
        manifest_uids(_manifest_bytes(["1.2.3.4", "1.2.3.4"]), 2)


def test_source_mapping_accepts_all_observed_challenge_namespace_candidates():
    source_key = _function("source_key")
    namespace = _function("namespace")
    assert source_key("Prostate3T-01-0001") == "prostate_3t"
    assert source_key("ProstateDx-02-0001") == "prostate_diagnosis"
    assert source_key("Prostate3T-03-0001") == "prostate_3t"
    assert namespace("Prostate3T-01-0001") == "01"
    assert namespace("ProstateDx-02-0001") == "02"
    assert namespace("Prostate3T-03-0001") == "03"
    with pytest.raises(ValueError, match="Unsupported challenge PatientID"):
        source_key("Prostate3T-04-0001")


def test_label_records_preserves_later_partition_namespace():
    label_records = _function("label_records")
    archive = _zip_bytes(
        {
            "Leaderboard/Prostate3T-02-0001.nrrd": b"three-t",
            "Leaderboard/ProstateDx-02-0002.nrrd": b"diagnosis",
            "Leaderboard/README.txt": b"ignored",
        }
    )
    labels = label_records(archive, "leaderboard", 2)
    assert [record["patient_id"] for record in labels] == [
        "Prostate3T-02-0001",
        "ProstateDx-02-0002",
    ]
    assert {record["patient_namespace"] for record in labels} == {"02"}


def test_map_identities_records_namespace_without_presuming_partition_mapping():
    map_identities = _function("map_identities")
    partitions = {
        "training": ["1.2.3.4"],
        "leaderboard": ["1.2.3.5"],
        "test": ["1.2.3.6"],
    }
    rows: list[dict[str, Any]] = [
        {
            "PatientID": "Prostate3T-01-0001",
            "collection_id": "prostate_3t",
            "SeriesInstanceUID": "1.2.3.4",
        },
        {
            "PatientID": "ProstateDx-02-0001",
            "collection_id": "prostate_diagnosis",
            "SeriesInstanceUID": "1.2.3.5",
        },
        {
            "PatientID": "Prostate3T-03-0001",
            "collection_id": "prostate_3t",
            "SeriesInstanceUID": "1.2.3.6",
        },
    ]
    result = map_identities(partitions, rows)
    assert result["partition_namespaces"] == {
        "training": ["01"],
        "leaderboard": ["02"],
        "test": ["03"],
    }


def test_official_binary_falls_back_to_curl_without_changing_authority(monkeypatch):
    official_binary = _function("official_binary")
    globals_ = official_binary.__globals__
    transport_error = globals_["TransportUnavailable"]

    def fail_urllib(*args, **kwargs):
        raise transport_error("https://example.invalid/data", [{"client": "urllib"}])

    def succeed_curl(url):
        return b"abc", {
            "client": "curl",
            "http_status": 200,
            "size_bytes": 3,
            "sha256": "synthetic",
        }

    monkeypatch.setitem(globals_, "request_bytes", fail_urllib)
    monkeypatch.setitem(globals_, "curl_bytes", succeed_curl)
    payload, record = official_binary("https://example.invalid/data")
    assert payload == b"abc"
    assert record["client"] == "curl"
    assert record["prior_failures"] == [{"client": "urllib"}]


def test_shared_list_crosscheck_transport_failure_is_nonfatal(monkeypatch):
    crosscheck = _function("shared_list_crosscheck")
    globals_ = crosscheck.__globals__
    transport_error = globals_["TransportUnavailable"]

    def unavailable(*args, **kwargs):
        raise transport_error("https://example.invalid/shared", [{"client": "urllib"}])

    monkeypatch.setitem(globals_, "shared_list", unavailable)
    result = crosscheck("synthetic", 2, ["1.2.3.4", "1.2.3.5"])
    assert result["status"] == "transport_unavailable"
    assert result["required_for_partition_identity"] is False


def test_shared_list_crosscheck_mismatch_is_gate_issue(monkeypatch):
    crosscheck = _function("shared_list_crosscheck")
    globals_ = crosscheck.__globals__

    def conflicting(*args, **kwargs):
        return {"series_uids": ["1.2.3.4", "1.2.3.9"], "name": "synthetic"}

    monkeypatch.setitem(globals_, "shared_list", conflicting)
    result = crosscheck("synthetic", 2, ["1.2.3.4", "1.2.3.5"])
    assert result["status"] == "mismatch"
    assert result["matches_manifest_authority"] is False


def test_partition_manifest_uses_exact_official_binary_membership(monkeypatch):
    partition_manifest = _function("partition_manifest")
    globals_ = partition_manifest.__globals__
    uids = [f"1.2.840.{index}" for index in range(10)]

    def synthetic_binary(url):
        return _manifest_bytes(uids), {"client": "synthetic", "url": url}

    monkeypatch.setitem(globals_, "official_binary", synthetic_binary)
    record = partition_manifest("test")
    assert record["series_uids"] == sorted(uids)
    assert record["transport"]["client"] == "synthetic"


def test_historical_training_checks_preserves_known_correction_cases():
    historical_training_checks = _function("historical_training_checks")
    label_index = {
        "ProstateDx-01-0006": {"corrected_label_filename": True},
        "ProstateDx-01-0055": {},
        "ProstateDx-01-0035": {},
    }
    assert historical_training_checks(label_index) == []


def test_failure_record_keeps_result_bearing_boundary_closed():
    failure_record = _function("failure_record")
    result = failure_record(RuntimeError("synthetic failure"))
    assert result["status"] == "failed"
    assert result["schema_version"] == 5
    assert result["authorization_boundary"]["result_bearing_authorized"] is False
    assert result["authorization_boundary"]["split_assignment_authorized"] is False
