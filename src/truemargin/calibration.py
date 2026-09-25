"""
calibration.py
--------------
The heart of TrueMargin: given (a) the TRUE displacement between two images and
(b) an estimator's predicted displacement + predicted per-point uncertainty,
answer the one question that makes this a company:

    "When the model says it's 90% sure the true point is inside this bubble,
     is the true point actually inside 90% of the time?"

That is CALIBRATION. Most registration work reports average error (TRE) and stops.
Nobody ships an honest, guaranteed confidence volume. This module builds it.

All functions are numpy-only so they run anywhere, on synthetic OR real
registration output. Later, the same functions consume SimpleITK/elastix/ProsRegNet
displacement fields instead of synthetic ones -- the calibration harness never changes.
"""

from __future__ import annotations

import numpy as np


# ----------------------------------------------------------------------
# Error and uncertainty primitives
# ----------------------------------------------------------------------
def displacement_error(u_est: np.ndarray, u_true: np.ndarray) -> np.ndarray:
    """Per-point error-vector magnitude |u_est - u_true|.

    u_est, u_true: arrays shaped (D, ...) where D is spatial dim (2 or 3).
    Returns: array shaped (...) of error magnitudes (e.g. in mm if inputs are mm).
    """
    e = u_est - u_true
    return np.sqrt(np.sum(e * e, axis=0))


