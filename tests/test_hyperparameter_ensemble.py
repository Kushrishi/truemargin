from __future__ import annotations

import inspect
import runpy
from pathlib import Path
from typing import Any

from truemargin import registration as reg

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "18_hyperparameter_ensemble_sensitivity.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
CASES = SCRIPT["CASES"]
HYPERPARAMETER_CONFIGS = SCRIPT["HYPERPARAMETER_CONFIGS"]
evaluate_hyperparameter_gate = SCRIPT["evaluate_hyperparameter_gate"]


def test_baseline_hyperparameter_defaults_match_frozen_nominal_settings() -> None:
    signature = inspect.signature(reg.baseline_bspline_registration)
    assert signature.parameters["metric_bins"].default == 50
    assert signature.parameters["gradient_convergence_tolerance"].default == 1e-5


def test_hyperparameter_grid_is_exact_and_deterministic() -> None:
    assert HYPERPARAMETER_CONFIGS == (
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
    assert len(set(HYPERPARAMETER_CONFIGS)) == 9


def _rows(
    *,
    floor_complete: int = 5,
    grid_complete: int = 5,
    non_inert: int = 5,
    floor_sigma: float = 0.01,
    spacing_min: float = 0.4,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, patient in enumerate(CASES):
        floor_ok = index < floor_complete
        grid_ok = index < grid_complete
        required = max(3.0 * floor_sigma, 0.25 * spacing_min)
        grid_sigma = required if index < non_inert else max(0.0, required - 0.01)
        rows.append(
            {
                "patient": patient,
                "floor_complete": floor_ok,
                "grid_complete": grid_ok,
                "floor_sigma_median_mm": floor_sigma,
                "grid_sigma_median_mm": grid_sigma,
                "spacing_min_mm": spacing_min,
                "grid_proxy_error_median_mm": 10.0 + index,
            }
        )
    return rows


def test_gate_promotes_with_four_shared_complete_non_inert_patients() -> None:
    eligible, floor_count, shared_count, non_inert_count, _ = evaluate_hyperparameter_gate(
        _rows(non_inert=4)
    )
    assert eligible is True
    assert floor_count == 5
    assert shared_count == 5
    assert non_inert_count == 4


def test_gate_fails_when_repeatability_floor_is_not_assessable() -> None:
    eligible, floor_count, _, _, _ = evaluate_hyperparameter_gate(_rows(floor_complete=3))
    assert eligible is False
    assert floor_count == 3


def test_gate_requires_four_shared_complete_patients() -> None:
    eligible, _, shared_count, _, _ = evaluate_hyperparameter_gate(_rows(grid_complete=3))
    assert eligible is False
    assert shared_count == 3


def test_gate_requires_four_non_inert_patients() -> None:
    eligible, _, _, non_inert_count, _ = evaluate_hyperparameter_gate(_rows(non_inert=3))
    assert eligible is False
    assert non_inert_count == 3


def test_resolution_floor_is_used_when_repeatability_floor_is_small() -> None:
    rows = _rows(floor_sigma=0.01, spacing_min=0.4, non_inert=5)
    eligible, _, _, _, diagnostics = evaluate_hyperparameter_gate(rows)
    assert eligible is True
    assert all(item["required_signal_mm"] == 0.1 for item in diagnostics)


def test_three_times_repeatability_floor_dominates_when_larger() -> None:
    rows = _rows(floor_sigma=0.2, spacing_min=0.4, non_inert=5)
    eligible, _, _, _, diagnostics = evaluate_hyperparameter_gate(rows)
    assert eligible is True
    assert all(abs(item["required_signal_mm"] - 0.6) < 1e-12 for item in diagnostics)


def test_proxy_error_cannot_change_promotion() -> None:
    rows = _rows(non_inert=4)
    baseline_result = evaluate_hyperparameter_gate(rows)[:4]

    for index, row in enumerate(rows):
        row["grid_proxy_error_median_mm"] = 0.0 if index == 0 else 1e12

    assert evaluate_hyperparameter_gate(rows)[:4] == baseline_result
