"""Known-GT comparator orchestration for the frozen TrueMargin study."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from truemargin import comparators
from truemargin import hyperparameter as hyper


@dataclass(frozen=True)
class DirectComparatorResult:
    """Per-case direct-comparator outputs without changing target validity."""

    reverse_complete: bool
    reverse_member_reasons: tuple[str, ...]
    ice: np.ndarray | None
    ice_failure_reason: str | None
    residual: np.ndarray | None
    residual_failure_reason: str | None
    jacdev: np.ndarray | None
    jacdev_failure_reason: str | None


def _failure_reason(prefix: str, exc: Exception) -> str:
    return f"{prefix}:{type(exc).__name__}:{exc}"


def run_direct_comparators(
    *,
    fixed: np.ndarray,
    moving: np.ndarray,
    forward_u_mean: np.ndarray,
    idx_zyx: np.ndarray,
    spacing: tuple[float, ...],
    crop_diagonal_mm: float,
) -> DirectComparatorResult:
    """Compute frozen local comparators for one forward-complete case.

    Residual and Jacobian deviation reuse the forward ensemble mean. ICE runs
    the same frozen nine-member estimator with fixed/moving roles reversed.
    Comparator failures are method-specific and never change primary target
    completeness.
    """
    fixed_array = np.asarray(fixed)
    moving_array = np.asarray(moving)
    forward = np.asarray(forward_u_mean, dtype=np.float64)
    landmarks = np.asarray(idx_zyx, dtype=np.int64)

    residual: np.ndarray | None = None
    residual_failure: str | None = None
    try:
        residual = comparators.absolute_residual_scores(
            fixed_array,
            moving_array,
            forward,
            landmarks,
            spacing,
        )
    except Exception as exc:
        residual_failure = _failure_reason("residual", exc)

    jacdev: np.ndarray | None = None
    jacdev_failure: str | None = None
    try:
        jacdev = comparators.jacobian_deviation_scores(
            forward,
            landmarks,
            spacing,
        )
    except Exception as exc:
        jacdev_failure = _failure_reason("jacdev", exc)

    reverse_complete = False
    reverse_reasons: tuple[str, ...] = ()
    ice: np.ndarray | None = None
    ice_failure: str | None = None
    try:
        reverse = hyper.run_hyperparameter_ensemble(
            moving_array,
            fixed_array,
            spacing=spacing,
            crop_diagonal_mm=float(crop_diagonal_mm),
        )
        reverse_complete = bool(reverse.complete)
        reverse_reasons = tuple(reverse.member_reasons)
        if not reverse.complete:
            failed = sum(reason != "ok" for reason in reverse.member_reasons)
            ice_failure = f"reverse_ensemble_incomplete:{failed}/{len(reverse.member_reasons)}"
        else:
            assert reverse.u_mean is not None
            try:
                ice = comparators.inverse_consistency_scores(
                    forward,
                    reverse.u_mean,
                    landmarks,
                    spacing,
                )
            except Exception as exc:
                ice_failure = _failure_reason("ice", exc)
    except Exception as exc:
        ice_failure = _failure_reason("reverse_ensemble", exc)

    return DirectComparatorResult(
        reverse_complete=reverse_complete,
        reverse_member_reasons=reverse_reasons,
        ice=ice,
        ice_failure_reason=ice_failure,
        residual=residual,
        residual_failure_reason=residual_failure,
        jacdev=jacdev,
        jacdev_failure_reason=jacdev_failure,
    )


def score_case_metrics(
    score: np.ndarray,
    known_error: np.ndarray,
) -> dict[str, Any]:
    """Return the frozen local-informativeness/blind-spot metrics for one method."""
    score_values = np.asarray(score, dtype=np.float64)
    error_values = np.asarray(known_error, dtype=np.float64)
    if (
        score_values.ndim != 1
        or error_values.ndim != 1
        or len(score_values) != len(error_values)
        or len(score_values) < 4
    ):
        raise ValueError("score and known_error must be matching one-dimensional vectors")
    if not np.isfinite(score_values).all() or not np.isfinite(error_values).all():
        raise ValueError("score and known_error must be finite")

    rho, degenerate = comparators.rank_association(score_values, error_values)
    score_q25, score_q75 = np.percentile(score_values, [25, 75])
    error_q75 = float(np.percentile(error_values, 75))
    low_score = score_values <= score_q25
    high_score = score_values >= score_q75
    blind_spot = (error_values >= error_q75) & low_score

    return {
        "spearman_known_error": rho,
        "rank_degenerate": degenerate,
        "score_median": float(np.median(score_values)),
        "score_iqr": float(np.percentile(score_values, 75) - np.percentile(score_values, 25)),
        "quartile_known_error_delta_mm": float(
            np.median(error_values[high_score]) - np.median(error_values[low_score])
        ),
        "blind_spot_rate": float(np.mean(blind_spot)),
    }


def anatomy_summary(
    case_rows: list[dict[str, Any]],
    *,
    patients: list[str],
    method: str,
    min_complete_cases: int,
) -> list[dict[str, Any]]:
    """Aggregate one comparator to the frozen anatomy inferential unit."""
    output: list[dict[str, Any]] = []
    valid_key = f"{method}_valid"
    rho_key = f"spearman_{method}_known_error"
    degenerate_key = f"{method}_rank_degenerate"

    for patient in patients:
        patient_rows = [row for row in case_rows if row["patient"] == patient]
        valid_rows = [row for row in patient_rows if bool(row.get(valid_key, False))]
        assessable = len(valid_rows) >= min_complete_cases
        anatomy: dict[str, Any] = {
            "patient": patient,
            "valid_cases": len(valid_rows),
            "assessable": assessable,
            "rank_degenerate_cases": sum(
                bool(row.get(degenerate_key, False)) for row in valid_rows
            ),
            "median_case_spearman": (
                float(np.median([row[rho_key] for row in valid_rows]))
                if assessable
                else float("nan")
            ),
        }
        if assessable:
            for suffix in ("quartile_known_error_delta_mm", "blind_spot_rate"):
                key = f"{method}_{suffix}"
                values = np.asarray(
                    [row[key] for row in valid_rows if key in row],
                    dtype=np.float64,
                )
                finite = values[np.isfinite(values)]
                anatomy[f"median_{suffix}"] = (
                    float(np.median(finite)) if len(finite) else float("nan")
                )
        output.append(anatomy)
    return output
