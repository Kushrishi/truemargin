"""Pure contract helpers for the frozen TrueMargin M6 Phase A study.

This module defines cohort, provenance, geometry, hashing, and calibration aggregation
rules. It does not acquire data or run registration.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from truemargin.hierarchical_conformal import (
    calibrated_radius,
    hierarchical_conformal_threshold,
)

EXPECTED_CALIBRATION_ANATOMIES = 30
EXPECTED_PER_SOURCE = 15
EXPECTED_POINTS = 50
NOMINAL_COVERAGES = (0.80, 0.90, 0.95)
GEOMETRY_HASH_ROUNDING_DECIMALS = 8
SOURCES = ("prostate_3t", "prostate_diagnosis")
UID_RE = re.compile(r"\d+(?:\.\d+)+")

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


def _round_geometry(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, GEOMETRY_HASH_ROUNDING_DECIMALS)
    if isinstance(value, list):
        return [_round_geometry(item) for item in value]
    if isinstance(value, dict):
        return {key: _round_geometry(item) for key, item in value.items()}
    return value


def geometry_sha256(record: dict[str, Any]) -> str:
    """Return the canonical frozen Phase A geometry identity."""
    missing = [field for field in GEOMETRY_HASH_FIELDS if field not in record]
    if missing:
        raise ValueError(f"geometry record is missing fields: {missing}")
    payload = _round_geometry({field: record[field] for field in GEOMETRY_HASH_FIELDS})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def array_sha256(values: np.ndarray) -> str:
    """Hash one numeric result vector with explicit dtype and shape identity."""
    array = np.asarray(values, dtype="<f8")
    if array.ndim != 1:
        raise ValueError("result vector must be one-dimensional")
    header = json.dumps(
        {"dtype": "<f8", "shape": list(array.shape)}, sort_keys=True
    ).encode()
    return hashlib.sha256(
        header + b"\0" + np.ascontiguousarray(array).tobytes()
    ).hexdigest()


def load_split(path: Path) -> tuple[dict[str, str], set[str]]:
    split = json.loads(path.read_text(encoding="utf-8"))
    calibration: dict[str, str] = {}
    evaluation: set[str] = set()
    for source in SOURCES:
        roles = split["roles"][source]
        for patient_id in roles["calibration"]:
            if patient_id in calibration:
                raise RuntimeError(f"duplicate calibration PatientID: {patient_id}")
            calibration[patient_id] = source
        evaluation.update(roles["evaluation"])
    if len(calibration) != EXPECTED_CALIBRATION_ANATOMIES:
        raise RuntimeError(f"expected 30 calibration anatomies; found {len(calibration)}")
    if len(evaluation) != EXPECTED_CALIBRATION_ANATOMIES:
        raise RuntimeError(f"expected 30 evaluation anatomies; found {len(evaluation)}")
    if set(calibration) & evaluation:
        raise RuntimeError("calibration and evaluation cohorts overlap")
    for source in SOURCES:
        if sum(value == source for value in calibration.values()) != EXPECTED_PER_SOURCE:
            raise RuntimeError(f"calibration source imbalance for {source}")
    return calibration, evaluation


def load_geometry_freeze(path: Path) -> dict[str, dict[str, str]]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("schema_version") != 1 or freeze.get("record") != "m6-phase-a-geometry-freeze":
        raise RuntimeError("unexpected M6 Phase A geometry freeze schema")
    if freeze.get("geometry_hash_rounding_decimals") != GEOMETRY_HASH_ROUNDING_DECIMALS:
        raise RuntimeError("unexpected M6 geometry hash rounding rule")
    records = freeze.get("calibration")
    if not isinstance(records, dict) or len(records) != EXPECTED_CALIBRATION_ANATOMIES:
        raise RuntimeError(
            "M6 Phase A geometry freeze must contain exactly 30 calibration anatomies"
        )
    for patient_id, record in records.items():
        if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("geometry_sha256", ""))):
            raise RuntimeError(f"invalid geometry digest for {patient_id}")
        if UID_RE.fullmatch(str(record.get("series_uid", ""))) is None:
            raise RuntimeError(f"invalid frozen SeriesInstanceUID for {patient_id}")
    return records


def verify_source_files(
    repo_root: Path,
    source_git_sha: str,
    result_defining_paths: tuple[str, ...],
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", source_git_sha):
        raise RuntimeError(f"invalid pinned source Git SHA: {source_git_sha!r}")

    def git(*args: str) -> bytes:
        return subprocess.check_output(
            ["git", *args], cwd=repo_root, stderr=subprocess.STDOUT
        )

    try:
        git("cat-file", "-e", f"{source_git_sha}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pinned source commit is unavailable: {source_git_sha}") from exc

    drift: list[str] = []
    for relative_path in result_defining_paths:
        current = (repo_root / relative_path).read_bytes()
        try:
            frozen = git("show", f"{source_git_sha}:{relative_path}")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"result-defining path missing from source: {relative_path}"
            ) from exc
        if current != frozen:
            drift.append(relative_path)
    if drift:
        raise RuntimeError("result-defining source drift: " + ", ".join(drift))


def verify_request(
    *,
    repo_root: Path,
    request_path: Path,
    split_path: Path,
    geometry_freeze_path: Path,
    pinned_paths: dict[str, Path],
    result_defining_paths: tuple[str, ...],
) -> dict[str, Any]:
    if not request_path.is_file():
        raise RuntimeError(
            "M6 Phase A request is absent; result-bearing calibration is unauthorized"
        )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "milestone": "M6",
        "authorized_mode": "phase-a-calibration-only",
        "result_bearing_authorized": True,
        "phase_a_calibration_authorized": True,
        "evaluation_authorized": False,
        "evaluation_anatomies_authorized": 0,
        "calibration_anatomies_authorized": 30,
        "forward_registrations_planned": 270,
        "reverse_registrations_planned": 270,
        "primary_signal": "sigma_mm",
        "secondary_signal": "ice_mm",
        "points_per_anatomy": 50,
        "nominal_coverages": [0.8, 0.9, 0.95],
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise RuntimeError(
                f"M6 Phase A authorization mismatch for {key}: {request.get(key)!r}"
            )

    calibration, evaluation = load_split(split_path)
    freeze = load_geometry_freeze(geometry_freeze_path)
    if set(freeze) != set(calibration):
        raise RuntimeError("Phase A geometry freeze does not match the calibration cohort")
    if set(freeze) & evaluation:
        raise RuntimeError("Phase A geometry freeze exposes an evaluation anatomy")

    source_git_sha = str(request.get("source_git_sha", ""))
    verify_source_files(repo_root, source_git_sha, result_defining_paths)
    if request.get("source_ci_conclusion") != "success" or not isinstance(
        request.get("source_ci_run_id"), int
    ):
        raise RuntimeError("M6 Phase A request does not pin a successful source CI run")

    pins = request.get("pinned_blobs", {})
    for name, path in pinned_paths.items():
        if git_blob_sha(path) != pins.get(name):
            raise RuntimeError(f"M6 Phase A pinned blob mismatch: {name}")
    return request


def radius_efficiency(signals: list[np.ndarray], threshold: float) -> dict[str, Any]:
    medians: list[float] = []
    infinite_radii = 0
    total_radii = 0
    for signal in signals:
        radii = calibrated_radius(signal, threshold)
        infinite_radii += int(np.sum(np.isposinf(radii)))
        total_radii += len(radii)
        medians.append(float(np.median(radii)))
    values = np.asarray(medians, dtype=np.float64)
    if np.isposinf(values).all():
        median = q25 = q75 = float("inf")
    else:
        median = float(np.median(values))
        q25 = float(np.percentile(values, 25))
        q75 = float(np.percentile(values, 75))
    return {
        "per_anatomy_median_radius_mm": medians,
        "median_of_anatomy_medians_mm": median,
        "iqr_of_anatomy_medians_mm": [q25, q75],
        "infinite_radius_count": infinite_radii,
        "total_radius_count": total_radii,
    }


def aggregate_records(
    records: dict[str, dict[str, Any]],
    calibration: dict[str, str],
) -> tuple[str, list[str], dict[str, Any]]:
    primary_failures = [
        patient for patient, record in records.items() if not bool(record.get("primary_complete"))
    ]
    source_results: dict[str, Any] = {}
    for source in SOURCES:
        patients = sorted(
            patient for patient, patient_source in calibration.items() if patient_source == source
        )
        source_records = [records[patient] for patient in patients]
        primary_assessable = all(bool(record.get("primary_complete")) for record in source_records)
        ice_assessable = all(bool(record.get("ice_complete")) for record in source_records)
        method_results: dict[str, Any] = {}

        for method, assessable, signal_key, score_key in (
            ("sigma", primary_assessable, "sigma_mm", "sigma_scores"),
            ("ice", ice_assessable, "ice_mm", "ice_scores"),
        ):
            if not assessable:
                method_results[method] = {
                    "assessable": False,
                    "reason": "one or more predeclared calibration anatomies are method-incomplete",
                }
                continue
            groups = [np.asarray(record[score_key], dtype=np.float64) for record in source_records]
            signals = [
                np.asarray(record[signal_key], dtype=np.float64) for record in source_records
            ]
            if any(group.shape != (EXPECTED_POINTS,) for group in groups):
                raise RuntimeError(f"{source} {method} score group shape mismatch")

            thresholds: dict[str, Any] = {}
            for nominal in NOMINAL_COVERAGES:
                fitted = hierarchical_conformal_threshold(groups, nominal_coverage=nominal)
                if nominal == 0.95 and not np.isposinf(fitted.threshold):
                    raise RuntimeError("K=15 95% HCP sentinel must be positive infinity")
                thresholds[f"{nominal:.2f}"] = {
                    "nominal_coverage": nominal,
                    "alpha": fitted.alpha,
                    "threshold": fitted.threshold,
                    "finite": fitted.is_finite,
                    "calibration_groups": fitted.calibration_groups,
                    "calibration_scores": fitted.calibration_scores,
                    "infinity_atom_mass": fitted.infinity_atom_mass,
                    "radius_efficiency": radius_efficiency(signals, fitted.threshold),
                }
            method_results[method] = {
                "assessable": True,
                "thresholds": thresholds,
                "zero_signal_count": int(sum(np.sum(signal == 0.0) for signal in signals)),
                "infinite_score_count": int(
                    sum(np.sum(np.isposinf(group)) for group in groups)
                ),
                "score_hashes": {
                    record["patient_id"]: record["hashes"][score_key]
                    for record in source_records
                },
            }

        source_results[source] = {
            "patients": patients,
            "primary_assessable": primary_assessable,
            "ice_assessable": ice_assessable,
            "methods": method_results,
        }

    status = "complete" if not primary_failures else "incomplete"
    return status, primary_failures, source_results
