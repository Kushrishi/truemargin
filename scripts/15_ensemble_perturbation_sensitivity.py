#!/usr/bin/env python3
"""Run the prospective five-patient ensemble perturbation sensitivity study.

This script implements the experiment frozen in
``docs/ensemble_baseline_protocol.md``. It is deliberately separate from the
15-patient production runner: these outputs are sensitivity evidence used to choose
whether the corrected perturbation is non-inert and stable, not final cohort results.

The real-data error uses the existing zero-displacement proxy/reference assumption.
It is not independently verified pointwise T2-to-DCE registration ground truth.
"""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping
from typing import Any

import numpy as np
import SimpleITK as sitk
import yaml
from scipy.stats import pearsonr, spearmanr

from truemargin import calibration as cal
from truemargin import checkpoint_specs as ckptspec
from truemargin import ensemble, provenance
from truemargin import io_utils as ioutil
from truemargin import registration as reg

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(REPO_ROOT, "data")
OUT = os.path.join(REPO_ROOT, "outputs")
MANIFEST_ROOT = os.path.join(DATA, "prostate_fused_manifest", "prostate_fused_mri_pathology")
HECAP_DIR = os.path.join(DATA, "hecap")

PROTOCOL_MAIN_SHA = "fe90dac687b1f847e7f98cb7d9d3a13c172c9f96"
MODE = "fast_dev"
EXPECTED_MESH_SIZE = 3
EXPECTED_MAX_ITERATIONS = 15
EXPECTED_SEED = 0
ENSEMBLE_N = 5
MAX_LANDMARKS_PER_PATIENT = 75
CROP_PAD_VOXELS = 15
NEAR_ZERO_SIGMA_MM = 1e-6
NDIM = 3

# Frozen before corrected results. Do not alter this subset after observing results
# without a dated amendment to docs/ensemble_baseline_protocol.md.
CASES = {
    "aaa0054": {"t2_series": "69199", "dce_series": "56739"},
    "aaa0059": {"t2_series": "38468", "dce_series": "30585"},
    "aaa0061": {"t2_series": "93002", "dce_series": "82463"},
    "aaa0063": {"t2_series": "78011", "dce_series": "48684"},
    "aaa0066": {"t2_series": "67726", "dce_series": "52406"},
}

# Frozen six-condition perturbation grid. The legacy absolute setting is a historical
# control and is never eligible for corrected-alpha selection.
SETTINGS = (
    ("relative_std", 0.00),
    ("relative_std", 0.01),
    ("relative_std", 0.02),
    ("relative_std", 0.05),
    ("relative_std", 0.10),
    ("absolute_intensity", 0.02),
)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def find_series_dir(patient: str, series_id: str) -> str:
    pdir = os.path.join(MANIFEST_ROOT, patient)
    study = os.listdir(pdir)[0]
    return os.path.join(pdir, study, series_id)


def load_series(series_dir: str) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(series_dir)
    reader.SetFileNames(files)
    return reader.Execute()


def landmark_physical_points(mask_img: sitk.Image, seed: int, max_points: int) -> np.ndarray:
    """Match script 04's deterministic HECaP landmark sampling exactly."""
    mask = sitk.GetArrayFromImage(mask_img)
    voxel_idx = np.argwhere(mask > 0)
    rng = np.random.default_rng(seed)
    if len(voxel_idx) > max_points:
        chosen = rng.choice(len(voxel_idx), size=max_points, replace=False)
        voxel_idx = voxel_idx[chosen]
    return np.array(
        [mask_img.TransformIndexToPhysicalPoint((int(x), int(y), int(z))) for z, y, x in voxel_idx]
    )


def setting_id(perturbation: str, scale: float) -> str:
    scale_text = f"{scale:.2f}".replace(".", "p")
    return f"{perturbation}_{scale_text}"


def crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent_mm = (
        shape_zyx[2] * spacing_xyz[0],
        shape_zyx[1] * spacing_xyz[1],
        shape_zyx[0] * spacing_xyz[2],
    )
    return float(np.sqrt(sum(float(e) ** 2 for e in extent_mm)))


def mean_displacement_magnitude(field: np.ndarray) -> float:
    return float(np.sqrt(np.sum(field * field, axis=0)).mean())


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
        "error_median_mm": float(np.median(err)),
        "error_mean_mm": float(np.mean(err)),
        "error_p90_mm": float(np.percentile(err, 90)),
        "spearman_sigma_error": _safe_correlation(sigma, err, rank=True),
        "pearson_sigma_error": _safe_correlation(sigma, err, rank=False),
        "quartile_error_delta_mm": float(np.median(err[high_sigma]) - np.median(err[low_sigma])),
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

    t2_arr = sitk.GetArrayFromImage(t2_img).astype(np.float32)
    dce_arr = sitk.GetArrayFromImage(dce_on_t2).astype(np.float32)
    mask_arr = sitk.GetArrayFromImage(mask_img)
    spacing = tuple(float(v) for v in t2_img.GetSpacing())

    idx = np.array(
        [t2_img.TransformPhysicalPointToContinuousIndex(tuple(point)) for point in points]
    )
    idx_zyx = np.round(idx[:, ::-1]).astype(int)
    t2_crop, dce_crop, idx_crop = ioutil.crop_to_mask_bbox(
        t2_arr,
        dce_arr,
        mask_arr,
        idx_zyx,
        pad=CROP_PAD_VOXELS,
    )

    return {
        "fixed": t2_crop,
        "moving": dce_crop,
        "idx_crop": idx_crop,
        "spacing": spacing,
        "crop_diagonal_mm": crop_diagonal_mm(t2_crop.shape, spacing),
    }


