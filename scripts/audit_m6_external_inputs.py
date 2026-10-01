#!/usr/bin/env python3
"""Audit the official NCI-ISBI prostate challenge identity surface for TrueMargin M6.

This diagnostic is metadata-only. Image-series identity is established from current
TCIA APIs rather than depending on legacy Confluence attachment transport:

1. the analysis DOI provides the complete source-series universe;
2. the historical official training and leaderboard shared lists provide partition
   membership; and
3. the test partition is the exact disjoint remainder.

Official segmentation archives are audited separately because annotation transport is
required for ROI/geometry work but is not required to establish image-series identity.
No DICOM image payloads are downloaded, no M6 cohort roles are assigned, no
registration is run, and no calibration is fit.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CHALLENGE_NAME = "NCI-ISBI 2013 Challenge: Automated Segmentation of Prostate Structures"
CHALLENGE_DOI = "10.7937/K9/TCIA.2015.zF0vlOPv"
CHALLENGE_DOI_URL = f"https://doi.org/{CHALLENGE_DOI}"
CURRENT_ANALYSIS_PAGE = (
    "https://www.cancerimagingarchive.net/analysis-result/isbi-mr-prostate-2013/"
)
TCIA_PUBLIC_BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
TCIA_ADVANCED_BASE = "https://services.cancerimagingarchive.net/nbia-api"
TCIA_TOKEN_URL = f"{TCIA_ADVANCED_BASE}/oauth/token"
TCIA_DOI_SERIES_URL = f"{TCIA_ADVANCED_BASE}/services/getCollectionOrSeriesForDOI"
IDC_REST_BASE = "https://api.imaging.datacommons.cancer.gov/v3"
EXPECTED_TOTAL_SUBJECTS = 80
EXPECTED_TOTAL_SERIES = 80
API_ATTEMPTS = 3
API_TIMEOUT_SECONDS = 45
LEGACY_ATTEMPTS = 1
LEGACY_TIMEOUT_SECONDS = 12
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
        "legacy_manifest_name": "ISBI-Prostate-Challenge-Training.tcia",
        "legacy_manifest_urls": [
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
                    )
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
                    )
                ],
            },
        ],
    },
    "leaderboard": {
        "expected_subjects": 10,
        "expected_series": 10,
        "shared_list_name": "ISBI Prostate Challenge - Leader Board",
        "legacy_manifest_name": "ISBI-Prostate-Challenge-LeaderBoard.tcia",
        "legacy_manifest_urls": [
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
        "shared_list_name": None,
        "legacy_manifest_name": "ISBI-Prostate-Challenge-Testing.tcia",
        "legacy_manifest_urls": [
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


class TransportUnavailable(RuntimeError):
    """Raised after a network resource exhausts its declared retry policy."""

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
    request_headers = {"User-Agent": "truemargin-research/0.1"}
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
        "transport_failures_before_success": failures,
    }


def _post_form_json(
    url: str,
    fields: dict[str, str],
    *,
    bearer_token: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if bearer_token is not None:
        headers["Authorization"] = f"Bearer {bearer_token}"
    raw, failures = _request(url, data=data, headers=headers)
    return _decode_json(raw, source=url), {
        "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
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


def get_nbia_guest_token() -> tuple[str, dict[str, Any]]:
    """Request TCIA's documented public-data guest token without persisting it."""
    decoded, provenance = _post_form_json(
        TCIA_TOKEN_URL,
        {
            "username": "nbia_guest",
            "password": "",
            "client_id": "NBIA",
            "grant_type": "password",
        },
    )
    if not isinstance(decoded, dict) or not isinstance(decoded.get("access_token"), str):
        raise RuntimeError("TCIA guest-token response did not contain access_token")
    token = str(decoded["access_token"])
    safe = {
        **provenance,
        "token_persisted": False,
        "expires_in": decoded.get("expires_in"),
        "scope": decoded.get("scope"),
    }
    return token, safe


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


