#!/usr/bin/env python3
"""Audit the external image/label identities proposed for TrueMargin M6.

This diagnostic is intentionally metadata-only. It downloads the small official
TCIA training-segmentation archives, derives the 60 challenge PatientIDs from
those archive members, and asks IDC for every public MR series associated with
those exact patients. It does not choose a source series, download DICOM images,
assign M6 cohort roles, run registration, or fit calibration.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CHALLENGE_NAME = "NCI-ISBI 2013 Challenge: Automated Segmentation of Prostate Structures"
CHALLENGE_DOI = "10.7937/K9/TCIA.2015.zF0vlOPv"
IDC_REST_BASE = "https://api.imaging.datacommons.cancer.gov/v3"
NETWORK_ATTEMPTS = 4
NETWORK_BACKOFF_SECONDS = (2, 4, 8)

SOURCES: dict[str, dict[str, Any]] = {
    "prostate_3t": {
        "patient_prefix": "Prostate3T-01-",
        "expected_subjects": 30,
        "source_collection": "Prostate-3T",
        "source_collection_doi": "10.7937/K9/TCIA.2015.QJTV5IL5",
        "idc_collection_id": "prostate_3t",
        "archive_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/6882545/"
                "NCI_ISBI_Challenge-Prostate3T_Training_Segmentations.zip?api=v2&"
                "modificationDate=1689369325601&version=1"
            ),
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/6882545/"
                "NCI_ISBI_Challenge-Prostate3T_Training_Segmentations.zip?api=v2"
            ),
        ],
    },
    "prostate_diagnosis": {
        "patient_prefix": "ProstateDx-01-",
        "expected_subjects": 30,
        "source_collection": "PROSTATE-DIAGNOSIS",
        "source_collection_doi": "10.7937/K9/TCIA.2015.FOQEUJVT",
        "idc_collection_id": "prostate_diagnosis",
        "archive_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/6882545/"
                "NCI_ISBI_Challenge-ProstateDx_Training_Segmentations.zip?api=v2&"
                "modificationDate=1689369337858&version=1"
            ),
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/6882545/"
                "NCI_ISBI_Challenge-ProstateDx_Training_Segmentations.zip?api=v2"
            ),
        ],
    },
}

PATIENT_ID_RE = re.compile(r"(Prostate(?:3T|Dx)-01-\d{4})")
CANDIDATE_FIELDS = (
    "PatientID",
    "collection_id",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SeriesDescription",
    "ProtocolName",
    "Modality",
    "instanceCount",
    "BodyPartExamined",
    "Manufacturer",
    "ManufacturerModelName",
    "MagneticFieldStrength",
    "SliceThickness",
    "Rows",
    "Columns",
)


def _request(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 90,
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


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = _request(
        url,
        data=json.dumps(payload, sort_keys=True).encode("utf-8"),
        content_type="application/json",
        timeout=120,
    )
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return decoded


def download_archive(urls: list[str]) -> tuple[bytes, str, list[dict[str, str]]]:
    """Return archive bytes, successful URL, and failed transport attempts."""
    failures: list[dict[str, str]] = []
    for url in urls:
        try:
            return _request(url), url, failures
        except RuntimeError as exc:
            failures.append({"url": url, "error": str(exc)})
    raise RuntimeError(f"All {len(urls)} official archive transport URLs failed: {failures}")


def extract_patient_id(member_name: str, expected_prefix: str) -> str:
    """Extract and validate a challenge training PatientID from one NRRD member path."""
    match = PATIENT_ID_RE.search(Path(member_name).name)
    if match is None:
        raise ValueError(f"Cannot derive challenge PatientID from NRRD member: {member_name}")
    patient_id = match.group(1)
    if not patient_id.startswith(expected_prefix):
        raise ValueError(
            f"Archive member {member_name} resolved to unexpected source PatientID {patient_id}"
        )
    return patient_id


def enumerate_labels(
    archive_bytes: bytes,
    *,
    expected_prefix: str,
    expected_subjects: int,
) -> list[dict[str, Any]]:
    """Enumerate and hash the official NRRD label members in one source archive."""
    labels: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        members = sorted(
            info
            for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".nrrd")
        )
        for info in members:
            payload = archive.read(info)
            patient_id = extract_patient_id(info.filename, expected_prefix)
            labels.append(
                {
                    "patient_id": patient_id,
                    "archive_member": info.filename,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "corrected_label_filename": "correctedLabels" in Path(info.filename).name,
                }
            )

    patient_ids = [str(record["patient_id"]) for record in labels]
    duplicates = sorted({patient for patient in patient_ids if patient_ids.count(patient) > 1})
    if duplicates:
        raise RuntimeError(f"Duplicate NRRD PatientIDs in archive: {duplicates}")
    if len(labels) != expected_subjects:
        raise RuntimeError(
            f"Expected {expected_subjects} NRRD subjects for {expected_prefix}; found {len(labels)}"
        )
    return labels


def query_idc_series(patient_ids: list[str], collection_id: str) -> dict[str, Any]:
    """Return IDC MR-series metadata for all requested patients without selecting a series."""
    response = _post_json(
        f"{IDC_REST_BASE}/cohort/manifest",
        {
            "filters": {
                "terms": {
                    "collection_id": [collection_id],
                    "PatientID": patient_ids,
                    "Modality": ["MR"],
                }
            },
            "page": 0,
            "page_size": 5000,
        },
    )
    if response.get("truncated") is True:
        raise RuntimeError(f"IDC cohort metadata query was truncated for {collection_id}")
    rows = response.get("series")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"IDC response missing a valid series list for {collection_id}")
    return response


def serialize_candidate_series(row: dict[str, Any]) -> dict[str, Any]:
    """Keep only stable review-relevant fields from an IDC series row."""
    return {field: row.get(field) for field in CANDIDATE_FIELDS}


def group_candidate_series(
    patient_ids: list[str], rows: list[dict[str, Any]]
) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[str]]:
    """Group candidate MR series by requested challenge PatientID."""
    requested = set(patient_ids)
    grouped: dict[str, list[dict[str, Any]]] = {patient: [] for patient in patient_ids}
    unexpected: set[str] = set()
    for row in rows:
        patient = str(row.get("PatientID", ""))
        if patient not in requested:
            unexpected.add(patient)
            continue
        grouped[patient].append(serialize_candidate_series(row))

    for candidates in grouped.values():
        candidates.sort(
            key=lambda record: (
                str(record.get("StudyInstanceUID") or ""),
                str(record.get("SeriesInstanceUID") or ""),
            )
        )
    missing = sorted(patient for patient, candidates in grouped.items() if not candidates)
    return grouped, missing, sorted(unexpected)


def audit_source(source_key: str, config: dict[str, Any]) -> dict[str, Any]:
    archive_bytes, archive_url, transport_failures = download_archive(list(config["archive_urls"]))
    labels = enumerate_labels(
        archive_bytes,
        expected_prefix=str(config["patient_prefix"]),
        expected_subjects=int(config["expected_subjects"]),
    )
    patient_ids = sorted(str(record["patient_id"]) for record in labels)
    response = query_idc_series(patient_ids, str(config["idc_collection_id"]))
    rows = response["series"]
    grouped, missing, unexpected = group_candidate_series(patient_ids, rows)

    return {
        "source_key": source_key,
        "source_collection": config["source_collection"],
        "source_collection_doi": config["source_collection_doi"],
        "idc_collection_id": config["idc_collection_id"],
        "expected_subjects": config["expected_subjects"],
        "archive": {
            "selected_url": archive_url,
            "transport_failures_before_success": transport_failures,
            "size_bytes": len(archive_bytes),
            "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        },
        "labels": labels,
        "patient_ids": patient_ids,
        "idc_query": {
            "warnings": response.get("warnings", []),
            "truncated": response.get("truncated", False),
            "candidate_series_rows": len(rows),
            "missing_patient_ids": missing,
            "unexpected_patient_ids": unexpected,
        },
        "candidate_series_by_patient": grouped,
    }


def build_audit() -> dict[str, Any]:
    """Build the complete 60-subject metadata-only audit record."""
    sources = {key: audit_source(key, config) for key, config in SOURCES.items()}
    all_patient_ids = [
        patient for source in sources.values() for patient in source["patient_ids"]
    ]
    if len(all_patient_ids) != 60 or len(set(all_patient_ids)) != 60:
        raise RuntimeError(
            f"Expected 60 unique challenge training PatientIDs; found {len(set(all_patient_ids))}"
        )

    missing = {
        source_key: source["idc_query"]["missing_patient_ids"]
        for source_key, source in sources.items()
        if source["idc_query"]["missing_patient_ids"]
    }
    unexpected = {
        source_key: source["idc_query"]["unexpected_patient_ids"]
        for source_key, source in sources.items()
        if source["idc_query"]["unexpected_patient_ids"]
    }
    status = "complete" if not missing and not unexpected else "incomplete"

    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "external-input-identity",
        "status": status,
        "challenge": {
            "name": CHALLENGE_NAME,
            "doi": CHALLENGE_DOI,
            "training_subjects_expected": 60,
        },
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "calibration_fit_authorized": False,
            "split_assignment_authorized": False,
            "dicom_download_performed": False,
            "source_series_selected": False,
        },
        "sources": sources,
        "summary": {
            "unique_training_patient_ids": len(set(all_patient_ids)),
            "missing_patient_ids_by_source": missing,
            "unexpected_patient_ids_by_source": unexpected,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/m6_input_identity_audit.json"),
        help="Path for the machine-readable audit record.",
    )
    args = parser.parse_args()

    try:
        result = build_audit()
    except Exception as exc:
        result = {
            "schema_version": 1,
            "milestone": "M6",
            "audit": "external-input-identity",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "authorization_boundary": {
                "result_bearing_authorized": False,
                "registration_authorized": False,
                "calibration_fit_authorized": False,
                "split_assignment_authorized": False,
                "dicom_download_performed": False,
                "source_series_selected": False,
            },
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_INPUT_IDENTITY_AUDIT_STATUS={result['status'].upper()}")
    summary = result.get("summary", {})
    if "unique_training_patient_ids" in summary:
        print(f"M6_TRAINING_PATIENT_IDS={summary['unique_training_patient_ids']}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
