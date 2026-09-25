"""Canonical provenance manifests for TrueMargin's existing scientific checkpoints.

Keeping these specifications in one place prevents producer and consumer scripts from
silently disagreeing about which settings define checkpoint compatibility.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import numpy as np

from truemargin import provenance


def ensemble_patient_manifest(
    *,
    repo_root: str | os.PathLike[str],
    patient: str,
    t2_series: str,
    dce_series: str,
    mode: str,
    mode_cfg: Mapping[str, Any],
    reg_cfg: Mapping[str, Any],
    max_landmarks: int,
    perturbation: str = "absolute_intensity",
    perturbation_scale: float | None = None,
) -> dict[str, Any]:
    if perturbation not in ("absolute_intensity", "relative_std"):
        raise ValueError(
            "perturbation must be 'absolute_intensity' or 'relative_std', " f"got {perturbation!r}"
        )
    if perturbation_scale is None:
        perturbation_scale = float(reg_cfg["ensemble_jitter"])

    source_files = [
        "scripts/04_tcia_case_calibration.py",
        "src/truemargin/registration.py",
        "src/truemargin/io_utils.py",
        "src/truemargin/calibration.py",
    ]
    if perturbation == "relative_std":
        source_files.append("src/truemargin/ensemble.py")

    return provenance.build_manifest(
        repo_root=repo_root,
        experiment="real-prostate-ensemble-v1",
        artifact_id=patient,
        parameters={
            "registration_mode": mode,
            "mesh_size": int(mode_cfg["mesh_size"]),
            "max_iterations": int(mode_cfg["max_iterations"]),
            "uncertainty_method": "input-intensity-perturbation-ensemble",
            "ensemble_n": int(reg_cfg["ensemble_n"]),
            "ensemble_perturbation": perturbation,
            "ensemble_perturbation_scale": float(perturbation_scale),
            "seed": int(reg_cfg["seed"]),
            "max_landmarks_per_patient": int(max_landmarks),
            "crop_pad_voxels": 15,
            "dce_phase_strategy": "per-slice middle temporal phase",
            "dce_phase_fraction": 0.5,
            "true_displacement_reference": "zero-displacement proxy",
            "center_first": False,
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "patient": patient,
            "t2_series": t2_series,
            "dce_series": dce_series,
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=source_files,
    )


def ensemble_sensitivity_manifest(
    *,
    repo_root: str | os.PathLike[str],
    patient: str,
    t2_series: str,
    dce_series: str,
    mode_cfg: Mapping[str, Any],
    seed: int,
    max_landmarks: int,
    ensemble_n: int,
    perturbation: str,
    perturbation_scale: float,
    near_zero_sigma: float,
) -> dict[str, Any]:
    """Provenance for the frozen five-patient perturbation-sensitivity study."""
    if perturbation not in ("absolute_intensity", "relative_std"):
        raise ValueError(
            "perturbation must be 'absolute_intensity' or 'relative_std', " f"got {perturbation!r}"
        )
    setting_id = f"{perturbation}:{float(perturbation_scale):.6g}"
    return provenance.build_manifest(
        repo_root=repo_root,
        experiment="real-prostate-ensemble-sensitivity-v1",
        artifact_id=f"{patient}:{setting_id}",
        parameters={
            "registration_mode": "fast_dev",
            "mesh_size": int(mode_cfg["mesh_size"]),
            "max_iterations": int(mode_cfg["max_iterations"]),
            "uncertainty_method": "input-intensity-perturbation-ensemble",
            "ensemble_n": int(ensemble_n),
            "ensemble_perturbation": perturbation,
            "ensemble_perturbation_scale": float(perturbation_scale),
            "seed": int(seed),
            "max_landmarks_per_patient": int(max_landmarks),
            "crop_pad_voxels": 15,
            "dce_phase_strategy": "per-slice middle temporal phase",
            "dce_phase_fraction": 0.5,
            "true_displacement_reference": "zero-displacement proxy",
            "center_first": False,
            "member_failure_policy": [
                "registration_exception",
                "nonfinite_displacement",
                "shape_mismatch",
                "mean_displacement_exceeds_crop_physical_diagonal",
            ],
            "failed_member_action": "mark_entire_patient_setting_unstable",
            "near_zero_sigma_threshold": float(near_zero_sigma),
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "sensitivity_cohort": [
                "aaa0054",
                "aaa0059",
                "aaa0061",
                "aaa0063",
                "aaa0066",
            ],
            "patient": patient,
            "t2_series": t2_series,
            "dce_series": dce_series,
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=[
            "scripts/15_ensemble_perturbation_sensitivity.py",
            "src/truemargin/ensemble.py",
            "src/truemargin/registration.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def curvature_patient_manifest(
    *,
    repo_root: str | os.PathLike[str],
    patient: str,
    t2_series: str,
    dce_series: str,
    mode: str,
    mode_cfg: Mapping[str, Any],
    reg_cfg: Mapping[str, Any],
    max_landmarks: int,
    perturb_eps: float,
) -> dict[str, Any]:
    return provenance.build_manifest(
        repo_root=repo_root,
        experiment="real-prostate-curvature-v1",
        artifact_id=patient,
        parameters={
            "registration_mode": mode,
            "mesh_size": int(mode_cfg["mesh_size"]),
            "max_iterations": int(mode_cfg["max_iterations"]),
            "uncertainty_method": "diagonal-local-curvature-mc-propagation",
            "perturb_eps": float(perturb_eps),
            "mc_samples": 30,
            "mc_seed": 0,
            "seed": int(reg_cfg["seed"]),
            "max_landmarks_per_patient": int(max_landmarks),
            "crop_pad_voxels": 15,
            "dce_phase_strategy": "per-slice middle temporal phase",
            "dce_phase_fraction": 0.5,
            "true_displacement_reference": "zero-displacement proxy",
            "center_first_policy": "false_then_retry_true_once_on_runtime_error",
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "patient": patient,
            "t2_series": t2_series,
            "dce_series": dce_series,
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=[
            "scripts/08_curvature_vs_ensemble.py",
            "src/truemargin/registration.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def _declared_real_series(path: str | os.PathLike[str], patient: str) -> tuple[str, str]:
    stored = provenance.read_checkpoint_manifest(path)
    data_identity = stored.get("data_identity")
    if not isinstance(data_identity, dict):
        raise provenance.CheckpointProvenanceError(
            f"Checkpoint {path} has no structured data_identity provenance."
        )
    if stored.get("artifact_id") != patient or data_identity.get("patient") != patient:
        raise provenance.CheckpointProvenanceError(
            f"Checkpoint {path} does not declare patient {patient!r}; refusing filename-only trust."
        )
    t2_series = data_identity.get("t2_series")
    dce_series = data_identity.get("dce_series")
    if not isinstance(t2_series, str) or not isinstance(dce_series, str):
        raise provenance.CheckpointProvenanceError(
            f"Checkpoint {path} is missing T2/DCE series identity in its provenance."
        )
    return t2_series, dce_series


def load_ensemble_patient_checkpoint(
    path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str],
    patient: str,
    mode: str,
    mode_cfg: Mapping[str, Any],
    reg_cfg: Mapping[str, Any],
    max_landmarks: int,
    perturbation: str = "absolute_intensity",
    perturbation_scale: float | None = None,
) -> dict[str, np.ndarray]:
    t2_series, dce_series = _declared_real_series(path, patient)
    expected = ensemble_patient_manifest(
        repo_root=repo_root,
        patient=patient,
        t2_series=t2_series,
        dce_series=dce_series,
        mode=mode,
        mode_cfg=mode_cfg,
        reg_cfg=reg_cfg,
        max_landmarks=max_landmarks,
        perturbation=perturbation,
        perturbation_scale=perturbation_scale,
    )
    return provenance.load_checkpoint(path, expected_manifest=expected)


def load_curvature_patient_checkpoint(
    path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str],
    patient: str,
    mode: str,
    mode_cfg: Mapping[str, Any],
    reg_cfg: Mapping[str, Any],
    max_landmarks: int,
    perturb_eps: float,
) -> dict[str, np.ndarray]:
    t2_series, dce_series = _declared_real_series(path, patient)
    expected = curvature_patient_manifest(
        repo_root=repo_root,
        patient=patient,
        t2_series=t2_series,
        dce_series=dce_series,
        mode=mode,
        mode_cfg=mode_cfg,
        reg_cfg=reg_cfg,
        max_landmarks=max_landmarks,
        perturb_eps=perturb_eps,
    )
    return provenance.load_checkpoint(path, expected_manifest=expected)


def synthetic_case_manifest(
    *,
    repo_root: str | os.PathLike[str],
    case_i: int,
    mode_cfg: Mapping[str, Any],
    reg_cfg: Mapping[str, Any],
    crop_shape_zyx: tuple[int, int, int],
    n_landmarks: int,
    landmark_margin: int,
    known_disp_scale: float,
    deform_mesh_size: int,
    intensity_noise_std: float,
    base_t2_series: str,
) -> dict[str, Any]:
    return provenance.build_manifest(
        repo_root=repo_root,
        experiment="synthetic-known-ground-truth-v1",
        artifact_id=f"case_{case_i:02d}",
        parameters={
            "case_seed": int(case_i),
            "registration_mode": "fast_dev",
            "mesh_size": int(mode_cfg["mesh_size"]),
            "max_iterations": int(mode_cfg["max_iterations"]),
            "ensemble_n": int(reg_cfg["ensemble_n"]),
            "ensemble_jitter": float(reg_cfg["ensemble_jitter"]),
            "intensity_normalization": "divide fixed and moving by fixed-image std",
            "crop_shape_zyx": list(crop_shape_zyx),
            "n_landmarks_per_case": int(n_landmarks),
            "landmark_margin_voxels": int(landmark_margin),
            "known_disp_parameter_scale": float(known_disp_scale),
            "deformation_mesh_size": int(deform_mesh_size),
            "intensity_noise_std": float(intensity_noise_std),
            "curvature_perturb_eps": 0.5,
            "curvature_mc_samples": 30,
            "curvature_mc_seed": int(case_i),
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "base_patient": "aaa0071",
            "base_t2_series": base_t2_series,
            "ground_truth": "known synthetic B-spline deformation",
        },
        source_files=[
            "scripts/13_synthetic_ground_truth_validation.py",
            "src/truemargin/registration.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )
