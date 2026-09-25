#!/usr/bin/env python3
"""Fetch the frozen public inputs needed for the TrueMargin geometry preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

COLLECTION = "Prostate-Fused-MRI-Pathology"
COLLECTION_VERSION = "2"
COLLECTION_VERSION_DATE = "2023-04-10"
NBIA_API_BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
HECAP_ARCHIVE_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/23691514/"
    "fused_prostate_matlab.zip?api=v2&modificationDate=1476802701461&version=1"
)

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


def _json_get(url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list response from {url}")
    return payload


def _download(url: str, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            handle.write(chunk)
    return digest.hexdigest()


def resolve_frozen_series(
    rows: list[dict[str, Any]],
    *,
    patient: str,
    suffix: str,
) -> dict[str, Any]:
    patient_rows = [row for row in rows if str(row.get("PatientID", "")) == patient]
    matches = [
        row
        for row in patient_rows
        if str(row.get("SeriesInstanceUID", "")).endswith(suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"{patient}: frozen T2 suffix {suffix!r} resolved to {len(matches)} public series"
        )

    selected = matches[0]
    descriptor = " ".join(
        str(selected.get(key, ""))
        for key in ("SeriesDescription", "ProtocolName")
    ).lower()
    if "t2" not in descriptor:
        raise RuntimeError(
            f"{patient}: frozen series {selected.get('SeriesInstanceUID')} "
            f"is not described as T2: {descriptor!r}"
        )
    return selected


def _extract_flat_zip(archive: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if not name:
                continue
            if name in seen:
                raise RuntimeError(f"Duplicate filename while flattening archive: {name}")
            seen.add(name)
            target = destination / name
            with zf.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            count += 1
    if count == 0:
        raise RuntimeError(f"Archive contained no files: {archive}")
    return count


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
    radiology_root = (
        data_root
        / "prostate_fused_manifest"
        / "prostate_fused_mri_pathology"
    )
    hecap_root = data_root / "hecap"

    resolved: dict[str, dict[str, Any]] = {}
    for patient, suffix in FROZEN_T2_SERIES_SUFFIXES.items():
        query = urllib.parse.urlencode(
            {
                "Collection": COLLECTION,
                "PatientID": patient,
                "Modality": "MR",
                "format": "json",
            }
        )
        rows = _json_get(f"{NBIA_API_BASE}/getSeries?{query}")
        selected = resolve_frozen_series(rows, patient=patient, suffix=suffix)

        uid = str(selected["SeriesInstanceUID"])
        study_uid = str(selected["StudyInstanceUID"])
        series_dir = radiology_root / patient / study_uid / suffix
        image_query = urllib.parse.urlencode({"SeriesInstanceUID": uid})

        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / f"{patient}-{suffix}.zip"
            archive_sha256 = _download(f"{NBIA_API_BASE}/getImage?{image_query}", archive)
            object_count = _extract_flat_zip(archive, series_dir)

        resolved[patient] = {
            "frozen_series_suffix": suffix,
            "series_instance_uid": uid,
            "study_instance_uid": study_uid,
            "series_description": selected.get("SeriesDescription"),
            "protocol_name": selected.get("ProtocolName"),
            "api_image_count": selected.get("ImageCount"),
            "downloaded_file_count": object_count,
            "download_archive_sha256": archive_sha256,
        }

    with tempfile.TemporaryDirectory() as tmp:
        hecap_archive = Path(tmp) / "fused_prostate_matlab.zip"
        hecap_archive_sha256 = _download(HECAP_ARCHIVE_URL, hecap_archive)
        hecap_files = _extract_hecap_masks(hecap_archive, hecap_root)

    manifest = {
        "schema_version": 1,
        "purpose": "truemargin_known_gt_geometry_preflight_inputs",
        "collection": COLLECTION,
        "collection_version": COLLECTION_VERSION,
        "collection_version_date": COLLECTION_VERSION_DATE,
        "nbia_api_base": NBIA_API_BASE,
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
    print(f"resolved_t2_series={len(manifest['frozen_t2_series'])}")
    print(f"hecap_masks={len(manifest['hecap_file_sha256'])}")
    print(f"manifest={args.output}")


if __name__ == "__main__":
    main()
