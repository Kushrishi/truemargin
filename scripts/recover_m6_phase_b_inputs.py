"""Acquire only evaluation archives and recover their unchanged frozen identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from truemargin.m6_zip_recovery import recover_frozen_zip

REPO = Path(__file__).resolve().parents[1]
FREEZE = REPO / "research/M6_PHASE_B_INPUT_FREEZE.json"
URL = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    from m6_phase_b_evaluation import verify_execution_authorization

    verify_execution_authorization()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    freeze_bytes = FREEZE.read_bytes()
    rows = json.loads(freeze_bytes)["evaluation"]
    if len(rows) != 30:
        raise ValueError("recovery is restricted to the 30 frozen evaluation inputs")
    # Whole UTC interval of the pinned acquisition-only preflight run.
    start = datetime(2026, 10, 2, 18, 53, 44)
    end = datetime(2026, 10, 2, 18, 54, 58)

    def acquire(patient: str, row: dict[str, str]) -> dict[str, object]:
        query = urllib.parse.urlencode(
            {"SeriesInstanceUID": row["series_uid"], "NewFileNames": "Yes"}
        )
        request = urllib.request.Request(
            f"{URL}?{query}", headers={"User-Agent": "TrueMargin-input-recovery"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        current_sha = hashlib.sha256(payload).hexdigest()
        recovered, recovery = recover_frozen_zip(
            payload, row["dicom_zip_sha256"], start=start, end=end
        )
        if hashlib.sha256(recovered).hexdigest() != row["dicom_zip_sha256"]:
            raise AssertionError("recovery digest changed before preservation")
        path = args.output_dir / f"{patient}.zip"
        path.write_bytes(recovered)
        return {
            "patient_id": patient,
            "series_uid": row["series_uid"],
            "current_official_archive_sha256": current_sha,
            "recovered_archive_sha256": row["dicom_zip_sha256"],
            "size_bytes": len(recovered),
            **recovery,
        }

    records: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(acquire, patient, row): patient for patient, row in sorted(rows.items())
        }
        for future in as_completed(futures):
            patient = futures[future]
            try:
                records.append(future.result())
                print(f"EXACT_INPUT_RECOVERED={patient}", flush=True)
            except Exception as exc:
                failures.append({"patient_id": patient, "error": f"{type(exc).__name__}: {exc}"})
                print(f"INPUT_UNRESOLVED={patient}: {exc}", flush=True)
    record = {
        "schema_version": 1,
        "record": "m6-evaluation-historical-archive-recovery",
        "date_utc": "2026-10-03",
        "status": "complete" if len(records) == 30 and not failures else "incomplete",
        "historical_preflight_run_id": 37050507332,
        "historical_preflight_artifact_sha256": (
            "cebada652ad648afba98e79e88b06d9315d1e59f228a080a7656ad707486db68"
        ),
        "input_freeze_sha256": hashlib.sha256(freeze_bytes).hexdigest(),
        "search_start_utc": start.isoformat(),
        "search_end_utc": end.isoformat(),
        "complete_evaluation_inputs": len(records),
        "failed_evaluation_inputs": len(failures),
        "evaluation": sorted(records, key=lambda row: str(row["patient_id"])),
        "failures": sorted(failures, key=lambda row: row["patient_id"]),
        "evaluation_acquired": bool(records),
        "image_decoding_performed": False,
        "registration_performed": False,
        "numerical_evaluation_outputs_inspected": False,
        "input_registry_changed": False,
        "evaluation_execution_authorized": True,
    }
    (args.output_dir / "recovery.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
