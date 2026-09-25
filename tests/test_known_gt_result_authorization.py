from __future__ import annotations

import importlib.util
from pathlib import Path


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_result_request_matches_frozen_authorization(monkeypatch) -> None:
    root = Path(__file__).parents[1]
    runner = _load(
        root / "scripts" / "19_hyperparameter_known_gt_validation.py",
        "known_gt_runner_for_authorization_test",
    )
    shard = _load(
        root / "scripts" / "20_known_gt_result_shard.py",
        "known_gt_shard_for_authorization_test",
    )

    request = runner.verify_result_bearing_authorization()
    assert request["source_git_sha"] == shard.SOURCE_GIT_SHA
    assert request["source_ci_run_id"] == shard.SOURCE_CI_RUN_ID
    assert request["source_ci_conclusion"] == "success"
    assert request["execution_mode"] == shard.EXECUTION_MODE
    assert request["planned_shards"] == 10
    assert request["cases_per_shard"] == 3
    assert request["planned_forward_registrations"] == 270
    assert request["planned_reverse_registrations"] == 270
    assert request["cd_feasible"] is False
    assert request["cd_registration_count"] == 0
    assert request["total_planned_registrations"] == 540
    assert request["result_bearing_outcomes_observed_before_authorization"] is False

    for relative_path, field in shard.ORCHESTRATION_BLOB_FIELDS.items():
        assert request[field] == runner._git_blob_sha(str(root / relative_path))

    observed_source: list[str] = []
    monkeypatch.setattr(
        shard,
        "_verify_source_files",
        lambda source_git_sha: observed_source.append(source_git_sha),
    )
    _, verified = shard.verify_execution_authorization()
    assert verified == request
    assert observed_source == [shard.SOURCE_GIT_SHA]
