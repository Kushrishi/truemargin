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


def test_full_series_identity_translates_every_legacy_folder() -> None:
    fetcher = _load_fetcher()
    identities = fetcher.load_frozen_series_identity()

    assert set(identities) == set(fetcher.FROZEN_T2_SERIES_SUFFIXES)
    for patient, suffix in fetcher.FROZEN_T2_SERIES_SUFFIXES.items():
        identity = identities[patient]
        assert identity["legacy_folder"] == suffix
        assert identity["series_uid"].endswith(suffix)
        assert identity["series_description"] == "T2 AXIAL SM FOV"
        assert int(identity["instance_count"]) > 0


def test_idc_filters_pin_collection_patient_and_modality() -> None:
    fetcher = _load_fetcher()

    assert fetcher._idc_filters("aaa0044") == {
        "terms": {
            "collection_id": ["prostate_fused_mri_pathology"],
            "PatientID": ["aaa0044"],
            "Modality": ["MR"],
        }
    }


def _identity() -> dict[str, object]:
    return {
        "legacy_folder": "13614",
        "study_uid": "1.2.3",
        "series_uid": "1.2.3.9876543213614",
        "series_description": "T2 AXIAL SM FOV",
        "instance_count": 30,
    }


def test_series_resolution_requires_exact_full_uid_and_metadata_identity() -> None:
    fetcher = _load_fetcher()
    rows = [
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.9876543213614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL SM FOV",
            "instanceCount": 30,
        },
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.1111111113614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL PELVIS",
            "instanceCount": 40,
        },
    ]

    selected = fetcher.resolve_frozen_series(rows, patient="aaa0044", identity=_identity())

    assert selected["SeriesInstanceUID"] == "1.2.3.9876543213614"


def test_series_resolution_rejects_missing_or_duplicate_full_uid() -> None:
    fetcher = _load_fetcher()
    with pytest.raises(RuntimeError, match="resolved to 0 public series"):
        fetcher.resolve_frozen_series([], patient="aaa0044", identity=_identity())

    duplicate = [
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.9876543213614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL SM FOV",
            "instanceCount": 30,
        }
        for _ in range(2)
    ]
    with pytest.raises(RuntimeError, match="resolved to 2 public series"):
        fetcher.resolve_frozen_series(duplicate, patient="aaa0044", identity=_identity())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("StudyInstanceUID", "9.9.9", "StudyInstanceUID drift"),
        ("SeriesDescription", "T2 AXIAL PELVIS", "SeriesDescription drift"),
        ("instanceCount", 29, "instance-count drift"),
    ],
)
def test_series_resolution_rejects_metadata_drift(field, value, message) -> None:
    fetcher = _load_fetcher()
    row = {
        "collection_id": "prostate_fused_mri_pathology",
        "PatientID": "aaa0044",
        "Modality": "MR",
        "SeriesInstanceUID": "1.2.3.9876543213614",
        "StudyInstanceUID": "1.2.3",
        "SeriesDescription": "T2 AXIAL SM FOV",
        "instanceCount": 30,
    }
    row[field] = value

    with pytest.raises(RuntimeError, match=message):
        fetcher.resolve_frozen_series([row], patient="aaa0044", identity=_identity())


def test_series_resolution_ignores_rows_outside_frozen_collection_or_modality() -> None:
    fetcher = _load_fetcher()
    rows = [
        {
            "collection_id": "other_collection",
            "PatientID": "aaa0044",
            "Modality": "MR",
            "SeriesInstanceUID": "1.2.3.9876543213614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL SM FOV",
            "instanceCount": 30,
        },
        {
            "collection_id": "prostate_fused_mri_pathology",
            "PatientID": "aaa0044",
            "Modality": "CT",
            "SeriesInstanceUID": "1.2.3.9876543213614",
            "StudyInstanceUID": "1.2.3",
            "SeriesDescription": "T2 AXIAL SM FOV",
            "instanceCount": 30,
        },
    ]

    with pytest.raises(RuntimeError, match="resolved to 0 public series"):
        fetcher.resolve_frozen_series(rows, patient="aaa0044", identity=_identity())


def test_idc_manifest_download_command_uses_required_manifest_option(tmp_path: Path) -> None:
    fetcher = _load_fetcher()
    manifest = tmp_path / "manifest.s5cmd"
    download_root = tmp_path / "download"

    assert fetcher._idc_download_command(manifest, download_root) == [
        "idc",
        "download-from-manifest",
        "--manifest-file",
        str(manifest),
        "--download-dir",
        str(download_root),
    ]


def test_patient_subset_defaults_to_full_frozen_cohort() -> None:
    fetcher = _load_fetcher()

    assert fetcher._normalize_patients(None) == tuple(fetcher.FROZEN_T2_SERIES_SUFFIXES)


def test_patient_subset_accepts_exact_unique_frozen_patients() -> None:
    fetcher = _load_fetcher()

    assert fetcher._normalize_patients(["aaa0072"]) == ("aaa0072",)
    assert fetcher._normalize_patients(["aaa0044", "aaa0087"]) == (
        "aaa0044",
        "aaa0087",
    )


@pytest.mark.parametrize(
    ("patients", "message"),
    [
        ([], "At least one patient"),
        (["aaa0044", "aaa0044"], "must be unique"),
        (["not-a-frozen-patient"], "Unknown frozen patient"),
    ],
)
def test_patient_subset_rejects_invalid_requests(patients, message) -> None:
    fetcher = _load_fetcher()

    with pytest.raises(ValueError, match=message):
        fetcher._normalize_patients(patients)
