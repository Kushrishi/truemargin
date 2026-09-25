"""Frozen local comparator primitives for the known-GT study."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.stats import spearmanr

RANK_DEGENERACY_TOL = 1e-12


def _spacing_array(spacing_xyz: tuple[float, ...]) -> np.ndarray:
    spacing = np.asarray(spacing_xyz, dtype=np.float64)
    if spacing.shape != (3,) or not np.isfinite(spacing).all() or np.any(spacing <= 0.0):
        raise ValueError("spacing_xyz must contain three finite positive values")
    return spacing


def _landmark_array(idx_zyx: np.ndarray) -> np.ndarray:
    idx = np.asarray(idx_zyx, dtype=np.float64)
    if idx.ndim != 2 or idx.shape[1] != 3 or not np.isfinite(idx).all():
        raise ValueError("landmarks must have shape (n, 3) with finite z/y/x coordinates")
    return idx


def _field_array(field: np.ndarray) -> np.ndarray:
    value = np.asarray(field, dtype=np.float64)
    if value.ndim != 4 or value.shape[0] != 3:
        raise ValueError("displacement field must have shape (3, z, y, x)")
    if not np.isfinite(value).all():
        raise ValueError("displacement field must be finite")
    return value


def indices_zyx_to_physical_xyz(
    idx_zyx: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Convert normalized-grid z/y/x indices to zero-origin physical x/y/z mm."""
    idx = _landmark_array(idx_zyx)
    spacing = _spacing_array(spacing_xyz)
    return idx[:, ::-1] * spacing


