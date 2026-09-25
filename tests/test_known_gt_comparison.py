from __future__ import annotations

import numpy as np

from truemargin import hyperparameter as hyper
from truemargin import known_gt_comparison


def _translation_field(
    shape_zyx: tuple[int, int, int],
    translation_xyz: tuple[float, float, float],
) -> np.ndarray:
    field = np.zeros((3, *shape_zyx), dtype=np.float64)
    for component, value in enumerate(translation_xyz):
        field[component] = value
    return field


def test_direct_comparators_swap_image_roles_for_reverse_ensemble(monkeypatch) -> None:
    shape = (9, 10, 12)
    fixed = np.ones(shape, dtype=np.float64)
    moving = np.full(shape, 2.0, dtype=np.float64)
    forward = np.zeros((3, *shape), dtype=np.float64)
    reverse_field = np.zeros_like(forward)
    landmarks = np.asarray([[4, 4, 4], [5, 5, 5]], dtype=np.int64)
    calls: list[tuple[np.ndarray, np.ndarray]] = []

    def fake_reverse(fixed_arg, moving_arg, **kwargs):
        calls.append((fixed_arg, moving_arg))
        return hyper.HyperparameterEnsembleResult(
            complete=True,
            u_mean=reverse_field,
            sigma=np.zeros(shape, dtype=np.float64),
            member_reasons=("ok",) * len(hyper.CONFIGS),
            member_mean_displacement_mm=np.zeros(len(hyper.CONFIGS)),
        )

    monkeypatch.setattr(known_gt_comparison.hyper, "run_hyperparameter_ensemble", fake_reverse)

    result = known_gt_comparison.run_direct_comparators(
        fixed=fixed,
        moving=moving,
        forward_u_mean=forward,
        idx_zyx=landmarks,
        spacing=(1.0, 1.0, 1.0),
        crop_diagonal_mm=100.0,
    )

    assert len(calls) == 1
    np.testing.assert_array_equal(calls[0][0], moving)
    np.testing.assert_array_equal(calls[0][1], fixed)
    assert result.reverse_complete is True
    assert result.ice_failure_reason is None
    np.testing.assert_allclose(result.ice, 0.0)


def test_reverse_failure_does_not_invalidate_residual_or_jacobian(monkeypatch) -> None:
    shape = (9, 10, 12)
    fixed = np.zeros(shape, dtype=np.float64)
    moving = np.zeros(shape, dtype=np.float64)
    forward = np.zeros((3, *shape), dtype=np.float64)
    landmarks = np.asarray([[4, 4, 4], [5, 5, 5]], dtype=np.int64)

    def fake_reverse(fixed_arg, moving_arg, **kwargs):
        return hyper.HyperparameterEnsembleResult(
            complete=False,
            u_mean=None,
            sigma=None,
            member_reasons=("ok",) * 8 + ("deliberate_failure",),
            member_mean_displacement_mm=np.zeros(len(hyper.CONFIGS)),
        )

    monkeypatch.setattr(known_gt_comparison.hyper, "run_hyperparameter_ensemble", fake_reverse)

    result = known_gt_comparison.run_direct_comparators(
        fixed=fixed,
        moving=moving,
        forward_u_mean=forward,
        idx_zyx=landmarks,
        spacing=(1.0, 1.0, 1.0),
        crop_diagonal_mm=100.0,
    )

    assert result.reverse_complete is False
    assert result.ice is None
    assert result.ice_failure_reason == "reverse_ensemble_incomplete:1/9"
    assert result.residual_failure_reason is None
    assert result.jacdev_failure_reason is None
    np.testing.assert_allclose(result.residual, 0.0)
    np.testing.assert_allclose(result.jacdev, 0.0)


def test_direct_comparator_ice_uses_forward_and_reverse_means(monkeypatch) -> None:
    shape = (9, 10, 12)
    fixed = np.zeros(shape, dtype=np.float64)
    moving = np.zeros(shape, dtype=np.float64)
    forward = _translation_field(shape, (1.0, 0.0, 0.0))
    reverse = _translation_field(shape, (-0.25, 0.0, 0.0))
    landmarks = np.asarray([[4, 4, 4], [5, 5, 6]], dtype=np.int64)

    def fake_reverse(fixed_arg, moving_arg, **kwargs):
        return hyper.HyperparameterEnsembleResult(
            complete=True,
            u_mean=reverse,
            sigma=np.zeros(shape, dtype=np.float64),
            member_reasons=("ok",) * 9,
            member_mean_displacement_mm=np.zeros(9),
        )

    monkeypatch.setattr(known_gt_comparison.hyper, "run_hyperparameter_ensemble", fake_reverse)

    result = known_gt_comparison.run_direct_comparators(
        fixed=fixed,
        moving=moving,
        forward_u_mean=forward,
        idx_zyx=landmarks,
        spacing=(1.0, 1.0, 1.0),
        crop_diagonal_mm=100.0,
    )

    np.testing.assert_allclose(result.ice, 0.75)


def test_score_case_metrics_uses_higher_score_as_more_suspected_error() -> None:
    error = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    score = error.copy()

    metrics = known_gt_comparison.score_case_metrics(score, error)

    assert metrics["spearman_known_error"] == 1.0
    assert metrics["rank_degenerate"] is False
    assert metrics["quartile_known_error_delta_mm"] > 0.0
    assert metrics["blind_spot_rate"] == 0.0


def test_anatomy_summary_uses_method_specific_validity() -> None:
    patients = [f"p{i}" for i in range(10)]
    rows: list[dict[str, object]] = []
    for patient_index, patient in enumerate(patients):
        valid_count = 2 if patient_index < 8 else 1
        for replicate in range(3):
            valid = replicate < valid_count
            rows.append(
                {
                    "patient": patient,
                    "ice_valid": valid,
                    "spearman_ice_known_error": 0.25 if valid else float("nan"),
                    "ice_rank_degenerate": False,
                }
            )

    summary = known_gt_comparison.anatomy_summary(
        rows,
        patients=patients,
        method="ice",
        min_complete_cases=2,
    )

    assert sum(bool(row["assessable"]) for row in summary) == 8
    assert all(row["valid_cases"] == 2 for row in summary[:8])
    assert all(row["valid_cases"] == 1 for row in summary[8:])
