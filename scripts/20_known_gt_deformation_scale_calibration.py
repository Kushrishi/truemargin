#!/usr/bin/env python3
"""Select a global fold-free known-GT B-spline coefficient scale using geometry only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = REPO_ROOT / "research" / "KNOWN_GT_GEOMETRY_CALIBRATION_REQUEST.json"
OUTPUT_PATH = REPO_ROOT / "outputs" / "known_gt_deformation_scale_calibration.json"

PROTOCOL_MAIN_BLOB_SHA = "98a747c502a4aca6d8e65f8373bc4e62a8f1b7a0"
PROTOCOL_AMENDMENT_1_BLOB_SHA = "1eafe77bb847b1a77229e267ef32e6bbedd27bc2"
PROTOCOL_AMENDMENT_2_BLOB_SHA = "5f1e1464e8f8d0eb81b90f92caf5a94d7ed81ac7"
CANDIDATE_STDS = (3.5, 3.0, 2.5)
EXPECTED_ANATOMIES = (
    "aaa0044",
    "aaa0051",
    "aaa0053",
    "aaa0060",
    "aaa0064",
    "aaa0069",
    "aaa0071",
    "aaa0072",
    "aaa0086",
    "aaa0087",
)
PLANNED_CASES = 30


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _load_known_gt_runner() -> ModuleType:
    path = REPO_ROOT / "scripts" / "19_hyperparameter_known_gt_validation.py"
    spec = importlib.util.spec_from_file_location("known_gt_runner_for_scale_calibration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load known-GT runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_request() -> dict[str, Any]:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "study": "hyperparameter-known-gt-v1",
        "authorized_mode": "geometry-scale-calibration-only",
        "result_bearing_authorized": False,
        "triggering_geometry_run_id": 36167535578,
        "triggering_source_git_sha": "bcd7099bca8d37f9f895227c386503610639bd03",
        "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
        "protocol_amendment_1_blob_sha": PROTOCOL_AMENDMENT_1_BLOB_SHA,
        "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
        "coefficient_std_candidates": list(CANDIDATE_STDS),
        "selection_rule": "largest candidate with 30/30 original geometry checks passing",
        "held_out_anatomies": list(EXPECTED_ANATOMIES),
        "planned_cases_per_candidate": PLANNED_CASES,
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise SystemExit(
                f"Invalid geometry-calibration request field {key!r}: "
                f"expected {value!r}, got {request.get(key)!r}"
            )

    amendment_path = REPO_ROOT / "docs" / "hyperparameter_known_gt_protocol_amendment_2.md"
    actual_blob = _git_blob_sha(amendment_path)
    if actual_blob != PROTOCOL_AMENDMENT_2_BLOB_SHA:
        raise SystemExit(
            "Amendment 2 content drift: "
            f"expected {PROTOCOL_AMENDMENT_2_BLOB_SHA}, got {actual_blob}"
        )
    return request


def first_passing_candidate(candidate_results: list[dict[str, Any]]) -> float | None:
    for result in candidate_results:
        if (
            int(result["planned_cases"]) == PLANNED_CASES
            and int(result["passed_cases"]) == PLANNED_CASES
            and int(result["failed_cases"]) == 0
        ):
            return float(result["coefficient_std"])
    return None


def evaluate_candidate(
    runner: ModuleType,
    prepared: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]],
    coefficient_std: float,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for anatomy_index, (patient, _series) in enumerate(runner.HELD_OUT_CASES.items()):
        crop, mask_crop, spacing = prepared[patient]
        for replicate in range(runner.N_REPLICATES):
            try:
                record = runner.geometry_record(
                    patient=patient,
                    anatomy_index=anatomy_index,
                    replicate=replicate,
                    crop=crop,
                    mask_crop=mask_crop,
                    spacing=spacing,
                    coefficient_std=coefficient_std,
                )
            except Exception as exc:
                failure = {
                    "patient": patient,
                    "anatomy_index": anatomy_index,
                    "replicate": replicate,
                    "case_seed": runner.case_seed(anatomy_index, replicate),
                    "coefficient_std": coefficient_std,
                    "reason": f"{type(exc).__name__}:{exc}",
                }
                failures.append(failure)
                print(
                    f"std={coefficient_std:g} patient={patient} replicate={replicate} "
                    f"seed={failure['case_seed']} GEOMETRY_FAILED {failure['reason']}"
                )
                continue

            records.append(record)
            print(
                f"std={coefficient_std:g} patient={patient} replicate={replicate} "
                f"seed={record['case_seed']} jacobian_min={record['jacobian_min']:.6g} "
                f"true_disp_median={record['true_displacement_median_mm']:.6g} mm"
            )

    return {
        "coefficient_std": coefficient_std,
        "planned_cases": PLANNED_CASES,
        "passed_cases": len(records),
        "failed_cases": len(failures),
        "records": records,
        "failures": failures,
    }


def main() -> None:
    verify_request()
    runner = _load_known_gt_runner()
    runner.verify_protocol_identities()

    if tuple(runner.HELD_OUT_CASES) != EXPECTED_ANATOMIES:
        raise SystemExit("Held-out anatomy order drifted from Amendment 2.")
    if runner.N_REPLICATES != 3:
        raise SystemExit("Replicate count drifted from Amendment 2.")

    prepared: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]] = {}
    for patient, series in runner.HELD_OUT_CASES.items():
        prepared[patient] = runner.prepare_anatomy(patient, series)

    candidate_results: list[dict[str, Any]] = []
    selected: float | None = None
    for coefficient_std in CANDIDATE_STDS:
        print(f"=== GEOMETRY_SCALE_CANDIDATE std={coefficient_std:g} ===")
        result = evaluate_candidate(runner, prepared, coefficient_std)
        candidate_results.append(result)
        if int(result["failed_cases"]) == 0:
            selected = coefficient_std
            break

    payload = {
        "schema_version": 1,
        "study": "hyperparameter-known-gt-v1",
        "mode": "geometry-scale-calibration-only",
        "result_bearing_authorized": False,
        "git_sha": runner.provenance.current_git_sha(str(REPO_ROOT)),
        "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
        "protocol_amendment_1_blob_sha": PROTOCOL_AMENDMENT_1_BLOB_SHA,
        "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
        "candidate_stds": list(CANDIDATE_STDS),
        "selection_rule": "largest candidate with 30/30 original geometry checks passing",
        "selected_coefficient_std": selected,
        "candidate_results": candidate_results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if selected is None:
        print("GEOMETRY_SCALE_CALIBRATION=FAIL selected=None")
        print(f"record={OUTPUT_PATH}")
        raise SystemExit(
            "No frozen global coefficient standard deviation passed 30/30 geometry cases."
        )

    print(f"GEOMETRY_SCALE_CALIBRATION=PASS selected={selected:g}")
    print(f"record={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
