from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from truemargin.m6_input_identity import assert_frozen_digest


def archive(second: int) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        info = zipfile.ZipInfo("slice.dcm", date_time=(2026, 10, 2, 12, 0, second))
        z.writestr(info, b"identical member bytes")
    return out.getvalue()


def test_exact_frozen_bytes_are_required_even_when_zip_members_match():
    frozen, changed = archive(0), archive(2)
    expected = hashlib.sha256(frozen).hexdigest()
    assert (
        assert_frozen_digest(frozen, expected, patient_id="calibration", input_kind="dicom_zip")
        == expected
    )
    with pytest.raises(RuntimeError, match="registration remains blocked"):
        assert_frozen_digest(changed, expected, patient_id="calibration", input_kind="dicom_zip")


@pytest.mark.parametrize("input_kind", ["dicom_zip", "label"])
def test_input_substitution_is_rejected(input_kind):
    with pytest.raises(RuntimeError, match="identity mismatch"):
        assert_frozen_digest(
            b"substituted",
            hashlib.sha256(b"frozen").hexdigest(),
            patient_id="calibration",
            input_kind=input_kind,
        )


def test_malformed_expected_digest_is_rejected():
    with pytest.raises(ValueError, match="full SHA256"):
        assert_frozen_digest(b"input", "unfrozen", patient_id="calibration", input_kind="label")