def query_doi_series() -> dict[str, Any]:
    """Return the exact 80-series universe associated with the official analysis DOI."""
    token, token_provenance = get_nbia_guest_token()
    decoded, provenance = _post_form_json(
        TCIA_DOI_SERIES_URL,
        {"DOI": CHALLENGE_DOI_URL, "CollectionOrSeries": "series"},
        bearer_token=token,
    )
    uids, rows = _validate_uid_rows(decoded, expected=EXPECTED_TOTAL_SERIES, source="TCIA DOI API")
    collections = sorted(
        {
            str(row.get("collection"))
            for row in rows
            if row.get("collection") not in (None, "", "null")
        }
    )
    return {
        "authority": "TCIA NBIA Advanced REST getCollectionOrSeriesForDOI",
        "doi": CHALLENGE_DOI_URL,
        "expected_series": EXPECTED_TOTAL_SERIES,
        "series_uids": sorted(uids),
        "reported_collections": collections,
        "response": provenance,
        "authentication": token_provenance,
    }


def query_shared_list(name: str, *, expected: int) -> dict[str, Any]:
    """Return one official historical challenge shared-list membership from current TCIA API."""
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
        "authority": "TCIA NBIA Search REST getContentsByName",
        "shared_list_name": name,
        "expected_series": expected,
        "series_uids": sorted(uids),
        "rows": compact_rows,
        "response": provenance,
    }


def derive_partition_uids(
    doi_uids: list[str], training_uids: list[str], leaderboard_uids: list[str]
) -> dict[str, list[str]]:
    """Freeze partition identity from authoritative pre-outcome series sets."""
    universe = set(doi_uids)
    training = set(training_uids)
    leaderboard = set(leaderboard_uids)
    if len(universe) != EXPECTED_TOTAL_SERIES:
        raise RuntimeError(f"DOI universe must contain {EXPECTED_TOTAL_SERIES} unique series")
    if len(training) != int(PARTITIONS["training"]["expected_series"]):
        raise RuntimeError("Training shared-list series count is not 60")
    if len(leaderboard) != int(PARTITIONS["leaderboard"]["expected_series"]):
        raise RuntimeError("Leaderboard shared-list series count is not 10")
    if not training <= universe:
        raise RuntimeError("Training shared-list contains series outside DOI universe")
    if not leaderboard <= universe:
        raise RuntimeError("Leaderboard shared-list contains series outside DOI universe")
    overlap = sorted(training & leaderboard)
    if overlap:
        raise RuntimeError(f"Training and leaderboard shared lists overlap: {overlap[:3]}")
    test = universe - training - leaderboard
    if len(test) != int(PARTITIONS["test"]["expected_series"]):
        raise RuntimeError(f"Expected 10 test remainder series; found {len(test)}")
    return {
        "training": sorted(training),
        "leaderboard": sorted(leaderboard),
        "test": sorted(test),
    }


def parse_tcia_series_uids(manifest_bytes: bytes, *, expected_series: int) -> list[str]:
    """Parse a legacy NBIA ``.tcia`` manifest for optional provenance cross-checking."""
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


def _download_legacy(urls: list[str]) -> tuple[bytes, str, list[dict[str, Any]]]:
    all_failures: list[dict[str, Any]] = []
    for url in urls:
        try:
            payload, failures = _request(
                url,
                timeout=LEGACY_TIMEOUT_SECONDS,
                attempts=LEGACY_ATTEMPTS,
            )
            return payload, url, all_failures + failures
        except TransportUnavailable as exc:
            all_failures.append({"url": url, "attempts": exc.failures})
    raise TransportUnavailable(";".join(urls), all_failures)


