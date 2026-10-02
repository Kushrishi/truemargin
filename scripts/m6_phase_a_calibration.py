#!/usr/bin/env python3
"""Run the source-pinned TrueMargin M6 Phase A calibration stage.

Phase A is result-bearing, but calibration-only. One invocation may run exactly one
patient from the frozen 30-anatomy calibration registry. Aggregation consumes only
those per-anatomy artifacts and fits the prospectively frozen source-specific HCP
thresholds. The 30 evaluation anatomies are never authorized or loaded here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import runpy
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

from truemargin import calibration as cal
from truemargin import comparators
from truemargin import hierarchical_conformal as hcp
from truemargin import hyperparameter as hyper
from truemargin import io_utils as ioutil

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = REPO_ROOT / "research" / "M6_PHASE_A_CALIBRATION_REQUEST.json"
FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_INPUT_FREEZE.json"
GEOMETRY_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_GEOMETRY_FREEZE.json"
AMENDED_PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight_amendment_1.py"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "m6_phase_a_calibration.json"

AMENDED = runpy.run_path(str(AMENDED_PREFLIGHT_PATH), run_name="m6_phase_a_preflight")
BASE = AMENDED["BASE"]
INTENSITY_NOISE_STD = 0.03
EXPECTED_CALIBRATION = 30
EXPECTED_PER_SOURCE = 15
EXPECTED_POINTS = 50
NOMINAL_LEVELS = (0.80, 0.90, 0.95)
GEOMETRY_HASH_FIELDS = (
    "patient_id",
    "source_key",
    "role",
    "series_uid",
    "deformation_seed",
    "noise_seed",
    "points_seed",
    "shape_zyx",
    "spacing_xyz_mm",
    "topology_scale",
    "boundary_margin_reference_mm",
    "boundary_margin_voxels_zyx",
    "landmark_indices_zyx",
    "landmark_physical_xyz_mm",
    "transformed_physical_xyz_mm",
    "true_displacement_xyz_mm",
)


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _round_floats(value: Any, decimals: int) -> Any:
    if isinstance(value, float):
        return round(value, decimals)
    if isinstance(value, list):
        return [_round_floats(item, decimals) for item in value]
    if isinstance(value, dict):
        return {key: _round_floats(item, decimals) for key, item in value.items()}
    return value


def geometry_hash(record: dict[str, Any], *, decimals: int) -> str:
    payload = {field: record[field] for field in GEOMETRY_HASH_FIELDS}
    canonical = json.dumps(
        _round_floats(payload, decimals),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def array_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype="<f8"))
    header = json.dumps(list(array.shape), separators=(",", ":")).encode() + b"\0"
    return hashlib.sha256(header + array.tobytes(order="C")).hexdigest()


def provenance_record() -> dict[str, Any]:
    """Return hosted-run provenance without changing the scientific inputs."""
    return {
        "source_git_sha": os.environ.get("GITHUB_SHA"),
        "workflow_run_id": (
            int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None
        ),
        "request_blob_sha": git_blob_sha(REQUEST_PATH),
        "input_freeze_blob_sha": git_blob_sha(FREEZE_PATH),
        "geometry_freeze_blob_sha": git_blob_sha(GEOMETRY_FREEZE_PATH),
    }


def _json_vector(values: np.ndarray) -> list[float | str]:
    output: list[float | str] = []
    for value in np.asarray(values, dtype=np.float64):
        if np.isposinf(value):
            output.append("Infinity")
        elif np.isfinite(value):
            output.append(float(value))
        else:
            raise ValueError(
                "M6 Phase A vectors may contain only finite values or positive infinity"
            )
    return output


def _parse_vector(values: list[float | str]) -> np.ndarray:
    parsed = [np.inf if value == "Infinity" else float(value) for value in values]
    return np.asarray(parsed, dtype=np.float64)


def source_key(patient_id: str) -> str:
    return str(BASE["source_key"](patient_id))


def load_freeze() -> dict[str, Any]:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("schema_version") != 1 or freeze.get("record") != "m6-phase-a-input-freeze":
        raise RuntimeError("Unexpected M6 Phase A input freeze identity")
    geometry_freeze = json.loads(GEOMETRY_FREEZE_PATH.read_text(encoding="utf-8"))
    if geometry_freeze.get("calibration") is None:
        raise RuntimeError("Missing M6 Phase A geometry registry")
    calibration = freeze.get("calibration")
    if not isinstance(calibration, dict) or len(calibration) != EXPECTED_CALIBRATION:
        raise RuntimeError(
            "M6 Phase A geometry freeze must contain exactly 30 calibration anatomies"
        )
    geometry_records = geometry_freeze["calibration"]
    if set(geometry_records) != set(calibration):
        raise RuntimeError("M6 Phase A input and geometry registries disagree on calibration roles")
    for patient_id, record in calibration.items():
        if record["series_uid"] != geometry_records[patient_id]["series_uid"]:
            raise RuntimeError(f"M6 Phase A series identity drift for {patient_id}")
        if record["geometry_sha256"] != geometry_records[patient_id]["geometry_sha256"]:
            raise RuntimeError(f"M6 Phase A geometry identity drift for {patient_id}")
    counts = {
        source: sum(source_key(patient) == source for patient in calibration)
        for source in ("prostate_3t", "prostate_diagnosis")
    }
    if counts != {"prostate_3t": EXPECTED_PER_SOURCE, "prostate_diagnosis": EXPECTED_PER_SOURCE}:
        raise RuntimeError(f"Unexpected M6 Phase A source counts: {counts}")
    return freeze


def load_request() -> dict[str, Any]:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "milestone": "M6",
        "authorized_mode": "phase-a-calibration-only",
        "result_bearing_authorized": True,
        "forward_registration_authorized": True,
        "reverse_registration_authorized": True,
        "sigma_computation_authorized": True,
        "ice_computation_authorized": True,
        "calibration_fit_authorized": True,
        "evaluation_authorized": False,
        "expected_calibration_anatomies": EXPECTED_CALIBRATION,
        "expected_anatomies_per_source": EXPECTED_PER_SOURCE,
        "points_per_anatomy": EXPECTED_POINTS,
        "expected_case_output_prefix": "outputs/m6_phase_a_case_",
        "expected_aggregate_output": "outputs/m6_phase_a_calibration.json",
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise RuntimeError(f"M6 Phase A request mismatch for {key}: {request.get(key)!r}")

    if tuple(float(value) for value in request.get("nominal_coverages", ())) != NOMINAL_LEVELS:
        raise RuntimeError("M6 Phase A nominal coverage levels do not match the frozen protocol")
    if request.get("primary_signal") != "nine-member hyperparameter-ensemble sigma":
        raise RuntimeError("Unexpected M6 Phase A primary signal")
    if request.get("secondary_signal") != "ensemble-mean ICE":
        raise RuntimeError("Unexpected M6 Phase A secondary signal")
    if request.get("near_zero_diagnostic_mm") != 1e-6:
        raise RuntimeError("Unexpected prospective near-zero diagnostic threshold")

    blobs = request.get("source_blobs")
    if not isinstance(blobs, dict) or not blobs:
        raise RuntimeError("M6 Phase A request has no source-blob registry")
    for relative_path, expected_sha in blobs.items():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            raise RuntimeError(f"Pinned M6 Phase A source file is missing: {relative_path}")
        observed = git_blob_sha(path)
        if observed != expected_sha:
            raise RuntimeError(
                f"M6 Phase A source drift for {relative_path}: "
                f"expected {expected_sha}, got {observed}"
            )

    freeze = load_freeze()
    if request.get("source_preflight_artifact_sha256") != freeze.get(
        "source_preflight_artifact_sha256"
    ):
        raise RuntimeError("M6 Phase A preflight artifact identity mismatch")
    if request.get("source_preflight_audit_sha256") != freeze.get("source_preflight_audit_sha256"):
        raise RuntimeError("M6 Phase A preflight audit identity mismatch")
    return request


def calibration_patients() -> list[str]:
    load_request()
    return sorted(load_freeze()["calibration"])


def _crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent = np.asarray(
        [
            shape_zyx[2] * spacing_xyz[0],
            shape_zyx[1] * spacing_xyz[1],
            shape_zyx[0] * spacing_xyz[2],
        ],
        dtype=np.float64,
    )
    return float(np.linalg.norm(extent))


def _build_synthetic(
    patient_id: str,
    image: sitk.Image,
    label: sitk.Image,
    geometry: dict[str, Any],
) -> dict[str, Any]:
    crop, mask_crop, spacing = BASE["prepare_anatomy"](image, label)
    source_img = BASE["make_source_image"](crop, spacing)
    transform, _ = BASE["make_topology_safe_known_transform"](
        source_img, BASE["deterministic_seed"](patient_id, "deformation")
    )
    fixed_roi = BASE["make_fixed_roi_mask"](mask_crop, source_img, transform)
    idx_zyx, _, margins_zyx, reference_mm = AMENDED["sample_landmarks"](
        fixed_roi,
        spacing,
        BASE["deterministic_seed"](patient_id, "points"),
    )

    expected_idx = np.asarray(geometry["landmark_indices_zyx"], dtype=np.int64)
    if not np.array_equal(idx_zyx, expected_idx):
        raise RuntimeError(f"Frozen M6 Phase A point geometry drift for {patient_id}")
    if [int(value) for value in margins_zyx] != geometry["boundary_margin_voxels_zyx"]:
        raise RuntimeError(f"Frozen M6 Phase A boundary margin drift for {patient_id}")
    if not math.isclose(
        float(reference_mm),
        float(geometry["boundary_margin_reference_mm"]),
        rel_tol=0.0,
        abs_tol=1e-8,
    ):
        raise RuntimeError(f"Frozen M6 Phase A physical margin drift for {patient_id}")

    fixed_img = sitk.Resample(source_img, source_img, transform, sitk.sitkLinear, 0.0)
    moving = sitk.GetArrayFromImage(source_img).astype(np.float32)
    fixed = sitk.GetArrayFromImage(fixed_img).astype(np.float32)
    scale = float(np.std(moving))
    if not np.isfinite(scale) or scale <= np.finfo(np.float32).eps:
        raise ValueError(f"Invalid moving-source intensity scale for {patient_id}")
    moving = moving / scale
    fixed = fixed / scale
    noise_seed = BASE["deterministic_seed"](patient_id, "noise")
    rng = np.random.default_rng(noise_seed)
    fixed = fixed + rng.normal(0.0, INTENSITY_NOISE_STD, fixed.shape).astype(np.float32)

    true_displacement = np.asarray(geometry["true_displacement_xyz_mm"], dtype=np.float64).T
    if true_displacement.shape != (3, EXPECTED_POINTS):
        raise RuntimeError(f"Unexpected frozen true-displacement shape for {patient_id}")
    return {
        "fixed": fixed,
        "moving": moving,
        "idx_zyx": idx_zyx,
        "u_true": true_displacement,
        "spacing": tuple(float(value) for value in spacing),
        "crop_diagonal_mm": _crop_diagonal_mm(crop.shape, spacing),
    }


def _signal_diagnostics(values: np.ndarray, near_zero_mm: float) -> dict[str, Any]:
    signal = np.asarray(values, dtype=np.float64)
    if signal.ndim != 1 or len(signal) != EXPECTED_POINTS:
        raise ValueError("M6 signal diagnostic requires exactly 50 pointwise values")
    return {
        "zero_count": int(np.sum(signal == 0.0)),
        "near_zero_positive_count": int(np.sum((signal > 0.0) & (signal <= near_zero_mm))),
        "minimum_mm": float(np.min(signal)),
        "median_mm": float(np.median(signal)),
        "maximum_mm": float(np.max(signal)),
    }


def run_case(patient_id: str) -> dict[str, Any]:
    request = load_request()
    freeze = load_freeze()
    calibration = freeze["calibration"]
    if patient_id not in calibration:
        raise RuntimeError(f"Patient is not authorized for M6 Phase A calibration: {patient_id}")

    expected = calibration[patient_id]
    uid = str(expected["series_uid"])
    labels_zip = BASE["_download"](BASE["TRAINING_LABEL_URL"])
    labels = BASE["label_members"](labels_zip)
    if patient_id not in labels:
        raise RuntimeError(f"Official challenge label not found for {patient_id}")

    with tempfile.TemporaryDirectory(prefix=f"truemargin-m6-phase-a-{patient_id}-") as tmp:
        root = Path(tmp)
        dicom_payload = BASE["download_series"](uid)
        observed_dicom_sha = hashlib.sha256(dicom_payload).hexdigest()
        if observed_dicom_sha != expected["dicom_zip_sha256"]:
            raise RuntimeError(
                f"M6 Phase A DICOM payload drift for {patient_id}: "
                f"expected {expected['dicom_zip_sha256']}, got {observed_dicom_sha}"
            )
        observed_label_sha = hashlib.sha256(labels[patient_id]).hexdigest()
        if observed_label_sha != expected["label_sha256"]:
            raise RuntimeError(
                f"M6 Phase A label payload drift for {patient_id}: "
                f"expected {expected['label_sha256']}, got {observed_label_sha}"
            )
        observed_patient, image = BASE["_read_series"](dicom_payload, uid, root / "dicom")
        if observed_patient != patient_id:
            raise RuntimeError(
                f"M6 Phase A patient mismatch: expected {patient_id}, observed {observed_patient}"
            )
        label = BASE["_read_label"](labels[patient_id], root / "label.nrrd")
        geometry = AMENDED["preflight_geometry"](
            patient_id,
            "calibration",
            uid,
            image,
            label,
        )
        observed_geometry_hash = geometry_hash(
            geometry, decimals=int(freeze["geometry_hash_rounding_decimals"])
        )
        if observed_geometry_hash != expected["geometry_sha256"]:
            raise RuntimeError(
                f"M6 Phase A frozen geometry hash mismatch for {patient_id}: "
                f"expected {expected['geometry_sha256']}, got {observed_geometry_hash}"
            )

        synthetic = _build_synthetic(patient_id, image, label, geometry)
        fixed = np.asarray(synthetic["fixed"], dtype=np.float32)
        moving = np.asarray(synthetic["moving"], dtype=np.float32)
        spacing = tuple(float(value) for value in synthetic["spacing"])
        idx_zyx = np.asarray(synthetic["idx_zyx"], dtype=np.int64)
        crop_diagonal = float(synthetic["crop_diagonal_mm"])

        forward = hyper.run_hyperparameter_ensemble(
            fixed,
            moving,
            spacing=spacing,
            crop_diagonal_mm=crop_diagonal,
        )
        record: dict[str, Any] = {
            "schema_version": 1,
            "milestone": "M6",
            "phase": "A",
            "provenance": provenance_record(),
            "patient_id": patient_id,
            "source_key": source_key(patient_id),
            "role": "calibration",
            "series_uid": uid,
            "geometry_sha256": observed_geometry_hash,
            "dicom_zip_sha256": observed_dicom_sha,
            "label_sha256": observed_label_sha,
            "forward_complete": bool(forward.complete),
            "forward_member_reasons": list(forward.member_reasons),
            "reverse_complete": False,
            "reverse_member_reasons": [],
            "ice_valid": False,
            "ice_failure_reason": None,
            "points": EXPECTED_POINTS,
            "known_error_mm": [],
            "sigma_mm": [],
            "sigma_score": [],
            "ice_mm": [],
            "ice_score": [],
            "array_sha256": {},
            "signal_diagnostics": {},
            "authorization_boundary": {
                "evaluation_authorized": False,
                "evaluation_accessed": False,
            },
        }

        if not forward.complete:
            record["status"] = "primary_incomplete"
            return record

        assert forward.u_mean is not None
        assert forward.sigma is not None
        u_est = ioutil.sample_field_at_points(forward.u_mean, idx_zyx)
        sigma_mm = np.asarray(
            ioutil.sample_field_at_points(forward.sigma, idx_zyx), dtype=np.float64
        )
        error_mm = np.asarray(
            cal.displacement_error(u_est, np.asarray(synthetic["u_true"], dtype=np.float64)),
            dtype=np.float64,
        )
        sigma_score = hcp.ratio_nonconformity(error_mm, sigma_mm)
        record["known_error_mm"] = error_mm.tolist()
        record["sigma_mm"] = sigma_mm.tolist()
        record["sigma_score"] = _json_vector(sigma_score)
        record["array_sha256"].update(
            {
                "known_error_mm": array_sha256(error_mm),
                "sigma_mm": array_sha256(sigma_mm),
                "sigma_score": array_sha256(sigma_score),
            }
        )
        record["signal_diagnostics"]["sigma"] = _signal_diagnostics(
            sigma_mm, float(request["near_zero_diagnostic_mm"])
        )

        try:
            reverse = hyper.run_hyperparameter_ensemble(
                moving,
                fixed,
                spacing=spacing,
                crop_diagonal_mm=crop_diagonal,
            )
            record["reverse_complete"] = bool(reverse.complete)
            record["reverse_member_reasons"] = list(reverse.member_reasons)
            if reverse.complete:
                assert reverse.u_mean is not None
                ice_mm = np.asarray(
                    comparators.inverse_consistency_scores(
                        forward.u_mean,
                        reverse.u_mean,
                        idx_zyx,
                        spacing,
                    ),
                    dtype=np.float64,
                )
                ice_score = hcp.ratio_nonconformity(error_mm, ice_mm)
                record["ice_valid"] = True
                record["ice_mm"] = ice_mm.tolist()
                record["ice_score"] = _json_vector(ice_score)
                record["array_sha256"].update(
                    {
                        "ice_mm": array_sha256(ice_mm),
                        "ice_score": array_sha256(ice_score),
                    }
                )
                record["signal_diagnostics"]["ice"] = _signal_diagnostics(
                    ice_mm, float(request["near_zero_diagnostic_mm"])
                )
            else:
                failed = sum(reason != "ok" for reason in reverse.member_reasons)
                record["ice_failure_reason"] = (
                    f"reverse_ensemble_incomplete:{failed}/{len(reverse.member_reasons)}"
                )
        except Exception as exc:
            record["ice_failure_reason"] = f"{type(exc).__name__}:{exc}"

        record["status"] = "complete"
        return record


def _load_case_files(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("m6_phase_a_case_*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _threshold_record(groups: list[np.ndarray], nominal: float) -> dict[str, Any]:
    result = hcp.hierarchical_conformal_threshold(groups, nominal_coverage=nominal)
    return {
        "nominal_coverage": nominal,
        "alpha": result.alpha,
        "threshold": None if np.isposinf(result.threshold) else float(result.threshold),
        "threshold_is_infinite": bool(np.isposinf(result.threshold)),
        "calibration_groups": result.calibration_groups,
        "calibration_scores": result.calibration_scores,
        "infinity_atom_mass": result.infinity_atom_mass,
    }


def _efficiency_summary(
    cases: list[dict[str, Any]], signal_key: str, threshold: float
) -> dict[str, Any]:
    medians: list[float] = []
    infinite_points = 0
    total_points = 0
    for case in cases:
        signal = np.asarray(case[signal_key], dtype=np.float64)
        radii = hcp.calibrated_radius(signal, threshold)
        total_points += len(radii)
        infinite_points += int(np.sum(np.isposinf(radii)))
        medians.append(float(np.median(radii)))
    finite_medians = np.asarray(
        [value for value in medians if np.isfinite(value)], dtype=np.float64
    )
    return {
        "per_anatomy_median_radius_mm": medians,
        "median_of_anatomy_medians_mm": (
            float(np.median(finite_medians)) if len(finite_medians) else None
        ),
        "iqr_of_anatomy_medians_mm": (
            float(np.percentile(finite_medians, 75) - np.percentile(finite_medians, 25))
            if len(finite_medians)
            else None
        ),
        "infinite_radius_points": infinite_points,
        "total_points": total_points,
    }


def aggregate(directory: Path) -> dict[str, Any]:
    request = load_request()
    freeze = load_freeze()
    expected_patients = set(freeze["calibration"])
    records = _load_case_files(directory)
    observed = [str(record.get("patient_id")) for record in records]
    if len(observed) != len(set(observed)):
        raise RuntimeError("Duplicate M6 Phase A case artifacts")
    if set(observed) != expected_patients:
        missing = sorted(expected_patients - set(observed))
        unexpected = sorted(set(observed) - expected_patients)
        raise RuntimeError(
            f"M6 Phase A case-set mismatch: missing={missing}, unexpected={unexpected}"
        )

    records.sort(key=lambda item: str(item["patient_id"]))
    primary_failures = [record for record in records if record.get("status") != "complete"]
    sources: dict[str, Any] = {}
    for source in ("prostate_3t", "prostate_diagnosis"):
        source_cases = [record for record in records if record["source_key"] == source]
        if len(source_cases) != EXPECTED_PER_SOURCE:
            raise RuntimeError(f"M6 Phase A source {source} does not contain 15 cases")
        source_primary_complete = all(record.get("status") == "complete" for record in source_cases)
        source_ice_complete = source_primary_complete and all(
            bool(record.get("ice_valid")) for record in source_cases
        )
        source_record: dict[str, Any] = {
            "calibration_anatomies": len(source_cases),
            "primary_complete": source_primary_complete,
            "ice_complete": source_ice_complete,
            "sigma_thresholds": {},
            "ice_thresholds": {},
            "sigma_efficiency": {},
            "ice_efficiency": {},
        }
        if source_primary_complete:
            sigma_groups = [_parse_vector(record["sigma_score"]) for record in source_cases]
            for nominal in NOMINAL_LEVELS:
                fitted = hcp.hierarchical_conformal_threshold(
                    sigma_groups, nominal_coverage=nominal
                )
                key = f"{int(round(nominal * 100))}"
                source_record["sigma_thresholds"][key] = _threshold_record(sigma_groups, nominal)
                source_record["sigma_efficiency"][key] = _efficiency_summary(
                    source_cases, "sigma_mm", fitted.threshold
                )
        if source_ice_complete:
            ice_groups = [_parse_vector(record["ice_score"]) for record in source_cases]
            for nominal in NOMINAL_LEVELS:
                fitted = hcp.hierarchical_conformal_threshold(
                    ice_groups, nominal_coverage=nominal
                )
                key = f"{int(round(nominal * 100))}"
                source_record["ice_thresholds"][key] = _threshold_record(ice_groups, nominal)
                source_record["ice_efficiency"][key] = _efficiency_summary(
                    source_cases, "ice_mm", fitted.threshold
                )
        sources[source] = source_record

    primary_complete = not primary_failures and all(
        source_record["primary_complete"] for source_record in sources.values()
    )
    return {
        "schema_version": 1,
        "milestone": "M6",
        "phase": "A",
        "provenance": provenance_record(),
        "status": "complete" if primary_complete else "primary_incomplete",
        "calibration_anatomies": EXPECTED_CALIBRATION,
        "evaluation_anatomies_accessed": 0,
        "primary_signal": request["primary_signal"],
        "secondary_signal": request["secondary_signal"],
        "nominal_coverages": list(NOMINAL_LEVELS),
        "near_zero_diagnostic_mm": request["near_zero_diagnostic_mm"],
        "source_preflight_artifact_sha256": request["source_preflight_artifact_sha256"],
        "source_preflight_audit_sha256": request["source_preflight_audit_sha256"],
        "sources": sources,
        "cases": records,
        "primary_failure_patients": [record["patient_id"] for record in primary_failures],
        "authorization_boundary": {
            "phase_a_calibration_authorized": True,
            "evaluation_authorized": False,
            "evaluation_performed": False,
            "phase_b_authorized": False,
        },
        "next_step": (
            "Review and seal the complete Phase A artifact and exact thresholds before creating "
            "a separate Phase B evaluation authorization."
            if primary_complete
            else (
                "Preserve primary scientific failures. Do not replace cases or alter the "
                "frozen protocol."
            )
        ),
    }


def write_json(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--patient-id")
    mode.add_argument("--aggregate-dir", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        if args.patient_id:
            record = run_case(str(args.patient_id))
        else:
            record = aggregate(Path(args.aggregate_dir))
    except Exception as exc:
        record = {
            "schema_version": 1,
            "milestone": "M6",
            "phase": "A",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "authorization_boundary": {
                "evaluation_authorized": False,
                "evaluation_performed": False,
            },
        }

    write_json(args.output, record)
    print(f"M6_PHASE_A_STATUS={record['status'].upper()}")
    print("M6_EVALUATION_AUTHORIZED=False")
    return 0 if record["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
