"""Tests for metrics.py -- previously had NO test file at all, which is
exactly how an independent adversarial audit found jacobian_determinant
computing a wrong result: the function was unused everywhere else in the
repo, so nothing ever exercised it, and no test would have caught a bug in
it either way."""

import numpy as np

from truemargin import metrics


def test_dice_perfect_overlap():
    a = np.array([[1, 1, 0], [0, 1, 0]])
    b = np.array([[1, 1, 0], [0, 1, 0]])
    assert metrics.dice(a, b) == 1.0


def test_dice_no_overlap():
    a = np.array([[1, 1, 0], [0, 0, 0]])
    b = np.array([[0, 0, 0], [0, 0, 1]])
    assert metrics.dice(a, b) == 0.0


def test_dice_both_empty_is_perfect_by_convention():
    a = np.zeros((3, 3))
    b = np.zeros((3, 3))
    assert metrics.dice(a, b) == 1.0


def test_jacobian_determinant_identity_field_is_one():
    # Zero displacement everywhere -- the identity map has Jacobian 1
    # everywhere (no stretching, no folding).
    shape = (10, 10)
    disp = np.zeros((2, *shape))
    j = metrics.jacobian_determinant(disp)
    np.testing.assert_allclose(j, 1.0)


def test_jacobian_determinant_matches_closed_form_anisotropic_stretch():
    # Found via independent adversarial audit: an earlier version of this
    # function paired the diagonal/off-diagonal partial derivatives up
    # wrong, which an isotropic test case (e.g. uniform scaling) would NOT
    # have caught, since the wrong pairing happens to give the same answer
    # when the field is symmetric between axes. This uses an ANISOTROPIC
    # field specifically because that's what exposes the bug: the map
    # (y, x) -> (y + 1*y, x) = (2y, x) has a known, closed-form Jacobian of
    # exactly 2.0 everywhere (only the y-axis is stretched, by 2x; x is
    # unchanged) -- the buggy version returned 1.0, completely missing the
    # area doubling.
    shape = (20, 20)
    y, _x = np.indices(shape).astype(np.float64)
    disp = np.zeros((2, *shape))
    disp[0] = 1.0 * y  # y-displacement grows linearly with y -- pure y-stretch
    disp[1] = 0.0  # no x-displacement at all

    j = metrics.jacobian_determinant(disp)
    # Skip the outer 2 voxels on each side: np.gradient uses one-sided
    # differences at the array boundary, which are less accurate for a
    # linear-but-not-constant field near the edge -- not what this test is
    # about, so avoid it rather than loosen the tolerance everywhere.
    interior = j[2:-2, 2:-2]
    np.testing.assert_allclose(interior, 2.0, atol=1e-6)


def test_jacobian_determinant_flags_folding_as_nonpositive():
    # A strong enough local compression should push the Jacobian below zero
    # (physically impossible folding) -- fraction_folded relies on exactly
    # this threshold.
    shape = (20, 20)
    y, _x = np.indices(shape).astype(np.float64)
    disp = np.zeros((2, *shape))
    disp[0] = -2.0 * y  # y-displacement shrinks faster than 1:1 -- folds
    j = metrics.jacobian_determinant(disp)
    interior = j[2:-2, 2:-2]
    assert np.all(interior < 0), "Expected folding (negative Jacobian) but found none"


def test_fraction_folded_zero_for_identity():
    shape = (10, 10)
    disp = np.zeros((2, *shape))
    assert metrics.fraction_folded(disp) == 0.0


def test_jacobian_determinant_3d_not_implemented():
    disp = np.zeros((3, 5, 5, 5))
    try:
        metrics.jacobian_determinant(disp)
        raise AssertionError("Expected NotImplementedError for 3D input")
    except NotImplementedError:
        pass
