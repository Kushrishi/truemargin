"""Tests for the frozen TrueMargin M6 hierarchical conformal primitives."""

from __future__ import annotations

import numpy as np
import pytest

from truemargin.hierarchical_conformal import (
    calibrated_radius,
    equal_group_coverage,
    hierarchical_conformal_threshold,
    ratio_nonconformity,
)


def test_ratio_nonconformity_preserves_zero_signal_rule() -> None:
    error = np.array([0.0, 2.0, 4.0, 3.0])
    signal = np.array([0.0, 0.0, 2.0, 1.5])

    scores = ratio_nonconformity(error, signal)

    assert scores[0] == 0.0
    assert np.isposinf(scores[1])
    assert scores[2] == 2.0
    assert scores[3] == 2.0


def test_ratio_nonconformity_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="matching one-dimensional"):
        ratio_nonconformity(np.zeros(2), np.zeros((2, 1)))
    with pytest.raises(ValueError, match="finite nonnegative"):
        ratio_nonconformity(np.array([1.0, np.nan]), np.ones(2))
    with pytest.raises(ValueError, match="finite nonnegative"):
        ratio_nonconformity(np.ones(2), np.array([1.0, -1.0]))


def test_hcp_uses_equal_group_mass_not_pooled_point_mass() -> None:
    groups = [
        np.array([1.0]),
        np.array([2.0, 3.0, 4.0]),
    ]

    result = hierarchical_conformal_threshold(groups, nominal_coverage=0.50)

    assert result.threshold == 3.0
    assert result.calibration_groups == 2
    assert result.calibration_scores == 4
    assert result.infinity_atom_mass == pytest.approx(1.0 / 3.0)


def test_m6_k15_nominal_levels_match_frozen_discrete_construction() -> None:
    groups = [np.arange(50, dtype=np.float64) for _ in range(15)]

    q80 = hierarchical_conformal_threshold(groups, nominal_coverage=0.80)
    q90 = hierarchical_conformal_threshold(groups, nominal_coverage=0.90)
    q95 = hierarchical_conformal_threshold(groups, nominal_coverage=0.95)

    assert q80.threshold == 42.0
    assert q90.threshold == 47.0
    assert np.isposinf(q95.threshold)
    assert q95.infinity_atom_mass == pytest.approx(1.0 / 16.0)


def test_hcp_retains_positive_infinity_scores() -> None:
    groups = [
        np.array([0.0, 1.0, np.inf]),
        np.array([0.0, 1.0, 2.0]),
    ]

    result = hierarchical_conformal_threshold(groups, nominal_coverage=0.80)

    assert np.isposinf(result.threshold)


def test_hcp_rejects_negative_nan_and_negative_infinity_scores() -> None:
    for invalid in (-1.0, np.nan, -np.inf):
        with pytest.raises(ValueError, match="invalid nonconformity score"):
            hierarchical_conformal_threshold(
                [np.array([0.0, invalid])],
                nominal_coverage=0.90,
            )


def test_hcp_rejects_invalid_nominal_coverage() -> None:
    groups = [np.array([1.0, 2.0])]
    for invalid in (0.0, 1.0, -0.1, 1.1, np.nan):
        with pytest.raises(ValueError, match="nominal_coverage"):
            hierarchical_conformal_threshold(groups, nominal_coverage=invalid)


def test_calibrated_radius_handles_finite_and_infinite_thresholds() -> None:
    signal = np.array([0.0, 1.5, 2.0])

    finite = calibrated_radius(signal, 2.0)
    infinite = calibrated_radius(signal, np.inf)

    np.testing.assert_allclose(finite, np.array([0.0, 3.0, 4.0]))
    assert np.isposinf(infinite).all()


def test_calibrated_radius_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="finite nonnegative"):
        calibrated_radius(np.array([1.0, np.nan]), 2.0)
    with pytest.raises(ValueError, match="threshold"):
        calibrated_radius(np.array([1.0]), -1.0)


def test_equal_group_coverage_weights_anatomies_equally() -> None:
    errors = [
        np.array([1.0]),
        np.array([1.0, 2.0, 3.0]),
    ]
    radii = [
        np.array([0.0]),
        np.array([2.0, 2.0, 2.0]),
    ]

    per_group, mean = equal_group_coverage(errors, radii)

    np.testing.assert_allclose(per_group, np.array([0.0, 2.0 / 3.0]))
    assert mean == pytest.approx(1.0 / 3.0)


def test_equal_group_coverage_accepts_infinite_radii() -> None:
    per_group, mean = equal_group_coverage(
        [np.array([1.0, 2.0])],
        [np.array([np.inf, np.inf])],
    )

    np.testing.assert_allclose(per_group, np.array([1.0]))
    assert mean == 1.0
