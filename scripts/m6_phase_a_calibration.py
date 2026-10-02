#!/usr/bin/env python3
"""Run source-pinned TrueMargin M6 Phase A calibration only.

The runner may execute the frozen estimator on the 30 calibration anatomies and fit
predeclared source-specific HCP thresholds. It cannot authorize or run evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

from truemargin import comparators
from truemargin import hyperparameter as hyper
from truemargin import io_utils as ioutil
from truemargin.hierarchical_conformal import ratio_nonconformity
from truemargin.m6_phase_a import (
    EXPECTED_CALIBRATION_ANATOMIES,
    EXPECTED_POINTS,
    aggregate_records,
    array_sha256,
    geometry_sha256,
    git_blob_sha,
    load_geometry_freeze,
    load_split,
    verify_request,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = REPO_ROOT / "research" / "M6_PHASE_A_REQUEST.json"
SPLIT_PATH = REPO_ROOT / "research" / "M6_SPLIT.json"
GEOMETRY_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_A_GEOMETRY_FREEZE.json"
PROTOCOL_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol.md"
AMENDMENT_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol_amendment_1.md"
BASE_PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight.py"
AMENDED_PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight_amendment_1.py"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "m6_phase_a"
INTENSITY_NOISE_STD = 0.03

BASE = runpy.run_path(str(BASE_PREFLIGHT_PATH), run_name="m6_phase_a_base_preflight")
AMENDED = runpy.run_path(str(AMENDED_PREFLIGHT_PATH), run_name="m6_phase_a_amended_preflight")

RESULT_DEFINING_PATHS = (
    "scripts/m6_phase_a_calibration.py",
    "scripts/m6_deformation_preflight.py",
    "scripts/m6_deformation_preflight_amendment_1.py",
    ".github/workflows/m6-phase-a-calibration.yml",
    "docs/m6_calibration_protocol.md",
    "docs/m6_calibration_protocol_amendment_1.md",
    "research/M6_SPLIT.json",
    "research/M6_PHASE_A_GEOMETRY_FREEZE.json",
    "src/truemargin/m6_phase_a.py",
    "src/truemargin/hyperparameter.py",
    "src/truemargin/comparators.py",
    "src/truemargin/known_gt_comparison.py",
    "src/truemargin/registration.py",
    "src/truemargin/ensemble.py",
    "src/truemargin/io_utils.py",
    "src/truemargin/hierarchical_conformal.py",
)
PINNED_PATHS = {
    "protocol": PROTOCOL_PATH,
    "amendment": AMENDMENT_PATH,
    "split": SPLIT_PATH,
    "geometry_freeze": GEOMETRY_FREEZE_PATH,
}


def verify_execution_authorization() -> dict[str, Any]:
    return verify_request(
        repo_root=REPO_ROOT,
        request_path=REQUEST_PATH,
        split_path=SPLIT_PATH,
        geometry_freeze_path=GEOMETRY_FREEZE_PATH,
        pinned_paths=PINNED_PATHS,
        result_defining_paths=RESULT_DEFINING_PATHS,
    )


def crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent = (
        shape_zyx[2] * spacing_xyz[0],
        shape_zyx[1] * spacing_xyz[1],
        shape_zyx[0] * spacing_xyz[2],
    )
    return float(np.sqrt(sum(float(value) ** 2 for value in extent)))


def load_exact_input(
    patient_id: str, series_uid: str, root: Path
) -> tuple[sitk.Image, sitk.Image, str, str]:
    labels_zip = BASE["_download"](BASE["TRAINING_LABEL_URL"])
    labels = BASE["label_members"](labels_zip)
    if patient_id not in labels:
        raise RuntimeError(f"official training label is missing for {patient_id}")
    dicom_payload = BASE["download_series"](series_uid)
    observed_patient, image = BASE["_read_series"](dicom_payload, series_uid, root / "dicom")
    if observed_patient != patient_id:
        raise RuntimeError(
            f"frozen series identity mismatch: expected {patient_id}, observed {observed_patient}"
        )
    label = BASE["_read_label"](labels[patient_id], root / "label.nrrd")
    return (
        image,
        label,
        hashlib.sha256(dicom_payload).hexdigest(),
        hashlib.sha256(labels[patient_id]).hexdigest(),
    )


def build_synthetic_case(
    patient_id: str,
    series_uid: str,
    image: sitk.Image,
    label: sitk.Image,
) -> tuple[dict[str, Any], str]:
    record = AMENDED["preflight_geometry"](
        patient_id, "calibration", series_uid, image, label
    )
    frozen = load_geometry_freeze(GEOMETRY_FREEZE_PATH)[patient_id]
    observed_hash = geometry_sha256(record)
    if observed_hash != frozen["geometry_sha256"]:
        raise RuntimeError(
            f"frozen geometry drift for {patient_id}: {observed_hash} "
            f"!= {frozen['geometry_sha256']}"
        )

    crop, _, spacing = BASE["prepare_anatomy"](image, label)
    source_img = BASE["make_source_image"](crop, spacing)
    transform, _ = BASE["make_topology_safe_known_transform"](
        source_img, int(record["deformation_seed"])
    )
    fixed_img = sitk.Resample(source_img, source_img, transform, sitk.sitkLinear, 0.0)
    moving = sitk.GetArrayFromImage(source_img).astype(np.float32)
    fixed = sitk.GetArrayFromImage(fixed_img).astype(np.float32)
    scale = float(np.std(moving))
    if not np.isfinite(scale) or scale <= np.finfo(np.float32).eps:
        raise RuntimeError("moving-source crop has invalid intensity standard deviation")
    moving = moving / scale
    fixed = fixed / scale
    rng = np.random.default_rng(int(record["noise_seed"]))
    fixed += rng.normal(0.0, INTENSITY_NOISE_STD, fixed.shape).astype(np.float32)

    idx_zyx = np.asarray(record["landmark_indices_zyx"], dtype=np.int64)
    u_true = np.asarray(record["true_displacement_xyz_mm"], dtype=np.float64).T
    if idx_zyx.shape != (EXPECTED_POINTS, 3) or u_true.shape != (3, EXPECTED_POINTS):
        raise RuntimeError("frozen point geometry has an unexpected shape")
    return {
        "fixed": fixed,
        "moving": moving,
        "idx_zyx": idx_zyx,
        "u_true": u_true,
        "spacing": tuple(float(value) for value in spacing),
        "crop_diagonal_mm": crop_diagonal_mm(tuple(crop.shape), spacing),
    }, observed_hash


def failure_payload(
    patient_id: str,
    source_key: str,
    series_uid: str,
    geometry_hash: str,
    message: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "milestone": "M6",
        "phase": "A",
        "patient_id": patient_id,
        "source_key": source_key,
        "series_uid": series_uid,
        "geometry_sha256": geometry_hash,
        "status": "incomplete",
        "primary_complete": False,
        "ice_complete": False,
        "failure": message,
        "evaluation_accessed": False,
    }


def run_patient(patient_id: str, output_root: Path) -> Path:
    request = verify_execution_authorization()
    calibration, evaluation = load_split(SPLIT_PATH)
    if patient_id in evaluation or patient_id not in calibration:
        raise RuntimeError(f"patient is not authorized for M6 Phase A: {patient_id}")
    source = calibration[patient_id]
    frozen = load_geometry_freeze(GEOMETRY_FREEZE_PATH)[patient_id]
    series_uid = frozen["series_uid"]

    shard_dir = output_root / "shards"
    checkpoint_dir = output_root / "checkpoints"
    shard_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_path = shard_dir / f"{patient_id}.json"

    with tempfile.TemporaryDirectory(prefix=f"truemargin-m6-phase-a-{patient_id}-") as tmp:
        image, label, dicom_sha, label_sha = load_exact_input(
            patient_id, series_uid, Path(tmp)
        )
        synthetic, geometry_hash = build_synthetic_case(
            patient_id, series_uid, image, label
        )

    fixed = np.asarray(synthetic["fixed"], dtype=np.float32)
    moving = np.asarray(synthetic["moving"], dtype=np.float32)
    spacing = synthetic["spacing"]
    idx_zyx = np.asarray(synthetic["idx_zyx"], dtype=np.int64)
    u_true = np.asarray(synthetic["u_true"], dtype=np.float64)
    diagonal = float(synthetic["crop_diagonal_mm"])

    forward = hyper.run_hyperparameter_ensemble(
        fixed, moving, spacing=spacing, crop_diagonal_mm=diagonal
    )
    if not forward.complete or forward.u_mean is None or forward.sigma is None:
        payload = failure_payload(
            patient_id,
            source,
            series_uid,
            geometry_hash,
            "forward ensemble incomplete: " + " | ".join(forward.member_reasons),
        )
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return output_path

    u_est = ioutil.sample_field_at_points(forward.u_mean, idx_zyx)
    sigma_mm = np.asarray(
        ioutil.sample_field_at_points(forward.sigma, idx_zyx), dtype=np.float64
    )
    known_error_mm = np.linalg.norm(u_est - u_true, axis=0)
    if sigma_mm.shape != (EXPECTED_POINTS,) or known_error_mm.shape != (EXPECTED_POINTS,):
        raise RuntimeError("forward pointwise result shape mismatch")
    if not np.isfinite(sigma_mm).all() or np.any(sigma_mm < 0.0):
        raise RuntimeError("primary sigma contains invalid values")
    if not np.isfinite(known_error_mm).all() or np.any(known_error_mm < 0.0):
        raise RuntimeError("known registration error contains invalid values")
    sigma_scores = ratio_nonconformity(known_error_mm, sigma_mm)

    reverse = hyper.run_hyperparameter_ensemble(
        moving, fixed, spacing=spacing, crop_diagonal_mm=diagonal
    )
    ice_complete = bool(reverse.complete and reverse.u_mean is not None)
    ice_mm = np.asarray([], dtype=np.float64)
    ice_scores = np.asarray([], dtype=np.float64)
    ice_failure = ""
    if ice_complete:
        try:
            ice_mm = comparators.inverse_consistency_scores(
                forward.u_mean, reverse.u_mean, idx_zyx, spacing
            )
            if ice_mm.shape != (EXPECTED_POINTS,) or not np.isfinite(ice_mm).all():
                raise ValueError("ICE pointwise result is incomplete or non-finite")
            if np.any(ice_mm < 0.0):
                raise ValueError("ICE contains a negative value")
            ice_scores = ratio_nonconformity(known_error_mm, ice_mm)
        except Exception as exc:
            ice_complete = False
            ice_failure = f"{type(exc).__name__}: {exc}"
            ice_mm = np.asarray([], dtype=np.float64)
            ice_scores = np.asarray([], dtype=np.float64)
    else:
        ice_failure = "reverse ensemble incomplete: " + " | ".join(reverse.member_reasons)

    np.savez_compressed(
        checkpoint_dir / f"{patient_id}.npz",
        idx_zyx=idx_zyx,
        u_true=u_true,
        known_error_mm=known_error_mm,
        sigma_mm=sigma_mm,
        sigma_scores=sigma_scores,
        ice_mm=ice_mm,
        ice_scores=ice_scores,
    )
    payload = {
        "schema_version": 1,
        "milestone": "M6",
        "phase": "A",
        "patient_id": patient_id,
        "source_key": source,
        "series_uid": series_uid,
        "geometry_sha256": geometry_hash,
        "status": "complete",
        "primary_complete": True,
        "ice_complete": ice_complete,
        "ice_failure": ice_failure,
        "forward_member_reasons": list(forward.member_reasons),
        "reverse_member_reasons": list(reverse.member_reasons),
        "dicom_zip_sha256": dicom_sha,
        "label_sha256": label_sha,
        "known_error_mm": known_error_mm.tolist(),
        "sigma_mm": sigma_mm.tolist(),
        "sigma_scores": sigma_scores.tolist(),
        "ice_mm": ice_mm.tolist(),
        "ice_scores": ice_scores.tolist(),
        "hashes": {
            "known_error_mm": array_sha256(known_error_mm),
            "sigma_mm": array_sha256(sigma_mm),
            "sigma_scores": array_sha256(sigma_scores),
            "ice_mm": array_sha256(ice_mm) if ice_complete else None,
            "ice_scores": array_sha256(ice_scores) if ice_complete else None,
        },
        "summary": {
            "known_error_median_mm": float(np.median(known_error_mm)),
            "sigma_median_mm": float(np.median(sigma_mm)),
            "sigma_zero_count": int(np.sum(sigma_mm == 0.0)),
            "sigma_infinite_score_count": int(np.sum(np.isposinf(sigma_scores))),
            "ice_median_mm": float(np.median(ice_mm)) if ice_complete else None,
            "ice_zero_count": int(np.sum(ice_mm == 0.0)) if ice_complete else None,
            "ice_infinite_score_count": (
                int(np.sum(np.isposinf(ice_scores))) if ice_complete else None
            ),
        },
        "source_git_sha": request["source_git_sha"],
        "request_blob_sha": git_blob_sha(REQUEST_PATH),
        "evaluation_accessed": False,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_path


def aggregate_shards(shard_root: Path, output_path: Path) -> int:
    request = verify_execution_authorization()
    calibration, evaluation = load_split(SPLIT_PATH)
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(shard_root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        patient = payload.get("patient_id")
        if patient in calibration:
            if patient in records:
                raise RuntimeError(f"duplicate Phase A shard for {patient}")
            records[patient] = payload
    if set(records) != set(calibration):
        missing = sorted(set(calibration) - set(records))
        raise RuntimeError(f"Phase A shard set is incomplete: missing={missing}")
    if set(records) & evaluation:
        raise RuntimeError("Phase A shard set contains an evaluation anatomy")

    status, primary_failures, source_results = aggregate_records(records, calibration)
    result = {
        "schema_version": 1,
        "milestone": "M6",
        "phase": "A",
        "status": status,
        "authorization_boundary": {
            "phase_a_calibration_authorized": True,
            "evaluation_authorized": False,
            "evaluation_accessed": False,
            "threshold_changes_after_phase_a_authorized": False,
        },
        "source_git_sha": request["source_git_sha"],
        "source_ci_run_id": request["source_ci_run_id"],
        "request_blob_sha": git_blob_sha(REQUEST_PATH),
        "calibration_anatomies": EXPECTED_CALIBRATION_ANATOMIES,
        "evaluation_anatomies_accessed": 0,
        "primary_failures": primary_failures,
        "ice_failures": [
            patient for patient, record in records.items() if not bool(record.get("ice_complete"))
        ],
        "sources": source_results,
        "shards": {
            patient: {
                "series_uid": record["series_uid"],
                "geometry_sha256": record["geometry_sha256"],
                "primary_complete": record["primary_complete"],
                "ice_complete": record["ice_complete"],
                "hashes": record.get("hashes", {}),
            }
            for patient, record in sorted(records.items())
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if status == "complete" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--patient")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--aggregate-root", type=Path)
    parser.add_argument(
        "--aggregate-output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "m6_phase_a_calibration.json",
    )
    args = parser.parse_args()

    if args.verify_only:
        if args.patient or args.aggregate_root:
            raise SystemExit("--verify-only cannot be combined with execution modes")
        request = verify_execution_authorization()
        print(f"M6_PHASE_A_SOURCE_GIT_SHA={request['source_git_sha']}")
        print("M6_PHASE_A_AUTHORIZATION=PASS")
        print("M6_EVALUATION_AUTHORIZED=False")
        return 0
    if args.patient and args.aggregate_root:
        raise SystemExit("choose either --patient or --aggregate-root")
    if args.patient:
        output = run_patient(args.patient, args.output_root)
        payload = json.loads(output.read_text(encoding="utf-8"))
        print(f"M6_PHASE_A_PATIENT={args.patient}")
        print(f"M6_PHASE_A_PATIENT_STATUS={payload['status'].upper()}")
        print(f"M6_PHASE_A_ICE_COMPLETE={payload.get('ice_complete', False)}")
        return 0 if payload["status"] == "complete" else 1
    if args.aggregate_root:
        return aggregate_shards(args.aggregate_root, args.aggregate_output)
    raise SystemExit("provide --patient, --aggregate-root, or --verify-only")


if __name__ == "__main__":
    raise SystemExit(main())
