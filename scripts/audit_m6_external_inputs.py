#!/usr/bin/env python3
"""Audit the complete official NCI-ISBI challenge identity surface for TrueMargin M6.

This diagnostic is intentionally metadata-only. It hashes the official TCIA
challenge manifests and label archives, derives the exact 80 source
SeriesInstanceUIDs and 80 label PatientIDs across training, leaderboard, and
test partitions, and resolves those exact series in IDC for review. It does not
download DICOM images, choose a series heuristically, assign M6 cohort roles,
run registration, or fit calibration.
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
EXPECTED_TOTAL_SUBJECTS = 80
EXPECTED_TOTAL_SERIES = 80

SOURCES: dict[str, dict[str, str]] = {
    "prostate_3t": {
        "patient_prefix": "Prostate3T-01-",
        "source_collection": "Prostate-3T",
        "source_collection_doi": "10.7937/K9/TCIA.2015.QJTV5IL5",
        "idc_collection_id": "prostate_3t",
    },
    "prostate_diagnosis": {
        "patient_prefix": "ProstateDx-01-",
        "source_collection": "PROSTATE-DIAGNOSIS",
        "source_collection_doi": "10.7937/K9/TCIA.2015.FOQEUJVT",
        "idc_collection_id": "prostate_diagnosis",
    },
}

PARTITIONS: dict[str, dict[str, Any]] = {
    "training": {
        "expected_subjects": 60,
        "expected_series": 60,
        "manifest_name": "ISBI-Prostate-Challenge-Training.tcia",
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-Training.tcia?api=v2"
            )
        ],
        "label_archives": [
            {
                "name": "NCI_ISBI_Challenge-Prostate3T_Training_Segmentations.zip",
                "source_key": "prostate_3t",
                "expected_subjects": 30,
                "urls": [
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI_ISBI_Challenge-Prostate3T_Training_Segmentations.zip?api=v2&"
                        "modificationDate=1689368483744&version=1"
                    ),
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI_ISBI_Challenge-Prostate3T_Training_Segmentations.zip?api=v2"
                    ),
                ],
            },
            {
                "name": "NCI_ISBI_Challenge-ProstateDx_Training_Segmentations.zip",
                "source_key": "prostate_diagnosis",
                "expected_subjects": 30,
                "urls": [
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI_ISBI_Challenge-ProstateDx_Training_Segmentations.zip?api=v2&"
                        "modificationDate=1689368511369&version=2"
                    ),
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI_ISBI_Challenge-ProstateDx_Training_Segmentations.zip?api=v2"
                    ),
                ],
            },
        ],
    },
    "leaderboard": {
        "expected_subjects": 10,
        "expected_series": 10,
        "manifest_name": "ISBI-Prostate-Challenge-LeaderBoard.tcia",
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-LeaderBoard.tcia?api=v2"
            )
        ],
        "label_archives": [
            {
                "name": "NCI-ISBI 2013 Prostate Challenge - Leaderboard.zip",
                "source_key": None,
                "expected_subjects": 10,
                "urls": [
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Leaderboard.zip?api=v2"
                    )
                ],
            }
        ],
    },
    "test": {
        "expected_subjects": 10,
        "expected_series": 10,
        "manifest_name": "ISBI-Prostate-Challenge-Testing.tcia",
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-Testing.tcia?api=v2"
            )
        ],
        "label_archives": [
            {
                "name": "NCI-ISBI 2013 Prostate Challenge - Test.zip",
                "source_key": None,
                "expected_subjects": 10,
                "urls": [
                    (
                        "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                        "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Test.zip?api=v2"
                    )
                ],
            }
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


def parse_tcia_series_uids(manifest_bytes: bytes, *, expected_series: int) -> list[str]:
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
        raise RuntimeError("TCIA manifest contains duplicate SeriesInstanceUID values")
    if len(series_uids) != expected_series:
        raise RuntimeError(f"Expected {expected_series} series; found {len(series_uids)}")
    return series_uids


def source_key_for_patient_id(patient_id: str) -> str:
    """Map an official challenge PatientID to its TCIA source collection."""
    matches = [
        source_key
        for source_key, config in SOURCES.items()
        if patient_id.startswith(config["patient_prefix"])
    ]
    if len(matches) != 1:
        raise ValueError(f"Cannot map challenge PatientID to exactly one source: {patient_id}")
    return matches[0]


def extract_patient_id(member_name: str) -> str:
    """Extract a challenge PatientID from one official NRRD member path."""
    match = PATIENT_ID_RE.search(Path(member_name).name)
    if match is None:
        raise ValueError(f"Cannot derive challenge PatientID from NRRD member: {member_name}")
    patient_id = match.group(1)
    source_key_for_patient_id(patient_id)
    return patient_id


def enumerate_labels(
    archive_bytes: bytes,
    *,
    partition: str,
    expected_subjects: int,
    expected_source_key: str | None = None,
) -> list[dict[str, Any]]:
    """Enumerate and hash official NRRD label members from one challenge archive."""
    labels: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        members = sorted(
            (
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".nrrd")
            ),
            key=lambda info: info.filename,
        )
        for info in members:
            payload = archive.read(info)
            patient_id = extract_patient_id(info.filename)
            source_key = source_key_for_patient_id(patient_id)
            if expected_source_key is not None and source_key != expected_source_key:
                raise RuntimeError(
                    f"Archive expected source {expected_source_key} but {patient_id} "
                    f"maps to {source_key}"
                )
            labels.append(
                {
                    "patient_id": patient_id,
                    "partition": partition,
                    "source_key": source_key,
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
            f"Expected {expected_subjects} NRRD subjects for {partition}; found {len(labels)}"
        )
    return labels


def audit_label_archive(partition: str, config: dict[str, Any]) -> dict[str, Any]:
    """Download, hash, and enumerate one official challenge label archive."""
    archive_bytes, archive_url, transport_failures = download_resource(list(config["urls"]))
    labels = enumerate_labels(
        archive_bytes,
        partition=partition,
        expected_subjects=int(config["expected_subjects"]),
        expected_source_key=config.get("source_key"),
    )
    return {
        "name": config["name"],
        "expected_subjects": config["expected_subjects"],
        "expected_source_key": config.get("source_key"),
        "selected_url": archive_url,
        "transport_failures_before_success": transport_failures,
        "size_bytes": len(archive_bytes),
        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "labels": labels,
    }


def audit_partition(partition: str, config: dict[str, Any]) -> dict[str, Any]:
    """Hash one official partition manifest and all authoritative label archives."""
    manifest_bytes, manifest_url, manifest_failures = download_resource(
        list(config["manifest_urls"])
    )
    series_uids = parse_tcia_series_uids(
        manifest_bytes, expected_series=int(config["expected_series"])
    )
    archives = [
        audit_label_archive(partition, archive_config)
        for archive_config in config["label_archives"]
    ]
    labels = [label for archive in archives for label in archive["labels"]]
    patient_ids = [str(record["patient_id"]) for record in labels]
    if len(patient_ids) != int(config["expected_subjects"]):
        raise RuntimeError(
            f"Expected {config['expected_subjects']} total labels for {partition}; "
            f"found {len(patient_ids)}"
        )
    if len(patient_ids) != len(set(patient_ids)):
        raise RuntimeError(f"Partition {partition} contains duplicate label PatientIDs")

    source_counts: dict[str, int] = {source_key: 0 for source_key in SOURCES}
    for label in labels:
        source_counts[str(label["source_key"])] += 1

    return {
        "partition": partition,
        "expected_subjects": config["expected_subjects"],
        "expected_series": config["expected_series"],
        "manifest": {
            "name": config["manifest_name"],
            "selected_url": manifest_url,
            "transport_failures_before_success": manifest_failures,
            "size_bytes": len(manifest_bytes),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "series_uids": series_uids,
        },
        "label_archives": archives,
        "labels": labels,
        "patient_ids": sorted(patient_ids),
        "source_counts": source_counts,
    }


def build_label_index(partitions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Create a unique patient identity index across all official partitions."""
    label_index: dict[str, dict[str, Any]] = {}
    for partition_name, partition in partitions.items():
        for label in partition["labels"]:
            patient_id = str(label["patient_id"])
            if patient_id in label_index:
                prior = label_index[patient_id]["partition"]
                raise RuntimeError(
                    f"PatientID {patient_id} appears in multiple challenge partitions: "
                    f"{prior}, {partition_name}"
                )
            label_index[patient_id] = label
    return label_index


