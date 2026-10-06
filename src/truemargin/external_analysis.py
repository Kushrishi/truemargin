"""Pre-outcome coordinate and case-hierarchical analysis utilities.

No landmark file access. Arrays supplied by a separately gated caller only.
Undefined associations remain explicit; no case is silently dropped.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.stats import binomtest, spearmanr


def physical_to_index_xyz(points, spacing, origin, direction):
    points = np.asarray(points, dtype=float)
    spacing = np.asarray(spacing, dtype=float)
    origin = np.asarray(origin, dtype=float)
    direction = np.asarray(direction, dtype=float).reshape(3, 3)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must be N by 3 physical XYZ")
    if spacing.shape != (3,) or origin.shape != (3,) or np.any(spacing <= 0):
        raise ValueError("invalid grid geometry")
    if not all(np.isfinite(x).all() for x in (points, spacing, origin, direction)):
        raise ValueError("nonfinite geometry")
    if not np.allclose(direction.T @ direction, np.eye(3), rtol=0.0, atol=1e-8):
        raise ValueError("direction must be orthonormal")
    return np.linalg.solve(direction, (points - origin).T).T / spacing


def sample_grid(values, indices_xyz):
    """Linear sample scalar ZYX or XYZ-component-first field; reject OOB."""
    values = np.asarray(values, dtype=float)
    points = np.asarray(indices_xyz, dtype=float)
    if values.ndim not in (3, 4) or (values.ndim == 4 and values.shape[0] != 3):
        raise ValueError("expected scalar ZYX or field [3,Z,Y,X]")
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("invalid index points")
    if not np.isfinite(values).all():
        raise ValueError("nonfinite grid")
    bounds = np.array(values.shape[-3:][::-1]) - 1
    if np.any(points < 0) or np.any(points > bounds):
        raise ValueError("landmark outside image grid")
    coords = points[:, ::-1].T
    if values.ndim == 3:
        return map_coordinates(values, coords, order=1, mode="nearest", prefilter=False)
    return np.column_stack(
        [map_coordinates(v, coords, order=1, mode="nearest", prefilter=False) for v in values]
    )


def case_statistics(error, signals):
    error = np.asarray(error, dtype=float)
    if error.ndim != 1 or error.size < 2 or not np.isfinite(error).all() or np.any(error < 0):
        raise ValueError("invalid landmark error")
    result = {}
    for name, score in signals.items():
        if score is None:
            result[name] = {"status": "failed", "rho": None, "blind_spots": None}
            continue
        score = np.asarray(score, dtype=float)
        if score.shape != error.shape or not np.isfinite(score).all():
            raise ValueError("invalid signal")
        rho = (
            None
            if np.ptp(score) == 0 or np.ptp(error) == 0
            else float(spearmanr(score, error).statistic)
        )
        result[name] = {
            "status": "undefined" if rho is None else "complete",
            "rho": rho,
            "blind_spots": int(
                np.sum((error >= np.quantile(error, 0.75)) & (score <= np.quantile(score, 0.25)))
            ),
        }
    return result


def bootstrap_median(values, seed=20261006):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError("invalid case statistics")
    rng = np.random.default_rng(seed)
    medians = np.median(rng.choice(values, size=(10000, len(values)), replace=True), axis=1)
    return np.quantile(medians, [0.025, 0.975]).tolist()


def aggregate_cases(cases, expected_ids, seed=20261006):
    if len(expected_ids) != 10 or len(set(expected_ids)) != 10 or set(cases) != set(expected_ids):
        raise ValueError("exact ten frozen case identities required")
    for case_id in expected_ids:
        methods = cases[case_id]
        if not isinstance(methods, dict) or "spread" not in methods:
            raise ValueError("case must contain target spread statistics")
        for record in methods.values():
            if not isinstance(record, dict) or record.get("status") not in {
                "complete",
                "undefined",
                "failed",
            }:
                raise ValueError("invalid case statistic status")
            rho = record.get("rho")
            if record["status"] == "complete":
                if isinstance(rho, bool) or not isinstance(rho, (int, float)):
                    raise ValueError("complete correlation must be numerical")
                if not np.isfinite(rho) or not -1 <= rho <= 1:
                    raise ValueError("correlation must be finite and within [-1,1]")
            elif rho is not None:
                raise ValueError("undefined/failed correlation must be null")
            blind = record.get("blind_spots")
            if record["status"] == "failed":
                if blind is not None:
                    raise ValueError("failed signal cannot supply blind-spot count")
            elif type(blind) is not int or blind < 0:
                raise ValueError("blind-spot count must be a nonnegative integer")
    target = [cases[i]["spread"]["rho"] for i in expected_ids]
    if any(v is None for v in target):
        return {"status": "primary_not_assessable", "cases": cases}
    if any(not {"ice", "residual", "jacobian"} <= set(cases[i]) for i in expected_ids):
        raise ValueError("all frozen comparators must be recorded, including failures")
    positive = sum(v > 0 for v in target)
    result = {
        "status": "complete",
        "median_case_rho": float(np.median(target)),
        "positive_cases": positive,
        "case_count": 10,
        "sign_test_one_sided": float(binomtest(positive, 10, 0.5, alternative="greater").pvalue),
        "median_bootstrap_95": bootstrap_median(target, seed),
        "seed": seed,
        "replicates": 10000,
        "comparators": {},
        "cases": cases,
    }
    for method in ("ice", "residual", "jacobian"):
        valid = [i for i in expected_ids if cases[i][method]["rho"] is not None]
        differences = [cases[i]["spread"]["rho"] - cases[i][method]["rho"] for i in valid]
        result["comparators"][method] = {
            "assessable_case_ids": valid,
            "failed_or_undefined_case_ids": [i for i in expected_ids if i not in valid],
            "paired_differences": differences,
            "median_difference": float(np.median(differences)) if differences else None,
            "paired_bootstrap_95": (bootstrap_median(differences, seed) if differences else None),
        }
    return result
