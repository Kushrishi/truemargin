"""Copy and verify a completed registration member using an external receipt.

Destinations are filesystem paths, including operator-mounted storage. This does
not provision storage or prove that a mount is persistent. Keep the returned
receipt somewhere independent of the copy being checked.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import numpy as np

from truemargin.field_checkpoint import read_field_checkpoint_record
from truemargin.provenance import _sha256_file

FILES = (
    "started.json",
    "progress.jsonl",
    "field/field.npy",
    "field/checkpoint.npz",
    "completed.json",
)


def _regular_file(root: Path, name: str) -> Path:
    path = root / name
    if root.is_symlink() or any((root / p).is_symlink() for p in path.relative_to(root).parents):
        raise ValueError("member paths must not be symbolic links")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing regular member file: {name}")
    return path


def _json(path: Path) -> dict:
    def invalid(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError("member record must be an object")
    return value


def _validate_member(root: Path, expected_manifest: dict) -> None:
    for name in FILES:
        _regular_file(root, name)
    if (root / "failed.json").exists():
        raise ValueError("failed attempts cannot be retained as completed members")
    started = _json(root / "started.json")
    if started.get("manifest") != expected_manifest:
        raise ValueError("started manifest differs from expected producer provenance")
    completed = _json(root / "completed.json")
    if completed.get("status") != "completed":
        raise ValueError("member has no completed terminal status")
    field = np.load(root / "field/field.npy", mmap_mode="r", allow_pickle=False)
    if not isinstance(field, np.memmap):
        raise ValueError("completed field must be an NPY array")
    record = read_field_checkpoint_record(
        root / "field",
        expected_manifest=expected_manifest,
        expected_shape=field.shape,
        expected_dtype=field.dtype,
    )
    if (
        list(field.shape) != completed.get("field_shape")
        or field.dtype.str != completed.get("field_dtype")
        or field.nbytes != completed.get("field_payload_bytes")
        or record.sha256 != completed.get("field_sha256")
        or _sha256_file(record.path) != record.sha256
    ):
        raise ValueError("field identity differs from terminal or checkpoint record")


def verify_retained_member(directory: Path, *, receipt: dict, expected_manifest: dict) -> dict:
    """Verify all copied bytes against a separately retained producer receipt."""
    if receipt.get("schema_version") != "registration-member-retention/1":
        raise ValueError("unsupported retention receipt")
    files = receipt.get("files")
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError("receipt must identify exactly the completed member files")
    for name in FILES:
        record = files[name]
        path = _regular_file(directory, name)
        if (
            not isinstance(record, dict)
            or path.stat().st_size != record.get("bytes")
            or _sha256_file(path) != record.get("sha256")
        ):
            raise ValueError(f"retained bytes differ from producer receipt: {name}")
    _validate_member(directory, expected_manifest)
    return {
        "verified": True,
        "member_id": expected_manifest["artifact_id"],
        "file_bytes": sum(files[name]["bytes"] for name in FILES),
    }


def retain_registration_member(source: Path, destination: Path, *, expected_manifest: dict) -> dict:
    """Copy a completed immutable member once, then verify every copied byte.

    The completion record is copied last. An interruption leaves a claimed,
    incomplete destination; it never authorizes replaying registration. No existing
    destination is overwritten. Streaming buffers are bounded to 1 MiB.
    """
    _validate_member(source, expected_manifest)
    receipt: dict = {
        "schema_version": "registration-member-retention/1",
        "files": {
            name: {"bytes": (source / name).stat().st_size, "sha256": _sha256_file(source / name)}
            for name in FILES
        },
    }
    destination.mkdir()
    (destination / "field").mkdir()
    for name in FILES:
        src = _regular_file(source, name)
        target = destination / name
        # Rename the final marker only after its entire content is synced.
        partial = target.with_name(target.name + ".partial")
        with src.open("rb") as reader, partial.open("xb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        if (
            partial.stat().st_size != receipt["files"][name]["bytes"]
            or _sha256_file(partial) != receipt["files"][name]["sha256"]
        ):
            raise ValueError(f"source changed during retention: {name}")
        partial.rename(target)
    verify_retained_member(destination, receipt=receipt, expected_manifest=expected_manifest)
    return receipt
