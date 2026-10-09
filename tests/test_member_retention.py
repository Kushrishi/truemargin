import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from truemargin import member_retention as retention
from truemargin import registration_member as producer


def completed_member(tmp_path, monkeypatch):
    def synthetic(fixed, moving, **options):
        options["progress_callback"](0, -1.0)
        options["completion_callback"](
            {"optimizer_stop_condition": "synthetic", "optimizer_iteration": 1}
        )
        return np.arange(72, dtype=np.float64).reshape(3, 2, 3, 4)

    monkeypatch.setattr(producer, "baseline_bspline_registration", synthetic)
    source = tmp_path / "source"
    producer.execute_registration_member(
        source,
        fixed=np.zeros((2, 3, 4)),
        moving=np.ones((2, 3, 4)),
        settings=producer.RegistrationSettings(3, 15, (1.0, 1.0, 1.0), False, 50, 1e-5),
        repo_root=Path(__file__).resolve().parents[1],
        member_id="synthetic",
        case_id="synthetic",
        fixed_image_id="fixed",
        moving_image_id="moving",
    )
    return source, json.loads((source / "started.json").read_text())["manifest"]


def test_recovery_after_source_is_unavailable(tmp_path, monkeypatch):
    source, manifest = completed_member(tmp_path, monkeypatch)
    destination = tmp_path / "retained"
    receipt = retention.retain_registration_member(source, destination, expected_manifest=manifest)
    source.rename(tmp_path / "unavailable-original")
    result = retention.verify_retained_member(
        destination, receipt=receipt, expected_manifest=manifest
    )
    assert result["verified"] and result["member_id"] == "synthetic"
    np.testing.assert_array_equal(
        np.load(destination / "field/field.npy"), np.arange(72).reshape(3, 2, 3, 4)
    )
    with pytest.raises(FileExistsError):
        retention.retain_registration_member(destination, destination, expected_manifest=manifest)


@pytest.mark.parametrize("name", retention.FILES)
def test_any_corrupted_member_file_is_rejected(tmp_path, monkeypatch, name):
    source, manifest = completed_member(tmp_path, monkeypatch)
    destination = tmp_path / "retained"
    receipt = retention.retain_registration_member(source, destination, expected_manifest=manifest)
    path = destination / name
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)
    with pytest.raises(ValueError, match="retained bytes differ"):
        retention.verify_retained_member(destination, receipt=receipt, expected_manifest=manifest)


def test_interrupted_copy_never_publishes_completion_or_retries(tmp_path, monkeypatch):
    source, manifest = completed_member(tmp_path, monkeypatch)
    destination = tmp_path / "retained"
    original = shutil.copyfileobj
    calls = 0

    def interrupt(reader, writer, length):
        nonlocal calls
        calls += 1
        if calls == 3:
            writer.write(reader.read(32))
            raise OSError("simulated unavailable destination")
        return original(reader, writer, length)

    monkeypatch.setattr(retention.shutil, "copyfileobj", interrupt)
    with pytest.raises(OSError):
        retention.retain_registration_member(source, destination, expected_manifest=manifest)
    assert not (destination / "completed.json").exists()
    assert (destination / "field/field.npy.partial").stat().st_size == 32
    with pytest.raises(FileExistsError):
        retention.retain_registration_member(source, destination, expected_manifest=manifest)
    assert calls == 3


def test_failed_or_wrong_provenance_source_is_not_copied(tmp_path, monkeypatch):
    source, manifest = completed_member(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="producer provenance"):
        retention.retain_registration_member(source, tmp_path / "bad", expected_manifest={})
    (source / "failed.json").write_text("{}")
    with pytest.raises(ValueError, match="failed attempts"):
        retention.retain_registration_member(source, tmp_path / "bad", expected_manifest=manifest)
    assert not (tmp_path / "bad").exists()


def test_symlinked_field_is_not_followed(tmp_path, monkeypatch):
    source, manifest = completed_member(tmp_path, monkeypatch)
    field = source / "field"
    field.rename(tmp_path / "outside")
    field.symlink_to(tmp_path / "outside", target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        retention.retain_registration_member(source, tmp_path / "bad", expected_manifest=manifest)
