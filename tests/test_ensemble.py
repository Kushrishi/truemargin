import numpy as np
import pytest

from truemargin import ensemble


def _fake_registration_recorder(calls):
    def fake_registration(fixed, moving, **kwargs):
        calls.append((fixed.copy(), moving.copy(), dict(kwargs)))
        return np.zeros((fixed.ndim, *fixed.shape), dtype=np.float64)

    return fake_registration


def _nonconstant_inputs():
    fixed = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
    moving = (np.arange(24, dtype=np.float64).reshape(2, 3, 4) * 3.0) + 17.0
    return fixed, moving


def test_absolute_intensity_mode_reproduces_historical_draw_semantics(monkeypatch) -> None:
    fixed, moving = _nonconstant_inputs()
    calls = []
    monkeypatch.setattr(
        ensemble, "baseline_bspline_registration", _fake_registration_recorder(calls)
    )

    ensemble.ensemble_uncertainty(
        fixed,
        moving,
        n=3,
        perturbation="absolute_intensity",
        perturbation_scale=0.02,
        seed=7,
        mesh_size=3,
        max_iterations=15,
        spacing=(0.5, 0.5, 3.0),
    )

    expected_rng = np.random.default_rng(7)
    assert len(calls) == 3
    for fixed_seen, moving_seen, kwargs in calls:
        expected_fixed = fixed + expected_rng.normal(0.0, 0.02, fixed.shape)
        expected_moving = moving + expected_rng.normal(0.0, 0.02, moving.shape)
        np.testing.assert_array_equal(fixed_seen, expected_fixed)
        np.testing.assert_array_equal(moving_seen, expected_moving)
        assert kwargs["mesh_size"] == 3
        assert kwargs["max_iterations"] == 15
        assert kwargs["spacing"] == (0.5, 0.5, 3.0)
        assert kwargs["center_first"] is False


def test_relative_std_perturbation_is_scale_equivariant(monkeypatch) -> None:
    fixed, moving = _nonconstant_inputs()

    calls_original = []
    monkeypatch.setattr(
        ensemble,
        "baseline_bspline_registration",
        _fake_registration_recorder(calls_original),
    )
    ensemble.ensemble_uncertainty(
        fixed,
        moving,
        n=3,
        perturbation="relative_std",
        perturbation_scale=0.05,
        seed=11,
    )

    fixed_factor = 10.0
    moving_factor = 4.0
    calls_scaled = []
    monkeypatch.setattr(
        ensemble,
        "baseline_bspline_registration",
        _fake_registration_recorder(calls_scaled),
    )
    ensemble.ensemble_uncertainty(
        fixed * fixed_factor,
        moving * moving_factor,
        n=3,
        perturbation="relative_std",
        perturbation_scale=0.05,
        seed=11,
    )

    for (fixed_a, moving_a, _), (fixed_b, moving_b, _) in zip(
        calls_original, calls_scaled, strict=True
    ):
        np.testing.assert_allclose(
            fixed_a - fixed,
            (fixed_b - fixed * fixed_factor) / fixed_factor,
            rtol=1e-12,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            moving_a - moving,
            (moving_b - moving * moving_factor) / moving_factor,
            rtol=1e-12,
            atol=1e-12,
        )


def test_member_sequence_is_nested_across_ensemble_sizes(monkeypatch) -> None:
    fixed, moving = _nonconstant_inputs()

    calls_5 = []
    monkeypatch.setattr(
        ensemble, "baseline_bspline_registration", _fake_registration_recorder(calls_5)
    )
    ensemble.ensemble_uncertainty(
        fixed,
        moving,
        n=5,
        perturbation="relative_std",
        perturbation_scale=0.02,
        seed=19,
    )

    calls_10 = []
    monkeypatch.setattr(
        ensemble, "baseline_bspline_registration", _fake_registration_recorder(calls_10)
    )
    ensemble.ensemble_uncertainty(
        fixed,
        moving,
        n=10,
        perturbation="relative_std",
        perturbation_scale=0.02,
        seed=19,
    )

    for call_5, call_10 in zip(calls_5, calls_10[:5], strict=True):
        np.testing.assert_array_equal(call_5[0], call_10[0])
        np.testing.assert_array_equal(call_5[1], call_10[1])


