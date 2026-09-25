#!/usr/bin/env python3
"""Fetch the frozen public inputs needed for the TrueMargin geometry preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

COLLECTION = "Prostate-Fused-MRI-Pathology"
IDC_COLLECTION_ID = "prostate_fused_mri_pathology"
COLLECTION_VERSION = "2"
COLLECTION_VERSION_DATE = "2023-04-10"
IDC_REST_BASE = "https://api.imaging.datacommons.cancer.gov/v3"
IDC_INDEX_VERSION = "0.12.5"
HECAP_ARCHIVE_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/23691514/"
    "fused_prostate_matlab.zip?api=v2&modificationDate=1476802701461&version=1"
)
NETWORK_ATTEMPTS = 4
NETWORK_BACKOFF_SECONDS = (2, 4, 8)

FROZEN_T2_SERIES_SUFFIXES = {
    "aaa0044": "13614",
    "aaa0051": "36207",
    "aaa0053": "45314",
    "aaa0060": "12400",
    "aaa0064": "40733",
    "aaa0069": "58343",
    "aaa0071": "27783",
    "aaa0072": "64767",
    "aaa0086": "42255",
    "aaa0087": "30095",
}
SERIES_IDENTITY_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "KNOWN_GT_SERIES_IDENTITY.json"
)


def load_frozen_series_identity() -> dict[str, dict[str, Any]]:
    payload = json.loads(SERIES_IDENTITY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("Frozen series identity schema drift")
    if payload.get("study") != "hyperparameter-known-gt-v1":
        raise RuntimeError("Frozen series identity study drift")
    if payload.get("collection_id") != IDC_COLLECTION_ID:
        raise RuntimeError("Frozen series identity collection drift")

    series = payload.get("series")
    if not isinstance(series, dict):
        raise RuntimeError("Frozen series identity is missing the series mapping")
    if set(series) != set(FROZEN_T2_SERIES_SUFFIXES):
        raise RuntimeError("Frozen series identity patient set drift")

    for patient, legacy_suffix in FROZEN_T2_SERIES_SUFFIXES.items():
        identity = series[patient]
        if not isinstance(identity, dict):
            raise RuntimeError(f"{patient}: invalid frozen series identity record")
        if identity.get("legacy_folder") != legacy_suffix:
            raise RuntimeError(f"{patient}: legacy series folder identity drift")
        series_uid = str(identity.get("series_uid", ""))
        if not series_uid.endswith(legacy_suffix):
            raise RuntimeError(f"{patient}: full SeriesInstanceUID does not match legacy suffix")
        if identity.get("series_description") != "T2 AXIAL SM FOV":
            raise RuntimeError(f"{patient}: frozen T2 series description drift")
    return series


def _request(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 60,
) -> bytes:
    headers = {"User-Agent": "truemargin-research/0.1"}
    if content_type is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )

    last_error: BaseException | None = None
    for attempt in range(NETWORK_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            last_error = exc
            if attempt + 1 == NETWORK_ATTEMPTS:
                break
            time.sleep(NETWORK_BACKOFF_SECONDS[min(attempt, len(NETWORK_BACKOFF_SECONDS) - 1)])
    message = f"Network request failed after {NETWORK_ATTEMPTS} attempts: {url}"
    raise RuntimeError(message) from last_error


def _get_json(url: str) -> dict[str, Any]:
    payload = json.loads(_request(url).decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return payload


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = _request(
        url,
        data=json.dumps(payload, sort_keys=True).encode("utf-8"),
        content_type="application/json",
        timeout=90,
    )
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return decoded


def _post_text(url: str, payload: dict[str, Any]) -> str:
    raw = _request(
        url,
        data=json.dumps(payload, sort_keys=True).encode("utf-8"),
        content_type="application/json",
        timeout=90,
    )
    text = raw.decode("utf-8").strip()
    if not text:
        raise RuntimeError(f"Expected non-empty text response from {url}")
    return text + "\n"


def _download(url: str, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = _request(url, timeout=90)
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _idc_filters(patient: str, *, series_uid: str | None = None) -> dict[str, Any]:
    terms: dict[str, list[str]] = {
        "collection_id": [IDC_COLLECTION_ID],
        "PatientID": [patient],
        "Modality": ["MR"],
    }
    if series_uid is not None:
        terms["SeriesInstanceUID"] = [series_uid]
    return {"terms": terms}


def _idc_series_rows(patient: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = {
        "filters": _idc_filters(patient),
        "page": 0,
        "page_size": 500,
    }
    response = _post_json(f"{IDC_REST_BASE}/cohort/manifest", payload)

    warnings = response.get("warnings", [])
    if warnings:
        raise RuntimeError(f"IDC cohort query warnings for {patient}: {warnings}")
    if response.get("truncated") is True:
        raise RuntimeError(f"IDC cohort query truncated for {patient}")

    rows = response.get("series")
    if not isinstance(rows, list):
        raise RuntimeError(f"IDC cohort response missing series list for {patient}")
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"IDC cohort response contains invalid series rows for {patient}")
    return rows, response


def resolve_frozen_series(
    rows: list[dict[str, Any]],
    *,
    patient: str,
    identity: dict[str, Any],
) -> dict[str, Any]:
    expected_uid = str(identity["series_uid"])
    expected_study_uid = str(identity["study_uid"])
    expected_description = str(identity["series_description"])
    expected_count = int(identity["instance_count"])
    legacy_suffix = str(identity["legacy_folder"])

    if not expected_uid.endswith(legacy_suffix):
        raise RuntimeError(f"{patient}: frozen full UID / legacy-folder mismatch")

    patient_rows = [
        row
        for row in rows
        if str(row.get("PatientID", "")) == patient
        and str(row.get("collection_id", IDC_COLLECTION_ID)) == IDC_COLLECTION_ID
        and str(row.get("Modality", "MR")) == "MR"
    ]
    matches = [row for row in patient_rows if str(row.get("SeriesInstanceUID", "")) == expected_uid]
    if len(matches) != 1:
        raise RuntimeError(
            f"{patient}: frozen full SeriesInstanceUID resolved to " f"{len(matches)} public series"
        )

    selected = matches[0]
    if str(selected.get("StudyInstanceUID", "")) != expected_study_uid:
        raise RuntimeError(f"{patient}: frozen StudyInstanceUID drift")
    if str(selected.get("SeriesDescription", "")) != expected_description:
        raise RuntimeError(f"{patient}: frozen SeriesDescription drift")
    if int(selected.get("instanceCount", -1)) != expected_count:
        raise RuntimeError(f"{patient}: frozen series instance-count drift")
    return selected


def _idc_manifest_for_series(patient: str, series_uid: str) -> str:
    response = _post_text(
        f"{IDC_REST_BASE}/cohort/manifest.txt",
        {
            "filters": _idc_filters(patient, series_uid=series_uid),
            "source": "aws",
        },
    )
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not lines or any(not line.startswith("s3://") for line in lines):
        raise RuntimeError(f"IDC returned an invalid download manifest for {patient}")
    return "\n".join(lines) + "\n"


def _copy_downloaded_dicoms(download_root: Path, destination: Path) -> int:
    files = sorted(download_root.rglob("*.dcm"))
    if not files:
        raise RuntimeError(f"IDC download produced no DICOM files under {download_root}")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    for source in files:
        if source.name in seen:
            raise RuntimeError(
                f"Duplicate DICOM filename while flattening IDC download: {source.name}"
            )
        seen.add(source.name)
        shutil.copy2(source, destination / source.name)
    return len(files)


def _download_idc_series(patient: str, series_uid: str, destination: Path) -> tuple[int, str]:
    manifest_text = _idc_manifest_for_series(patient, series_uid)
    manifest_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        manifest_path = tmp_root / "manifest.s5cmd"
        download_root = tmp_root / "download"
        manifest_path.write_text(manifest_text, encoding="utf-8")

        completed = subprocess.run(
            [
                "idc",
                "download-from-manifest",
                "--manifest-file",
                str(manifest_path),
                "--download-dir",
                str(download_root),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=1800,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"IDC download failed for {patient} / {series_uid}: "
                f"exit={completed.returncode}\n{completed.stdout[-4000:]}"
            )

        object_count = _copy_downloaded_dicoms(download_root, destination)
    return object_count, manifest_sha256


def _extract_hecap_masks(archive: Path, destination: Path) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(tmp_root)
        all_files = [path for path in tmp_root.rglob("*") if path.is_file()]
        for patient in FROZEN_T2_SERIES_SUFFIXES:
            filename = f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha"
            matches = [path for path in all_files if path.name == filename]
            if len(matches) != 1:
                raise RuntimeError(
                    f"{patient}: expected exactly one HECaP file {filename}, found {len(matches)}"
                )
            target = destination / filename
            shutil.copy2(matches[0], target)
            copied[patient] = hashlib.sha256(target.read_bytes()).hexdigest()
    return copied


def fetch_inputs(data_root: Path, output: Path) -> dict[str, Any]:
    idc_version = _get_json(f"{IDC_REST_BASE}/version")
    if not str(idc_version.get("idc_version", "")).startswith("v"):
        raise RuntimeError(f"Unexpected IDC version response: {idc_version}")

    installed_idc_index = importlib.metadata.version("idc-index")
    if installed_idc_index != IDC_INDEX_VERSION:
        raise RuntimeError(
            f"idc-index version drift: expected {IDC_INDEX_VERSION}, got {installed_idc_index}"
        )

    radiology_root = data_root / "prostate_fused_manifest" / "prostate_fused_mri_pathology"
    hecap_root = data_root / "hecap"

    frozen_series = load_frozen_series_identity()
    resolved: dict[str, dict[str, Any]] = {}
    for patient, identity in frozen_series.items():
        rows, cohort_response = _idc_series_rows(patient)
        selected = resolve_frozen_series(rows, patient=patient, identity=identity)

        uid = str(selected["SeriesInstanceUID"])
        study_uid = str(selected["StudyInstanceUID"])
        legacy_folder = str(identity["legacy_folder"])
        series_dir = radiology_root / patient / study_uid / legacy_folder
        object_count, series_manifest_sha256 = _download_idc_series(patient, uid, series_dir)

        resolved[patient] = {
            "legacy_series_folder": legacy_folder,
            "frozen_series_identity": identity,
            "series_instance_uid": uid,
            "study_instance_uid": study_uid,
            "series_description": selected.get("SeriesDescription"),
            "protocol_name": selected.get("ProtocolName"),
            "reported_instance_count": selected.get("instanceCount"),
            "downloaded_file_count": object_count,
            "series_manifest_sha256": series_manifest_sha256,
            "cohort_filters_applied": cohort_response.get("filters_applied"),
        }

    with tempfile.TemporaryDirectory() as tmp:
        hecap_archive = Path(tmp) / "fused_prostate_matlab.zip"
        hecap_archive_sha256 = _download(HECAP_ARCHIVE_URL, hecap_archive)
        hecap_files = _extract_hecap_masks(hecap_archive, hecap_root)

    manifest = {
        "schema_version": 2,
        "purpose": "truemargin_known_gt_geometry_preflight_inputs",
        "collection": COLLECTION,
        "idc_collection_id": IDC_COLLECTION_ID,
        "collection_version": COLLECTION_VERSION,
        "collection_version_date": COLLECTION_VERSION_DATE,
        "idc_rest_base": IDC_REST_BASE,
        "idc_release": idc_version,
        "idc_index_version": installed_idc_index,
        "series_identity_path": str(
            SERIES_IDENTITY_PATH.relative_to(Path(__file__).resolve().parents[1])
        ),
        "frozen_t2_series": resolved,
        "hecap_source_url": HECAP_ARCHIVE_URL,
        "hecap_archive_sha256": hecap_archive_sha256,
        "hecap_file_sha256": hecap_files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/known_gt_data_acquisition.json"),
    )
    args = parser.parse_args()

    manifest = fetch_inputs(args.data_root, args.output)
    print(f"idc_release={manifest['idc_release'].get('idc_version')}")
    print(f"idc_index_version={manifest['idc_index_version']}")
    print(f"resolved_t2_series={len(manifest['frozen_t2_series'])}")
    print(f"hecap_masks={len(manifest['hecap_file_sha256'])}")
    print(f"manifest={args.output}")


if __name__ == "__main__":
    main()
