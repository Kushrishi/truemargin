from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "16_registration_convergence_sensitivity.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
CASES = SCRIPT["CASES"]
ITERATION_BUDGETS = SCRIPT["ITERATION_BUDGETS"]
add_reference_metrics = SCRIPT["add_reference_metrics"]
select_iterations = SCRIPT["select_iterations"]


def _rows(*, converged_by_budget: dict[int, int] | None = None) -> list[dict[str, Any]]:
    converged_by_budget = converged_by_budget or {15: 5, 30: 5, 60: 5}
    rows: list[dict[str, Any]] = []
    patients = list(CASES)
    for budget in ITERATION_BUDGETS:
        for index, patient in enumerate(patients):
            is_reference = budget == 100
            rows.append(
                {
                    "patient": patient,
                    "max_iterations": budget,
                    "assessable": True,
                    "reference_assessable": not is_reference,
                    "converged_to_reference": (
                        False if is_reference else index < converged_by_budget[budget]
                    ),
                    "proxy_error_median_mm": 10.0 + budget,
                }
            )
    return rows


def test_selects_smallest_lower_budget_that_passes_frozen_gate() -> None:
    selected, diagnostics = select_iterations(
        _rows(converged_by_budget={15: 4, 30: 5, 60: 5}),
        reference_assessable_patients=5,
    )

    assert selected == 15
    by_budget = {item["max_iterations"]: item for item in diagnostics}
    assert by_budget[15]["eligible"] is True
    assert by_budget[30]["eligible"] is True
    assert by_budget[60]["eligible"] is True


def test_selects_next_budget_when_15_iterations_does_not_converge_for_four_patients() -> None:
    selected, diagnostics = select_iterations(
        _rows(converged_by_budget={15: 3, 30: 4, 60: 5}),
        reference_assessable_patients=5,
    )

    assert selected == 30
    by_budget = {item["max_iterations"]: item for item in diagnostics}
    assert by_budget[15]["eligible"] is False
    assert by_budget[30]["eligible"] is True


def test_no_lower_budget_selected_when_reference_is_not_assessable_in_four_patients() -> None:
    selected, diagnostics = select_iterations(
        _rows(),
        reference_assessable_patients=3,
    )

    assert selected is None
    assert all(item["eligible"] is False for item in diagnostics)


def test_selection_does_not_use_proxy_error() -> None:
    rows = _rows(converged_by_budget={15: 3, 30: 4, 60: 5})
    for row in rows:
        if row["max_iterations"] == 15:
            row["proxy_error_median_mm"] = 0.0
        elif row["max_iterations"] == 30:
            row["proxy_error_median_mm"] = 1e9

    selected, _ = select_iterations(rows, reference_assessable_patients=5)

    assert selected == 30


def test_reference_metrics_use_resolution_and_repeatability_tolerance_floors() -> None:
    rows: list[dict[str, Any]] = []
    representatives: dict[tuple[str, int], np.ndarray | None] = {}

    for patient in CASES:
        for budget in ITERATION_BUDGETS:
            row = {
                "patient": patient,
                "max_iterations": budget,
                "assessable": True,
                "spacing_min_mm": 0.4,
                "spacing_max_mm": 4.0,
                "repeatability_median_mm": 0.1,
                "repeatability_p90_mm": 0.5,
                "converged_to_reference": False,
            }
            rows.append(row)
            representatives[(patient, budget)] = np.zeros((3, 5), dtype=float)

    reference_count = add_reference_metrics(rows, representatives)

    assert reference_count == 5
    candidate = next(
        row for row in rows if row["patient"] == "aaa0054" and row["max_iterations"] == 15
    )
    assert candidate["median_tolerance_mm"] == 0.4
    assert candidate["p90_tolerance_mm"] == 2.0
    assert candidate["reference_delta_median_mm"] == 0.0
    assert candidate["reference_delta_p90_mm"] == 0.0
    assert candidate["converged_to_reference"] is True


def test_reference_delta_above_frozen_tolerance_fails_patient_gate() -> None:
    rows: list[dict[str, Any]] = []
    representatives: dict[tuple[str, int], np.ndarray | None] = {}

    for patient in CASES:
        for budget in ITERATION_BUDGETS:
            rows.append(
                {
                    "patient": patient,
                    "max_iterations": budget,
                    "assessable": True,
                    "spacing_min_mm": 0.4,
                    "spacing_max_mm": 4.0,
                    "repeatability_median_mm": 0.1,
                    "repeatability_p90_mm": 0.5,
                    "converged_to_reference": False,
                }
            )
            value = 0.0
            if patient == "aaa0054" and budget == 15:
                value = 3.0
            representatives[(patient, budget)] = np.full((3, 5), value, dtype=float)

    add_reference_metrics(rows, representatives)

    candidate = next(
        row for row in rows if row["patient"] == "aaa0054" and row["max_iterations"] == 15
    )
    assert candidate["reference_delta_median_mm"] > candidate["median_tolerance_mm"]
    assert candidate["converged_to_reference"] is False
