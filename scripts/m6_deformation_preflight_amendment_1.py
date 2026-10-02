#!/usr/bin/env python3
"""Run TrueMargin M6 deformation preflight amendment 1.

This wrapper preserves the original M6 deformation preflight implementation and
changes only the fixed-domain boundary-margin rule authorized by amendment 1.
It does not run registration, compute sigma or ICE, fit calibration, or evaluate
coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight.py"
BASE_REQUEST_PATH = REPO_ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_REQUEST.json"
AMENDMENT_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol_amendment_1.md"
AMENDMENT_REQUEST_PATH = (
    REPO_ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_AMENDMENT_1_REQUEST.json"
)
PREFLIGHT_RESULT_1_PATH = REPO_ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_RESULT_1.json"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "m6_deformation_preflight_amendment_1.json"

BASE = runpy.run_path(str(BASE_SCRIPT_PATH), run_name="m6_deformation_preflight_base")
REFERENCE_MARGIN_VOXELS = 8
NDIM = 3
N_LANDMARKS = int(BASE["N_LANDMARKS"])


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def load_amendment_authorization() -> dict[str, Any]:
    request = json.loads(AMENDMENT_REQUEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "milestone": "M6",
        "authorized_mode": "deformation-only-preflight-amendment-1",
        "result_bearing_authorized": False,
        "registration_authorized": False,
        "forward_registration_authorized": False,
        "reverse_registration_authorized": False,
        "sigma_computation_authorized": False,
        "ice_computation_authorized": False,
        "calibration_fit_authorized": False,
        "evaluation_authorized": False,
        "synthetic_deformation_authorized": True,
        "roi_warp_authorized": True,
        "point_sampling_authorized": True,
        "expected_anatomies": 60,
        "deformation_replicates_per_anatomy": 1,
        "points_per_anatomy": N_LANDMARKS,
        "expected_output": "outputs/m6_deformation_preflight_amendment_1.json",
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise RuntimeError(
                f"M6 amendment authorization mismatch for {key}: "
                f"{request.get(key)!r} != {value!r}"
            )

    base = request["base_preflight"]
    if base.get("script_path") != str(BASE_SCRIPT_PATH.relative_to(REPO_ROOT)):
        raise RuntimeError("M6 amendment base-script path mismatch")
    if git_blob_sha(BASE_SCRIPT_PATH) != base.get("script_blob_sha"):
        raise RuntimeError("M6 amendment base-script blob mismatch")
    if base.get("request_path") != str(BASE_REQUEST_PATH.relative_to(REPO_ROOT)):
        raise RuntimeError("M6 amendment base-request path mismatch")
    if git_blob_sha(BASE_REQUEST_PATH) != base.get("request_blob_sha"):
        raise RuntimeError("M6 amendment base-request blob mismatch")

    rule = request["amended_boundary_rule"]
    if rule.get("reference_margin_voxels") != REFERENCE_MARGIN_VOXELS:
        raise RuntimeError("Unexpected M6 boundary reference margin")
    if rule.get("reference_spacing") != "minimum voxel spacing of the prepared anatomy":
        raise RuntimeError("Unexpected M6 boundary reference-spacing rule")
    if rule.get("axis_margin_rule") != "ceil(reference_margin_mm / axis_spacing_mm)":
        raise RuntimeError("Unexpected M6 axis-margin rule")
    if rule.get("minimum_axis_margin_voxels") != 1:
        raise RuntimeError("Unexpected M6 minimum axis margin")
    if rule.get("apply_to_all_60_anatomies") is not True:
        raise RuntimeError("M6 amendment must apply to all 60 anatomies")

    prior = json.loads(PREFLIGHT_RESULT_1_PATH.read_text(encoding="utf-8"))
    prerequisite = request["prior_preflight"]
    # The durable prior-result record stores scientific outcome provenance.
    # GitHub artifact identity is pinned separately in the amendment request because
    # artifact ID and archive digest are Actions metadata, not fields in that record.
    for key in (
        "workflow_run_id",
        "source_git_sha",
        "audit_output_sha256",
        "complete_anatomies",
        "failed_anatomies",
        "result_bearing_outcomes_observed",
    ):
        if prior.get(key) != prerequisite.get(key):
            raise RuntimeError(f"M6 amendment prior-preflight mismatch for {key}")
    if prior.get("result_bearing_outcomes_observed") is not False:
        raise RuntimeError("M6 amendment requires no prior result-bearing outcomes")
    return request


def boundary_margin_voxels(
    spacing_xyz: tuple[float, ...],
) -> tuple[np.ndarray, float]:
    """Convert one physical safety distance to z/y/x integer voxel margins."""
    spacing = np.asarray(spacing_xyz, dtype=np.float64)
    if spacing.shape != (NDIM,) or not np.isfinite(spacing).all() or np.any(spacing <= 0.0):
        raise ValueError(f"invalid voxel spacing for boundary rule: {spacing_xyz}")
    reference_mm = float(REFERENCE_MARGIN_VOXELS * np.min(spacing))
    margins_xyz = np.ceil(reference_mm / spacing - 1e-12).astype(np.int64)
    margins_xyz = np.maximum(margins_xyz, 1)
    return margins_xyz[::-1].copy(), reference_mm


def sample_landmarks(
    fixed_roi_mask: np.ndarray, spacing_xyz: tuple[float, ...], seed: int
) -> tuple[np.ndarray, int, np.ndarray, float]:
    if fixed_roi_mask.ndim != NDIM:
        raise ValueError("fixed ROI mask must be 3-D")
    candidates = np.argwhere(np.asarray(fixed_roi_mask) > 0)
    shape = np.asarray(fixed_roi_mask.shape, dtype=np.int64)
    margins_zyx, reference_mm = boundary_margin_voxels(spacing_xyz)
    if np.any(shape <= 2 * margins_zyx):
        raise ValueError(
            "prepared crop is too small for amended physical boundary margin: "
            f"shape={shape.tolist()}, margins_zyx={margins_zyx.tolist()}"
        )
    eligible = candidates[
        np.all(candidates >= margins_zyx, axis=1)
        & np.all(candidates < (shape - margins_zyx), axis=1)
    ]
    if len(eligible) < N_LANDMARKS:
        raise ValueError(
            f"fixed ROI has only {len(eligible)} eligible voxels after amended "
            f"physical boundary margin {margins_zyx.tolist()} z/y/x voxels "
            f"({reference_mm:.6g} mm reference); need {N_LANDMARKS}"
        )
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(eligible), size=N_LANDMARKS, replace=False)
    return eligible[selected].astype(np.int64), int(len(eligible)), margins_zyx, reference_mm


def preflight_geometry(
    patient_id: str,
    role: str,
    series_uid: str,
    image: sitk.Image,
    label: sitk.Image,
) -> dict[str, Any]:
    crop, mask_crop, spacing = BASE["prepare_anatomy"](image, label)
    source_img = BASE["make_source_image"](crop, spacing)
    deformation_seed = BASE["deterministic_seed"](patient_id, "deformation")
    noise_seed = BASE["deterministic_seed"](patient_id, "noise")
    points_seed = BASE["deterministic_seed"](patient_id, "points")
    transform, topology = BASE["make_topology_safe_known_transform"](source_img, deformation_seed)

    displacement_image = BASE["_known_displacement_field"](source_img, transform)
    displacement = sitk.GetArrayFromImage(displacement_image)
    if not np.isfinite(displacement).all():
        raise ValueError("known displacement field is non-finite")
    field_magnitude = np.linalg.norm(displacement, axis=-1)

    fixed_roi = BASE["make_fixed_roi_mask"](mask_crop, source_img, transform)
    idx_zyx, eligible_count, margins_zyx, reference_mm = sample_landmarks(
        fixed_roi, spacing, points_seed
    )
    if len(np.unique(idx_zyx, axis=0)) != N_LANDMARKS:
        raise ValueError("point sampler did not produce 50 unique points")
    if not np.all(fixed_roi[tuple(idx_zyx.T)]):
        raise ValueError("sampled point is outside the fixed-domain prostate ROI")

    points = BASE["landmark_geometry"](source_img, transform, idx_zyx)
    return {
        "patient_id": patient_id,
        "source_key": BASE["source_key"](patient_id),
        "role": role,
        "series_uid": series_uid,
        "status": "complete",
        "deformation_seed": deformation_seed,
        "noise_seed": noise_seed,
        "points_seed": points_seed,
        "shape_zyx": [int(value) for value in crop.shape],
        "spacing_xyz_mm": [float(value) for value in spacing],
        "raw_jacobian_min": float(topology["raw_jacobian_min"]),
        "topology_scale": float(topology["topology_scale"]),
        "topology_attenuated": bool(topology["topology_attenuated"]),
        "jacobian_min": float(topology["jacobian_min"]),
        "fixed_roi_voxels": int(np.sum(fixed_roi)),
        "eligible_fixed_roi_voxels": eligible_count,
        "boundary_margin_reference_mm": float(reference_mm),
        "boundary_margin_voxels_zyx": [int(value) for value in margins_zyx],
        "sampled_roi_points": N_LANDMARKS,
        "field_true_displacement_min_mm": float(np.min(field_magnitude)),
        "field_true_displacement_median_mm": float(np.median(field_magnitude)),
        "field_true_displacement_p90_mm": float(np.percentile(field_magnitude, 90)),
        "field_true_displacement_max_mm": float(np.max(field_magnitude)),
        **points,
    }


def build_audit() -> dict[str, Any]:
    amendment = load_amendment_authorization()
    base_globals = BASE["build_audit"].__globals__
    original_preflight_geometry = base_globals["preflight_geometry"]
    base_globals["preflight_geometry"] = preflight_geometry
    try:
        result = BASE["build_audit"]()
    finally:
        base_globals["preflight_geometry"] = original_preflight_geometry

    result["schema_version"] = 2
    result["audit"] = "deformation-only-preflight-amendment-1"
    result["frozen_design"].pop("roi_boundary_margin_voxels", None)
    result["frozen_design"]["boundary_margin_rule"] = {
        "reference_margin_voxels": REFERENCE_MARGIN_VOXELS,
        "reference_spacing": "minimum voxel spacing of the prepared anatomy",
        "reference_margin_mm": "8 * min(spacing_xyz_mm)",
        "axis_margin_rule": "ceil(reference_margin_mm / axis_spacing_mm)",
        "minimum_axis_margin_voxels": 1,
    }
    result["amendment"] = {
        "protocol_amendment": str(AMENDMENT_PATH.relative_to(REPO_ROOT)),
        "request": str(AMENDMENT_REQUEST_PATH.relative_to(REPO_ROOT)),
        "prior_preflight_record": str(PREFLIGHT_RESULT_1_PATH.relative_to(REPO_ROOT)),
        "prior_preflight_workflow_run_id": amendment["prior_preflight"]["workflow_run_id"],
        "base_preflight_script_blob_sha": amendment["base_preflight"]["script_blob_sha"],
    }
    return result


def failure_record(exc: BaseException) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "milestone": "M6",
        "audit": "deformation-only-preflight-amendment-1",
        "status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "forward_registration_performed": False,
            "reverse_registration_performed": False,
            "sigma_computed": False,
            "ice_computed": False,
            "calibration_fit_performed": False,
            "evaluation_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build_audit()
    except Exception as exc:
        result = failure_record(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_DEFORMATION_AMENDMENT_1_STATUS={result['status'].upper()}")
    print(f"M6_DEFORMATION_COMPLETE_COUNT={result.get('complete_count', 0)}")
    print(f"M6_DEFORMATION_FAILURE_COUNT={result.get('failure_count', 0)}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
