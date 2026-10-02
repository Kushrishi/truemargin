"""Integrity tests for the frozen M6 Phase A calibration geometry registry."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_GEOMETRY_FREEZE.json"
SPLIT_PATH = REPO_ROOT / "research" / "M6_SPLIT.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase_a_geometry_freeze_matches_only_frozen_calibration_roles() -> None:
    freeze = _load(FREEZE_PATH)
    split = _load(SPLIT_PATH)

    expected = {
        patient_id
        for source_roles in split["roles"].values()
        for patient_id in source_roles["calibration"]
    }
    evaluation = {
        patient_id
        for source_roles in split["roles"].values()
        for patient_id in source_roles["evaluation"]
    }
    observed = set(freeze["calibration"])

    assert observed == expected
    assert len(observed) == 30
    assert observed.isdisjoint(evaluation)


def test_phase_a_geometry_freeze_is_source_balanced_and_well_formed() -> None:
    freeze = _load(FREEZE_PATH)
    records = freeze["calibration"]

    counts = Counter(
        "prostate_3t" if patient.startswith("Prostate3T-") else "prostate_diagnosis"
        for patient in records
    )
    assert counts == {"prostate_3t": 15, "prostate_diagnosis": 15}

    series_uids = [record["series_uid"] for record in records.values()]
    assert len(series_uids) == len(set(series_uids)) == 30
    for record in records.values():
        assert len(record["geometry_sha256"]) == 64
        assert len(record["series_uid"]) > 20


def test_phase_a_geometry_freeze_pins_completed_preflight() -> None:
    freeze = _load(FREEZE_PATH)

    assert freeze["schema_version"] == 1
    assert freeze["record"] == "m6-phase-a-geometry-freeze"
    assert freeze["geometry_hash_rounding_decimals"] == 8
    assert (
        freeze["source_preflight_artifact_sha256"]
        == "cebada652ad648afba98e79e88b06d9315d1e59f228a080a7656ad707486db68"
    )
    assert (
        freeze["source_preflight_audit_sha256"]
        == "0b07544f3990ca47034641934238af56613d05ef6afeb71afca0de6f9df6c993"
    )
