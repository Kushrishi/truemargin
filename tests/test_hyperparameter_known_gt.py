from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

from truemargin import hyperparameter as hyper


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1] / "scripts" / "19_hyperparameter_known_gt_validation.py"
    )
    spec = importlib.util.spec_from_file_location("hyperparameter_known_gt_runner", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_promoted_hyperparameter_grid_is_exact() -> None:
    assert hyper.MESH_SIZE == 3
    assert hyper.MAX_ITERATIONS == 15
    assert hyper.CENTER_FIRST is False
    assert hyper.METRIC_BINS == (32, 50, 64)
    assert hyper.GRADIENT_TOLERANCES == (1e-4, 1e-5, 1e-6)
    assert hyper.CONFIGS == (
        (32, 1e-4),
        (32, 1e-5),
        (32, 1e-6),
        (50, 1e-4),
        (50, 1e-5),
        (50, 1e-6),
        (64, 1e-4),
        (64, 1e-5),
        (64, 1e-6),
    )


def test_promoted_helper_requires_all_nine_members(monkeypatch) -> None:
    calls: list[tuple[int, float]] = []

    def fake_registration(fixed, moving, **kwargs):
        calls.append((kwargs["metric_bins"], kwargs["gradient_convergence_tolerance"]))
        return np.zeros((3, *fixed.shape), dtype=np.float64)

    monkeypatch.setattr(hyper.reg, "baseline_bspline_registration", fake_registration)
    fixed = np.zeros((5, 6, 7), dtype=np.float32)
    result = hyper.run_hyperparameter_ensemble(
        fixed,
        fixed.copy(),
        spacing=(1.0, 1.0, 1.0),
        crop_diagonal_mm=100.0,
    )

    assert result.complete is True
    assert calls == list(hyper.CONFIGS)
    assert result.u_mean is not None
    assert result.sigma is not None
    assert result.u_mean.shape == (3, 5, 6, 7)
    assert result.sigma.shape == (5, 6, 7)
    assert result.member_reasons == ("ok",) * 9


def test_one_failed_hyperparameter_member_invalidates_case(monkeypatch) -> None:
    failing = hyper.CONFIGS[4]

    def fake_registration(fixed, moving, **kwargs):
        config = (
            kwargs["metric_bins"],
            kwargs["gradient_convergence_tolerance"],
        )
        if config == failing:
            raise RuntimeError("deliberate test failure")
        return np.zeros((3, *fixed.shape), dtype=np.float64)

    monkeypatch.setattr(hyper.reg, "baseline_bspline_registration", fake_registration)
    fixed = np.zeros((5, 6, 7), dtype=np.float32)
    result = hyper.run_hyperparameter_ensemble(
        fixed,
        fixed.copy(),
        spacing=(1.0, 1.0, 1.0),
        crop_diagonal_mm=100.0,
    )

    assert result.complete is False
    assert result.u_mean is None
    assert result.sigma is None
    assert sum(reason != "ok" for reason in result.member_reasons) == 1
    assert "registration_exception:RuntimeError" in result.member_reasons[4]


def test_synthetic_resample_direction_matches_fixed_to_moving_truth() -> None:
    array = np.broadcast_to(np.arange(9, dtype=np.float32), (5, 6, 9)).copy()
    moving = sitk.GetImageFromArray(array)
    moving.SetSpacing((1.0, 1.0, 1.0))
    transform = sitk.TranslationTransform(3, (2.0, 0.0, 0.0))

    fixed = sitk.Resample(
        moving,
        moving,
        transform,
        sitk.sitkNearestNeighbor,
        -1.0,
    )
    fixed_array = sitk.GetArrayFromImage(fixed)

    assert fixed_array[2, 3, 3] == 5.0
    point = fixed.TransformIndexToPhysicalPoint((3, 3, 2))
    transformed = transform.TransformPoint(point)
    true_displacement = np.asarray(transformed) - np.asarray(point)
    np.testing.assert_allclose(true_displacement, (2.0, 0.0, 0.0))


def test_held_out_cohort_and_seed_schedule_are_frozen() -> None:
    runner = _load_runner()
    assert runner.PROTOCOL_MAIN_SHA == "44afb8653c8c90b33a438107481f7be4586b0e68"
    assert runner.PROTOCOL_AMENDMENT_SHA == "d37b5a4a7931fdd3947870ba651b097f712ebdb3"
    assert runner.HELD_OUT_CASES == {
        "aaa0044": {"t2_series": "13614"},
        "aaa0051": {"t2_series": "36207"},
        "aaa0053": {"t2_series": "45314"},
        "aaa0060": {"t2_series": "12400"},
        "aaa0064": {"t2_series": "40733"},
        "aaa0069": {"t2_series": "58343"},
        "aaa0071": {"t2_series": "27783"},
        "aaa0072": {"t2_series": "64767"},
        "aaa0086": {"t2_series": "42255"},
        "aaa0087": {"t2_series": "30095"},
    }
    assert not (set(runner.HELD_OUT_CASES) & runner.PROMOTION_PATIENTS)
    assert runner.N_REPLICATES == 3
    assert [runner.case_seed(0, r) for r in range(3)] == [0, 1, 2]
    assert [runner.case_seed(9, r) for r in range(3)] == [9000, 9001, 9002]
    assert runner.NOISE_SEED_OFFSET == 100_000
    assert runner.LANDMARK_SEED_OFFSET == 200_000


def test_landmarks_are_unique_inside_roi_and_respect_margin() -> None:
    runner = _load_runner()
    mask = np.zeros((30, 40, 50), dtype=np.uint8)
    mask[8:22, 8:32, 8:42] = 1
    points_a = runner.sample_landmarks(mask, seed=123)
    points_b = runner.sample_landmarks(mask, seed=123)

    np.testing.assert_array_equal(points_a, points_b)
    assert points_a.shape == (50, 3)
    assert len(np.unique(points_a, axis=0)) == 50
    assert np.all(points_a >= runner.LANDMARK_MARGIN)
    assert np.all(points_a < np.asarray(mask.shape) - runner.LANDMARK_MARGIN)
    assert np.all(mask[tuple(points_a.T)] == 1)


def test_fixed_roi_mask_uses_fixed_to_moving_transform_direction() -> None:
    runner = _load_runner()
    source = np.zeros((5, 6, 9), dtype=np.float32)
    source_img = runner.make_source_image(source, (1.0, 1.0, 1.0))
    mask = np.zeros_like(source, dtype=np.uint8)
    mask[2, 3, 5] = 1
    transform = sitk.TranslationTransform(3, (2.0, 0.0, 0.0))

    fixed_roi = runner.make_fixed_roi_mask(mask, source_img, transform)

    assert fixed_roi[2, 3, 3]
    assert not fixed_roi[2, 3, 5]


def test_rank_degenerate_case_maps_to_zero() -> None:
    runner = _load_runner()
    rho, degenerate = runner._safe_spearman(
        np.ones(50),
        np.arange(50, dtype=float),
    )
    assert rho == 0.0
    assert degenerate is True


def test_anatomy_and_global_assessability_rules() -> None:
    runner = _load_runner()
    rows = []
    patients = list(runner.HELD_OUT_CASES)
    for patient_index, patient in enumerate(patients):
        n_complete = 2 if patient_index < 8 else 1
        for replicate in range(3):
            complete = replicate < n_complete
            rows.append(
                {
                    "patient": patient,
                    "replicate": replicate,
                    "complete": complete,
                    "spearman_sigma_known_error": (0.25 if complete else float("nan")),
                }
            )

    anatomy = runner.anatomy_rows(rows)
    assert sum(row["assessable"] for row in anatomy) == 8
    assert all(row["complete_cases"] >= 2 for row in anatomy[:8])
    assert all(row["complete_cases"] == 1 for row in anatomy[8:])


def test_exact_sign_test_and_positive_label_on_consistent_anatomy_signal() -> None:
    runner = _load_runner()
    anatomy = [
        {
            "patient": patient,
            "assessable": i < 8,
            "median_case_spearman": 0.25 if i < 8 else float("nan"),
        }
        for i, patient in enumerate(runner.HELD_OUT_CASES)
    ]

    positives, n_anatomies, p_value = runner.exact_positive_sign_test(anatomy)
    assert positives == 8
    assert n_anatomies == 8
    assert p_value <= 0.05
    assert runner.positive_association_label(0.25, p_value) is True
    assert runner.positive_association_label(0.0, p_value) is False
    assert runner.positive_association_label(0.25, 0.051) is False


def test_exact_sign_test_counts_zero_as_nonpositive() -> None:
    runner = _load_runner()
    anatomy = [
        {
            "patient": patient,
            "assessable": i < 8,
            "median_case_spearman": 0.25 if i < 7 else 0.0,
        }
        for i, patient in enumerate(runner.HELD_OUT_CASES)
    ]

    positives, n_anatomies, p_value = runner.exact_positive_sign_test(anatomy)
    assert positives == 7
    assert n_anatomies == 8
    assert p_value <= 0.05


def test_bootstrap_interval_is_deterministic() -> None:
    runner = _load_runner()
    anatomy = [
        {
            "patient": patient,
            "assessable": i < 8,
            "median_case_spearman": 0.1 + 0.05 * i,
        }
        for i, patient in enumerate(runner.HELD_OUT_CASES)
    ]
    first = runner.bootstrap_interval(anatomy, n_bootstraps=200, seed=0)
    second = runner.bootstrap_interval(anatomy, n_bootstraps=200, seed=0)
    assert first == second
    assert first[0] <= first[1]


def test_result_bearing_authorization_pins_reviewed_preflight(tmp_path: Path) -> None:
    runner = _load_runner()
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    preflight = result_dir / "hyperparameter_known_gt_geometry_preflight.json"
    preflight.write_text('{"geometry_preflight":"PASS"}\n', encoding="utf-8")
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()

    request = {
        "schema_version": 1,
        "study": "hyperparameter-known-gt-v1",
        "authorized": True,
        "held_out_anatomies": list(runner.HELD_OUT_CASES),
        "n_replicates": runner.N_REPLICATES,
        "n_estimator_members": len(runner.hyper.CONFIGS),
        "planned_registrations": (
            len(runner.HELD_OUT_CASES) * runner.N_REPLICATES * len(runner.hyper.CONFIGS)
        ),
        "protocol_main_sha": runner.PROTOCOL_MAIN_SHA,
        "protocol_amendment_sha": runner.PROTOCOL_AMENDMENT_SHA,
        "geometry_preflight_record": "results/hyperparameter_known_gt_geometry_preflight.json",
        "geometry_preflight_sha256": digest,
    }
    request_path = tmp_path / "KNOWN_GT_RUN_REQUEST.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")

    verified = runner.verify_result_bearing_authorization(
        str(request_path),
        repo_root=str(tmp_path),
    )
    assert verified["authorized"] is True

    request["authorized"] = False
    request_path.write_text(json.dumps(request), encoding="utf-8")
    with pytest.raises(SystemExit, match="authorization field"):
        runner.verify_result_bearing_authorization(
            str(request_path),
            repo_root=str(tmp_path),
        )
