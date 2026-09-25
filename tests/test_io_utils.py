"""Tests for the real-data glue helpers in io_utils.py -- these don't need
SimpleITK/OpenSlide or any downloaded data, only numpy."""

import numpy as np
import pytest

from truemargin import io_utils


class _FakeImage:
    """Minimal stand-in for a SimpleITK Image exposing just the four grid
    properties assert_same_grid checks -- lets this test run without
    SimpleITK installed (SimpleITK is not available in every environment
    this test suite runs in, e.g. CI's fast lint job or this sandbox)."""

    def __init__(self, size, spacing, origin, direction):
        self._size = size
        self._spacing = spacing
        self._origin = origin
        self._direction = direction

    def GetSize(self):
        return self._size

    def GetSpacing(self):
        return self._spacing

    def GetOrigin(self):
        return self._origin

    def GetDirection(self):
        return self._direction


def _grid(size=(10, 10, 5), spacing=(0.5, 0.5, 3.0), origin=(0.0, 0.0, 0.0)):
    return _FakeImage(size, spacing, origin, (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))


def test_assert_same_grid_passes_for_identical_grids():
    a, b = _grid(), _grid()
    io_utils.assert_same_grid(a, b)  # should not raise


def test_assert_same_grid_catches_size_mismatch():
    a = _grid(size=(10, 10, 5))
    b = _grid(size=(10, 10, 6))
    with pytest.raises(ValueError, match="size"):
        io_utils.assert_same_grid(a, b)


def test_assert_same_grid_catches_origin_mismatch():
    # This is the specific, subtle case found by an independent audit:
    # matching size (so nothing else would crash downstream) but a
    # sub-voxel origin shift, which would otherwise silently bias every
    # landmark's assumed physical location instead of raising an error.
    a = _grid(origin=(0.0, 0.0, 0.0))
    b = _grid(origin=(0.3, 0.0, 0.0))  # sub-voxel shift given spacing=0.5
    with pytest.raises(ValueError, match="origin"):
        io_utils.assert_same_grid(a, b)


def test_assert_same_grid_catches_spacing_mismatch():
    a = _grid(spacing=(0.5, 0.5, 3.0))
    b = _grid(spacing=(0.4, 0.5, 3.0))
    with pytest.raises(ValueError, match="spacing"):
        io_utils.assert_same_grid(a, b)


def test_assert_same_grid_tolerates_tiny_floating_point_noise():
    # DICOM-derived floating point values (e.g. from GDCM parsing) can differ
    # by a tiny amount even for "the same" grid across two separately-read
    # images -- the tolerance exists specifically so this doesn't false-fire
    # on harmless numerical noise.
    a = _grid(origin=(0.0, 0.0, 0.0))
    b = _grid(origin=(1e-6, 0.0, 0.0))
    io_utils.assert_same_grid(a, b)  # should not raise


def test_load_landmark_pairs_roundtrip(tmp_path):
    fixed = np.array([[1.0, 2.0], [3.0, 4.0]])
    moving = np.array([[1.5, 2.5], [3.5, 4.5]])
    csv_path = tmp_path / "landmarks.csv"
    np.savetxt(csv_path, np.hstack([fixed, moving]), delimiter=",")

    f, m = io_utils.load_landmark_pairs(str(csv_path), ndim=2)
    np.testing.assert_allclose(f, fixed)
    np.testing.assert_allclose(m, moving)


def test_load_landmark_pairs_wrong_ndim_raises(tmp_path):
    csv_path = tmp_path / "landmarks.csv"
    np.savetxt(csv_path, np.array([[1.0, 2.0, 3.0, 4.0]]), delimiter=",")
    with pytest.raises(ValueError):
        io_utils.load_landmark_pairs(str(csv_path), ndim=3)


def test_sample_field_at_points_scalar():
    field = np.arange(25.0).reshape(5, 5)
    points = np.array([[0, 0], [2, 3], [4, 4]])
    got = io_utils.sample_field_at_points(field, points)
    np.testing.assert_allclose(got, [field[0, 0], field[2, 3], field[4, 4]])


