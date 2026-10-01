#!/usr/bin/env python3
"""Audit the external image/label identities proposed for TrueMargin M6.

This diagnostic is intentionally metadata-only. It hashes the official TCIA
challenge training manifest and label archives, derives the exact 60 source
SeriesInstanceUIDs and 60 label PatientIDs, and resolves those exact series in
IDC for review. It does not download DICOM images, choose a series heuristically,
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
OFFICIAL_IMAGE_MANIFEST_URLS = [
    (
        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
        "ISBI-Prostate-Challenge-Training.tcia?api=v2"
    )
]

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
SERIES_UID_RE = re.compile(r"\d+(?:\.\d+)+")
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


def download_resource(urls: list[str]) -> tuple[bytes, str, list[dict[str, str]]]:
    """Return resource bytes, successful URL, and failed transport attempts."""
    failures: list[dict[str, str]] = []
    for url in urls:
        try:
            return _request(url), url, failures
        except RuntimeError as exc:
            failures.append({"url": url, "error": str(exc)})
    raise RuntimeError(f"All {len(urls)} official transport URLs failed: {failures}")


def parse_tcia_series_uids(manifest_bytes: bytes, expected_series: int = 60) -> list[str]:
    """Parse the exact series UID list from an NBIA ``.tcia`` manifest."""
    text = manifest_bytes.decode("utf-8-sig")
    lines = [line.strip() for line in text.splitlines()]
    marker = "ListOfSeriesToDownload="
    try:
        marker_index = lines.index(marker)
    except ValueError as exc:
        raise RuntimeError("TCIA manifest is missing ListOfSeriesToDownload marker") from exc

    series_uids = [line for line in lines[marker_index + 1 :] if line]
    invalid = [uid for uid in series_uids if SERIES_UID_RE.fullmatch(uid) is None]
    if invalid:
        raise RuntimeError(f"TCIA manifest contains invalid series UID lines: {invalid[:3]}")
    if len(series_uids) != len(set(series_uids)):
        raise RuntimeError("TCIA training manifest contains duplicate SeriesInstanceUID values")
    if len(series_uids) != expected_series:
        raise RuntimeError(
            f"Expected {expected_series} challenge training series; found {len(series_uids)}"
        )
    return series_uids


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


def query_idc_official_series(series_uids: list[str]) -> dict[str, Any]:
    """Resolve the exact official challenge series UIDs in current IDC metadata."""
    response = _post_json(
        f"{IDC_REST_BASE}/cohort/manifest",
        {
            "filters": {
                "terms": {
                    "collection_id": [
                        str(SOURCES["prostate_3t"]["idc_collection_id"]),
                        str(SOURCES["prostate_diagnosis"]["idc_collection_id"]),
                    ],
                    "SeriesInstanceUID": series_uids,
                    "Modality": ["MR"],
                }
            },
            "page": 0,
            "page_size": 5000,
        },
    )
    if response.get("truncated") is True:
        raise RuntimeError("IDC official-series metadata query was truncated")
    rows = response.get("series")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("IDC response is missing a valid official-series list")
    return response


def serialize_series(row: dict[str, Any]) -> dict[str, Any]:
    """Keep only stable review-relevant fields from one IDC series row."""
    return {field: row.get(field) for field in CANDIDATE_FIELDS}


def map_official_series_to_labels(
    labels_by_source: dict[str, list[dict[str, Any]]],
    official_series_uids: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cross-check exact manifest series against the official challenge label roster."""
    source_by_patient: dict[str, str] = {}
    for source_key, labels in labels_by_source.items():
        for label in labels:
            patient_id = str(label["patient_id"])
            if patient_id in source_by_patient:
                raise RuntimeError(f"Label PatientID appears in multiple sources: {patient_id}")
            source_by_patient[patient_id] = source_key

    requested_uids = set(official_series_uids)
    rows_by_uid: dict[str, list[dict[str, Any]]] = {uid: [] for uid in official_series_uids}
    unexpected_uids: set[str] = set()
    for row in rows:
        uid = str(row.get("SeriesInstanceUID", ""))
        if uid not in requested_uids:
            unexpected_uids.add(uid)
            continue
        rows_by_uid[uid].append(row)

    missing_uids = sorted(uid for uid, matches in rows_by_uid.items() if not matches)
    duplicate_uids = sorted(uid for uid, matches in rows_by_uid.items() if len(matches) > 1)
    mapping: dict[str, list[dict[str, Any]]] = {
        patient_id: [] for patient_id in sorted(source_by_patient)
    }
    unexpected_patient_ids: set[str] = set()
    collection_mismatches: list[dict[str, str]] = []

    for uid in official_series_uids:
        matches = rows_by_uid[uid]
        if len(matches) != 1:
            continue
        row = matches[0]
        patient_id = str(row.get("PatientID", ""))
        source_key = source_by_patient.get(patient_id)
        if source_key is None:
            unexpected_patient_ids.add(patient_id)
            continue

        expected_collection_id = str(SOURCES[source_key]["idc_collection_id"])
        observed_collection_id = row.get("collection_id")
        if (
            observed_collection_id is not None
            and str(observed_collection_id) != expected_collection_id
        ):
            collection_mismatches.append(
                {
                    "patient_id": patient_id,
                    "series_uid": uid,
                    "expected_collection_id": expected_collection_id,
                    "observed_collection_id": str(observed_collection_id),
                }
            )
        mapping[patient_id].append(serialize_series(row))

    missing_patient_ids = sorted(patient for patient, matches in mapping.items() if not matches)
    multiple_series_patient_ids = sorted(
        patient for patient, matches in mapping.items() if len(matches) > 1
    )

    return {
        "official_series_by_patient": mapping,
        "missing_series_uids_in_idc": missing_uids,
        "duplicate_series_uids_in_idc": duplicate_uids,
        "unexpected_series_uids_from_idc": sorted(unexpected_uids),
        "missing_label_patient_ids": missing_patient_ids,
        "multiple_official_series_per_label_patient": multiple_series_patient_ids,
        "unexpected_patient_ids_from_idc": sorted(unexpected_patient_ids),
        "source_collection_mismatches": collection_mismatches,
    }


