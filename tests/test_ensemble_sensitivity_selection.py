from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "15_ensemble_perturbation_sensitivity.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
CASES = SCRIPT["CASES"]
select_alpha = SCRIPT["select_alpha"]
setting_id = SCRIPT["setting_id"]


def _row(
    patient: str,
    alpha: float,
    *,
    complete: bool = True,
    sigma_median_mm: float = 1.0,
    error_median_mm: float = 10.0,
    spearman: float = 0.0,
) -> dict[str, Any]:
    return {
        "patient": patient,
        "setting": setting_id("relative_std", alpha),
        "perturbation": "relative_std",
        "perturbation_scale": alpha,
        "complete": complete,
        "sigma_median_mm": sigma_median_mm,
        "error_median_mm": error_median_mm,
        "spearman_sigma_error": spearman,
    }


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patient in CASES:
        rows.append(_row(patient, 0.00, sigma_median_mm=1.0, error_median_mm=10.0))
        rows.append(_row(patient, 0.01, sigma_median_mm=2.0, error_median_mm=10.0))
        rows.append(_row(patient, 0.02, sigma_median_mm=3.1, error_median_mm=11.0))
        rows.append(_row(patient, 0.05, sigma_median_mm=6.0, error_median_mm=13.0))
        rows.append(_row(patient, 0.10, sigma_median_mm=10.0, error_median_mm=20.0))
    return rows


def test_selects_smallest_alpha_that_passes_frozen_stability_gate() -> None:
    selected, diagnostics = select_alpha(_rows())

    assert selected == 0.02
    by_alpha = {item["alpha"]: item for item in diagnostics}
    assert by_alpha[0.01]["eligible"] is False  # perturbation still too close to floor
    assert by_alpha[0.02]["eligible"] is True
    assert by_alpha[0.05]["eligible"] is False  # proxy error is >25% worse than alpha=0
    assert by_alpha[0.10]["eligible"] is False


def test_selection_does_not_optimize_sigma_error_correlation() -> None:
    rows = _rows()
    for row in rows:
        if row["perturbation_scale"] == 0.02:
            row["spearman_sigma_error"] = -1.0
        if row["perturbation_scale"] == 0.10:
            row["spearman_sigma_error"] = 1.0

    selected, _ = select_alpha(rows)

    assert selected == 0.02


def test_unstable_candidate_is_not_eligible_even_if_other_diagnostics_pass() -> None:
    rows = _rows()
    failed_patients = list(CASES)[:2]
    for row in rows:
        if row["perturbation_scale"] == 0.02 and row["patient"] in failed_patients:
            row["complete"] = False

    selected, diagnostics = select_alpha(rows)

    assert selected is None
    by_alpha = {item["alpha"]: item for item in diagnostics}
    assert by_alpha[0.02]["complete_patients"] == 3
    assert by_alpha[0.02]["eligible"] is False
