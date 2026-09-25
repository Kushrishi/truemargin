"""Sanity tests: a perfectly-calibrated estimator should trace the diagonal;
recalibration should reduce ECE. Run: PYTHONPATH=src python -m pytest -q  (or run directly)."""

import numpy as np
import pytest

from truemargin import calibration as cal


def test_perfect_calibration_is_near_diagonal():
    rng = np.random.default_rng(0)
    H = W = 200
    sigma = np.full((H, W), 1.0)
    # true errors drawn EXACTLY from the model -> should be well calibrated
    e = rng.standard_normal((2, H, W)) * sigma[None]
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp = cal.reliability_curve(err, sigma, ndim=2)
    assert cal.expected_calibration_error(lv, emp) < 0.03


def test_recalibration_reduces_error():
    rng = np.random.default_rng(1)
    H = W = 200
    sigma_pred = np.full((H, W), 0.4)  # overconfident (too small)
    true_sigma = 1.0
    e = rng.standard_normal((2, H, W)) * true_sigma
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp_raw = cal.reliability_curve(err, sigma_pred, ndim=2)
    s = cal.fit_variance_scale(err, sigma_pred, ndim=2)
    lv, emp_fix = cal.reliability_curve(err, s * sigma_pred, ndim=2)
    assert cal.expected_calibration_error(lv, emp_fix) < cal.expected_calibration_error(lv, emp_raw)
    assert abs(s - (true_sigma / 0.4)) < 0.15  # recovers the right scale (~2.5)


# ----------------------------------------------------------------------
# ndim=3 coverage math -- every real-data script in this project uses
# ndim=3, but until this test was added (following an independent
# adversarial audit), only ndim=2 was ever exercised by the test suite.
# ----------------------------------------------------------------------
def test_perfect_calibration_ndim3_is_near_diagonal():
    rng = np.random.default_rng(2)
    n = 20000
    sigma = np.full(n, 1.0)
    e = rng.standard_normal((3, n)) * sigma[None]
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp = cal.reliability_curve(err, sigma, ndim=3)
    assert cal.expected_calibration_error(lv, emp) < 0.03


def test_coverage_radius_ndim3_matches_chi_distribution():
    # Independent check: for iid N(0, sigma^2) components in 3D, the
    # magnitude^2 / sigma^2 follows a chi-squared(3) distribution, so the
    # empirical fraction of points below coverage_radius(p) should match p
    # itself, not just "be well-calibrated on average" via ECE.
    rng = np.random.default_rng(3)
    n = 200000
    sigma = 2.0
    e = rng.standard_normal((3, n)) * sigma
    err = cal.displacement_error(e, np.zeros_like(e))
    for p in (0.1, 0.5, 0.9, 0.99):
        r = cal.coverage_radius(np.full(n, sigma), p, ndim=3)
        empirical = np.mean(err <= r)
        assert abs(empirical - p) < 0.01, f"p={p}: empirical={empirical}"


# ----------------------------------------------------------------------
# Split-conformal prediction -- previously zero test coverage; this is
# exactly where an independent adversarial audit found a real off-by-one
# bug (np.quantile(..., method="higher") did not match the documented
# ceil((n+1)(1-alpha))-th order statistic). These tests pin down the
# CORRECT behavior so a regression would be caught.
# ----------------------------------------------------------------------
def test_conformal_radius_exact_order_statistic():
    # Hand-constructed case where the exact answer is unambiguous: 10
    # calibration scores 1..10, alpha=0.1 -> k = ceil(11*0.9) = 10 -> the
    # 10th (largest) of 10 scores, i.e. q_hat should be exactly 10.0.
    err = np.arange(1, 11, dtype=float)
    sigma = np.ones(10)
    q_hat = cal.conformal_radius(err, sigma, alpha=0.10)
    assert q_hat == 10.0

    # alpha=0.3 -> k = ceil(11*0.7) = 8 -> the 8th smallest of 1..10 = 8.0.
    q_hat2 = cal.conformal_radius(err, sigma, alpha=0.30)
    assert q_hat2 == 8.0


def test_conformal_radius_infinite_when_not_enough_calibration_points():
    # k = ceil((n+1)(1-alpha)) can exceed n for small n / small alpha --
    # the honest answer is that no finite radius can guarantee that
    # confidence level, not a silently-too-narrow interval.
    err = np.array([1.0, 2.0, 3.0])
    sigma = np.ones(3)
    q_hat = cal.conformal_radius(err, sigma, alpha=0.01)
    assert q_hat == float("inf")


