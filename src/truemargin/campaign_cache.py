"""Recover and summarize completed members without executing registration.

Expected manifests and retention receipts must be supplied from independently
reviewed producer records. Do not derive them from a copy being verified. This
module does not authenticate data origin, authorize a study, or resume a worker.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from truemargin.ensemble import summarize_fields_blockwise
from truemargin.field_cache import CachedField, open_verified_field_cache
from truemargin.hyperparameter import CENTER_FIRST, CONFIGS, MAX_ITERATIONS, MESH_SIZE
from truemargin.member_retention import retain_registration_member, verify_retained_member
from truemargin.registration_member import RegistrationSettings


@dataclass(frozen=True)
class RetainedMember:
    directory: Path
    expected_manifest: dict
    receipt: dict


def _geometry(manifest: dict) -> tuple[tuple[int, ...], tuple[float, ...]]:
    if manifest.get("experiment") != "single-registration-member":
        raise ValueError("single-registration-member manifest required")
    if not isinstance(manifest.get("artifact_id"), str) or not manifest["artifact_id"].strip():
        raise ValueError("nonblank member identity required")
    data = manifest["data_identity"]
    if data["case_id"] not in {f"4DCT{i}" for i in range(1, 11)}:
        raise ValueError("DIR-Lab case identity required")
    if {data["fixed_image_id"], data["moving_image_id"]} != {"T00", "T50"}:
        raise ValueError("T00/T50 direction required")
    shape = tuple(data["fixed"]["shape"])
    if (
        len(shape) != 3
        or any(type(n) is not int or n < 1 for n in shape)
        or list(shape) != data["moving"]["shape"]
    ):
        raise ValueError("matching three-dimensional image shapes required")
    settings = RegistrationSettings(**manifest["parameters"]["registration"])
    settings.validate(3)
    if (
        settings.mesh_size != MESH_SIZE
        or settings.max_iterations != MAX_ITERATIONS
        or settings.center_first != CENTER_FIRST
        or (settings.metric_bins, settings.gradient_convergence_tolerance) not in CONFIGS
    ):
        raise ValueError("member must use the frozen hyperparameter grid")
    return (3, *shape), tuple(settings.spacing)


def _check_field(field: np.ndarray, spacing: tuple[float, ...], block_voxels: int) -> None:
    """Apply the frozen finite/mean-displacement gate with bounded temporaries."""
    flat = field.reshape(3, -1)
    diagonal = float(np.linalg.norm((np.array(field.shape[1:][::-1]) - 1) * spacing))
    if diagonal <= 0 or not np.isfinite(diagonal):
        raise ValueError("positive finite physical grid diagonal required")
    total = 0.0
    for start in range(0, flat.shape[1], block_voxels):
        block = flat[:, start : start + block_voxels]
        if not np.isfinite(block).all():
            raise ValueError("field values must be finite")
        with np.errstate(over="ignore", invalid="ignore"):
            magnitudes = np.sqrt(np.sum(block * block, axis=0))
        if not np.isfinite(magnitudes).all():
            raise ValueError("displacement magnitude must be finite")
        total += float(np.sum(magnitudes, dtype=np.float64))
    if total / flat.shape[1] > diagonal:
        raise ValueError("mean displacement exceeds physical grid diagonal")


def _block_size(block_voxels: int) -> None:
    if type(block_voxels) is not int or block_voxels < 2:
        raise ValueError("block_voxels must be an integer of at least two")


def verify_campaign_member(member: RetainedMember, *, block_voxels: int = 65536) -> CachedField:
    """Verify real producer schemas, then scan the entire mapped field."""
    _block_size(block_voxels)
    shape, spacing = _geometry(member.expected_manifest)
    verify_retained_member(
        member.directory, receipt=member.receipt, expected_manifest=member.expected_manifest
    )
    path = member.directory / "field/field.npy"
    field = np.load(path, mmap_mode="r", allow_pickle=False)
    if field.shape != shape or field.dtype != np.dtype("<f8") or not field.flags.c_contiguous:
        raise ValueError("component-first contiguous float64 field geometry required")
    _check_field(field, spacing, block_voxels)
    return CachedField(
        member.expected_manifest["artifact_id"],
        path,
        member.receipt["files"]["field/field.npy"]["sha256"],
    )


def recover_campaign_member(
    member: RetainedMember, destination: Path, *, block_voxels: int = 65536
) -> RetainedMember:
    """Copy once using existing retention, preserving interrupted destinations.

    An existing destination is never overwritten. This is file recovery, not an
    optimizer retry. The result retains the independently supplied receipt.
    """
    verify_campaign_member(member, block_voxels=block_voxels)
    copied_receipt = retain_registration_member(
        member.directory, destination, expected_manifest=member.expected_manifest
    )
    if copied_receipt != member.receipt:
        raise ValueError("source changed relative to independent receipt during recovery")
    recovered = RetainedMember(destination, member.expected_manifest, member.receipt)
    verify_campaign_member(recovered, block_voxels=block_voxels)
    return recovered


def summarize_campaign_group(
    members: Sequence[RetainedMember], *, block_voxels: int = 65536
) -> tuple[np.ndarray, np.ndarray]:
    """Require all nine configurations for one identified image pair and source.

    Maps are read-only and the accepted blockwise formula is reused. Outputs
    occupy one mean field and one scalar grid. No survivor-only estimate, field
    publication, registration execution or landmark access is performed.
    """
    _block_size(block_voxels)
    if len(members) != len(CONFIGS):
        raise ValueError("exactly nine frozen members required")
    first = members[0].expected_manifest
    shape, _ = _geometry(first)
    by_config = {}
    ids = set()
    for member in members:
        manifest = member.expected_manifest
        _geometry(manifest)
        for key in ("schema_version", "project_version", "git_sha", "code_hash", "source_files"):
            if manifest[key] != first[key]:
                raise ValueError("group producer source identities must agree")
        if (
            manifest["data_identity"] != first["data_identity"]
            or manifest["parameters"]["packages"] != first["parameters"]["packages"]
            or manifest["parameters"]["registration"]["spacing"]
            != first["parameters"]["registration"]["spacing"]
        ):
            raise ValueError("group image, direction, package and spacing identities must agree")
        settings = manifest["parameters"]["registration"]
        config = (settings["metric_bins"], settings["gradient_convergence_tolerance"])
        member_id = manifest["artifact_id"]
        if config in by_config or member_id in ids:
            raise ValueError("duplicate configuration or member identity")
        by_config[config] = member
        ids.add(member_id)
    records = [
        verify_campaign_member(by_config[config], block_voxels=block_voxels) for config in CONFIGS
    ]
    fields = open_verified_field_cache(
        records,
        expected_member_ids=[record.member_id for record in records],
        expected_shape=shape,
        expected_dtype=np.dtype("<f8"),
    )
    return summarize_fields_blockwise(fields, block_voxels=block_voxels)
