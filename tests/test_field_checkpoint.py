import copy
import errno
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from truemargin import provenance
from truemargin.ensemble import summarize_fields, summarize_fields_blockwise
from truemargin.field_cache import open_verified_field_cache
from truemargin.field_checkpoint import read_field_checkpoint_record, save_field_checkpoint

SHAPE = (3, 2, 4, 5)


def _manifest(member):
    # Synthetic supplied provenance; no real image, archive or landmark is accessed.
    return {
        "schema_version": 1,
        "artifact_id": member,
        "git_sha": "a" * 40,
        "experiment": "synthetic-field-publication",
        "parameters": {"bins": 50},
        "data_identity": {"case": "synthetic", "direction": "forward"},
        "source_files": {"producer.py": "b" * 64},
    }


def _read(directory, manifest):
    return read_field_checkpoint_record(
        directory,
        expected_manifest=manifest,
        expected_shape=SHAPE,
        expected_dtype=np.dtype("float64"),
    )


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("layout", ["contiguous", "interleaved-vector-last"])
@pytest.mark.parametrize("block", [7, 65536])
def test_nine_saved_members_reopen_with_exact_summary_parity(tmp_path, dtype, layout, block):
    rng = np.random.default_rng(9)
    fields = [rng.normal(size=SHAPE).astype(dtype) for _ in range(9)]
    if layout == "interleaved-vector-last":
        fields = [np.moveaxis(np.ascontiguousarray(np.moveaxis(f, 0, -1)), -1, 0) for f in fields]
    records = []
    for index, field in enumerate(fields):
        member = f"synthetic-{index}"
        directory = tmp_path / member
        saved = save_field_checkpoint(
            directory, field=field, manifest=_manifest(member), block_voxels=block
        )
        assert (
            read_field_checkpoint_record(
                directory,
                expected_manifest=_manifest(member),
                expected_shape=SHAPE,
                expected_dtype=np.dtype(dtype),
            )
            == saved
        )
        records.append(saved)
    reopened = open_verified_field_cache(
        records,
        expected_member_ids=[r.member_id for r in records],
        expected_shape=SHAPE,
        expected_dtype=np.dtype(dtype),
    )
    for expected, actual in zip(
        summarize_fields(fields), summarize_fields_blockwise(reopened, block_voxels=13), strict=True
    ):
        np.testing.assert_array_equal(expected, actual)


@pytest.mark.parametrize("failure", ["field_write", "field_sync", "marker"])
def test_failed_save_has_no_completion_marker_and_cannot_be_retried(tmp_path, monkeypatch, failure):
    directory = tmp_path / "member"
    manifest = _manifest("member")

    def fail(*args, **kwargs):
        if failure == "field_write":
            args[0].write(b"partial field")
        raise OSError(errno.ENOSPC, "injected field save failure")

    if failure == "field_write":
        monkeypatch.setattr(np.lib.format, "write_array_header_2_0", fail)
    elif failure == "field_sync":
        monkeypatch.setattr(provenance.os, "fsync", fail)
    else:
        monkeypatch.setattr(provenance, "save_checkpoint", fail)
    with pytest.raises(OSError, match="injected field save failure"):
        save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest=manifest)
    assert directory.exists() and not (directory / "checkpoint.npz").exists()
    with pytest.raises(FileNotFoundError):
        _read(directory, manifest)
    with pytest.raises(FileExistsError):
        save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest=manifest)


def test_completed_directory_is_never_clobbered(tmp_path):
    directory = tmp_path / "member"
    manifest = _manifest("member")
    save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest=manifest)
    original = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(FileExistsError):
        save_field_checkpoint(directory, field=np.ones(SHAPE), manifest=manifest)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == original


