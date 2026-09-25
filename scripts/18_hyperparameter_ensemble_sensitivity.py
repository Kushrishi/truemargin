#!/usr/bin/env python3
"""Run the frozen five-patient registration-hyperparameter ensemble gate."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.stats import pearsonr, spearmanr

from truemargin import calibration as cal
from truemargin import ensemble, provenance
from truemargin import io_utils as ioutil
from truemargin import registration as reg

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(REPO_ROOT, "data")
OUT = os.path.join(REPO_ROOT, "outputs")
MANIFEST_ROOT = os.path.join(DATA, "prostate_fused_manifest", "prostate_fused_mri_pathology")
HECAP_DIR = os.path.join(DATA, "hecap")

PROTOCOL_MAIN_SHA = "7e7a33640ae082f748e7bd060f62bf05011bbcf8"
PROTOCOL_PATH = "docs/hyperparameter_ensemble_protocol.md"
MESH_SIZE = 3
MAX_ITERATIONS = 15
CENTER_FIRST = False
LANDMARK_SEED = 0
FLOOR_N = 5
MAX_LANDMARKS_PER_PATIENT = 75
CROP_PAD_VOXELS = 15
NEAR_ZERO_SIGMA_MM = 1e-6
NDIM = 3
NOMINAL_BINS = 50
NOMINAL_GRADIENT_TOLERANCE = 1e-5
METRIC_BINS = (32, 50, 64)
GRADIENT_TOLERANCES = (1e-4, 1e-5, 1e-6)
HYPERPARAMETER_CONFIGS = tuple(
    (metric_bins, gradient_tolerance)
    for metric_bins in METRIC_BINS
    for gradient_tolerance in GRADIENT_TOLERANCES
)

CASES = {
    "aaa0054": {"t2_series": "69199", "dce_series": "56739"},
    "aaa0059": {"t2_series": "38468", "dce_series": "30585"},
    "aaa0061": {"t2_series": "93002", "dce_series": "82463"},
    "aaa0063": {"t2_series": "78011", "dce_series": "48684"},
    "aaa0066": {"t2_series": "67726", "dce_series": "52406"},
}


def find_series_dir(patient: str, series_id: str) -> str:
    patient_dir = os.path.join(MANIFEST_ROOT, patient)
    study = os.listdir(patient_dir)[0]
    return os.path.join(patient_dir, study, series_id)


def load_series(series_dir: str) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(series_dir)
    reader.SetFileNames(files)
    return reader.Execute()


def landmark_physical_points(mask_img: sitk.Image, seed: int, max_points: int) -> np.ndarray:
    mask = sitk.GetArrayFromImage(mask_img)
    voxel_idx = np.argwhere(mask > 0)
    rng = np.random.default_rng(seed)
    if len(voxel_idx) > max_points:
        chosen = rng.choice(len(voxel_idx), size=max_points, replace=False)
        voxel_idx = voxel_idx[chosen]
    return np.array(
        [mask_img.TransformIndexToPhysicalPoint((int(x), int(y), int(z))) for z, y, x in voxel_idx]
    )


def crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent_mm = (
        shape_zyx[2] * spacing_xyz[0],
        shape_zyx[1] * spacing_xyz[1],
        shape_zyx[0] * spacing_xyz[2],
    )
    return float(np.sqrt(sum(float(value) ** 2 for value in extent_mm)))


def mean_displacement_magnitude(field: np.ndarray) -> float:
    return float(np.sqrt(np.sum(field * field, axis=0)).mean())


def config_id(metric_bins: int, gradient_tolerance: float) -> str:
    tolerance_label = f"{gradient_tolerance:.0e}".replace("-", "m").replace("+", "p")
    return f"bins_{metric_bins}_gtol_{tolerance_label}"


def _safe_correlation(x: np.ndarray, y: np.ndarray, *, rank: bool) -> float:
    if len(x) < 2 or float(np.std(x)) <= NEAR_ZERO_SIGMA_MM or float(np.std(y)) <= 1e-12:
        return float("nan")
    result = spearmanr(x, y) if rank else pearsonr(x, y)
    return float(result.statistic)


def _iqr(values: np.ndarray) -> float:
    q25, q75 = np.percentile(values, [25, 75])
    return float(q75 - q25)


def pointwise_metrics(err: np.ndarray, sigma: np.ndarray) -> dict[str, float]:
    sigma_q25, sigma_q75 = np.percentile(sigma, [25, 75])
    err_q75 = float(np.percentile(err, 75))
    high_sigma = sigma >= sigma_q75
    low_sigma = sigma <= sigma_q25
    blind_spot = (err >= err_q75) & low_sigma
    sigma_mean = float(np.mean(sigma))

    return {
        "sigma_median_mm": float(np.median(sigma)),
        "sigma_iqr_mm": _iqr(sigma),
        "sigma_near_zero_fraction": float(np.mean(sigma <= NEAR_ZERO_SIGMA_MM)),
        "sigma_cv": (
            float(np.std(sigma) / sigma_mean)
            if abs(sigma_mean) > NEAR_ZERO_SIGMA_MM
            else float("nan")
        ),
        "proxy_error_median_mm": float(np.median(err)),
        "proxy_error_mean_mm": float(np.mean(err)),
        "proxy_error_p90_mm": float(np.percentile(err, 90)),
        "spearman_sigma_proxy_error": _safe_correlation(sigma, err, rank=True),
        "pearson_sigma_proxy_error": _safe_correlation(sigma, err, rank=False),
        "quartile_proxy_error_delta_mm": float(
            np.median(err[high_sigma]) - np.median(err[low_sigma])
        ),
        "blind_spot_rate": float(np.mean(blind_spot)),
    }


def _prepare_patient(patient: str, series: Mapping[str, str], seed: int) -> dict[str, Any]:
    t2_dir = find_series_dir(patient, series["t2_series"])
    dce_dir = find_series_dir(patient, series["dce_series"])
    mask_path = os.path.join(HECAP_DIR, f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha")
    if not os.path.exists(mask_path):
        raise SystemExit(f"Missing HECaP mask: {mask_path}")

    t2_img = load_series(t2_dir)
    dce_img = ioutil.load_dce_single_phase(dce_dir)
    mask_img = sitk.ReadImage(mask_path)
    ioutil.assert_same_grid(mask_img, t2_img, "HECaP mask", "T2 image")

    points = landmark_physical_points(mask_img, seed=seed, max_points=MAX_LANDMARKS_PER_PATIENT)
    dce_on_t2 = sitk.Resample(dce_img, t2_img, sitk.Transform(), sitk.sitkLinear, 0.0)

    fixed = sitk.GetArrayFromImage(t2_img).astype(np.float32)
    moving = sitk.GetArrayFromImage(dce_on_t2).astype(np.float32)
    mask = sitk.GetArrayFromImage(mask_img)
    spacing = tuple(float(value) for value in t2_img.GetSpacing())

    idx_xyz = np.array(
        [t2_img.TransformPhysicalPointToContinuousIndex(tuple(point)) for point in points]
    )
    idx_zyx = np.round(idx_xyz[:, ::-1]).astype(int)
    fixed_crop, moving_crop, idx_crop = ioutil.crop_to_mask_bbox(
        fixed,
        moving,
        mask,
        idx_zyx,
        pad=CROP_PAD_VOXELS,
    )

    return {
        "fixed": fixed_crop,
        "moving": moving_crop,
        "idx_crop": idx_crop,
        "spacing": spacing,
        "crop_diagonal_mm": crop_diagonal_mm(fixed_crop.shape, spacing),
    }


def _manifest(
    *,
    patient: str,
    series: Mapping[str, str],
    kind: str,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "kind": kind,
        "mesh_size": MESH_SIZE,
        "max_iterations": MAX_ITERATIONS,
        "center_first": CENTER_FIRST,
        "landmark_seed": LANDMARK_SEED,
        "max_landmarks_per_patient": MAX_LANDMARKS_PER_PATIENT,
        "crop_pad_voxels": CROP_PAD_VOXELS,
        "dce_phase_strategy": "per-slice middle temporal phase",
        "dce_phase_fraction": 0.5,
        "true_displacement_reference": "zero-displacement proxy",
        "member_failure_policy": [
            "registration_exception",
            "nonfinite_displacement",
            "shape_mismatch",
            "mean_displacement_exceeds_crop_physical_diagonal",
        ],
    }
    if kind == "floor":
        parameters.update(
            {
                "ensemble_n": FLOOR_N,
                "metric_bins": NOMINAL_BINS,
                "gradient_convergence_tolerance": NOMINAL_GRADIENT_TOLERANCE,
            }
        )
    elif kind == "grid":
        parameters["configs"] = [
            {
                "metric_bins": metric_bins,
                "gradient_convergence_tolerance": gradient_tolerance,
            }
            for metric_bins, gradient_tolerance in HYPERPARAMETER_CONFIGS
        ]
    else:
        raise ValueError(f"unsupported manifest kind: {kind!r}")

    return provenance.build_manifest(
        repo_root=REPO_ROOT,
        experiment="real-prostate-hyperparameter-ensemble-v1",
        artifact_id=f"{patient}:hyperparameter_ensemble:{kind}",
        parameters=parameters,
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "sensitivity_cohort": list(CASES),
            "patient": patient,
            "t2_series": series["t2_series"],
            "dce_series": series["dce_series"],
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=[
            "scripts/18_hyperparameter_ensemble_sensitivity.py",
            PROTOCOL_PATH,
            "src/truemargin/registration.py",
            "src/truemargin/ensemble.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def _run_one_registration(
    *,
    fixed: np.ndarray,
    moving: np.ndarray,
    spacing: tuple[float, ...],
    expected_shape: tuple[int, ...],
    diagonal: float,
    metric_bins: int,
    gradient_tolerance: float,
) -> tuple[np.ndarray | None, str, float]:
    try:
        field = reg.baseline_bspline_registration(
            fixed,
            moving,
            mesh_size=MESH_SIZE,
            max_iterations=MAX_ITERATIONS,
            spacing=spacing,
            center_first=CENTER_FIRST,
            metric_bins=metric_bins,
            gradient_convergence_tolerance=gradient_tolerance,
        )
    except Exception as exc:
        return None, f"registration_exception:{type(exc).__name__}:{exc}", float("nan")

    reason = ensemble.validate_member_field(
        field,
        expected_shape=expected_shape,
        crop_diagonal_mm=diagonal,
    )
    mean_displacement = float("nan")
    if field.shape == expected_shape and np.isfinite(field).all():
        mean_displacement = mean_displacement_magnitude(field)
    if reason is not None:
        return None, reason, mean_displacement
    return field, "ok", mean_displacement


def _summarize_complete_fields(
    fields: list[np.ndarray],
    idx_crop: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    u_mean, sigma = ensemble.summarize_fields(fields)
    u_est = ioutil.sample_field_at_points(u_mean, idx_crop)
    sigma_at = ioutil.sample_field_at_points(sigma, idx_crop)
    err = cal.displacement_error(u_est, np.zeros_like(u_est))
    return np.asarray(err), np.asarray(sigma_at)


def _run_floor(
    *,
    patient: str,
    series: Mapping[str, str],
    prepared: Mapping[str, Any],
    checkpoint_root: str,
) -> Mapping[str, np.ndarray]:
    fixed = np.asarray(prepared["fixed"])
    moving = np.asarray(prepared["moving"])
    idx_crop = np.asarray(prepared["idx_crop"])
    spacing = tuple(float(value) for value in prepared["spacing"])
    diagonal = float(prepared["crop_diagonal_mm"])
    expected_shape = (NDIM, *fixed.shape)

    checkpoint_dir = os.path.join(checkpoint_root, "repeatability_floor")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"{patient}.npz")
    manifest = _manifest(patient=patient, series=series, kind="floor")
    if os.path.exists(checkpoint_path):
        print("  floor: loading validated checkpoint")
        return provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)

    fields: list[np.ndarray] = []
    member_reasons = np.full(FLOOR_N, "not_run", dtype="U1024")
    member_mean_displacement = np.full(FLOOR_N, np.nan, dtype=np.float64)

    for member_index in range(FLOOR_N):
        field, reason, mean_displacement = _run_one_registration(
            fixed=fixed,
            moving=moving,
            spacing=spacing,
            expected_shape=expected_shape,
            diagonal=diagonal,
            metric_bins=NOMINAL_BINS,
            gradient_tolerance=NOMINAL_GRADIENT_TOLERANCE,
        )
        member_reasons[member_index] = reason
        member_mean_displacement[member_index] = mean_displacement
        if field is None:
            print(f"    floor member {member_index}: FAILED {reason}")
            continue
        fields.append(field)

    failed_count = int(np.sum(member_reasons != "ok"))
    complete = failed_count == 0 and len(fields) == FLOOR_N
    arrays: dict[str, np.ndarray] = {
        "complete": np.asarray(complete),
        "err": np.asarray([], dtype=np.float64),
        "sigma": np.asarray([], dtype=np.float64),
        "member_reasons": member_reasons,
        "member_mean_displacement_mm": member_mean_displacement,
        "failed_member_count": np.asarray(failed_count, dtype=np.int64),
        "spacing_xyz_mm": np.asarray(spacing, dtype=np.float64),
        "crop_diagonal_mm": np.asarray(diagonal, dtype=np.float64),
        "n_landmarks": np.asarray(len(idx_crop), dtype=np.int64),
    }
    if complete:
        err, sigma = _summarize_complete_fields(fields, idx_crop)
        arrays["err"] = err
        arrays["sigma"] = sigma

    provenance.save_checkpoint(checkpoint_path, arrays=arrays, manifest=manifest)
    return arrays


def _run_grid(
    *,
    patient: str,
    series: Mapping[str, str],
    prepared: Mapping[str, Any],
    checkpoint_root: str,
) -> Mapping[str, np.ndarray]:
    fixed = np.asarray(prepared["fixed"])
    moving = np.asarray(prepared["moving"])
    idx_crop = np.asarray(prepared["idx_crop"])
    spacing = tuple(float(value) for value in prepared["spacing"])
    diagonal = float(prepared["crop_diagonal_mm"])
    expected_shape = (NDIM, *fixed.shape)

    checkpoint_dir = os.path.join(checkpoint_root, "grid")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"{patient}.npz")
    manifest = _manifest(patient=patient, series=series, kind="grid")
    if os.path.exists(checkpoint_path):
        print("  grid: loading validated checkpoint")
        return provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)

    n_configs = len(HYPERPARAMETER_CONFIGS)
    fields: list[np.ndarray] = []
    member_reasons = np.full(n_configs, "not_run", dtype="U1024")
    member_mean_displacement = np.full(n_configs, np.nan, dtype=np.float64)
    config_bins = np.asarray([item[0] for item in HYPERPARAMETER_CONFIGS], dtype=np.int64)
    config_tolerances = np.asarray(
        [item[1] for item in HYPERPARAMETER_CONFIGS],
        dtype=np.float64,
    )

    for member_index, (metric_bins, gradient_tolerance) in enumerate(HYPERPARAMETER_CONFIGS):
        field, reason, mean_displacement = _run_one_registration(
            fixed=fixed,
            moving=moving,
            spacing=spacing,
            expected_shape=expected_shape,
            diagonal=diagonal,
            metric_bins=metric_bins,
            gradient_tolerance=gradient_tolerance,
        )
        member_reasons[member_index] = reason
        member_mean_displacement[member_index] = mean_displacement
        if field is None:
            print(
                "    grid member "
                f"{member_index} ({config_id(metric_bins, gradient_tolerance)}): "
                f"FAILED {reason}"
            )
            continue
        fields.append(field)

    failed_count = int(np.sum(member_reasons != "ok"))
    complete = failed_count == 0 and len(fields) == n_configs
    arrays: dict[str, np.ndarray] = {
        "complete": np.asarray(complete),
        "err": np.asarray([], dtype=np.float64),
        "sigma": np.asarray([], dtype=np.float64),
        "member_reasons": member_reasons,
        "member_mean_displacement_mm": member_mean_displacement,
        "failed_member_count": np.asarray(failed_count, dtype=np.int64),
        "config_metric_bins": config_bins,
        "config_gradient_tolerance": config_tolerances,
        "spacing_xyz_mm": np.asarray(spacing, dtype=np.float64),
        "crop_diagonal_mm": np.asarray(diagonal, dtype=np.float64),
        "n_landmarks": np.asarray(len(idx_crop), dtype=np.int64),
    }
    if complete:
        err, sigma = _summarize_complete_fields(fields, idx_crop)
        arrays["err"] = err
        arrays["sigma"] = sigma

    provenance.save_checkpoint(checkpoint_path, arrays=arrays, manifest=manifest)
    return arrays


def _prefixed_metrics(prefix: str, result: Mapping[str, np.ndarray]) -> dict[str, Any]:
    output: dict[str, Any] = {
        f"{prefix}_complete": bool(np.asarray(result["complete"]).item()),
        f"{prefix}_failed_member_count": int(np.asarray(result["failed_member_count"]).item()),
        f"{prefix}_member_reasons": " | ".join(str(value) for value in result["member_reasons"]),
    }
    if output[f"{prefix}_complete"]:
        output.update(
            {
                f"{prefix}_{key}": value
                for key, value in pointwise_metrics(
                    np.asarray(result["err"]),
                    np.asarray(result["sigma"]),
                ).items()
            }
        )
    return output


def build_patient_row(
    *,
    patient: str,
    floor_result: Mapping[str, np.ndarray],
    grid_result: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    spacing = np.asarray(floor_result["spacing_xyz_mm"], dtype=float)
    row: dict[str, Any] = {
        "patient": patient,
        "spacing_min_mm": float(np.min(spacing)),
        "spacing_max_mm": float(np.max(spacing)),
        "crop_diagonal_mm": float(np.asarray(floor_result["crop_diagonal_mm"]).item()),
        "n_landmarks": int(np.asarray(floor_result["n_landmarks"]).item()),
    }
    row.update(_prefixed_metrics("floor", floor_result))
    row.update(_prefixed_metrics("grid", grid_result))
    return row


def evaluate_hyperparameter_gate(
    rows: list[dict[str, Any]],
) -> tuple[bool, int, int, int, list[dict[str, Any]]]:
    floor_complete = sum(bool(row["floor_complete"]) for row in rows)
    shared_complete = 0
    non_inert_count = 0
    diagnostics: list[dict[str, Any]] = []

    for row in rows:
        shared = bool(row["floor_complete"] and row["grid_complete"])
        required_signal = float("nan")
        non_inert = False
        if shared:
            shared_complete += 1
            floor_sigma = float(row["floor_sigma_median_mm"])
            resolution_floor = 0.25 * float(row["spacing_min_mm"])
            required_signal = max(3.0 * floor_sigma, resolution_floor)
            non_inert = float(row["grid_sigma_median_mm"]) >= required_signal
            non_inert_count += int(non_inert)

        diagnostics.append(
            {
                "patient": row["patient"],
                "shared_complete": shared,
                "required_signal_mm": required_signal,
                "non_inert": non_inert,
            }
        )

    eligible = floor_complete >= 4 and shared_complete >= 4 and non_inert_count >= 4
    return eligible, floor_complete, shared_complete, non_inert_count, diagnostics


def _write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    preferred = [
        "patient",
        "spacing_min_mm",
        "spacing_max_mm",
        "crop_diagonal_mm",
        "n_landmarks",
        "floor_complete",
        "floor_failed_member_count",
        "floor_sigma_median_mm",
        "grid_complete",
        "grid_failed_member_count",
        "grid_sigma_median_mm",
    ]
    all_fields = set().union(*(row.keys() for row in rows))
    fields = [field for field in preferred if field in all_fields]
    fields.extend(sorted(all_fields - set(fields)))
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    head = provenance.current_git_sha(REPO_ROOT)
    checkpoint_root = os.path.join(OUT, "checkpoints", "hyperparameter_ensemble_sensitivity")
    os.makedirs(checkpoint_root, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    print("=== TrueMargin prospective hyperparameter-ensemble sensitivity ===")
    print(f"Git SHA: {head}")
    print(f"Protocol main SHA: {PROTOCOL_MAIN_SHA}")
    print(f"Protocol: {PROTOCOL_PATH}")
    print(f"Patients: {list(CASES)}")
    print(f"Metric bins: {METRIC_BINS}")
    print(f"Gradient tolerances: {GRADIENT_TOLERANCES}")
    print(f"Hyperparameter configurations: {len(HYPERPARAMETER_CONFIGS)}")
    print(
        f"Registration: mesh={MESH_SIZE}, max_iterations={MAX_ITERATIONS}, "
        f"center_first={CENTER_FIRST}, floor_repeats={FLOOR_N}"
    )
    print(
        "Proxy error and association metrics are descriptive only and cannot "
        "promote the mechanism."
    )

    rows: list[dict[str, Any]] = []

    for patient, series in CASES.items():
        print(f"\n--- {patient}: preparing real-data inputs ---")
        prepared = _prepare_patient(patient, series, seed=LANDMARK_SEED)
        print(
            f"  crop={np.asarray(prepared['fixed']).shape}, "
            f"spacing={prepared['spacing']}, "
            f"diagonal={float(prepared['crop_diagonal_mm']):.3f} mm"
        )

        print(f"  nominal floor: running/validating {FLOOR_N} repeats")
        floor_result = _run_floor(
            patient=patient,
            series=series,
            prepared=prepared,
            checkpoint_root=checkpoint_root,
        )
        if bool(np.asarray(floor_result["complete"]).item()):
            floor_metrics = pointwise_metrics(
                np.asarray(floor_result["err"]),
                np.asarray(floor_result["sigma"]),
            )
            print(
                "    floor complete=5/5: " f"sigma median={floor_metrics['sigma_median_mm']:.6g} mm"
            )
        else:
            failed = int(np.asarray(floor_result["failed_member_count"]).item())
            print(f"    floor complete=NO: failed_members={failed}")

        print(f"  hyperparameter grid: running/validating {len(HYPERPARAMETER_CONFIGS)} configs")
        grid_result = _run_grid(
            patient=patient,
            series=series,
            prepared=prepared,
            checkpoint_root=checkpoint_root,
        )
        if bool(np.asarray(grid_result["complete"]).item()):
            grid_metrics = pointwise_metrics(
                np.asarray(grid_result["err"]),
                np.asarray(grid_result["sigma"]),
            )
            print(
                f"    grid complete={len(HYPERPARAMETER_CONFIGS)}/{len(HYPERPARAMETER_CONFIGS)}: "
                f"sigma median={grid_metrics['sigma_median_mm']:.6g} mm, "
                f"proxy-error median={grid_metrics['proxy_error_median_mm']:.6g} mm"
            )
        else:
            failed = int(np.asarray(grid_result["failed_member_count"]).item())
            print(f"    grid complete=NO: failed_configs={failed}")

        rows.append(
            build_patient_row(
                patient=patient,
                floor_result=floor_result,
                grid_result=grid_result,
            )
        )

    eligible, floor_complete, shared_complete, non_inert_count, diagnostics = (
        evaluate_hyperparameter_gate(rows)
    )

    metrics_path = os.path.join(OUT, "hyperparameter_ensemble_sensitivity_patient_metrics.csv")
    summary_path = os.path.join(OUT, "hyperparameter_ensemble_sensitivity_summary.json")
    _write_csv(metrics_path, rows)

    summary = {
        "experiment": "real-prostate-hyperparameter-ensemble-v1",
        "git_sha": head,
        "protocol_main_sha": PROTOCOL_MAIN_SHA,
        "protocol_path": PROTOCOL_PATH,
        "patients": list(CASES),
        "mesh_size": MESH_SIZE,
        "max_iterations": MAX_ITERATIONS,
        "center_first": CENTER_FIRST,
        "floor_n": FLOOR_N,
        "metric_bins": list(METRIC_BINS),
        "gradient_tolerances": list(GRADIENT_TOLERANCES),
        "hyperparameter_configs": [
            {
                "metric_bins": metric_bins,
                "gradient_convergence_tolerance": gradient_tolerance,
            }
            for metric_bins, gradient_tolerance in HYPERPARAMETER_CONFIGS
        ],
        "ground_truth_status": (
            "zero-displacement proxy/reference assumption; not verified pointwise GT; "
            "proxy error excluded from mechanism promotion"
        ),
        "floor_complete_patients": floor_complete,
        "shared_complete_patients": shared_complete,
        "non_inert_patients": non_inert_count,
        "hyperparameter_ensemble_eligible": eligible,
        "patient_gate_diagnostics": diagnostics,
        "selection_rule": (
            "floor complete in >=4/5; >=4 shared complete floor+grid patients; "
            ">=4 shared patients with grid median sigma >= "
            "max(3*floor median sigma, 0.25*min spacing)"
        ),
        "rows": rows,
    }
    with open(summary_path, "w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("\n=== Predeclared hyperparameter-ensemble gate ===")
    print(f"nominal repeatability-floor complete: {floor_complete}/5")
    print(f"hyperparameter grid shared complete: {shared_complete}/5")
    print(f"hyperparameter grid non_inert: {non_inert_count}/5")
    print(f"HYPERPARAMETER_ENSEMBLE_ELIGIBLE={eligible}")
    if eligible:
        print("Next stage: freeze this exact nine-member grid for independent evaluation.")
    else:
        print(
            "Stop this mechanism; do not widen the grid, vary mesh/iterations, "
            "or select a favorable subset post hoc."
        )
    print(f"Patient metrics: {metrics_path}")
    print(f"Machine-readable summary: {summary_path}")


if __name__ == "__main__":
    main()
