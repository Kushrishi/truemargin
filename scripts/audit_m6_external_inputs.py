#!/usr/bin/env python3
"""Metadata-only identity audit for the TrueMargin M6 external substrate."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CHALLENGE_DOI = "10.7937/K9/TCIA.2015.zF0vlOPv"
TCIA_V4_SHARED_LIST = (
    "https://services.cancerimagingarchive.net/services/v4/SharedList/query/ContentsByName"
)
IDC_MANIFEST = "https://api.imaging.datacommons.cancer.gov/v3/cohort/manifest"
EXPECTED_TOTAL = 80
API_ATTEMPTS = 3
API_TIMEOUT = 45
BINARY_URLLIB_TIMEOUT = 12
CURL_TIMEOUT = 60
BACKOFF = (2, 5)

SOURCES = {
    "prostate_3t": {"stem": "Prostate3T-", "collection_id": "prostate_3t"},
    "prostate_diagnosis": {"stem": "ProstateDx-", "collection_id": "prostate_diagnosis"},
}
PARTITIONS: dict[str, dict[str, Any]] = {
    "training": {
        "subjects": 60,
        "series": 60,
        "shared_list": "ISBI Prostate Challenge - Training",
        "label_name": "NCI-ISBI 2013 Prostate Challenge - Training.zip",
        "label_url": (
            "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
            "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Training.zip?api=v2"
        ),
    },
    "leaderboard": {
        "subjects": 10,
        "series": 10,
        "shared_list": "ISBI Prostate Challenge - Leader Board",
        "label_name": "NCI-ISBI 2013 Prostate Challenge - Leaderboard.zip",
        "label_url": (
            "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
            "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Leaderboard.zip?api=v2"
        ),
    },
    "test": {
        "subjects": 10,
        "series": 10,
        "shared_list": None,
        "manifest_name": "ISBI-Prostate-Challenge-Testing.tcia",
        "manifest_url": (
            "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
            "ISBI-Prostate-Challenge-Testing.tcia?api=v2"
        ),
        "label_name": "NCI-ISBI 2013 Prostate Challenge - Test.zip",
        "label_url": (
            "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
            "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Test.zip?api=v2"
        ),
    },
}
PATIENT_RE = re.compile(r"(Prostate(?:3T|Dx)-(?:01|02|03)-\d{4})")
NAMESPACE_RE = re.compile(r"^Prostate(?:3T|Dx)-(?P<namespace>\d{2})-\d{4}$")
UID_RE = re.compile(r"\d+(?:\.\d+)+")
IDC_FIELDS = (
    "PatientID",
    "collection_id",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SeriesDescription",
    "ProtocolName",
    "Modality",
    "instanceCount",
    "Manufacturer",
    "ManufacturerModelName",
    "MagneticFieldStrength",
    "SliceThickness",
    "Rows",
    "Columns",
)


class TransportUnavailable(RuntimeError):
    def __init__(self, url: str, failures: list[dict[str, Any]]):
        self.url = url
        self.failures = failures
        super().__init__(f"Transport unavailable for {url}: {json.dumps(failures, sort_keys=True)}")


def _error(exc: BaseException, client: str) -> dict[str, Any]:
    out: dict[str, Any] = {"client": client, "type": type(exc).__name__, "message": str(exc)}
    if isinstance(exc, urllib.error.HTTPError):
        out["http_status"] = int(exc.code)
        out["http_reason"] = str(exc.reason)
    elif isinstance(exc, urllib.error.URLError):
        out["reason"] = str(exc.reason)
    return out


def request_bytes(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    attempts: int = API_ATTEMPTS,
    timeout: int = API_TIMEOUT,
) -> tuple[bytes, list[dict[str, Any]]]:
    request_headers = {"User-Agent": "truemargin-research/0.1", **(headers or {})}
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
            item = _error(exc, "urllib")
            item["attempt"] = attempt + 1
            failures.append(item)
            if attempt + 1 < attempts:
                time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
    raise TransportUnavailable(url, failures)


def curl_bytes(url: str) -> tuple[bytes, dict[str, Any]]:
    with tempfile.NamedTemporaryFile(prefix="truemargin-tcia-", delete=False) as handle:
        path = Path(handle.name)
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
                str(CURL_TIMEOUT),
                "--retry",
                "2",
                "--retry-delay",
                "2",
                "--retry-all-errors",
                "--output",
                str(path),
                "--write-out",
                "%{http_code}",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=CURL_TIMEOUT + 30,
            check=False,
        )
        status = proc.stdout.strip()
        if proc.returncode != 0:
            raise RuntimeError(
                f"curl exit={proc.returncode} http={status or 'unknown'} "
                f"stderr={proc.stderr.strip()[:512]}"
            )
        payload = path.read_bytes()
        if not payload:
            raise RuntimeError(f"curl returned an empty payload with HTTP {status or 'unknown'}")
        return payload, {
            "client": "curl",
            "http_status": int(status) if status.isdigit() else None,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    finally:
        path.unlink(missing_ok=True)


def official_binary(url: str) -> tuple[bytes, dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    try:
        payload, prior = request_bytes(url, attempts=1, timeout=BINARY_URLLIB_TIMEOUT)
        return payload, {
            "url": url,
            "client": "urllib",
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "prior_failures": prior,
        }
    except TransportUnavailable as exc:
        failures.extend(exc.failures)
    try:
        payload, record = curl_bytes(url)
        return payload, {"url": url, **record, "prior_failures": failures}
    except Exception as exc:
        failures.append(_error(exc, "curl"))
        raise TransportUnavailable(url, failures) from exc


def json_get(url: str) -> tuple[Any, dict[str, Any]]:
    raw, failures = request_bytes(url)
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Expected JSON from {url}") from exc
    return payload, {
        "url": url,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "transport_failures_before_success": failures,
    }


def json_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw, _ = request_bytes(
        url,
        data=json.dumps(payload, sort_keys=True).encode(),
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    decoded = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return decoded


def series_rows(payload: Any, source: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next(
            (
                payload[key]
                for key in ("series", "Series", "results", "Results", "data", "Data")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
        if rows is None:
            raise RuntimeError(f"No series list found in JSON from {source}")
    else:
        raise RuntimeError(f"Expected JSON list/object from {source}")
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"Non-object series row returned by {source}")
    return [dict(row) for row in rows]


def series_uid(row: dict[str, Any]) -> str:
    for key in ("SeriesInstanceUID", "seriesInstanceUID"):
        value = row.get(key)
        if isinstance(value, str) and UID_RE.fullmatch(value):
            return value
    raise RuntimeError(f"Series row lacks a valid SeriesInstanceUID: {sorted(row)}")


def exact_uids(payload: Any, expected: int, source: str) -> tuple[list[str], list[dict[str, Any]]]:
    rows = series_rows(payload, source)
    uids = [series_uid(row) for row in rows]
    if len(uids) != len(set(uids)):
        raise RuntimeError(f"Duplicate SeriesInstanceUID returned by {source}")
    if len(uids) != expected:
        raise RuntimeError(f"Expected {expected} series from {source}; found {len(uids)}")
    return uids, rows


def shared_list(name: str, expected: int) -> dict[str, Any]:
    url = f"{TCIA_V4_SHARED_LIST}?{urllib.parse.urlencode({'name': name})}"
    payload, provenance = json_get(url)
    uids, _ = exact_uids(payload, expected, f"shared list {name!r}")
    return {
        "authority": "TCIA v4 SharedList/query/ContentsByName",
        "name": name,
        "series_uids": sorted(uids),
        "response": provenance,
    }


def manifest_uids(raw: bytes, expected: int) -> list[str]:
    lines = [line.strip() for line in raw.decode("utf-8-sig").splitlines()]
    marker = "ListOfSeriesToDownload="
    if marker not in lines:
        raise RuntimeError("TCIA manifest lacks ListOfSeriesToDownload marker")
    uids = [line for line in lines[lines.index(marker) + 1 :] if line]
    if any(UID_RE.fullmatch(uid) is None for uid in uids):
        raise RuntimeError("TCIA manifest contains a non-UID series line")
    if len(uids) != len(set(uids)):
        raise RuntimeError("TCIA manifest contains duplicate SeriesInstanceUID values")
    if len(uids) != expected:
        raise RuntimeError(f"Expected {expected} manifest series; found {len(uids)}")
    return uids


def test_manifest() -> dict[str, Any]:
    config = PARTITIONS["test"]
    raw, transport = official_binary(str(config["manifest_url"]))
    return {
        "authority": "official TCIA Source Image Data - Test manifest",
        "name": config["manifest_name"],
        "series_uids": sorted(manifest_uids(raw, int(config["series"]))),
        "transport": transport,
    }


def validate_partitions(
    training: list[str], leaderboard: list[str], test: list[str]
) -> dict[str, list[str]]:
    sets = {
        "training": set(training),
        "leaderboard": set(leaderboard),
        "test": set(test),
    }
    for name, values in sets.items():
        expected = int(PARTITIONS[name]["series"])
        if len(values) != expected:
            raise RuntimeError(f"Expected {expected} unique {name} series; found {len(values)}")
    names = list(sets)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            overlap = sorted(sets[left] & sets[right])
            if overlap:
                raise RuntimeError(f"{left}/{right} series overlap: {overlap[:3]}")
    union = set().union(*sets.values())
    if len(union) != EXPECTED_TOTAL:
        raise RuntimeError(f"Expected {EXPECTED_TOTAL} unique challenge series; found {len(union)}")
    return {name: sorted(values) for name, values in sets.items()}


def source_key(patient_id: str) -> str:
    if PATIENT_RE.fullmatch(patient_id) is None:
        raise ValueError(f"Unsupported challenge PatientID: {patient_id}")
    matches = [name for name, cfg in SOURCES.items() if patient_id.startswith(cfg["stem"])]
    if len(matches) != 1:
        raise ValueError(f"PatientID does not map to exactly one source: {patient_id}")
    return matches[0]


def namespace(patient_id: str) -> str:
    match = NAMESPACE_RE.fullmatch(patient_id)
    if match is None:
        raise ValueError(f"Cannot derive namespace from PatientID: {patient_id}")
    return str(match.group("namespace"))


def idc_series(uids: list[str]) -> dict[str, Any]:
    response = json_post(
        IDC_MANIFEST,
        {
            "filters": {
                "terms": {
                    "collection_id": [cfg["collection_id"] for cfg in SOURCES.values()],
                    "SeriesInstanceUID": uids,
                    "Modality": ["MR"],
                }
            },
            "page": 0,
            "page_size": 5000,
        },
    )
    if response.get("truncated") is True:
        raise RuntimeError("IDC metadata response was truncated")
    if not isinstance(response.get("series"), list):
        raise RuntimeError("IDC response lacks series list")
    return response


def map_identities(partitions: dict[str, list[str]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    partition_for_uid = {uid: part for part, uids in partitions.items() for uid in uids}
    expected = set(partition_for_uid)
    by_uid: dict[str, list[dict[str, Any]]] = {uid: [] for uid in expected}
    unexpected: set[str] = set()
    for row in rows:
        uid = str(row.get("SeriesInstanceUID", ""))
        if uid in by_uid:
            by_uid[uid].append(row)
        else:
            unexpected.add(uid)

    issues: dict[str, Any] = {}
    missing = sorted(uid for uid, matches in by_uid.items() if not matches)
    duplicates = sorted(uid for uid, matches in by_uid.items() if len(matches) > 1)
    if missing:
        issues["missing_series_uids_in_idc"] = missing
    if duplicates:
        issues["duplicate_series_uids_in_idc"] = duplicates
    if unexpected:
        issues["unexpected_series_uids_from_idc"] = sorted(unexpected)

    records: list[dict[str, Any]] = []
    bad_patients: list[dict[str, str]] = []
    collection_mismatches: list[dict[str, str]] = []
    for uid in sorted(expected):
        if len(by_uid[uid]) != 1:
            continue
        row = by_uid[uid][0]
        patient_id = str(row.get("PatientID", ""))
        try:
            key = source_key(patient_id)
            ns = namespace(patient_id)
        except ValueError:
            bad_patients.append({"series_uid": uid, "patient_id": patient_id})
            continue
        observed_collection = row.get("collection_id")
        expected_collection = SOURCES[key]["collection_id"]
        if observed_collection is not None and str(observed_collection) != expected_collection:
            collection_mismatches.append(
                {
                    "series_uid": uid,
                    "patient_id": patient_id,
                    "expected_collection_id": expected_collection,
                    "observed_collection_id": str(observed_collection),
                }
            )
        records.append(
            {
                "series_uid": uid,
                "patient_id": patient_id,
                "patient_namespace": ns,
                "partition": partition_for_uid[uid],
                "source_key": key,
                "series": {field: row.get(field) for field in IDC_FIELDS},
            }
        )
    if bad_patients:
        issues["invalid_patient_ids"] = bad_patients
    if collection_mismatches:
        issues["source_collection_mismatches"] = collection_mismatches

    patients = [record["patient_id"] for record in records]
    duplicate_patients = sorted({p for p in patients if patients.count(p) > 1})
    if duplicate_patients:
        issues["duplicate_patient_ids"] = duplicate_patients
    if len(records) != EXPECTED_TOTAL:
        issues["resolved_series_count"] = len(records)
    if len(set(patients)) != EXPECTED_TOTAL:
        issues["unique_patient_count"] = len(set(patients))

    patient_ids = {
        part: sorted(record["patient_id"] for record in records if record["partition"] == part)
        for part in PARTITIONS
    }
    namespaces = {
        part: sorted(
            {record["patient_namespace"] for record in records if record["partition"] == part}
        )
        for part in PARTITIONS
    }
    source_counts: dict[str, dict[str, int]] = {}
    for part in PARTITIONS:
        counts = {key: 0 for key in SOURCES}
        for record in records:
            if record["partition"] == part:
                counts[record["source_key"]] += 1
        source_counts[part] = counts
        if len(patient_ids[part]) != int(PARTITIONS[part]["subjects"]):
            issues.setdefault("partition_patient_counts", {})[part] = len(patient_ids[part])

    return {
        "status": "complete" if not issues else "incomplete",
        "series_records": records,
        "partition_patient_ids": patient_ids,
        "partition_namespaces": namespaces,
        "partition_source_counts": source_counts,
        "issues": issues,
    }


def extract_patient_id(name: str) -> str:
    match = PATIENT_RE.search(Path(name).name)
    if match is None:
        raise ValueError(f"Cannot derive challenge PatientID from NRRD member: {name}")
    patient_id = match.group(1)
    source_key(patient_id)
    return patient_id


def label_records(raw: bytes, partition: str, expected: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = sorted(
            (
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".nrrd")
            ),
            key=lambda item: item.filename,
        )
        for info in members:
            payload = archive.read(info)
            patient_id = extract_patient_id(info.filename)
            records.append(
                {
                    "patient_id": patient_id,
                    "patient_namespace": namespace(patient_id),
                    "partition": partition,
                    "source_key": source_key(patient_id),
                    "archive_member": info.filename,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "corrected_label_filename": "correctedLabels" in Path(info.filename).name,
                }
            )
    ids = [record["patient_id"] for record in records]
    duplicates = sorted({patient for patient in ids if ids.count(patient) > 1})
    if duplicates:
        raise RuntimeError(f"Duplicate NRRD PatientIDs: {duplicates}")
    if len(records) != expected:
        raise RuntimeError(f"Expected {expected} NRRD subjects for {partition}; found {len(records)}")
    return records


def audit_label_partition(partition: str) -> dict[str, Any]:
    cfg = PARTITIONS[partition]
    try:
        raw, transport = official_binary(str(cfg["label_url"]))
        labels = label_records(raw, partition, int(cfg["subjects"]))
        return {
            "status": "complete",
            "name": cfg["label_name"],
            "transport": transport,
            "labels": labels,
        }
    except TransportUnavailable as exc:
        return {
            "status": "transport_unavailable",
            "name": cfg["label_name"],
            "transport_failures": exc.failures,
        }
    except Exception as exc:
        return {
            "status": "invalid",
            "name": cfg["label_name"],
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def historical_training_checks(index: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    corrected = index.get("ProstateDx-01-0006")
    if corrected is None or corrected.get("corrected_label_filename") is not True:
        issues.append("corrected ProstateDx-01-0006 label filename was not preserved")
    if "ProstateDx-01-0055" not in index:
        issues.append("documented ProstateDx-01-0055 mismatch case is missing")
    if "ProstateDx-01-0035" not in index:
        issues.append("documented ProstateDx-01-0035 identity-correction case is missing")
    return issues


def audit_annotations(image_patient_ids: dict[str, list[str]]) -> dict[str, Any]:
    partitions = {part: audit_label_partition(part) for part in PARTITIONS}
    complete = all(record["status"] == "complete" for record in partitions.values())
    issues: dict[str, Any] = {}
    namespaces: dict[str, list[str]] = {}
    historical: list[str] | None = None

    if complete:
        index: dict[str, dict[str, Any]] = {}
        for part, record in partitions.items():
            labels = record["labels"]
            namespaces[part] = sorted({label["patient_namespace"] for label in labels})
            observed = sorted(label["patient_id"] for label in labels)
            expected = sorted(image_patient_ids[part])
            if observed != expected:
                issues.setdefault("image_annotation_patient_mismatch", {})[part] = {
                    "missing_annotations": sorted(set(expected) - set(observed)),
                    "unexpected_annotations": sorted(set(observed) - set(expected)),
                }
            for label in labels:
                patient_id = label["patient_id"]
                if patient_id in index:
                    issues.setdefault("cross_partition_duplicate_patient_ids", []).append(patient_id)
                index[patient_id] = label
        if len(index) != EXPECTED_TOTAL:
            issues["unique_label_patient_count"] = len(index)
        historical = historical_training_checks(index)
        if historical:
            issues["historical_training_conditions"] = historical

    if issues or any(record["status"] == "invalid" for record in partitions.values()):
        status = "incomplete"
    elif complete:
        status = "complete"
    elif any(record["status"] == "transport_unavailable" for record in partitions.values()):
        status = "transport_unavailable"
    else:
        status = "incomplete"
    return {
        "status": status,
        "partitions": partitions,
        "partition_namespaces": namespaces,
        "historical_training_conditions": historical,
        "issues": issues,
    }


def audit_image_identity() -> dict[str, Any]:
    training = shared_list(str(PARTITIONS["training"]["shared_list"]), 60)
    leaderboard = shared_list(str(PARTITIONS["leaderboard"]["shared_list"]), 10)
    test = test_manifest()
    partitions = validate_partitions(
        training["series_uids"], leaderboard["series_uids"], test["series_uids"]
    )
    all_uids = sorted(uid for values in partitions.values() for uid in values)
    response = idc_series(all_uids)
    mapping = map_identities(partitions, response["series"])
    return {
        "status": mapping["status"],
        "authority": {
            "training_shared_list": training,
            "leaderboard_shared_list": leaderboard,
            "test_manifest": test,
        },
        "partition_series_uids": partitions,
        "idc_resolution": {
            "warnings": response.get("warnings", []),
            "truncated": response.get("truncated", False),
            "series_rows": len(response["series"]),
            **mapping,
        },
        "issues": mapping["issues"],
    }


def closed_boundary() -> dict[str, bool]:
    return {
        "result_bearing_authorized": False,
        "registration_authorized": False,
        "calibration_fit_authorized": False,
        "split_assignment_authorized": False,
        "dicom_download_performed": False,
        "heuristic_source_series_selection_performed": False,
    }


def build_audit() -> dict[str, Any]:
    image = audit_image_identity()
    annotations = audit_annotations(image["idc_resolution"]["partition_patient_ids"])
    ready = image["status"] == "complete" and annotations["status"] == "complete"
    return {
        "schema_version": 4,
        "milestone": "M6",
        "audit": "external-input-identity",
        "status": "complete" if ready else "incomplete",
        "challenge": {"doi": CHALLENGE_DOI, "subjects_expected": 80, "series_expected": 80},
        "authorization_boundary": closed_boundary(),
        "image_identity": image,
        "annotation_identity": annotations,
        "summary": {
            "image_identity_status": image["status"],
            "annotation_identity_status": annotations["status"],
            "identity_freeze_ready": ready,
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
        "authorization_boundary": closed_boundary(),
    }
    if isinstance(exc, TransportUnavailable):
        record["transport_failure"] = {"url": exc.url, "attempts": exc.failures}
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/m6_input_identity_audit.json"))
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
        print(f"M6_IMAGE_IDENTITY_STATUS={summary['image_identity_status'].upper()}")
        print(f"M6_ANNOTATION_IDENTITY_STATUS={summary['annotation_identity_status'].upper()}")
    print("RESULT_BEARING_AUTHORIZED=False")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
