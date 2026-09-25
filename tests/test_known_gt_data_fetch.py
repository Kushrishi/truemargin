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


def test_idc_filters_pin_collection_patient_and_modality() -> None:
    fetcher = _load_fetcher()

    assert fetcher._idc_filters("aaa0044") == {
        "terms": {
            "collection_id": ["prostate_fused_mri_pathology"],
            "PatientID": ["aaa0044"],
            "Modality": ["MR"],
        }
    }


def test_series_resolution_requires_unique_frozen_uid_component_and_t2_identity() -> None:
    fetcher = _load_fetcher()
    rows = [
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
        },
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.99999",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "DCE",
        },
    ]

    selected = fetcher.resolve_frozen_series(rows, patient="aaa0044", suffix="13614")

    assert selected["SeriesInstanceUID"] == "1.2.3.13614"


def test_series_resolution_rejects_ambiguous_non_t2_and_non_exact_suffix() -> None:
    fetcher = _load_fetcher()
    ambiguous = [
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
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
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "DCE",
        }
    ]
    with pytest.raises(RuntimeError, match="not described as T2"):
        fetcher.resolve_frozen_series(non_t2, patient="aaa0044", suffix="13614")

    suffix_collision = [
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.113614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
        }
    ]
    with pytest.raises(RuntimeError, match="resolved to 0 public series"):
        fetcher.resolve_frozen_series(suffix_collision, patient="aaa0044", suffix="13614")


def test_series_resolution_ignores_rows_outside_frozen_collection_or_modality() -> None:
    fetcher = _load_fetcher()
    rows = [
        {
            "collection_id": "other_collection",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
        },
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "CT",
            "SeriesInstanceUID": "1.2.3.13614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL",
        },
    ]

    with pytest.raises(RuntimeError, match="resolved to 0 public series"):
        fetcher.resolve_frozen_series(rows, patient="aaa0044", suffix="13614")
