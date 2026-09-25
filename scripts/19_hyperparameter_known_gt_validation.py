#!/usr/bin/env python3
"""Evaluate the frozen hyperparameter ensemble against synthetic known deformation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections.abc import Mapping
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.stats import binomtest, pearsonr, spearmanr

from truemargin import calibration as cal
from truemargin import comparators, provenance
from truemargin import hyperparameter as hyper
from truemargin import io_utils as ioutil
from truemargin import known_gt_comparison as comparison

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(REPO_ROOT, "data")
OUT = os.path.join(REPO_ROOT, "outputs")
MANIFEST_ROOT = os.path.join(DATA, "prostate_fused_manifest", "prostate_fused_mri_pathology")
HECAP_DIR = os.path.join(DATA, "hecap")
RUN_REQUEST_PATH = os.path.join(REPO_ROOT, "research", "KNOWN_GT_RUN_REQUEST.json")

PROTOCOL_MAIN_BLOB_SHA = "98a747c502a4aca6d8e65f8373bc4e62a8f1b7a0"
PROTOCOL_MAIN_PRIVATE_FREEZE_COMMIT = "44afb8653c8c90b33a438107481f7be4586b0e68"
PROTOCOL_PATH = "docs/hyperparameter_known_gt_protocol.md"
PROTOCOL_AMENDMENT_BLOB_SHA = "1eafe77bb847b1a77229e267ef32e6bbedd27bc2"
PROTOCOL_AMENDMENT_PRIVATE_FREEZE_COMMIT = "d37b5a4a7931fdd3947870ba651b097f712ebdb3"
PROTOCOL_AMENDMENT_PATH = "docs/hyperparameter_known_gt_protocol_amendment_1.md"
PROTOCOL_AMENDMENT_2_BLOB_SHA = "bcd0a6b970891724c755cde75111f56d6fad7492"
PROTOCOL_AMENDMENT_2_PATH = "docs/hyperparameter_known_gt_protocol_amendment_2.md"
COMPARATOR_PROTOCOL_BLOB_SHA = "2d383d3bed7503e2ceaecf36f599e7965726a18d"
COMPARATOR_PROTOCOL_PATH = "docs/hyperparameter_known_gt_comparator_protocol.md"
EXECUTION_CONTROL_AMENDMENT_BLOB_SHA = "9dc7c2680e128b3a67d9bd864ab465a47d6e7e53"
EXECUTION_CONTROL_AMENDMENT_PATH = "docs/hyperparameter_known_gt_execution_control_amendment_1.md"
GEOMETRY_PREFLIGHT_RECORD = "results/hyperparameter_known_gt_geometry_preflight.json"
GEOMETRY_PREFLIGHT_BLOB_SHA = "fb90f421c6d11dcaff407d9f8267503925dd4aaa"
GEOMETRY_PREFLIGHT_UPLOADED_SHA256 = (
    "fbf0b60f50e8bd6af2af2af036fe94b4491ad0ffe4ab15863b0ce8f95515c2d2"
)
ACQUISITION_RECORD = "results/known_gt_data_acquisition.json"
ACQUISITION_BLOB_SHA = "7481390f2565fbe49aff8faf00f1e59ca0f82c9c"

HELD_OUT_CASES = {
    "aaa0044": {"t2_series": "13614"},
    "aaa0051": {"t2_series": "36207"},
    "aaa0053": {"t2_series": "45314"},
    "aaa0060": {"t2_series": "12400"},
    "aaa0064": {"t2_series": "40733"},
    "aaa0069": {"t2_series": "58343"},
    "aaa0071": {"t2_series": "27783"},
    "aaa0072": {"t2_series": "64767"},
    "aaa0086": {"t2_series": "42255"},
    "aaa0087": {"t2_series": "30095"},
}

PROMOTION_PATIENTS = {"aaa0054", "aaa0059", "aaa0061", "aaa0063", "aaa0066"}
N_REPLICATES = 3
CROP_PAD_VOXELS = 15
DEFORM_MESH_SIZE = 4
KNOWN_COEFFICIENT_STD = 4.0
TOPOLOGY_SCALES = (
    1.00,
    0.95,
    0.90,
    0.85,
    0.80,
    0.75,
    0.70,
    0.65,
    0.60,
    0.55,
    0.50,
)
INTENSITY_NOISE_STD = 0.03
N_LANDMARKS = 50
LANDMARK_MARGIN = 8
NOISE_SEED_OFFSET = 100_000
LANDMARK_SEED_OFFSET = 200_000
MIN_ASSESSABLE_CASES_PER_ANATOMY = 2
MIN_ASSESSABLE_ANATOMIES = 8
N_BOOTSTRAPS = 10_000
BOOTSTRAP_SEED = 0
RANK_DEGENERACY_TOL = 1e-12
NDIM = 3
DIRECT_COMPARATOR_METHODS = ("ice", "residual", "jacdev")
SECONDARY_METRICS = (
    "pearson_sigma_known_error",
    "known_error_median_mm",
    "known_error_mean_mm",
    "known_error_p90_mm",
    "sigma_median_mm",
    "sigma_iqr_mm",
    "quartile_known_error_delta_mm",
    "blind_spot_rate",
    "true_displacement_min_mm",
    "true_displacement_median_mm",
    "true_displacement_p90_mm",
    "true_displacement_max_mm",
)


def _git_blob_sha(path: str) -> str:
    with open(path, "rb") as handle:
        content = handle.read()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def verify_protocol_identities(repo_root: str = REPO_ROOT) -> dict[str, str]:
    expected = {
        PROTOCOL_PATH: PROTOCOL_MAIN_BLOB_SHA,
        PROTOCOL_AMENDMENT_PATH: PROTOCOL_AMENDMENT_BLOB_SHA,
        PROTOCOL_AMENDMENT_2_PATH: PROTOCOL_AMENDMENT_2_BLOB_SHA,
        COMPARATOR_PROTOCOL_PATH: COMPARATOR_PROTOCOL_BLOB_SHA,
        EXECUTION_CONTROL_AMENDMENT_PATH: EXECUTION_CONTROL_AMENDMENT_BLOB_SHA,
    }
    observed: dict[str, str] = {}
    for relative_path, expected_sha in expected.items():
        full_path = os.path.join(repo_root, relative_path)
        if not os.path.isfile(full_path):
            raise SystemExit(f"Frozen protocol file is missing: {full_path}")
        actual_sha = _git_blob_sha(full_path)
        if actual_sha != expected_sha:
            raise SystemExit(
                f"Frozen protocol content drift for {relative_path}: "
                f"expected blob {expected_sha}, got {actual_sha}"
            )
        observed[relative_path] = actual_sha
    return observed


def find_series_dir(patient: str, series_id: str) -> str:
    patient_dir = os.path.join(MANIFEST_ROOT, patient)
    study = os.listdir(patient_dir)[0]
    return os.path.join(patient_dir, study, series_id)


def load_series(series_dir: str) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(series_dir)
    reader.SetFileNames(files)
    return reader.Execute()


def crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent_mm = (
        shape_zyx[2] * spacing_xyz[0],
        shape_zyx[1] * spacing_xyz[1],
        shape_zyx[0] * spacing_xyz[2],
    )
    return float(np.sqrt(sum(float(value) ** 2 for value in extent_mm)))


def case_seed(anatomy_index: int, replicate: int) -> int:
    if anatomy_index < 0:
        raise ValueError("anatomy_index must be non-negative")
    if replicate not in range(N_REPLICATES):
        raise ValueError(f"replicate must be in [0, {N_REPLICATES - 1}]")
    return 1000 * anatomy_index + replicate


def _mask_bbox_crop(
    t2_img: sitk.Image, mask_img: sitk.Image
) -> tuple[np.ndarray, np.ndarray, tuple[float, ...]]:
    ioutil.assert_same_grid(mask_img, t2_img, "HECaP mask", "T2 image")
    t2 = sitk.GetArrayFromImage(t2_img).astype(np.float32)
    mask = sitk.GetArrayFromImage(mask_img)
    voxel_idx = np.argwhere(mask > 0)
    if len(voxel_idx) == 0:
        raise ValueError("HECaP mask is empty")

    lo = np.maximum(voxel_idx.min(axis=0) - CROP_PAD_VOXELS, 0)
    hi = np.minimum(voxel_idx.max(axis=0) + CROP_PAD_VOXELS + 1, np.asarray(mask.shape))
    slices = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi, strict=True))
    crop = t2[slices]
    mask_crop = (mask[slices] > 0).astype(np.uint8)
    return crop, mask_crop, tuple(float(value) for value in t2_img.GetSpacing())


def prepare_anatomy(
    patient: str, series: Mapping[str, str]
) -> tuple[np.ndarray, np.ndarray, tuple[float, ...]]:
    t2_img = load_series(find_series_dir(patient, series["t2_series"]))
    mask_path = os.path.join(HECAP_DIR, f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha")
    if not os.path.exists(mask_path):
        raise SystemExit(f"Missing HECaP mask: {mask_path}")
    mask_img = sitk.ReadImage(mask_path)
    return _mask_bbox_crop(t2_img, mask_img)


def make_source_image(crop: np.ndarray, spacing: tuple[float, ...]) -> sitk.Image:
    image = sitk.GetImageFromArray(crop.astype(np.float32))
    image.SetSpacing(spacing)
    image.SetOrigin(tuple(0.0 for _ in spacing))
    image.SetDirection(tuple(float(i == j) for i in range(NDIM) for j in range(NDIM)))
    return image


def make_fixed_roi_mask(
    mask_crop: np.ndarray,
    source_img: sitk.Image,
    transform: sitk.Transform,
) -> np.ndarray:
    moving_mask = sitk.GetImageFromArray((np.asarray(mask_crop) > 0).astype(np.uint8))
    moving_mask.CopyInformation(source_img)
    fixed_mask = sitk.Resample(
        moving_mask,
        source_img,
        transform,
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt8,
    )
    return sitk.GetArrayFromImage(fixed_mask) > 0


def make_known_transform(source_img: sitk.Image, seed: int) -> sitk.Transform:
    transform = sitk.BSplineTransformInitializer(source_img, [DEFORM_MESH_SIZE] * NDIM)
    rng = np.random.default_rng(seed)
    params = rng.normal(0.0, KNOWN_COEFFICIENT_STD, len(transform.GetParameters()))
    transform.SetParameters(tuple(float(value) for value in params))
    return transform


def sample_landmarks(fixed_roi_mask: np.ndarray, seed: int) -> np.ndarray:
    if fixed_roi_mask.ndim != NDIM:
        raise ValueError("fixed ROI mask must be 3-D")

    candidates = np.argwhere(np.asarray(fixed_roi_mask) > 0)
    if len(candidates) == 0:
        raise ValueError("fixed ROI mask is empty")

    shape = np.asarray(fixed_roi_mask.shape, dtype=np.int64)
    inside_margin = np.all(candidates >= LANDMARK_MARGIN, axis=1) & np.all(
        candidates < (shape - LANDMARK_MARGIN), axis=1
    )
    eligible = candidates[inside_margin]
    if len(eligible) < N_LANDMARKS:
        raise ValueError(
            f"fixed ROI has only {len(eligible)} eligible voxels after "
            f"{LANDMARK_MARGIN}-voxel margin; need {N_LANDMARKS}"
        )

    rng = np.random.default_rng(seed)
    selected = rng.choice(len(eligible), size=N_LANDMARKS, replace=False)
    return eligible[selected].astype(np.int64)


def true_displacement_at_indices(
    source_img: sitk.Image,
    transform: sitk.Transform,
    idx_zyx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    displacement = np.zeros((NDIM, len(idx_zyx)), dtype=np.float64)
    transformed_points = np.zeros((len(idx_zyx), NDIM), dtype=np.float64)
    for i, (z, y, x) in enumerate(idx_zyx):
        point = source_img.TransformIndexToPhysicalPoint((int(x), int(y), int(z)))
        transformed = transform.TransformPoint(point)
        transformed_points[i] = transformed
        displacement[:, i] = np.asarray(transformed) - np.asarray(point)
    return displacement, transformed_points


def _physical_point_inside(image: sitk.Image, point: np.ndarray) -> bool:
    continuous = image.TransformPhysicalPointToContinuousIndex(
        tuple(float(value) for value in point)
    )
    return all(
        -1e-9 <= value <= (size - 1) + 1e-9
        for value, size in zip(continuous, image.GetSize(), strict=True)
    )


def _known_displacement_field(source_img: sitk.Image, transform: sitk.Transform) -> sitk.Image:
    displacement_filter = sitk.TransformToDisplacementFieldFilter()
    displacement_filter.SetReferenceImage(source_img)
    return displacement_filter.Execute(transform)


def _transform_jacobian_min(source_img: sitk.Image, transform: sitk.Transform) -> float:
    displacement_image = _known_displacement_field(source_img, transform)
    displacement = sitk.GetArrayFromImage(displacement_image)
    if not np.isfinite(displacement).all():
        return float("nan")
    jacobian_image = sitk.DisplacementFieldJacobianDeterminant(displacement_image, True)
    jacobian = sitk.GetArrayFromImage(jacobian_image)
    if not np.isfinite(jacobian).all():
        return float("nan")
    return float(np.min(jacobian))


def make_topology_safe_known_transform(
    source_img: sitk.Image, seed: int
) -> tuple[sitk.Transform, dict[str, float | bool]]:
    raw_transform = make_known_transform(source_img, seed)
    raw_params = np.asarray(raw_transform.GetParameters(), dtype=np.float64)
    if not np.isfinite(raw_params).all():
        raise ValueError("known B-spline parameters are non-finite")

    raw_jacobian_min = _transform_jacobian_min(source_img, raw_transform)
    for scale in TOPOLOGY_SCALES:
        transform = sitk.BSplineTransformInitializer(source_img, [DEFORM_MESH_SIZE] * NDIM)
        scaled_params = raw_params * scale
        transform.SetParameters(tuple(float(value) for value in scaled_params))
        jacobian_min = _transform_jacobian_min(source_img, transform)
        if np.isfinite(jacobian_min) and jacobian_min > 0.0:
            return transform, {
                "raw_jacobian_min": float(raw_jacobian_min),
                "topology_scale": float(scale),
                "jacobian_min": float(jacobian_min),
                "topology_attenuated": bool(scale < 1.0),
            }

    raise ValueError(
        "known deformation remains invalid after topology backtracking: "
        f"raw minimum Jacobian={raw_jacobian_min:.6g}"
    )


def geometry_record(
    *,
    patient: str,
    anatomy_index: int,
    replicate: int,
    crop: np.ndarray,
    mask_crop: np.ndarray,
    spacing: tuple[float, ...],
) -> dict[str, Any]:
    seed = case_seed(anatomy_index, replicate)
    source_img = make_source_image(crop, spacing)
    transform, topology = make_topology_safe_known_transform(source_img, seed)

    displacement_image = _known_displacement_field(source_img, transform)
    displacement = sitk.GetArrayFromImage(displacement_image)
    if not np.isfinite(displacement).all():
        raise ValueError("known displacement field is non-finite")
    field_magnitude = np.sqrt(np.sum(displacement * displacement, axis=-1))

    jacobian_image = sitk.DisplacementFieldJacobianDeterminant(displacement_image, True)
    jacobian = sitk.GetArrayFromImage(jacobian_image)
    if not np.isfinite(jacobian).all():
        raise ValueError("known deformation Jacobian contains non-finite values")
    jacobian_min = float(np.min(jacobian))
    if jacobian_min <= 0.0:
        raise ValueError(f"known deformation folds: minimum Jacobian={jacobian_min:.6g}")

    fixed_roi = make_fixed_roi_mask(mask_crop, source_img, transform)
    roi_candidates = np.argwhere(fixed_roi)
    shape = np.asarray(fixed_roi.shape, dtype=np.int64)
    eligible_roi = roi_candidates[
        np.all(roi_candidates >= LANDMARK_MARGIN, axis=1)
        & np.all(roi_candidates < (shape - LANDMARK_MARGIN), axis=1)
    ]
    idx_zyx = sample_landmarks(fixed_roi, seed + LANDMARK_SEED_OFFSET)
    if len(np.unique(idx_zyx, axis=0)) != N_LANDMARKS:
        raise ValueError("landmark sampler did not produce unique landmarks")
    if not np.all(fixed_roi[tuple(idx_zyx.T)]):
        raise ValueError("sampled landmark is outside the fixed-domain HECaP ROI")

    u_true, transformed_points = true_displacement_at_indices(source_img, transform, idx_zyx)
    if not np.isfinite(u_true).all():
        raise ValueError("true landmark displacement contains non-finite values")
    if not all(_physical_point_inside(source_img, point) for point in transformed_points):
        raise ValueError("a transformed landmark leaves the moving-source domain")

    magnitude = np.sqrt(np.sum(u_true * u_true, axis=0))
    return {
        "patient": patient,
        "anatomy_index": anatomy_index,
        "replicate": replicate,
        "case_seed": seed,
        "noise_seed": seed + NOISE_SEED_OFFSET,
        "landmark_seed": seed + LANDMARK_SEED_OFFSET,
        "shape_zyx": tuple(int(value) for value in crop.shape),
        "spacing_xyz_mm": spacing,
        "crop_diagonal_mm": crop_diagonal_mm(crop.shape, spacing),
        "raw_jacobian_min": float(topology["raw_jacobian_min"]),
        "topology_scale": float(topology["topology_scale"]),
        "topology_attenuated": bool(topology["topology_attenuated"]),
        "jacobian_min": jacobian_min,
        "fixed_roi_voxels": int(np.sum(fixed_roi)),
        "eligible_fixed_roi_voxels": int(len(eligible_roi)),
        "sampled_roi_landmarks": int(len(idx_zyx)),
        "all_landmarks_in_fixed_roi": bool(np.all(fixed_roi[tuple(idx_zyx.T)])),
        "field_true_displacement_min_mm": float(np.min(field_magnitude)),
        "field_true_displacement_median_mm": float(np.median(field_magnitude)),
        "field_true_displacement_p90_mm": float(np.percentile(field_magnitude, 90)),
        "field_true_displacement_max_mm": float(np.max(field_magnitude)),
        "true_displacement_min_mm": float(np.min(magnitude)),
        "true_displacement_median_mm": float(np.median(magnitude)),
        "true_displacement_p90_mm": float(np.percentile(magnitude, 90)),
        "true_displacement_max_mm": float(np.max(magnitude)),
    }


def build_synthetic_case(
    *,
    crop: np.ndarray,
    mask_crop: np.ndarray,
    spacing: tuple[float, ...],
    anatomy_index: int,
    replicate: int,
) -> dict[str, Any]:
    seed = case_seed(anatomy_index, replicate)
    source_img = make_source_image(crop, spacing)
    transform, _ = make_topology_safe_known_transform(source_img, seed)
    fixed_roi = make_fixed_roi_mask(mask_crop, source_img, transform)
    idx_zyx = sample_landmarks(fixed_roi, seed + LANDMARK_SEED_OFFSET)
    u_true, _ = true_displacement_at_indices(source_img, transform, idx_zyx)

    fixed_img = sitk.Resample(source_img, source_img, transform, sitk.sitkLinear, 0.0)
    moving = sitk.GetArrayFromImage(source_img).astype(np.float32)
    fixed = sitk.GetArrayFromImage(fixed_img).astype(np.float32)
    scale = float(np.std(moving))
    if not np.isfinite(scale) or scale <= np.finfo(np.float32).eps:
        raise ValueError("moving-source crop has invalid intensity standard deviation")
    moving = moving / scale
    fixed = fixed / scale

    rng_noise = np.random.default_rng(seed + NOISE_SEED_OFFSET)
    fixed = fixed + rng_noise.normal(0.0, INTENSITY_NOISE_STD, fixed.shape).astype(np.float32)

    return {
        "fixed": fixed,
        "moving": moving,
        "fixed_roi_mask": fixed_roi,
        "idx_zyx": idx_zyx,
        "u_true": u_true,
        "crop_diagonal_mm": crop_diagonal_mm(crop.shape, spacing),
        "spacing": spacing,
    }


def _safe_spearman(sigma: np.ndarray, error: np.ndarray) -> tuple[float, bool]:
    sigma = np.asarray(sigma, dtype=np.float64)
    error = np.asarray(error, dtype=np.float64)
    if len(sigma) < 2 or len(error) != len(sigma):
        raise ValueError("sigma/error arrays must have matching length >=2")
    if not np.isfinite(sigma).all() or not np.isfinite(error).all():
        raise ValueError("sigma/error arrays must be finite")
    if float(np.std(sigma)) <= RANK_DEGENERACY_TOL or float(np.std(error)) <= RANK_DEGENERACY_TOL:
        return 0.0, True
    result = spearmanr(sigma, error)
    rho = float(result.statistic)
    if not np.isfinite(rho):
        return 0.0, True
    return rho, False


def _safe_pearson(sigma: np.ndarray, error: np.ndarray) -> float:
    if float(np.std(sigma)) <= RANK_DEGENERACY_TOL or float(np.std(error)) <= RANK_DEGENERACY_TOL:
        return float("nan")
    value = float(pearsonr(sigma, error).statistic)
    return value if np.isfinite(value) else float("nan")


def case_metrics(error: np.ndarray, sigma: np.ndarray) -> dict[str, Any]:
    rho, rank_degenerate = _safe_spearman(sigma, error)
    sigma_q25, sigma_q75 = np.percentile(sigma, [25, 75])
    error_q75 = float(np.percentile(error, 75))
    low_sigma = sigma <= sigma_q25
    high_sigma = sigma >= sigma_q75
    blind_spot = (error >= error_q75) & low_sigma
    return {
        "spearman_sigma_known_error": rho,
        "rank_degenerate": rank_degenerate,
        "pearson_sigma_known_error": _safe_pearson(sigma, error),
        "known_error_median_mm": float(np.median(error)),
        "known_error_mean_mm": float(np.mean(error)),
        "known_error_p90_mm": float(np.percentile(error, 90)),
        "sigma_median_mm": float(np.median(sigma)),
        "sigma_iqr_mm": float(np.percentile(sigma, 75) - np.percentile(sigma, 25)),
        "quartile_known_error_delta_mm": float(
            np.median(error[high_sigma]) - np.median(error[low_sigma])
        ),
        "blind_spot_rate": float(np.mean(blind_spot)),
    }


def _case_manifest(
    *,
    patient: str,
    t2_series: str,
    anatomy_index: int,
    replicate: int,
) -> dict[str, Any]:
    seed = case_seed(anatomy_index, replicate)
    return provenance.build_manifest(
        repo_root=REPO_ROOT,
        experiment="hyperparameter-known-gt-v1",
        artifact_id=f"{patient}:replicate_{replicate}",
        parameters={
            "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
            "protocol_main_private_freeze_commit": PROTOCOL_MAIN_PRIVATE_FREEZE_COMMIT,
            "protocol_amendment_blob_sha": PROTOCOL_AMENDMENT_BLOB_SHA,
            "protocol_amendment_private_freeze_commit": PROTOCOL_AMENDMENT_PRIVATE_FREEZE_COMMIT,
            "protocol_amendment_path": PROTOCOL_AMENDMENT_PATH,
            "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
            "comparator_protocol_blob_sha": COMPARATOR_PROTOCOL_BLOB_SHA,
            "execution_control_amendment_blob_sha": EXECUTION_CONTROL_AMENDMENT_BLOB_SHA,
            "hyperparameter_configs": [
                {
                    "metric_bins": bins,
                    "gradient_convergence_tolerance": tolerance,
                }
                for bins, tolerance in hyper.CONFIGS
            ],
            "mesh_size": hyper.MESH_SIZE,
            "max_iterations": hyper.MAX_ITERATIONS,
            "center_first": hyper.CENTER_FIRST,
            "deformation_mesh_size": DEFORM_MESH_SIZE,
            "known_coefficient_std": KNOWN_COEFFICIENT_STD,
            "intensity_noise_std": INTENSITY_NOISE_STD,
            "crop_pad_voxels": CROP_PAD_VOXELS,
            "n_landmarks": N_LANDMARKS,
            "landmark_margin": LANDMARK_MARGIN,
            "case_seed": seed,
            "noise_seed": seed + NOISE_SEED_OFFSET,
            "landmark_seed": seed + LANDMARK_SEED_OFFSET,
            "landmark_domain": "warped_hecap_fixed_roi",
            "synthetic_direction": "fixed_synth_to_moving_source",
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "cohort": list(HELD_OUT_CASES),
            "patient": patient,
            "t2_series": t2_series,
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=[
            "scripts/19_hyperparameter_known_gt_validation.py",
            PROTOCOL_PATH,
            PROTOCOL_AMENDMENT_PATH,
            PROTOCOL_AMENDMENT_2_PATH,
            COMPARATOR_PROTOCOL_PATH,
            EXECUTION_CONTROL_AMENDMENT_PATH,
            "src/truemargin/hyperparameter.py",
            "src/truemargin/comparators.py",
            "src/truemargin/known_gt_comparison.py",
            "src/truemargin/registration.py",
            "src/truemargin/ensemble.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def _prefixed_direct_metrics(
    method: str,
    score: np.ndarray,
    known_error: np.ndarray,
) -> dict[str, Any]:
    metrics = comparison.score_case_metrics(score, known_error)
    return {
        f"spearman_{method}_known_error": metrics["spearman_known_error"],
        f"{method}_rank_degenerate": metrics["rank_degenerate"],
        f"{method}_score_median": metrics["score_median"],
        f"{method}_score_iqr": metrics["score_iqr"],
        f"{method}_quartile_known_error_delta_mm": metrics["quartile_known_error_delta_mm"],
        f"{method}_blind_spot_rate": metrics["blind_spot_rate"],
    }


def _run_case(
    *,
    patient: str,
    t2_series: str,
    anatomy_index: int,
    replicate: int,
    crop: np.ndarray,
    mask_crop: np.ndarray,
    spacing: tuple[float, ...],
    checkpoint_root: str,
) -> dict[str, Any]:
    checkpoint_dir = os.path.join(checkpoint_root, patient)
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"replicate_{replicate}.npz")
    manifest = _case_manifest(
        patient=patient,
        t2_series=t2_series,
        anatomy_index=anatomy_index,
        replicate=replicate,
    )
    if os.path.exists(checkpoint_path):
        arrays = provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)
    else:
        synthetic = build_synthetic_case(
            crop=crop,
            mask_crop=mask_crop,
            spacing=spacing,
            anatomy_index=anatomy_index,
            replicate=replicate,
        )
        fixed = np.asarray(synthetic["fixed"])
        moving = np.asarray(synthetic["moving"])
        result = hyper.run_hyperparameter_ensemble(
            fixed,
            moving,
            spacing=spacing,
            crop_diagonal_mm=float(synthetic["crop_diagonal_mm"]),
        )
        arrays: dict[str, np.ndarray] = {
            "complete": np.asarray(result.complete),
            "error": np.asarray([], dtype=np.float64),
            "sigma": np.asarray([], dtype=np.float64),
            "u_true": np.asarray(synthetic["u_true"], dtype=np.float64),
            "idx_zyx": np.asarray(synthetic["idx_zyx"], dtype=np.int64),
            "member_reasons": np.asarray(result.member_reasons, dtype="U1024"),
            "member_mean_displacement_mm": result.member_mean_displacement_mm,
            "spacing_xyz_mm": np.asarray(spacing, dtype=np.float64),
            "crop_diagonal_mm": np.asarray(
                synthetic["crop_diagonal_mm"],
                dtype=np.float64,
            ),
            "reverse_complete": np.asarray(False),
            "reverse_member_reasons": np.asarray([], dtype="U1024"),
        }
        for method in DIRECT_COMPARATOR_METHODS:
            arrays[f"{method}_valid"] = np.asarray(False)
            arrays[f"{method}_score"] = np.asarray([], dtype=np.float64)
            arrays[f"{method}_failure_reason"] = np.asarray(
                "forward_target_incomplete",
                dtype="U4096",
            )

        if result.complete:
            assert result.u_mean is not None
            assert result.sigma is not None
            idx_zyx = np.asarray(synthetic["idx_zyx"])
            u_est = ioutil.sample_field_at_points(result.u_mean, idx_zyx)
            sigma_at = ioutil.sample_field_at_points(result.sigma, idx_zyx)
            error = cal.displacement_error(u_est, np.asarray(synthetic["u_true"]))
            arrays["error"] = np.asarray(error, dtype=np.float64)
            arrays["sigma"] = np.asarray(sigma_at, dtype=np.float64)

            direct = comparison.run_direct_comparators(
                fixed=fixed,
                moving=moving,
                forward_u_mean=result.u_mean,
                idx_zyx=idx_zyx,
                spacing=spacing,
                crop_diagonal_mm=float(synthetic["crop_diagonal_mm"]),
            )
            arrays["reverse_complete"] = np.asarray(direct.reverse_complete)
            arrays["reverse_member_reasons"] = np.asarray(
                direct.reverse_member_reasons,
                dtype="U1024",
            )
            direct_scores = {
                "ice": direct.ice,
                "residual": direct.residual,
                "jacdev": direct.jacdev,
            }
            direct_failures = {
                "ice": direct.ice_failure_reason,
                "residual": direct.residual_failure_reason,
                "jacdev": direct.jacdev_failure_reason,
            }
            for method in DIRECT_COMPARATOR_METHODS:
                score = direct_scores[method]
                failure = direct_failures[method]
                arrays[f"{method}_valid"] = np.asarray(score is not None)
                arrays[f"{method}_score"] = (
                    np.asarray(score, dtype=np.float64)
                    if score is not None
                    else np.asarray([], dtype=np.float64)
                )
                arrays[f"{method}_failure_reason"] = np.asarray(
                    failure or "",
                    dtype="U4096",
                )

        provenance.save_checkpoint(checkpoint_path, arrays=arrays, manifest=manifest)

    complete = bool(np.asarray(arrays["complete"]).item())
    row: dict[str, Any] = {
        "patient": patient,
        "anatomy_index": anatomy_index,
        "replicate": replicate,
        "case_seed": case_seed(anatomy_index, replicate),
        "complete": complete,
        "failed_member_count": int(np.sum(np.asarray(arrays["member_reasons"]) != "ok")),
        "member_reasons": " | ".join(str(value) for value in arrays["member_reasons"]),
        "reverse_complete": bool(np.asarray(arrays["reverse_complete"]).item()),
        "reverse_member_reasons": " | ".join(
            str(value) for value in arrays["reverse_member_reasons"]
        ),
    }
    true_mag = np.sqrt(np.sum(np.asarray(arrays["u_true"]) ** 2, axis=0))
    row.update(
        {
            "true_displacement_min_mm": float(np.min(true_mag)),
            "true_displacement_median_mm": float(np.median(true_mag)),
            "true_displacement_p90_mm": float(np.percentile(true_mag, 90)),
            "true_displacement_max_mm": float(np.max(true_mag)),
        }
    )

    if complete:
        error = np.asarray(arrays["error"], dtype=np.float64)
        row.update(case_metrics(error, np.asarray(arrays["sigma"], dtype=np.float64)))
        for method in DIRECT_COMPARATOR_METHODS:
            valid = bool(np.asarray(arrays[f"{method}_valid"]).item())
            failure_reason = str(np.asarray(arrays[f"{method}_failure_reason"]).item())
            row[f"{method}_valid"] = valid
            row[f"{method}_failure_reason"] = failure_reason
            if valid:
                score = np.asarray(arrays[f"{method}_score"], dtype=np.float64)
                row.update(_prefixed_direct_metrics(method, score, error))
    else:
        for method in DIRECT_COMPARATOR_METHODS:
            row[f"{method}_valid"] = False
            row[f"{method}_failure_reason"] = "forward_target_incomplete"

    return row


def anatomy_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for patient in HELD_OUT_CASES:
        patient_rows = [row for row in case_rows if row["patient"] == patient]
        complete_rows = [row for row in patient_rows if bool(row["complete"])]
        assessable = len(complete_rows) >= MIN_ASSESSABLE_CASES_PER_ANATOMY
        anatomy: dict[str, Any] = {
            "patient": patient,
            "complete_cases": len(complete_rows),
            "assessable": assessable,
            "rank_degenerate_cases": sum(
                bool(row.get("rank_degenerate", False)) for row in complete_rows
            ),
            "median_case_spearman": (
                float(np.median([row["spearman_sigma_known_error"] for row in complete_rows]))
                if assessable
                else float("nan")
            ),
        }
        if assessable:
            for metric in SECONDARY_METRICS:
                values = np.asarray(
                    [row[metric] for row in complete_rows if metric in row],
                    dtype=np.float64,
                )
                finite = values[np.isfinite(values)]
                anatomy[f"median_{metric}"] = (
                    float(np.median(finite)) if len(finite) else float("nan")
                )
        output.append(anatomy)
    return output


def global_secondary_summary(
    anatomy_summary: list[dict[str, Any]],
) -> dict[str, float]:
    assessable = [row for row in anatomy_summary if bool(row["assessable"])]
    output: dict[str, float] = {}
    for metric in SECONDARY_METRICS:
        key = f"median_{metric}"
        values = np.asarray(
            [row[key] for row in assessable if key in row],
            dtype=np.float64,
        )
        finite = values[np.isfinite(values)]
        output[metric] = float(np.median(finite)) if len(finite) else float("nan")
    return output


def exact_positive_sign_test(
    anatomy_summary: list[dict[str, Any]],
) -> tuple[int, int, float]:
    values = np.asarray(
        [row["median_case_spearman"] for row in anatomy_summary if bool(row["assessable"])],
        dtype=np.float64,
    )
    if len(values) < MIN_ASSESSABLE_ANATOMIES:
        raise ValueError("sign test requires an assessable evaluation")
    if not np.isfinite(values).all():
        raise ValueError("assessable anatomy effects must be finite")

    positives = int(np.sum(values > 0.0))
    p_value = float(binomtest(positives, n=len(values), p=0.5, alternative="greater").pvalue)
    return positives, int(len(values)), p_value


def bootstrap_interval(
    anatomy_summary: list[dict[str, Any]],
    *,
    n_bootstraps: int = N_BOOTSTRAPS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    values = np.asarray(
        [row["median_case_spearman"] for row in anatomy_summary if bool(row["assessable"])],
        dtype=np.float64,
    )
    if len(values) < MIN_ASSESSABLE_ANATOMIES:
        raise ValueError("bootstrap requires an assessable evaluation")
    rng = np.random.default_rng(seed)
    stats = np.empty(n_bootstraps, dtype=np.float64)
    for i in range(n_bootstraps):
        sample = rng.choice(values, size=len(values), replace=True)
        stats[i] = float(np.median(sample))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def positive_association_label(observed: float, p_value: float) -> bool:
    return bool(observed > 0.0 and p_value <= 0.05)


def direct_comparator_summaries(
    case_rows: list[dict[str, Any]],
    target_anatomy_summary: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Aggregate the frozen direct comparators without changing the primary test."""
    target_by_patient = {row["patient"]: row for row in target_anatomy_summary}
    summary: dict[str, dict[str, Any]] = {}
    anatomy_by_method: dict[str, list[dict[str, Any]]] = {}
    p_methods: list[str] = []
    p_values: list[float] = []

    for method in DIRECT_COMPARATOR_METHODS:
        anatomy = comparison.anatomy_summary(
            case_rows,
            patients=list(HELD_OUT_CASES),
            method=method,
            min_complete_cases=MIN_ASSESSABLE_CASES_PER_ANATOMY,
        )
        anatomy_by_method[method] = anatomy
        assessable_rows = [row for row in anatomy if bool(row["assessable"])]
        assessable = len(assessable_rows) >= MIN_ASSESSABLE_ANATOMIES
        method_summary: dict[str, Any] = {
            "assessable_anatomies": len(assessable_rows),
            "assessable": assessable,
            "median_anatomy_spearman": None,
            "positive_anatomies": None,
            "sign_test_n": None,
            "raw_exact_sign_p": None,
            "holm_adjusted_sign_p": None,
            "bootstrap_95_ci": None,
            "median_anatomy_quartile_known_error_delta_mm": None,
            "median_anatomy_blind_spot_rate": None,
            "paired_joint_anatomies": 0,
            "paired_target_minus_comparator_median": None,
            "paired_target_minus_comparator_bootstrap_95_ci": None,
            "paired_target_minus_comparator_values": None,
        }

        if assessable:
            effects = np.asarray(
                [row["median_case_spearman"] for row in assessable_rows],
                dtype=np.float64,
            )
            positives, sign_n, p_value = exact_positive_sign_test(anatomy)
            ci_lo, ci_hi = bootstrap_interval(anatomy)
            method_summary.update(
                {
                    "median_anatomy_spearman": float(np.median(effects)),
                    "positive_anatomies": positives,
                    "sign_test_n": sign_n,
                    "raw_exact_sign_p": p_value,
                    "bootstrap_95_ci": [ci_lo, ci_hi],
                }
            )
            p_methods.append(method)
            p_values.append(p_value)

            for metric in (
                "median_quartile_known_error_delta_mm",
                "median_blind_spot_rate",
            ):
                values = np.asarray(
                    [row[metric] for row in assessable_rows if metric in row],
                    dtype=np.float64,
                )
                finite = values[np.isfinite(values)]
                if len(finite):
                    method_summary[f"median_anatomy_{metric.removeprefix('median_')}"] = float(
                        np.median(finite)
                    )

        jointly_assessable = [
            patient
            for patient in HELD_OUT_CASES
            if bool(target_by_patient[patient]["assessable"])
            and bool(next(row for row in anatomy if row["patient"] == patient)["assessable"])
        ]
        method_summary["paired_joint_anatomies"] = len(jointly_assessable)
        if len(jointly_assessable) >= MIN_ASSESSABLE_ANATOMIES:
            comparator_by_patient = {row["patient"]: row for row in anatomy}
            target_values = np.asarray(
                [
                    target_by_patient[patient]["median_case_spearman"]
                    for patient in jointly_assessable
                ],
                dtype=np.float64,
            )
            comparator_values = np.asarray(
                [
                    comparator_by_patient[patient]["median_case_spearman"]
                    for patient in jointly_assessable
                ],
                dtype=np.float64,
            )
            observed, ci_lo, ci_hi = comparators.paired_median_bootstrap(
                target_values,
                comparator_values,
                n_bootstraps=N_BOOTSTRAPS,
                seed=BOOTSTRAP_SEED,
            )
            method_summary.update(
                {
                    "paired_target_minus_comparator_median": observed,
                    "paired_target_minus_comparator_bootstrap_95_ci": [ci_lo, ci_hi],
                    "paired_target_minus_comparator_values": (
                        target_values - comparator_values
                    ).tolist(),
                }
            )

        summary[method] = method_summary

    if p_values:
        adjusted = comparators.holm_adjust(np.asarray(p_values, dtype=np.float64))
        for method, value in zip(p_methods, adjusted, strict=True):
            summary[method]["holm_adjusted_sign_p"] = float(value)

    return summary, anatomy_by_method


