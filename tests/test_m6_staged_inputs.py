"""Staged calibration inputs fail closed before image decoding or computation."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    scope = runpy.run_path(str(REPO / "scripts/m6_phase_a_calibration.py"))
    scope = scope["load_exact_input"].__globals__
    image_bytes = b"frozen archive fixture"
    label_bytes = b"frozen label fixture"
    freeze = tmp_path / "freeze.json"
    freeze.write_text(
        json.dumps(
            {
                "calibration": {
                    "calibration-fixture": {
                        "series_uid": "fixture-series",
                        "dicom_zip_sha256": hashlib.sha256(image_bytes).hexdigest(),
                        "label_sha256": hashlib.sha256(label_bytes).hexdigest(),
                    }
                }
            }
        )
    )
    monkeypatch.setitem(scope, "INPUT_FREEZE_PATH", freeze)
    monkeypatch.setitem(scope["BASE"], "_download", lambda _: b"label archive fixture")
    monkeypatch.setitem(
        scope["BASE"],
        "label_members",
        lambda _: {
            "calibration-fixture": label_bytes,
        },
    )
    monkeypatch.setitem(
        scope["BASE"],
        "download_series",
        lambda _: pytest.fail("staged execution must not download images"),
    )
    monkeypatch.setitem(
        scope,
        "recover_frozen_zip",
        lambda *a, **k: pytest.fail("staged execution must not repair or reinterpret cached bytes"),
    )
    decoded = []

    def read_series(payload, series, root):
        decoded.append((payload, series))
        return "calibration-fixture", "image fixture"

    monkeypatch.setitem(scope["BASE"], "_read_series", read_series)
    monkeypatch.setitem(scope["BASE"], "_read_label", lambda *a: "label fixture")
    cache = tmp_path / "dicom"
    cache.mkdir()
    (cache / "calibration-fixture.zip").write_bytes(image_bytes)
    monkeypatch.setenv("M6_CALIBRATION_DICOM_CACHE", str(cache))
    scope["test_cache"] = cache
    scope["test_decoded"] = decoded
    return scope


def test_exact_staged_bytes_are_used_without_network_or_recovery(runner, tmp_path):
    image, label, image_sha, label_sha = runner["load_exact_input"](
        "calibration-fixture", "fixture-series", tmp_path
    )
    assert (image, label) == ("image fixture", "label fixture")
    assert image_sha == hashlib.sha256(b"frozen archive fixture").hexdigest()
    assert label_sha == hashlib.sha256(b"frozen label fixture").hexdigest()
    assert runner["test_decoded"] == [(b"frozen archive fixture", "fixture-series")]


def test_missing_staged_archive_does_not_fall_back_to_network(runner, tmp_path):
    (runner["test_cache"] / "calibration-fixture.zip").unlink()
    with pytest.raises(FileNotFoundError):
        runner["load_exact_input"]("calibration-fixture", "fixture-series", tmp_path)
    assert runner["test_decoded"] == []


def test_changed_staged_bytes_fail_before_decoding(runner, tmp_path):
    (runner["test_cache"] / "calibration-fixture.zip").write_bytes(b"changed archive")
    with pytest.raises(RuntimeError, match="identity"):
        runner["load_exact_input"]("calibration-fixture", "fixture-series", tmp_path)
    assert runner["test_decoded"] == []


def test_wrong_series_fails_before_decoding(runner, tmp_path):
    with pytest.raises(RuntimeError, match="SeriesInstanceUID mismatch"):
        runner["load_exact_input"]("calibration-fixture", "different-series", tmp_path)
    assert runner["test_decoded"] == []


def test_changed_label_fails_before_image_decoding(runner, monkeypatch, tmp_path):
    monkeypatch.setitem(
        runner["BASE"],
        "label_members",
        lambda _: {
            "calibration-fixture": b"changed label",
        },
    )
    with pytest.raises(RuntimeError, match="identity"):
        runner["load_exact_input"]("calibration-fixture", "fixture-series", tmp_path)
    assert runner["test_decoded"] == []


def test_observed_patient_identity_must_match(runner, monkeypatch, tmp_path):
    monkeypatch.setitem(
        runner["BASE"],
        "_read_series",
        lambda *a: (
            "wrong-patient",
            "image fixture",
        ),
    )
    with pytest.raises(RuntimeError, match="series identity mismatch"):
        runner["load_exact_input"]("calibration-fixture", "fixture-series", tmp_path)