def audit_legacy_manifest_crosscheck(
    partition: str, authoritative_uids: list[str]
) -> dict[str, Any]:
    """Cross-check legacy manifest if transport happens to be available; absence is non-fatal."""
    config = PARTITIONS[partition]
    try:
        payload, selected_url, failures = _download_legacy(list(config["legacy_manifest_urls"]))
        parsed = parse_tcia_series_uids(payload, expected_series=int(config["expected_series"]))
        matches = set(parsed) == set(authoritative_uids)
        return {
            "status": "complete" if matches else "mismatch",
            "required_for_image_identity": False,
            "name": config["legacy_manifest_name"],
            "selected_url": selected_url,
            "transport_failures_before_success": failures,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "matches_api_identity": matches,
            "series_uids": sorted(parsed),
        }
    except TransportUnavailable as exc:
        return {
            "status": "transport_unavailable",
            "required_for_image_identity": False,
            "name": config["legacy_manifest_name"],
            "transport_failures": exc.failures,
        }
    except Exception as exc:
        return {
            "status": "invalid",
            "required_for_image_identity": False,
            "name": config["legacy_manifest_name"],
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


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
    """Resolve the authoritative 80 UID set in current IDC metadata without downloading DICOM."""
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
            record["patient_id"]
            for record in series_records
            if record["partition"] == partition
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
    archive_bytes: bytes,
    *,
    partition: str,
    expected_subjects: int,
    expected_source_key: str | None = None,
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
    try:
        payload, selected_url, failures = _download_legacy(list(config["urls"]))
    except TransportUnavailable as exc:
        return {
            "status": "transport_unavailable",
            "name": config["name"],
            "expected_subjects": config["expected_subjects"],
            "expected_source_key": config.get("source_key"),
            "transport_failures": exc.failures,
        }
    try:
        labels = enumerate_labels(
            payload,
            partition=partition,
            expected_subjects=int(config["expected_subjects"]),
            expected_source_key=config.get("source_key"),
        )
    except Exception as exc:
        return {
            "status": "invalid",
            "name": config["name"],
            "expected_subjects": config["expected_subjects"],
            "selected_url": selected_url,
            "transport_failures_before_success": failures,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "status": "complete",
        "name": config["name"],
        "expected_subjects": config["expected_subjects"],
        "expected_source_key": config.get("source_key"),
        "selected_url": selected_url,
        "transport_failures_before_success": failures,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "labels": labels,
    }


def build_label_index(partitions: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    label_index: dict[str, dict[str, Any]] = {}
    for partition, labels in partitions.items():
        for label in labels:
            patient_id = str(label["patient_id"])
            if patient_id in label_index:
                prior = label_index[patient_id]["partition"]
                raise RuntimeError(
                    f"PatientID {patient_id} appears in multiple challenge partitions: "
                    f"{prior}, {partition}"
                )
            label_index[patient_id] = label
    return label_index


def validate_historical_training_conditions(
    label_index: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    issues: list[str] = []
    corrected = label_index.get("ProstateDx-01-0006")
    mismatch_case = label_index.get("ProstateDx-01-0055")
    patient_id_fix = label_index.get("ProstateDx-01-0035")
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


def audit_annotations(partition_patient_ids: dict[str, list[str]]) -> dict[str, Any]:
    """Audit annotation identity without letting attachment transport erase image evidence."""
    partition_records: dict[str, dict[str, Any]] = {}
    labels_by_partition: dict[str, list[dict[str, Any]]] = {}
    transport_unavailable = False
    invalid = False

    for partition, config in PARTITIONS.items():
        archives = [audit_label_archive(partition, archive) for archive in config["label_archives"]]
        complete_labels = [
            label
            for archive in archives
            if archive["status"] == "complete"
            for label in archive["labels"]
        ]
        labels_by_partition[partition] = complete_labels
        statuses = [archive["status"] for archive in archives]
        if any(status == "transport_unavailable" for status in statuses):
            transport_unavailable = True
        if any(status == "invalid" for status in statuses):
            invalid = True
        partition_records[partition] = {"archives": archives}

    all_complete = all(
        archive["status"] == "complete"
        for partition in partition_records.values()
        for archive in partition["archives"]
    )
    issues: dict[str, Any] = {}
    label_index: dict[str, dict[str, Any]] = {}
    historical: dict[str, Any] | None = None

    if all_complete:
        try:
            label_index = build_label_index(labels_by_partition)
        except RuntimeError as exc:
            issues["label_index"] = str(exc)
        if label_index:
            if len(label_index) != EXPECTED_TOTAL_SUBJECTS:
                issues["unique_label_patient_count"] = len(label_index)
            for partition, labels in labels_by_partition.items():
                observed = sorted(str(label["patient_id"]) for label in labels)
                expected = sorted(partition_patient_ids[partition])
                if observed != expected:
                    issues.setdefault("image_annotation_patient_mismatch", {})[partition] = {
                        "missing_annotations": sorted(set(expected) - set(observed)),
                        "unexpected_annotations": sorted(set(observed) - set(expected)),
                    }
            historical = validate_historical_training_conditions(label_index)
            if historical["issues"]:
                issues["historical_training_conditions"] = historical["issues"]

    if invalid or issues:
        status = "incomplete"
    elif all_complete:
        status = "complete"
    elif transport_unavailable:
        status = "transport_unavailable"
    else:
        status = "incomplete"

    return {
        "status": status,
        "required_before_result_bearing_m6": True,
        "analysis_page": CURRENT_ANALYSIS_PAGE,
        "partitions": partition_records,
        "historical_training_conditions": historical,
        "issues": issues,
    }


def audit_image_identity() -> dict[str, Any]:
    doi_record = query_doi_series()
    training_record = query_shared_list(
        str(PARTITIONS["training"]["shared_list_name"]),
        expected=int(PARTITIONS["training"]["expected_series"]),
    )
    leaderboard_record = query_shared_list(
        str(PARTITIONS["leaderboard"]["shared_list_name"]),
        expected=int(PARTITIONS["leaderboard"]["expected_series"]),
    )
    partition_uids = derive_partition_uids(
        doi_record["series_uids"],
        training_record["series_uids"],
        leaderboard_record["series_uids"],
    )

    legacy_crosschecks = {
        partition: audit_legacy_manifest_crosscheck(partition, uids)
        for partition, uids in partition_uids.items()
    }
    legacy_mismatches = {
        partition: record
        for partition, record in legacy_crosschecks.items()
        if record["status"] in {"mismatch", "invalid"}
    }

    all_uids = sorted(uid for uids in partition_uids.values() for uid in uids)
    idc_response = query_idc_official_series(all_uids)
    mapping = map_series_identity(partition_uids, idc_response["series"])
    issues = dict(mapping["issues"])
    if legacy_mismatches:
        issues["legacy_manifest_crosscheck"] = legacy_mismatches

    return {
        "status": "complete" if not issues else "incomplete",
        "authority": {
            "doi_series_universe": doi_record,
            "training_shared_list": training_record,
            "leaderboard_shared_list": leaderboard_record,
            "test_partition_rule": (
                "DOI universe minus training shared list minus leaderboard shared list"
            ),
        },
        "partition_series_uids": partition_uids,
        "legacy_manifest_crosschecks": legacy_crosschecks,
        "idc_resolution": {
            "warnings": idc_response.get("warnings", []),
            "truncated": idc_response.get("truncated", False),
            "series_rows": len(idc_response["series"]),
            **mapping,
        },
        "issues": issues,
    }


def build_audit() -> dict[str, Any]:
    """Build the M6 pre-result identity audit while preserving partial gate evidence."""
    image_identity = audit_image_identity()
    partition_patient_ids = image_identity["idc_resolution"]["partition_patient_ids"]
    annotations = audit_annotations(partition_patient_ids)
    overall_complete = (
        image_identity["status"] == "complete" and annotations["status"] == "complete"
    )

    return {
        "schema_version": 3,
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
        "schema_version": 3,
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
