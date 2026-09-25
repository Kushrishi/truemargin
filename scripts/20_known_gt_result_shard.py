#!/usr/bin/env python3
"""Run one frozen TrueMargin known-GT anatomy shard with strict source pinning."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

SOURCE_GIT_SHA = "f52aee24b49327bf7989ae0746dbf2ad981510d1"
SOURCE_CI_RUN_ID = 36184383591
EXECUTION_MODE = "ten_anatomy_shards_plus_canonical_aggregate"
ORCHESTRATION_BLOB_FIELDS = {
    "scripts/20_known_gt_result_shard.py": "shard_orchestrator_blob_sha",
    ".github/workflows/known-gt-result-bearing.yml": "result_workflow_blob_sha",
    "scripts/fetch_known_gt_inputs.py": "acquisition_utility_blob_sha",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "19_hyperparameter_known_gt_validation.py"

RESULT_DEFINING_PATHS = (
    "scripts/19_hyperparameter_known_gt_validation.py",
    "docs/hyperparameter_known_gt_protocol.md",
    "docs/hyperparameter_known_gt_protocol_amendment_1.md",
    "docs/hyperparameter_known_gt_protocol_amendment_2.md",
    "docs/hyperparameter_known_gt_comparator_protocol.md",
    "docs/hyperparameter_known_gt_execution_control_amendment_1.md",
    "research/KNOWN_GT_CD_FEASIBILITY.json",
    "src/truemargin/hyperparameter.py",
    "src/truemargin/comparators.py",
    "src/truemargin/known_gt_comparison.py",
    "src/truemargin/registration.py",
    "src/truemargin/ensemble.py",
    "src/truemargin/io_utils.py",
    "src/truemargin/calibration.py",
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("known_gt_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load known-GT runner from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        stderr=subprocess.STDOUT,
    )


def _verify_source_files(source_git_sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", source_git_sha):
        raise SystemExit(f"Invalid pinned source Git SHA: {source_git_sha!r}")
    if source_git_sha != SOURCE_GIT_SHA:
        raise SystemExit(
            f"Unexpected source Git SHA: expected {SOURCE_GIT_SHA}, got {source_git_sha}"
        )

    try:
        _git("cat-file", "-e", f"{source_git_sha}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Pinned source commit is unavailable: {source_git_sha}") from exc

    mismatches: list[str] = []
    for relative_path in RESULT_DEFINING_PATHS:
        current = (REPO_ROOT / relative_path).read_bytes()
        try:
            frozen = _git("show", f"{source_git_sha}:{relative_path}")
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                f"Result-defining path missing from pinned source: {relative_path}"
            ) from exc
        if current != frozen:
            mismatches.append(relative_path)

    if mismatches:
        raise SystemExit(
            "Result-defining source drift from pinned implementation revision: "
            + ", ".join(mismatches)
        )


def verify_execution_authorization() -> tuple[Any, dict[str, Any]]:
    runner = _load_runner()
    runner.verify_protocol_identities()
    request = runner.verify_result_bearing_authorization()

    expected_extra = {
        "source_git_sha": SOURCE_GIT_SHA,
        "source_ci_run_id": SOURCE_CI_RUN_ID,
        "source_ci_conclusion": "success",
        "execution_mode": EXECUTION_MODE,
        "planned_shards": 10,
        "cases_per_shard": runner.N_REPLICATES,
    }
    for key, expected in expected_extra.items():
        if request.get(key) != expected:
            raise SystemExit(
                f"Invalid source/execution authorization field {key!r}: "
                f"expected {expected!r}, got {request.get(key)!r}"
            )

    _verify_source_files(request["source_git_sha"])

    for relative_path, request_field in ORCHESTRATION_BLOB_FIELDS.items():
        expected_blob = request.get(request_field)
        if not isinstance(expected_blob, str) or not re.fullmatch(
            r"[0-9a-f]{40}", expected_blob
        ):
            raise SystemExit(
                f"Invalid orchestration blob field {request_field!r}: "
                f"{expected_blob!r}"
            )
        actual_blob = runner._git_blob_sha(str(REPO_ROOT / relative_path))
        if actual_blob != expected_blob:
            raise SystemExit(
                f"Orchestration content drift for {relative_path}: "
                f"expected blob {expected_blob}, got {actual_blob}"
            )

    return runner, request


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def run_patient_shard(patient: str) -> None:
    runner, request = verify_execution_authorization()
    patients = list(runner.HELD_OUT_CASES)
    if patient not in runner.HELD_OUT_CASES:
        raise SystemExit(f"Patient {patient!r} is not in the frozen held-out cohort.")

    anatomy_index = patients.index(patient)
    series = runner.HELD_OUT_CASES[patient]
    crop, mask_crop, spacing = runner.prepare_anatomy(patient, series)

    geometry: list[dict[str, Any]] = []
    for replicate in range(runner.N_REPLICATES):
        geometry.append(
            runner.geometry_record(
                patient=patient,
                anatomy_index=anatomy_index,
                replicate=replicate,
                crop=crop,
                mask_crop=mask_crop,
                spacing=spacing,
            )
        )

    checkpoint_root = str(
        REPO_ROOT / "outputs" / "checkpoints" / "hyperparameter_known_gt"
    )
    case_rows: list[dict[str, Any]] = []
    for replicate in range(runner.N_REPLICATES):
        row = runner._run_case(
            patient=patient,
            t2_series=series["t2_series"],
            anatomy_index=anatomy_index,
            replicate=replicate,
            crop=crop,
            mask_crop=mask_crop,
            spacing=spacing,
            checkpoint_root=checkpoint_root,
        )
        case_rows.append(_clean_row(row))

    output_dir = REPO_ROOT / "outputs" / "shards"
    output_dir.mkdir(parents=True, exist_ok=True)
    request_blob = runner._git_blob_sha(runner.RUN_REQUEST_PATH)
    payload = {
        "schema_version": 1,
        "study": "hyperparameter-known-gt-v1",
        "patient": patient,
        "anatomy_index": anatomy_index,
        "source_git_sha": request["source_git_sha"],
        "execution_git_sha": runner.provenance.current_git_sha(runner.REPO_ROOT),
        "run_request_blob_sha": request_blob,
        "planned_cases": runner.N_REPLICATES,
        "geometry_records": geometry,
        "case_rows": case_rows,
    }
    output = output_dir / f"{patient}.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"SHARD_PATIENT={patient}")
    print(f"SHARD_CASES={len(case_rows)}")
    print(f"SHARD_COMPLETE_CASES={sum(bool(row['complete']) for row in case_rows)}")
    print(f"SHARD_OUTPUT={output}")


def main() -> None:
    runner, _ = verify_execution_authorization()

    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--patient", choices=tuple(runner.HELD_OUT_CASES))
    args = parser.parse_args()

    if args.verify_only:
        if args.patient is not None:
            raise SystemExit("--verify-only and --patient are mutually exclusive.")
        print(f"RESULT_SOURCE_GIT_SHA={SOURCE_GIT_SHA}")
        print(f"RESULT_SOURCE_CI_RUN_ID={SOURCE_CI_RUN_ID}")
        print("RESULT_BEARING_AUTHORIZATION=PASS")
        return

    if args.patient is None:
        raise SystemExit("Provide --patient for a shard or use --verify-only.")
    run_patient_shard(args.patient)


if __name__ == "__main__":
    main()
