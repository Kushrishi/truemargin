import numpy as np
import pytest

from truemargin import provenance

TEST_SHA_A = "a" * 40
TEST_SHA_B = "b" * 40


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git" / "refs" / "heads").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (repo / ".git" / "refs" / "heads" / "main").write_text(f"{TEST_SHA_A}\n", encoding="utf-8")
    (repo / "producer.py").write_text("VALUE = 1\n", encoding="utf-8")
    return repo


def _manifest(repo, *, jitter: float = 0.02) -> dict:
    return provenance.build_manifest(
        repo_root=repo,
        experiment="unit-test",
        artifact_id="case-01",
        parameters={"jitter": jitter, "ensemble_n": 5},
        data_identity={"patient": "aaa0001", "series": "12345"},
        source_files=["producer.py"],
    )


def test_current_git_sha_reads_mounted_git_directory(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    assert provenance.current_git_sha(repo) == TEST_SHA_A


def test_current_git_sha_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("TRUEMARGIN_GIT_SHA", TEST_SHA_B)
    assert provenance.current_git_sha(repo) == TEST_SHA_B


def test_matching_checkpoint_round_trip(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _make_repo(tmp_path)
    manifest = _manifest(repo)
    path = tmp_path / "case.npz"
    expected_err = np.array([1.0, 2.0])
    expected_sigma = np.array([0.1, 0.2])

    provenance.save_checkpoint(
        path,
        arrays={"err": expected_err, "sigma": expected_sigma},
        manifest=manifest,
    )
    output = capsys.readouterr().out
    assert "experiment=unit-test" in output
    assert "artifact=case-01" in output
    assert f"git_sha={TEST_SHA_A}" in output
    assert f"config_hash={manifest['config_hash']}" in output
    assert f"code_hash={manifest['code_hash']}" in output

    loaded = provenance.load_checkpoint(path, expected_manifest=manifest)
    np.testing.assert_array_equal(loaded["err"], expected_err)
    np.testing.assert_array_equal(loaded["sigma"], expected_sigma)


def test_legacy_checkpoint_without_manifest_is_rejected(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    path = tmp_path / "legacy.npz"
    np.savez(path, err=np.array([1.0]), sigma=np.array([0.1]))

    with pytest.raises(provenance.CheckpointProvenanceError, match="Legacy checkpoint"):
        provenance.load_checkpoint(path, expected_manifest=_manifest(repo))


def test_parameter_mismatch_is_rejected(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    path = tmp_path / "case.npz"
    provenance.save_checkpoint(
        path,
        arrays={"err": np.array([1.0]), "sigma": np.array([0.1])},
        manifest=_manifest(repo, jitter=0.02),
    )

    with pytest.raises(provenance.CheckpointProvenanceError, match="provenance mismatch"):
        provenance.load_checkpoint(path, expected_manifest=_manifest(repo, jitter=0.2))


def test_result_defining_code_change_is_rejected(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    path = tmp_path / "case.npz"
    original = _manifest(repo)
    provenance.save_checkpoint(
        path,
        arrays={"err": np.array([1.0]), "sigma": np.array([0.1])},
        manifest=original,
    )

    (repo / "producer.py").write_text("VALUE = 2\n", encoding="utf-8")
    changed = _manifest(repo)
    with pytest.raises(provenance.CheckpointProvenanceError, match="provenance mismatch"):
        provenance.load_checkpoint(path, expected_manifest=changed)


def test_git_sha_change_alone_does_not_invalidate_identical_code(tmp_path) -> None:
    repo = _make_repo(tmp_path)
    path = tmp_path / "case.npz"
    original = _manifest(repo)
    provenance.save_checkpoint(
        path,
        arrays={"err": np.array([1.0]), "sigma": np.array([0.1])},
        manifest=original,
    )

    (repo / ".git" / "refs" / "heads" / "main").write_text(f"{TEST_SHA_B}\n", encoding="utf-8")
    later_commit_same_code = _manifest(repo)
    loaded = provenance.load_checkpoint(path, expected_manifest=later_commit_same_code)
    np.testing.assert_array_equal(loaded["err"], np.array([1.0]))