def _run_patient_setting(
    *,
    patient: str,
    series: Mapping[str, str],
    prepared: Mapping[str, Any],
    perturbation: str,
    perturbation_scale: float,
    mode_cfg: Mapping[str, Any],
    seed: int,
    checkpoint_root: str,
) -> dict[str, np.ndarray]:
    sid = setting_id(perturbation, perturbation_scale)
    checkpoint_dir = os.path.join(checkpoint_root, sid)
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"{patient}.npz")
    manifest = ckptspec.ensemble_sensitivity_manifest(
        repo_root=REPO_ROOT,
        patient=patient,
        t2_series=series["t2_series"],
        dce_series=series["dce_series"],
        mode_cfg=mode_cfg,
        seed=seed,
        max_landmarks=MAX_LANDMARKS_PER_PATIENT,
        ensemble_n=ENSEMBLE_N,
        perturbation=perturbation,
        perturbation_scale=perturbation_scale,
        near_zero_sigma=NEAR_ZERO_SIGMA_MM,
    )
    if os.path.exists(checkpoint_path):
        print(f"  {sid}: loading validated checkpoint")
        return provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)

    fixed = np.asarray(prepared["fixed"])
    moving = np.asarray(prepared["moving"])
    spacing = tuple(prepared["spacing"])
    diagonal = float(prepared["crop_diagonal_mm"])
    idx_crop = np.asarray(prepared["idx_crop"])
    expected_shape = (fixed.ndim, *fixed.shape)

    fixed_std = float(np.std(fixed))
    moving_std = float(np.std(moving))
    fixed_noise_sd, moving_noise_sd = ensemble.perturbation_noise_scales(
        fixed,
        moving,
        perturbation=perturbation,  # type: ignore[arg-type]
        perturbation_scale=perturbation_scale,
    )

    fields: list[np.ndarray] = []
    member_mean_displacement = np.full(ENSEMBLE_N, np.nan, dtype=np.float64)
    member_reasons = ["not_run"] * ENSEMBLE_N

    for member_i, (fixed_perturbed, moving_perturbed) in enumerate(
        ensemble.perturbed_inputs(
            fixed,
            moving,
            n=ENSEMBLE_N,
            perturbation=perturbation,  # type: ignore[arg-type]
            perturbation_scale=perturbation_scale,
            seed=seed,
        )
    ):
        try:
            field = reg.baseline_bspline_registration(
                fixed_perturbed,
                moving_perturbed,
                mesh_size=int(mode_cfg["mesh_size"]),
                max_iterations=int(mode_cfg["max_iterations"]),
                spacing=spacing,
            )
        except Exception as exc:
            member_reasons[member_i] = f"registration_exception:{type(exc).__name__}:{exc}"
            print(f"    member {member_i}: FAILED registration exception")
            continue

        reason = ensemble.validate_member_field(
            field,
            expected_shape=expected_shape,
            crop_diagonal_mm=diagonal,
        )
        if field.shape == expected_shape and np.isfinite(field).all():
            member_mean_displacement[member_i] = mean_displacement_magnitude(field)
        if reason is not None:
            member_reasons[member_i] = reason
            print(f"    member {member_i}: FAILED {reason}")
            continue

        member_reasons[member_i] = "ok"
        fields.append(field)

    failed_count = sum(reason != "ok" for reason in member_reasons)
    complete = failed_count == 0 and len(fields) == ENSEMBLE_N

    arrays: dict[str, np.ndarray] = {
        "complete": np.asarray(complete),
        "err": np.asarray([], dtype=np.float64),
        "sigma": np.asarray([], dtype=np.float64),
        "member_mean_displacement_mm": member_mean_displacement,
        "member_reasons": np.asarray(member_reasons, dtype="U1024"),
        "failed_member_count": np.asarray(failed_count, dtype=np.int64),
        "fixed_std": np.asarray(fixed_std),
        "moving_std": np.asarray(moving_std),
        "fixed_noise_sd": np.asarray(fixed_noise_sd),
        "moving_noise_sd": np.asarray(moving_noise_sd),
        "crop_diagonal_mm": np.asarray(diagonal),
        "n_landmarks": np.asarray(len(idx_crop), dtype=np.int64),
    }

    if complete:
        u_mean, sigma = ensemble.summarize_fields(fields)
        u_est = ioutil.sample_field_at_points(u_mean, idx_crop)
        sigma_at = ioutil.sample_field_at_points(sigma, idx_crop)
        err = cal.displacement_error(u_est, np.zeros_like(u_est))
        arrays["err"] = np.asarray(err)
        arrays["sigma"] = np.asarray(sigma_at)

    provenance.save_checkpoint(checkpoint_path, arrays=arrays, manifest=manifest)
    return arrays


