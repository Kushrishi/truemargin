#!/usr/bin/env python3
"""Run source-pinned TrueMargin M6 Phase B held-out evaluation only.

The runner executes only the 30 evaluation anatomies after a separate committed
request. It consumes sealed thresholds and never fits calibration.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import runpy
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

from truemargin import comparators
from truemargin import hyperparameter as hyper
from truemargin import io_utils as ioutil
from truemargin.hierarchical_conformal import ratio_nonconformity
from truemargin.m6_input_identity import assert_frozen_digest
from truemargin.m6_phase_a import (
    EXPECTED_POINTS,
    array_sha256,
    geometry_sha256,
    git_blob_sha,
)
from truemargin.m6_phase_b import (
    aggregate_records,
    evaluation_cohort,
    load_evaluation_freeze,
    load_seal,
    verify_request,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = REPO_ROOT / "research" / "M6_PHASE_B_REQUEST.json"
SPLIT_PATH = REPO_ROOT / "research" / "M6_SPLIT.json"
GEOMETRY_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_B_INPUT_FREEZE.json"
INPUT_FREEZE_PATH = REPO_ROOT / "research" / "M6_PHASE_B_INPUT_FREEZE.json"
PROTOCOL_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol.md"
AMENDMENT_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol_amendment_1.md"
BASE_PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight.py"
AMENDED_PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m6_deformation_preflight_amendment_1.py"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "m6_phase_b"
INTENSITY_NOISE_STD = 0.03

BASE = runpy.run_path(str(BASE_PREFLIGHT_PATH), run_name="m6_phase_b_base_preflight")
AMENDED = runpy.run_path(str(AMENDED_PREFLIGHT_PATH), run_name="m6_phase_b_amended_preflight")


SEAL_PATH = REPO_ROOT / "research/M6_PHASE_A_THRESHOLD_SEAL.json"
AGGREGATE_PATH = REPO_ROOT / "results/m6_phase_a/outputs/m6_phase_a/m6_phase_a_calibration.json"
PINNED_PATHS = {
    "protocol": PROTOCOL_PATH,
    "amendment": AMENDMENT_PATH,
    "split": SPLIT_PATH,
    "input_freeze": INPUT_FREEZE_PATH,
    "threshold_seal": SEAL_PATH,
    "calibration_aggregate": AGGREGATE_PATH,
}
RESULT_DEFINING_PATHS = (
    "scripts/m6_phase_b_evaluation.py",
    "scripts/recover_m6_phase_b_inputs.py",
    "scripts/stage_m6_phase_b_labels.py",
    ".github/workflows/m6-phase-b-evaluation.yml",
    "src/truemargin/m6_phase_b.py",
    "research/M6_PHASE_B_INPUT_FREEZE.json",
    "research/M6_PHASE_A_THRESHOLD_SEAL.json",
    "results/m6_phase_a/outputs/m6_phase_a/m6_phase_a_calibration.json",
    "docs/m6_calibration_protocol.md",
    "docs/m6_calibration_protocol_amendment_1.md",
    "docs/m6_phase_b_execution.md",
    "research/M6_SPLIT.json",
    "scripts/m6_deformation_preflight.py",
    "scripts/m6_deformation_preflight_amendment_1.py",
    "src/truemargin/m6_phase_a.py",
    "src/truemargin/hierarchical_conformal.py",
    "src/truemargin/hyperparameter.py",
    "src/truemargin/comparators.py",
    "src/truemargin/known_gt_comparison.py",
    "src/truemargin/registration.py",
    "src/truemargin/ensemble.py",
    "src/truemargin/io_utils.py",
    "src/truemargin/m6_input_identity.py",
    "src/truemargin/m6_zip_recovery.py",
    "tests/test_m6_phase_b.py",
    "tests/test_hierarchical_conformal.py",
    "tests/test_hyperparameter_known_gt.py",
    "tests/test_comparators.py",
)


def verify_execution_authorization() -> dict[str, Any]:
    return verify_request(
        repo_root=REPO_ROOT,
        request_path=REQUEST_PATH,
        pinned_paths=PINNED_PATHS,
        result_defining_paths=RESULT_DEFINING_PATHS,
    )


def load_geometry_freeze(path: Path) -> dict[str, dict[str, str]]:
    return load_evaluation_freeze(path, evaluation_cohort(SPLIT_PATH))


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
    frozen = load_geometry_freeze(INPUT_FREEZE_PATH)[patient_id]
    if frozen["series_uid"] != series_uid:
        raise RuntimeError("input registry SeriesInstanceUID mismatch")
    cache_root = os.environ.get("M6_EVALUATION_DICOM_CACHE")
    label_archive = os.environ.get("M6_EVALUATION_LABEL_ARCHIVE")
    if not cache_root or not label_archive:
        raise RuntimeError("Phase B requires verified workflow-local image and label caches")
    payload = Path(label_archive).read_bytes()
    if (
        hashlib.sha256(payload).hexdigest()
        != "c3436559b474c60e78633ea98601241f39cb27e30fb9d48b1d29f2821bfbf047"
    ):
        raise RuntimeError("official training label archive digest mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [
            info
            for info in archive.infolist()
            if not info.is_dir() and Path(info.filename).name == f"{patient_id}.nrrd"
        ]
        if len(candidates) != 1:
            raise RuntimeError("expected exactly one authorized evaluation label")
        label_payload = archive.read(candidates[0])
    label_sha = assert_frozen_digest(
        label_payload, frozen["label_sha256"], patient_id=patient_id, input_kind="label"
    )
    dicom_payload = (Path(cache_root) / f"{patient_id}.zip").read_bytes()
    dicom_sha = assert_frozen_digest(
        dicom_payload, frozen["dicom_zip_sha256"], patient_id=patient_id, input_kind="dicom_zip"
    )
    observed_patient, image = BASE["_read_series"](dicom_payload, series_uid, root / "dicom")
    if observed_patient != patient_id:
        raise RuntimeError(
            f"frozen series identity mismatch: expected {patient_id}, observed {observed_patient}"
        )
    label = BASE["_read_label"](label_payload, root / "label.nrrd")
    return (
        image,
        label,
        dicom_sha,
        label_sha,
    )


def build_synthetic_case(
    patient_id: str,
    series_uid: str,
    image: sitk.Image,
    label: sitk.Image,
) -> tuple[dict[str, Any], str]:
    record = AMENDED["preflight_geometry"](patient_id, "evaluation", series_uid, image, label)
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
        "phase": "B",
        "patient_id": patient_id,
        "source_key": source_key,
        "series_uid": series_uid,
        "geometry_sha256": geometry_hash,
        "status": "incomplete",
        "primary_complete": False,
        "ice_complete": False,
        "failure": message,
        "evaluation_accessed": True,
    }


def run_patient(patient_id: str, output_root: Path) -> Path:
    request = verify_execution_authorization()
    evaluation = evaluation_cohort(SPLIT_PATH)
    if patient_id not in evaluation:
        raise RuntimeError(f"patient is not authorized for M6 Phase B: {patient_id}")
    source = evaluation[patient_id]
    frozen = load_geometry_freeze(GEOMETRY_FREEZE_PATH)[patient_id]
    series_uid = frozen["series_uid"]

    shard_dir = output_root / "shards"
    checkpoint_dir = output_root / "checkpoints"
    shard_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_path = shard_dir / f"{patient_id}.json"

    with tempfile.TemporaryDirectory(prefix=f"truemargin-m6-phase-b-{patient_id}-") as tmp:
        image, label, dicom_sha, label_sha = load_exact_input(patient_id, series_uid, Path(tmp))
        synthetic, geometry_hash = build_synthetic_case(patient_id, series_uid, image, label)

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
        payload.update(
            {
                **frozen,
                "forward_member_reasons": list(forward.member_reasons),
                "reverse_member_reasons": [],
                "source_git_sha": request["source_git_sha"],
                "request_blob_sha": git_blob_sha(REQUEST_PATH),
                "threshold_seal_blob_sha": git_blob_sha(SEAL_PATH),
            }
        )
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return output_path

    u_est = ioutil.sample_field_at_points(forward.u_mean, idx_zyx)
    sigma_mm = np.asarray(ioutil.sample_field_at_points(forward.sigma, idx_zyx), dtype=np.float64)
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
        "phase": "B",
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
        "threshold_seal_blob_sha": git_blob_sha(SEAL_PATH),
        "evaluation_accessed": True,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def aggregate_shards(shard_root: Path, output_path: Path) -> int:
    request = verify_execution_authorization()
    cohort = evaluation_cohort(SPLIT_PATH)
    freeze = load_evaluation_freeze(INPUT_FREEZE_PATH, cohort)
    seal = load_seal(SEAL_PATH, AGGREGATE_PATH)
    records = {}
    for path in sorted(shard_root.rglob("*.json")):
        record = json.loads(path.read_text())
        patient = record.get("patient_id")
        if patient is None:
            raise RuntimeError(f"unexpected non-anatomy JSON in shard input: {path}")
        if patient not in cohort or patient in records:
            raise RuntimeError("unauthorized or duplicate evaluation shard")
        records[patient] = record
    result = aggregate_records(
        records,
        cohort,
        freeze,
        seal,
        source_git_sha=request["source_git_sha"],
        request_blob_sha=git_blob_sha(REQUEST_PATH),
        threshold_seal_blob_sha=git_blob_sha(SEAL_PATH),
    )
    result.update(
        {
            "schema_version": 1,
            "milestone": "M6",
            "phase": "B",
            "source_git_sha": request["source_git_sha"],
            "source_ci_run_id": request["source_ci_run_id"],
            "request_blob_sha": git_blob_sha(REQUEST_PATH),
            "threshold_seal_blob_sha": git_blob_sha(SEAL_PATH),
            "calibration_aggregate_sha256": seal["aggregate_sha256"],
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "complete" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--patient")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--aggregate-root", type=Path)
    parser.add_argument(
        "--aggregate-output", type=Path, default=DEFAULT_OUTPUT_ROOT / "m6_phase_b_evaluation.json"
    )
    args = parser.parse_args()
    verify_execution_authorization()
    if args.verify_only:
        print("M6_PHASE_B_AUTHORIZATION=VERIFIED")
        return 0
    if bool(args.patient) == bool(args.aggregate_root):
        parser.error("choose exactly one patient or aggregate root")
    if args.aggregate_root:
        return aggregate_shards(args.aggregate_root, args.aggregate_output)
    path = run_patient(args.patient, args.output_root)
    print(f"M6_PHASE_B_SHARD_PATH={path}")
    return 0 if json.loads(path.read_text())["primary_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
