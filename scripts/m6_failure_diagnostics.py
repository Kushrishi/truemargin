"""Descriptive M6 failure diagnostics; never refit or replace accepted thresholds.

Uses retained JSON vectors only. Input digests, cohort checks and frozen geometry
identities make the report replayable without images, registration or NumPy.
"""

import argparse
import collections
import csv
import hashlib
import json
import math
import statistics
import struct
from pathlib import Path


def ranks(values):
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def spearman(first, second):
    if len(first) != len(second) or len(first) < 2:
        raise ValueError("rank vectors must have equal nontrivial length")
    a, b = ranks(first), ranks(second)
    if len(set(a)) == 1 or len(set(b)) == 1:
        return None
    return statistics.correlation(a, b)


def vector_digest(values):
    header = json.dumps({"dtype": "<f8", "shape": [len(values)]}, sort_keys=True).encode()
    return hashlib.sha256(
        header + b"\0" + struct.pack("<" + "d" * len(values), *values)
    ).hexdigest()


def validate_record(record, patient, source, phase, frozen):
    if (
        record["patient_id"] != patient
        or record["source_key"] != source
        or record["phase"] != phase
        or not record["primary_complete"]
        or record["evaluation_accessed"] != (phase == "B")
        or record["forward_member_reasons"] != ["ok"] * 9
    ):
        raise ValueError("incomplete or mismatched primary record")
    for key in ("geometry_sha256", "series_uid"):
        if record[key] != frozen[key]:
            raise ValueError("frozen geometry identity mismatch")
    if phase == "B":
        for key in ("dicom_zip_sha256", "label_sha256"):
            if record[key] != frozen[key]:
                raise ValueError("frozen input identity mismatch")
    for key in ("known_error_mm", "sigma_mm", "sigma_scores"):
        values = record[key]
        if len(values) != 50 or any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError("requires 50 finite nonnegative primary values")
        if vector_digest(values) != record["hashes"][key]:
            raise ValueError("primary vector digest mismatch")
    for error, sigma, score in zip(
        record["known_error_mm"], record["sigma_mm"], record["sigma_scores"], strict=True
    ):
        if sigma <= 0 or error / sigma != score:
            raise ValueError("diagnostic requires unchanged positive-sigma ratio scores")
    if record["ice_complete"]:
        if record["reverse_member_reasons"] != ["ok"] * 9:
            raise ValueError("ICE completion/member mismatch")
        if len(record["ice_mm"]) != 50:
            raise ValueError("ICE completion/vector mismatch")


def anatomy_row(record, multiplier):
    error, sigma = record["known_error_mm"], record["sigma_mm"]
    radii = [multiplier * value for value in sigma]
    return {
        "patient_id": record["patient_id"],
        "error_mean_mm": statistics.fmean(error),
        "error_median_mm": statistics.median(error),
        "error_max_mm": max(error),
        "sigma_mean_mm": statistics.fmean(sigma),
        "sigma_median_mm": statistics.median(sigma),
        "sigma_min_mm": min(sigma),
        "sigma_max_mm": max(sigma),
        "sigma_error_spearman": spearman(sigma, error),
        "radius_mean_mm": statistics.fmean(radii),
        "radius_median_mm": statistics.median(radii),
        "coverage": sum(e <= radius for e, radius in zip(error, radii, strict=True)) / 50,
        "ice_complete": record["ice_complete"],
        "ice_failure": record["ice_failure"],
        "forward_members_pass_recorded_validity_checks": True,
        "reverse_member_reasons": record["reverse_member_reasons"],
    }


