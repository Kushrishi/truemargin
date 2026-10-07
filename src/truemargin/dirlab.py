"""Pre-outcome DIR-Lab 4DCT geometry and coordinate conventions.

This module deliberately performs no file I/O and has no landmark-file reader.
It contains only public, non-outcome case geometry plus coordinate conversions
that can be tested on synthetic values before any held-out landmark is opened.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DirLabCaseGeometry:
    """Public image geometry for one DIR-Lab 4DCT case.

    ``size_xyz`` follows DIR-Lab's documented coordinate order: RL, AP, SI.
    ``spacing_xyz_mm`` follows the same axis order.
    """

    case_id: str
    size_xyz: tuple[int, int, int]
    spacing_xyz_mm: tuple[float, float, float]

    @property
    def expected_int16_bytes(self) -> int:
        """Raw payload size implied by the documented 16-bit image class."""
        return int(np.prod(self.size_xyz, dtype=np.int64)) * 2


DIRLAB_4DCT_CASES: tuple[DirLabCaseGeometry, ...] = (
    DirLabCaseGeometry("4DCT1", (256, 256, 94), (0.97, 0.97, 2.5)),
    DirLabCaseGeometry("4DCT2", (256, 256, 112), (1.16, 1.16, 2.5)),
    DirLabCaseGeometry("4DCT3", (256, 256, 104), (1.15, 1.15, 2.5)),
    DirLabCaseGeometry("4DCT4", (256, 256, 99), (1.13, 1.13, 2.5)),
    DirLabCaseGeometry("4DCT5", (256, 256, 106), (1.10, 1.10, 2.5)),
    DirLabCaseGeometry("4DCT6", (512, 512, 128), (0.97, 0.97, 2.5)),
    DirLabCaseGeometry("4DCT7", (512, 512, 136), (0.97, 0.97, 2.5)),
    DirLabCaseGeometry("4DCT8", (512, 512, 128), (0.97, 0.97, 2.5)),
    DirLabCaseGeometry("4DCT9", (512, 512, 128), (0.97, 0.97, 2.5)),
    DirLabCaseGeometry("4DCT10", (512, 512, 120), (0.97, 0.97, 2.5)),
)


def case_geometry(case_id: str) -> DirLabCaseGeometry:
    """Return the prospectively recorded public geometry for ``case_id``."""
    for geometry in DIRLAB_4DCT_CASES:
        if geometry.case_id == case_id:
            return geometry
    raise ValueError(f"unknown DIR-Lab 4DCT case: {case_id}")


def one_based_rl_ap_si_to_zero_based_index_xyz(
    coordinates: np.ndarray,
    *,
    size_xyz: tuple[int, int, int],
) -> np.ndarray:
    """Convert documented DIR-Lab voxel-centroid coordinates to zero-based indices.

    DIR-Lab defines the coordinate rows in (RL, AP, SI) order and defines
    (1, 1, 1) at the centroid of the right-anterior-superior corner voxel.
    For the qualified raw-order RL/AP/SI decoder representation, this
    conversion subtracts one from each coordinate without any
    axis permutation or sign choice.

    The function accepts an in-memory array only. It intentionally does not
    know how to locate or open a DIR-Lab coordinate file.
    """
    raw = np.asarray(coordinates)
    if raw.dtype.kind not in "iuf":
        raise ValueError("coordinates must be numeric")
    values = raw.astype(np.float64, copy=False)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("coordinates must have shape (N, 3)")
    if len(values) == 0:
        raise ValueError("coordinates must not be empty")
    if not np.isfinite(values).all():
        raise ValueError("coordinates must be finite")

    size = np.asarray(size_xyz, dtype=np.float64)
    if size.shape != (3,) or not np.isfinite(size).all() or np.any(size < 1):
        raise ValueError("size_xyz must contain three positive dimensions")
    if np.any(values < 1.0) or np.any(values > size):
        raise ValueError("DIR-Lab coordinates fall outside documented one-based image bounds")
    return values - 1.0


def index_xyz_to_native_physical_mm(
    index_xyz: np.ndarray,
    *,
    spacing_xyz_mm: tuple[float, float, float],
) -> np.ndarray:
    """Map zero-based native DIR-Lab indices into an origin-zero physical frame.

    The returned frame uses +x right-to-left, +y anterior-to-posterior and
    +z superior-to-inferior. It is an estimator-local frame, not a claim that
    DIR-Lab encodes a standard DICOM LPS/RAS patient frame.
    """
    raw = np.asarray(index_xyz)
    if raw.dtype.kind not in "iuf":
        raise ValueError("index_xyz must be numeric")
    values = raw.astype(np.float64, copy=False)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("index_xyz must have shape (N, 3)")
    if not np.isfinite(values).all():
        raise ValueError("index_xyz must be finite")

    spacing = np.asarray(spacing_xyz_mm, dtype=np.float64)
    if spacing.shape != (3,) or not np.isfinite(spacing).all() or np.any(spacing <= 0):
        raise ValueError("spacing_xyz_mm must contain three finite positive values")
    return values * spacing
