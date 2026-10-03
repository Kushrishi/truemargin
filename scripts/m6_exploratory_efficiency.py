"""Post-M6 descriptive comparison; not a prespecified confirmatory result.

The baseline is a source-specific constant radius fitted only to retained
calibration errors with the same 15-group hierarchical weights. Sigma keeps
its accepted sealed multipliers. No registration or accepted artifact is changed.
"""

import argparse
import hashlib
import json
import math
import statistics
from fractions import Fraction
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def constant_threshold(groups, nominal):
    if len(groups) != 15 or any(len(values) != 50 for values in groups):
        raise ValueError("requires the unchanged 15-anatomy, 50-point source design")
    errors = sorted(x for values in groups for x in values)
    if any(not math.isfinite(x) or x < 0 for x in errors):
        raise ValueError("invalid calibration error")
    rank = math.ceil(Fraction(nominal) * 800)
    return errors[rank - 1] if rank <= 750 else math.inf


def analyze(root):
    split = load(root / "research/M6_SPLIT.json")
    seal = load(root / "research/M6_PHASE_A_THRESHOLD_SEAL.json")
    calibration = {
        p.stem: load(p) for p in (root / "results/m6_phase_a/phase-a-shards/shards").glob("*.json")
    }
    evaluation = {
        p.stem: load(p) for p in (root / "results/m6_phase_b/phase-b-shards/shards").glob("*.json")
    }
    expected_calibration = {p for roles in split["roles"].values() for p in roles["calibration"]}
    expected_evaluation = {p for roles in split["roles"].values() for p in roles["evaluation"]}
    if set(calibration) != expected_calibration or set(evaluation) != expected_evaluation:
        raise ValueError("cohort mismatch")
    sources = {}
    for source, roles in split["roles"].items():
        patients = sorted(roles["evaluation"])
        groups = [calibration[p]["known_error_mm"] for p in roles["calibration"]]
        sources[source] = {}
        for nominal in ("0.80", "0.90"):
            constant = constant_threshold(groups, nominal)
            multiplier = seal["thresholds"][source]["sigma"]["thresholds"][nominal]
            rows = []
            for patient in patients:
                record = evaluation[patient]
                if not record["primary_complete"] or len(record["known_error_mm"]) != 50:
                    raise ValueError("incomplete primary cohort")
                radii = [multiplier * x for x in record["sigma_mm"]]
                errors = record["known_error_mm"]
                rows.append(
                    {
                        "patient_id": patient,
                        "sigma_coverage": sum(e <= r for e, r in zip(errors, radii, strict=True))
                        / 50,
                        "constant_coverage": sum(e <= constant for e in errors) / 50,
                        "sigma_mean_radius_mm": statistics.fmean(radii),
                        "sigma_median_radius_mm": statistics.median(radii),
                        "constant_radius_mm": constant,
                    }
                )
            sigma_mean = statistics.fmean(r["sigma_mean_radius_mm"] for r in rows)
            sources[source][nominal] = {
                "constant_threshold_mm": constant,
                "sealed_sigma_multiplier": multiplier,
                "sigma_equal_anatomy_coverage": statistics.fmean(r["sigma_coverage"] for r in rows),
                "constant_equal_anatomy_coverage": statistics.fmean(
                    r["constant_coverage"] for r in rows
                ),
                "sigma_equal_anatomy_mean_radius_mm": sigma_mean,
                "constant_equal_anatomy_mean_radius_mm": constant,
                "sigma_median_of_anatomy_medians_mm": statistics.median(
                    r["sigma_median_radius_mm"] for r in rows
                ),
                "sigma_to_constant_mean_radius_ratio": sigma_mean / constant,
                "anatomies_with_smaller_sigma_mean_radius": sum(
                    r["sigma_mean_radius_mm"] < constant for r in rows
                ),
                "per_anatomy": rows,
            }
    input_paths = [
        root / "research/M6_PHASE_A_THRESHOLD_SEAL.json",
        root / "research/M6_SPLIT.json",
    ]
    input_paths += sorted((root / "results/m6_phase_a/phase-a-shards/shards").glob("*.json"))
    input_paths += sorted((root / "results/m6_phase_b/phase-b-shards/shards").glob("*.json"))
    return {
        "schema_version": 1,
        "record": "m6-post-outcome-exploratory-efficiency-comparison",
        "confirmatory": False,
        "evaluation_results_observed_before_analysis_choice": True,
        "accepted_sigma_thresholds_changed": False,
        "new_registrations": 0,
        "baseline_fit_uses_evaluation_errors": False,
        "coverage_matched_comparison": False,
        "ninety_five_percent_constant_and_sigma_radii": "positive_infinity",
        "input_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in input_paths
        },
        "sources": sources,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", type=Path)
    print(json.dumps(analyze(parser.parse_args().repository_root), indent=2, sort_keys=True))
