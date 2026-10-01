"""Unit tests for generic calibration and ordinary split-conformal helpers."""

import numpy as np
import pytest

from truemargin import calibration as cal


def test_perfect_calibration_is_near_diagonal():
    rng = np.random.default_rng(0)
    H = W = 200
    sigma = np.full((H, W), 1.0)
    e = rng.standard_normal((2, H, W)) * sigma[None]
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp = cal.reliability_curve(err, sigma, ndim=2)
    assert cal.expected_calibration_error(lv, emp) < 0.03


def test_recalibration_reduces_error():
    rng = np.random.default_rng(1)
    H = W = 200
    sigma_pred = np.full((H, W), 0.4)
    true_sigma = 1.0
    e = rng.standard_normal((2, H, W)) * true_sigma
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp_raw = cal.reliability_curve(err, sigma_pred, ndim=2)
    s = cal.fit_variance_scale(err, sigma_pred, ndim=2)
    lv, emp_fix = cal.reliability_curve(err, s * sigma_pred, ndim=2)
    assert cal.expected_calibration_error(lv, emp_fix) < cal.expected_calibration_error(lv, emp_raw)
    assert abs(s - (true_sigma / 0.4)) < 0.15


def test_perfect_calibration_ndim3_is_near_diagonal():
    rng = np.random.default_rng(2)
    n = 20000
    sigma = np.full(n, 1.0)
    e = rng.standard_normal((3, n)) * sigma[None]
    err = cal.displacement_error(e, np.zeros_like(e))
    lv, emp = cal.reliability_curve(err, sigma, ndim=3)
    assert cal.expected_calibration_error(lv, emp) < 0.03


def test_coverage_radius_ndim3_matches_chi_distribution():
    rng = np.random.default_rng(3)
    n = 200000
    sigma = 2.0
    e = rng.standard_normal((3, n)) * sigma
    err = cal.displacement_error(e, np.zeros_like(e))
    for p in (0.1, 0.5, 0.9, 0.99):
        r = cal.coverage_radius(np.full(n, sigma), p, ndim=3)
        empirical = np.mean(err <= r)
        assert abs(empirical - p) < 0.01, f"p={p}: empirical={empirical}"


def test_conformal_radius_exact_order_statistic():
    # Ten calibration scores 1..10, alpha=0.1:
    # k = ceil((10 + 1) * 0.9) = 10, so q_hat is the largest score.
    err = np.arange(1, 11, dtype=float)
    sigma = np.ones(10)
    q_hat = cal.conformal_radius(err, sigma, alpha=0.10)
    assert q_hat == 10.0

    # alpha=0.3 -> k = ceil(11 * 0.7) = 8.
    q_hat2 = cal.conformal_radius(err, sigma, alpha=0.30)
    assert q_hat2 == 8.0


def test_conformal_radius_infinite_when_not_enough_calibration_points():
    # If k exceeds n, the requested ordinary split-conformal level has no
    # finite calibration order statistic under this construction.
    err = np.array([1.0, 2.0, 3.0])
    sigma = np.ones(3)
    q_hat = cal.conformal_radius(err, sigma, alpha=0.01)
    assert q_hat == float("inf")


def test_conformal_coverage_achieves_target_on_exchangeable_data():
    # Monte Carlo sanity check for the helper under an actually exchangeable
    # synthetic point-level setting. This test does not model the grouped M6
    # anatomy structure and therefore does not validate an M6 coverage claim.
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
    assert below_target_count / n_trials < 0.5


def test_conformal_coverage_min_sigma_matches_calibration_side():
    # Verify that the evaluation helper applies the same retained-domain rule
    # as the calibration helper. Coverage reported after filtering is coverage
    # on that retained domain; excluded low-sigma observations must be reported
    # separately in a scientific analysis.
    rng = np.random.default_rng(5)
    n_good = 300
    sigma_good = np.full(n_good, 1.5)
    e_good = rng.standard_normal((3, n_good)) * sigma_good[None]
    err_good = cal.displacement_error(e_good, np.zeros_like(e_good))

    n_blind = 100
    sigma_blind = np.full(n_blind, 0.0001)
    err_blind = np.full(n_blind, 2.0)

    err_all = np.concatenate([err_good, err_blind])
    sigma_all = np.concatenate([sigma_good, sigma_blind])

    min_sigma = 0.01
    alpha = 0.10
    q_hat = cal.conformal_radius(err_good, sigma_good, alpha=alpha, min_sigma=min_sigma)

    coverage_unfiltered = cal.conformal_coverage(err_all, sigma_all, q_hat, min_sigma=0.0)
    assert coverage_unfiltered < 0.80

    coverage_filtered = cal.conformal_coverage(err_all, sigma_all, q_hat, min_sigma=min_sigma)
    assert coverage_filtered >= 0.85


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