def test_relative_std_allows_zero_alpha_repeatability_floor(monkeypatch) -> None:
    fixed, moving = _nonconstant_inputs()
    calls = []
    monkeypatch.setattr(
        ensemble, "baseline_bspline_registration", _fake_registration_recorder(calls)
    )

    ensemble.ensemble_uncertainty(
        fixed,
        moving,
        n=2,
        perturbation="relative_std",
        perturbation_scale=0.0,
        seed=0,
    )

    assert len(calls) == 2
    for fixed_seen, moving_seen, _ in calls:
        np.testing.assert_array_equal(fixed_seen, fixed)
        np.testing.assert_array_equal(moving_seen, moving)


@pytest.mark.parametrize("which", ["fixed", "moving"])
def test_relative_std_rejects_zero_variance_image(monkeypatch, which: str) -> None:
    fixed, moving = _nonconstant_inputs()
    if which == "fixed":
        fixed = np.ones_like(fixed)
    else:
        moving = np.ones_like(moving)

    monkeypatch.setattr(ensemble, "baseline_bspline_registration", _fake_registration_recorder([]))
    with pytest.raises(ValueError, match="non-zero .* standard deviation"):
        ensemble.ensemble_uncertainty(
            fixed,
            moving,
            n=2,
            perturbation="relative_std",
            perturbation_scale=0.02,
        )


@pytest.mark.parametrize("scale", [-0.01, np.inf, np.nan])
def test_invalid_perturbation_scale_is_rejected(scale: float) -> None:
    fixed, moving = _nonconstant_inputs()
    with pytest.raises(ValueError, match="finite and non-negative"):
        ensemble.ensemble_uncertainty(
            fixed,
            moving,
            n=2,
            perturbation="relative_std",
            perturbation_scale=scale,
        )


def test_unknown_perturbation_strategy_is_rejected() -> None:
    fixed, moving = _nonconstant_inputs()
    with pytest.raises(ValueError, match="perturbation must be"):
        ensemble.ensemble_uncertainty(
            fixed,
            moving,
            n=2,
            perturbation="not-a-method",  # type: ignore[arg-type]
            perturbation_scale=0.02,
        )


def test_ensemble_size_must_allow_spread_estimation() -> None:
    fixed, moving = _nonconstant_inputs()
    with pytest.raises(ValueError, match="n must be at least 2"):
        ensemble.ensemble_uncertainty(fixed, moving, n=1)


def test_perturbed_inputs_support_single_member_diagnostics() -> None:
    fixed, moving = _nonconstant_inputs()
    pairs = list(
        ensemble.perturbed_inputs(
            fixed,
            moving,
            n=1,
            perturbation="relative_std",
            perturbation_scale=0.02,
            seed=3,
        )
    )
    assert len(pairs) == 1
    assert pairs[0][0].shape == fixed.shape
    assert pairs[0][1].shape == moving.shape


def test_validate_member_field_accepts_physical_field() -> None:
    field = np.ones((3, 2, 2, 2), dtype=np.float64)
    assert (
        ensemble.validate_member_field(
            field,
            expected_shape=(3, 2, 2, 2),
            crop_diagonal_mm=10.0,
        )
        is None
    )


def test_validate_member_field_rejects_shape_mismatch() -> None:
    field = np.zeros((3, 2, 2, 2), dtype=np.float64)
    reason = ensemble.validate_member_field(
        field,
        expected_shape=(3, 3, 2, 2),
        crop_diagonal_mm=10.0,
    )
    assert reason is not None and reason.startswith("shape_mismatch:")


def test_validate_member_field_rejects_nonfinite_values() -> None:
    field = np.zeros((3, 2, 2, 2), dtype=np.float64)
    field[0, 0, 0, 0] = np.nan
    assert (
        ensemble.validate_member_field(
            field,
            expected_shape=field.shape,
            crop_diagonal_mm=10.0,
        )
        == "nonfinite_displacement"
    )


def test_validate_member_field_rejects_runaway_mean_displacement() -> None:
    field = np.full((3, 2, 2, 2), 10.0, dtype=np.float64)
    reason = ensemble.validate_member_field(
        field,
        expected_shape=field.shape,
        crop_diagonal_mm=5.0,
    )
    assert reason is not None and reason.startswith("mean_displacement_exceeds_crop_diagonal:")


def test_summarize_fields_matches_historical_rms_definition() -> None:
    first = np.zeros((3, 1, 1, 1), dtype=np.float64)
    second = np.full((3, 1, 1, 1), 2.0, dtype=np.float64)
    u_mean, sigma = ensemble.summarize_fields([first, second])

    np.testing.assert_array_equal(u_mean, np.ones_like(first))
    np.testing.assert_allclose(sigma, np.ones((1, 1, 1)))
