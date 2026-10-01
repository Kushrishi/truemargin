"""Calibration and coverage helpers for registration-uncertainty research.

This module contains generic primitives for:

- displacement-error magnitudes;
- parametric Gaussian-scale reliability diagnostics;
- robust scalar or binned scale fitting; and
- an ordinary split-conformal radius based on ``error / sigma`` scores.

These helpers are not, by themselves, the TrueMargin M6 confirmatory method. Ordinary
split conformal requires exchangeability of the calibration and future score units. The
M6 design treats spatial observations as nested within anatomies, so a separately
reviewed group-aware protocol is required before any confirmatory coverage claim.

No clinical, generalization, or formal M6 coverage claim follows from calling these
functions alone.
"""

from __future__ import annotations

import numpy as np


# ----------------------------------------------------------------------
# Error and uncertainty primitives
# ----------------------------------------------------------------------
def displacement_error(u_est: np.ndarray, u_true: np.ndarray) -> np.ndarray:
    """Return per-point error-vector magnitude ``|u_est - u_true|``.

    ``u_est`` and ``u_true`` are arrays shaped ``(D, ...)`` where ``D`` is the
    spatial dimension. The returned array has shape ``(...)`` and inherits the
    input distance units.
    """
    e = u_est - u_true
    return np.sqrt(np.sum(e * e, axis=0))


def coverage_radius(sigma: np.ndarray, p: float, ndim: int = 2) -> np.ndarray:
    """Return a parametric radius at nominal level ``p``.

    The reference model assumes independent zero-mean Gaussian error components
    with common scale ``sigma``. Under that model, the error magnitude follows a
    chi distribution scaled by ``sigma``:

    - ``ndim=2``: ``r_p = sigma * sqrt(-2 ln(1 - p))``;
    - ``ndim=3``: ``r_p = sigma * sqrt(chi2.ppf(p, df=3))``.

    This is a model-based reference calculation, not a distribution-free coverage
    guarantee.
    """
    p = float(np.clip(p, 1e-6, 1 - 1e-9))
    if ndim == 2:
        k = np.sqrt(-2.0 * np.log(1.0 - p))
    elif ndim == 3:
        from scipy.stats import chi2

        k = np.sqrt(chi2.ppf(p, df=3))
    else:
        raise ValueError("ndim must be 2 or 3")
    return sigma * k


def empirical_coverage(err_mag: np.ndarray, sigma: np.ndarray, p: float, ndim: int = 2) -> float:
    """Return the observed fraction with error below the parametric level-``p`` radius."""
    r = coverage_radius(sigma, p, ndim=ndim)
    return float(np.mean(err_mag <= r))


# ----------------------------------------------------------------------
# Reliability curve + scalar calibration score
# ----------------------------------------------------------------------
def reliability_curve(
    err_mag: np.ndarray, sigma: np.ndarray, ndim: int = 2, levels: np.ndarray | None = None
):
    """Return nominal levels and empirical coverage under the parametric radius model.

    Agreement with the diagonal indicates that the assumed scale model is
    numerically compatible with the evaluated sample at those levels. The curve
    alone does not establish exchangeability, external validity, or clinical use.
    """
    if levels is None:
        levels = np.linspace(0.05, 0.99, 40)
    emp = np.array([empirical_coverage(err_mag, sigma, p, ndim=ndim) for p in levels])
    return levels, emp


def expected_calibration_error(levels: np.ndarray, emp: np.ndarray) -> float:
    """Return the mean absolute gap between nominal and empirical coverage."""
    return float(np.mean(np.abs(emp - levels)))


# ----------------------------------------------------------------------
# Parametric scale fitting
# ----------------------------------------------------------------------
def fit_variance_scale(
    err_mag_cal: np.ndarray, sigma_cal: np.ndarray, ndim: int = 2, min_sigma: float = 1e-6
) -> float:
    """Fit one robust global multiplier for ``sigma`` on a calibration sample.

    Under the isotropic Gaussian component model,
    ``err^2 / (ndim * sigma^2)`` scales with ``chi2(ndim) / ndim``. This helper
    estimates a multiplicative scale from the median ratio and normalizes by the
    population median of that reference distribution. The median is used for
    robustness to extreme ratios from very small positive ``sigma`` values.

    Points with ``sigma < min_sigma`` are excluded from the fit. That exclusion
    changes the population to which the fitted scale applies and must be reported
    when the helper is used in an analysis.

    This is a parametric scale estimator, not a conformal procedure and not an M6
    confirmatory method.
    """
    from scipy.stats import chi2

    keep = sigma_cal >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma_cal)} calibration points have sigma < min_sigma={min_sigma}; "
            "nothing usable to fit a scale from."
        )
    ratio = (err_mag_cal[keep] ** 2) / (ndim * (sigma_cal[keep] ** 2))
    correction = chi2.ppf(0.5, df=ndim) / ndim
    s2 = np.median(ratio) / correction
    return float(np.sqrt(s2))


