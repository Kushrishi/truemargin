"""Frozen registration-hyperparameter sensitivity estimator.

This module centralizes the exact nine-member estimator promoted by
``docs/hyperparameter_ensemble_result.md`` so downstream evaluations cannot
silently drift to a different grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from truemargin import ensemble
from truemargin import registration as reg

MESH_SIZE = 3
MAX_ITERATIONS = 15
CENTER_FIRST = False
METRIC_BINS = (32, 50, 64)
GRADIENT_TOLERANCES = (1e-4, 1e-5, 1e-6)
CONFIGS = tuple(
    (metric_bins, gradient_tolerance)
    for metric_bins in METRIC_BINS
    for gradient_tolerance in GRADIENT_TOLERANCES
)


@dataclass(frozen=True)
class HyperparameterEnsembleResult:
    """Operational result for the exact promoted nine-member estimator."""

    complete: bool
    u_mean: np.ndarray | None
    sigma: np.ndarray | None
    member_reasons: tuple[str, ...]
    member_mean_displacement_mm: np.ndarray


def config_id(metric_bins: int, gradient_tolerance: float) -> str:
    """Stable human-readable identity for one frozen grid member."""
    tolerance_label = f"{gradient_tolerance:.0e}".replace("-", "m").replace("+", "p")
    return f"bins_{metric_bins}_gtol_{tolerance_label}"


def _mean_displacement_magnitude(field: np.ndarray) -> float:
    return float(np.sqrt(np.sum(field * field, axis=0)).mean())


def run_hyperparameter_ensemble(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    spacing: tuple[float, ...],
    crop_diagonal_mm: float,
) -> HyperparameterEnsembleResult:
    """Run the exact nine-member promoted estimator on one image pair.

    A case is complete only when every predeclared configuration is valid.
    Failed members are never silently dropped into a survivor-only summary.
    """
    if fixed.shape != moving.shape:
        raise ValueError("fixed and moving must have identical shapes")
    if fixed.ndim != 3:
        raise ValueError("the promoted estimator expects 3-D volumes")
    if len(spacing) != fixed.ndim:
        raise ValueError("spacing dimensionality must match the input volumes")

    expected_shape = (fixed.ndim, *fixed.shape)
    fields: list[np.ndarray] = []
    reasons: list[str] = []
    mean_displacements: list[float] = []

    for metric_bins, gradient_tolerance in CONFIGS:
        try:
            field = reg.baseline_bspline_registration(
                fixed,
                moving,
                mesh_size=MESH_SIZE,
                max_iterations=MAX_ITERATIONS,
                spacing=spacing,
                center_first=CENTER_FIRST,
                metric_bins=metric_bins,
                gradient_convergence_tolerance=gradient_tolerance,
            )
        except Exception as exc:
            reasons.append(f"registration_exception:{type(exc).__name__}:{exc}")
            mean_displacements.append(float("nan"))
            continue

        reason = ensemble.validate_member_field(
            field,
            expected_shape=expected_shape,
            crop_diagonal_mm=crop_diagonal_mm,
        )
        mean_displacement = float("nan")
        if field.shape == expected_shape and np.isfinite(field).all():
            mean_displacement = _mean_displacement_magnitude(field)
        mean_displacements.append(mean_displacement)

        if reason is not None:
            reasons.append(reason)
            continue

        reasons.append("ok")
        fields.append(field)

    complete = len(fields) == len(CONFIGS) and all(reason == "ok" for reason in reasons)
    means = np.asarray(mean_displacements, dtype=np.float64)
    if not complete:
        return HyperparameterEnsembleResult(
            complete=False,
            u_mean=None,
            sigma=None,
            member_reasons=tuple(reasons),
            member_mean_displacement_mm=means,
        )

    u_mean, sigma = ensemble.summarize_fields(fields)
    return HyperparameterEnsembleResult(
        complete=True,
        u_mean=u_mean,
        sigma=sigma,
        member_reasons=tuple(reasons),
        member_mean_displacement_mm=means,
    )
