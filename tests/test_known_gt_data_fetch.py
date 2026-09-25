from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_fetcher():
    path = Path(__file__).parents[1] / "scripts" / "fetch_known_gt_inputs.py"
    spec = importlib.util.spec_from_file_location("fetch_known_gt_inputs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_series_suffixes_match_known_gt_runner() -> None:
    fetcher = _load_fetcher()

    runner_path = Path(__file__).parents[1] / "scripts" / "19_hyperparameter_known_gt_validation.py"
    spec = importlib.util.spec_from_file_location("known_gt_runner_for_data_test", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    assert {
        patient: values["t2_series"] for patient, values in runner.HELD_OUT_CASES.items()
    } == fetcher.FROZEN_T2_SERIES_SUFFIXES


def test_series_resolution_requires_unique_frozen_uid_suffix_and_t2_identity() -> None:
    fetcher = _load_fetcher()
    rows = [
        {
            "PatientID": "aaa0044",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
            "ProtocolName": "T2",
        },
        {
            "PatientID": "aaa0044",
            "SeriesInstanceUID": "1.2.3.99999",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "DCE",
            "ProtocolName": "DCE",
        },
    ]

    selected = fetcher.resolve_frozen_series(rows, patient="aaa0044", suffix="13614")

    assert selected["SeriesInstanceUID"] == "1.2.3.13614"


def test_series_resolution_rejects_ambiguity_and_non_t2() -> None:
    fetcher = _load_fetcher()
    ambiguous = [
        {
            "PatientID": "aaa0044",
            "SeriesInstanceUID": f"1.2.{prefix}.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
        }
        for prefix in (1, 2)
    ]
    with pytest.raises(RuntimeError, match="resolved to 2 public series"):
        fetcher.resolve_frozen_series(ambiguous, patient="aaa0044", suffix="13614")

    non_t2 = [
        {
            "PatientID": "aaa0044",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "DCE",
            "ProtocolName": "DCE",
        }
    ]
    with pytest.raises(RuntimeError, match="not described as T2"):
        fetcher.resolve_frozen_series(non_t2, patient="aaa0044", suffix="13614")
