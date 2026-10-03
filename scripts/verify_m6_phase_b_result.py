"""Audit retained Phase B evidence without importing the experiment implementation.

Uses standard-library arithmetic and decodes float64 NPY checkpoints directly.
Does not acquire images, run registration, refit thresholds, or infer clinical validity.
"""

import argparse
import ast
import hashlib
import json
import math
import statistics
import struct
import zipfile
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def close(actual, expected, label):
    require(
        actual == expected or math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label
    )


def quantile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    if ordered[lo] == ordered[hi]:
        return ordered[lo]
    return ordered[lo] + (position - lo) * (ordered[hi] - ordered[lo])


def npy_vector(data):
    require(data[:6] == b"\x93NUMPY", "invalid NPY magic")
    major = data[6]
    require(major in (1, 2), "unsupported NPY version")
    width = 2 if major == 1 else 4
    length = int.from_bytes(data[8 : 8 + width], "little")
    start = 8 + width + length
    header = ast.literal_eval(data[8 + width : start].decode("latin1").strip())
    require(header["descr"] == "<f8" and header["fortran_order"] is False, "checkpoint dtype/order")
    require(len(header["shape"]) == 1, "checkpoint vector shape")
    count = header["shape"][0]
    require(len(data) - start == count * 8, "checkpoint vector length")
    return list(struct.unpack("<" + "d" * count, data[start:]))


