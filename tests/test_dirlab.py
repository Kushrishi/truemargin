"""Synthetic-only tests for DIR-Lab pre-outcome coordinate handling."""

import numpy as np
import pytest

from truemargin.dirlab import (
    DIRLAB_4DCT_CASES,
    case_geometry,
    index_xyz_to_native_physical_mm,
    one_based_rl_ap_si_to_zero_based_index_xyz,
)


def test_public_case_geometry_is_complete_and_unique():
    assert [row.case_id for row in DIRLAB_4DCT_CASES] == [
        "4DCT1",
        "4DCT2",
        "4DCT3",
        "4DCT4",
        "4DCT5",
        "4DCT6",
        "4DCT7",
        "4DCT8",
        "4DCT9",
        "4DCT10",
    ]
    assert len({row.case_id for row in DIRLAB_4DCT_CASES}) == 10
    assert case_geometry("4DCT1").size_xyz == (256, 256, 94)
    assert case_geometry("4DCT10").spacing_xyz_mm == pytest.approx((0.97, 0.97, 2.5))
    assert all(row.expected_int16_bytes == np.prod(row.size_xyz) * 2 for row in DIRLAB_4DCT_CASES)


def test_one_based_origin_and_fractional_voxel_conversion():
    converted = one_based_rl_ap_si_to_zero_based_index_xyz(
        np.array([[1.0, 1.0, 1.0], [2.5, 3.25, 4.75]]),
        size_xyz=(10, 11, 12),
    )
    np.testing.assert_allclose(converted, [[0.0, 0.0, 0.0], [1.5, 2.25, 3.75]])


def test_documented_axis_order_is_not_permuted_or_reflected():
    index = one_based_rl_ap_si_to_zero_based_index_xyz(
        np.array([[4.0, 5.0, 6.0]]),
        size_xyz=(10, 11, 12),
    )
    physical = index_xyz_to_native_physical_mm(
        index,
        spacing_xyz_mm=(2.0, 3.0, 4.0),
    )
    np.testing.assert_allclose(index, [[3.0, 4.0, 5.0]])
    np.testing.assert_allclose(physical, [[6.0, 12.0, 20.0]])


@pytest.mark.parametrize(
    "coordinates",
    [
        np.array([[0.0, 1.0, 1.0]]),
        np.array([[11.0, 1.0, 1.0]]),
        np.array([[1.0, float("nan"), 1.0]]),
        np.array([[1.0, float("inf"), 1.0]]),
    ],
)
def test_invalid_coordinate_values_are_rejected(coordinates):
    with pytest.raises(ValueError):
        one_based_rl_ap_si_to_zero_based_index_xyz(coordinates, size_xyz=(10, 10, 10))


def test_coordinate_conversion_rejects_non_numeric_or_malformed_input():
    with pytest.raises(ValueError, match="numeric"):
        one_based_rl_ap_si_to_zero_based_index_xyz(
            np.array([["1", "2", "3"]]),
            size_xyz=(10, 10, 10),
        )
    with pytest.raises(ValueError, match="shape"):
        one_based_rl_ap_si_to_zero_based_index_xyz(
            np.array([1.0, 2.0, 3.0]),
            size_xyz=(10, 10, 10),
        )


def test_unknown_case_is_rejected():
    with pytest.raises(ValueError, match="unknown"):
        case_geometry("4DCT11")
