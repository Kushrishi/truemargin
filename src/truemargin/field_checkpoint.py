"""Non-clobbering local field publication with a provenance completion marker.

A failed save leaves its claimed directory for inspection, without a completion
marker. Nothing retries, resumes an optimizer, deletes a member or runs a campaign.
Remote retention and parent-directory power-loss durability are not qualified.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from truemargin import provenance
from truemargin.field_cache import CachedField


def _member_id(manifest: Mapping[str, Any]) -> str:
    member_id = manifest.get("artifact_id")
    if not isinstance(member_id, str) or not member_id:
        raise ValueError("field provenance requires a nonempty artifact identity")
    return member_id


def save_field_checkpoint(
    directory: Path, *, field: np.ndarray, manifest: Mapping[str, Any], block_voxels: int = 65536
) -> CachedField:
    """Claim a fresh directory, sync the field, then publish its NPZ marker.

    Input must be a finite floating-point field with component-first geometry and
    spatial axes that reshape without copying. Interleaved SimpleITK vector views
    are supported. C-order output uses bounded byte buffers, without a full-field
    transpose/copy. No dtype conversion or estimator change occurs. The caller supplies
    reviewed case/direction/input/configuration/source provenance and separately
    retains optimizer-stop, timing and failure evidence. Saving bytes cannot prove
    that a registration occurred or authorize it.
    """
    member_id = _member_id(manifest)
    if isinstance(block_voxels, bool) or not isinstance(block_voxels, int) or block_voxels < 1:
        raise ValueError("block_voxels must be a positive integer")
    if (
        field.ndim < 3
        or field.shape[0] != field.ndim - 1
        or any(size < 1 for size in field.shape)
        or field.dtype.kind != "f"
    ):
        raise ValueError("field must have floating-point component-first geometry")
    for axis in range(1, field.ndim - 1):
        if field.strides[axis] != field.strides[axis + 1] * field.shape[axis + 1]:
            raise ValueError("field spatial axes must reshape without copying")
    flat = field.reshape(field.shape[0], -1)
    if not np.shares_memory(field, flat):
        raise ValueError("field spatial axes must reshape without copying")
    for start in range(0, flat.shape[1], block_voxels):
        if not np.isfinite(flat[:, start : start + block_voxels]).all():
            raise ValueError("field values must be finite")
    # Exclusive directory creation refuses an existing completed or failed attempt.
    directory.mkdir()
    path = directory / "field.npy"
    with path.open("xb") as target:
        np.lib.format.write_array_header_2_0(
            target,
            {
                "descr": np.lib.format.dtype_to_descr(field.dtype),
                "fortran_order": False,
                "shape": field.shape,
            },
        )
        for component in range(field.shape[0]):
            for start in range(0, flat.shape[1], block_voxels):
                target.write(flat[component, start : start + block_voxels].tobytes(order="C"))
        target.flush()
        os.fsync(target.fileno())
    digest = provenance._sha256_file(path)
    provenance.save_checkpoint(
        directory / "checkpoint.npz",
        arrays={
            "field_sha256": np.asarray(digest),
            "field_shape": np.asarray(field.shape, dtype=np.int64),
            "field_dtype": np.asarray(field.dtype.str),
        },
        manifest=manifest,
    )
    return CachedField(member_id, path, digest)


def read_field_checkpoint_record(
    directory: Path,
    *,
    expected_manifest: Mapping[str, Any],
    expected_shape: tuple[int, ...],
    expected_dtype: np.dtype,
) -> CachedField:
    """Read a completion marker only when its provenance and layout match.

    The returned record must pass ``open_verified_field_cache`` before its field
    is used; this function checks metadata, not payload bytes or finite values.
    Missing completion markers remain incomplete even if a field file exists.
    """
    member_id = _member_id(expected_manifest)
    data = provenance.load_checkpoint(
        directory / "checkpoint.npz", expected_manifest=expected_manifest
    )
    if set(data) != {"field_sha256", "field_shape", "field_dtype"}:
        raise ValueError("field checkpoint metadata keys do not match")
    shape, dtype, digest = data["field_shape"], data["field_dtype"], data["field_sha256"]
    if (
        shape.dtype != np.dtype("int64")
        or shape.shape != (len(expected_shape),)
        or not np.array_equal(shape, expected_shape)
        or dtype.shape != ()
        or dtype.dtype.kind != "U"
        or str(dtype.item()) != np.dtype(expected_dtype).str
        or digest.shape != ()
        or digest.dtype.kind != "U"
    ):
        raise ValueError("field checkpoint layout metadata does not match")
    digest_value = str(digest.item())
    if len(digest_value) != 64 or any(c not in "0123456789abcdef" for c in digest_value):
        raise ValueError("field checkpoint digest is invalid")
    return CachedField(member_id, directory / "field.npy", digest_value)
