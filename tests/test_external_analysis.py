import numpy as np
import pytest

from truemargin.external_analysis import (
    aggregate_cases,
    bootstrap_median,
    case_statistics,
    physical_to_index_xyz,
    sample_grid,
)


def test_physical_coordinates_and_field_component_order():
    direction = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    index = np.array([[1.5, 2.0, 1.0]])
    spacing = np.array([2.0, 3.0, 4.0])
    origin = np.array([11.0, -3.0, 42.0])
    physical = origin + (direction @ (index * spacing).T).T
    np.testing.assert_allclose(physical_to_index_xyz(physical, spacing, origin, direction), index)
    z, y, x = np.indices((3, 4, 5))
    field = np.stack([x + 2 * y, 3 * z, 4 * x + y]).astype(float)
    np.testing.assert_allclose(sample_grid(field, index), [[5.5, 3.0, 8.0]])
    np.testing.assert_allclose(sample_grid(x.astype(float), index), [1.5])
    with pytest.raises(ValueError):
        sample_grid(field, [[5, 0, 0]])


def test_case_hierarchy_sign_and_bootstrap():
    ids = [f"{i:03}" for i in range(21, 31)]
    row = case_statistics(
        [1, 2, 3, 4],
        {"spread": [1, 2, 3, 4], "ice": [4, 3, 2, 1], "residual": None, "jacobian": [1, 1, 1, 1]},
    )
    result = aggregate_cases(dict.fromkeys(ids, row), ids)
    assert result["median_case_rho"] == 1
    assert result["sign_test_one_sided"] == 1 / 1024
    assert result["median_bootstrap_95"] == [1, 1]
    assert result["comparators"]["ice"]["paired_differences"] == [2] * 10
    assert result["comparators"]["residual"]["failed_or_undefined_case_ids"] == ids
    assert bootstrap_median([-0.2, 0.3, 0.7]) == bootstrap_median([-0.2, 0.3, 0.7])
    with pytest.raises(ValueError):
        aggregate_cases({ids[0]: row}, ids)


def test_undefined_target_not_silently_dropped():
    ids = [str(i) for i in range(10)]
    row = case_statistics([1, 2], {"spread": [1, 1]})
    assert aggregate_cases(dict.fromkeys(ids, row), ids)["status"] == "primary_not_assessable"
