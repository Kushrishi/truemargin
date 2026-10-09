"""Execute one explicitly requested registration and retain its completed field.

This API has no campaign, retry, optimizer resume or remote-transfer behavior.
The caller remains responsible for study authorization and durable remote copies.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from truemargin.field_cache import CachedField
from truemargin.field_checkpoint import save_field_checkpoint
from truemargin.provenance import build_manifest
from truemargin.registration import baseline_bspline_registration


@dataclass(frozen=True)
class RegistrationSettings:
    """All settings are explicit; spacing uses physical x, y, z order."""

    mesh_size: int
    max_iterations: int
    spacing: tuple[float, ...]
    center_first: bool
    metric_bins: int
    gradient_convergence_tolerance: float

    def validate(self, ndim: int) -> None:
        for name, minimum in (("mesh_size", 1), ("max_iterations", 1), ("metric_bins", 2)):
            value = getattr(self, name)
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if type(self.center_first) is not bool:
            raise ValueError("center_first must be boolean")
        if len(self.spacing) != ndim or any(not np.isfinite(x) or x <= 0 for x in self.spacing):
            raise ValueError("spacing must be finite, positive and match image dimensions")
        if (
            not np.isfinite(self.gradient_convergence_tolerance)
            or self.gradient_convergence_tolerance <= 0
        ):
            raise ValueError("gradient convergence tolerance must be finite and positive")


def _image_identity(image: np.ndarray) -> dict:
    if image.ndim not in (2, 3) or image.dtype.kind not in "iuf" or not image.flags.c_contiguous:
        raise ValueError("images must be real C-contiguous 2D or 3D arrays")
    if any(size < 1 for size in image.shape):
        raise ValueError("image dimensions must be nonempty")
    flat = image.reshape(-1)
    digest = hashlib.sha256()
    for start in range(0, flat.size, 65536):
        block = flat[start : start + 65536]
        if not np.isfinite(block).all():
            raise ValueError("images must contain finite values")
        digest.update(memoryview(block).cast("B"))
    return {"sha256": digest.hexdigest(), "shape": list(image.shape), "dtype": image.dtype.str}


def _write_json(path: Path, record: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def execute_registration_member(
    directory: Path,
    *,
    fixed: np.ndarray,
    moving: np.ndarray,
    settings: RegistrationSettings,
    repo_root: Path,
    member_id: str,
    case_id: str,
    fixed_image_id: str,
    moving_image_id: str,
) -> CachedField:
    """Claim once, register once, save field bytes, then publish a terminal record.

    Array digests bind the actual ordered inputs; supplied identifiers are labels,
    not authentication of data origin. Progress events may repeat optimizer iteration
    indices and are retained individually. A finite returned field does not imply
    convergence. Timings measure this call in its current process, not peak RSS or
    exclusive worker CPU. Process death can leave an incomplete claimed directory.
    """
    for value in (member_id, case_id, fixed_image_id, moving_image_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("member, case and image identities must be nonblank")
    settings.validate(fixed.ndim)
    if fixed.ndim != moving.ndim:
        raise ValueError("fixed and moving image dimensions must match")
    identities: dict = {"fixed": _image_identity(fixed), "moving": _image_identity(moving)}
    identities.update(
        case_id=case_id, fixed_image_id=fixed_image_id, moving_image_id=moving_image_id
    )
    parameters = asdict(settings)
    # Use a JSON round-trip so tuples have the same representation on disk/readback.
    parameters = json.loads(json.dumps(parameters, allow_nan=False))
    packages = {}
    for package in ("numpy", "SimpleITK"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "not-installed"
    manifest = build_manifest(
        repo_root=repo_root,
        experiment="single-registration-member",
        artifact_id=member_id,
        parameters={"registration": parameters, "packages": packages},
        data_identity=identities,
        source_files=[
            f"src/truemargin/{name}.py"
            for name in ("registration", "registration_member", "field_checkpoint", "provenance")
        ],
    )
    directory.mkdir()  # Existing successful OR failed attempts cannot be rerun here.
    started = time.perf_counter()
    cpu_started = time.process_time()
    stop = None
    phase = "registration"

    def completed(record):
        nonlocal stop
        if stop is not None:
            raise ValueError("registration emitted more than one optimizer stop record")
        stop = dict(record)

    try:
        _write_json(directory / "started.json", {"manifest": manifest, "automatic_retry": False})
        with (directory / "progress.jsonl").open("x", encoding="utf-8") as log:

            def progress(iteration, metric):
                log.write(
                    json.dumps(
                        {
                            "iteration": int(iteration),
                            "metric": float(metric),
                            "elapsed_seconds": time.perf_counter() - started,
                        },
                        allow_nan=False,
                    )
                    + "\n"
                )
                log.flush()
                os.fsync(log.fileno())

            field = baseline_bspline_registration(
                fixed,
                moving,
                **asdict(settings),
                progress_callback=progress,
                completion_callback=completed,
            )
        registration_wall = time.perf_counter() - started
        registration_cpu = time.process_time() - cpu_started
        if stop is None:
            raise ValueError("registration returned without an optimizer stop record")
        if field.shape != (fixed.ndim, *fixed.shape):
            raise ValueError("returned field geometry does not match fixed image")
        phase = "field_publication"
        saved = save_field_checkpoint(directory / "field", field=field, manifest=manifest)
        _write_json(
            directory / "completed.json",
            {
                "status": "completed",
                "optimizer": stop,
                "registration_wall_seconds": registration_wall,
                "registration_process_cpu_seconds": registration_cpu,
                "total_wall_seconds": time.perf_counter() - started,
                "field_sha256": saved.sha256,
                "field_shape": list(field.shape),
                "field_dtype": field.dtype.str,
                "field_payload_bytes": field.nbytes,
                "remote_retention": "not_verified",
                "peak_rss_bytes": None,
            },
        )
        return saved
    except BaseException as error:
        try:
            _write_json(
                directory / "failed.json",
                {
                    "status": "failed",
                    "phase": phase,
                    "error_type": type(error).__name__,
                    "elapsed_seconds": time.perf_counter() - started,
                    "optimizer": stop,
                    "automatic_retry": False,
                },
            )
        except (OSError, ValueError) as record_error:
            error.add_note(f"Failure record could not be saved: {type(record_error).__name__}")
        raise
