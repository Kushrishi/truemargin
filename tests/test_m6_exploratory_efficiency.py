"""Check exploratory baseline fitting cannot consume evaluation errors."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "exploratory_efficiency", ROOT / "scripts/m6_exploratory_efficiency.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_evaluation_error_changes_do_not_change_fitted_baseline(tmp_path):
    for relative in (
        "research/M6_SPLIT.json",
        "research/M6_PHASE_A_THRESHOLD_SEAL.json",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    for relative in (
        "results/m6_phase_a/phase-a-shards/shards",
        "results/m6_phase_b/phase-b-shards/shards",
    ):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    before = analysis.analyze(tmp_path)
    path = tmp_path / "results/m6_phase_b/phase-b-shards/shards/Prostate3T-01-0001.json"
    row = json.loads(path.read_text())
    row["known_error_mm"] = [1000.0] * 50
    path.write_text(json.dumps(row))
    after = analysis.analyze(tmp_path)
    for source, levels in before["sources"].items():
        for nominal, result in levels.items():
            assert (
                after["sources"][source][nominal]["constant_threshold_mm"]
                == result["constant_threshold_mm"]
            )
            assert (
                after["sources"][source][nominal]["sealed_sigma_multiplier"]
                == result["sealed_sigma_multiplier"]
            )
    assert (
        after["sources"]["prostate_3t"]["0.90"]["constant_equal_anatomy_coverage"]
        < before["sources"]["prostate_3t"]["0.90"]["constant_equal_anatomy_coverage"]
    )


def test_incomplete_calibration_groups_are_rejected():
    with pytest.raises(ValueError, match="unchanged"):
        analysis.constant_threshold([[1.0] * 50] * 14, "0.90")
