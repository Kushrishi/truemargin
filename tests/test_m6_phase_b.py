"""Pre-result tests use synthetic vectors only; never load evaluation images."""

from __future__ import annotations

import ast
import copy
import json
import runpy
from pathlib import Path

import numpy as np
import pytest

from truemargin.hierarchical_conformal import ratio_nonconformity
from truemargin.m6_phase_a import array_sha256, git_blob_sha
from truemargin.m6_phase_b import (
    aggregate_records,
    evaluation_cohort,
    load_evaluation_freeze,
    load_seal,
    verify_request,
)

ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "research/M6_PHASE_A_THRESHOLD_SEAL.json"
AGGREGATE = ROOT / "results/m6_phase_a/outputs/m6_phase_a/m6_phase_a_calibration.json"
FREEZE = ROOT / "research/M6_PHASE_B_INPUT_FREEZE.json"
SPLIT = ROOT / "research/M6_SPLIT.json"


@pytest.fixture
def fixture():
    cohort = evaluation_cohort(SPLIT)
    freeze = load_evaluation_freeze(FREEZE, cohort)
    seal = load_seal(SEAL, AGGREGATE)
    records = {}
    for patient, source in cohort.items():
        errors = np.arange(50, dtype=np.float64)
        sigma = np.ones(50)
        ice = np.ones(50)
        vectors = {
            "known_error_mm": errors,
            "sigma_mm": sigma,
            "ice_mm": ice,
            "sigma_scores": ratio_nonconformity(errors, sigma),
            "ice_scores": ratio_nonconformity(errors, ice),
        }
        records[patient] = {
            "patient_id": patient,
            "source_key": source,
            **freeze[patient],
            "phase": "B",
            "evaluation_accessed": True,
            "source_git_sha": "f" * 40,
            "request_blob_sha": "r",
            "threshold_seal_blob_sha": "s",
            "primary_complete": True,
            "ice_complete": True,
            "ice_failure": "",
            "forward_member_reasons": ["ok"] * 9,
            "reverse_member_reasons": ["ok"] * 9,
            **{key: value.tolist() for key, value in vectors.items()},
            "hashes": {key: array_sha256(value) for key, value in vectors.items()},
        }
    return records, cohort, freeze, seal


def aggregate(fixture):
    records, cohort, freeze, seal = fixture
    return aggregate_records(
        records,
        cohort,
        freeze,
        seal,
        source_git_sha="f" * 40,
        request_blob_sha="r",
        threshold_seal_blob_sha="s",
    )


def test_source_coverage_uses_exact_sealed_thresholds_and_retains_unavailable_ice(fixture):
    result = aggregate(fixture)
    sigma3t = result["sources"]["prostate_3t"]["methods"]["sigma"]
    sigmadx = result["sources"]["prostate_diagnosis"]["methods"]["sigma"]
    assert sigma3t["levels"]["0.90"]["equal_anatomy_mean_coverage"] == pytest.approx(0.84)
    assert sigmadx["levels"]["0.90"]["equal_anatomy_mean_coverage"] == 1.0
    assert sigma3t["levels"]["0.90"]["coverage_gap"] == pytest.approx(-0.06)
    assert result["balanced_across_sources"]["sigma"]["levels"]["0.90"][
        "equal_source_equal_anatomy_mean_coverage"
    ] == pytest.approx(0.92)
    ice3t = result["sources"]["prostate_3t"]["methods"]["ice"]
    assert ice3t["evaluation_complete"] and not ice3t["calibrated_assessable"]
    assert "levels" not in ice3t and "uncalibrated_reference" in ice3t
    assert result["balanced_across_sources"]["ice"] == {"assessable": False}
    assert len(sigma3t["levels"]["0.90"]["per_anatomy_coverage"]) == 15
    assert result["thresholds_refitted"] is False


def test_zero_signal_and_infinity_sentinel_are_not_floored(fixture):
    row = next(iter(fixture[0].values()))
    row["sigma_mm"][1] = 0.0
    row["sigma_scores"] = ratio_nonconformity(
        np.array(row["known_error_mm"]), np.array(row["sigma_mm"])
    ).tolist()
    for key in ("sigma_mm", "sigma_scores"):
        row["hashes"][key] = array_sha256(np.array(row[key]))
    result = aggregate(fixture)
    sigma = result["sources"][row["source_key"]]["methods"]["sigma"]
    assert sigma["levels"]["0.95"]["equal_anatomy_mean_coverage"] == 1.0
    assert sigma["levels"]["0.95"]["radius_diagnostics"]["infinite_fraction"] == 1.0
    assert sigma["score_diagnostics"]["infinite_fraction"] > 0
    assert sigma["signal_diagnostics"]["zero_fraction"] > 0


