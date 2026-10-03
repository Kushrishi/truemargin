"""Independently verify retained Phase A evidence; no data acquisition or registration.

The order-statistic calculation uses only the standard library and the frozen
15 groups x 50 points design, independently of the project's HCP implementation.
"""

import argparse
import hashlib
import json
import math
import struct
from fractions import Fraction
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("evidence_root", type=Path)
root = parser.parse_args().evidence_root
aggregate_path = root / "outputs/m6_phase_a/m6_phase_a_calibration.json"
aggregate = json.loads(aggregate_path.read_text())
request_path = root / "research/M6_PHASE_A_REQUEST.json"
request = json.loads(request_path.read_text())
split = json.loads((root / "research/M6_SPLIT.json").read_text())
input_freeze = json.loads((root / "research/M6_PHASE_A_INPUT_FREEZE.json").read_text())[
    "calibration"
]
geometry_freeze = json.loads((root / "research/M6_PHASE_A_GEOMETRY_FREEZE.json").read_text())[
    "calibration"
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


require(
    digest(aggregate_path) == "66e926e68912ae2e4fa039f5b78194346f7dd638f32230aad0a629f135087e55",
    "accepted aggregate identity mismatch",
)
require(
    blob(request_path) == "e300105b98e23b593a7d2044d965f28630b48a34",
    "accepted request identity mismatch",
)
manifest_entries = 0
for name in ["m6_phase_a_calibration.sha256", "m6_phase_a_shards.sha256"]:
    for line in (root / "outputs/m6_phase_a" / name).read_text().splitlines():
        expected, relative = line.split(None, 1)
        path = root / relative.strip()
        require(path.resolve().is_relative_to(root.resolve()), "unsafe manifest path")
        require(digest(path) == expected, "manifest mismatch: " + relative)
        manifest_entries += 1
pins = {
    "protocol": "docs/m6_calibration_protocol.md",
    "amendment": "docs/m6_calibration_protocol_amendment_1.md",
    "split": "research/M6_SPLIT.json",
    "geometry_freeze": "research/M6_PHASE_A_GEOMETRY_FREEZE.json",
    "input_freeze": "research/M6_PHASE_A_INPUT_FREEZE.json",
}
for name, path in pins.items():
    require(blob(root / path) == request["pinned_blobs"][name], "frozen blob mismatch: " + name)
require(blob(request_path) == aggregate["request_blob_sha"], "request identity mismatch")
require(
    aggregate["source_git_sha"] == request["source_git_sha"], "implementation identity mismatch"
)
require(
    aggregate["status"] == "complete" and aggregate["primary_failures"] == [], "primary incomplete"
)
require(
    aggregate["calibration_anatomies"] == 30 and aggregate["evaluation_anatomies_accessed"] == 0,
    "cohort boundary mismatch",
)
require(aggregate["authorization_boundary"]["evaluation_accessed"] is False, "evaluation accessed")
calibration = {p: source for source, roles in split["roles"].items() for p in roles["calibration"]}
evaluation = {p for roles in split["roles"].values() for p in roles["evaluation"]}
records = {}
for path in sorted((root / "phase-a-shards/shards").glob("*.json")):
    record = json.loads(path.read_text())
    patient = record["patient_id"]
    require(patient not in records, "duplicate anatomy")
    require(patient in calibration and patient not in evaluation, "unexpected anatomy")
    require(record["source_key"] == calibration[patient], "source mismatch")
    require(
        record["evaluation_accessed"] is False and record["primary_complete"] is True,
        "anatomy boundary mismatch",
    )
    require(
        record["source_git_sha"] == aggregate["source_git_sha"]
        and record["request_blob_sha"] == aggregate["request_blob_sha"],
        "shard provenance mismatch",
    )
    for field, value in input_freeze[patient].items():
        require(record[field] == value, "input identity mismatch: " + patient + "/" + field)
    for field, value in geometry_freeze[patient].items():
        require(record[field] == value, "geometry identity mismatch")
    require(len(record["forward_member_reasons"]) == 9, "forward ensemble size mismatch")
    for field, expected in record["hashes"].items():
        values = record[field]
        if expected is None:
            require(
                field in ["ice_mm", "ice_scores"]
                and record["ice_complete"] is False
                and values == [],
                "invalid absent ICE hash",
            )
            continue
        header = json.dumps({"dtype": "<f8", "shape": [len(values)]}, sort_keys=True).encode()
        actual = hashlib.sha256(
            header + b"\0" + struct.pack("<" + "d" * len(values), *values)
        ).hexdigest()
        require(actual == expected, "array hash mismatch: " + patient + "/" + field)
    errors = record["known_error_mm"]
    require(
        len(errors) == 50 and all(math.isfinite(x) and x >= 0 for x in errors),
        "invalid known errors",
    )
    for method in ["sigma", "ice"]:
        if method == "ice" and not record["ice_complete"]:
            continue
        signals, scores = record[method + "_mm"], record[method + "_scores"]
        require(len(signals) == len(scores) == 50, "score group size mismatch")
        for error, signal, score in zip(errors, signals, scores, strict=True):
            require(math.isfinite(signal) and signal >= 0, "invalid signal")
            expected = error / signal if signal > 0 else (0.0 if error == 0 else math.inf)
            require(score == expected, "ratio score mismatch")
    records[patient] = record
require(
    set(records) == set(calibration) == set(input_freeze) == set(geometry_freeze),
    "incomplete frozen cohort",
)
verified = {}
for source in split["roles"]:
    patients = sorted(p for p, s in calibration.items() if s == source)
    require(len(patients) == 15, "source size mismatch")
    require(
        aggregate["sources"][source]["patients"] == patients, "aggregate source membership mismatch"
    )
    verified[source] = {}
    for method in ["sigma", "ice"]:
        assessable = all(
            records[p][method + "_complete" if method == "ice" else "primary_complete"]
            for p in patients
        )
        result = aggregate["sources"][source]["methods"][method]
        require(result["assessable"] == assessable, "method assessability mismatch")
        if not assessable:
            require("thresholds" not in result, "incomplete method has thresholds")
            verified[source][method] = {"assessable": False}
            continue
        ordered = sorted(x for p in patients for x in records[p][method + "_scores"])
        thresholds = {}
        for nominal in ["0.80", "0.90", "0.95"]:
            rank = math.ceil(Fraction(nominal) * 800)
            threshold = ordered[rank - 1] if rank <= 750 else math.inf
            require(result["thresholds"][nominal]["threshold"] == threshold, "threshold mismatch")
            thresholds[nominal] = threshold if math.isfinite(threshold) else "positive_infinity"
        verified[source][method] = {"assessable": True, "thresholds": thresholds}
report = {
    "schema_version": 1,
    "record": "independent-phase-a-evidence-verification",
    "manifest_entries_verified": manifest_entries,
    "patient_shards_verified": len(records),
    "frozen_blob_pins_verified": len(pins),
    "all_input_and_geometry_identities_match": True,
    "all_numeric_array_hashes_match": True,
    "all_complete_method_ratio_scores_match": True,
    "threshold_method": (
        "stdlib exact ranks 640,720,760 in 750 scores plus infinity mass; "
        "each finite score mass 1/800"
    ),
    "aggregate_sha256": digest(aggregate_path),
    "request_blob_sha": blob(request_path),
    "evaluation_anatomies_accessed": 0,
    "ice_failures": aggregate["ice_failures"],
    "verified_thresholds": verified,
}
print(json.dumps(report, indent=2, sort_keys=True))
