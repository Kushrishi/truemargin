"""Calibration-only scale validation checks."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "calibration_only",
    ROOT / "scripts/m6_calibration_only_scale_validation.py",
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_validation_uses_phase_a_without_phase_b(tmp_path):
    (tmp_path / "research").mkdir()
    shutil.copy(ROOT / "research/M6_SPLIT.json", tmp_path / "research/M6_SPLIT.json")
    shutil.copytree(ROOT / "results/m6_phase_a", tmp_path / "results/m6_phase_a")

    result = analysis.validate(tmp_path)
    assert result["phase_b_accessed"] is False
    assert result["accepted_m6_results_changed"] is False


def test_fold_partitions_are_complete_and_disjoint():
    result = analysis.validate(ROOT)
    for source in result["sources"].values():
        assert len(source["folds"]) == 15
        for fold in source["folds"]:
            groups = [
                {fold["holdout_id"]},
                set(fold["fit_ids"]),
                set(fold["multiplier_ids"]),
            ]
            assert [len(group) for group in groups] == [1, 4, 10]
            assert not (groups[0] & groups[1])
            assert not (groups[0] & groups[2])
            assert not (groups[1] & groups[2])
            assert len(set.union(*groups)) == 15


def test_retained_phase_a_development_summary():
    result = analysis.validate(ROOT)

    three_t = result["sources"]["prostate_3t"]["summary"]
    assert three_t["constant"]["mean_coverage"] == pytest.approx(0.968)
    assert three_t["constant"]["mean_radius_mm"] == pytest.approx(2.3059972152)
    assert three_t["affine"]["mean_coverage"] == pytest.approx(0.98)
    assert three_t["affine"]["mean_radius_mm"] == pytest.approx(2.6643541259)
    assert three_t["spread"]["mean_radius_mm"] == pytest.approx(5.4493170612)
    assert three_t["ice"]["assessable_folds"] == 0

    diagnosis = result["sources"]["prostate_diagnosis"]["summary"]
    assert diagnosis["constant"]["mean_coverage"] == pytest.approx(0.9893333333)
    assert diagnosis["constant"]["mean_radius_mm"] == pytest.approx(4.0137748307)
    assert diagnosis["affine"]["mean_coverage"] == pytest.approx(0.9546666667)
    assert diagnosis["affine"]["mean_radius_mm"] == pytest.approx(3.1529053226)
    assert diagnosis["spread"]["mean_radius_mm"] == pytest.approx(9.0017307304)
    assert diagnosis["ice"]["assessable_folds"] == 15
    assert diagnosis["ice"]["mean_coverage"] == pytest.approx(0.9866666667)