def diagnose(root):
    inputs = []

    def read(relative):
        path = root / relative
        inputs.append(path)
        return json.loads(path.read_text())

    split = read("research/M6_SPLIT.json")
    seal = read("research/M6_PHASE_A_THRESHOLD_SEAL.json")
    cal_freeze = read("research/M6_PHASE_A_GEOMETRY_FREEZE.json")["calibration"]
    eval_freeze = read("research/M6_PHASE_B_INPUT_FREEZE.json")["evaluation"]
    sources = {}
    for source, roles in split["roles"].items():
        multiplier = seal["thresholds"][source]["sigma"]["thresholds"]["0.90"]
        records = {}
        for phase, role, freeze in (
            ("A", "calibration", cal_freeze),
            ("B", "evaluation", eval_freeze),
        ):
            if len(roles[role]) != 15 or len(set(roles[role])) != 15:
                raise ValueError("requires unchanged 15-anatomy source roles")
            records[role] = []
            for patient in sorted(roles[role]):
                relative = f"results/m6_phase_{phase.lower()}/phase-{phase.lower()}-shards"
                record = read(f"{relative}/shards/{patient}.json")
                validate_record(record, patient, source, phase, freeze[patient])
                records[role].append(record)
        if set(roles["calibration"]) & set(roles["evaluation"]):
            raise ValueError("calibration/evaluation overlap")
        ordered = sorted(
            (score, record["patient_id"], index)
            for record in records["calibration"]
            for index, score in enumerate(record["sigma_scores"])
        )
        cutoff, patient, index = ordered[719]
        if cutoff != multiplier:
            raise ValueError("rank 720 disagrees with unchanged threshold seal")
        cutoff_record = next(r for r in records["calibration"] if r["patient_id"] == patient)
        tail = [row for row in ordered if row[0] >= cutoff]
        calibration_rows = [anatomy_row(r, multiplier) for r in records["calibration"]]
        evaluation_rows = [anatomy_row(r, multiplier) for r in records["evaluation"]]
        radius_sum = sum(r["radius_mean_mm"] for r in evaluation_rows)
        biggest = max(evaluation_rows, key=lambda r: r["radius_mean_mm"])
        sources[source] = {
            "sealed_90_multiplier": multiplier,
            "calibration_cutoff": {
                "finite_order_statistic_rank": 720,
                "finite_score_count": 750,
                "patient_id": patient,
                "point_index": index,
                "error_mm": cutoff_record["known_error_mm"][index],
                "sigma_mm": cutoff_record["sigma_mm"][index],
                "tail_definition": "all finite calibration scores >= sealed 90% cutoff",
                "tail_point_count": len(tail),
                "tail_points_by_anatomy": dict(
                    sorted(collections.Counter(row[1] for row in tail).items())
                ),
            },
            "calibration": calibration_rows,
            "evaluation": evaluation_rows,
            "evaluation_radius_summary": {
                "equal_anatomy_mean_mm": radius_sum / 15,
                "largest_mean_radius_patient": biggest["patient_id"],
                "largest_mean_radius_mm": biggest["radius_mean_mm"],
                "largest_anatomy_fraction_of_radius_sum": biggest["radius_mean_mm"] / radius_sum,
                "leave_largest_out_mean_mm_sensitivity_only": statistics.fmean(
                    r["radius_mean_mm"] for r in evaluation_rows if r is not biggest
                ),
                "primary_cohort_exclusions": 0,
            },
        }
    m5_paths = (
        "results/m5/m5_case_characterization.csv",
        "results/m5/m5_sigma_blind_spots.csv",
    )
    m5_rows = []
    for relative in m5_paths:
        path = root / relative
        inputs.append(path)
        with path.open() as stream:
            m5_rows.append(list(csv.DictReader(stream)))
    cases, blind = m5_rows
    negatives = [r for r in cases if float(r["sigma_case_spearman"]) < 0]
    return {
        "schema_version": 1,
        "record": "m6-post-outcome-retained-evidence-failure-diagnostics",
        "confirmatory": False,
        "thresholds_refitted": False,
        "new_registrations": 0,
        "primary_results_changed": False,
        "sources": sources,
        "m5_existing_evidence": {
            "independent_replication": False,
            "case_count": len(cases),
            "negative_case_count": len(negatives),
            "negative_cases": negatives,
            "blind_spot_points": len(blind),
            "blind_spot_cases": len({(r["patient"], r["replicate"]) for r in blind}),
            "blind_spot_anatomies": len({r["patient"] for r in blind}),
        },
        "mechanism_not_identified": True,
        "input_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(inputs)
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(diagnose(args.repository_root), indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        args.output.write_text(payload + "\n")
    else:
        print(payload)
