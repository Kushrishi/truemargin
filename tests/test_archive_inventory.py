"""ZIP metadata inventory must not parse landmark contents."""

import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "inventory_external", Path(__file__).parents[1] / "scripts/inventory_external_archive.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_metadata_only_inventory_and_checksum_guard(tmp_path, monkeypatch):
    path = tmp_path / "training.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("training/scans/case_001_exp.nii.gz", b"fake")
        archive.writestr("training/scans/case_001_insp.nii.gz", b"fake")
        archive.writestr("training/keypoints/sealed.csv", b"DO NOT PARSE")
    digest = hashlib.md5(path.read_bytes()).hexdigest()

    def deny(*args, **kwargs):
        raise AssertionError("no ZIP payload access permitted")

    monkeypatch.setattr(zipfile.ZipFile, "open", deny)
    record = module.inventory(path, digest)
    assert record["complete_pair_ids"] == ["001"]
    assert record["landmarks_accessed"] is False
    with pytest.raises(ValueError, match="MD5 mismatch"):
        module.inventory(path, "0" * 32)


def test_rejects_unsafe_archive_names(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../escape", b"fake")
    with pytest.raises(ValueError, match="unsafe"):
        module.inventory(path, hashlib.md5(path.read_bytes()).hexdigest())
