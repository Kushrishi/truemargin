"""Checkpoint provenance helpers for result-defining experiment artifacts.

TrueMargin has had several result-changing fixes. A checkpoint is therefore safe to
reuse only when it can prove which code, configuration, and data identity produced it.
This module keeps that contract deliberately small: manifests are JSON, embedded inside
the existing ``.npz`` checkpoint, and validated before any arrays are returned.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from truemargin import __version__

SCHEMA_VERSION = 1
PROVENANCE_KEY = "__truemargin_provenance__"


class CheckpointProvenanceError(RuntimeError):
    """Raised when a checkpoint cannot prove that it matches the requested run."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_git_dir(repo_root: Path) -> Path:
    git_entry = repo_root / ".git"
    if git_entry.is_dir():
        return git_entry
    if git_entry.is_file():
        text = git_entry.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if not text.lower().startswith(prefix):
            raise CheckpointProvenanceError(f"Unrecognized .git file format at {git_entry}")
        git_dir = Path(text[len(prefix) :].strip())
        if not git_dir.is_absolute():
            git_dir = (repo_root / git_dir).resolve()
        return git_dir
    raise CheckpointProvenanceError(
        f"Cannot determine Git SHA: {git_entry} is unavailable. "
        "When running through Docker Compose, mount the repository .git directory read-only; "
        "otherwise set TRUEMARGIN_GIT_SHA to the exact 40-character commit SHA."
    )


def current_git_sha(repo_root: str | os.PathLike[str]) -> str:
    """Return the exact repository commit SHA without requiring a ``git`` executable."""
    env_sha = os.environ.get("TRUEMARGIN_GIT_SHA", "").strip().lower()
    if env_sha:
        if len(env_sha) != 40 or any(c not in "0123456789abcdef" for c in env_sha):
            raise CheckpointProvenanceError(
                "TRUEMARGIN_GIT_SHA must be an exact 40-character hexadecimal commit SHA."
            )
        return env_sha

    root = Path(repo_root).resolve()
    git_dir = _resolve_git_dir(root)
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        sha = head.lower()
    else:
        ref_name = head.split(":", 1)[1].strip()
        loose_ref = git_dir / ref_name
        if loose_ref.exists():
            sha = loose_ref.read_text(encoding="utf-8").strip().lower()
        else:
            packed_refs = git_dir / "packed-refs"
            sha = ""
            if packed_refs.exists():
                for line in packed_refs.read_text(encoding="utf-8").splitlines():
                    if not line or line.startswith("#") or line.startswith("^"):
                        continue
                    candidate_sha, candidate_ref = line.split(" ", 1)
                    if candidate_ref.strip() == ref_name:
                        sha = candidate_sha.strip().lower()
                        break
            if not sha:
                raise CheckpointProvenanceError(
                    f"Cannot resolve Git ref {ref_name!r} under {git_dir}."
                )

    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise CheckpointProvenanceError(f"Resolved invalid Git SHA {sha!r} from {git_dir}")
    return sha


def build_manifest(
    *,
    repo_root: str | os.PathLike[str],
    experiment: str,
    artifact_id: str,
    parameters: Mapping[str, Any],
    data_identity: Mapping[str, Any],
    source_files: list[str],
) -> dict[str, Any]:
    """Build a deterministic manifest for one checkpoint.

    ``source_files`` should contain only result-defining code for the producer. Their
    content hashes, rather than the repository SHA alone, determine compatibility. This
    allows a documentation-only commit to reuse a scientifically identical checkpoint
    while still recording the exact Git SHA that originally produced it.
    """
    root = Path(repo_root).resolve()
    source_hashes: dict[str, str] = {}
    for rel_path in sorted(source_files):
        path = root / rel_path
        if not path.is_file():
            raise CheckpointProvenanceError(
                f"Cannot fingerprint result-defining source file {rel_path!r}: {path} is missing."
            )
        source_hashes[rel_path] = _sha256_file(path)

    parameters_dict = dict(parameters)
    data_identity_dict = dict(data_identity)
    return {
        "schema_version": SCHEMA_VERSION,
        "project_version": __version__,
        "git_sha": current_git_sha(root),
        "experiment": experiment,
        "artifact_id": artifact_id,
        "parameters": parameters_dict,
        "data_identity": data_identity_dict,
        "config_hash": _sha256_json(parameters_dict),
        "source_files": source_hashes,
        "code_hash": _sha256_json(source_hashes),
    }