def query_idc_official_series(series_uids: list[str]) -> dict[str, Any]:
    """Resolve the exact official challenge series UIDs in current IDC metadata."""
    response = _post_json(
        f"{IDC_REST_BASE}/cohort/manifest",
        {
            "filters": {
                "terms": {
                    "collection_id": [config["idc_collection_id"] for config in SOURCES.values()],
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
    label_index: dict[str, dict[str, Any]],
    official_series_uids: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cross-check exact official manifest series against all challenge labels."""
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
        patient_id: [] for patient_id in sorted(label_index)
    }
    unexpected_patient_ids: set[str] = set()
    collection_mismatches: list[dict[str, str]] = []

    for uid in official_series_uids:
        matches = rows_by_uid[uid]
        if len(matches) != 1:
            continue
        row = matches[0]
        patient_id = str(row.get("PatientID", ""))
        label = label_index.get(patient_id)
        if label is None:
            unexpected_patient_ids.add(patient_id)
            continue

        source_key = str(label["source_key"])
        expected_collection_id = SOURCES[source_key]["idc_collection_id"]
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
        mapping[patient_id].append(
            {
                "partition": label["partition"],
                "source_key": source_key,
                "series": serialize_series(row),
            }
        )

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


def validate_historical_training_conditions(
    label_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Verify known TCIA corrections remain explicit in the 80-subject identity record."""
    corrected = label_index.get("ProstateDx-01-0006")
    mismatch_case = label_index.get("ProstateDx-01-0055")
    patient_id_fix = label_index.get("ProstateDx-01-0035")
    issues: list[str] = []

    if corrected is None or corrected.get("corrected_label_filename") is not True:
        issues.append("corrected ProstateDx-01-0006 label filename was not preserved")
    if mismatch_case is None:
        issues.append("documented ProstateDx-01-0055 image/label mismatch case is missing")
    if patient_id_fix is None:
        issues.append("documented ProstateDx-01-0035 identity-correction case is missing")

    return {
        "prostate_dx_0006_corrected_label_preserved": not any("0006" in item for item in issues),
        "prostate_dx_0055_preserved": not any("0055" in item for item in issues),
        "prostate_dx_0035_preserved": not any("0035" in item for item in issues),
        "issues": issues,
    }


def build_audit() -> dict[str, Any]:
    """Build the complete 80-subject metadata-only challenge identity audit."""
    partitions = {
        partition_name: audit_partition(partition_name, config)
        for partition_name, config in PARTITIONS.items()
    }
    label_index = build_label_index(partitions)
    all_patient_ids = sorted(label_index)
    if len(all_patient_ids) != EXPECTED_TOTAL_SUBJECTS:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_SUBJECTS} unique challenge PatientIDs; "
            f"found {len(all_patient_ids)}"
        )

    all_series_uids = [
        uid for partition in partitions.values() for uid in partition["manifest"]["series_uids"]
    ]
    if len(all_series_uids) != EXPECTED_TOTAL_SERIES:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_SERIES} official series UIDs; found {len(all_series_uids)}"
        )
    if len(all_series_uids) != len(set(all_series_uids)):
        raise RuntimeError("Official challenge manifests contain duplicate UIDs across partitions")

    historical_conditions = validate_historical_training_conditions(label_index)
    idc_response = query_idc_official_series(all_series_uids)
    rows = idc_response["series"]
    resolution = map_official_series_to_labels(label_index, all_series_uids, rows)
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
    if historical_conditions["issues"]:
        issues["historical_training_conditions"] = historical_conditions["issues"]
    status = "complete" if not issues else "incomplete"

    source_totals = {source_key: 0 for source_key in SOURCES}
    for label in label_index.values():
        source_totals[str(label["source_key"])] += 1

    return {
        "schema_version": 2,
        "milestone": "M6",
        "audit": "external-input-identity",
        "status": status,
        "challenge": {
            "name": CHALLENGE_NAME,
            "doi": CHALLENGE_DOI,
            "subjects_expected": EXPECTED_TOTAL_SUBJECTS,
            "series_expected": EXPECTED_TOTAL_SERIES,
            "partitions": {
                name: {
                    "subjects_expected": config["expected_subjects"],
                    "series_expected": config["expected_series"],
                }
                for name, config in PARTITIONS.items()
            },
        },
        "authorization_boundary": {
            "result_bearing_authorized": False,
            "registration_authorized": False,
            "calibration_fit_authorized": False,
            "split_assignment_authorized": False,
            "dicom_download_performed": False,
            "heuristic_source_series_selection_performed": False,
        },
        "sources": SOURCES,
        "partitions": partitions,
        "historical_training_conditions": historical_conditions,
        "idc_resolution": {
            "warnings": idc_response.get("warnings", []),
            "truncated": idc_response.get("truncated", False),
            "series_rows": len(rows),
            **resolution,
        },
        "summary": {
            "unique_patient_ids": len(all_patient_ids),
            "official_series_uids": len(all_series_uids),
            "idc_series_rows": len(rows),
            "source_totals": source_totals,
            "partition_source_counts": {
                name: partition["source_counts"] for name, partition in partitions.items()
            },
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
            "schema_version": 2,
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
    if "unique_patient_ids" in summary:
        print(f"M6_CHALLENGE_PATIENT_IDS={summary['unique_patient_ids']}")
    if "official_series_uids" in summary:
        print(f"M6_CHALLENGE_SERIES_UIDS={summary['official_series_uids']}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
