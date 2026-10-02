"""Pre-result validation for the TrueMargin M6 Phase A execution package."""

from __future__ import annotations

import runpy
from pathlib import Path

import numpy as np

SCRIPT = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "m6_phase_a.py"),
    run_name="m6_phase_a_test",
)


def _function(name: str):
    return SCRIPT[name]


def test_phase_a_patient_boundary_matches_frozen_split() -> None:
    calibration_patients = _function("calibration_patients")
    evaluation_patients = _function("evaluation_patients")
    patients = calibration_patients()

    assert len(patients) == len(set(patients)) == 30
    assert len(evaluation_patients()) == 30
    assert set(patients).isdisjoint(evaluation_patients())
    assert sum(patient.startswith("Prostate3T-") for patient in patients) == 15
    assert sum(patient.startswith("ProstateDx-") for patient in patients) == 15


def test_geometry_hash_has_frozen_rounding_boundary() -> None:
    geometry_hash = _function("geometry_hash")
    fields = SCRIPT["GEOMETRY_FIELDS"]
    base = {field: 0 for field in fields}
    base.update(
        {
            "patient_id": "P",
            "source_key": "S",
            "role": "calibration",
            "series_uid": "1.2.3",
            "shape_zyx": [1, 2, 3],
            "spacing_xyz_mm": [0.5, 0.5, 3.0],
            "boundary_margin_voxels_zyx": [2, 8, 8],
            "landmark_indices_zyx": [[2, 8, 8]],
            "landmark_physical_xyz_mm": [[1.0, 2.0, 3.0]],
            "transformed_physical_xyz_mm": [[1.1, 2.0, 3.0]],
            "true_displacement_xyz_mm": [[0.1, 0.0, 0.0]],
        }
    )
    within_rounding = dict(base)
    within_rounding["topology_scale"] = 4e-10
    materially_different = dict(base)
    materially_different["topology_scale"] = 1e-5

    assert geometry_hash(base, decimals=8) == geometry_hash(within_rounding, decimals=8)
    assert geometry_hash(base, decimals=8) != geometry_hash(materially_different, decimals=8)


def _complete_records(method: str = "sigma") -> list[dict]:
    score_summary = _function("_method_score_summary")
    records = []
    for index in range(15):
        error = np.linspace(0.5, 2.0, 50, dtype=np.float64) + index * 0.001
        signal = np.linspace(0.25, 1.5, 50, dtype=np.float64)
        record = {
            "patient_id": f"P{index:02d}",
            "source_key": "prostate_3t",
            "status": "complete",
            "known_error_mm": error.tolist(),
            f"{method}_mm": signal.tolist(),
            f"{method}_valid": True,
            f"{method}_score_summary": score_summary(error, signal),
        }
        records.append(record)
    return records


def test_source_hcp_preserves_infinite_95_percent_sentinel() -> None:
    source_method_result = _function("_source_method_result")
    result = source_method_result("prostate_3t", "sigma", _complete_records())

    assert result["assessable"] is True
    assert result["valid_anatomies"] == 15
    assert result["thresholds"]["0.80"]["calibration_groups"] == 15
    assert result["thresholds"]["0.90"]["calibration_scores"] == 750
    assert result["thresholds"]["0.95"]["q_alpha"] == "Infinity"
    assert result["thresholds"]["0.95"]["finite_threshold"] is False
    assert result["thresholds"]["0.95"]["infinity_atom_mass"] == 1 / 16


def test_ice_failure_does_not_change_sigma_assessability() -> None:
    source_method_result = _function("_source_method_result")
    records = _complete_records("sigma")
    for record in records:
        record["ice_valid"] = False
        record["ice_mm"] = None
        record["ice_score_summary"] = None
        record["ice_failure_reason"] = "synthetic_reverse_failure"

    sigma = source_method_result("prostate_3t", "sigma", records)
    ice = source_method_result("prostate_3t", "ice", records)

    assert sigma["assessable"] is True
    assert ice["assessable"] is False
    assert ice["valid_anatomies"] == 0
    assert len(ice["failures"]) == 15
