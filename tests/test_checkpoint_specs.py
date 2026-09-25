from truemargin import checkpoint_specs as ckptspec

TEST_SHA = "a" * 40


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git" / "refs" / "heads").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (repo / ".git" / "refs" / "heads" / "main").write_text(f"{TEST_SHA}\n", encoding="utf-8")

    for relative_path in [
        "scripts/04_tcia_case_calibration.py",
        "scripts/15_ensemble_perturbation_sensitivity.py",
        "src/truemargin/registration.py",
        "src/truemargin/ensemble.py",
        "src/truemargin/io_utils.py",
        "src/truemargin/calibration.py",
    ]:
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative_path}\n", encoding="utf-8")
    return repo


def _manifest(repo, *, perturbation: str, scale: float) -> dict:
    reg_cfg = {"ensemble_n": 5, "ensemble_jitter": 0.02, "seed": 0}
    mode_cfg = {"mesh_size": 3, "max_iterations": 15}
    return ckptspec.ensemble_patient_manifest(
        repo_root=repo,
        patient="aaa0054",
        t2_series="t2-series",
        dce_series="dce-series",
        mode="fast_dev",
        mode_cfg=mode_cfg,
        reg_cfg=reg_cfg,
        max_landmarks=75,
        perturbation=perturbation,
        perturbation_scale=scale,
    )


def _sensitivity_manifest(repo, *, perturbation: str, scale: float) -> dict:
    return ckptspec.ensemble_sensitivity_manifest(
        repo_root=repo,
        patient="aaa0054",
        t2_series="t2-series",
        dce_series="dce-series",
        mode_cfg={"mesh_size": 3, "max_iterations": 15},
        seed=0,
        max_landmarks=75,
        ensemble_n=5,
        perturbation=perturbation,
        perturbation_scale=scale,
        near_zero_sigma=1e-6,
    )


def test_ensemble_manifest_records_strategy_and_scale(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    absolute = _manifest(repo, perturbation="absolute_intensity", scale=0.02)
    relative = _manifest(repo, perturbation="relative_std", scale=0.02)

    assert absolute["parameters"]["ensemble_perturbation"] == "absolute_intensity"
    assert absolute["parameters"]["ensemble_perturbation_scale"] == 0.02
    assert relative["parameters"]["ensemble_perturbation"] == "relative_std"
    assert relative["parameters"]["ensemble_perturbation_scale"] == 0.02
    assert absolute["config_hash"] != relative["config_hash"]


def test_only_relative_manifest_fingerprints_corrected_ensemble_code(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    absolute_before = _manifest(repo, perturbation="absolute_intensity", scale=0.02)
    relative_before = _manifest(repo, perturbation="relative_std", scale=0.02)

    ensemble_path = repo / "src/truemargin/ensemble.py"
    ensemble_path.write_text("# corrected ensemble implementation changed\n", encoding="utf-8")

    absolute_after = _manifest(repo, perturbation="absolute_intensity", scale=0.02)
    relative_after = _manifest(repo, perturbation="relative_std", scale=0.02)

    assert absolute_before["code_hash"] == absolute_after["code_hash"]
    assert relative_before["code_hash"] != relative_after["code_hash"]


def test_sensitivity_manifest_separates_perturbation_settings(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    alpha_zero = _sensitivity_manifest(repo, perturbation="relative_std", scale=0.0)
    alpha_two = _sensitivity_manifest(repo, perturbation="relative_std", scale=0.02)
    legacy = _sensitivity_manifest(repo, perturbation="absolute_intensity", scale=0.02)

    assert alpha_zero["experiment"] == "real-prostate-ensemble-sensitivity-v1"
    assert alpha_zero["artifact_id"] != alpha_two["artifact_id"]
    assert alpha_two["artifact_id"] != legacy["artifact_id"]
    assert len({alpha_zero["config_hash"], alpha_two["config_hash"], legacy["config_hash"]}) == 3


def test_sensitivity_manifest_fingerprints_runner_code(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    before = _sensitivity_manifest(repo, perturbation="relative_std", scale=0.02)

    runner = repo / "scripts/15_ensemble_perturbation_sensitivity.py"
    runner.write_text("# sensitivity analysis changed\n", encoding="utf-8")
    after = _sensitivity_manifest(repo, perturbation="relative_std", scale=0.02)

    assert before["code_hash"] != after["code_hash"]
