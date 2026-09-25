"""Explicit perturbation strategies for registration-ensemble uncertainty.

The historical TrueMargin ensemble perturbed raw fixed/moving intensities by an
absolute Gaussian standard deviation of 0.02. On raw DICOM-scale MRI that can be
negligible, so this module adds a dimensionless, per-image standard-deviation mode
without silently changing the legacy implementation in ``registration.py``.

The corrected mode is a sensitivity ensemble, not a physical scanner-noise model
or Bayesian posterior. See ``docs/ensemble_baseline_protocol.md``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Literal

import numpy as np

from truemargin.registration import baseline_bspline_registration

PerturbationStrategy = Literal["absolute_intensity", "relative_std"]


def _noise_scales(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    perturbation: PerturbationStrategy,
    perturbation_scale: float,
) -> tuple[float, float]:
    """Return fixed/moving Gaussian noise standard deviations.

    ``absolute_intensity`` reproduces the historical semantics: the same raw
    standard deviation is used for both images.

    ``relative_std`` makes the perturbation dimensionless while leaving the
    registration inputs themselves on their original intensity scales. Each image
    receives noise with standard deviation ``perturbation_scale * image.std()``.
    """
    scale = float(perturbation_scale)
    if not np.isfinite(scale) or scale < 0:
        raise ValueError("perturbation_scale must be finite and non-negative")

    if perturbation == "absolute_intensity":
        return scale, scale
    if perturbation != "relative_std":
        raise ValueError(
            "perturbation must be 'absolute_intensity' or 'relative_std', " f"got {perturbation!r}"
        )

    fixed_std = float(np.std(fixed))
    moving_std = float(np.std(moving))
    tiny = np.finfo(np.float64).eps
    if not np.isfinite(fixed_std) or fixed_std <= tiny:
        raise ValueError(
            "relative_std perturbation requires a finite, non-zero fixed-image standard deviation"
        )
    if not np.isfinite(moving_std) or moving_std <= tiny:
        raise ValueError(
            "relative_std perturbation requires a finite, non-zero moving-image standard deviation"
        )
    return scale * fixed_std, scale * moving_std


def perturbation_noise_scales(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    perturbation: PerturbationStrategy,
    perturbation_scale: float,
) -> tuple[float, float]:
    """Public read-only view of the effective fixed/moving perturbation scales."""
    return _noise_scales(
        fixed,
        moving,
        perturbation=perturbation,
        perturbation_scale=perturbation_scale,
    )


def perturbed_inputs(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    n: int,
    perturbation: PerturbationStrategy,
    perturbation_scale: float,
    seed: int,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield the deterministic perturbed image pairs used by an ensemble.

    This is the single source of truth for member generation. A sensitivity
    runner can therefore inspect every registration member (including failures)
    without duplicating the RNG sequence used by :func:`ensemble_uncertainty`.
    Calls with the same inputs/settings/seed are prefix-nested across ``n``.
    """
    if n < 1:
        raise ValueError("n must be at least 1")
    fixed_noise_sd, moving_noise_sd = _noise_scales(
        fixed,
        moving,
        perturbation=perturbation,
        perturbation_scale=perturbation_scale,
    )
    rng = np.random.default_rng(seed)
    for _ in range(n):
        yield (
            fixed + rng.normal(0.0, fixed_noise_sd, fixed.shape),
            moving + rng.normal(0.0, moving_noise_sd, moving.shape),
        )


def validate_member_field(
    field: np.ndarray,
    *,
    expected_shape: tuple[int, ...],
    crop_diagonal_mm: float,
) -> str | None:
    """Return a frozen-protocol failure reason for one displacement field.

    The perturbation-sensitivity protocol treats a member as failed if its field
    is non-finite, has the wrong shape, or has mean displacement magnitude above
    the crop's physical diagonal. Returning a string rather than raising lets the
    runner finish all members and report the full failure count for a setting.
    """
    if field.shape != expected_shape:
        return f"shape_mismatch:{field.shape!r}!={expected_shape!r}"
    if not np.isfinite(field).all():
        return "nonfinite_displacement"
    if not np.isfinite(crop_diagonal_mm) or crop_diagonal_mm <= 0:
        raise ValueError("crop_diagonal_mm must be finite and positive")

    mean_magnitude = float(np.sqrt(np.sum(field * field, axis=0)).mean())
    if mean_magnitude > crop_diagonal_mm:
        return (
            f"mean_displacement_exceeds_crop_diagonal:"
            f"{mean_magnitude:.6g}>{crop_diagonal_mm:.6g}"
        )
    return None


def summarize_fields(fields: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Compute the historical ensemble mean and scalar RMS sigma convention."""
    if len(fields) < 2:
        raise ValueError("at least two valid fields are required to estimate ensemble spread")
    fields_array = np.stack(fields)  # (n, D, ...)
    u_mean = fields_array.mean(0)  # (D, ...)
    ndim = fields_array.shape[1]
    sigma = np.sqrt(((fields_array - u_mean) ** 2).sum(1).mean(0) / ndim)
    return u_mean, sigma


def ensemble_uncertainty(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    n: int = 5,
    perturbation: PerturbationStrategy = "absolute_intensity",
    perturbation_scale: float = 0.02,
    seed: int = 0,
    mesh_size: int = 8,
    max_iterations: int = 100,
    spacing: tuple[float, ...] | None = None,
    center_first: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate registration uncertainty from a deterministic perturbation ensemble.

    Args:
        fixed, moving: image arrays passed to the registration unchanged except
            for the per-member additive perturbation.
        n: number of ensemble members. The RNG is initialized once per call, so
            calls with the same inputs/settings/seed are nested: the first five
            members of ``n=20`` are exactly the same perturbations as ``n=5``.
        perturbation: ``absolute_intensity`` for the historical raw-unit jitter,
            or ``relative_std`` for the corrected scale-aware sensitivity test.
        perturbation_scale: raw intensity standard deviation in absolute mode;
            dimensionless fraction of each image's own standard deviation in
            relative mode. Zero is allowed to measure the registration
            repeatability floor.
        seed: base NumPy RNG seed used for member perturbations.
        mesh_size, max_iterations, spacing, center_first: forwarded unchanged to
            ``baseline_bspline_registration``.

    Returns:
        ``(u_mean, sigma)`` using the same scalar RMS-across-axes convention as
        the historical ensemble implementation.
    """
    if n < 2:
        raise ValueError("n must be at least 2 to estimate ensemble spread")

    fields = []
    for fixed_perturbed, moving_perturbed in perturbed_inputs(
        fixed,
        moving,
        n=n,
        perturbation=perturbation,
        perturbation_scale=perturbation_scale,
        seed=seed,
    ):
        fields.append(
            baseline_bspline_registration(
                fixed_perturbed,
                moving_perturbed,
                mesh_size=mesh_size,
                max_iterations=max_iterations,
                spacing=spacing,
                center_first=center_first,
            )
        )

    return summarize_fields(fields)
