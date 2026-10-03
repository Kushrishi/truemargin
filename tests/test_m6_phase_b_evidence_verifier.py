"""The result audit must reject altered evidence even with rewritten manifests."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "phase_b_verifier", ROOT / "scripts/verify_m6_phase_b_result.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


@pytest.fixture
def evidence(tmp_path):
    destination = tmp_path / "evidence"
    shutil.copytree(ROOT / "results/m6_phase_b", destination)
    return destination


def rewrite_aggregate(root, mutate):
    path = root / "outputs/m6_phase_b/m6_phase_b_evaluation.json"
    value = json.loads(path.read_text())
    mutate(value)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    (root / "outputs/m6_phase_b/m6_phase_b_evaluation.sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest()
        + "  outputs/m6_phase_b/m6_phase_b_evaluation.json\n"
    )


def test_retained_evidence_passes(evidence):
    report = verifier.main(evidence)
    assert report["patient_shards_verified"] == 30
    assert report["numerical_checkpoints_verified"] == 30
    assert report["ice_failures"] == ["ProstateDx-01-0043"]


def test_coverage_tamper_with_new_manifest_is_rejected(evidence):
    def mutate(value):
        level = value["sources"]["prostate_3t"]["methods"]["sigma"]["levels"]["0.90"]
        level["equal_anatomy_mean_coverage"] = 0.9

    rewrite_aggregate(evidence, mutate)
    with pytest.raises(ValueError, match="source coverage"):
        verifier.main(evidence)


def test_threshold_refit_with_new_manifest_is_rejected(evidence):
    def mutate(value):
        value["sources"]["prostate_3t"]["methods"]["sigma"]["levels"]["0.90"]["threshold"] = 40.0

    rewrite_aggregate(evidence, mutate)
    with pytest.raises(ValueError, match="threshold refit"):
        verifier.main(evidence)


def test_missing_checkpoint_is_rejected(evidence):
    (evidence / "phase-b-shards/checkpoints/Prostate3T-01-0001.npz").unlink()
    with pytest.raises(FileNotFoundError):
        verifier.main(evidence)
