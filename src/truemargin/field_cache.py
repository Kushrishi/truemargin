"""Verified read-only reopening of a complete, immutable NPY member cache.

Expected records must come from reviewed producer provenance, not hashes computed
from the copy being checked. This module performs no registration, transfer,
eviction, retry or optimizer resume. Files must remain immutable while mapped.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from truemargin.provenance import _sha256_file


@dataclass(frozen=True)
class CachedField:
    member_id: str
    path: Path
    sha256: str


def open_verified_field_cache(
    records: Sequence[CachedField],
    *,
    expected_member_ids: Sequence[str],
    expected_shape: tuple[int, ...],
    expected_dtype: np.dtype,
) -> list[np.ndarray]:
    """Verify every member before returning maps in the declared frozen order.

    Missing, duplicate or unexpected identities reject the entire cache, including
    a survivor-only subset. Byte identity, shape and dtype are checked separately.
    File hashing uses bounded buffers; fields are mapped read-only, without a
    dense ensemble stack. The existing blockwise summarizer checks finite values.

    These checks cannot authenticate self-declared metadata or prove remote
    retention. Scientific settings/input/direction identity must be validated by
    the caller's provenance contract before supplying the expected records.
    """
    ids = list(expected_member_ids)
    if len(ids) < 2 or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("declare at least two nonempty expected member identities")
    if len(set(ids)) != len(ids):
        raise ValueError("expected member identities must be unique")
    if (
        len(expected_shape) < 3
        or expected_shape[0] != len(expected_shape) - 1
        or any(
            isinstance(size, bool) or not isinstance(size, int) or size < 1
            for size in expected_shape
        )
    ):
        raise ValueError("expected shape must have component-first spatial geometry")
    dtype = np.dtype(expected_dtype)
    if dtype.kind != "f":
        raise ValueError("expected dtype must be real floating point")
    by_id: dict[str, CachedField] = {}
    for record in records:
        if record.member_id in by_id:
            raise ValueError(f"duplicate cached member: {record.member_id}")
        if len(record.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in record.sha256
        ):
            raise ValueError(f"invalid SHA-256 for member: {record.member_id}")
        by_id[record.member_id] = record
    if set(by_id) != set(ids):
        raise ValueError("cache must contain exactly the expected member identities")

    fields: list[np.ndarray] = []
    for member_id in ids:
        record = by_id[member_id]
        if _sha256_file(record.path) != record.sha256:
            raise ValueError(f"cached field checksum mismatch: {member_id}")
        field = np.load(record.path, mmap_mode="r", allow_pickle=False)
        if not isinstance(field, np.memmap):
            # Only NPY arrays are supported; NPZ archives do not provide field maps.
            if isinstance(field, np.lib.npyio.NpzFile):
                field.close()
            raise ValueError(f"cached field must be a memory-mapped NPY array: {member_id}")
        if field.shape != expected_shape or field.dtype != dtype:
            raise ValueError(f"cached field shape or dtype mismatch: {member_id}")
        if not field.flags.c_contiguous:
            raise ValueError(f"cached field must have contiguous spatial axes: {member_id}")
        fields.append(field)
    return fields
