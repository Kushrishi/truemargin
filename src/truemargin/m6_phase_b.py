"""Sealed-threshold M6 evaluation contracts; no acquisition or registration."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from truemargin.hierarchical_conformal import calibrated_radius, ratio_nonconformity
from truemargin.m6_phase_a import (
    EXPECTED_POINTS,
    SOURCES,
    array_sha256,
    git_blob_sha,
    load_split,
    radius_efficiency,
    verify_source_files,
)

RUNTIME_VERSIONS = {"python": "3.12.14", "numpy": "2.5.3", "scipy": "1.18.1", "SimpleITK": "2.5.6"}
NEAR_ZERO_VALUE = float(np.finfo(np.float64).eps)
NOMINALS = ("0.80", "0.90", "0.95")


def evaluation_cohort(split_path: Path) -> dict[str, str]:
    calibration, evaluation = load_split(split_path)
    split = json.loads(split_path.read_text())
    result = {
        patient: source for source in SOURCES for patient in split["roles"][source]["evaluation"]
    }
    if set(result) != evaluation or set(result) & set(calibration):
        raise RuntimeError("Phase B cohort differs from the frozen split")
    if any(sum(s == source for s in result.values()) != 15 for source in SOURCES):
        raise RuntimeError("Phase B source imbalance")
    return result


def load_evaluation_freeze(path: Path, cohort: dict[str, str]) -> dict[str, dict[str, str]]:
    freeze = json.loads(path.read_text())
    if (
        freeze.get("schema_version") != 1
        or freeze.get("record") != "m6-phase-b-input-and-geometry-freeze"
        or freeze.get("geometry_hash_rounding_decimals") != 8
        or freeze.get("role") != "evaluation"
    ):
        raise RuntimeError("invalid Phase B input freeze")
    records = freeze.get("evaluation", {})
    if set(records) != set(cohort) or len(records) != 30:
        raise RuntimeError("Phase B input freeze does not match all 30 evaluation anatomies")
    for patient, row in records.items():
        for key in ("dicom_zip_sha256", "label_sha256", "geometry_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(row.get(key, ""))):
                raise RuntimeError(f"invalid Phase B digest: {patient}/{key}")
        if not re.fullmatch(r"\d+(?:\.\d+)+", str(row.get("series_uid", ""))):
            raise RuntimeError("invalid Phase B SeriesInstanceUID")
    return records


def load_seal(seal_path: Path, aggregate_path: Path) -> dict[str, Any]:
    seal = json.loads(seal_path.read_text())
    raw = aggregate_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != seal.get("aggregate_sha256"):
        raise RuntimeError("sealed calibration aggregate digest mismatch")
    aggregate = json.loads(raw)
    if (
        seal.get("record") != "m6-phase-a-threshold-seal"
        or seal.get("threshold_changes_authorized") is not False
        or aggregate.get("status") != "complete"
        or aggregate.get("calibration_anatomies") != 30
        or aggregate.get("evaluation_anatomies_accessed") != 0
    ):
        raise RuntimeError("Phase A acceptance boundary mismatch")
    if set(seal.get("thresholds", {})) != set(SOURCES):
        raise RuntimeError("sealed source set mismatch")
    for source in SOURCES:
        if set(seal["thresholds"][source]) != {"sigma", "ice"}:
            raise RuntimeError("sealed method set mismatch")
        for method in ("sigma", "ice"):
            fitted = aggregate["sources"][source]["methods"][method]
            frozen = seal["thresholds"][source][method]
            if frozen["assessable"] != fitted["assessable"]:
                raise RuntimeError("sealed method availability mismatch")
            if not frozen["assessable"]:
                if "thresholds" in frozen:
                    raise RuntimeError("unassessable calibration has thresholds")
                continue
            if set(frozen["thresholds"]) != set(NOMINALS):
                raise RuntimeError("sealed nominal levels mismatch")
            for nominal in NOMINALS:
                encoded = frozen["thresholds"][nominal]
                value = float("inf") if encoded == "positive_infinity" else float(encoded)
                if value != fitted["thresholds"][nominal]["threshold"]:
                    raise RuntimeError("sealed threshold differs from accepted calibration")
    return seal


def verify_request(
    *,
    repo_root: Path,
    request_path: Path,
    result_defining_paths: tuple[str, ...],
    pinned_paths: dict[str, Path],
) -> dict[str, Any]:
    if not request_path.is_file():
        raise RuntimeError("Phase B request is absent; evaluation remains unauthorized")
    request = json.loads(request_path.read_text())
    expected = {
        "schema_version": 1,
        "milestone": "M6",
        "authorized_mode": "phase-b-evaluation-only",
        "result_bearing_authorized": True,
        "evaluation_authorized": True,
        "calibration_fit_authorized": False,
        "calibration_anatomies_authorized": 0,
        "evaluation_anatomies_authorized": 30,
        "forward_registrations_planned": 270,
        "reverse_registrations_planned": 270,
        "points_per_anatomy": 50,
        "primary_signal": "sigma_mm",
        "secondary_signal": "ice_mm",
        "nominal_coverages": [0.8, 0.9, 0.95],
        "threshold_changes_authorized": False,
        "runtime_versions": {
            "python": "3.12.14",
            "numpy": "2.5.3",
            "scipy": "1.18.1",
            "SimpleITK": "2.5.6",
        },
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise RuntimeError(f"Phase B authorization mismatch: {key}")
    verify_source_files(repo_root, str(request.get("source_git_sha", "")), result_defining_paths)
    if request.get("source_ci_conclusion") != "success" or not isinstance(
        request.get("source_ci_run_id"), int
    ):
        raise RuntimeError("Phase B requires successful pinned implementation CI")
    for key, path in pinned_paths.items():
        if git_blob_sha(path) != request.get("pinned_blobs", {}).get(key):
            raise RuntimeError(f"Phase B pinned blob mismatch: {key}")
    cohort = evaluation_cohort(pinned_paths["split"])
    load_evaluation_freeze(pinned_paths["input_freeze"], cohort)
    load_seal(pinned_paths["threshold_seal"], pinned_paths["calibration_aggregate"])
    return request


def vector_diagnostics(values: np.ndarray) -> dict[str, Any]:
    return {
        "count": len(values),
        "zero_fraction": float(np.mean(values == 0)),
        "near_zero_positive_fraction": float(np.mean((values > 0) & (values <= NEAR_ZERO_VALUE))),
        "near_zero_positive_upper_bound": NEAR_ZERO_VALUE,
        "infinite_fraction": float(np.mean(np.isposinf(values))),
    }


def coverage_summary(
    records: list[dict[str, Any]], method: str, threshold: float, nominal: float | None
) -> dict[str, Any]:
    signals = [np.asarray(row[method + "_mm"], dtype=np.float64) for row in records]
    errors = [np.asarray(row["known_error_mm"], dtype=np.float64) for row in records]
    radii = [calibrated_radius(signal, threshold) for signal in signals]
    coverage = [
        float(np.mean(error <= radius)) for error, radius in zip(errors, radii, strict=True)
    ]
    mean = float(np.mean(coverage))
    return {
        "threshold": threshold,
        "nominal_coverage": nominal,
        "per_anatomy_coverage": {
            row["patient_id"]: value for row, value in zip(records, coverage, strict=True)
        },
        "equal_anatomy_mean_coverage": mean,
        "coverage_gap": None if nominal is None else mean - nominal,
        "radius_efficiency": radius_efficiency(signals, threshold),
        "radius_diagnostics": vector_diagnostics(np.concatenate(radii)),
    }


def aggregate_records(
    records: dict[str, dict[str, Any]],
    cohort: dict[str, str],
    freeze: dict[str, dict[str, str]],
    seal: dict[str, Any],
    *,
    source_git_sha: str,
    request_blob_sha: str,
    threshold_seal_blob_sha: str,
) -> dict[str, Any]:
    if set(records) != set(cohort) or len(records) != 30:
        raise RuntimeError("require exactly the 30 evaluation shards; no partial aggregation")
    for patient, record in records.items():
        required = {
            "patient_id": patient,
            "source_key": cohort[patient],
            "phase": "B",
            "evaluation_accessed": True,
            "source_git_sha": source_git_sha,
            "request_blob_sha": request_blob_sha,
            "threshold_seal_blob_sha": threshold_seal_blob_sha,
            "runtime_versions": RUNTIME_VERSIONS,
            **freeze[patient],
        }
        for key, value in required.items():
            if record.get(key) != value:
                raise RuntimeError(f"evaluation shard identity mismatch: {patient}/{key}")
        if not isinstance(record.get("primary_complete"), bool) or not isinstance(
            record.get("ice_complete"), bool
        ):
            raise RuntimeError("missing method validity flags")
        if not record["primary_complete"]:
            if not record.get("failure") or record["ice_complete"]:
                raise RuntimeError("invalid primary failure record")
            continue
        if record.get("forward_member_reasons") != ["ok"] * 9:
            raise RuntimeError("complete primary method requires all nine members")
        errors = np.asarray(record["known_error_mm"], dtype=np.float64)
        if (
            errors.shape != (EXPECTED_POINTS,)
            or not np.isfinite(errors).all()
            or np.any(errors < 0)
        ):
            raise RuntimeError("invalid evaluation known-error vector")
        if array_sha256(errors) != record["hashes"]["known_error_mm"]:
            raise RuntimeError("evaluation known-error hash mismatch")
        for method in ("sigma", "ice"):
            if method == "ice" and not record["ice_complete"]:
                if (
                    not record.get("ice_failure")
                    or record["ice_mm"] != []
                    or record["ice_scores"] != []
                ):
                    raise RuntimeError("incomplete ICE must retain failure and empty vectors")
                continue
            if method == "ice" and record.get("reverse_member_reasons") != ["ok"] * 9:
                raise RuntimeError("complete ICE requires all nine reverse members")
            signal = np.asarray(record[method + "_mm"], dtype=np.float64)
            scores = np.asarray(record[method + "_scores"], dtype=np.float64)
            if signal.shape != (EXPECTED_POINTS,) or scores.shape != signal.shape:
                raise RuntimeError("evaluation score vector shape mismatch")
            if not np.array_equal(ratio_nonconformity(errors, signal), scores):
                raise RuntimeError("evaluation ratio-score mismatch")
            for key, values in ((method + "_mm", signal), (method + "_scores", scores)):
                if array_sha256(values) != record["hashes"][key]:
                    raise RuntimeError("evaluation numeric-vector hash mismatch")
    sources: dict[str, Any] = {}
    for source in SOURCES:
        rows = [records[p] for p in sorted(cohort) if cohort[p] == source]
        methods = {}
        for method in ("sigma", "ice"):
            validity = "primary_complete" if method == "sigma" else "ice_complete"
            failures = [row["patient_id"] for row in rows if not row[validity]]
            calibration_ok = seal["thresholds"][source][method]["assessable"]
            result: dict[str, Any] = {
                "evaluation_complete": not failures,
                "failures": failures,
                "calibration_assessable": calibration_ok,
                "calibrated_assessable": calibration_ok and not failures,
            }
            if not failures:
                result["uncalibrated_reference"] = coverage_summary(rows, method, 1.0, None)
                result["signal_diagnostics"] = vector_diagnostics(
                    np.concatenate([np.asarray(row[method + "_mm"]) for row in rows])
                )
                result["score_diagnostics"] = vector_diagnostics(
                    np.concatenate([np.asarray(row[method + "_scores"]) for row in rows])
                )
            if result["calibrated_assessable"]:
                levels = {}
                for nominal in NOMINALS:
                    encoded = seal["thresholds"][source][method]["thresholds"][nominal]
                    q = float("inf") if encoded == "positive_infinity" else float(encoded)
                    levels[nominal] = coverage_summary(rows, method, q, float(nominal))
                result["levels"] = levels
            else:
                result["reason"] = (
                    "calibration unavailable or at least one predeclared evaluation anatomy "
                    "method-incomplete; no reduced-cohort claim"
                )
            methods[method] = result
        sources[source] = {"patients": [row["patient_id"] for row in rows], "methods": methods}
    balanced: dict[str, Any] = {}
    for method in ("sigma", "ice"):
        available = all(sources[s]["methods"][method]["calibrated_assessable"] for s in SOURCES)
        balanced[method] = {"assessable": available}
        if available:
            balanced[method]["levels"] = {
                nominal: {
                    "equal_source_equal_anatomy_mean_coverage": float(
                        np.mean(
                            [
                                sources[s]["methods"][method]["levels"][nominal][
                                    "equal_anatomy_mean_coverage"
                                ]
                                for s in SOURCES
                            ]
                        )
                    ),
                    "nominal_coverage": float(nominal),
                }
                for nominal in NOMINALS
            }
    return {
        "status": (
            "complete"
            if all(row["primary_complete"] for row in records.values())
            else "primary-incomplete"
        ),
        "evaluation_anatomies": 30,
        "primary_failures": [p for p in sorted(records) if not records[p]["primary_complete"]],
        "ice_failures": [p for p in sorted(records) if not records[p]["ice_complete"]],
        "sources": sources,
        "balanced_across_sources": balanced,
        "thresholds_refitted": False,
        "pooled_independent_point_inference_used": False,
        "near_zero_diagnostic_rule": (
            "0 < value <= float64 epsilon; descriptive only, " "no flooring or abstention"
        ),
    }
