"""Tests for M6 deformation preflight amendment 1."""

from __future__ import annotations

import ast
import json
import runpy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AMENDED_PATH = ROOT / "scripts" / "m6_deformation_preflight_amendment_1.py"
BASE_PATH = ROOT / "scripts" / "m6_deformation_preflight.py"
AMENDED = runpy.run_path(str(AMENDED_PATH), run_name="m6_deformation_amendment_test")
BASE = runpy.run_path(str(BASE_PATH), run_name="m6_deformation_base_test")


def test_amendment_authorization_is_geometry_only_and_pins_base_preflight():
    request = json.loads(
        (ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_AMENDMENT_1_REQUEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert request["authorized_mode"] == "deformation-only-preflight-amendment-1"
    assert request["expected_anatomies"] == 60
    assert request["amended_boundary_rule"]["apply_to_all_60_anatomies"] is True
    assert request["base_preflight"]["script_blob_sha"] == AMENDED["git_blob_sha"](BASE_PATH)
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


def test_amendment_authorization_accepts_pinned_actions_metadata_separately():
    request = AMENDED["load_amendment_authorization"]()
    prior = json.loads(
        (ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_RESULT_1.json").read_text(encoding="utf-8")
    )
    prerequisite = request["prior_preflight"]

    assert prerequisite["artifact_id"] is not None
    assert prerequisite["artifact_sha256"]
    assert "artifact_id" not in prior
    assert "artifact_sha256" not in prior
    for key in (
        "workflow_run_id",
        "source_git_sha",
        "audit_output_sha256",
        "complete_anatomies",
        "failed_anatomies",
        "result_bearing_outcomes_observed",
    ):
        assert prior[key] == prerequisite[key]


def test_first_preflight_failure_is_preserved_before_amendment():
    result = json.loads(
        (ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_RESULT_1.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "incomplete"
    assert result["complete_anatomies"] == 56
    assert result["failed_anatomies"] == 4
    assert result["result_bearing_outcomes_observed"] is False
    assert {case["patient_id"] for case in result["failed_cases"]} == {
        "Prostate3T-01-0001",
        "Prostate3T-01-0008",
        "Prostate3T-01-0013",
        "Prostate3T-01-0028",
    }
    assert all(case["source_z_slices"] == 15 for case in result["failed_cases"])


def test_physical_margin_preserves_eight_voxels_on_finest_axes():
    margins_zyx, reference_mm = AMENDED["boundary_margin_voxels"]((0.6, 0.6, 4.0))
    np.testing.assert_array_equal(margins_zyx, np.array([2, 8, 8]))
    assert reference_mm == 4.8


def test_physical_margin_makes_15_slice_anisotropic_volume_sampleable():
    fixed_roi = np.ones((15, 40, 40), dtype=bool)
    points, eligible, margins_zyx, reference_mm = AMENDED["sample_landmarks"](
        fixed_roi, (0.6, 0.6, 4.0), 1234
    )
    np.testing.assert_array_equal(margins_zyx, np.array([2, 8, 8]))
    assert reference_mm == 4.8
    assert eligible > 50
    assert points.shape == (50, 3)
    assert len(np.unique(points, axis=0)) == 50


def test_amendment_does_not_change_deformation_primitive():
    make_source = BASE["make_source_image"]
    source = make_source(np.zeros((40, 42, 44), dtype=np.float32), (1.1, 0.9, 2.0))
    seed = 123456789
    amended_transform = BASE["make_known_transform"](source, seed)
    base_transform = BASE["make_known_transform"](source, seed)
    np.testing.assert_array_equal(
        np.asarray(amended_transform.GetParameters()), np.asarray(base_transform.GetParameters())
    )


def test_amendment_wrapper_has_no_result_bearing_truemargin_imports():
    tree = ast.parse(AMENDED_PATH.read_text(encoding="utf-8"))
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
    source = AMENDED_PATH.read_text(encoding="utf-8")
    assert "run_hyperparameter_ensemble" not in source
    assert "fit_split_conformal" not in source
