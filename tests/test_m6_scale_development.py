"""Scale arithmetic and separation of fit/calibration/evaluation evidence."""

import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "scale_development", ROOT / "scripts/m6_scale_development.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_recovers_known_affine_scale():
    row = {"sigma_mm": [0.1, 0.3, 0.8], "known_error_mm": [2.3, 2.9, 4.4]}
    assert analysis.fit_affine([row]) == pytest.approx((2.0, 3.0))


def test_negative_slope_uses_nonnegative_boundary():
    row = {"sigma_mm": [1.0, 2.0, 3.0], "known_error_mm": [3.0, 2.0, 1.0]}
    assert analysis.fit_affine([row]) == pytest.approx((2.0, 0.0))


def test_hierarchical_infinity_atom_and_order_statistic():
    groups = [{"sigma_mm": [1.0] * 50, "known_error_mm": list(range(1, 51))}] * 10
    assert analysis.threshold(groups, lambda s: 1.0) == 50
    assert math.isinf(analysis.threshold(groups, lambda s: 1.0, "0.95"))
    with pytest.raises(ValueError, match="positive"):
        analysis.threshold(groups, lambda s: 0.0)


def test_evaluation_errors_cannot_change_fitted_models(tmp_path):
    for directory in ("research", "results/m6_phase_a", "results/m6_phase_b", "results/m5"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    before = analysis.develop(tmp_path)
    patient = before["sources"]["prostate_3t"]["models"]["constant"]["per_anatomy"][0]["patient_id"]
    path = tmp_path / f"results/m6_phase_b/phase-b-shards/shards/{patient}.json"
    row = json.loads(path.read_text())
    row["known_error_mm"] = [e + 100 for e in row["known_error_mm"]]
    row["sigma_scores"] = [
        e / s for e, s in zip(row["known_error_mm"], row["sigma_mm"], strict=True)
    ]
    for key in ("known_error_mm", "sigma_scores"):
        row["hashes"][key] = sys.modules["m6_failure_diagnostics"].vector_digest(row[key])
    path.write_text(json.dumps(row))
    after = analysis.develop(tmp_path)
    for source, result in before["sources"].items():
        other = after["sources"][source]
        for key in ("fit_ids", "calibration_ids", "affine_intercept_mm", "affine_slope"):
            assert result[key] == other[key]
        for name, model in result["models"].items():
            assert model["multiplier"] == other["models"][name]["multiplier"]
    assert (
        after["sources"]["prostate_3t"]["models"]["constant"]["equal_anatomy_coverage"]
        < before["sources"]["prostate_3t"]["models"]["constant"]["equal_anatomy_coverage"]
    )
