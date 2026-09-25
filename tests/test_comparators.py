from __future__ import annotations

import numpy as np
import pytest

from truemargin import comparators


def _constant_translation_field(
    shape_zyx: tuple[int, int, int],
    translation_xyz: tuple[float, float, float],
) -> np.ndarray:
    field = np.zeros((3, *shape_zyx), dtype=np.float64)
    for component, value in enumerate(translation_xyz):
        field[component] = value
    return field


def test_indices_zyx_to_physical_xyz_respects_anisotropic_spacing() -> None:
    idx = np.asarray([[2, 3, 4], [1, 5, 6]], dtype=np.int64)

    physical = comparators.indices_zyx_to_physical_xyz(
        idx,
        spacing_xyz=(0.5, 1.5, 2.0),
    )

    np.testing.assert_allclose(
        physical,
        np.asarray(
            [
                [2.0, 4.5, 4.0],
                [3.0, 7.5, 2.0],
            ]
        ),
    )


def test_inverse_consistency_is_zero_for_perfect_inverse_translation() -> None:
    shape = (9, 10, 12)
    spacing = (0.5, 1.0, 2.0)
    forward = _constant_translation_field(shape, (1.0, 0.0, 0.0))
    reverse = _constant_translation_field(shape, (-1.0, 0.0, 0.0))
    landmarks = np.asarray([[4, 4, 4], [4, 5, 6], [5, 6, 7]], dtype=np.int64)

    ice = comparators.inverse_consistency_scores(forward, reverse, landmarks, spacing)

    np.testing.assert_allclose(ice, 0.0, atol=1e-12)


def test_inverse_consistency_reports_known_translation_mismatch() -> None:
    shape = (9, 10, 12)
    spacing = (0.5, 1.0, 2.0)
    forward = _constant_translation_field(shape, (1.0, 0.0, 0.0))
    reverse = _constant_translation_field(shape, (-0.25, 0.0, 0.0))
    landmarks = np.asarray([[4, 4, 4], [4, 5, 6]], dtype=np.int64)

    ice = comparators.inverse_consistency_scores(forward, reverse, landmarks, spacing)

    np.testing.assert_allclose(ice, 0.75, atol=1e-12)


def test_inverse_consistency_fails_when_cycle_sampling_leaves_domain() -> None:
    shape = (7, 7, 7)
    forward = _constant_translation_field(shape, (10.0, 0.0, 0.0))
    reverse = _constant_translation_field(shape, (-10.0, 0.0, 0.0))
    landmarks = np.asarray([[3, 3, 3]], dtype=np.int64)

    with pytest.raises(ValueError, match="outside the image domain"):
        comparators.inverse_consistency_scores(
            forward,
            reverse,
            landmarks,
            spacing_xyz=(1.0, 1.0, 1.0),
        )


def test_absolute_residual_is_zero_for_exact_linear_translation() -> None:
    shape = (7, 8, 12)
    spacing = (0.5, 1.0, 2.0)
    x_mm = np.arange(shape[2], dtype=np.float64) * spacing[0]
    moving = np.broadcast_to(x_mm, shape).copy()
    forward = _constant_translation_field(shape, (1.0, 0.0, 0.0))
    fixed = moving + 1.0
    landmarks = np.asarray([[3, 3, 3], [3, 4, 6], [4, 5, 7]], dtype=np.int64)

    residual = comparators.absolute_residual_scores(
        fixed,
        moving,
        forward,
        landmarks,
        spacing,
    )

    np.testing.assert_allclose(residual, 0.0, atol=1e-12)


def test_absolute_residual_preserves_known_mismatch() -> None:
    shape = (7, 8, 12)
    moving = np.broadcast_to(np.arange(shape[2], dtype=np.float64), shape).copy()
    forward = _constant_translation_field(shape, (1.0, 0.0, 0.0))
    fixed = moving + 2.0
    landmarks = np.asarray([[3, 3, 3], [3, 4, 6]], dtype=np.int64)

    residual = comparators.absolute_residual_scores(
        fixed,
        moving,
        forward,
        landmarks,
        spacing_xyz=(1.0, 1.0, 1.0),
    )

    np.testing.assert_allclose(residual, 1.0, atol=1e-12)


def test_jacobian_deviation_is_zero_for_identity_field() -> None:
    shape = (9, 10, 11)
    field = np.zeros((3, *shape), dtype=np.float64)
    landmarks = np.asarray([[4, 4, 4], [5, 5, 5]], dtype=np.int64)

    score = comparators.jacobian_deviation_scores(
        field,
        landmarks,
        spacing_xyz=(0.5, 1.0, 2.0),
    )

    np.testing.assert_allclose(score, 0.0, atol=1e-12)


def test_jacobian_deviation_matches_known_x_scaling() -> None:
    shape = (9, 10, 11)
    spacing = (0.5, 1.0, 2.0)
    alpha = 0.2
    x_mm = np.arange(shape[2], dtype=np.float64) * spacing[0]
    field = np.zeros((3, *shape), dtype=np.float64)
    field[0] = alpha * np.broadcast_to(x_mm, shape)
    landmarks = np.asarray([[4, 4, 4], [5, 5, 6]], dtype=np.int64)

    score = comparators.jacobian_deviation_scores(field, landmarks, spacing)

    np.testing.assert_allclose(score, alpha, rtol=1e-10, atol=1e-10)


def test_rank_association_maps_degenerate_score_to_zero() -> None:
    rho, degenerate = comparators.rank_association(
        np.ones(50, dtype=np.float64),
        np.arange(50, dtype=np.float64),
    )

    assert rho == 0.0
    assert degenerate is True


def test_rank_association_preserves_positive_ordering() -> None:
    error = np.asarray([0.1, 0.4, 0.2, 0.9, 0.7], dtype=np.float64)

    rho, degenerate = comparators.rank_association(error.copy(), error)

    assert rho == pytest.approx(1.0)
    assert degenerate is False


def test_holm_adjustment_is_monotone_in_sorted_order() -> None:
    adjusted = comparators.holm_adjust(np.asarray([0.01, 0.04, 0.03]))

    np.testing.assert_allclose(adjusted, np.asarray([0.03, 0.06, 0.06]))


def test_paired_bootstrap_is_deterministic() -> None:
    target = np.asarray([0.5, 0.4, 0.7, 0.2, 0.6, 0.3, 0.8, 0.45])
    comparator = np.asarray([0.3, 0.35, 0.5, 0.1, 0.55, 0.2, 0.65, 0.25])

    first = comparators.paired_median_bootstrap(
        target,
        comparator,
        n_bootstraps=500,
        seed=0,
    )
    second = comparators.paired_median_bootstrap(
        target,
        comparator,
        n_bootstraps=500,
        seed=0,
    )

    assert first == second
    assert first[1] <= first[0] <= first[2]
