#!/usr/bin/env python3
"""Fetch the frozen public inputs needed for the TrueMargin geometry preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
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


def _download(url: str, destination: Path, timeout: int = 90) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    last_error: BaseException | None = None

    for attempt in range(NETWORK_ATTEMPTS):
        try:
            digest = hashlib.sha256()
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with destination.open("wb") as handle:
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        handle.write(chunk)
            return digest.hexdigest()
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt + 1 == NETWORK_ATTEMPTS:
                break
            delay = NETWORK_BACKOFF_SECONDS[min(attempt, len(NETWORK_BACKOFF_SECONDS) - 1)]
            time.sleep(delay)

    message = f"Network download failed after {NETWORK_ATTEMPTS} attempts: {url}"
    raise RuntimeError(message) from last_error


def _series_query(patient: str) -> str:
    if patient not in FROZEN_T2_SERIES_SUFFIXES:
        raise ValueError(f"Patient is not in the frozen cohort: {patient}")
    return f"""
        SELECT
            collection_id,
            PatientID,
            StudyInstanceUID,
            SeriesInstanceUID,
            Modality,
            SeriesDescription,
            instanceCount,
            series_size_MB,
            series_aws_url
        FROM index
        WHERE collection_id = '{IDC_COLLECTION_ID}'
          AND PatientID = '{patient}'
          AND Modality = 'MR'
        ORDER BY SeriesInstanceUID
    """


def _series_rows(client: Any, patient: str) -> list[dict[str, Any]]:
    frame = client.sql_query(_series_query(patient))
    rows = frame.to_dict(orient="records")
    if not isinstance(rows, list):
        raise RuntimeError(f"IDC index query returned an invalid result for {patient}")
    return rows


def resolve_frozen_series(
    rows: list[dict[str, Any]],
    *,
    patient: str,
    suffix: str,
) -> dict[str, Any]:
    patient_rows = [
        row
        for row in rows
        if str(row.get("collection_id", "")) == IDC_COLLECTION_ID
        and str(row.get("PatientID", "")) == patient
        and str(row.get("Modality", "")) == "MR"
    ]
    matches = [
        row
        for row in patient_rows
        if str(row.get("SeriesInstanceUID", "")).rsplit(".", 1)[-1] == suffix
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"{patient}: frozen T2 suffix {suffix!r} resolved to {len(matches)} public series"
        )

    selected = matches[0]
    descriptor = str(selected.get("SeriesDescription", "")).lower()
    if "t2" not in descriptor:
        raise RuntimeError(
            f"{patient}: frozen series {selected.get('SeriesInstanceUID')} "
            f"is not described as T2: {descriptor!r}"
        )
    return selected


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


def _download_idc_series(client: Any, series_uid: str, destination: Path) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        download_root = Path(tmp) / "download"
        client.download_dicom_series(
            seriesInstanceUID=[series_uid],
            downloadDir=str(download_root),
            dirTemplate="%SeriesInstanceUID",
        )
        return _copy_downloaded_dicoms(download_root, destination)


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
    from idc_index import IDCClient

    installed_idc_index = importlib.metadata.version("idc-index")
    installed_idc_index_data = importlib.metadata.version("idc-index-data")
    if installed_idc_index != IDC_INDEX_VERSION:
        raise RuntimeError(
            f"idc-index version drift: expected {IDC_INDEX_VERSION}, got {installed_idc_index}"
        )

    client = IDCClient.client()
    radiology_root = data_root / "prostate_fused_manifest" / "prostate_fused_mri_pathology"
    hecap_root = data_root / "hecap"

    resolved: dict[str, dict[str, Any]] = {}
    for patient, suffix in FROZEN_T2_SERIES_SUFFIXES.items():
        rows = _series_rows(client, patient)
        selected = resolve_frozen_series(rows, patient=patient, suffix=suffix)

        uid = str(selected["SeriesInstanceUID"])
        study_uid = str(selected["StudyInstanceUID"])
        series_dir = radiology_root / patient / study_uid / suffix
        object_count = _download_idc_series(client, uid, series_dir)

        series_aws_url = str(selected.get("series_aws_url", ""))
        if not series_aws_url.startswith("s3://"):
            raise RuntimeError(f"{patient}: IDC index returned invalid series_aws_url")

        resolved[patient] = {
            "frozen_series_suffix": suffix,
            "series_instance_uid": uid,
            "study_instance_uid": study_uid,
            "series_description": selected.get("SeriesDescription"),
            "reported_instance_count": selected.get("instanceCount"),
            "series_size_mb": selected.get("series_size_MB"),
            "series_aws_url": series_aws_url,
            "series_aws_url_sha256": hashlib.sha256(series_aws_url.encode()).hexdigest(),
            "downloaded_file_count": object_count,
        }

    with tempfile.TemporaryDirectory() as tmp:
        hecap_archive = Path(tmp) / "fused_prostate_matlab.zip"
        hecap_archive_sha256 = _download(HECAP_ARCHIVE_URL, hecap_archive)
        hecap_files = _extract_hecap_masks(hecap_archive, hecap_root)

    manifest = {
        "schema_version": 3,
        "purpose": "truemargin_known_gt_geometry_preflight_inputs",
        "collection": COLLECTION,
        "idc_collection_id": IDC_COLLECTION_ID,
        "collection_version": COLLECTION_VERSION,
        "collection_version_date": COLLECTION_VERSION_DATE,
        "metadata_source": "idc-index local read-only index",
        "idc_index_version": installed_idc_index,
        "idc_index_data_version": installed_idc_index_data,
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
    print(f"idc_index_version={manifest['idc_index_version']}")
    print(f"idc_index_data_version={manifest['idc_index_data_version']}")
    print(f"resolved_t2_series={len(manifest['frozen_t2_series'])}")
    print(f"hecap_masks={len(manifest['hecap_file_sha256'])}")
    print(f"manifest={args.output}")


if __name__ == "__main__":
    main()