@pytest.mark.parametrize("key", ["artifact_id", "parameters", "data_identity", "source_files"])
def test_wrong_provenance_is_rejected(tmp_path, key):
    directory = tmp_path / "member"
    manifest = _manifest("member")
    save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest=manifest)
    changed = copy.deepcopy(manifest)
    changed[key] = "other" if key == "artifact_id" else {"different": True}
    with pytest.raises(provenance.CheckpointProvenanceError, match="provenance mismatch"):
        _read(directory, changed)


@pytest.mark.parametrize("defect", ["shape", "dtype", "nonfinite", "fortran"])
def test_invalid_field_rejected_before_claiming_directory(tmp_path, defect):
    field = np.zeros(SHAPE)
    if defect == "shape":
        field = np.zeros((4, 2, 4, 5))
    elif defect == "dtype":
        field = field.astype(np.int64)
    elif defect == "nonfinite":
        field.flat[-1] = np.nan
    else:
        field = np.asfortranarray(field)
    directory = tmp_path / "member"
    with pytest.raises(ValueError):
        save_field_checkpoint(directory, field=field, manifest=_manifest("member"))
    assert not directory.exists()


def test_abrupt_exit_before_marker_publication_stays_incomplete(tmp_path):
    directory = tmp_path / "interrupted"
    code = """
import os, sys
import numpy as np
from pathlib import Path
from truemargin import provenance
from truemargin.field_checkpoint import save_field_checkpoint
def interrupted_marker(target, **payload):
    target.write(b'partial marker')
    target.flush()
    os._exit(17)
provenance.np.savez = interrupted_marker
save_field_checkpoint(Path(sys.argv[1]), field=np.zeros((3,2,4,5)),
                      manifest={'artifact_id':'member'})
"""
    env = dict(os.environ, PYTHONPATH=str(Path(provenance.__file__).parents[1]))
    result = subprocess.run([sys.executable, "-c", code, str(directory)], env=env, timeout=20)
    assert result.returncode == 17
    assert (directory / "field.npy").exists()
    assert not (directory / "checkpoint.npz").exists()
    with pytest.raises(FileNotFoundError):
        _read(directory, _manifest("member"))


@pytest.mark.parametrize("wrong", ["shape", "dtype"])
def test_marker_layout_must_match_expected_contract(tmp_path, wrong):
    directory = tmp_path / "member"
    manifest = _manifest("member")
    save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest=manifest)
    with pytest.raises(ValueError, match="layout metadata"):
        read_field_checkpoint_record(
            directory,
            expected_manifest=manifest,
            expected_shape=(3, 2, 4, 4) if wrong == "shape" else SHAPE,
            expected_dtype=np.dtype("float32") if wrong == "dtype" else np.dtype("float64"),
        )


@pytest.mark.parametrize("block", [0, -1, True, 1.5])
def test_invalid_block_rejected_before_claim(tmp_path, block):
    directory = tmp_path / "member"
    with pytest.raises(ValueError, match="block_voxels"):
        save_field_checkpoint(
            directory, field=np.zeros(SHAPE), manifest=_manifest("member"), block_voxels=block
        )
    assert not directory.exists()


def test_missing_member_identity_rejected_before_claim(tmp_path):
    directory = tmp_path / "member"
    with pytest.raises(ValueError, match="artifact identity"):
        save_field_checkpoint(directory, field=np.zeros(SHAPE), manifest={})
    assert not directory.exists()


@pytest.mark.parametrize("defect", ["keys", "digest"])
def test_invalid_marker_metadata_rejected(tmp_path, defect):
    directory = tmp_path / "member"
    manifest = _manifest("member")
    directory.mkdir()
    arrays = {
        "field_sha256": np.asarray("not-a-digest"),
        "field_shape": np.asarray(SHAPE, dtype=np.int64),
        "field_dtype": np.asarray(np.dtype("float64").str),
    }
    if defect == "keys":
        arrays.pop("field_shape")
    provenance.save_checkpoint(directory / "checkpoint.npz", arrays=arrays, manifest=manifest)
    with pytest.raises(ValueError, match="metadata keys|digest is invalid"):
        _read(directory, manifest)