def coverage_radius(sigma: np.ndarray, p: float, ndim: int = 2) -> np.ndarray:
    """Radius of the predicted 'confidence bubble' at nominal level p.

    Model assumption: each component of the error ~ N(0, sigma^2), independent.
    Then the error MAGNITUDE follows a chi distribution scaled by sigma.
      - ndim=2 (Rayleigh):    r_p = sigma * sqrt(-2 ln(1 - p))
      - ndim=3 (Maxwell):     r_p = sigma * sqrt(chi2.ppf(p, df=3))
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
    """Fraction of points whose TRUE error falls inside the predicted level-p bubble."""
    r = coverage_radius(sigma, p, ndim=ndim)
    return float(np.mean(err_mag <= r))


# ----------------------------------------------------------------------
# Reliability curve + scalar calibration score
# ----------------------------------------------------------------------
def reliability_curve(
    err_mag: np.ndarray, sigma: np.ndarray, ndim: int = 2, levels: np.ndarray | None = None
):
    """Return (nominal_levels, empirical_coverage) — the reliability diagram data.

    Perfectly calibrated  -> empirical == nominal (the diagonal).
    Below the diagonal     -> OVERCONFIDENT (bubbles too small; truth escapes).
    Above the diagonal     -> underconfident (bubbles needlessly large).
    """
    if levels is None:
        levels = np.linspace(0.05, 0.99, 40)
    emp = np.array([empirical_coverage(err_mag, sigma, p, ndim=ndim) for p in levels])
    return levels, emp


def expected_calibration_error(levels: np.ndarray, emp: np.ndarray) -> float:
    """Mean absolute gap between the reliability curve and the diagonal.
    0 == perfectly calibrated. Bigger == more dishonest confidence.
    """
    return float(np.mean(np.abs(emp - levels)))


# ----------------------------------------------------------------------
# Recalibration (the 'fix' — paper #2 in the plan)
# ----------------------------------------------------------------------
def fit_variance_scale(
    err_mag_cal: np.ndarray, sigma_cal: np.ndarray, ndim: int = 2, min_sigma: float = 1e-6
) -> float:
    """Fit ONE global scale s so that s*sigma is well-calibrated, on a calibration split.

    Under the Gaussian model, ratio_i = err_i^2 / (ndim * sigma_i^2) satisfies
    ratio_i = s^2 * (chi2(ndim) sample / ndim). The textbook MLE takes the MEAN
    of these ratios (mean of chi2(ndim)/ndim is exactly 1, so s^2 = mean(ratio)
    directly). But the mean is not robust: a handful of points where the
    ensemble's 5 registration attempts happened to land on nearly the exact
    same answer (near-zero sigma -- genuinely observed on real 3D data with a
    coarse mesh, not a bug) blow the ratio up toward infinity for any nonzero
    error, and those few extreme values can dominate the mean entirely (seen
    in practice: a mean-based fit gave s in the hundreds/thousands, clearly
    not a real calibration number).

    This uses the MEDIAN instead, which is far less sensitive to that kind of
    contamination, then corrects for the fact that median(chi2(ndim)/ndim) is
    NOT 1 (unlike the mean) -- dividing by that known correction factor keeps
    the estimate mathematically unbiased rather than just "more robust but
    quietly wrong."

    min_sigma: points with sigma below this are still excluded outright (not
    just epsilon-protected) since a literal sigma=0 is a divide-by-zero, not
    a small-but-real value.
    """
    from scipy.stats import chi2

    keep = sigma_cal >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma_cal)} calibration points have sigma < min_sigma={min_sigma}; "
            "nothing usable to fit a scale from."
        )
    ratio = (err_mag_cal[keep] ** 2) / (ndim * (sigma_cal[keep] ** 2))
    correction = chi2.ppf(0.5, df=ndim) / ndim  # median(chi2(ndim)/ndim), != 1
    s2 = np.median(ratio) / correction
    return float(np.sqrt(s2))


def fit_variance_scale_binned(
    err_mag_cal: np.ndarray,
    sigma_cal: np.ndarray,
    ndim: int = 2,
    n_bins: int = 5,
    min_sigma: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
    """Like fit_variance_scale, but fits a SEPARATE scale per bin of predicted
    sigma, instead of one global number for every point.

    Why: a single global scale assumes the model is wrong by the same relative
    amount everywhere. On real data that assumption can fail -- e.g. it might
    be mildly overconfident where sigma is already large, and wildly
    overconfident where sigma is small, in which case one global scale either
    undercorrects the bad region or overcorrects the already-okay one (this is
    exactly what we saw on the real 15-patient result: one scale turned
    overconfidence into overcorrection).

    Points with sigma < min_sigma are dropped BEFORE binning (see
    fit_variance_scale's docstring for why): sorting by sigma means these
    degenerate points would otherwise cluster into the first bin(s) and blow
    up that bin's fitted scale into a meaningless number.

    Points are sorted by predicted sigma and split into n_bins equal-sized
    groups; fit_variance_scale() is applied within each group independently.

    Returns:
        bin_edges: sigma values marking bin boundaries (length n_bins+1)
        scales: fitted scale per bin (length n_bins)
    Use apply_binned_scale() to apply this to new (unseen) points.
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
    # Bin edges = the sigma value at the start of each bin, plus the max sigma
    # seen, so apply_binned_scale can look up which bin a new point falls into.
    edges = np.array([b[0] for b in bins_sigma] + [sigma_sorted[-1]])
    return edges, scales


def apply_binned_scale(sigma: np.ndarray, bin_edges: np.ndarray, scales: np.ndarray) -> np.ndarray:
    """Apply per-bin scales (from fit_variance_scale_binned) to new sigma values.

    Each point's sigma is matched to the bin whose edges it falls within, and
    scaled by that bin's fitted factor. Points outside the fitted range are
    clamped to the nearest bin's scale rather than extrapolated.
    """
    bin_idx = np.searchsorted(bin_edges, sigma, side="right") - 1
    bin_idx = np.clip(bin_idx, 0, len(scales) - 1)
    return sigma * scales[bin_idx]


# ----------------------------------------------------------------------
# Split-conformal prediction (a formally guaranteed alternative to
# fit_variance_scale -- see milestone 3, docs/roadmap.md)
# ----------------------------------------------------------------------
def conformal_radius(
    err_mag_cal: np.ndarray, sigma_cal: np.ndarray, alpha: float = 0.10, min_sigma: float = 0.01
) -> float:
    """Split-conformal calibration: a DISTRIBUTION-FREE alternative to
    fit_variance_scale.

    fit_variance_scale (and fit_variance_scale_binned) assume the error
    follows a specific parametric model (error components ~ N(0, sigma^2)),
    then fit a scale to make that assumed model match the data as well as
    possible on average. That's a reasonable, standard approach, but the
    resulting coverage guarantee is only as good as the Gaussian assumption
    -- if real errors are heavier-tailed or skewed, the "1-alpha confidence
    region" may not actually contain the true point 1-alpha of the time.

    Split-conformal prediction sidesteps the parametric assumption entirely.
    It only assumes the calibration and future (validation/test) points are
    EXCHANGEABLE (a weaker, more defensible assumption than "errors are
    Gaussian" -- roughly, that calibration and future points are drawn the
    same way, not that they follow any particular distribution). Under that
    assumption, scaling sigma by the returned q_hat gives a MATHEMATICALLY
    GUARANTEED marginal coverage of at least (1-alpha), regardless of the
    true error distribution's shape.

    Method: compute a nonconformity score for each calibration point,
    s_i = err_i / sigma_i (how many "sigma-units" the true error actually
    was). q_hat is the ceil((n+1)(1-alpha))/n empirical quantile of these
    scores -- NOT simply the (1-alpha) quantile; this finite-sample
    correction (from Vovk et al.'s conformal prediction theory) is what
    makes the guarantee exact rather than approximate for finite n.

    min_sigma: calibration points with sigma below this are excluded. This
    matters MORE here than in fit_variance_scale: the ratio-based
    nonconformity score s_i = err_i/sigma_i is directly, catastrophically
    sensitive to near-zero sigma (a single point with real error and
    sigma=0.0007 produces a score in the thousands, dominating the whole
    quantile), whereas fit_variance_scale's median-based estimator is far
    more robust to a handful of such points. The default (0.01) matches the
    blind-spot threshold used throughout this project's diagnostics (see
    docs/real_data_findings.md Result 3) rather than an arbitrary small
    epsilon (1e-6 was tried first here and was not aggressive enough --
    see docs/roadmap.md milestone 3 for the empirical finding that
    motivated raising this default).
    """
    keep = sigma_cal >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma_cal)} calibration points have sigma < min_sigma={min_sigma}; "
            "nothing usable to calibrate a conformal radius from."
        )
    scores = err_mag_cal[keep] / sigma_cal[keep]
    n = len(scores)
    # Exact split-conformal quantile (Vovk et al.): q_hat is the k-th SMALLEST
    # of the n calibration scores (1-indexed), where k = ceil((n+1)(1-alpha)).
    # This was previously computed via np.quantile(scores, k/n, method="higher"),
    # which is NOT equivalent -- np.quantile's "higher" interpolation rounds a
    # continuous rank UP to the next order statistic, silently returning the
    # (k+1)-th smallest value instead of the k-th for interior k. That bug was
    # caught by an independent audit (verified via direct order-statistic
    # comparison and a 200,000-trial Monte Carlo check): it made the interval
    # slightly too conservative rather than invalid, but it did not implement
    # the formula the code claimed to. Fixed here by taking the k-th order
    # statistic directly, with the standard conformal-prediction convention
    # that if k > n (not enough calibration points to guarantee this alpha
    # at all), q_hat is infinite -- no finite radius can offer the guarantee.
    k = int(np.ceil((n + 1) * (1 - alpha)))
    if k > n:
        return float("inf")
    return float(np.sort(scores)[k - 1])