def fit_variance_scale_binned(
    err_mag_cal: np.ndarray,
    sigma_cal: np.ndarray,
    ndim: int = 2,
    n_bins: int = 5,
    min_sigma: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit separate robust scale multipliers across bins of predicted ``sigma``.

    This exploratory helper relaxes the assumption that one multiplicative scale
    is adequate across the full ``sigma`` range. Points with ``sigma < min_sigma``
    are removed before binning, then the retained points are sorted by ``sigma``
    and split into approximately equal-sized groups. ``fit_variance_scale`` is
    applied within each group.

    Returns:
        ``bin_edges``: sigma values marking bin boundaries, length ``n_bins + 1``.
        ``scales``: fitted scale for each bin, length ``n_bins``.

    This data-adaptive binned fit is not a distribution-free calibration guarantee
    and is not authorized as the confirmatory M6 method.
    """
    keep = sigma_cal >= min_sigma
    n_dropped = (~keep).sum()
    if n_dropped:
        print(
            f"  fit_variance_scale_binned: dropping {n_dropped}/{len(sigma_cal)} "
            f"calibration points with sigma < {min_sigma} (no usable signal)"
        )
    err_mag_cal, sigma_cal = err_mag_cal[keep], sigma_cal[keep]

    order = np.argsort(sigma_cal)
    err_sorted = err_mag_cal[order]
    sigma_sorted = sigma_cal[order]
    bins_err = np.array_split(err_sorted, n_bins)
    bins_sigma = np.array_split(sigma_sorted, n_bins)

    scales = np.array(
        [
            fit_variance_scale(e, s, ndim=ndim, min_sigma=min_sigma)
            for e, s in zip(bins_err, bins_sigma, strict=True)
        ]
    )
    edges = np.array([b[0] for b in bins_sigma] + [sigma_sorted[-1]])
    return edges, scales


def apply_binned_scale(sigma: np.ndarray, bin_edges: np.ndarray, scales: np.ndarray) -> np.ndarray:
    """Apply previously fitted per-bin scales to ``sigma`` values.

    Values outside the fitted sigma range are assigned the nearest edge bin rather
    than extrapolated beyond the learned scales.
    """
    bin_idx = np.searchsorted(bin_edges, sigma, side="right") - 1
    bin_idx = np.clip(bin_idx, 0, len(scales) - 1)
    return sigma * scales[bin_idx]


# ----------------------------------------------------------------------
# Ordinary split-conformal score primitive
# ----------------------------------------------------------------------
def conformal_radius(
    err_mag_cal: np.ndarray, sigma_cal: np.ndarray, alpha: float = 0.10, min_sigma: float = 0.01
) -> float:
    """Return an ordinary split-conformal multiplier for ``error / sigma`` scores.

    For retained calibration units, the nonconformity score is
    ``err_mag_cal / sigma_cal``. Let ``n`` be the number of retained calibration
    scores and ``k = ceil((n + 1) * (1 - alpha))``. The returned multiplier is the
    ``k``-th smallest score; if ``k > n``, no finite order statistic can provide
    the requested ordinary split-conformal level and the function returns infinity.

    The standard finite-sample marginal guarantee applies only when the calibration
    scores and the future score unit satisfy the required exchangeability conditions
    and the same score/domain rule is used prospectively. In particular, this helper
    does **not** make spatial points nested within the same anatomy exchangeable.
    TrueMargin M6 therefore requires a separately reviewed anatomy-aware method.

    ``min_sigma`` defines a retained-score domain. Any coverage interpretation after
    filtering applies only to that prospectively defined retained population; excluded
    low-sigma observations must be reported separately and cannot be silently removed
    to improve coverage.
    """
    keep = sigma_cal >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma_cal)} calibration points have sigma < min_sigma={min_sigma}; "
            "nothing usable to calibrate a conformal radius from."
        )
    scores = err_mag_cal[keep] / sigma_cal[keep]
    n = len(scores)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    if k > n:
        return float("inf")
    return float(np.sort(scores)[k - 1])


def conformal_coverage(
    err_mag: np.ndarray, sigma: np.ndarray, q_hat: float, min_sigma: float = 0.01
) -> float:
    """Return empirical coverage of ``q_hat * sigma`` on the retained domain.

    The same ``min_sigma`` rule used during calibration should be applied when the
    intended evaluation population is the retained domain. This function reports an
    empirical fraction only; it does not itself establish conformal validity. Any
    finite-sample guarantee depends on the design assumptions used to obtain
    ``q_hat``, including the relevant exchangeability unit.

    Observations excluded by ``min_sigma`` remain scientifically relevant failures or
    abstentions and should be counted and reported separately.
    """
    keep = sigma >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma)} validation points have sigma < min_sigma={min_sigma}; "
            "nothing usable to evaluate coverage on."
        )
    return float(np.mean(err_mag[keep] <= q_hat * sigma[keep]))


# ----------------------------------------------------------------------
# Geometric accuracy summaries
# ----------------------------------------------------------------------
def tre(u_est: np.ndarray, u_true: np.ndarray, landmarks=None) -> dict:
    """Return target-registration-error summary statistics."""
    err = displacement_error(u_est, u_true)
    if landmarks is not None:
        err = err[landmarks]
    return {
        "mean": float(np.mean(err)),
        "median": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "max": float(np.max(err)),
    }
