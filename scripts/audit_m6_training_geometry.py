#!/usr/bin/env python3
"""Geometry-only eligibility audit for the 60 NCI-ISBI training anatomies used by M6.

This audit may download the prospectively identified training DICOM series and official
NRRD labels. It does not generate synthetic deformations, run registration, compute
TrueMargin sigma or ICE, assign calibration/evaluation roles, or fit calibration.
Eligibility is based only on identity, readable geometry, label semantics, and physical
ROI containment.
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

TRAINING_MANIFEST_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
    "ISBI-Prostate-Challenge-Training.tcia?api=v2"
)
TRAINING_LABEL_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
    "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Training.zip?api=v2"
)
NBIA_IMAGE_URL = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage"
EXPECTED_CASES = 60
EXPECTED_SOURCE_COUNTS = {"Prostate3T": 30, "ProstateDx": 30}
ALLOWED_LABELS = {0, 1, 2}
PATIENT_RE = re.compile(r"(Prostate(?:3T|Dx)-01-\d{4})")
UID_RE = re.compile(r"\d+(?:\.\d+)+")
BOUND_TOL = 1e-5
DOWNLOAD_WORKERS = 4


class TransportUnavailable(RuntimeError):
    """Raised when both bounded HTTP clients fail."""


def _download(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as first:
        with tempfile.NamedTemporaryFile(prefix="truemargin-m6-", delete=False) as handle:
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
    start = lines.index(marker) + 1
    uids = [line for line in lines[start:] if line]
    if len(uids) != EXPECTED_CASES:
        raise RuntimeError(f"Expected {EXPECTED_CASES} training series; found {len(uids)}")
    if len(set(uids)) != EXPECTED_CASES or any(UID_RE.fullmatch(uid) is None for uid in uids):
        raise RuntimeError("Training manifest contains invalid or duplicate SeriesInstanceUIDs")
    return uids


def label_members(payload: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".nrrd"):
                continue
            match = PATIENT_RE.search(Path(info.filename).name)
            if match is None:
                continue
            patient_id = match.group(1)
            if patient_id in out:
                raise RuntimeError(f"Duplicate training label for {patient_id}")
            out[patient_id] = archive.read(info)
    if len(out) != EXPECTED_CASES:
        raise RuntimeError(f"Expected {EXPECTED_CASES} training labels; found {len(out)}")
    return out


def source_for_patient(patient_id: str) -> str:
    if patient_id.startswith("Prostate3T-"):
        return "Prostate3T"
    if patient_id.startswith("ProstateDx-"):
        return "ProstateDx"
    raise ValueError(f"Unexpected challenge PatientID: {patient_id}")


def _flatten_dicom_zip(payload: bytes, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if not members:
            raise RuntimeError("TCIA getImage returned an empty archive")
        for index, info in enumerate(members):
            data = archive.read(info)
            (target / f"{index:04d}.dcm").write_bytes(data)


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
        header.GetMetaData("0010|0020").strip()
        if header.HasMetaDataKey("0010|0020")
        else ""
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


def image_geometry(image: sitk.Image) -> dict[str, Any]:
    return {
        "size": [int(value) for value in image.GetSize()],
        "spacing": [float(value) for value in image.GetSpacing()],
        "origin": [float(value) for value in image.GetOrigin()],
        "direction": [float(value) for value in image.GetDirection()],
    }


def foreground_containment(label: sitk.Image, image: sitk.Image) -> dict[str, Any]:
    array = sitk.GetArrayFromImage(label)
    values = sorted(int(value) for value in np.unique(array))
    foreground_zyx = np.argwhere(array > 0)
    if foreground_zyx.size == 0:
        return {
            "foreground_voxels": 0,
            "out_of_domain_foreground_voxels": 0,
            "allowed_label_values": set(values) <= ALLOWED_LABELS,
            "label_values": values,
        }

    index_xyz = foreground_zyx[:, ::-1].astype(np.float64)
    label_spacing = np.asarray(label.GetSpacing(), dtype=np.float64)
    label_origin = np.asarray(label.GetOrigin(), dtype=np.float64)
    label_direction = np.asarray(label.GetDirection(), dtype=np.float64).reshape(3, 3)
    physical = label_origin + (index_xyz * label_spacing) @ label_direction.T

    image_origin = np.asarray(image.GetOrigin(), dtype=np.float64)
    image_spacing = np.asarray(image.GetSpacing(), dtype=np.float64)
    image_direction = np.asarray(image.GetDirection(), dtype=np.float64).reshape(3, 3)
    scaled_index = (physical - image_origin) @ np.linalg.inv(image_direction).T
    continuous_index = scaled_index / image_spacing
    size = np.asarray(image.GetSize(), dtype=np.float64)
    inside = np.all(
        (continuous_index >= (-0.5 - BOUND_TOL))
        & (continuous_index <= (size - 0.5 + BOUND_TOL)),
        axis=1,
    )
    return {
        "foreground_voxels": int(foreground_zyx.shape[0]),
        "out_of_domain_foreground_voxels": int((~inside).sum()),
        "allowed_label_values": set(values) <= ALLOWED_LABELS,
        "label_values": values,
    }


def assess_geometry(patient_id: str, image: sitk.Image, label: sitk.Image) -> dict[str, Any]:
    if image.GetDimension() != 3 or label.GetDimension() != 3:
        raise RuntimeError("M6 geometry audit requires 3D image and label volumes")
    containment = foreground_containment(label, image)
    resampled = sitk.Resample(
        label,
        image,
        sitk.Transform(),
        sitk.sitkNearestNeighbor,
        0,
        label.GetPixelID(),
    )
    resampled_array = sitk.GetArrayFromImage(resampled)
    resampled_values = sorted(int(value) for value in np.unique(resampled_array))
    resampled_foreground = int(np.count_nonzero(resampled_array))
    criteria = {
        "three_dimensional": True,
        "label_values_allowed": bool(containment["allowed_label_values"]),
        "label_foreground_nonempty": int(containment["foreground_voxels"]) > 0,
        "foreground_physically_contained": int(containment["out_of_domain_foreground_voxels"]) == 0,
        "resampled_foreground_nonempty": resampled_foreground > 0,
        "resampled_values_allowed": set(resampled_values) <= ALLOWED_LABELS,
    }
    eligible = all(criteria.values())
    return {
        "patient_id": patient_id,
        "source": source_for_patient(patient_id),
        "eligible": eligible,
        "criteria": criteria,
        "image_geometry": image_geometry(image),
        "label_geometry": image_geometry(label),
        "array_size_equal": image.GetSize() == label.GetSize(),
        "foreground": containment,
        "resampled_foreground_voxels": resampled_foreground,
        "resampled_label_values": resampled_values,
        "known_0055_dimension_mismatch": patient_id == "ProstateDx-01-0055",
    }


def download_series(uid: str) -> bytes:
    query = urllib.parse.urlencode({"SeriesInstanceUID": uid, "NewFileNames": "Yes"})
    return _download(f"{NBIA_IMAGE_URL}?{query}", timeout=180)


def audit_case(uid: str, label_index: dict[str, bytes], root: Path) -> dict[str, Any]:
    case_dir = root / hashlib.sha256(uid.encode()).hexdigest()[:16]
    case_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = download_series(uid)
        patient_id, image = _read_series(payload, uid, case_dir / "dicom")
        if patient_id not in label_index:
            raise RuntimeError(f"No official training label found for {patient_id}")
        label = _read_label(label_index[patient_id], case_dir / "label.nrrd")
        record = assess_geometry(patient_id, image, label)
        record["series_uid"] = uid
        record["dicom_zip_sha256"] = hashlib.sha256(payload).hexdigest()
        record["label_sha256"] = hashlib.sha256(label_index[patient_id]).hexdigest()
        return record
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def build_audit() -> dict[str, Any]:
    manifest = _download(TRAINING_MANIFEST_URL)
    labels_zip = _download(TRAINING_LABEL_URL)
    uids = parse_manifest_series_uids(manifest)
    labels = label_members(labels_zip)

    with tempfile.TemporaryDirectory(prefix="truemargin-m6-geometry-") as temp:
        root = Path(temp)
        records: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
            futures = {pool.submit(audit_case, uid, labels, root): uid for uid in uids}
            for future in as_completed(futures):
                records.append(future.result())

    records.sort(key=lambda item: item["patient_id"])
    patient_ids = [str(item["patient_id"]) for item in records]
    if len(records) != EXPECTED_CASES or len(set(patient_ids)) != EXPECTED_CASES:
        raise RuntimeError("Geometry audit did not resolve exactly 60 unique training anatomies")
    source_counts = {
        source: sum(item["source"] == source for item in records)
        for source in EXPECTED_SOURCE_COUNTS
    }
    if source_counts != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(f"Unexpected training source composition: {source_counts}")

    ineligible = [item["patient_id"] for item in records if not item["eligible"]]
    mismatch = next((item for item in records if item["patient_id"] == "ProstateDx-01-0055"), None)
    if mismatch is None:
        raise RuntimeError("Known ProstateDx-01-0055 case missing from training audit")

    status = "complete" if not ineligible else "incomplete"
    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "training-geometry-eligibility",
        "status": status,
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "calibration_fit_authorized": False,
            "split_assignment_authorized": False,
            "synthetic_deformation_authorized": False,
            "dicom_download_performed": True,
        },
        "policy": {
            "partition": "training",
            "expected_anatomies": EXPECTED_CASES,
            "eligibility_uses_outcomes": False,
            "array_size_equality_required": False,
            "physical_foreground_containment_required": True,
            "nearest_neighbor_resampling_required": True,
            "allowed_label_values": sorted(ALLOWED_LABELS),
            "known_0055_dimension_mismatch_is_automatic_exclusion": False,
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
        "eligible_count": EXPECTED_CASES - len(ineligible),
        "ineligible_patient_ids": ineligible,
        "known_0055_record": mismatch,
        "cases": records,
        "summary": {
            "geometry_freeze_ready": not ineligible,
            "split_assignment_authorized": False,
            "result_bearing_m6_authorized": False,
        },
    }


def failure_record(exc: BaseException) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "training-geometry-eligibility",
        "status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "calibration_fit_authorized": False,
            "split_assignment_authorized": False,
            "synthetic_deformation_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/m6_training_geometry_eligibility.json"),
    )
    args = parser.parse_args()
    try:
        result = build_audit()
    except Exception as exc:
        result = failure_record(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_TRAINING_GEOMETRY_STATUS={result['status'].upper()}")
    if "eligible_count" in result:
        print(f"M6_TRAINING_ELIGIBLE={result['eligible_count']}/{EXPECTED_CASES}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
