"""Group-aware conformal primitives for the frozen TrueMargin M6 protocol.

The M6 protocol treats anatomy as the exchangeability group and spatial ROI
locations as observations nested within that anatomy. This module implements the
prospectively frozen weighted empirical construction without loading research data
or authorizing any result-bearing execution.

The construction follows ``docs/m6_calibration_protocol.md``:

* each of ``K`` calibration anatomies receives total mass ``1 / (K + 1)``;
* that anatomy's mass is divided equally across its observed scores; and
* an additional mass ``1 / (K + 1)`` is placed at positive infinity.

These helpers implement the frozen mathematics only. A formal M6 claim also
depends on the protocol's source stratification, cohort split, fixed sampling rule,
method validity requirements, and prospective execution boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isinf

import numpy as np


@dataclass(frozen=True)
class HCPThreshold:
    """One weighted hierarchical conformal threshold."""

    nominal_coverage: float
    alpha: float
    threshold: float
    calibration_groups: int
    calibration_scores: int
    infinity_atom_mass: float

    @property
    def is_finite(self) -> bool:
        """Return whether the fitted threshold is finite."""

        return bool(np.isfinite(self.threshold))


def ratio_nonconformity(error_mm: np.ndarray, signal_mm: np.ndarray) -> np.ndarray:
    """Return the frozen M6 ``error / signal`` nonconformity score.

    Zero signals follow the prospective M6 rule exactly:

    * ``signal > 0``: ``error / signal``;
    * ``signal == 0`` and ``error == 0``: ``0``;
    * ``signal == 0`` and ``error > 0``: positive infinity.

    Errors and signals must otherwise be finite, nonnegative, one-dimensional,
    and shape matched. No epsilon floor, clipping, or observation removal is used.
    """

    error = np.asarray(error_mm, dtype=np.float64)
    signal = np.asarray(signal_mm, dtype=np.float64)
    if error.ndim != 1 or signal.ndim != 1 or error.shape != signal.shape:
        raise ValueError("error_mm and signal_mm must be matching one-dimensional arrays")
    if len(error) == 0:
        raise ValueError("error_mm and signal_mm must be non-empty")
    if not np.isfinite(error).all() or np.any(error < 0.0):
        raise ValueError("error_mm must contain finite nonnegative values")
    if not np.isfinite(signal).all() or np.any(signal < 0.0):
        raise ValueError("signal_mm must contain finite nonnegative values")

    scores = np.empty_like(error)
    positive = signal > 0.0
    scores[positive] = error[positive] / signal[positive]
    zero_signal = ~positive
    scores[zero_signal & (error == 0.0)] = 0.0
    scores[zero_signal & (error > 0.0)] = np.inf
    return scores


def _validated_group_scores(group_scores: Sequence[np.ndarray]) -> tuple[np.ndarray, ...]:
    groups = tuple(np.asarray(scores, dtype=np.float64) for scores in group_scores)
    if not groups:
        raise ValueError("at least one calibration group is required")

    for index, scores in enumerate(groups):
        if scores.ndim != 1 or len(scores) == 0:
            raise ValueError(f"calibration group {index} must be a non-empty one-dimensional array")
        if np.isnan(scores).any() or np.isneginf(scores).any() or np.any(scores < 0.0):
            raise ValueError(
                f"calibration group {index} contains an invalid nonconformity score"
            )
    return groups


def hierarchical_conformal_threshold(
    group_scores: Sequence[np.ndarray],
    *,
    nominal_coverage: float,
) -> HCPThreshold:
    """Fit the frozen equal-anatomy hierarchical conformal threshold.

    The returned value is the lower ``nominal_coverage`` quantile of the weighted
    empirical measure specified in the M6 protocol. Positive-infinity scores are
    retained. A separate positive-infinity atom with mass ``1 / (K + 1)`` is always
    included.

    ``Fraction`` is used for the empirical weights so boundary cases such as the
    ``K=15`` 95% sentinel are decided by the protocol's exact discrete mass rather
    than floating-point accumulation error.
    """

    coverage = float(nominal_coverage)
    if not np.isfinite(coverage) or not 0.0 < coverage < 1.0:
        raise ValueError("nominal_coverage must be finite and strictly between 0 and 1")

    groups = _validated_group_scores(group_scores)
    k_groups = len(groups)
    group_mass = Fraction(1, k_groups + 1)
    target_mass = Fraction(str(coverage))

    weighted_scores: list[tuple[float, Fraction]] = []
    for scores in groups:
        point_mass = group_mass / len(scores)
        weighted_scores.extend((float(score), point_mass) for score in scores)

    weighted_scores.append((float("inf"), group_mass))
    weighted_scores.sort(key=lambda item: item[0])

    cumulative = Fraction(0, 1)
    threshold = float("inf")
    for score, weight in weighted_scores:
        cumulative += weight
        if cumulative >= target_mass:
            threshold = score
            break

    return HCPThreshold(
        nominal_coverage=coverage,
        alpha=1.0 - coverage,
        threshold=threshold,
        calibration_groups=k_groups,
        calibration_scores=sum(len(scores) for scores in groups),
        infinity_atom_mass=float(group_mass),
    )


def calibrated_radius(signal_mm: np.ndarray, threshold: float) -> np.ndarray:
    """Apply a frozen nonnegative multiplicative threshold to a method signal.

    An infinite HCP threshold represents an infinite interval. In that case every
    returned radius is positive infinity, including locations with zero signal.
    This avoids the undefined numerical product ``infinity * 0`` while preserving
    the protocol's set-valued interpretation.
    """

    signal = np.asarray(signal_mm, dtype=np.float64)
    if signal.ndim != 1 or len(signal) == 0:
        raise ValueError("signal_mm must be a non-empty one-dimensional array")
    if not np.isfinite(signal).all() or np.any(signal < 0.0):
        raise ValueError("signal_mm must contain finite nonnegative values")

    q_hat = float(threshold)
    if np.isnan(q_hat) or q_hat < 0.0 or q_hat == float("-inf"):
        raise ValueError("threshold must be nonnegative and may be positive infinity")
    if isinf(q_hat):
        return np.full(signal.shape, np.inf, dtype=np.float64)
    return signal * q_hat


def equal_group_coverage(
    error_groups_mm: Sequence[np.ndarray],
    radius_groups_mm: Sequence[np.ndarray],
) -> tuple[np.ndarray, float]:
    """Return per-group empirical coverage and the equal-group mean.

    This helper is intended for the M6 reporting rule. It does not pool spatial
    observations across anatomies as if they were independent trials.
    """

    if len(error_groups_mm) != len(radius_groups_mm) or not error_groups_mm:
        raise ValueError("error and radius group collections must be matching and non-empty")

    per_group = np.empty(len(error_groups_mm), dtype=np.float64)
    for index, (errors_raw, radii_raw) in enumerate(
        zip(error_groups_mm, radius_groups_mm, strict=True)
    ):
        errors = np.asarray(errors_raw, dtype=np.float64)
        radii = np.asarray(radii_raw, dtype=np.float64)
        if errors.ndim != 1 or radii.ndim != 1 or errors.shape != radii.shape or len(errors) == 0:
            raise ValueError(f"group {index} errors and radii must be matching non-empty vectors")
        if not np.isfinite(errors).all() or np.any(errors < 0.0):
            raise ValueError(f"group {index} errors must be finite and nonnegative")
        if np.isnan(radii).any() or np.isneginf(radii).any() or np.any(radii < 0.0):
            raise ValueError(
                f"group {index} radii must be nonnegative and may be positive infinity"
            )
        per_group[index] = float(np.mean(errors <= radii))

    return per_group, float(np.mean(per_group))