def conformal_coverage(
    err_mag: np.ndarray, sigma: np.ndarray, q_hat: float, min_sigma: float = 0.01
) -> float:
    """Empirical fraction of points whose true error falls within the
    conformal radius q_hat * sigma. On held-out exchangeable data, this
    should come out close to (or above) the target (1-alpha) used to fit
    q_hat -- that's the guarantee conformal_radius provides, and this
    function is how you empirically check it actually held.

    min_sigma MUST match the value passed to conformal_radius when q_hat was
    fit. Bug found and fixed here: conformal_radius excludes calibration
    points with sigma < min_sigma before fitting q_hat (see its docstring --
    near-zero sigma makes the ratio-based nonconformity score blow up), but
    this function previously had no min_sigma filter at all, so it tested
    q_hat against a validation set that still included those same degenerate
    points. Since q_hat * sigma is tiny whenever sigma is near zero, any
    validation point with near-zero sigma and nonzero real error is
    essentially guaranteed to "fail" coverage regardless of how good q_hat
    is -- an asymmetry between calibration and validation that breaks
    conformal prediction's exchangeability assumption and its guarantee
    along with it (calibration and test scores must be produced by the SAME
    rule). Excluding these points from BOTH sides restores that symmetry.
    Points with sigma < min_sigma are a real, disclosed blind spot (tracked
    separately throughout this project, e.g. scripts/06's blind-spot
    diagnostic) -- this function's result should be reported alongside how
    many/which fraction of points were excluded, not silently.
    """
    keep = sigma >= min_sigma
    if keep.sum() == 0:
        raise ValueError(
            f"All {len(sigma)} validation points have sigma < min_sigma={min_sigma}; "
            "nothing usable to evaluate coverage on."
        )
    return float(np.mean(err_mag[keep] <= q_hat * sigma[keep]))


# ----------------------------------------------------------------------
# Geometric metrics (accuracy, for context — NOT the moat)
# ----------------------------------------------------------------------
def tre(u_est: np.ndarray, u_true: np.ndarray, landmarks=None) -> dict:
    """Target Registration Error summary (mm) over all points or at landmarks."""
    err = displacement_error(u_est, u_true)
    if landmarks is not None:
        err = err[landmarks]
    return {
        "mean": float(np.mean(err)),
        "median": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "max": float(np.max(err)),
    }