def _write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    clean_rows = [
        {key: value for key, value in row.items() if not key.startswith("_")} for row in rows
    ]
    fields = sorted(set().union(*(row.keys() for row in clean_rows)))
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean_rows)


def verify_result_bearing_authorization(
    path: str = RUN_REQUEST_PATH,
    *,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    if not os.path.exists(path):
        raise SystemExit(
            "Result-bearing execution is not authorized. Complete comparator "
            "implementation/CD feasibility first; then commit a reviewed "
            "research/KNOWN_GT_RUN_REQUEST.json."
        )

    with open(path) as handle:
        request = json.load(handle)

    forward_registrations = len(HELD_OUT_CASES) * N_REPLICATES * len(hyper.CONFIGS)
    reverse_registrations = forward_registrations
    expected = {
        "schema_version": 2,
        "study": "hyperparameter-known-gt-v1",
        "authorized_mode": "result-bearing",
        "result_bearing_authorized": True,
        "held_out_anatomies": list(HELD_OUT_CASES),
        "n_replicates": N_REPLICATES,
        "n_forward_members": len(hyper.CONFIGS),
        "n_reverse_members": len(hyper.CONFIGS),
        "planned_forward_registrations": forward_registrations,
        "planned_reverse_registrations": reverse_registrations,
        "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
        "protocol_amendment_blob_sha": PROTOCOL_AMENDMENT_BLOB_SHA,
        "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
        "comparator_protocol_blob_sha": COMPARATOR_PROTOCOL_BLOB_SHA,
        "execution_control_amendment_blob_sha": EXECUTION_CONTROL_AMENDMENT_BLOB_SHA,
        "geometry_preflight_record": GEOMETRY_PREFLIGHT_RECORD,
        "geometry_preflight_git_blob_sha": GEOMETRY_PREFLIGHT_BLOB_SHA,
        "geometry_preflight_uploaded_sha256": GEOMETRY_PREFLIGHT_UPLOADED_SHA256,
        "acquisition_record": ACQUISITION_RECORD,
        "acquisition_git_blob_sha": ACQUISITION_BLOB_SHA,
    }
    for key, value in expected.items():
        if request.get(key) != value:
            raise SystemExit(
                f"Invalid result-bearing authorization field {key!r}: "
                f"expected {value!r}, got {request.get(key)!r}"
            )

    cd_feasible = request.get("cd_feasible")
    cd_registration_count = request.get("cd_registration_count")
    total_registrations = request.get("total_planned_registrations")
    if not isinstance(cd_feasible, bool):
        raise SystemExit("Authorization must pin a boolean CD feasibility decision.")
    if not isinstance(cd_registration_count, int) or cd_registration_count < 0:
        raise SystemExit("Authorization must pin a non-negative CD registration count.")
    if cd_feasible and cd_registration_count <= 0:
        raise SystemExit("A feasible CD plan must pin a positive additional registration count.")
    if not cd_feasible and cd_registration_count != 0:
        raise SystemExit("An infeasible CD decision must use zero additional registrations.")

    expected_total = forward_registrations + reverse_registrations + cd_registration_count
    if total_registrations != expected_total:
        raise SystemExit(
            "Invalid total planned registration count: "
            f"expected {expected_total}, got {total_registrations!r}"
        )

    cd_record = request.get("cd_feasibility_record")
    cd_record_blob = request.get("cd_feasibility_record_blob_sha")
    if not isinstance(cd_record, str) or not cd_record:
        raise SystemExit("Authorization must pin the CD feasibility record path.")
    if not isinstance(cd_record_blob, str) or len(cd_record_blob) != 40:
        raise SystemExit("Authorization must pin the CD feasibility record Git blob.")

    for relative_path, expected_blob in (
        (GEOMETRY_PREFLIGHT_RECORD, GEOMETRY_PREFLIGHT_BLOB_SHA),
        (ACQUISITION_RECORD, ACQUISITION_BLOB_SHA),
        (cd_record, cd_record_blob),
    ):
        full_path = os.path.join(repo_root, relative_path)
        if not os.path.isfile(full_path):
            raise SystemExit(f"Authorized evidence file is missing: {full_path}")
        actual_blob = _git_blob_sha(full_path)
        if actual_blob != expected_blob:
            raise SystemExit(
                f"Authorized evidence blob drift for {relative_path}: "
                f"expected {expected_blob}, got {actual_blob}"
            )

    return request


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--geometry-only",
        action="store_true",
        help="validate all 30 frozen synthetic geometries and exit before registration",
    )
    mode.add_argument(
        "--run-result-bearing",
        action="store_true",
        help="run registrations only with a committed reviewed run authorization",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    verify_protocol_identities()
    if args.run_result_bearing:
        verify_result_bearing_authorization()

    head = provenance.current_git_sha(REPO_ROOT)
    os.makedirs(OUT, exist_ok=True)
    checkpoint_root = os.path.join(OUT, "checkpoints", "hyperparameter_known_gt")
    os.makedirs(checkpoint_root, exist_ok=True)

    print("=== TrueMargin hyperparameter ensemble known-GT evaluation ===")
    print(f"Git SHA: {head}")
    print(f"Protocol: {PROTOCOL_PATH} @ blob {PROTOCOL_MAIN_BLOB_SHA}")
    print(f"Protocol amendment: {PROTOCOL_AMENDMENT_PATH} " f"@ blob {PROTOCOL_AMENDMENT_BLOB_SHA}")
    print(
        f"Protocol amendment 2: {PROTOCOL_AMENDMENT_2_PATH} "
        f"@ blob {PROTOCOL_AMENDMENT_2_BLOB_SHA}"
    )
    print(
        f"Comparator protocol: {COMPARATOR_PROTOCOL_PATH} " f"@ blob {COMPARATOR_PROTOCOL_BLOB_SHA}"
    )
    print(
        f"Execution-control amendment: {EXECUTION_CONTROL_AMENDMENT_PATH} "
        f"@ blob {EXECUTION_CONTROL_AMENDMENT_BLOB_SHA}"
    )
    print(f"Held-out anatomies: {list(HELD_OUT_CASES)}")
    print(f"Frozen hyperparameter configs: {hyper.CONFIGS}")
    print("Phase 1: geometry-only validation for all 30 predeclared cases")

    prepared: dict[str, tuple[np.ndarray, np.ndarray, tuple[float, ...]]] = {}
    geometry: list[dict[str, Any]] = []
    geometry_failures: list[dict[str, Any]] = []
    for anatomy_index, (patient, series) in enumerate(HELD_OUT_CASES.items()):
        try:
            crop, mask_crop, spacing = prepare_anatomy(patient, series)
        except (Exception, SystemExit) as exc:
            message = f"anatomy_preparation:{type(exc).__name__}:{exc}"
            print(f"--- geometry {patient}: FAILED {message} ---")
            for replicate in range(N_REPLICATES):
                geometry_failures.append(
                    {
                        "patient": patient,
                        "anatomy_index": anatomy_index,
                        "replicate": replicate,
                        "case_seed": case_seed(anatomy_index, replicate),
                        "reason": message,
                    }
                )
            continue

        prepared[patient] = (crop, mask_crop, spacing)
        print(f"--- geometry {patient}: crop={crop.shape}, spacing={spacing} ---")
        for replicate in range(N_REPLICATES):
            try:
                record = geometry_record(
                    patient=patient,
                    anatomy_index=anatomy_index,
                    replicate=replicate,
                    crop=crop,
                    mask_crop=mask_crop,
                    spacing=spacing,
                )
            except Exception as exc:
                failure = {
                    "patient": patient,
                    "anatomy_index": anatomy_index,
                    "replicate": replicate,
                    "case_seed": case_seed(anatomy_index, replicate),
                    "reason": f"{type(exc).__name__}:{exc}",
                }
                geometry_failures.append(failure)
                print(
                    f"  replicate={replicate} seed={failure['case_seed']} "
                    f"GEOMETRY_FAILED {failure['reason']}"
                )
                continue
            geometry.append(record)
            print(
                f"  replicate={replicate} seed={record['case_seed']} "
                f"jacobian_min={record['jacobian_min']:.6g} "
                f"true_disp_median={record['true_displacement_median_mm']:.6g} mm"
            )

    geometry_path = os.path.join(OUT, "hyperparameter_known_gt_geometry.json")
    geometry_payload = {
        "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
        "protocol_amendment_blob_sha": PROTOCOL_AMENDMENT_BLOB_SHA,
        "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
        "comparator_protocol_blob_sha": COMPARATOR_PROTOCOL_BLOB_SHA,
        "execution_control_amendment_blob_sha": EXECUTION_CONTROL_AMENDMENT_BLOB_SHA,
        "git_sha": head,
        "planned_cases": len(HELD_OUT_CASES) * N_REPLICATES,
        "passed_cases": len(geometry),
        "failed_cases": len(geometry_failures),
        "records": geometry,
        "failures": geometry_failures,
    }
    with open(geometry_path, "w") as handle:
        json.dump(geometry_payload, handle, indent=2, sort_keys=True)

    if geometry_failures:
        print(
            f"GEOMETRY_PREFLIGHT=FAIL passed={len(geometry)}/30 "
            f"failed={len(geometry_failures)}/30"
        )
        print(f"Geometry record: {geometry_path}")
        raise SystemExit(
            "Geometry-only preflight failed; no hyperparameter known-GT registrations were run."
        )

    print(f"GEOMETRY_PREFLIGHT=PASS cases={len(geometry)}/30")
    print(f"Geometry record: {geometry_path}")
    if args.geometry_only:
        print("GEOMETRY_ONLY_STATUS=PASS")
        return
    print("Phase 2: running frozen nine-member estimator")

    case_rows: list[dict[str, Any]] = []
    for anatomy_index, (patient, series) in enumerate(HELD_OUT_CASES.items()):
        crop, mask_crop, spacing = prepared[patient]
        print(f"\n--- {patient}: known-GT registrations ---")
        for replicate in range(N_REPLICATES):
            row = _run_case(
                patient=patient,
                t2_series=series["t2_series"],
                anatomy_index=anatomy_index,
                replicate=replicate,
                crop=crop,
                mask_crop=mask_crop,
                spacing=spacing,
                checkpoint_root=checkpoint_root,
            )
            if row["complete"]:
                checkpoint_path = os.path.join(
                    checkpoint_root, patient, f"replicate_{replicate}.npz"
                )
                arrays = provenance.load_checkpoint(
                    checkpoint_path,
                    expected_manifest=_case_manifest(
                        patient=patient,
                        t2_series=series["t2_series"],
                        anatomy_index=anatomy_index,
                        replicate=replicate,
                    ),
                )
                row["_sigma"] = np.asarray(arrays["sigma"], dtype=np.float64)
                row["_error"] = np.asarray(arrays["error"], dtype=np.float64)
                print(
                    f"  replicate={replicate} complete=9/9 "
                    f"rho={row['spearman_sigma_known_error']:.6g} "
                    f"error_median={row['known_error_median_mm']:.6g} mm"
                )
            else:
                print(
                    f"  replicate={replicate} complete=NO "
                    f"failed_members={row['failed_member_count']}"
                )
            case_rows.append(row)

    anatomy_summary = anatomy_rows(case_rows)
    direct_summary, direct_anatomy = direct_comparator_summaries(
        case_rows,
        anatomy_summary,
    )
    assessable_count = sum(bool(row["assessable"]) for row in anatomy_summary)
    assessable = assessable_count >= MIN_ASSESSABLE_ANATOMIES

    case_metrics_path = os.path.join(OUT, "hyperparameter_known_gt_case_metrics.csv")
    anatomy_metrics_path = os.path.join(OUT, "hyperparameter_known_gt_anatomy_metrics.csv")
    comparator_anatomy_path = os.path.join(
        OUT,
        "hyperparameter_known_gt_comparator_anatomy_metrics.csv",
    )
    summary_path = os.path.join(OUT, "hyperparameter_known_gt_summary.json")
    _write_csv(case_metrics_path, case_rows)
    _write_csv(anatomy_metrics_path, anatomy_summary)
    _write_csv(
        comparator_anatomy_path,
        [{"method": method, **row} for method, rows in direct_anatomy.items() for row in rows],
    )

    secondary_summary = global_secondary_summary(anatomy_summary)
    summary: dict[str, Any] = {
        "protocol_main_blob_sha": PROTOCOL_MAIN_BLOB_SHA,
        "protocol_amendment_blob_sha": PROTOCOL_AMENDMENT_BLOB_SHA,
        "protocol_amendment_2_blob_sha": PROTOCOL_AMENDMENT_2_BLOB_SHA,
        "comparator_protocol_blob_sha": COMPARATOR_PROTOCOL_BLOB_SHA,
        "execution_control_amendment_blob_sha": EXECUTION_CONTROL_AMENDMENT_BLOB_SHA,
        "geometry_preflight_git_blob_sha": GEOMETRY_PREFLIGHT_BLOB_SHA,
        "geometry_preflight_uploaded_sha256": GEOMETRY_PREFLIGHT_UPLOADED_SHA256,
        "acquisition_git_blob_sha": ACQUISITION_BLOB_SHA,
        "git_sha": head,
        "held_out_anatomies": list(HELD_OUT_CASES),
        "planned_cases": len(HELD_OUT_CASES) * N_REPLICATES,
        "complete_cases": sum(bool(row["complete"]) for row in case_rows),
        "assessable_anatomies": assessable_count,
        "known_gt_evaluation_assessable": assessable,
        "known_gt_pointwise_association_positive": False,
        "primary_median_anatomy_spearman": None,
        "primary_positive_anatomies": None,
        "primary_sign_test_n": None,
        "primary_exact_sign_p": None,
        "primary_anatomy_spearman_values": None,
        "primary_bootstrap_95_ci": None,
        "secondary_across_anatomy_medians": secondary_summary,
        "direct_comparators": direct_summary,
        "contrastive_discrepancy": {
            "feasibility_decision": "pending_pre_result_audit",
            "included_in_this_run": False,
        },
    }

    print("\n=== Predeclared known-GT pointwise-informativeness evaluation ===")
    print(f"assessable anatomies: {assessable_count}/10")
    print(f"KNOWN_GT_EVALUATION_ASSESSABLE={assessable}")

    if assessable:
        anatomy_values = [
            float(row["median_case_spearman"]) for row in anatomy_summary if bool(row["assessable"])
        ]
        observed = float(np.median(anatomy_values))
        positives, sign_n, p_value = exact_positive_sign_test(anatomy_summary)
        ci_lo, ci_hi = bootstrap_interval(anatomy_summary)
        positive = positive_association_label(observed, p_value)
        summary.update(
            {
                "known_gt_pointwise_association_positive": positive,
                "primary_median_anatomy_spearman": observed,
                "primary_positive_anatomies": positives,
                "primary_sign_test_n": sign_n,
                "primary_exact_sign_p": p_value,
                "primary_anatomy_spearman_values": anatomy_values,
                "primary_bootstrap_95_ci": [ci_lo, ci_hi],
            }
        )
        print(f"PRIMARY_MEDIAN_ANATOMY_SPEARMAN={observed:.9g}")
        print(f"PRIMARY_POSITIVE_ANATOMIES={positives}/{sign_n}")
        print(f"PRIMARY_EXACT_SIGN_P={p_value:.9g}")
        print(f"PRIMARY_ANATOMY_SPEARMAN_VALUES={anatomy_values}")
        print(f"PRIMARY_BOOTSTRAP_95_CI=[{ci_lo:.9g},{ci_hi:.9g}]")
        print(f"KNOWN_GT_POINTWISE_ASSOCIATION_POSITIVE={positive}")
    else:
        print("KNOWN_GT_POINTWISE_ASSOCIATION_POSITIVE=False -- evaluation not assessable")

    print("\n=== Frozen direct local comparator summaries ===")
    for method in DIRECT_COMPARATOR_METHODS:
        values = direct_summary[method]
        print(
            f"{method.upper()}_ASSESSABLE={values['assessable']} "
            f"anatomies={values['assessable_anatomies']}/10"
        )
        if values["assessable"]:
            print(
                f"{method.upper()}_MEDIAN_ANATOMY_SPEARMAN="
                f"{values['median_anatomy_spearman']:.9g} "
                f"raw_sign_p={values['raw_exact_sign_p']:.9g} "
                f"holm_p={values['holm_adjusted_sign_p']:.9g}"
            )
            if values["paired_target_minus_comparator_median"] is not None:
                print(
                    f"{method.upper()}_PAIRED_TARGET_MINUS_COMPARATOR_MEDIAN="
                    f"{values['paired_target_minus_comparator_median']:.9g}"
                )

    with open(summary_path, "w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    print(f"Case metrics: {case_metrics_path}")
    print(f"Anatomy metrics: {anatomy_metrics_path}")
    print(f"Comparator anatomy metrics: {comparator_anatomy_path}")
    print(f"Machine-readable summary: {summary_path}")


if __name__ == "__main__":
    main()
