from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import datetime

import pytest

from truemargin.m6_input_identity import assert_frozen_digest
from truemargin.m6_zip_recovery import recover_frozen_zip

START = datetime(2026, 10, 2, 18, 54, 24)
END = datetime(2026, 10, 2, 18, 54, 30)


def archive(seconds: tuple[int, ...], content: bytes = b"original pixel bytes") -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for i, second in enumerate(seconds):
            info = zipfile.ZipInfo(f"{i}.dcm", date_time=(2026, 10, 2, 18, 54, second))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return out.getvalue()


@pytest.mark.parametrize("seconds", [(26, 26, 26), (26, 26, 28)])
def test_recovery_matches_original_archive_bytes_and_unchanged_guard(seconds):
    original = archive(seconds)
    current = archive((0, 0, 2))
    digest = hashlib.sha256(original).hexdigest()
    recovered, record = recover_frozen_zip(current, digest, start=START, end=END)
    assert recovered == original
    assert record["recovery"] == "exact_frozen_archive_digest"
    assert (
        assert_frozen_digest(recovered, digest, patient_id="calibration", input_kind="dicom_zip")
        == digest
    )


def test_modified_member_bytes_cannot_be_recovered_or_accepted():
    original = archive((26, 26, 28))
    substituted = archive((0, 0, 2), b"different image pixels")
    digest = hashlib.sha256(original).hexdigest()
    with pytest.raises(RuntimeError, match="identity remains unresolved"):
        recover_frozen_zip(substituted, digest, start=START, end=END)
    with pytest.raises(RuntimeError, match="registration remains blocked"):
        assert_frozen_digest(substituted, digest, patient_id="calibration", input_kind="dicom_zip")


def test_exact_input_is_preserved_without_search():
    original = archive((26, 26, 28))
    recovered, record = recover_frozen_zip(
        original, hashlib.sha256(original).hexdigest(), start=START, end=END
    )
    assert recovered == original
    assert record == {"recovery": "already_exact", "attempts": 0}


def test_out_of_window_historical_timestamp_remains_blocked():
    original = archive((10, 10, 10))
    with pytest.raises(RuntimeError, match="identity remains unresolved"):
        recover_frozen_zip(
            archive((0, 0, 2)), hashlib.sha256(original).hexdigest(), start=START, end=END
        )


def test_search_cannot_be_unbounded():
    with pytest.raises(ValueError, match="unbounded"):
        recover_frozen_zip(b"anything", "0" * 64, start=START, end=datetime(2026, 10, 3))