def test_failed_primary_anatomy_is_retained_and_source_is_not_reduced(fixture):
    row = next(iter(fixture[0].values()))
    row.update(primary_complete=False, ice_complete=False, failure="forward ensemble incomplete")
    result = aggregate(fixture)
    assert result["status"] == "primary-incomplete"
    assert row["patient_id"] in result["primary_failures"]
    assert not result["sources"][row["source_key"]]["methods"]["sigma"]["calibrated_assessable"]
    assert not result["balanced_across_sources"]["sigma"]["assessable"]


def test_failed_secondary_anatomy_does_not_change_primary(fixture):
    row = next(row for row in fixture[0].values() if row["source_key"] == "prostate_diagnosis")
    row.update(ice_complete=False, ice_failure="reverse failure", ice_mm=[], ice_scores=[])
    row["hashes"].update(ice_mm=None, ice_scores=None)
    result = aggregate(fixture)
    assert result["status"] == "complete"
    assert result["sources"]["prostate_diagnosis"]["methods"]["sigma"]["calibrated_assessable"]
    assert not result["sources"]["prostate_diagnosis"]["methods"]["ice"]["calibrated_assessable"]


@pytest.mark.parametrize("fault", ["partial", "calibration_patient", "hash", "request", "geometry"])
def test_incomplete_or_altered_shards_rejected(fixture, fault):
    patient = next(iter(fixture[0]))
    row = fixture[0][patient]
    if fault == "partial":
        fixture[0].pop(patient)
    elif fault == "calibration_patient":
        fixture[0]["unauthorized-calibration-anatomy"] = fixture[0].pop(patient)
    elif fault == "hash":
        row["hashes"]["sigma_mm"] = "0" * 64
    elif fault == "request":
        row["request_blob_sha"] = "other"
    else:
        row["geometry_sha256"] = "0" * 64
    with pytest.raises(RuntimeError):
        aggregate(fixture)


def test_modified_seal_rejected(tmp_path):
    seal = json.loads(SEAL.read_text())
    seal["thresholds"]["prostate_3t"]["sigma"]["thresholds"]["0.90"] += 1
    altered = tmp_path / "seal.json"
    altered.write_text(json.dumps(seal))
    with pytest.raises(RuntimeError, match="differs"):
        load_seal(altered, AGGREGATE)