def audit_label_source(source_key: str, config: dict[str, Any]) -> dict[str, Any]:
    archive_bytes, archive_url, transport_failures = download_resource(list(config["archive_urls"]))
    labels = enumerate_labels(
        archive_bytes,
        expected_prefix=str(config["patient_prefix"]),
        expected_subjects=int(config["expected_subjects"]),
    )
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
        "patient_ids": sorted(str(record["patient_id"]) for record in labels),
    }


def build_audit() -> dict[str, Any]:
    """Build the complete 60-subject metadata-only audit record."""
    manifest_bytes, manifest_url, manifest_transport_failures = download_resource(
        OFFICIAL_IMAGE_MANIFEST_URLS
    )
    official_series_uids = parse_tcia_series_uids(manifest_bytes)

    sources = {key: audit_label_source(key, config) for key, config in SOURCES.items()}
    labels_by_source = {source_key: source["labels"] for source_key, source in sources.items()}
    all_patient_ids = [
        patient for source in sources.values() for patient in source["patient_ids"]
    ]
    if len(all_patient_ids) != 60 or len(set(all_patient_ids)) != 60:
        raise RuntimeError(
            f"Expected 60 unique challenge training PatientIDs; found {len(set(all_patient_ids))}"
        )

    idc_response = query_idc_official_series(official_series_uids)
    rows = idc_response["series"]
    resolution = map_official_series_to_labels(labels_by_source, official_series_uids, rows)
    issue_keys = (
        "missing_series_uids_in_idc",
        "duplicate_series_uids_in_idc",
        "unexpected_series_uids_from_idc",
        "missing_label_patient_ids",
        "multiple_official_series_per_label_patient",
        "unexpected_patient_ids_from_idc",
        "source_collection_mismatches",
    )
    issues = {key: resolution[key] for key in issue_keys if resolution[key]}
    status = "complete" if not issues else "incomplete"

    return {
        "schema_version": 1,
        "milestone": "M6",
        "audit": "external-input-identity",
        "status": status,
        "challenge": {
            "name": CHALLENGE_NAME,
            "doi": CHALLENGE_DOI,
            "training_subjects_expected": 60,
            "training_series_expected": 60,
        },
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "calibration_fit_authorized": False,
            "split_assignment_authorized": False,
            "dicom_download_performed": False,
            "heuristic_source_series_selection_performed": False,
        },
        "official_training_image_manifest": {
            "selected_url": manifest_url,
            "transport_failures_before_success": manifest_transport_failures,
            "size_bytes": len(manifest_bytes),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "series_uids": official_series_uids,
        },
        "sources": sources,
        "idc_resolution": {
            "warnings": idc_response.get("warnings", []),
            "truncated": idc_response.get("truncated", False),
            "series_rows": len(rows),
            **resolution,
        },
        "summary": {
            "unique_training_patient_ids": len(set(all_patient_ids)),
            "official_training_series_uids": len(official_series_uids),
            "idc_series_rows": len(rows),
            "mapping_issues": issues,
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
                "heuristic_source_series_selection_performed": False,
            },
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_INPUT_IDENTITY_AUDIT_STATUS={result['status'].upper()}")
    summary = result.get("summary", {})
    if "unique_training_patient_ids" in summary:
        print(f"M6_TRAINING_PATIENT_IDS={summary['unique_training_patient_ids']}")
    if "official_training_series_uids" in summary:
        print(f"M6_TRAINING_SERIES_UIDS={summary['official_training_series_uids']}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