def main(root):
    def load(name):
        return json.loads((root / name).read_text())

    request = load("research/M6_PHASE_B_REQUEST.json")
    split = load("research/M6_SPLIT.json")
    frozen = load("research/M6_PHASE_B_INPUT_FREEZE.json")["evaluation"]
    seal = load("research/M6_PHASE_A_THRESHOLD_SEAL.json")
    aggregate_path = root / "outputs/m6_phase_b/m6_phase_b_evaluation.json"
    aggregate = json.loads(aggregate_path.read_text())
    pins = {
        "protocol": "docs/m6_calibration_protocol.md",
        "amendment": "docs/m6_calibration_protocol_amendment_1.md",
        "split": "research/M6_SPLIT.json",
        "input_freeze": "research/M6_PHASE_B_INPUT_FREEZE.json",
        "threshold_seal": "research/M6_PHASE_A_THRESHOLD_SEAL.json",
        "calibration_aggregate": (
            "results/m6_phase_a/outputs/m6_phase_a/m6_phase_a_calibration.json"
        ),
    }
    for name, path in pins.items():
        require(blob(root / path) == request["pinned_blobs"][name], "blob mismatch: " + name)
    require(
        digest(root / pins["calibration_aggregate"])
        == seal["aggregate_sha256"]
        == aggregate["calibration_aggregate_sha256"],
        "calibration identity",
    )
    require(
        blob(root / "research/M6_PHASE_B_REQUEST.json") == aggregate["request_blob_sha"],
        "request identity",
    )
    require(
        blob(root / pins["threshold_seal"]) == aggregate["threshold_seal_blob_sha"], "seal identity"
    )
    require(
        aggregate["source_git_sha"]
        == request["source_git_sha"]
        == "ee4034c58435ded3e2f9c283e38fa70d78f1d792",
        "implementation identity",
    )
    require(aggregate["source_ci_run_id"] == request["source_ci_run_id"], "CI identity")
    require(
        aggregate["status"] == "complete" and aggregate["evaluation_anatomies"] == 30,
        "incomplete aggregate",
    )
    require(
        aggregate["thresholds_refitted"] is False
        and aggregate["pooled_independent_point_inference_used"] is False,
        "scientific boundary",
    )
    manifest_paths = set()
    for name in ("m6_phase_b_evaluation.sha256", "m6_phase_b_shards.sha256"):
        for line in (root / "outputs/m6_phase_b" / name).read_text().splitlines():
            expected, relative = line.split(None, 1)
            path = root / relative.strip()
            require(path.resolve().is_relative_to(root.resolve()), "unsafe path")
            require(relative not in manifest_paths, "duplicate manifest path")
            require(digest(path) == expected, "manifest mismatch: " + relative)
            manifest_paths.add(relative)
    evaluation = {
        p: source for source, roles in split["roles"].items() for p in roles["evaluation"]
    }
    calibration = {p for roles in split["roles"].values() for p in roles["calibration"]}
    require(
        len(evaluation) == 30 and len(calibration) == 30 and not set(evaluation) & calibration,
        "split boundary",
    )
    records = {}
    checkpoint_count = 0
    for path in sorted((root / "phase-b-shards/shards").glob("*.json")):
        record = json.loads(path.read_text())
        patient = record["patient_id"]
        require(patient in evaluation and patient not in records, "unexpected/duplicate patient")
        require(
            record["source_key"] == evaluation[patient] and record["phase"] == "B",
            "patient source/phase",
        )
        for key in ("request_blob_sha", "source_git_sha", "threshold_seal_blob_sha"):
            require(record[key] == aggregate[key], "shard provenance: " + key)
        require(record["runtime_versions"] == request["runtime_versions"], "runtime drift")
        require(record["evaluation_accessed"] is True, "role mismatch")
        for key, value in frozen[patient].items():
            require(record[key] == value, "input/geometry identity: " + patient + "/" + key)
        require(
            len(record["forward_member_reasons"]) == len(record["reverse_member_reasons"]) == 9,
            "ensemble size",
        )
        require(
            record["primary_complete"] and all(x == "ok" for x in record["forward_member_reasons"]),
            "primary failure",
        )
        errors = record["known_error_mm"]
        require(
            len(errors) == 50 and all(math.isfinite(x) and x >= 0 for x in errors), "known errors"
        )
        with zipfile.ZipFile(
            root / "phase-b-shards/checkpoints" / (patient + ".npz")
        ) as checkpoint:
            for key, expected in record["hashes"].items():
                values = record[key]
                require(
                    npy_vector(checkpoint.read(key + ".npy")) == values,
                    "checkpoint mismatch: " + key,
                )
                if expected is None:
                    require(
                        key in ("ice_mm", "ice_scores")
                        and not record["ice_complete"]
                        and values == [],
                        "absent comparator",
                    )
                else:
                    header = json.dumps(
                        {"dtype": "<f8", "shape": [len(values)]}, sort_keys=True
                    ).encode()
                    actual = hashlib.sha256(
                        header + b"\0" + struct.pack("<" + "d" * len(values), *values)
                    ).hexdigest()
                    require(actual == expected, "vector hash: " + key)
            checkpoint_count += 1
        for method in ("sigma", "ice"):
            if method == "ice" and not record["ice_complete"]:
                require(bool(record["ice_failure"]), "missing failure reason")
                continue
            signals, scores = record[method + "_mm"], record[method + "_scores"]
            require(len(signals) == len(scores) == 50, "score length")
            for error, signal, score in zip(errors, signals, scores, strict=True):
                require(math.isfinite(signal) and signal >= 0, "invalid signal")
                require(
                    score == (error / signal if signal > 0 else (0 if error == 0 else math.inf)),
                    "score rule",
                )
        records[patient] = record
    require(set(records) == set(evaluation) == set(frozen), "cohort identity")
    expected_files = {"outputs/m6_phase_b/m6_phase_b_evaluation.json"}
    expected_files |= {f"phase-b-shards/shards/{p}.json" for p in records}
    require(manifest_paths == expected_files, "manifest scope")
    require(
        {p.stem for p in (root / "phase-b-shards/checkpoints").glob("*.npz")} == set(records),
        "checkpoint cohort",
    )
    require(aggregate["primary_failures"] == [], "primary failure reporting")
    ice_failures = sorted(p for p, r in records.items() if not r["ice_complete"])
    require(aggregate["ice_failures"] == ice_failures, "ICE failure reporting")
    verified = {}
    for source in split["roles"]:
        patients = sorted(p for p, s in evaluation.items() if s == source)
        require(
            len(patients) == 15 and aggregate["sources"][source]["patients"] == patients,
            "source cohort",
        )
        verified[source] = {}
        for method in ("sigma", "ice"):
            result = aggregate["sources"][source]["methods"][method]
            complete = all(
                records[p]["ice_complete" if method == "ice" else "primary_complete"]
                for p in patients
            )
            calibrated = complete and seal["thresholds"][source][method]["assessable"]
            require(
                result["evaluation_complete"] == complete
                and result["calibrated_assessable"] == calibrated,
                "assessability",
            )
            require(
                result["calibration_assessable"]
                == seal["thresholds"][source][method]["assessable"],
                "calibration assessability",
            )
            require(
                (
                    result["failures"] == [p for p in patients if p in ice_failures]
                    if method == "ice"
                    else result["failures"] == []
                ),
                "failure identities",
            )
            if not calibrated:
                require("levels" not in result, "invalid reduced-cohort claim")
            if not complete:
                require("uncalibrated_reference" not in result, "invalid reduced-cohort reference")
                verified[source][method] = {
                    "calibrated_assessable": False,
                    "evaluation_complete": False,
                }
                continue
            levels = {"uncalibrated": result["uncalibrated_reference"]}
            if calibrated:
                levels.update(result["levels"])
            summaries = {}
            for nominal, reported in levels.items():
                threshold = (
                    1.0
                    if nominal == "uncalibrated"
                    else seal["thresholds"][source][method]["thresholds"][nominal]
                )
                threshold = math.inf if threshold == "positive_infinity" else threshold
                require(reported["threshold"] == threshold, "threshold refit")
                coverages, medians = {}, []
                all_signals, all_scores, all_radii = [], [], []
                for patient in patients:
                    record = records[patient]
                    signals = record[method + "_mm"]
                    radii = [math.inf if math.isinf(threshold) else threshold * x for x in signals]
                    coverage = (
                        sum(e <= r for e, r in zip(record["known_error_mm"], radii, strict=True))
                        / 50
                    )
                    close(reported["per_anatomy_coverage"][patient], coverage, "patient coverage")
                    coverages[patient] = coverage
                    medians.append(statistics.median(radii))
                    all_signals.extend(signals)
                    all_scores.extend(record[method + "_scores"])
                    all_radii.extend(radii)
                mean = statistics.fmean(coverages.values())
                close(reported["equal_anatomy_mean_coverage"], mean, "source coverage")
                if nominal != "uncalibrated":
                    close(reported["coverage_gap"], mean - float(nominal), "coverage gap")
                efficiency = reported["radius_efficiency"]
                for actual, expected in zip(
                    efficiency["per_anatomy_median_radius_mm"], medians, strict=True
                ):
                    close(actual, expected, "median radius")
                close(
                    efficiency["median_of_anatomy_medians_mm"],
                    statistics.median(medians),
                    "source median",
                )
                for actual, expected in zip(
                    efficiency["iqr_of_anatomy_medians_mm"],
                    [quantile(medians, 0.25), quantile(medians, 0.75)],
                    strict=True,
                ):
                    close(actual, expected, "radius quartile")
                require(
                    efficiency["total_radius_count"] == 750
                    and efficiency["infinite_radius_count"]
                    == sum(math.isinf(x) for x in all_radii),
                    "radius counts",
                )
                for label, values, diagnostics in (
                    ("radius", all_radii, reported["radius_diagnostics"]),
                    ("signal", all_signals, result["signal_diagnostics"]),
                    ("score", all_scores, result["score_diagnostics"]),
                ):
                    require(diagnostics["count"] == 750, label + " count")
                    for field, count in (
                        ("zero_fraction", sum(x == 0 for x in values)),
                        ("infinite_fraction", sum(math.isinf(x) for x in values)),
                        (
                            "near_zero_positive_fraction",
                            sum(0 < x <= 2.220446049250313e-16 for x in values),
                        ),
                    ):
                        close(diagnostics[field], count / 750, label + "/" + field)
                summaries[nominal] = {
                    "coverage": mean,
                    "median_radius_mm": (
                        statistics.median(medians)
                        if math.isfinite(threshold)
                        else "positive_infinity"
                    ),
                    "minimum_anatomy_coverage": min(coverages.values()),
                    "maximum_anatomy_median_radius_mm": (
                        max(medians) if math.isfinite(threshold) else "positive_infinity"
                    ),
                }
            verified[source][method] = {
                "calibrated_assessable": calibrated,
                "evaluation_complete": complete,
                "levels": summaries,
            }
    require(
        aggregate["balanced_across_sources"]["ice"]["assessable"] is False, "balanced ICE claim"
    )
    for nominal in ("0.80", "0.90", "0.95"):
        expected = statistics.fmean(
            verified[s]["sigma"]["levels"][nominal]["coverage"] for s in verified
        )
        close(
            aggregate["balanced_across_sources"]["sigma"]["levels"][nominal][
                "equal_source_equal_anatomy_mean_coverage"
            ],
            expected,
            "balanced coverage",
        )
    return {
        "record": "independent-phase-b-evidence-verification",
        "schema_version": 1,
        "aggregate_sha256": digest(aggregate_path),
        "request_blob_sha": aggregate["request_blob_sha"],
        "manifest_entries_verified": len(manifest_paths),
        "frozen_blob_pins_verified": len(pins),
        "patient_shards_verified": len(records),
        "numerical_checkpoints_verified": checkpoint_count,
        "primary_failures": [],
        "ice_failures": ice_failures,
        "thresholds_refitted": False,
        "verified_sources": verified,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_root", type=Path)
    print(
        json.dumps(
            main(parser.parse_args().evidence_root), indent=2, sort_keys=True, allow_nan=False
        )
    )