def test_no_request_blocks_patient_and_transport_before_side_effects(monkeypatch, tmp_path):
    phase = runpy.run_path(str(ROOT / "scripts/m6_phase_b_evaluation.py"))
    phase["run_patient"].__globals__["REQUEST_PATH"] = tmp_path / "absent-request.json"
    with pytest.raises(RuntimeError, match="absent"):
        phase["run_patient"]("not-authorized", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_calibration_anatomy_rejected_even_with_mocked_authorization(monkeypatch, tmp_path):
    phase = runpy.run_path(str(ROOT / "scripts/m6_phase_b_evaluation.py"))
    phase["run_patient"].__globals__["verify_execution_authorization"] = lambda: {}
    calibration = json.loads(SPLIT.read_text())["roles"]["prostate_3t"]["calibration"][0]
    with pytest.raises(RuntimeError, match="not authorized"):
        phase["run_patient"](calibration, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_missing_cache_fails_before_decoding(monkeypatch, tmp_path):
    phase = runpy.run_path(str(ROOT / "scripts/m6_phase_b_evaluation.py"))
    monkeypatch.delenv("M6_EVALUATION_DICOM_CACHE", raising=False)
    monkeypatch.delenv("M6_EVALUATION_LABEL_ARCHIVE", raising=False)
    patient = next(iter(evaluation_cohort(SPLIT)))
    series = load_evaluation_freeze(FREEZE, evaluation_cohort(SPLIT))[patient]["series_uid"]
    with pytest.raises(RuntimeError, match="requires verified"):
        phase["load_exact_input"](patient, series, tmp_path)


def test_transport_entrypoints_stop_before_download_without_request(monkeypatch, tmp_path):
    import importlib
    import sys

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    phase = importlib.import_module("m6_phase_b_evaluation")
    monkeypatch.setattr(phase, "REQUEST_PATH", tmp_path / "absent.json")
    for filename, arguments in (
        ("stage_m6_phase_b_labels.py", ["--output", str(tmp_path / "labels")]),
        ("recover_m6_phase_b_inputs.py", ["--output-dir", str(tmp_path / "images")]),
    ):
        script = runpy.run_path(str(ROOT / "scripts" / filename))
        monkeypatch.setattr(sys, "argv", [filename, *arguments])
        with pytest.raises(RuntimeError, match="absent"):
            script["main"]()
    assert list(tmp_path.iterdir()) == []


def test_patient_runner_retains_checkpoint_and_provenance_with_synthetic_inputs(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    phase = runpy.run_path(str(ROOT / "scripts/m6_phase_b_evaluation.py"))
    namespace = phase["run_patient"].__globals__
    cohort = evaluation_cohort(SPLIT)
    patient = next(iter(cohort))
    row = load_evaluation_freeze(FREEZE, cohort)[patient]
    request_path = tmp_path / "request.json"
    request_path.write_text("{}")
    monkeypatch.setitem(namespace, "REQUEST_PATH", request_path)
    monkeypatch.setitem(
        namespace, "verify_execution_authorization", lambda: {"source_git_sha": "f" * 40}
    )
    monkeypatch.setitem(
        namespace,
        "load_exact_input",
        lambda *args: (None, None, row["dicom_zip_sha256"], row["label_sha256"]),
    )
    case = {
        "fixed": np.zeros((4, 4, 4)),
        "moving": np.zeros((4, 4, 4)),
        "spacing": (1.0, 1.0, 1.0),
        "idx_zyx": np.zeros((50, 3), dtype=np.int64),
        "u_true": np.zeros((3, 50)),
        "crop_diagonal_mm": 10.0,
    }
    monkeypatch.setitem(
        namespace, "build_synthetic_case", lambda *args: (case, row["geometry_sha256"])
    )
    ensemble = SimpleNamespace(
        complete=True,
        u_mean=np.zeros((3, 4, 4, 4)),
        sigma=np.ones((4, 4, 4)),
        member_reasons=["ok"] * 9,
    )
    calls = []

    def run_ensemble(*args, **kwargs):
        calls.append(kwargs)
        return ensemble

    monkeypatch.setattr(namespace["hyper"], "run_hyperparameter_ensemble", run_ensemble)
    monkeypatch.setattr(
        namespace["comparators"], "inverse_consistency_scores", lambda *args: np.ones(50)
    )
    path = phase["run_patient"](patient, tmp_path / "outputs")
    result = json.loads(path.read_text())
    assert result["phase"] == "B" and result["evaluation_accessed"] is True
    assert result["primary_complete"] and result["ice_complete"]
    assert result["request_blob_sha"] == git_blob_sha(request_path)
    assert result["threshold_seal_blob_sha"] == git_blob_sha(SEAL)
    assert len(calls) == 2
    assert all(call == {"spacing": (1.0, 1.0, 1.0), "crop_diagonal_mm": 10.0} for call in calls)
    assert (tmp_path / "outputs/checkpoints" / f"{patient}.npz").is_file()


def test_core_estimator_and_comparator_operations_unchanged_from_phase_a():
    def operations(filename):
        tree = ast.parse((ROOT / "scripts" / filename).read_text())
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_patient"
        )
        start = next(
            i
            for i, node in enumerate(function.body)
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "fixed"
        )
        end = next(
            i
            for i, node in enumerate(function.body)
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "savez_compressed"
        )
        nodes = copy.deepcopy(function.body[start:end])
        # Only failure provenance bookkeeping was added; computation stays exact.
        for node in nodes:
            if isinstance(node, ast.If):
                node.body = [
                    entry
                    for entry in node.body
                    if not (
                        isinstance(entry, ast.Expr)
                        and isinstance(entry.value, ast.Call)
                        and isinstance(entry.value.func, ast.Attribute)
                        and entry.value.func.attr == "update"
                    )
                ]
        return ast.dump(ast.Module(body=nodes, type_ignores=[]))

    assert operations("m6_phase_a_calibration.py") == operations("m6_phase_b_evaluation.py")


def test_request_rejects_refitting_and_changed_pins(monkeypatch, tmp_path):
    from truemargin import m6_phase_b

    monkeypatch.setattr(m6_phase_b, "verify_source_files", lambda *args: None)
    phase = runpy.run_path(str(ROOT / "scripts/m6_phase_b_evaluation.py"))
    pins = phase["PINNED_PATHS"]
    request = {
        "schema_version": 1,
        "milestone": "M6",
        "authorized_mode": "phase-b-evaluation-only",
        "result_bearing_authorized": True,
        "evaluation_authorized": True,
        "calibration_fit_authorized": False,
        "calibration_anatomies_authorized": 0,
        "evaluation_anatomies_authorized": 30,
        "forward_registrations_planned": 270,
        "reverse_registrations_planned": 270,
        "points_per_anatomy": 50,
        "primary_signal": "sigma_mm",
        "secondary_signal": "ice_mm",
        "nominal_coverages": [0.8, 0.9, 0.95],
        "threshold_changes_authorized": False,
        "source_git_sha": "f" * 40,
        "source_ci_run_id": 1,
        "source_ci_conclusion": "success",
        "pinned_blobs": {key: git_blob_sha(path) for key, path in pins.items()},
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    kwargs = {
        "repo_root": ROOT,
        "request_path": path,
        "result_defining_paths": (),
        "pinned_paths": pins,
    }
    assert verify_request(**kwargs) == request
    request["calibration_fit_authorized"] = True
    path.write_text(json.dumps(request))
    with pytest.raises(RuntimeError, match="calibration_fit"):
        verify_request(**kwargs)
    request["calibration_fit_authorized"] = False
    request["pinned_blobs"]["threshold_seal"] = "0" * 40
    path.write_text(json.dumps(request))
    with pytest.raises(RuntimeError, match="threshold_seal"):
        verify_request(**kwargs)