def _base_row(
    *,
    patient: str,
    perturbation: str,
    perturbation_scale: float,
    result: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    complete = bool(np.asarray(result["complete"]).item())
    row: dict[str, Any] = {
        "patient": patient,
        "setting": setting_id(perturbation, perturbation_scale),
        "perturbation": perturbation,
        "perturbation_scale": float(perturbation_scale),
        "ensemble_n": ENSEMBLE_N,
        "complete": complete,
        "failed_member_count": int(np.asarray(result["failed_member_count"]).item()),
        "fixed_std": float(np.asarray(result["fixed_std"]).item()),
        "moving_std": float(np.asarray(result["moving_std"]).item()),
        "fixed_noise_sd": float(np.asarray(result["fixed_noise_sd"]).item()),
        "moving_noise_sd": float(np.asarray(result["moving_noise_sd"]).item()),
        "crop_diagonal_mm": float(np.asarray(result["crop_diagonal_mm"]).item()),
        "n_landmarks": int(np.asarray(result["n_landmarks"]).item()),
        "member_reasons": " | ".join(str(v) for v in result["member_reasons"]),
        "lopo_calibration_status": "not_evaluated",
    }
    if complete:
        row.update(pointwise_metrics(np.asarray(result["err"]), np.asarray(result["sigma"])))
    return row


def _add_calibration_metrics(
    rows: list[dict[str, Any]],
    results: Mapping[tuple[str, str], Mapping[str, np.ndarray]],
    curve_levels: np.ndarray,
) -> None:
    for perturbation, scale in SETTINGS:
        sid = setting_id(perturbation, scale)
        complete_patients = [
            patient
            for patient in CASES
            if bool(np.asarray(results[(patient, sid)]["complete"]).item())
        ]
        for patient in complete_patients:
            row = next(r for r in rows if r["patient"] == patient and r["setting"] == sid)
            err = np.asarray(results[(patient, sid)]["err"])
            sigma = np.asarray(results[(patient, sid)]["sigma"])

            lv, empirical = cal.reliability_curve(err, sigma, ndim=NDIM, levels=curve_levels)
            row["raw_ece"] = cal.expected_calibration_error(lv, empirical)
            row["raw_coverage_90"] = cal.empirical_coverage(err, sigma, 0.90, ndim=NDIM)

            other_patients = [p for p in complete_patients if p != patient]
            if not other_patients:
                row["lopo_calibration_status"] = "insufficient_other_patients"
                continue
            fit_err = np.concatenate([np.asarray(results[(p, sid)]["err"]) for p in other_patients])
            fit_sigma = np.concatenate(
                [np.asarray(results[(p, sid)]["sigma"]) for p in other_patients]
            )
            try:
                scale_factor = cal.fit_variance_scale(fit_err, fit_sigma, ndim=NDIM)
            except ValueError as exc:
                row["lopo_calibration_status"] = f"fit_failed:{exc}"
                continue

            calibrated_sigma = scale_factor * sigma
            lv_cal, empirical_cal = cal.reliability_curve(
                err,
                calibrated_sigma,
                ndim=NDIM,
                levels=curve_levels,
            )
            radii_90 = cal.coverage_radius(calibrated_sigma, 0.90, ndim=NDIM)
            row.update(
                {
                    "lopo_calibration_status": "ok",
                    "lopo_scale": float(scale_factor),
                    "lopo_ece": cal.expected_calibration_error(lv_cal, empirical_cal),
                    "lopo_coverage_90": cal.empirical_coverage(
                        err,
                        calibrated_sigma,
                        0.90,
                        ndim=NDIM,
                    ),
                    "lopo_radius90_median_mm": float(np.median(radii_90)),
                    "lopo_radius90_iqr_mm": _iqr(radii_90),
                }
            )


def _relative_row(rows: list[dict[str, Any]], patient: str, alpha: float) -> dict[str, Any]:
    sid = setting_id("relative_std", alpha)
    return next(row for row in rows if row["patient"] == patient and row["setting"] == sid)


def select_alpha(rows: list[dict[str, Any]]) -> tuple[float | None, list[dict[str, Any]]]:
    diagnostics = []
    for alpha in (0.01, 0.02, 0.05, 0.10):
        complete_count = 0
        above_floor_count = 0
        shared_error_pairs = []

        for patient in CASES:
            baseline = _relative_row(rows, patient, 0.00)
            candidate = _relative_row(rows, patient, alpha)
            if candidate["complete"]:
                complete_count += 1
            if not (baseline["complete"] and candidate["complete"]):
                continue

            floor = float(baseline["sigma_median_mm"])
            candidate_sigma = float(candidate["sigma_median_mm"])
            if floor <= NEAR_ZERO_SIGMA_MM:
                above_floor = candidate_sigma > NEAR_ZERO_SIGMA_MM
            else:
                above_floor = candidate_sigma >= 3.0 * floor
            above_floor_count += int(above_floor)
            shared_error_pairs.append(
                (float(baseline["error_median_mm"]), float(candidate["error_median_mm"]))
            )

        shared_count = len(shared_error_pairs)
        if shared_count:
            baseline_error = float(np.median([pair[0] for pair in shared_error_pairs]))
            candidate_error = float(np.median([pair[1] for pair in shared_error_pairs]))
            if baseline_error <= 1e-12:
                error_ratio = 1.0 if candidate_error <= 1e-12 else float("inf")
            else:
                error_ratio = candidate_error / baseline_error
        else:
            baseline_error = float("nan")
            candidate_error = float("nan")
            error_ratio = float("nan")

        eligible = (
            above_floor_count >= 4
            and complete_count >= 4
            and shared_count >= 4
            and np.isfinite(error_ratio)
            and error_ratio <= 1.25
        )
        diagnostics.append(
            {
                "alpha": alpha,
                "complete_patients": complete_count,
                "above_repeatability_floor_patients": above_floor_count,
                "shared_error_patients": shared_count,
                "baseline_patient_median_error_mm": baseline_error,
                "candidate_patient_median_error_mm": candidate_error,
                "error_ratio_vs_alpha0": error_ratio,
                "eligible": bool(eligible),
            }
        )

    eligible_alphas = [float(item["alpha"]) for item in diagnostics if item["eligible"]]
    return (min(eligible_alphas) if eligible_alphas else None), diagnostics


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(val) for val in value]
    if isinstance(value, tuple):
        return [_json_safe(val) for val in value]
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _json_safe(row.get(key)) for key in fieldnames})


