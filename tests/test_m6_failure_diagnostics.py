"""Replay descriptive diagnostics without permitting a changed primary record."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "failure_diagnostics", ROOT / "scripts/m6_failure_diagnostics.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_tied_ranks_and_constant_signal():
    assert analysis.ranks([3, 1, 1, 2]) == [4, 1.5, 1.5, 3]
    assert analysis.spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert analysis.spearman([1, 1, 1], [1, 2, 3]) is None


def test_retained_report_replays_exactly():
    retained = json.loads((ROOT / "results/m6_exploratory/failure_diagnostics.json").read_text())
    assert analysis.diagnose(ROOT) == retained
    diagnosis = retained["sources"]["prostate_diagnosis"]
    assert diagnosis["calibration_cutoff"]["tail_points_by_anatomy"] == {"ProstateDx-01-0082": 31}
    assert diagnosis["evaluation_radius_summary"]["primary_cohort_exclusions"] == 0
    assert len(diagnosis["calibration"]) == len(diagnosis["evaluation"]) == 15


def test_changed_primary_values_and_geometry_are_rejected():
    patient = "ProstateDx-01-0043"
    relative = f"results/m6_phase_b/phase-b-shards/shards/{patient}.json"
    record = json.loads((ROOT / relative).read_text())
    frozen = json.loads((ROOT / "research/M6_PHASE_B_INPUT_FREEZE.json").read_text())
    identity = frozen["evaluation"][patient]
    record["sigma_mm"][0] += 1
    with pytest.raises(ValueError, match="digest"):
        analysis.validate_record(record, patient, "prostate_diagnosis", "B", identity)
    record = json.loads((ROOT / relative).read_text())
    record["geometry_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="geometry"):
        analysis.validate_record(record, patient, "prostate_diagnosis", "B", identity)


def test_unequal_rank_vector_lengths_are_rejected():
    with pytest.raises(ValueError, match="equal"):
        analysis.spearman([1, 2], [1, 2, 3])