def test_sample_field_at_points_vector():
    field = np.stack([np.arange(25.0).reshape(5, 5), -np.arange(25.0).reshape(5, 5)])
    points = np.array([[1, 1], [3, 2]])
    got = io_utils.sample_field_at_points(field, points)
    assert got.shape == (2, 2)
    np.testing.assert_allclose(got[:, 0], field[:, 1, 1])
    np.testing.assert_allclose(got[:, 1], field[:, 3, 2])


# ----------------------------------------------------------------------
# crop_to_mask_bbox -- previously zero test coverage despite being exactly
# the kind of function (index-shifting, asymmetric axes) most prone to
# silent (z,y,x) vs (x,y,z) bugs in medical imaging code. An independent
# adversarial audit specifically checked this by hand and found it correct;
# this test pins that down so a future regression would be caught.
# ----------------------------------------------------------------------
def test_crop_to_mask_bbox_preserves_landmark_values():
    rng = np.random.default_rng(0)
    # Deliberately asymmetric shape (z, y, x all different) so a swapped
    # axis order would produce a shape mismatch or a wrong-value lookup
    # rather than accidentally still working.
    shape = (8, 20, 30)
    fixed = rng.standard_normal(shape)
    moving = rng.standard_normal(shape)
    mask = np.zeros(shape, dtype=np.uint8)
    mask[3:5, 8:12, 15:20] = 1  # small region of interest, off-center on every axis

    # A landmark inside the mask region, in ORIGINAL (uncropped) (z,y,x) index space.
    points_idx = np.array([[4, 10, 17], [3, 9, 16]])

    fixed_val_before = fixed[4, 10, 17]
    moving_val_before = moving[3, 9, 16]

    fixed_crop, moving_crop, points_crop = io_utils.crop_to_mask_bbox(
        fixed, moving, mask, points_idx, pad=2
    )

    # The cropped array must be smaller (the whole point of cropping).
    assert fixed_crop.shape != shape
    assert all(c <= s for c, s in zip(fixed_crop.shape, shape, strict=True))

    # Looking up the SAME landmark via its re-expressed cropped-space index
    # must return the identical original value -- this is the property a
    # swapped axis order would break.
    z0, y0, x0 = points_crop[0]
    z1, y1, x1 = points_crop[1]
    assert fixed_crop[z0, y0, x0] == fixed_val_before
    assert moving_crop[z1, y1, x1] == moving_val_before


def test_crop_to_mask_bbox_empty_mask_raises():
    shape = (5, 5, 5)
    fixed = np.zeros(shape)
    moving = np.zeros(shape)
    mask = np.zeros(shape, dtype=np.uint8)  # no voxels set
    points_idx = np.array([[0, 0, 0]])
    with pytest.raises(ValueError):
        io_utils.crop_to_mask_bbox(fixed, moving, mask, points_idx)


# ----------------------------------------------------------------------
# _select_dce_phase_files -- the fix for the DCE multi-phase loading bug
# found via independent review + direct file-count verification (13 of 15
# real patients had DCE series 15-20x larger than their T2 series; aaa0086's
# 720-file series was confirmed via scripts/_inspect_dce_phases.py to be
# exactly 36 real slice positions x 20 repeated time-phases). These tests
# use fabricated position/time strings, matching real DICOM tag format, so
# they run without SimpleITK or any downloaded data.
# ----------------------------------------------------------------------
def test_select_dce_phase_files_picks_middle_phase_by_default():
    from truemargin.io_utils import _select_dce_phase_files

    # 2 slice positions (z=0, z=1), each scanned 3 times (3 phases).
    filenames = ["p0t0", "p0t1", "p0t2", "p1t0", "p1t1", "p1t2"]
    positions = [
        "0.0\\0.0\\0.0",
        "0.0\\0.0\\0.0",
        "0.0\\0.0\\0.0",
        "0.0\\0.0\\1.0",
        "0.0\\0.0\\1.0",
        "0.0\\0.0\\1.0",
    ]
    times = ["100000", "100020", "100040", "100000", "100020", "100040"]

    chosen = _select_dce_phase_files(filenames, positions, times, phase_fraction=0.5)

    # 3 phases -> middle index = 1 -> "t1" files, one per position, ordered by z.
    assert chosen == ["p0t1", "p1t1"]


def test_select_dce_phase_files_first_and_last_phase():
    from truemargin.io_utils import _select_dce_phase_files

    filenames = ["p0t0", "p0t1", "p0t2", "p1t0", "p1t1", "p1t2"]
    positions = ["0.0\\0.0\\0.0"] * 3 + ["0.0\\0.0\\1.0"] * 3
    times = ["100000", "100020", "100040"] * 2

    first = _select_dce_phase_files(filenames, positions, times, phase_fraction=0.0)
    last = _select_dce_phase_files(filenames, positions, times, phase_fraction=1.0)
    assert first == ["p0t0", "p1t0"]
    assert last == ["p0t2", "p1t2"]


def test_select_dce_phase_files_orders_by_z_not_input_order():
    from truemargin.io_utils import _select_dce_phase_files

    # Positions given out of z-order on purpose (z=5 listed before z=-3).
    filenames = ["a", "b"]
    positions = ["0\\0\\5.0", "0\\0\\-3.0"]
    times = ["100000", "100000"]

    chosen = _select_dce_phase_files(filenames, positions, times, phase_fraction=0.0)
    # z=-3.0 (file "b") should come first, then z=5.0 (file "a").
    assert chosen == ["b", "a"]


def test_select_dce_phase_files_tolerates_small_real_world_mismatch():
    # Real case found on aaa0051's actual DCE series: 32 slice positions,
    # 30 repeated 18 times and 2 repeated only 17 times (574 files total,
    # most plausibly the scanner truncating the last temporal phase for a
    # couple of outer slices). This must NOT raise -- a strict "every
    # position repeated identically" rule broke on real clinical data.
    from truemargin.io_utils import _select_dce_phase_files

    filenames: list[str] = []
    positions: list[str] = []
    times: list[str] = []
    for pi, z in enumerate([0.0, 3.0, 6.0]):
        n = 17 if pi == 1 else 18  # middle position has one fewer repeat
        for t in range(n):
            filenames.append(f"p{pi}t{t}")
            positions.append(f"0.0\\0.0\\{z}")
            times.append(str(100000 + t * 20))

    chosen = _select_dce_phase_files(filenames, positions, times, phase_fraction=0.5)

    # Each position resolves its OWN middle phase (index 8 for both a
    # 17-repeat and an 18-repeat position under round(0.5 * (n-1))), rather
    # than a single global index that would only exist for some positions.
    assert chosen == ["p0t8", "p1t8", "p2t8"]


def test_select_dce_phase_files_uneven_grid_raises():
    from truemargin.io_utils import _select_dce_phase_files

    # position "z0" repeated twice, "z1" repeated three times -- not a clean grid.
    filenames = ["a", "b", "c", "d", "e"]
    positions = ["z0", "z0", "z1", "z1", "z1"]
    times = ["1", "2", "1", "2", "3"]

    with pytest.raises(ValueError):
        _select_dce_phase_files(filenames, positions, times)


def test_select_dce_phase_files_single_phase_is_noop():
    from truemargin.io_utils import _select_dce_phase_files

    # Already single-phase (like aaa0071/aaa0072's DCE series) -- every
    # position appears exactly once, nothing should be dropped.
    filenames = ["s0", "s1", "s2"]
    positions = ["0\\0\\0.0", "0\\0\\1.0", "0\\0\\2.0"]
    times = ["100000", "100000", "100000"]

    chosen = _select_dce_phase_files(filenames, positions, times)
    assert sorted(chosen) == sorted(filenames)


def test_crop_to_mask_bbox_clamps_padding_at_volume_edge():
    # Mask touching the volume boundary -- padding must clamp to the array
    # bounds rather than producing a negative/out-of-range crop index.
    shape = (6, 6, 6)
    fixed = np.arange(np.prod(shape)).reshape(shape).astype(float)
    moving = fixed.copy()
    mask = np.zeros(shape, dtype=np.uint8)
    mask[0, 0, 0] = 1  # right at the corner
    points_idx = np.array([[0, 0, 0]])

    fixed_crop, _, points_crop = io_utils.crop_to_mask_bbox(fixed, moving, mask, points_idx, pad=10)

    assert fixed_crop.shape[0] <= shape[0]
    assert (points_crop >= 0).all()
    assert fixed_crop[tuple(points_crop[0])] == fixed[0, 0, 0]