def main() -> None:
    cfg = load_config(os.path.join(REPO_ROOT, "config", "default.yaml"))
    reg_cfg = cfg["registration"]
    cal_cfg = cfg["calibration"]
    mode_cfg = reg_cfg[MODE]

    # Fail loudly if the frozen protocol's supposedly isolated registration regime
    # drifted before this experiment was run.
    if int(mode_cfg["mesh_size"]) != EXPECTED_MESH_SIZE:
        raise SystemExit(
            f"Protocol requires fast_dev mesh_size={EXPECTED_MESH_SIZE}, "
            f"found {mode_cfg['mesh_size']}"
        )
    if int(mode_cfg["max_iterations"]) != EXPECTED_MAX_ITERATIONS:
        raise SystemExit(
            f"Protocol requires fast_dev max_iterations={EXPECTED_MAX_ITERATIONS}, "
            f"found {mode_cfg['max_iterations']}"
        )
    if int(reg_cfg["seed"]) != EXPECTED_SEED:
        raise SystemExit(
            f"Protocol requires registration seed={EXPECTED_SEED}, " f"found {reg_cfg['seed']}"
        )

    os.makedirs(OUT, exist_ok=True)
    checkpoint_root = os.path.join(OUT, "checkpoints", "ensemble_jitter_sensitivity")
    os.makedirs(checkpoint_root, exist_ok=True)

    print("=== TrueMargin prospective ensemble perturbation sensitivity ===")
    print(f"Git SHA: {provenance.current_git_sha(REPO_ROOT)}")
    print(f"Protocol frozen on main at: {PROTOCOL_MAIN_SHA}")
    print(f"Patients: {list(CASES)}")
    print(f"Settings: {SETTINGS}")
    print(
        f"Registration: {MODE}, mesh={mode_cfg['mesh_size']}, "
        f"max_iterations={mode_cfg['max_iterations']}, n={ENSEMBLE_N}"
    )
    print(f"Near-zero sigma diagnostic threshold: {NEAR_ZERO_SIGMA_MM:g} mm")
    print("Real-data error uses the zero-displacement proxy/reference assumption.\n")

    results: dict[tuple[str, str], Mapping[str, np.ndarray]] = {}
    rows: list[dict[str, Any]] = []

    for patient, series in CASES.items():
        print(f"--- {patient}: preparing real-data inputs ---")
        prepared = _prepare_patient(patient, series, seed=EXPECTED_SEED)
        print(
            f"  crop={np.asarray(prepared['fixed']).shape}, "
            f"spacing={prepared['spacing']}, "
            f"diagonal={prepared['crop_diagonal_mm']:.3f} mm"
        )
        for perturbation, perturbation_scale in SETTINGS:
            sid = setting_id(perturbation, perturbation_scale)
            print(f"  {sid}: running/validating {ENSEMBLE_N} members")
            result = _run_patient_setting(
                patient=patient,
                series=series,
                prepared=prepared,
                perturbation=perturbation,
                perturbation_scale=perturbation_scale,
                mode_cfg=mode_cfg,
                seed=EXPECTED_SEED,
                checkpoint_root=checkpoint_root,
            )
            results[(patient, sid)] = result
            row = _base_row(
                patient=patient,
                perturbation=perturbation,
                perturbation_scale=perturbation_scale,
                result=result,
            )
            rows.append(row)
            if row["complete"]:
                print(
                    f"    complete: median sigma={row['sigma_median_mm']:.6g} mm, "
                    f"median proxy-error={row['error_median_mm']:.6g} mm, "
                    f"Spearman={row['spearman_sigma_error']:.3f}"
                )
            else:
                print(f"    UNSTABLE: failed members={row['failed_member_count']}")
        print()

    curve_levels = np.linspace(0.05, 0.99, int(cal_cfg["levels"]))
    _add_calibration_metrics(rows, results, curve_levels)
    selected_alpha, alpha_diagnostics = select_alpha(rows)

    summary = {
        "experiment": "real-prostate-ensemble-sensitivity-v1",
        "git_sha": provenance.current_git_sha(REPO_ROOT),
        "protocol_main_sha": PROTOCOL_MAIN_SHA,
        "ground_truth_status": (
            "zero-displacement proxy/reference assumption; " "not verified pointwise GT"
        ),
        "patients": list(CASES),
        "settings": [
            {"perturbation": perturbation, "scale": scale, "ensemble_n": ENSEMBLE_N}
            for perturbation, scale in SETTINGS
        ],
        "near_zero_sigma_mm": NEAR_ZERO_SIGMA_MM,
        "selection_rule": (
            "smallest nonzero relative_std alpha with >=4/5 patients above repeatability floor, "
            ">=4/5 complete patients, >=4 shared error patients, and patient-median proxy-error "
            "ratio <=1.25 vs alpha=0"
        ),
        "selected_alpha": selected_alpha,
        "alpha_selection_diagnostics": alpha_diagnostics,
        "rows": rows,
    }

    csv_path = os.path.join(OUT, "ensemble_jitter_sensitivity_patient_metrics.csv")
    json_path = os.path.join(OUT, "ensemble_jitter_sensitivity_summary.json")
    _write_csv(csv_path, rows)
    with open(json_path, "w") as f:
        json.dump(_json_safe(summary), f, indent=2, sort_keys=True)
        f.write("\n")

    print("=== Predeclared alpha-selection gate ===")
    for item in alpha_diagnostics:
        ratio = item["error_ratio_vs_alpha0"]
        ratio_text = f"{ratio:.3f}" if np.isfinite(ratio) else "n/a"
        print(
            f"alpha={item['alpha']:.2f}: complete={item['complete_patients']}/5, "
            f"above_floor={item['above_repeatability_floor_patients']}/5, "
            f"shared_error={item['shared_error_patients']}/5, error_ratio={ratio_text}, "
            f"eligible={item['eligible']}"
        )
    if selected_alpha is None:
        print(
            "SELECTED_ALPHA=None -- no predeclared alpha is eligible. Stop at Gate A; "
            "do not widen/tune the grid post hoc."
        )
    else:
        print(f"SELECTED_ALPHA={selected_alpha:.2f} (smallest eligible nonzero alpha)")
    print(f"Patient metrics: {csv_path}")
    print(f"Machine-readable summary: {json_path}")


if __name__ == "__main__":
    main()
