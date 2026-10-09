"""Synthetic software parity only; no registration or real reference payloads."""

import numpy as np
import pytest

from truemargin.comparators import (
    absolute_residual_scores,
    indices_zyx_to_physical_xyz,
    inverse_consistency_scores,
    jacobian_deviation_scores,
    sample_scalar_physical,
)
from truemargin.ensemble import summarize_fields, summarize_fields_blockwise


@pytest.mark.parametrize("block", [2, 13, 47, 1000])
def test_disk_summary_and_comparator_parity(tmp_path, block):
    pytest.importorskip("SimpleITK")
    rng = np.random.default_rng(20261009)
    shape = (4, 5, 7)
    fields = [rng.uniform(-0.08, 0.08, (3, *shape)) for _ in range(9)]
    reverse = [rng.uniform(-0.08, 0.08, (3, *shape)) for _ in range(9)]
    expected_forward, expected_sigma = summarize_fields(fields)
    expected_reverse, _ = summarize_fields(reverse)

    def disk_summary(values, direction):
        mapped = []
        for member, field in enumerate(values):
            path = tmp_path / f"{direction}-{member}.npy"
            np.save(path, field, allow_pickle=False)
            mapped.append(np.load(path, mmap_mode="r", allow_pickle=False))
        mean, sigma = summarize_fields_blockwise(mapped, block_voxels=block)
        # Round-trip the summaries that a later analysis would actually consume.
        outputs = []
        for name, value in (("mean", mean), ("sigma", sigma)):
            path = tmp_path / f"{direction}-{name}.npy"
            np.save(path, value, allow_pickle=False)
            outputs.append(np.load(path, mmap_mode="r", allow_pickle=False))
        return outputs

    actual_forward, actual_sigma = disk_summary(fields, "forward")
    actual_reverse, _ = disk_summary(reverse, "reverse")
    for expected, actual in (
        (expected_forward, actual_forward),
        (expected_reverse, actual_reverse),
        (expected_sigma, actual_sigma),
    ):
        assert actual.dtype == expected.dtype == np.float64
        np.testing.assert_array_equal(actual, expected)

    spacing = (0.97, 1.16, 2.5)
    # Analytically interior synthetic points; no dataset landmark values.
    points = np.array([[1.1, 1.4, 2.2], [2.1, 2.4, 3.6]])
    z, y, x = np.indices(shape, dtype=np.float64)
    fixed = 1024 + 2 * x + 3 * y + 4 * z
    moving = fixed + 5 + 0.1 * x
    for expected, actual in (
        (
            sample_scalar_physical(
                expected_sigma, indices_zyx_to_physical_xyz(points, spacing), spacing
            ),
            sample_scalar_physical(
                actual_sigma, indices_zyx_to_physical_xyz(points, spacing), spacing
            ),
        ),
        (
            inverse_consistency_scores(expected_forward, expected_reverse, points, spacing),
            inverse_consistency_scores(actual_forward, actual_reverse, points, spacing),
        ),
        (
            absolute_residual_scores(fixed, moving, expected_forward, points, spacing),
            absolute_residual_scores(fixed, moving, actual_forward, points, spacing),
        ),
        (
            jacobian_deviation_scores(expected_forward, points, spacing),
            jacobian_deviation_scores(actual_forward, points, spacing),
        ),
    ):
        np.testing.assert_array_equal(actual, expected)
