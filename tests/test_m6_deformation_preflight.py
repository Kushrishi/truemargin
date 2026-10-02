"""Tests for the pre-result M6 deformation-only preflight."""

from __future__ import annotations

import ast
import hashlib
import json
import runpy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
M6_PATH = ROOT / "scripts" / "m6_deformation_preflight.py"
M4_PATH = ROOT / "scripts" / "19_hyperparameter_known_gt_validation.py"
M6 = runpy.run_path(str(M6_PATH), run_name="m6_deformation_preflight_test")
M4 = runpy.run_path(str(M4_PATH), run_name="m4_geometry_reference_test")


def test_m6_patient_seed_contract_is_exact_and_role_independent():
    seed = M6["deterministic_seed"]
    patient_id = "Prostate3T-01-0006"
    for stream in ("deformation", "noise", "points"):
        digest = hashlib.sha256(f"truemargin-m6-v1|{stream}|{patient_id}".encode()).digest()
        assert seed(patient_id, stream) == int.from_bytes(digest[:8], "big", signed=False)
    assert len({seed(patient_id, stream) for stream in ("deformation", "noise", "points")}) == 3


def test_m6_geometry_primitives_match_frozen_m4_conventions():
    make_source = M6["make_source_image"]
    source = make_source(np.zeros((40, 42, 44), dtype=np.float32), (1.1, 0.9, 2.0))
    seed = 123456789

    m6_transform = M6["make_known_transform"](source, seed)
    m4_transform = M4["make_known_transform"](source, seed)
    np.testing.assert_array_equal(
        np.asarray(m6_transform.GetParameters()), np.asarray(m4_transform.GetParameters())
    )

    fixed_roi = np.zeros((40, 42, 44), dtype=bool)
    fixed_roi[9:31, 9:33, 9:35] = True
    point_seed = 987654321
    m6_points, m6_eligible = M6["sample_landmarks"](fixed_roi, point_seed)
    m4_points = M4["sample_landmarks"](fixed_roi, point_seed)
    np.testing.assert_array_equal(m6_points, m4_points)
    assert m6_eligible >= 50
    assert len(np.unique(m6_points, axis=0)) == 50


def test_m6_split_is_loaded_without_dicom_identity_duplication():
    roles, patients = M6["load_split"]()
    assert len(roles) == 60
    assert len(patients) == 60
    assert set(roles.values()) == {"calibration", "evaluation"}
    assert sum(role == "calibration" for role in roles.values()) == 30
    assert sum(role == "evaluation" for role in roles.values()) == 30

    split = json.loads((ROOT / "research" / "M6_SPLIT.json").read_text(encoding="utf-8"))
    assert split["identity_policy"]["duplicated_dicom_uids_in_split"] is False


def test_m6_deformation_request_authorizes_geometry_only():
    request = json.loads(
        (ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_REQUEST.json").read_text(encoding="utf-8")
    )
    assert request["authorized_mode"] == "deformation-only-preflight"
    assert request["expected_anatomies"] == 60
    assert request["deformation_replicates_per_anatomy"] == 1
    assert request["points_per_anatomy"] == 50
    assert request["synthetic_deformation_authorized"] is True
    assert request["roi_warp_authorized"] is True
    assert request["point_sampling_authorized"] is True
    for key in (
        "result_bearing_authorized",
        "registration_authorized",
        "forward_registration_authorized",
        "reverse_registration_authorized",
        "sigma_computation_authorized",
        "ice_computation_authorized",
        "calibration_fit_authorized",
        "evaluation_authorized",
    ):
        assert request[key] is False, key


def test_m6_deformation_script_has_no_result_bearing_truemargin_imports():
    tree = ast.parse(M6_PATH.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    forbidden = {
        "truemargin.hyperparameter",
        "truemargin.calibration",
        "truemargin.comparators",
        "truemargin.known_gt_comparison",
    }
    assert forbidden.isdisjoint(imported)

    source = M6_PATH.read_text(encoding="utf-8")
    assert "run_hyperparameter_ensemble" not in source
    assert "fit_split_conformal" not in source