def _compatibility_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    # git_sha is recorded for provenance but is intentionally not itself a compatibility
    # key: the source-file hashes above detect scientific code changes directly, while a
    # README/paper-only commit should not force an expensive recomputation.
    return {k: v for k, v in manifest.items() if k != "git_sha"}


def _decode_manifest(checkpoint_path: Path, raw_manifest: np.ndarray) -> dict[str, Any]:
    try:
        decoded = json.loads(str(raw_manifest.item()))
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        raise CheckpointProvenanceError(
            f"Checkpoint {checkpoint_path} contains unreadable provenance metadata."
        ) from e
    if not isinstance(decoded, dict):
        raise CheckpointProvenanceError(
            f"Checkpoint {checkpoint_path} provenance must decode to a JSON object."
        )
    return decoded


def read_checkpoint_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read embedded provenance without returning or trusting result arrays."""
    checkpoint_path = Path(path)
    with np.load(checkpoint_path, allow_pickle=False) as data:
        if PROVENANCE_KEY not in data.files:
            raise CheckpointProvenanceError(
                f"Legacy checkpoint {checkpoint_path} has no TrueMargin provenance. "
                "Delete/recompute it under the current experiment configuration rather than "
                "silently trusting arrays produced by unknown code or settings."
            )
        return _decode_manifest(checkpoint_path, data[PROVENANCE_KEY])


def save_checkpoint(
    path: str | os.PathLike[str],
    *,
    arrays: Mapping[str, np.ndarray],
    manifest: Mapping[str, Any],
) -> None:
    """Save arrays and their provenance together in one non-pickle ``.npz`` file."""
    manifest_dict = dict(manifest)
    payload: dict[str, Any] = dict(arrays)
    if PROVENANCE_KEY in payload:
        raise ValueError(f"{PROVENANCE_KEY!r} is reserved for checkpoint provenance.")
    payload[PROVENANCE_KEY] = np.asarray(_canonical_json(manifest_dict))
    np.savez(path, **payload)
    print(
        "checkpoint provenance: "
        f"path={path} "
        f"experiment={manifest_dict.get('experiment')} "
        f"artifact={manifest_dict.get('artifact_id')} "
        f"git_sha={manifest_dict.get('git_sha')} "
        f"config_hash={manifest_dict.get('config_hash')} "
        f"code_hash={manifest_dict.get('code_hash')}"
    )


def load_checkpoint(
    path: str | os.PathLike[str], *, expected_manifest: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    """Load a checkpoint only if its result-defining provenance still matches."""
    checkpoint_path = Path(path)
    with np.load(checkpoint_path, allow_pickle=False) as data:
        if PROVENANCE_KEY not in data.files:
            raise CheckpointProvenanceError(
                f"Legacy checkpoint {checkpoint_path} has no TrueMargin provenance. "
                "Delete/recompute it under the current experiment configuration rather than "
                "silently trusting arrays produced by unknown code or settings."
            )
        stored_manifest = _decode_manifest(checkpoint_path, data[PROVENANCE_KEY])

        expected = dict(expected_manifest)
        if _compatibility_payload(stored_manifest) != _compatibility_payload(expected):
            stored_summary = {
                "git_sha": stored_manifest.get("git_sha"),
                "experiment": stored_manifest.get("experiment"),
                "artifact_id": stored_manifest.get("artifact_id"),
                "config_hash": stored_manifest.get("config_hash"),
                "code_hash": stored_manifest.get("code_hash"),
            }
            expected_summary = {
                "git_sha": expected.get("git_sha"),
                "experiment": expected.get("experiment"),
                "artifact_id": expected.get("artifact_id"),
                "config_hash": expected.get("config_hash"),
                "code_hash": expected.get("code_hash"),
            }
            raise CheckpointProvenanceError(
                f"Checkpoint provenance mismatch for {checkpoint_path}. "
                f"stored={stored_summary}, expected={expected_summary}. "
                "Recompute this checkpoint; do not mix result arrays across incompatible runs."
            )

        return {key: np.asarray(data[key]) for key in data.files if key != PROVENANCE_KEY}
