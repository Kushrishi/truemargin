"""External LungCT training-data preflight tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from truemargin.external_lung import discover_training_pairs, inspect_pair, preflight_training


def _write_image(
    path: Path,
    *,
    value: float,
    spacing: tuple[float, float, float] = (1.75, 1.25, 1.75),
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    import SimpleITK as sitk

    array = np.full((5, 6, 7), value, dtype=np.float32)
    image = sitk.GetImageFromArray(array)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)
    sitk.WriteImage(image, str(path))


def _dataset(tmp_path: Path, cases: tuple[str, ...] = ("001", "002")) -> Path:
    root = tmp_path / "lungct"
    scans = root / "scans"
    masks = root / "lungMasks"
    keypoints = root / "keypoints"
    scans.mkdir(parents=True)
    masks.mkdir()
    keypoints.mkdir()

    for case_id in cases:
        _write_image(scans / f"case_{case_id}_exp.nii.gz", value=-800.0)
        _write_image(scans / f"case_{case_id}_insp.nii.gz", value=-700.0)
        _write_image(masks / f"case_{case_id}_exp.nii.gz", value=1.0)
        _write_image(masks / f"case_{case_id}_insp.nii.gz", value=1.0)

    (keypoints / "case_001.csv").write_text("THIS IS NOT A LANDMARK FILE\n", encoding="utf-8")
    return root


def test_discovers_expiration_as_fixed_and_inspiration_as_moving(tmp_path):
    root = _dataset(tmp_path)
    pairs = discover_training_pairs(root)
    assert [pair.case_id for pair in pairs] == ["001", "002"]
    assert pairs[0].fixed_path.name == "case_001_exp.nii.gz"
    assert pairs[0].moving_path.name == "case_001_insp.nii.gz"
    assert pairs[0].fixed_mask_path is not None
    assert pairs[0].moving_mask_path is not None


def test_preflight_preserves_geometry_and_ignores_keypoints(tmp_path):
    root = _dataset(tmp_path, ("001",))
    rows = preflight_training(root, expected_pairs=1)
    row = rows[0]
    assert row.size_xyz == (7, 6, 5)
    assert row.shape_zyx == (5, 6, 7)
    assert row.spacing_xyz == pytest.approx((1.75, 1.25, 1.75))
    expected = np.linalg.norm(np.array([6 * 1.75, 5 * 1.25, 4 * 1.75]))
    assert row.diagonal_mm == pytest.approx(float(expected))
    assert row.fixed_min == pytest.approx(-800.0)
    assert row.moving_max == pytest.approx(-700.0)


def test_rejects_incomplete_pair(tmp_path):
    root = _dataset(tmp_path, ("001",))
    (root / "scans/case_001_insp.nii.gz").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        discover_training_pairs(root)


def test_rejects_mismatched_spacing_before_registration(tmp_path):
    root = _dataset(tmp_path, ("001",))
    _write_image(
        root / "scans/case_001_insp.nii.gz",
        value=-700.0,
        spacing=(1.5, 1.25, 1.75),
    )
    pair = discover_training_pairs(root)[0]
    with pytest.raises(ValueError, match="spacing differs"):
        inspect_pair(pair)


def test_rejects_mismatched_origin_before_registration(tmp_path):
    root = _dataset(tmp_path, ("001",))
    _write_image(
        root / "scans/case_001_insp.nii.gz",
        value=-700.0,
        origin=(1.0, 0.0, 0.0),
    )
    pair = discover_training_pairs(root)[0]
    with pytest.raises(ValueError, match="origins differ"):
        inspect_pair(pair)


def test_expected_pair_count_is_enforced(tmp_path):
    root = _dataset(tmp_path, ("001",))
    with pytest.raises(ValueError, match="expected 20 complete pairs"):
        preflight_training(root)
