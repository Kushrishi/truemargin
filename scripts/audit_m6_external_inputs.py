#!/usr/bin/env python3
"""Audit the official NCI-ISBI prostate challenge identity surface for TrueMargin M6.

This diagnostic is metadata-only. It establishes exact challenge-partition image
identity from official TCIA partition authorities before any M6 cohort roles are
assigned:

* Training: official TCIA shared list (60 series)
* Leaderboard: official TCIA shared list (10 series)
* Test: official TCIA test manifest (10 series)

The three sets must be pairwise disjoint and total 80 series. Exact UIDs are then
resolved in IDC metadata without downloading DICOM payloads. Official NRRD archives
are audited separately because annotation identity is required before ROI/geometry
work, but annotation transport must not erase otherwise valid image-identity evidence.

No M6 cohort roles are assigned, no DICOM image payloads are downloaded, no
registration is run, and no calibration is fit.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CHALLENGE_NAME = "NCI-ISBI 2013 Challenge: Automated Segmentation of Prostate Structures"
CHALLENGE_DOI = "10.7937/K9/TCIA.2015.zF0vlOPv"
CURRENT_ANALYSIS_PAGE = (
    "https://www.cancerimagingarchive.net/analysis-result/isbi-mr-prostate-2013/"
)
TCIA_PUBLIC_BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
IDC_REST_BASE = "https://api.imaging.datacommons.cancer.gov/v3"
EXPECTED_TOTAL_SUBJECTS = 80
EXPECTED_TOTAL_SERIES = 80
API_ATTEMPTS = 3
API_TIMEOUT_SECONDS = 45
ATTACHMENT_TIMEOUT_SECONDS = 60
NETWORK_BACKOFF_SECONDS = (2, 5)

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
        "shared_list_name": "ISBI Prostate Challenge - Training",
        "manifest_name": "ISBI-Prostate-Challenge-Training.tcia",
        "manifest_required": False,
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-Training.tcia?api=v2"
            )
        ],
        "label_archive_name": "NCI-ISBI 2013 Prostate Challenge - Training.zip",
        "label_archive_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Training.zip?api=v2"
            )
        ],
    },
    "leaderboard": {
        "expected_subjects": 10,
        "expected_series": 10,
        "shared_list_name": "ISBI Prostate Challenge - Leader Board",
        "manifest_name": "ISBI-Prostate-Challenge-LeaderBoard.tcia",
        "manifest_required": False,
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-LeaderBoard.tcia?api=v2"
            )
        ],
        "label_archive_name": "NCI-ISBI 2013 Prostate Challenge - Leaderboard.zip",
        "label_archive_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Leaderboard.zip?api=v2"
            )
        ],
    },
    "test": {
        "expected_subjects": 10,
        "expected_series": 10,
        "shared_list_name": None,
        "manifest_name": "ISBI-Prostate-Challenge-Testing.tcia",
        "manifest_required": True,
        "manifest_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "ISBI-Prostate-Challenge-Testing.tcia?api=v2"
            )
        ],
        "label_archive_name": "NCI-ISBI 2013 Prostate Challenge - Test.zip",
        "label_archive_urls": [
            (
                "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
                "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Test.zip?api=v2"
            )
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


class TransportUnavailable(RuntimeError):
    """Raised after a network resource exhausts its declared transport policy."""

    def __init__(self, url: str, failures: list[dict[str, Any]]):
        self.url = url
        self.failures = failures
        super().__init__(f"Transport unavailable for {url}: {json.dumps(failures, sort_keys=True)}")


def _serialize_transport_error(exc: BaseException) -> dict[str, Any]:
    record: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)}
    if isinstance(exc, urllib.error.HTTPError):
        record["http_status"] = int(exc.code)
        record["http_reason"] = str(exc.reason)
        try:
            body = exc.read(512).decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        if body:
            record["response_excerpt"] = body
    elif isinstance(exc, urllib.error.URLError):
        record["reason"] = str(exc.reason)
    return record


def _request(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = API_TIMEOUT_SECONDS,
    attempts: int = API_ATTEMPTS,
) -> tuple[bytes, list[dict[str, Any]]]:
    request_headers = {"User-Agent": "TrueMargin-M6-Audit/1.0"}
    if headers:
        request_headers.update(headers)

    failures: list[dict[str, Any]] = []
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            data=data,
            headers=request_headers,
            method="POST" if data is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), failures
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            failure = _serialize_transport_error(exc)
            failure["attempt"] = attempt + 1
            failures.append(failure)
            if attempt + 1 < attempts:
                time.sleep(NETWORK_BACKOFF_SECONDS[min(attempt, len(NETWORK_BACKOFF_SECONDS) - 1)])
    raise TransportUnavailable(url, failures)


def _decode_json(raw: bytes, *, source: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Expected JSON response from {source}") from exc


def _get_json(url: str) -> tuple[Any, dict[str, Any]]:
    raw, failures = _request(url)
    return _decode_json(raw, source=url), {
        "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "transport": "urllib",
        "transport_failures_before_success": failures,
    }


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw, _ = _request(
        url,
        data=json.dumps(payload, sort_keys=True).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    decoded = _decode_json(raw, source=url)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return decoded


def _curl_download(url: str) -> tuple[bytes, dict[str, Any]]:
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("curl is not available on this runner")
    command = [
        curl,
        "--location",
        "--fail-with-body",
        "--silent",
        "--show-error",
        "--retry",
        "2",
        "--retry-all-errors",
        "--connect-timeout",
        "10",
        "--max-time",
        str(ATTACHMENT_TIMEOUT_SECONDS),
        "--user-agent",
        "TrueMargin-M6-Audit/1.0",
        url,
    ]
    completed = subprocess.run(command, check=False, capture_output=True)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"curl exit {completed.returncode}: {stderr[:1000]}")
    return completed.stdout, {"transport": "curl", "curl_exit_code": completed.returncode}


def _download_attachment(urls: list[str]) -> tuple[bytes, str, dict[str, Any]]:
    """Download an official TCIA attachment with an auditable curl/urllib fallback."""
    failures: list[dict[str, Any]] = []
    for url in urls:
        try:
            payload, metadata = _curl_download(url)
            return payload, url, {**metadata, "failures_before_success": failures}
        except RuntimeError as exc:
            failures.append({"url": url, "transport": "curl", "error": str(exc)})

        try:
            payload, urllib_failures = _request(url, attempts=1, timeout=ATTACHMENT_TIMEOUT_SECONDS)
            return payload, url, {
                "transport": "urllib",
                "failures_before_success": failures + urllib_failures,
            }
        except TransportUnavailable as exc:
            failures.append({"url": url, "transport": "urllib", "attempts": exc.failures})

    raise TransportUnavailable(";".join(urls), failures)


def _series_uid_from_row(row: dict[str, Any]) -> str:
    for key in ("seriesInstanceUID", "SeriesInstanceUID"):
        value = row.get(key)
        if isinstance(value, str) and SERIES_UID_RE.fullmatch(value):
            return value
    raise RuntimeError(f"Series row has no valid SeriesInstanceUID: {sorted(row)}")


def _validate_uid_rows(
    rows: Any, *, expected: int, source: str
) -> tuple[list[str], list[dict[str, Any]]]:
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"Expected a JSON list of objects from {source}")
    typed_rows = [dict(row) for row in rows]
    uids = [_series_uid_from_row(row) for row in typed_rows]
    if len(uids) != len(set(uids)):
        raise RuntimeError(f"Duplicate SeriesInstanceUID values returned by {source}")
    if len(uids) != expected:
        raise RuntimeError(f"Expected {expected} series from {source}; found {len(uids)}")
    return uids, typed_rows


def query_shared_list(name: str, *, expected: int) -> dict[str, Any]:
    """Return an official challenge shared-list membership from current TCIA Search API."""
    url = f"{TCIA_PUBLIC_BASE}/getContentsByName?{urllib.parse.urlencode({'name': name})}"
    decoded, provenance = _get_json(url)
    uids, rows = _validate_uid_rows(decoded, expected=expected, source=f"shared list {name!r}")
    keep_fields = (
        "SeriesInstanceUID",
        "seriesInstanceUID",
        "PatientID",
        "Collection",
        "Modality",
        "Manufacturer",
        "ManufacturerModelName",
        "SeriesDescription",
        "ProtocolName",
        "ImageCount",
    )
    compact_rows = [{key: row.get(key) for key in keep_fields if key in row} for row in rows]
    return {
        "status": "complete",
        "authority": "TCIA NBIA Search REST getContentsByName",
        "shared_list_name": name,
        "expected_series": expected,
        "series_uids": sorted(uids),
        "rows": compact_rows,
        "response": provenance,
    }


def parse_tcia_series_uids(manifest_bytes: bytes, *, expected_series: int) -> list[str]:
    """Parse an official NBIA ``.tcia`` manifest into exact series UIDs."""
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


def audit_manifest(partition: str) -> dict[str, Any]:
    config = PARTITIONS[partition]
    try:
        payload, selected_url, transport = _download_attachment(list(config["manifest_urls"]))
    except TransportUnavailable as exc:
        return {
            "status": "transport_unavailable",
            "required": bool(config["manifest_required"]),
            "name": config["manifest_name"],
            "transport_failures": exc.failures,
        }
    try:
        parsed = parse_tcia_series_uids(payload, expected_series=int(config["expected_series"]))
    except Exception as exc:
        return {
            "status": "invalid",
            "required": bool(config["manifest_required"]),
            "name": config["manifest_name"],
            "selected_url": selected_url,
            "transport": transport,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "status": "complete",
        "required": bool(config["manifest_required"]),
        "name": config["manifest_name"],
        "selected_url": selected_url,
        "transport": transport,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "series_uids": sorted(parsed),
    }


def validate_partition_uids(partition_uids: dict[str, list[str]]) -> None:
    if set(partition_uids) != set(PARTITIONS):
        raise RuntimeError(f"Unexpected partition keys: {sorted(partition_uids)}")
    for partition, uids in partition_uids.items():
        expected = int(PARTITIONS[partition]["expected_series"])
        if len(uids) != expected or len(set(uids)) != expected:
            raise RuntimeError(
                f"Partition {partition} must contain {expected} unique series; found {len(set(uids))}"
            )
    pairs = (("training", "leaderboard"), ("training", "test"), ("leaderboard", "test"))
    for left, right in pairs:
        overlap = sorted(set(partition_uids[left]) & set(partition_uids[right]))
        if overlap:
            raise RuntimeError(f"Challenge partitions {left}/{right} overlap: {overlap[:3]}")
    union = {uid for uids in partition_uids.values() for uid in uids}
    if len(union) != EXPECTED_TOTAL_SERIES:
        raise RuntimeError(
            f"Challenge partition union must contain {EXPECTED_TOTAL_SERIES} series; found {len(union)}"
        )


def source_key_for_patient_id(patient_id: str) -> str:
    matches = [
        source_key
        for source_key, config in SOURCES.items()
        if patient_id.startswith(config["patient_prefix"])
    ]
    if len(matches) != 1:
        raise ValueError(f"Cannot map challenge PatientID to exactly one source: {patient_id}")
    return matches[0]


def query_idc_official_series(series_uids: list[str]) -> dict[str, Any]:
    """Resolve exact challenge UIDs in current IDC metadata without downloading DICOM."""
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
    return {field: row.get(field) for field in CANDIDATE_FIELDS}


def map_series_identity(
    partition_uids: dict[str, list[str]], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Resolve one UID -> one patient/source/partition and preserve acquisition metadata."""
    partition_for_uid = {
        uid: partition for partition, uids in partition_uids.items() for uid in uids
    }
    expected_uids = set(partition_for_uid)
    rows_by_uid: dict[str, list[dict[str, Any]]] = {uid: [] for uid in expected_uids}
    unexpected_uids: set[str] = set()
    for row in rows:
        uid = str(row.get("SeriesInstanceUID", ""))
        if uid in rows_by_uid:
            rows_by_uid[uid].append(row)
        else:
            unexpected_uids.add(uid)

    missing_uids = sorted(uid for uid, matches in rows_by_uid.items() if not matches)
    duplicate_uids = sorted(uid for uid, matches in rows_by_uid.items() if len(matches) > 1)
    series_records: list[dict[str, Any]] = []
    source_collection_mismatches: list[dict[str, str]] = []
    invalid_patient_ids: list[dict[str, str]] = []

    for uid in sorted(expected_uids):
        matches = rows_by_uid[uid]
        if len(matches) != 1:
            continue
        row = matches[0]
        patient_id = str(row.get("PatientID", ""))
        try:
            source_key = source_key_for_patient_id(patient_id)
        except ValueError:
            invalid_patient_ids.append({"series_uid": uid, "patient_id": patient_id})
            continue
        expected_collection = SOURCES[source_key]["idc_collection_id"]
        observed_collection = row.get("collection_id")
        if observed_collection is not None and str(observed_collection) != expected_collection:
            source_collection_mismatches.append(
                {
                    "series_uid": uid,
                    "patient_id": patient_id,
                    "expected_collection_id": expected_collection,
                    "observed_collection_id": str(observed_collection),
                }
            )
        series_records.append(
            {
                "series_uid": uid,
                "patient_id": patient_id,
                "partition": partition_for_uid[uid],
                "source_key": source_key,
                "series": serialize_series(row),
            }
        )

    patient_ids = [record["patient_id"] for record in series_records]
    duplicate_patient_ids = sorted(
        {patient for patient in patient_ids if patient_ids.count(patient) > 1}
    )
    partition_patient_ids: dict[str, list[str]] = {
        partition: sorted(
            record["patient_id"] for record in series_records if record["partition"] == partition
        )
        for partition in PARTITIONS
    }
    partition_source_counts: dict[str, dict[str, int]] = {}
    for partition in PARTITIONS:
        counts = {source_key: 0 for source_key in SOURCES}
        for record in series_records:
            if record["partition"] == partition:
                counts[record["source_key"]] += 1
        partition_source_counts[partition] = counts

    issues: dict[str, Any] = {}
    for key, value in (
        ("missing_series_uids_in_idc", missing_uids),
        ("duplicate_series_uids_in_idc", duplicate_uids),
        ("unexpected_series_uids_from_idc", sorted(unexpected_uids)),
        ("invalid_patient_ids", invalid_patient_ids),
        ("duplicate_patient_ids", duplicate_patient_ids),
        ("source_collection_mismatches", source_collection_mismatches),
    ):
        if value:
            issues[key] = value
    if len(series_records) != EXPECTED_TOTAL_SERIES:
        issues["resolved_series_count"] = len(series_records)
    if len(set(patient_ids)) != EXPECTED_TOTAL_SUBJECTS:
        issues["unique_patient_count"] = len(set(patient_ids))
    for partition, patient_list in partition_patient_ids.items():
        expected = int(PARTITIONS[partition]["expected_subjects"])
        if len(patient_list) != expected:
            issues.setdefault("partition_patient_counts", {})[partition] = len(patient_list)

    return {
        "status": "complete" if not issues else "incomplete",
        "series_records": series_records,
        "partition_patient_ids": partition_patient_ids,
        "partition_source_counts": partition_source_counts,
        "issues": issues,
    }


