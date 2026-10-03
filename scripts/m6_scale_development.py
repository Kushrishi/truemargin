"""Post-outcome scale-model exploration; never replaces accepted M6 results."""

import argparse
import hashlib
import json
import math
import statistics
from fractions import Fraction
from pathlib import Path

from m6_failure_diagnostics import diagnose


def fit_affine(groups):
    """Nonnegative least squares for error = intercept + slope * spread.

    Evaluate the unconstrained solution and both boundary solutions. All groups
    have the same number of points; anatomy weights are therefore equal.
    """
    pairs = [
        (s, e)
        for row in groups
        for s, e in zip(row["sigma_mm"], row["known_error_mm"], strict=True)
    ]
    x, y = zip(*pairs, strict=True)
    mx, my = statistics.fmean(x), statistics.fmean(y)
    xx = sum(v * v for v in x)
    variance = sum((v - mx) ** 2 for v in x)
    options = [(my, 0.0), (0.0, sum(a * b for a, b in pairs) / xx if xx else 0.0)]
    if variance:
        slope = sum((a - mx) * (b - my) for a, b in pairs) / variance
        intercept = my - slope * mx
        if slope >= 0 and intercept >= 0:
            options.append((intercept, slope))
    return min(options, key=lambda ab: sum((e - ab[0] - ab[1] * s) ** 2 for s, e in pairs))


def threshold(groups, scale, nominal="0.90"):
    scores = []
    for row in groups:
        for spread, error in zip(row["sigma_mm"], row["known_error_mm"], strict=True):
            denominator = scale(spread)
            if not math.isfinite(denominator) or denominator <= 0:
                raise ValueError("scale must be finite and positive")
            scores.append(error / denominator)
    if not groups or any(len(row["sigma_mm"]) != 50 for row in groups):
        raise ValueError("requires nonempty groups with 50 points")
    rank = math.ceil(Fraction(nominal) * (len(groups) + 1) * 50)
    return sorted(scores)[rank - 1] if rank <= len(scores) else math.inf


def develop(root, fit_block=0):
    if fit_block not in (0, 1, 2):
        raise ValueError("fit block must be 0, 1 or 2")
    verified = diagnose(root)
    split = json.loads((root / "research/M6_SPLIT.json").read_text())
    sources = {}
    for source, roles in split["roles"].items():
        ordered = sorted(roles["calibration"], key=lambda p: hashlib.sha256(p.encode()).hexdigest())
        fit_ids = ordered[5 * fit_block : 5 * (fit_block + 1)]
        calibration_ids = [p for p in ordered if p not in fit_ids]

        def read(patient, phase):
            return json.loads(
                (
                    root / f"results/m6_phase_{phase}/phase-{phase}-shards/shards/{patient}.json"
                ).read_text()
            )

        fit = [read(p, "a") for p in fit_ids]
        calibration = [read(p, "a") for p in calibration_ids]
        intercept, slope = fit_affine(fit)
        models = {
            "constant": lambda s: 1.0,
            "spread": lambda s: s,
            "affine": lambda s, a=intercept, b=slope: a + b * s,
        }
        results = {}
        for name, scale in models.items():
            q = threshold(calibration, scale)
            rows = []
            for patient in sorted(roles["evaluation"]):
                row = read(patient, "b")
                radii = [q * scale(s) for s in row["sigma_mm"]]
                rows.append(
                    {
                        "patient_id": patient,
                        "coverage": sum(
                            e <= r for e, r in zip(row["known_error_mm"], radii, strict=True)
                        )
                        / 50,
                        "mean_radius_mm": statistics.fmean(radii),
                        "median_radius_mm": statistics.median(radii),
                    }
                )
            results[name] = {
                "multiplier": q,
                "equal_anatomy_coverage": statistics.fmean(r["coverage"] for r in rows),
                "equal_anatomy_mean_radius_mm": statistics.fmean(r["mean_radius_mm"] for r in rows),
                "maximum_anatomy_mean_radius_mm": max(r["mean_radius_mm"] for r in rows),
                "per_anatomy": rows,
            }
        sources[source] = {
            "fit_ids": fit_ids,
            "calibration_ids": calibration_ids,
            "affine_intercept_mm": intercept,
            "affine_slope": slope,
            "models": results,
        }
    return {
        "record": "m6-post-outcome-scale-development",
        "confirmatory": False,
        "evaluation_previously_observed": True,
        "evaluation_used_for_fitting": False,
        "accepted_thresholds_changed": False,
        "new_registrations": 0,
        "nominal": "0.90",
        "coverage_matched": False,
        "fit_block": fit_block,
        "selection_rule": (
            "SHA256(patient_id): selected contiguous block of 5 fits; other 10 calibrate per source"
        ),
        "input_sha256": verified["input_sha256"],
        "sources": sources,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--fit-block", type=int, choices=(0, 1, 2), default=0)
    args = parser.parse_args()
    print(json.dumps(develop(args.root, args.fit_block), indent=2, sort_keys=True, allow_nan=False))
