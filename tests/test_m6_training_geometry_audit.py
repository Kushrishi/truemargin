"""Pure tests for the M6 training geometry/eligibility audit."""

from __future__ import annotations

import io
import runpy
import zipfile
from pathlib import Path

import pytest
import SimpleITK as sitk

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_m6_training_geometry.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH), run_name="m6_training_geometry_test")


def _fn(name: str):
    return SCRIPT[name]


def _manifest(uids: list[str]) -> bytes:
    return (
        "\n".join(
            [
                "manifestVersion=3.0",
                "ListOfSeriesToDownload=",
                *uids,
            ]
        )
        + "\n"
    ).encode()


def _label_zip(patient_ids: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for patient_id in patient_ids:
            archive.writestr(f"Training/{patient_id}.nrrd", b"synthetic")
    return buffer.getvalue()


def _image(size=(10, 10, 10), origin=(0.0, 0.0, 0.0)) -> sitk.Image:
    image = sitk.Image(size, sitk.sitkFloat32)
    image.SetSpacing((1.0, 1.0, 1.0))
    image.SetOrigin(origin)
    return image


def _label(
    size=(10, 10, 4),
    origin=(0.0, 0.0, 3.0),
    foreground_index=(5, 5, 1),
) -> sitk.Image:
    label = sitk.Image(size, sitk.sitkUInt8)
    label.SetSpacing((1.0, 1.0, 1.0))
    label.SetOrigin(origin)
    label[foreground_index] = 1
    return label


def test_manifest_parser_requires_exact_60_unique_uids():
    parse = _fn("parse_manifest_series_uids")
    uids = [f"1.2.840.{index}" for index in range(60)]
    assert parse(_manifest(uids)) == uids


def test_manifest_parser_rejects_duplicate_uid():
    parse = _fn("parse_manifest_series_uids")
    uids = [f"1.2.840.{index}" for index in range(59)] + ["1.2.840.0"]
    try:
        parse(_manifest(uids))
    except RuntimeError as exc:
        assert "invalid or duplicate" in str(exc)
    else:
        raise AssertionError("duplicate UID should fail")


def test_label_zip_requires_exact_training_namespace_and_count():
    index = _fn("label_members")
    patient_ids = [f"Prostate3T-01-{index_:04d}" for index_ in range(30)] + [
        f"ProstateDx-01-{index_:04d}" for index_ in range(30)
    ]
    assert set(index(_label_zip(patient_ids))) == set(patient_ids)


def test_dimension_mismatch_is_not_automatic_exclusion_when_physically_contained():
    assess = _fn("assess_geometry")
    result = assess("ProstateDx-01-0055", _image(), _label())
    assert result["array_size_equal"] is False
    assert result["known_0055_dimension_mismatch"] is True
    assert result["criteria"]["foreground_physically_contained"] is True
    assert result["eligible"] is True


def test_out_of_domain_foreground_blocks_eligibility():
    assess = _fn("assess_geometry")
    label = _label(origin=(0.0, 0.0, 10.0), foreground_index=(5, 5, 1))
    result = assess("ProstateDx-01-0055", _image(), label)
    assert result["foreground"]["out_of_domain_foreground_voxels"] == 1
    assert result["eligible"] is False


def test_unknown_label_value_blocks_eligibility():
    assess = _fn("assess_geometry")
    label = _label()
    label[5, 5, 1] = 7
    result = assess("ProstateDx-01-0055", _image(), label)
    assert result["criteria"]["label_values_allowed"] is False
    assert result["eligible"] is False


@pytest.mark.parametrize("value", [-0.5, 0.5, 1.5, 2.5])
def test_fractional_label_values_are_not_truncated(value):
    label = sitk.Cast(_label(), sitk.sitkFloat32)
    label[5, 5, 1] = value
    result = _fn("assess_geometry")("ProstateDx-01-0055", _image(), label)
    assert result["criteria"]["label_values_allowed"] is False
    assert result["criteria"]["resampled_values_allowed"] is False
    assert value in result["foreground"]["label_values"]
    assert value in result["resampled_label_values"]
    assert result["eligible"] is False


@pytest.mark.parametrize("value", [1.0, 2.0])
def test_integral_float_label_values_remain_eligible(value):
    label = sitk.Cast(_label(), sitk.sitkFloat32)
    label[5, 5, 1] = value
    result = _fn("assess_geometry")("ProstateDx-01-0055", _image(), label)
    assert result["eligible"] is True


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_label_values_fail_with_clear_error(value):
    label = sitk.Cast(_label(), sitk.sitkFloat32)
    label[5, 5, 1] = value
    with pytest.raises(RuntimeError, match="Label values must be finite"):
        _fn("assess_geometry")("ProstateDx-01-0055", _image(), label)