def extract_patient_id(member_name: str) -> str:
    match = PATIENT_ID_RE.search(Path(member_name).name)
    if match is None:
        raise ValueError(f"Cannot derive challenge PatientID from NRRD member: {member_name}")
    patient_id = match.group(1)
    source_key_for_patient_id(patient_id)
    return patient_id


def enumerate_labels(
    archive_bytes: bytes, *, partition: str, expected_subjects: int
) -> list[dict[str, Any]]:
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
            labels.append(
                {
                    "patient_id": patient_id,
                    "partition": partition,
                    "source_key": source_key_for_patient_id(patient_id),
                    "archive_member": info.filename,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
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


def audit_label_archive(partition: str) -> dict[str, Any]:
    config = PARTITIONS[partition]
    try:
        payload, selected_url, transport = _download_attachment(list(config["label_archive_urls"]))
    except TransportUnavailable as exc:
        return {
            "status": "transport_unavailable",
            "name": config["label_archive_name"],
            "expected_subjects": config["expected_subjects"],
            "transport_failures": exc.failures,
        }
    try:
        labels = enumerate_labels(
            payload,
            partition=partition,
            expected_subjects=int(config["expected_subjects"]),
        )
    except Exception as exc:
        return {
            "status": "invalid",
            "name": config["label_archive_name"],
            "expected_subjects": config["expected_subjects"],
            "selected_url": selected_url,
            "transport": transport,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "status": "complete",
        "name": config["label_archive_name"],
        "expected_subjects": config["expected_subjects"],
        "selected_url": selected_url,
        "transport": transport,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "labels": labels,
    }


def validate_historical_conditions(label_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required = (
        "ProstateDx-01-0006",
        "ProstateDx-01-0035",
        "ProstateDx-01-0055",
    )
    missing = [patient_id for patient_id in required if patient_id not in label_index]
    return {
        "prostate_dx_0006_present_in_current_official_training_archive": (
            "ProstateDx-01-0006" not in missing
        ),
        "prostate_dx_0035_preserved": "ProstateDx-01-0035" not in missing,
        "prostate_dx_0055_preserved": "ProstateDx-01-0055" not in missing,
        "missing": missing,
    }


def audit_annotations(partition_patient_ids: dict[str, list[str]]) -> dict[str, Any]:
    partition_records = {partition: audit_label_archive(partition) for partition in PARTITIONS}
    statuses = {partition: record["status"] for partition, record in partition_records.items()}
    if any(status == "invalid" for status in statuses.values()):
        return {
            "status": "incomplete",
            "required_before_result_bearing_m6": True,
            "analysis_page": CURRENT_ANALYSIS_PAGE,
            "partitions": partition_records,
            "issues": {"invalid_archive": statuses},
        }
    if any(status != "complete" for status in statuses.values()):
        return {
            "status": "transport_unavailable",
            "required_before_result_bearing_m6": True,
            "analysis_page": CURRENT_ANALYSIS_PAGE,
            "partitions": partition_records,
            "issues": {},
        }

    label_index: dict[str, dict[str, Any]] = {}
    issues: dict[str, Any] = {}
    for partition, record in partition_records.items():
        labels = record["labels"]
        observed = sorted(str(label["patient_id"]) for label in labels)
        expected = sorted(partition_patient_ids[partition])
        if observed != expected:
            issues.setdefault("image_annotation_patient_mismatch", {})[partition] = {
                "missing_annotations": sorted(set(expected) - set(observed)),
                "unexpected_annotations": sorted(set(observed) - set(expected)),
            }
        for label in labels:
            patient_id = str(label["patient_id"])
            if patient_id in label_index:
                issues.setdefault("cross_partition_duplicate_patient_ids", []).append(patient_id)
            label_index[patient_id] = label

    if len(label_index) != EXPECTED_TOTAL_SUBJECTS:
        issues["unique_label_patient_count"] = len(label_index)
    historical = validate_historical_conditions(label_index)
    if historical["missing"]:
        issues["historical_conditions"] = historical["missing"]

    return {
        "status": "complete" if not issues else "incomplete",
        "required_before_result_bearing_m6": True,
        "analysis_page": CURRENT_ANALYSIS_PAGE,
        "partitions": partition_records,
        "historical_conditions": historical,
        "issues": issues,
    }


def audit_image_identity() -> dict[str, Any]:
    issues: dict[str, Any] = {}
    authority: dict[str, Any] = {}
    partition_uids: dict[str, list[str]] = {}

    for partition in ("training", "leaderboard"):
        config = PARTITIONS[partition]
        try:
            record = query_shared_list(
                str(config["shared_list_name"]), expected=int(config["expected_series"])
            )
            authority[f"{partition}_shared_list"] = record
            partition_uids[partition] = list(record["series_uids"])
        except Exception as exc:
            authority[f"{partition}_shared_list"] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            issues[f"{partition}_shared_list"] = str(exc)

    manifest_records = {partition: audit_manifest(partition) for partition in PARTITIONS}
    authority["manifests"] = manifest_records
    test_manifest = manifest_records["test"]
    if test_manifest["status"] == "complete":
        partition_uids["test"] = list(test_manifest["series_uids"])
    else:
        issues["test_manifest"] = test_manifest

    if set(partition_uids) == set(PARTITIONS):
        try:
            validate_partition_uids(partition_uids)
        except RuntimeError as exc:
            issues["partition_invariants"] = str(exc)

        for partition in ("training", "leaderboard"):
            manifest = manifest_records[partition]
            if manifest["status"] == "complete":
                if set(manifest["series_uids"]) != set(partition_uids[partition]):
                    issues[f"{partition}_manifest_crosscheck"] = "manifest/shared-list UID mismatch"
            elif manifest["status"] == "invalid":
                issues[f"{partition}_manifest_crosscheck"] = manifest

    if issues or set(partition_uids) != set(PARTITIONS):
        return {
            "status": "incomplete",
            "authority": authority,
            "partition_series_uids": partition_uids,
            "idc_resolution": None,
            "issues": issues,
        }

    all_uids = sorted(uid for uids in partition_uids.values() for uid in uids)
    try:
        idc_response = query_idc_official_series(all_uids)
        mapping = map_series_identity(partition_uids, idc_response["series"])
    except Exception as exc:
        return {
            "status": "incomplete",
            "authority": authority,
            "partition_series_uids": partition_uids,
            "idc_resolution": {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            "issues": {"idc_resolution": str(exc)},
        }

    return {
        "status": mapping["status"],
        "authority": authority,
        "partition_series_uids": partition_uids,
        "idc_resolution": {
            "warnings": idc_response.get("warnings", []),
            "truncated": idc_response.get("truncated", False),
            "series_rows": len(idc_response["series"]),
            **mapping,
        },
        "issues": mapping["issues"],
    }


def build_audit() -> dict[str, Any]:
    """Build the M6 pre-result identity audit while preserving partial gate evidence."""
    image_identity = audit_image_identity()
    if image_identity["status"] == "complete":
        partition_patient_ids = image_identity["idc_resolution"]["partition_patient_ids"]
        annotations = audit_annotations(partition_patient_ids)
    else:
        annotations = {
            "status": "blocked_on_image_identity",
            "required_before_result_bearing_m6": True,
            "analysis_page": CURRENT_ANALYSIS_PAGE,
            "partitions": {},
            "issues": {},
        }
    overall_complete = (
        image_identity["status"] == "complete" and annotations["status"] == "complete"
    )

    return {
        "schema_version": 4,
        "milestone": "M6",
        "audit": "external-input-identity",
        "status": "complete" if overall_complete else "incomplete",
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
        "image_identity": image_identity,
        "annotation_identity": annotations,
        "summary": {
            "image_identity_status": image_identity["status"],
            "annotation_identity_status": annotations["status"],
            "identity_freeze_ready": overall_complete,
            "result_bearing_m6_authorized": False,
        },
    }


def failure_record(exc: BaseException) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 4,
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
    if isinstance(exc, TransportUnavailable):
        record["transport_failure"] = {"url": exc.url, "attempts": exc.failures}
    return record


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
        result = failure_record(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M6_INPUT_IDENTITY_AUDIT_STATUS={result['status'].upper()}")
    summary = result.get("summary", {})
    if summary:
        print(f"M6_IMAGE_IDENTITY_STATUS={summary.get('image_identity_status', 'UNKNOWN').upper()}")
        print(
            "M6_ANNOTATION_IDENTITY_STATUS="
            f"{summary.get('annotation_identity_status', 'UNKNOWN').upper()}"
        )
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
