import hashlib
import shutil
from dataclasses import replace

import numpy as np
import pytest

from truemargin.ensemble import summarize_fields, summarize_fields_blockwise
from truemargin.field_cache import CachedField, open_verified_field_cache

SHAPE = (3, 2, 4, 5)
DTYPE = np.dtype("float64")
IDS = [f"member-{index}" for index in range(9)]


def _record(path, member_id):
    return CachedField(member_id, path, hashlib.sha256(path.read_bytes()).hexdigest())


def _cache(tmp_path):
    rng = np.random.default_rng(42)
    fields = [rng.normal(size=SHAPE) for _ in IDS]
    records = []
    for member_id, field in zip(IDS, fields, strict=True):
        path = tmp_path / f"{member_id}.npy"
        np.save(path, field)
        records.append(_record(path, member_id))
    return fields, records


def _open(records, **kwargs):
    arguments = dict(expected_member_ids=IDS, expected_shape=SHAPE, expected_dtype=DTYPE)
    arguments.update(kwargs)
    return open_verified_field_cache(records, **arguments)


def test_copied_cache_reopens_in_frozen_order_and_matches_original(tmp_path):
    fields, records = _cache(tmp_path)
    copied = tmp_path / "copied"
    copied.mkdir()
    copy_records = []
    for record in reversed(records):
        target = copied / record.path.name
        shutil.copyfile(record.path, target)
        copy_records.append(replace(record, path=target))
    reopened = _open(copy_records)
    assert all(isinstance(field, np.memmap) and not field.flags.writeable for field in reopened)
    for original, recovered in zip(fields, reopened, strict=True):
        np.testing.assert_array_equal(original, recovered)
    with pytest.raises(ValueError, match="read-only"):
        reopened[0][0, 0, 0, 0] = 0
    for expected, actual in zip(
        summarize_fields(fields), summarize_fields_blockwise(reopened, block_voxels=13), strict=True
    ):
        np.testing.assert_array_equal(expected, actual)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "unexpected"])
def test_incomplete_or_wrong_members_rejected_before_reading_files(tmp_path, defect):
    _, records = _cache(tmp_path)
    if defect == "missing":
        records.pop()
    elif defect == "duplicate":
        records[-1] = records[0]
    else:
        records[-1] = replace(records[-1], member_id="other")
    records = [replace(record, path=tmp_path / "absent.npy") for record in records]
    with pytest.raises(ValueError, match="member"):
        _open(records)


@pytest.mark.parametrize("damage", ["truncated", "changed"])
def test_damaged_copy_rejected_against_original_digest(tmp_path, damage):
    _, records = _cache(tmp_path)
    path = records[0].path
    if damage == "truncated":
        path.write_bytes(path.read_bytes()[:16])
    else:
        np.save(path, np.zeros(SHAPE))
    with pytest.raises(ValueError, match="checksum mismatch"):
        _open(records)


@pytest.mark.parametrize("defect", ["shape", "dtype", "fortran", "npz"])
def test_matching_digest_does_not_bypass_array_contract(tmp_path, defect):
    _, records = _cache(tmp_path)
    path = records[0].path
    if defect == "shape":
        np.save(path, np.zeros((3, 2, 4, 4)))
    elif defect == "dtype":
        np.save(path, np.zeros(SHAPE, dtype=np.float32))
    elif defect == "fortran":
        np.save(path, np.asfortranarray(np.zeros(SHAPE)))
    else:
        with path.open("wb") as target:
            np.savez(target, field=np.zeros(SHAPE))
    records[0] = _record(path, records[0].member_id)
    with pytest.raises(ValueError, match="shape or dtype|contiguous|NPY"):
        _open(records)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expected_member_ids": IDS[:-1] + [IDS[0]]},
        {"expected_member_ids": [""]},
        {"expected_shape": (4, 2, 4, 5)},
        {"expected_shape": (3, True, 4, 5)},
        {"expected_dtype": np.dtype("int64")},
    ],
)
def test_invalid_expected_contract(tmp_path, kwargs):
    _, records = _cache(tmp_path)
    with pytest.raises(ValueError):
        _open(records, **kwargs)


def test_invalid_digest_rejected(tmp_path):
    _, records = _cache(tmp_path)
    records[0] = replace(records[0], sha256="not-a-digest")
    with pytest.raises(ValueError, match="SHA-256"):
        _open(records)
