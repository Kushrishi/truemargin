"""Training-only Learn2Reg LungCT discovery and geometry preflight.

This module intentionally has no landmark reader. It establishes the image/mask
identity and physical-geometry boundary before held-out manual landmarks are
accessed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_SCAN_PATTERN = re.compile(r"^case_(?P<case>\\d{3})_(?P<phase>exp|insp)\\.nii\\.gz$")


@dataclass(frozen=True)
class LungCTPair:
    case_id: str
    fixed_path: Path
    moving_path: Path
    fixed_mask_path: Path | None
    moving_mask_path: Path | None


@dataclass(frozen=True)
class LungCTGeometry:
    case_id: str
    size_xyz: tuple[int, int, int]
    shape_zyx: tuple[int, int, int]
    spacing_xyz: tuple[float, float, float]
    origin_xyz: tuple[float, float, float]
    direction: tuple[float, ...]
    diagonal_mm: float
    fixed_min: float
    fixed_max: float
    moving_min: float
    moving_max: float


def discover_training_pairs(root: Path) -> list[LungCTPair]:
    """Discover complete expiration/inspiration pairs under root/scans."""
    scans = root / "scans"
    if not scans.is_dir():
        raise ValueError(f"missing scans directory: {scans}")

    phases: dict[str, dict[str, Path]] = {}
    for path in sorted(scans.iterdir()):
        if not path.is_file():
            continue
        match = _SCAN_PATTERN.match(path.name)
        if match is None:
            continue
        case_id = match.group("case")
        phase = match.group("phase")
        if phase in phases.setdefault(case_id, {}):
            raise ValueError(f"duplicate {phase} image for case_{case_id}")
        phases[case_id][phase] = path

    if not phases:
        raise ValueError("no case_###_{exp,insp}.nii.gz scans found")

    pairs: list[LungCTPair] = []
    for case_id in sorted(phases):
        found = phases[case_id]
        missing = {"exp", "insp"} - set(found)
        if missing:
            raise ValueError(
                f"case_{case_id} is incomplete; missing: {', '.join(sorted(missing))}"
            )

        masks = root / "lungMasks"
        fixed_mask = masks / f"case_{case_id}_exp.nii.gz"
        moving_mask = masks / f"case_{case_id}_insp.nii.gz"
        pairs.append(
            LungCTPair(
                case_id=case_id,
                fixed_path=found["exp"],
                moving_path=found["insp"],
                fixed_mask_path=fixed_mask if fixed_mask.is_file() else None,
                moving_mask_path=moving_mask if moving_mask.is_file() else None,
            )
        )
    return pairs


def _close_tuple(left: tuple[float, ...], right: tuple[float, ...], atol: float = 1e-6) -> bool:
    return len(left) == len(right) and bool(
        np.allclose(np.asarray(left), np.asarray(right), rtol=0.0, atol=atol)
    )


def inspect_pair(pair: LungCTPair) -> LungCTGeometry:
    """Read one image pair and verify the geometry used by the frozen estimator."""
    try:
        import SimpleITK as sitk
    except ImportError as exc:
        raise ImportError("SimpleITK is required for external LungCT preflight") from exc

    fixed_image = sitk.ReadImage(str(pair.fixed_path))
    moving_image = sitk.ReadImage(str(pair.moving_path))

    if fixed_image.GetDimension() != 3 or moving_image.GetDimension() != 3:
        raise ValueError(f"case_{pair.case_id}: both images must be 3-D")

    fixed_size = tuple(int(value) for value in fixed_image.GetSize())
    moving_size = tuple(int(value) for value in moving_image.GetSize())
    if fixed_size != moving_size:
        raise ValueError(
            f"case_{pair.case_id}: fixed/moving sizes differ: {fixed_size} vs {moving_size}"
        )

    fixed_spacing = tuple(float(value) for value in fixed_image.GetSpacing())
    moving_spacing = tuple(float(value) for value in moving_image.GetSpacing())
    if not _close_tuple(fixed_spacing, moving_spacing):
        raise ValueError(
            f"case_{pair.case_id}: fixed/moving spacing differs: "
            f"{fixed_spacing} vs {moving_spacing}"
        )
    if any(not math.isfinite(value) or value <= 0.0 for value in fixed_spacing):
        raise ValueError(f"case_{pair.case_id}: spacing must be finite and positive")

    fixed_origin = tuple(float(value) for value in fixed_image.GetOrigin())
    moving_origin = tuple(float(value) for value in moving_image.GetOrigin())
    if not _close_tuple(fixed_origin, moving_origin):
        raise ValueError(
            f"case_{pair.case_id}: fixed/moving origins differ: {fixed_origin} vs {moving_origin}"
        )

    fixed_direction = tuple(float(value) for value in fixed_image.GetDirection())
    moving_direction = tuple(float(value) for value in moving_image.GetDirection())
    if not _close_tuple(fixed_direction, moving_direction):
        raise ValueError(f"case_{pair.case_id}: fixed/moving direction matrices differ")

    fixed = sitk.GetArrayFromImage(fixed_image).astype(np.float64, copy=False)
    moving = sitk.GetArrayFromImage(moving_image).astype(np.float64, copy=False)
    if fixed.ndim != 3 or moving.ndim != 3 or fixed.shape != moving.shape:
        raise ValueError(f"case_{pair.case_id}: array geometry is inconsistent")
    if not np.isfinite(fixed).all() or not np.isfinite(moving).all():
        raise ValueError(f"case_{pair.case_id}: image arrays contain non-finite values")

    extents = [
        max(size - 1, 0) * spacing
        for size, spacing in zip(fixed_size, fixed_spacing, strict=True)
    ]
    diagonal = float(math.sqrt(sum(value * value for value in extents)))

    return LungCTGeometry(
        case_id=pair.case_id,
        size_xyz=fixed_size,
        shape_zyx=tuple(int(value) for value in fixed.shape),
        spacing_xyz=fixed_spacing,
        origin_xyz=fixed_origin,
        direction=fixed_direction,
        diagonal_mm=diagonal,
        fixed_min=float(fixed.min()),
        fixed_max=float(fixed.max()),
        moving_min=float(moving.min()),
        moving_max=float(moving.max()),
    )


def preflight_training(root: Path, expected_pairs: int | None = 20) -> list[LungCTGeometry]:
    """Inspect training images only; no landmark path is opened by this function."""
    pairs = discover_training_pairs(root)
    if expected_pairs is not None and len(pairs) != expected_pairs:
        raise ValueError(f"expected {expected_pairs} complete pairs, found {len(pairs)}")
    return [inspect_pair(pair) for pair in pairs]
