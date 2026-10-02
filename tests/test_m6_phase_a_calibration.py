"""Pre-result tests for the frozen TrueMargin M6 Phase A execution boundary."""

from __future__ import annotations

import json
import runpy
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "m6_phase_a_calibration.py"
INPUT_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_INPUT_FREEZE.json"
GEOMETRY_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_GEOMETRY_FREEZE.json"
SPLIT_PATH = REPO_ROOT / "research" / "M6_SPLIT.json"
SCRIPT = runpy.run_path(str(SCRIPT_PATH), run_name="m6_phase_a_calibration_test")


def _function(name: str):
    return SCRIPT[name]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_input_freeze_matches_only_frozen_calibration_anatomies() -> None:
    freeze = _load(INPUT_FREEZE_PATH)
    geometry = _load(GEOMETRY_FREEZE_PATH)
    split = _load(SPLIT_PATH)

    expected = {
        patient
        for source_roles in split["roles"].values()
        for patient in source_roles["calibration"]
    }
    evaluation = {
        patient
        for source_roles in split["roles"].values()
        for patient in source_roles["evaluation"]
    }
    observed = set(freeze["calibration"])

    assert observed == expected == set(geometry["calibration"])
    assert len(observed) == 30
    assert observed.isdisjoint(evaluation)
    assert freeze["source_preflight_artifact_sha256"] == geometry[
        "source_preflight_artifact_sha256"
    ]
    assert freeze["source_preflight_audit_sha256"] == geometry[
        "source_preflight_audit_sha256"
    ]


def test_input_freeze_pins_payload_and_geometry_identity() -> None:
    freeze = _load(INPUT_FREEZE_PATH)
    geometry = _load(GEOMETRY_FREEZE_PATH)
    counts = Counter(
        "prostate_3t" if patient.startswith("Prostate3T-") else "prostate_diagnosis"
        for patient in freeze["calibration"]
    )
    assert counts == {"prostate_3t": 15, "prostate_diagnosis": 15}

    for patient, record in freeze["calibration"].items():
        assert record["series_uid"] == geometry["calibration"][patient]["series_uid"]
        assert record["geometry_sha256"] == geometry["calibration"][patient]["geometry_sha256"]
        for key in ("dicom_zip_sha256", "label_sha256", "geometry_sha256"):
            assert len(record[key]) == 64
            int(record[key], 16)


def test_json_vector_round_trip_preserves_positive_infinity() -> None:
    encode = _function("_json_vector")
    parse = _function("_parse_vector")
    values = np.array([0.0, 1.25, np.inf, 4.0], dtype=np.float64)

    encoded = encode(values)
    decoded = parse(encoded)

    assert encoded == [0.0, 1.25, "Infinity", 4.0]
    np.testing.assert_equal(decoded, values)


def _complete_case(patient_id: str, source: str, sigma_score: float, ice_score: float) -> dict:
    return {
        "patient_id": patient_id,
        "source_key": source,
        "status": "complete",
        "ice_valid": True,
        "sigma_score": [sigma_score] * 50,
        "ice_score": [ice_score] * 50,
        "sigma_mm": [1.0] * 50,
        "ice_mm": [1.0] * 50,
    }


def test_aggregate_fits_sources_separately_and_keeps_evaluation_sealed(
    tmp_path: Path,
) -> None:
    aggregate = _function("aggregate")
    globals_ = aggregate.__globals__
    freeze = _load(INPUT_FREEZE_PATH)
    for patient in sorted(freeze["calibration"]):
        source = "prostate_3t" if patient.startswith("Prostate3T-") else "prostate_diagnosis"
        sigma_score = 1.0 if source == "prostate_3t" else 3.0
        ice_score = 2.0 if source == "prostate_3t" else 4.0
        record = _complete_case(patient, source, sigma_score, ice_score)
        (tmp_path / f"m6_phase_a_case_{patient}.json").write_text(
            json.dumps(record) + "\n", encoding="utf-8"
        )

    original_request = globals_["load_request"]
    original_freeze = globals_["load_freeze"]
    original_provenance = globals_["provenance_record"]
    globals_["load_request"] = lambda: {
        "primary_signal": "nine-member hyperparameter-ensemble sigma",
        "secondary_signal": "ensemble-mean ICE",
        "near_zero_diagnostic_mm": 1e-6,
        "source_preflight_artifact_sha256": freeze["source_preflight_artifact_sha256"],
        "source_preflight_audit_sha256": freeze["source_preflight_audit_sha256"],
    }
    globals_["load_freeze"] = lambda: freeze
    globals_["provenance_record"] = lambda: {"test": True}
    try:
        result = aggregate(tmp_path)
    finally:
        globals_["load_request"] = original_request
        globals_["load_freeze"] = original_freeze
        globals_["provenance_record"] = original_provenance

    assert result["status"] == "complete"
    assert result["evaluation_anatomies_accessed"] == 0
    assert result["authorization_boundary"]["phase_b_authorized"] is False
    assert result["sources"]["prostate_3t"]["sigma_thresholds"]["90"]["threshold"] == 1.0
    assert result["sources"]["prostate_diagnosis"]["sigma_thresholds"]["90"]["threshold"] == 3.0
    assert result["sources"]["prostate_3t"]["sigma_thresholds"]["95"][
        "threshold_is_infinite"
    ] is True
    assert result["sources"]["prostate_diagnosis"]["ice_thresholds"]["90"]["threshold"] == 4.0


def test_aggregate_rejects_incomplete_case_set(tmp_path: Path) -> None:
    aggregate = _function("aggregate")
    globals_ = aggregate.__globals__
    freeze = _load(INPUT_FREEZE_PATH)
    patient = sorted(freeze["calibration"])[0]
    source = "prostate_3t" if patient.startswith("Prostate3T-") else "prostate_diagnosis"
    (tmp_path / f"m6_phase_a_case_{patient}.json").write_text(
        json.dumps(_complete_case(patient, source, 1.0, 1.0)) + "\n",
        encoding="utf-8",
    )

    original_request = globals_["load_request"]
    original_freeze = globals_["load_freeze"]
    original_provenance = globals_["provenance_record"]
    globals_["load_request"] = lambda: {}
    globals_["load_freeze"] = lambda: freeze
    globals_["provenance_record"] = lambda: {"test": True}
    try:
        with pytest.raises(RuntimeError, match="case-set mismatch"):
            aggregate(tmp_path)
    finally:
        globals_["load_request"] = original_request
        globals_["load_freeze"] = original_freeze
        globals_["provenance_record"] = original_provenance


def test_run_case_rejects_non_calibration_patient_before_network_access() -> None:
    run_case = _function("run_case")
    globals_ = run_case.__globals__
    freeze = _load(INPUT_FREEZE_PATH)

    original_request = globals_["load_request"]
    original_freeze = globals_["load_freeze"]
    globals_["load_request"] = lambda: {"near_zero_diagnostic_mm": 1e-6}
    globals_["load_freeze"] = lambda: freeze
    try:
        with pytest.raises(RuntimeError, match="not authorized"):
            run_case("Prostate3T-01-0001")
    finally:
        globals_["load_request"] = original_request
        globals_["load_freeze"] = original_freeze
