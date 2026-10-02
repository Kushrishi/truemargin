#!/usr/bin/env python3
"""Run the prospectively frozen M6 synthetic-deformation geometry preflight.

This script may reacquire the 60 preidentified NCI-ISBI training T2 series and official
labels, construct one frozen known deformation per anatomy, warp the prostate ROI, and
freeze 50 ROI locations. It must not run registration, compute TrueMargin sigma or ICE,
fit conformal calibration, or evaluate coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = REPO_ROOT / "research" / "M6_DEFORMATION_PREFLIGHT_REQUEST.json"
SPLIT_PATH = REPO_ROOT / "research" / "M6_SPLIT.json"
PROTOCOL_PATH = REPO_ROOT / "docs" / "m6_calibration_protocol.md"

TRAINING_MANIFEST_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
    "ISBI-Prostate-Challenge-Training.tcia?api=v2"
)
TRAINING_LABEL_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
    "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Training.zip?api=v2"
)
NBIA_IMAGE_URL = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage"
PATIENT_RE = re.compile(r"(Prostate(?:3T|Dx)-01-\d{4})")
UID_RE = re.compile(r"\d+(?:\.\d+)+")

EXPECTED_CASES = 60
EXPECTED_SOURCE_COUNTS = {"prostate_3t": 30, "prostate_diagnosis": 30}
CROP_PAD_VOXELS = 15
DEFORM_MESH_SIZE = 4
KNOWN_COEFFICIENT_STD = 4.0
TOPOLOGY_SCALES = (1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50)
N_LANDMARKS = 50
LANDMARK_MARGIN = 8
NDIM = 3
DOWNLOAD_WORKERS = 4
SEED_PREFIX = "truemargin-m6-v1"


class TransportUnavailable(RuntimeError):
    """Raised when bounded network acquisition fails."""


def _download(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as first:
        with tempfile.NamedTemporaryFile(prefix="truemargin-m6-deform-", delete=False) as handle:
            output = Path(handle.name)
        try:
            proc = subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--connect-timeout",
                    "15",
                    "--max-time",
                    str(max(timeout, 120)),
                    "--retry",
                    "2",
                    "--retry-delay",
                    "2",
                    "--retry-all-errors",
                    "--output",
                    str(output),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=max(timeout, 120) + 30,
                check=False,
            )
            if proc.returncode != 0:
                raise TransportUnavailable(
                    f"urllib={type(first).__name__}:{first}; "
                    f"curl={proc.returncode}:{proc.stderr.strip()}"
                )
            return output.read_bytes()
        finally:
            output.unlink(missing_ok=True)


def parse_manifest_series_uids(payload: bytes) -> list[str]:
    text = payload.decode("utf-8-sig")
    lines = [line.strip() for line in text.splitlines()]
    marker = "ListOfSeriesToDownload="
    if marker not in lines:
        raise RuntimeError("Training manifest missing ListOfSeriesToDownload marker")
    uids = [line for line in lines[lines.index(marker) + 1 :] if line]
    if len(uids) != EXPECTED_CASES:
        raise RuntimeError(f"Expected {EXPECTED_CASES} training series; found {len(uids)}")
    if len(set(uids)) != EXPECTED_CASES or any(UID_RE.fullmatch(uid) is None for uid in uids):
        raise RuntimeError("Training manifest contains invalid or duplicate SeriesInstanceUIDs")
    return uids


def label_members(payload: bytes) -> dict[str, bytes]:
    labels: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".nrrd"):
                continue
            match = PATIENT_RE.search(Path(info.filename).name)
            if match is None:
                continue
            patient_id = match.group(1)
            if patient_id in labels:
                raise RuntimeError(f"Duplicate training label for {patient_id}")
            labels[patient_id] = archive.read(info)
    if len(labels) != EXPECTED_CASES:
        raise RuntimeError(f"Expected {EXPECTED_CASES} training labels; found {len(labels)}")
    return labels


def source_key(patient_id: str) -> str:
    if patient_id.startswith("Prostate3T-"):
        return "prostate_3t"
    if patient_id.startswith("ProstateDx-"):
        return "prostate_diagnosis"
    raise ValueError(f"Unexpected challenge PatientID: {patient_id}")


def load_split() -> tuple[dict[str, str], set[str]]:
    record = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    roles: dict[str, str] = {}
    for source, source_roles in record["roles"].items():
        for role in ("calibration", "evaluation"):
            for patient_id in source_roles[role]:
                if patient_id in roles:
                    raise RuntimeError(f"Duplicate split PatientID: {patient_id}")
                if source_key(patient_id) != source:
                    raise RuntimeError(f"Split source mismatch for {patient_id}")
                roles[patient_id] = role
    if len(roles) != EXPECTED_CASES:
        raise RuntimeError(f"Expected 60 frozen split roles; found {len(roles)}")
    return roles, set(roles)


def deterministic_seed(patient_id: str, stream: str) -> int:
    if stream not in {"deformation", "noise", "points"}:
        raise ValueError(f"Unknown M6 random stream: {stream}")
    digest = hashlib.sha256(f"{SEED_PREFIX}|{stream}|{patient_id}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _flatten_dicom_zip(payload: bytes, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if not members:
            raise RuntimeError("TCIA getImage returned an empty archive")
        for index, info in enumerate(members):
            (target / f"{index:04d}.dcm").write_bytes(archive.read(info))


def _read_series(payload: bytes, expected_uid: str, target: Path) -> tuple[str, sitk.Image]:
    _flatten_dicom_zip(payload, target)
    files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(target), expected_uid)
    if not files:
        ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(target)) or ()
        if len(ids) != 1:
            raise RuntimeError(
                f"Expected one readable DICOM series for {expected_uid}; observed {list(ids)}"
            )
        files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(target), ids[0])
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(files)
    image = reader.Execute()

    header = sitk.ImageFileReader()
    header.SetFileName(files[0])
    header.ReadImageInformation()
    patient_id = (
        header.GetMetaData("0010|0020").strip() if header.HasMetaDataKey("0010|0020") else ""
    )
    observed_uid = (
        header.GetMetaData("0020|000e").strip() if header.HasMetaDataKey("0020|000e") else ""
    )
    if observed_uid and observed_uid != expected_uid:
        raise RuntimeError(f"Series UID mismatch: expected {expected_uid}, observed {observed_uid}")
    if PATIENT_RE.fullmatch(patient_id) is None:
        raise RuntimeError(f"Unexpected or missing training PatientID: {patient_id!r}")
    return patient_id, image


def _read_label(payload: bytes, target: Path) -> sitk.Image:
    target.write_bytes(payload)
    return sitk.ReadImage(str(target))


def download_series(uid: str) -> bytes:
    query = urllib.parse.urlencode({"SeriesInstanceUID": uid, "NewFileNames": "Yes"})
    return _download(f"{NBIA_IMAGE_URL}?{query}", timeout=180)


def prepare_anatomy(image: sitk.Image, label: sitk.Image) -> tuple[np.ndarray, np.ndarray, tuple[float, ...]]:
    if image.GetDimension() != 3 or label.GetDimension() != 3:
        raise ValueError("M6 deformation preflight requires 3-D image and label")
    resampled = sitk.Resample(
        label,
        image,
        sitk.Transform(),
        sitk.sitkNearestNeighbor,
        0,
        label.GetPixelID(),
    )
    mask = np.isin(sitk.GetArrayFromImage(resampled), (1, 2))
    if not np.any(mask):
        raise ValueError("Resampled prostate ROI is empty")
    t2 = sitk.GetArrayFromImage(image).astype(np.float32)
    voxels = np.argwhere(mask)
    lo = np.maximum(voxels.min(axis=0) - CROP_PAD_VOXELS, 0)
    hi = np.minimum(voxels.max(axis=0) + CROP_PAD_VOXELS + 1, np.asarray(mask.shape))
    slices = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi, strict=True))
    crop = t2[slices]
    mask_crop = mask[slices].astype(np.uint8)
    if crop.shape != mask_crop.shape or crop.ndim != NDIM:
        raise ValueError("Prepared image/ROI crop geometry mismatch")
    return crop, mask_crop, tuple(float(value) for value in image.GetSpacing())


def make_source_image(crop: np.ndarray, spacing: tuple[float, ...]) -> sitk.Image:
    image = sitk.GetImageFromArray(crop.astype(np.float32))
    image.SetSpacing(spacing)
    image.SetOrigin(tuple(0.0 for _ in spacing))
    image.SetDirection(tuple(float(i == j) for i in range(NDIM) for j in range(NDIM)))
    return image


def make_fixed_roi_mask(
    mask_crop: np.ndarray, source_img: sitk.Image, transform: sitk.Transform
) -> np.ndarray:
    moving_mask = sitk.GetImageFromArray((np.asarray(mask_crop) > 0).astype(np.uint8))
    moving_mask.CopyInformation(source_img)
    fixed_mask = sitk.Resample(
        moving_mask,
        source_img,
        transform,
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt8,
    )
    return sitk.GetArrayFromImage(fixed_mask) > 0


def make_known_transform(source_img: sitk.Image, seed: int) -> sitk.Transform:
    transform = sitk.BSplineTransformInitializer(source_img, [DEFORM_MESH_SIZE] * NDIM)
    rng = np.random.default_rng(seed)
    params = rng.normal(0.0, KNOWN_COEFFICIENT_STD, len(transform.GetParameters()))
    transform.SetParameters(tuple(float(value) for value in params))
    return transform


def _known_displacement_field(source_img: sitk.Image, transform: sitk.Transform) -> sitk.Image:
    displacement_filter = sitk.TransformToDisplacementFieldFilter()
    displacement_filter.SetReferenceImage(source_img)
    return displacement_filter.Execute(transform)


def _transform_jacobian_min(source_img: sitk.Image, transform: sitk.Transform) -> float:
    displacement_image = _known_displacement_field(source_img, transform)
    displacement = sitk.GetArrayFromImage(displacement_image)
    if not np.isfinite(displacement).all():
        return float("nan")
    jacobian_image = sitk.DisplacementFieldJacobianDeterminant(displacement_image, True)
    jacobian = sitk.GetArrayFromImage(jacobian_image)
    if not np.isfinite(jacobian).all():
        return float("nan")
    return float(np.min(jacobian))


def make_topology_safe_known_transform(
    source_img: sitk.Image, seed: int
) -> tuple[sitk.Transform, dict[str, float | bool]]:
    raw_transform = make_known_transform(source_img, seed)
    raw_params = np.asarray(raw_transform.GetParameters(), dtype=np.float64)
    if not np.isfinite(raw_params).all():
        raise ValueError("known B-spline parameters are non-finite")
    raw_jacobian_min = _transform_jacobian_min(source_img, raw_transform)

    for scale in TOPOLOGY_SCALES:
        transform = sitk.BSplineTransformInitializer(source_img, [DEFORM_MESH_SIZE] * NDIM)
        transform.SetParameters(tuple(float(value) for value in raw_params * scale))
        jacobian_min = _transform_jacobian_min(source_img, transform)
        if np.isfinite(jacobian_min) and jacobian_min > 0.0:
            return transform, {
                "raw_jacobian_min": float(raw_jacobian_min),
                "topology_scale": float(scale),
                "jacobian_min": float(jacobian_min),
                "topology_attenuated": bool(scale < 1.0),
            }
    raise ValueError(
        "known deformation remains invalid after topology backtracking: "
        f"raw minimum Jacobian={raw_jacobian_min:.6g}"
    )


def sample_landmarks(fixed_roi_mask: np.ndarray, seed: int) -> tuple[np.ndarray, int]:
    if fixed_roi_mask.ndim != NDIM:
        raise ValueError("fixed ROI mask must be 3-D")
    candidates = np.argwhere(np.asarray(fixed_roi_mask) > 0)
    shape = np.asarray(fixed_roi_mask.shape, dtype=np.int64)
    eligible = candidates[
        np.all(candidates >= LANDMARK_MARGIN, axis=1)
        & np.all(candidates < (shape - LANDMARK_MARGIN), axis=1)
    ]
    if len(eligible) < N_LANDMARKS:
        raise ValueError(
            f"fixed ROI has only {len(eligible)} eligible voxels after "
            f"{LANDMARK_MARGIN}-voxel margin; need {N_LANDMARKS}"
        )
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(eligible), size=N_LANDMARKS, replace=False)
    return eligible[selected].astype(np.int64), int(len(eligible))


def _physical_point_inside(image: sitk.Image, point: np.ndarray) -> bool:
    continuous = image.TransformPhysicalPointToContinuousIndex(
        tuple(float(value) for value in point)
    )
    return all(
        -1e-9 <= value <= (size - 1) + 1e-9
        for value, size in zip(continuous, image.GetSize(), strict=True)
    )


def landmark_geometry(
    source_img: sitk.Image, transform: sitk.Transform, idx_zyx: np.ndarray
) -> dict[str, Any]:
    physical_points: list[list[float]] = []
    transformed_points: list[list[float]] = []
    displacements: list[list[float]] = []
    for z, y, x in idx_zyx:
        point = np.asarray(
            source_img.TransformIndexToPhysicalPoint((int(x), int(y), int(z))), dtype=np.float64
        )
        transformed = np.asarray(transform.TransformPoint(tuple(point)), dtype=np.float64)
        if not _physical_point_inside(source_img, transformed):
            raise ValueError("a transformed landmark leaves the moving-source domain")
        physical_points.append(point.tolist())
        transformed_points.append(transformed.tolist())
        displacements.append((transformed - point).tolist())

    displacement = np.asarray(displacements, dtype=np.float64)
    if not np.isfinite(displacement).all():
        raise ValueError("true landmark displacement contains non-finite values")
    magnitude = np.linalg.norm(displacement, axis=1)
    return {
        "landmark_indices_zyx": idx_zyx.tolist(),
        "landmark_physical_xyz_mm": physical_points,
        "transformed_physical_xyz_mm": transformed_points,
        "true_displacement_xyz_mm": displacements,
        "true_displacement_min_mm": float(np.min(magnitude)),
        "true_displacement_median_mm": float(np.median(magnitude)),
        "true_displacement_p90_mm": float(np.percentile(magnitude, 90)),
        "true_displacement_max_mm": float(np.max(magnitude)),
    }


def preflight_geometry(
    patient_id: str,
    role: str,
    series_uid: str,
    image: sitk.Image,
    label: sitk.Image,
) -> dict[str, Any]:
    crop, mask_crop, spacing = prepare_anatomy(image, label)
    source_img = make_source_image(crop, spacing)
    deformation_seed = deterministic_seed(patient_id, "deformation")
    noise_seed = deterministic_seed(patient_id, "noise")
    points_seed = deterministic_seed(patient_id, "points")
    transform, topology = make_topology_safe_known_transform(source_img, deformation_seed)

    displacement_image = _known_displacement_field(source_img, transform)
    displacement = sitk.GetArrayFromImage(displacement_image)
    if not np.isfinite(displacement).all():
        raise ValueError("known displacement field is non-finite")
    field_magnitude = np.linalg.norm(displacement, axis=-1)

    fixed_roi = make_fixed_roi_mask(mask_crop, source_img, transform)
    idx_zyx, eligible_count = sample_landmarks(fixed_roi, points_seed)
    if len(np.unique(idx_zyx, axis=0)) != N_LANDMARKS:
        raise ValueError("point sampler did not produce 50 unique points")
    if not np.all(fixed_roi[tuple(idx_zyx.T)]):
        raise ValueError("sampled point is outside the fixed-domain prostate ROI")

    points = landmark_geometry(source_img, transform, idx_zyx)
    return {
        "patient_id": patient_id,
        "source_key": source_key(patient_id),
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
        "sampled_roi_points": N_LANDMARKS,
        "field_true_displacement_min_mm": float(np.min(field_magnitude)),
        "field_true_displacement_median_mm": float(np.median(field_magnitude)),
        "field_true_displacement_p90_mm": float(np.percentile(field_magnitude, 90)),
        "field_true_displacement_max_mm": float(np.max(field_magnitude)),
        **points,
    }


def audit_case(
    uid: str,
    labels: dict[str, bytes],
    roles: dict[str, str],
    root: Path,
) -> dict[str, Any]:
    case_dir = root / hashlib.sha256(uid.encode()).hexdigest()[:16]
    case_dir.mkdir(parents=True, exist_ok=True)
    patient_id = ""
    try:
        dicom_payload = download_series(uid)
        patient_id, image = _read_series(dicom_payload, uid, case_dir / "dicom")
        if patient_id not in roles:
            raise RuntimeError(f"Training PatientID is not in frozen M6 split: {patient_id}")
        if patient_id not in labels:
            raise RuntimeError(f"No official training label found for {patient_id}")
        label = _read_label(labels[patient_id], case_dir / "label.nrrd")
        record = preflight_geometry(patient_id, roles[patient_id], uid, image, label)
        record["dicom_zip_sha256"] = hashlib.sha256(dicom_payload).hexdigest()
        record["label_sha256"] = hashlib.sha256(labels[patient_id]).hexdigest()
        return record
    except Exception as exc:
        return {
            "patient_id": patient_id or None,
            "series_uid": uid,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def build_audit() -> dict[str, Any]:
    roles, expected_patients = load_split()
    manifest = _download(TRAINING_MANIFEST_URL)
    labels_zip = _download(TRAINING_LABEL_URL)
    uids = parse_manifest_series_uids(manifest)
    labels = label_members(labels_zip)
    if set(labels) != expected_patients:
        raise RuntimeError("Official training label PatientIDs do not match frozen M6 split")

    with tempfile.TemporaryDirectory(prefix="truemargin-m6-deformation-") as temp:
        root = Path(temp)
        records: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
            futures = {pool.submit(audit_case, uid, labels, roles, root): uid for uid in uids}
            for future in as_completed(futures):
                records.append(future.result())

    records.sort(key=lambda item: (str(item.get("patient_id")), str(item["series_uid"])))
    complete = [record for record in records if record["status"] == "complete"]
    failures = [record for record in records if record["status"] != "complete"]
    complete_patients = {str(record["patient_id"]) for record in complete}
    if not failures and complete_patients != expected_patients:
        raise RuntimeError("Completed preflight PatientIDs do not match frozen M6 split")

    source_counts = {
        source: sum(record.get("source_key") == source for record in complete)
        for source in EXPECTED_SOURCE_COUNTS
    }
    role_counts = {
        role: sum(record.get("role") == role for record in complete)
        for role in ("calibration", "evaluation")
    }
    status = "complete" if len(complete) == EXPECTED_CASES and not failures else "incomplete"

    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "deformation-only-preflight",
        "status": status,
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "forward_registration_performed": False,
            "reverse_registration_performed": False,
            "sigma_computed": False,
            "ice_computed": False,
            "calibration_fit_performed": False,
            "evaluation_performed": False,
            "synthetic_deformation_performed": True,
            "roi_warp_and_point_sampling_performed": True,
        },
        "frozen_design": {
            "anatomies": EXPECTED_CASES,
            "deformation_replicates_per_anatomy": 1,
            "deformation_mesh_size": DEFORM_MESH_SIZE,
            "raw_coefficient_std": KNOWN_COEFFICIENT_STD,
            "topology_scales": list(TOPOLOGY_SCALES),
            "crop_padding_voxels": CROP_PAD_VOXELS,
            "roi_boundary_margin_voxels": LANDMARK_MARGIN,
            "points_per_anatomy": N_LANDMARKS,
            "seed_prefix": SEED_PREFIX,
        },
        "manifest": {
            "url": TRAINING_MANIFEST_URL,
            "sha256": hashlib.sha256(manifest).hexdigest(),
        },
        "labels": {
            "url": TRAINING_LABEL_URL,
            "sha256": hashlib.sha256(labels_zip).hexdigest(),
        },
        "source_counts": source_counts,
        "role_counts": role_counts,
        "complete_count": len(complete),
        "failure_count": len(failures),
        "topology_attenuated_count": sum(
            bool(record.get("topology_attenuated")) for record in complete
        ),
        "minimum_eligible_fixed_roi_voxels": (
            min(int(record["eligible_fixed_roi_voxels"]) for record in complete)
            if complete
            else None
        ),
        "failures": failures,
        "cases": records,
    }


def failure_record(exc: BaseException) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "deformation-only-preflight",
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
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "m6_deformation_preflight.json",
    )
    args = parser.parse_args()
    try:
        result = build_audit()
    except Exception as exc:
        result = failure_record(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_DEFORMATION_PREFLIGHT_STATUS={result['status'].upper()}")
    print(f"M6_DEFORMATION_COMPLETE_COUNT={result.get('complete_count', 0)}")
    print(f"M6_DEFORMATION_FAILURE_COUNT={result.get('failure_count', 0)}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