def test_conformal_coverage_achieves_target_on_exchangeable_data():
    # The actual guarantee conformal prediction makes: on held-out data
    # drawn the same way as the calibration data, achieved coverage should
    # meet or exceed the target with high probability. Checked here across
    # many independent cal/val splits of the same exchangeable dataset.
    rng = np.random.default_rng(4)
    n_total = 400
    sigma = np.full(n_total, 1.5)
    e = rng.standard_normal((3, n_total)) * sigma[None]
    err = cal.displacement_error(e, np.zeros_like(e))

    target = 0.90
    alpha = 1 - target
    below_target_count = 0
    n_trials = 200
    for i in range(n_trials):
        trial_rng = np.random.default_rng(1000 + i)
        perm = trial_rng.permutation(n_total)
        cal_idx, val_idx = perm[:200], perm[200:]
        q_hat = cal.conformal_radius(err[cal_idx], sigma[cal_idx], alpha=alpha)
        coverage = cal.conformal_coverage(err[val_idx], sigma[val_idx], q_hat)
        if coverage < target:
            below_target_count += 1
    # The marginal guarantee is about average coverage across splits, not
    # every single split -- but it should not fail the vast majority of the
    # time on genuinely exchangeable data.
    assert below_target_count / n_trials < 0.5


def test_conformal_coverage_min_sigma_matches_calibration_side():
    # Bug found and fixed: conformal_radius excludes calibration points with
    # sigma < min_sigma before fitting q_hat, but conformal_coverage
    # previously had no such filter, so it tested q_hat against a
    # validation set that still included near-zero-sigma points. Since
    # q_hat * sigma is tiny whenever sigma is near zero, any such point
    # with nonzero real error automatically "fails" coverage regardless of
    # q_hat's quality -- an asymmetry that breaks the exchangeability
    # assumption conformal prediction relies on.
    #
    # Construct data where a chunk of points have near-zero sigma AND
    # nonzero real error (the exact "blind spot" pattern seen on real
    # ensemble registration data). Without filtering, coverage should be
    # dragged down by these points regardless of q_hat; with the SAME
    # min_sigma filter applied on both sides, coverage on the well-behaved
    # points should meet target as designed.
    rng = np.random.default_rng(5)
    n_good = 300
    sigma_good = np.full(n_good, 1.5)
    e_good = rng.standard_normal((3, n_good)) * sigma_good[None]
    err_good = cal.displacement_error(e_good, np.zeros_like(e_good))

    n_blind = 100
    sigma_blind = np.full(n_blind, 0.0001)  # near-zero, like a real blind-spot point
    err_blind = np.full(n_blind, 2.0)  # but real error is NOT near zero

    err_all = np.concatenate([err_good, err_blind])
    sigma_all = np.concatenate([sigma_good, sigma_blind])

    min_sigma = 0.01
    alpha = 0.10
    q_hat = cal.conformal_radius(err_good, sigma_good, alpha=alpha, min_sigma=min_sigma)

    # Without the fix (min_sigma=0 disables filtering): the blind-spot
    # points drag coverage down hard, since q_hat * 0.0001 ~= 0 << 2.0.
    coverage_unfiltered = cal.conformal_coverage(err_all, sigma_all, q_hat, min_sigma=0.0)
    assert (
        coverage_unfiltered < 0.80
    ), "expected unfiltered coverage to be dragged down by blind-spot points"

    # With the SAME min_sigma applied to validation as calibration: the
    # blind-spot points are excluded from the guarantee (a disclosed blind
    # spot, not a hidden one), and coverage on the remaining points should
    # meet the target as split-conformal prediction promises.
    coverage_filtered = cal.conformal_coverage(err_all, sigma_all, q_hat, min_sigma=min_sigma)
    assert (
        coverage_filtered >= 0.85
    ), f"expected filtered coverage near target 0.90, got {coverage_filtered}"


def test_conformal_coverage_raises_when_all_points_below_min_sigma():
    err = np.array([1.0, 2.0])
    sigma = np.array([0.001, 0.002])
    with pytest.raises(ValueError):
        cal.conformal_coverage(err, sigma, q_hat=5.0, min_sigma=0.01)


if __name__ == "__main__":
    test_perfect_calibration_is_near_diagonal()
    test_recalibration_reduces_error()
    test_perfect_calibration_ndim3_is_near_diagonal()
    test_coverage_radius_ndim3_matches_chi_distribution()
    test_conformal_radius_exact_order_statistic()
    test_conformal_radius_infinite_when_not_enough_calibration_points()
    test_conformal_coverage_achieves_target_on_exchangeable_data()
    print("OK: all calibration tests passed.")
