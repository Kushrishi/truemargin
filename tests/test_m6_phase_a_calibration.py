"""Pre-result tests for the M6 Phase A execution contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from truemargin.m6_phase_a import (
    GEOMETRY_HASH_FIELDS,
    _round_geometry,
    array_sha256,
    geometry_sha256,
    load_geometry_freeze,
    load_split,
    radius_efficiency,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_geometry_hash_is_canonical_and_geometry_only() -> None:
    record = {field: field for field in GEOMETRY_HASH_FIELDS}
    record.update(
        {
            "deformation_seed": 1,
            "noise_seed": 2,
            "points_seed": 3,
            "shape_zyx": [4, 5, 6],
            "spacing_xyz_mm": [0.60000002384186, 0.6, 4.0],
            "topology_scale": 0.95,
            "boundary_margin_reference_mm": 4.80000019073488,
            "boundary_margin_voxels_zyx": [2, 8, 8],
            "landmark_indices_zyx": [[1, 2, 3]],
            "landmark_physical_xyz_mm": [[1.234567891, 2.0, 3.0]],
            "transformed_physical_xyz_mm": [[1.4, 2.2, 3.1]],
            "true_displacement_xyz_mm": [[0.2, 0.2, 0.1]],
        }
    )
    first = geometry_sha256(record)
    record["non_geometry_note"] = "ignored"
    assert geometry_sha256(record) == first
    rounded = _round_geometry({field: record[field] for field in GEOMETRY_HASH_FIELDS})
    expected = hashlib.sha256(
        json.dumps(rounded, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert first == expected


def test_split_exposes_only_thirty_calibration_anatomies() -> None:
    calibration, evaluation = load_split(REPO_ROOT / "research" / "M6_SPLIT.json")
    assert len(calibration) == 30
    assert len(evaluation) == 30
    assert set(calibration).isdisjoint(evaluation)
    assert list(calibration.values()).count("prostate_3t") == 15
    assert list(calibration.values()).count("prostate_diagnosis") == 15


def test_geometry_freeze_matches_calibration_and_not_evaluation() -> None:
    calibration, evaluation = load_split(REPO_ROOT / "research" / "M6_SPLIT.json")
    freeze = load_geometry_freeze(REPO_ROOT / "research" / "M6_PHASE_A_GEOMETRY_FREEZE.json")
    assert set(freeze) == set(calibration)
    assert set(freeze).isdisjoint(evaluation)


def test_array_hash_includes_shape_and_values() -> None:
    assert array_sha256(np.array([1.0, 2.0])) != array_sha256(np.array([1.0, 3.0]))
    with pytest.raises(ValueError, match="one-dimensional"):
        array_sha256(np.zeros((1, 2)))


def test_radius_efficiency_preserves_infinite_threshold() -> None:
    summary = radius_efficiency([np.array([0.0, 1.0]), np.array([2.0, 3.0])], float("inf"))
    assert summary["infinite_radius_count"] == 4
    assert summary["total_radius_count"] == 4
    assert np.isposinf(summary["median_of_anatomy_medians_mm"])
