import json
from pathlib import Path

import numpy as np
import pytest

from truemargin import registration_member as member
from truemargin.field_checkpoint import read_field_checkpoint_record
from truemargin.provenance import _sha256_file

SETTINGS = member.RegistrationSettings(3, 15, (0.97, 0.97, 2.5), False, 50, 1e-5)


def execute(path):
    return member.execute_registration_member(
        path,
        fixed=np.zeros((2, 3, 4), dtype=np.int16),
        moving=np.ones((2, 3, 4), dtype=np.int16),
        settings=SETTINGS,
        repo_root=Path(__file__).resolve().parents[1],
        member_id="synthetic-forward",
        case_id="synthetic",
        fixed_image_id="fixed",
        moving_image_id="moving",
    )


def backend(fixed, moving, **kwargs):
    assert kwargs["mesh_size"] == 3 and kwargs["max_iterations"] == 15
    assert kwargs["metric_bins"] == 50 and kwargs["spacing"] == (0.97, 0.97, 2.5)
    assert kwargs["center_first"] is False
    assert kwargs["gradient_convergence_tolerance"] == 1e-5
    kwargs["progress_callback"](0, -1.0)
    kwargs["progress_callback"](0, -1.1)
    kwargs["completion_callback"](
        {
            "optimizer_stop_condition": "synthetic iteration limit",
            "optimizer_iteration": 15,
            "optimizer_metric": -1.1,
        }
    )
    return np.moveaxis(np.arange(72, dtype=np.float64).reshape(2, 3, 4, 3), -1, 0)


def test_single_member_saves_exact_field_stop_and_repeated_events(tmp_path, monkeypatch):
    monkeypatch.setattr(member, "baseline_bspline_registration", backend)
    path = tmp_path / "attempt"
    saved = execute(path)
    field = np.load(saved.path, mmap_mode="r", allow_pickle=False)
    expected = np.moveaxis(np.arange(72, dtype=np.float64).reshape(2, 3, 4, 3), -1, 0)
    np.testing.assert_array_equal(field, expected)
    assert _sha256_file(saved.path) == saved.sha256
    completed = json.loads((path / "completed.json").read_text())
    assert completed["optimizer"]["optimizer_stop_condition"] == "synthetic iteration limit"
    assert completed["field_payload_bytes"] == expected.nbytes
    assert completed["peak_rss_bytes"] is None
    assert completed["registration_wall_seconds"] >= 0
    assert completed["registration_process_cpu_seconds"] >= 0
    events = [json.loads(line) for line in (path / "progress.jsonl").read_text().splitlines()]
    assert [x["iteration"] for x in events] == [0, 0]
    manifest = json.loads((path / "started.json").read_text())["manifest"]
    assert (
        manifest["data_identity"]["fixed"]["sha256"]
        != manifest["data_identity"]["moving"]["sha256"]
    )
    assert (
        read_field_checkpoint_record(
            path / "field",
            expected_manifest=manifest,
            expected_shape=expected.shape,
            expected_dtype=expected.dtype,
        )
        == saved
    )
    with pytest.raises(FileExistsError):
        execute(path)


@pytest.mark.parametrize("mode", ["exception", "missing_stop", "geometry", "nan", "disk_full"])
def test_failed_attempts_remain_claimed_and_never_publish_success(tmp_path, monkeypatch, mode):
    calls = []

    def fail(fixed, moving, **kwargs):
        calls.append(True)
        if mode == "exception":
            raise RuntimeError("synthetic backend failure")
        if mode == "missing_stop":
            return np.zeros((3, 2, 3, 4))
        result = backend(fixed, moving, **kwargs)
        if mode == "geometry":
            return result[:, :, :, :2]
        if mode == "nan":
            result[0, 0, 0, 0] = np.nan
        return result

    monkeypatch.setattr(member, "baseline_bspline_registration", fail)
    if mode == "disk_full":

        def no_space(*args, **kwargs):
            raise OSError("synthetic ENOSPC")

        monkeypatch.setattr(member, "save_field_checkpoint", no_space)
    path = tmp_path / "attempt"
    with pytest.raises((RuntimeError, ValueError, OSError)):
        execute(path)
    assert not (path / "completed.json").exists()
    assert json.loads((path / "failed.json").read_text())["status"] == "failed"
    with pytest.raises(FileExistsError):
        execute(path)
    assert len(calls) == 1
