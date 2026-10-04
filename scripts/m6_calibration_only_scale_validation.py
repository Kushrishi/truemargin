"""Calibration-cohort-only development validation for M6 scale models.

This analysis uses only the 30 Phase-A calibration anatomies. For each source,
one anatomy is held out, four of the remaining anatomies fit the affine scale,
and ten calibrate the error multiplier. The held-out anatomy is then evaluated.
Phase-B evaluation records are never opened by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from fractions import Fraction
from pathlib import Path

from m6_scale_development import fit_affine


def _ordered(patient_ids):
    return sorted(patient_ids, key=lambda p: hashlib.sha256(p.encode()).hexdigest())


def _read_phase_a(root: Path, patient_id: str) -> dict:
    path = root / f"results/m6_phase_a/phase-a-shards/shards/{patient_id}.json"
    row = json.loads(path.read_text())
    if row.get("phase") != "A" or row.get("evaluation_accessed") is not False:
        raise ValueError(f"{patient_id}: expected a Phase-A record with evaluation_accessed=false")
    if row.get("primary_complete") is not True:
        raise ValueError(f"{patient_id}: incomplete primary record")
    for field in ("sigma_mm", "known_error_mm"):
        if len(row.get(field, [])) != 50:
            raise ValueError(f"{patient_id}: {field} must contain 50 points")
    return row


def _threshold(groups: list[dict], scale, field: str, nominal: str = "0.90") -> float:
    scores = []
    for row in groups:
        values = row.get(field, [])
        if len(values) != 50 or len(row.get("known_error_mm", [])) != 50:
            raise ValueError(f"{field} and known_error_mm must contain 50 points")
        for value, error in zip(values, row["known_error_mm"], strict=True):
            denominator = scale(value)
            if not math.isfinite(denominator) or denominator <= 0:
                raise ValueError("scale must be finite and positive")
            scores.append(error / denominator)

    if not groups:
        raise ValueError("requires at least one calibration anatomy")
    rank = math.ceil(Fraction(nominal) * (len(groups) + 1) * 50)
    return sorted(scores)[rank - 1] if rank <= len(scores) else math.inf


def _evaluate(row: dict, multiplier: float, scale, field: str) -> dict:
    radii = [multiplier * scale(value) for value in row[field]]
    coverage = sum(
        error <= radius for error, radius in zip(row["known_error_mm"], radii, strict=True)
    ) / len(radii)
    return {
        "coverage": coverage,
        "mean_radius_mm": statistics.fmean(radii),
        "median_radius_mm": statistics.median(radii),
        "maximum_radius_mm": max(radii),
    }


def _summarize(folds: list[dict], method: str) -> dict:
    rows = [
        fold["models"][method]
        for fold in folds
        if fold["models"].get(method, {}).get("assessable", True)
        and "coverage" in fold["models"].get(method, {})
    ]
    if not rows:
        return {
            "assessable_folds": 0,
            "mean_coverage": None,
            "median_coverage": None,
            "mean_radius_mm": None,
            "median_anatomy_radius_mm": None,
            "maximum_anatomy_mean_radius_mm": None,
        }
    return {
        "assessable_folds": len(rows),
        "mean_coverage": statistics.fmean(row["coverage"] for row in rows),
        "median_coverage": statistics.median(row["coverage"] for row in rows),
        "mean_radius_mm": statistics.fmean(row["mean_radius_mm"] for row in rows),
        "median_anatomy_radius_mm": statistics.median(row["median_radius_mm"] for row in rows),
        "maximum_anatomy_mean_radius_mm": max(row["mean_radius_mm"] for row in rows),
    }


def validate(root: Path) -> dict:
    split = json.loads((root / "research/M6_SPLIT.json").read_text())
    sources = {}

    for source, roles in split["roles"].items():
        calibration_ids = _ordered(roles["calibration"])
        if len(calibration_ids) != 15:
            raise ValueError(f"{source}: expected 15 Phase-A calibration anatomies")
        records = {patient: _read_phase_a(root, patient) for patient in calibration_ids}

        folds = []
        for holdout_id in calibration_ids:
            remaining = [patient for patient in calibration_ids if patient != holdout_id]
            fit_ids = remaining[:4]
            multiplier_ids = remaining[4:]
            if len(fit_ids) != 4 or len(multiplier_ids) != 10:
                raise AssertionError("fold must contain 4 fit and 10 multiplier anatomies")

            fit_rows = [records[patient] for patient in fit_ids]
            multiplier_rows = [records[patient] for patient in multiplier_ids]
            holdout = records[holdout_id]

            intercept, slope = fit_affine(fit_rows)
            model_defs = {
                "constant": ("sigma_mm", lambda value: 1.0),
                "spread": ("sigma_mm", lambda value: value),
                "affine": (
                    "sigma_mm",
                    lambda value, a=intercept, b=slope: a + b * value,
                ),
            }

            models = {}
            for name, (field, scale) in model_defs.items():
                multiplier = _threshold(multiplier_rows, scale, field, nominal="0.90")
                if not math.isfinite(multiplier):
                    raise ValueError(f"{source}/{holdout_id}/{name}: non-finite 90% multiplier")
                models[name] = {
                    "multiplier": multiplier,
                    **_evaluate(holdout, multiplier, scale, field),
                }

            ice_rows = [*multiplier_rows, holdout]
            if all(row.get("ice_complete") is True for row in ice_rows):
                ice_multiplier = _threshold(
                    multiplier_rows, lambda value: value, "ice_mm", nominal="0.90"
                )
                models["ice"] = {
                    "assessable": True,
                    "multiplier": ice_multiplier,
                    **_evaluate(holdout, ice_multiplier, lambda value: value, "ice_mm"),
                }
            else:
                models["ice"] = {
                    "assessable": False,
                    "reason": "retained incomplete ICE record in multiplier or holdout set",
                }

            folds.append(
                {
                    "holdout_id": holdout_id,
                    "fit_ids": fit_ids,
                    "multiplier_ids": multiplier_ids,
                    "affine_intercept_mm": intercept,
                    "affine_slope": slope,
                    "models": models,
                }
            )

        sources[source] = {
            "folds": folds,
            "summary": {
                method: _summarize(folds, method)
                for method in ("constant", "spread", "affine", "ice")
            },
        }

    return {
        "record": "m6-calibration-only-scale-validation",
        "confirmatory": False,
        "development_only": True,
        "phase_b_accessed": False,
        "accepted_m6_results_changed": False,
        "nominal_coverage": "0.90",
        "fold_design": "1 holdout + 4 affine-fit + 10 multiplier anatomies per source",
        "sources": sources,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), indent=2, sort_keys=True, allow_nan=False))
