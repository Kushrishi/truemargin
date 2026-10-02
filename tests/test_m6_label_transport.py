from __future__ import annotations

import hashlib
import io
import json
import runpy
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def transport():
    scope = runpy.run_path(str(Path(__file__).parents[1] / "scripts/stage_m6_phase_a_labels.py"))
    return scope["stage"].__globals__


def archive_fixture():
    output = io.BytesIO()
    freeze = {"calibration": {}}
    with zipfile.ZipFile(output, "w") as archive:
        for index in range(1, 61):
            patient = f"Prostate3T-01-{index:04d}"
            payload = f"synthetic label {index}".encode()
            archive.writestr(patient + ".nrrd", payload)
            if index <= 30:
                freeze["calibration"][patient] = {
                    "label_sha256": hashlib.sha256(payload).hexdigest()
                }
    return output.getvalue(), freeze


def test_verifies_only_frozen_calibration_label_contents(transport, monkeypatch):
    payload, freeze = archive_fixture()
    monkeypatch.setitem(transport, "ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())
    reads = []
    original = zipfile.ZipFile.read

    def record_read(archive, member, *args, **kwargs):
        reads.append(member.filename)
        return original(archive, member, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", record_read)
    verified = transport["verify_calibration_labels"](payload, freeze)
    assert len(verified) == 30
    assert set(reads) == {patient + ".nrrd" for patient in freeze["calibration"]}


def test_archive_identity_failure_stops_before_label_read(transport):
    payload, freeze = archive_fixture()
    with pytest.raises(ValueError, match="archive SHA-256 mismatch"):
        transport["verify_calibration_labels"](payload, freeze)


def test_label_identity_failure_is_not_retried_from_another_source(
    transport, monkeypatch, tmp_path
):
    payload, freeze = archive_fixture()
    monkeypatch.setitem(transport, "ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())
    freeze["calibration"]["Prostate3T-01-0001"]["label_sha256"] = "bad"
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(freeze))
    calls = []

    def download(url):
        calls.append(url)
        return payload

    monkeypatch.setitem(transport, "download", download)
    with pytest.raises(ValueError, match="label mismatch"):
        transport["stage"](path, tmp_path / "output")
    assert calls == [transport["OFFICIAL_URL"]]
    assert not (tmp_path / "output").exists()


def test_transport_failure_can_use_byte_identical_legacy_fallback(transport, monkeypatch, tmp_path):
    payload, freeze = archive_fixture()
    monkeypatch.setitem(transport, "ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(freeze))

    def download(url):
        if url == transport["OFFICIAL_URL"]:
            raise transport["TransportUnavailable"]("synthetic timeout")
        return payload

    monkeypatch.setitem(transport, "download", download)
    result = transport["stage"](path, tmp_path / "output")
    assert result["source_url"] == transport["LEGACY_URL"]
    assert result["prior_transport_errors"] == ["synthetic timeout"]
    assert (tmp_path / "output/training-labels.zip").read_bytes() == payload
    assert result["registration_performed"] is False
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        transport["stage"](path, tmp_path / "output")
