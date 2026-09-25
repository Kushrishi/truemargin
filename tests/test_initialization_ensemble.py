from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from truemargin import initialization

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "17_initialization_ensemble_sensitivity.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
CASES = SCRIPT["CASES"]
STRENGTHS_MM = SCRIPT["STRENGTHS_MM"]
select_initialization_delta = SCRIPT["select_initialization_delta"]


def test_zero_delta_produces_exact_zero_coefficients() -> None:
    params = initialization.initialization_parameters(
        32,
        delta_mm=0.0,
        patient_index=1,
        member_index=3,
    )
    np.testing.assert_array_equal(params, np.zeros(32))


def test_initialization_offsets_stay_within_frozen_half_range() -> None:
    params = initialization.initialization_parameters(
        256,
        delta_mm=1.0,
        patient_index=2,
        member_index=4,
    )
    assert np.max(np.abs(params)) <= 1.0


def test_initialization_rng_is_deterministic() -> None:
    first = initialization.initialization_parameters(
        64,
        delta_mm=0.5,
        patient_index=3,
        member_index=7,
    )
    second = initialization.initialization_parameters(
        64,
        delta_mm=0.5,
        patient_index=3,
        member_index=7,
    )
    np.testing.assert_array_equal(first, second)


def test_same_patient_member_direction_scales_across_strengths() -> None:
    small = initialization.initialization_parameters(
        128,
        delta_mm=0.5,
        patient_index=0,
        member_index=2,
    )
    large = initialization.initialization_parameters(
        128,
        delta_mm=2.0,
        patient_index=0,
        member_index=2,
    )
    np.testing.assert_allclose(large, 4.0 * small, rtol=0.0, atol=1e-15)


def test_member_generation_is_prefix_nested_for_later_size_study() -> None:
    first_five = [
        initialization.initialization_parameters(
            20,
            delta_mm=1.0,
            patient_index=4,
            member_index=index,
        )
        for index in range(5)
    ]
    first_twenty = [
        initialization.initialization_parameters(
            20,
            delta_mm=1.0,
            patient_index=4,
            member_index=index,
        )
        for index in range(20)
    ]
    for expected, actual in zip(first_five, first_twenty[:5], strict=True):
        np.testing.assert_array_equal(actual, expected)


def test_invalid_initialization_inputs_fail_loudly() -> None:
    with pytest.raises(ValueError, match="n_parameters"):
        initialization.initialization_parameters(
            0,
            delta_mm=1.0,
            patient_index=0,
            member_index=0,
        )
    with pytest.raises(ValueError, match="delta_mm"):
        initialization.initialization_parameters(
            4,
            delta_mm=-0.1,
            patient_index=0,
            member_index=0,
        )
    with pytest.raises(ValueError, match="non-negative"):
        initialization.initialization_parameters(
            4,
            delta_mm=1.0,
            patient_index=-1,
            member_index=0,
        )


def test_initial_parameter_vector_validation_rejects_bad_vectors() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        initialization._validated_initial_parameters(
            np.zeros((2, 2)),
            expected_size=4,
        )
    with pytest.raises(ValueError, match="length"):
        initialization._validated_initial_parameters(
            np.zeros(3),
            expected_size=4,
        )
    with pytest.raises(ValueError, match="finite"):
        initialization._validated_initial_parameters(
            np.array([0.0, 1.0, np.nan, 2.0]),
            expected_size=4,
        )


def test_no_initial_parameters_delegates_to_existing_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = np.ones((3, 2, 2, 2), dtype=np.float64)
    calls: list[dict[str, object]] = []

    def fake_baseline(fixed: np.ndarray, moving: np.ndarray, **kwargs: object) -> np.ndarray:
        calls.append({"fixed": fixed, "moving": moving, **kwargs})
        return sentinel

    monkeypatch.setattr(initialization, "baseline_bspline_registration", fake_baseline)
    fixed = np.zeros((2, 2, 2), dtype=np.float32)
    moving = np.ones((2, 2, 2), dtype=np.float32)

    result = initialization.initialized_bspline_registration(
        fixed,
        moving,
        mesh_size=3,
        max_iterations=15,
        spacing=(0.4, 0.4, 4.0),
        center_first=False,
        initial_parameters=None,
    )

    assert result is sentinel
    assert len(calls) == 1
    assert calls[0]["mesh_size"] == 3
    assert calls[0]["max_iterations"] == 15
    assert calls[0]["spacing"] == (0.4, 0.4, 4.0)
    assert calls[0]["center_first"] is False


def _selection_rows(
    *,
    floor_complete: int = 5,
    candidate_complete: dict[float, int] | None = None,
    non_inert: dict[float, int] | None = None,
) -> list[dict[str, Any]]:
    candidate_complete = candidate_complete or {0.5: 5, 1.0: 5, 2.0: 5}
    non_inert = non_inert or {0.5: 5, 1.0: 5, 2.0: 5}
    patients = list(CASES)
    rows: list[dict[str, Any]] = []

    for delta_mm in STRENGTHS_MM:
        for index, patient in enumerate(patients):
            if delta_mm == 0.0:
                complete = index < floor_complete
                sigma = 0.01
            else:
                complete = index < candidate_complete[delta_mm]
                sigma = 0.20 if index < non_inert[delta_mm] else 0.02
            rows.append(
                {
                    "patient": patient,
                    "delta_mm": delta_mm,
                    "complete": complete,
                    "sigma_median_mm": sigma,
                    "spacing_min_mm": 0.4,
                    "proxy_error_median_mm": 10.0 + index + delta_mm,
                }
            )
    return rows


def test_selects_smallest_strength_that_passes_frozen_gate() -> None:
    selected, floor_complete, diagnostics = select_initialization_delta(
        _selection_rows(non_inert={0.5: 4, 1.0: 5, 2.0: 5})
    )
    assert floor_complete == 5
    assert selected == 0.5
    assert diagnostics[0]["eligible"] is True


def test_selects_next_strength_when_smaller_strength_is_inert() -> None:
    selected, _, diagnostics = select_initialization_delta(
        _selection_rows(non_inert={0.5: 3, 1.0: 4, 2.0: 5})
    )
    assert selected == 1.0
    assert diagnostics[0]["eligible"] is False
    assert diagnostics[1]["eligible"] is True


def test_strength_gate_stops_when_zero_floor_is_not_assessable() -> None:
    selected, floor_complete, diagnostics = select_initialization_delta(
        _selection_rows(floor_complete=3)
    )
    assert floor_complete == 3
    assert selected is None
    assert all(item["eligible"] is False for item in diagnostics)


def test_strength_requires_four_shared_complete_patients() -> None:
    selected, _, diagnostics = select_initialization_delta(
        _selection_rows(
            candidate_complete={0.5: 3, 1.0: 4, 2.0: 5},
            non_inert={0.5: 5, 1.0: 4, 2.0: 5},
        )
    )
    assert selected == 1.0
    assert diagnostics[0]["shared_complete_patients"] == 3
    assert diagnostics[0]["eligible"] is False


def test_strength_selection_does_not_use_proxy_error() -> None:
    rows = _selection_rows(non_inert={0.5: 3, 1.0: 4, 2.0: 5})
    for row in rows:
        if row["delta_mm"] == 0.5:
            row["proxy_error_median_mm"] = 0.0
        elif row["delta_mm"] == 1.0:
            row["proxy_error_median_mm"] = 1e9

    selected, _, _ = select_initialization_delta(rows)
    assert selected == 1.0