def _physical_xyz_to_continuous_zyx(
    points_xyz: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    points = np.asarray(points_xyz, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("physical points must have shape (n, 3) and be finite")
    spacing = _spacing_array(spacing_xyz)
    return (points / spacing)[:, ::-1]


def _require_inside(coords_zyx: np.ndarray, shape_zyx: tuple[int, ...]) -> None:
    shape = np.asarray(shape_zyx, dtype=np.float64)
    if shape.shape != (3,) or np.any(shape <= 0):
        raise ValueError("shape_zyx must contain three positive dimensions")
    tolerance = 1e-9
    inside = np.all(coords_zyx >= -tolerance, axis=1) & np.all(
        coords_zyx <= (shape - 1.0 + tolerance), axis=1
    )
    if not np.all(inside):
        raise ValueError("sample point lies outside the image domain")


def sample_scalar_physical(
    volume_zyx: np.ndarray,
    points_xyz: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Linearly sample a scalar zero-origin/identity-direction 3-D image."""
    volume = np.asarray(volume_zyx, dtype=np.float64)
    if volume.ndim != 3 or not np.isfinite(volume).all():
        raise ValueError("scalar volume must be a finite 3-D array")
    coords = _physical_xyz_to_continuous_zyx(points_xyz, spacing_xyz)
    _require_inside(coords, volume.shape)
    values = map_coordinates(
        volume,
        coords.T,
        order=1,
        mode="constant",
        cval=np.nan,
        prefilter=False,
    )
    if not np.isfinite(values).all():
        raise ValueError("scalar interpolation produced non-finite values")
    return np.asarray(values, dtype=np.float64)


def sample_vector_physical(
    field_dzyx: np.ndarray,
    points_xyz: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Linearly sample an x/y/z displacement field at physical points."""
    field = _field_array(field_dzyx)
    coords = _physical_xyz_to_continuous_zyx(points_xyz, spacing_xyz)
    _require_inside(coords, field.shape[1:])
    sampled = np.stack(
        [
            map_coordinates(
                field[component],
                coords.T,
                order=1,
                mode="constant",
                cval=np.nan,
                prefilter=False,
            )
            for component in range(3)
        ],
        axis=1,
    )
    if not np.isfinite(sampled).all():
        raise ValueError("vector interpolation produced non-finite values")
    return np.asarray(sampled, dtype=np.float64)


def inverse_consistency_scores(
    forward_field_dzyx: np.ndarray,
    reverse_field_dzyx: np.ndarray,
    idx_zyx: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Return forward-then-reverse cycle error in millimetres."""
    forward = _field_array(forward_field_dzyx)
    reverse = _field_array(reverse_field_dzyx)
    if forward.shape[1:] != reverse.shape[1:]:
        raise ValueError("forward and reverse fields must share the same spatial grid")

    x_xyz = indices_zyx_to_physical_xyz(idx_zyx, spacing_xyz)
    u_forward = sample_vector_physical(forward, x_xyz, spacing_xyz)
    y_xyz = x_xyz + u_forward
    u_reverse = sample_vector_physical(reverse, y_xyz, spacing_xyz)
    x_cycle = y_xyz + u_reverse
    return np.linalg.norm(x_cycle - x_xyz, axis=1)


def absolute_residual_scores(
    fixed_zyx: np.ndarray,
    moving_zyx: np.ndarray,
    forward_field_dzyx: np.ndarray,
    idx_zyx: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Return absolute fixed-vs-warped-moving residual at frozen landmarks."""
    fixed = np.asarray(fixed_zyx, dtype=np.float64)
    moving = np.asarray(moving_zyx, dtype=np.float64)
    forward = _field_array(forward_field_dzyx)
    if fixed.ndim != 3 or moving.ndim != 3 or fixed.shape != moving.shape:
        raise ValueError("fixed and moving must be matching 3-D arrays")
    if forward.shape[1:] != fixed.shape:
        raise ValueError("forward field must share the image grid")
    if not np.isfinite(fixed).all() or not np.isfinite(moving).all():
        raise ValueError("fixed and moving images must be finite")

    x_xyz = indices_zyx_to_physical_xyz(idx_zyx, spacing_xyz)
    fixed_values = sample_scalar_physical(fixed, x_xyz, spacing_xyz)
    u_forward = sample_vector_physical(forward, x_xyz, spacing_xyz)
    y_xyz = x_xyz + u_forward
    moving_values = sample_scalar_physical(moving, y_xyz, spacing_xyz)
    return np.abs(fixed_values - moving_values)


def jacobian_deviation_scores(
    forward_field_dzyx: np.ndarray,
    idx_zyx: np.ndarray,
    spacing_xyz: tuple[float, ...],
) -> np.ndarray:
    """Return abs(det(I + grad u) - 1) at frozen fixed-domain landmarks."""
    field = _field_array(forward_field_dzyx)
    spacing = _spacing_array(spacing_xyz)
    try:
        import SimpleITK as sitk
    except ImportError as exc:
        raise ImportError("SimpleITK is required for Jacobian-deviation scoring") from exc

    vector_zyx_xyz = np.moveaxis(field, 0, -1)
    displacement = sitk.GetImageFromArray(vector_zyx_xyz, isVector=True)
    displacement.SetSpacing(tuple(float(value) for value in spacing))
    jacobian = sitk.DisplacementFieldJacobianDeterminant(displacement, True)
    jacobian_zyx = sitk.GetArrayFromImage(jacobian)
    if not np.isfinite(jacobian_zyx).all():
        raise ValueError("Jacobian determinant contains non-finite values")

    points_xyz = indices_zyx_to_physical_xyz(idx_zyx, spacing_xyz)
    sampled = sample_scalar_physical(jacobian_zyx, points_xyz, spacing_xyz)
    return np.abs(sampled - 1.0)


def rank_association(
    score: np.ndarray,
    known_error: np.ndarray,
    *,
    degeneracy_tol: float = RANK_DEGENERACY_TOL,
) -> tuple[float, bool]:
    """Return frozen Spearman association, mapping rank-degenerate cases to zero."""
    score_values = np.asarray(score, dtype=np.float64)
    error_values = np.asarray(known_error, dtype=np.float64)
    if (
        score_values.ndim != 1
        or error_values.ndim != 1
        or len(score_values) < 2
        or len(score_values) != len(error_values)
    ):
        raise ValueError("score and known_error must be matching one-dimensional arrays")
    if not np.isfinite(score_values).all() or not np.isfinite(error_values).all():
        raise ValueError("score and known_error must be finite")
    if (
        float(np.std(score_values)) <= degeneracy_tol
        or float(np.std(error_values)) <= degeneracy_tol
    ):
        return 0.0, True
    rho = float(spearmanr(score_values, error_values).statistic)
    if not np.isfinite(rho):
        return 0.0, True
    return rho, False


def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    """Return Holm-adjusted p-values in the original method order."""
    values = np.asarray(p_values, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("p_values must be a non-empty one-dimensional array")
    if not np.isfinite(values).all() or np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("p_values must be finite values in [0, 1]")

    order = np.argsort(values, kind="stable")
    adjusted_sorted = np.empty(len(values), dtype=np.float64)
    running = 0.0
    m = len(values)
    for rank, index in enumerate(order):
        candidate = min(1.0, float((m - rank) * values[index]))
        running = max(running, candidate)
        adjusted_sorted[rank] = running

    adjusted = np.empty(len(values), dtype=np.float64)
    adjusted[order] = adjusted_sorted
    return adjusted


def paired_median_bootstrap(
    target: np.ndarray,
    comparator: np.ndarray,
    *,
    n_bootstraps: int = 10_000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Return median(target-comparator) and its paired anatomy bootstrap interval."""
    target_values = np.asarray(target, dtype=np.float64)
    comparator_values = np.asarray(comparator, dtype=np.float64)
    if (
        target_values.ndim != 1
        or comparator_values.ndim != 1
        or len(target_values) == 0
        or len(target_values) != len(comparator_values)
    ):
        raise ValueError("target and comparator must be matching non-empty vectors")
    if not np.isfinite(target_values).all() or not np.isfinite(comparator_values).all():
        raise ValueError("paired anatomy effects must be finite")
    if n_bootstraps < 1:
        raise ValueError("n_bootstraps must be positive")

    delta = target_values - comparator_values
    observed = float(np.median(delta))
    rng = np.random.default_rng(seed)
    statistics = np.empty(n_bootstraps, dtype=np.float64)
    for i in range(n_bootstraps):
        sampled = rng.choice(delta, size=len(delta), replace=True)
        statistics[i] = float(np.median(sampled))
    lo, hi = np.percentile(statistics, [2.5, 97.5])
    return observed, float(lo), float(hi)
