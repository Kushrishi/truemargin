#!/usr/bin/env python3
"""Run the frozen five-patient B-spline initialization-sensitivity study.

The protocol is frozen in ``docs/initialization_ensemble_protocol.md``. This stage
selects only a stable, non-inert initialization perturbation scale. Real-data proxy
error and pointwise association metrics are descriptive and cannot select the scale.
"""

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
from truemargin import ensemble, initialization, provenance
from truemargin import io_utils as ioutil

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(REPO_ROOT, "data")
OUT = os.path.join(REPO_ROOT, "outputs")
MANIFEST_ROOT = os.path.join(DATA, "prostate_fused_manifest", "prostate_fused_mri_pathology")
HECAP_DIR = os.path.join(DATA, "hecap")

PROTOCOL_MAIN_SHA = "aa30335335b1403381050407b472841b9c7fdd0f"
PROTOCOL_PATH = "docs/initialization_ensemble_protocol.md"
MESH_SIZE = 3
MAX_ITERATIONS = 15
CENTER_FIRST = False
BASE_SEED = 0
ENSEMBLE_N = 5
MAX_LANDMARKS_PER_PATIENT = 75
CROP_PAD_VOXELS = 15
NEAR_ZERO_SIGMA_MM = 1e-6
NDIM = 3
STRENGTHS_MM = (0.0, 0.5, 1.0, 2.0)
NONZERO_STRENGTHS_MM = STRENGTHS_MM[1:]

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


def strength_id(delta_mm: float) -> str:
    return f"delta_{delta_mm:.1f}_mm".replace(".", "p")


def crop_diagonal_mm(shape_zyx: tuple[int, ...], spacing_xyz: tuple[float, ...]) -> float:
    extent_mm = (
        shape_zyx[2] * spacing_xyz[0],
        shape_zyx[1] * spacing_xyz[1],
        shape_zyx[0] * spacing_xyz[2],
    )
    return float(np.sqrt(sum(float(value) ** 2 for value in extent_mm)))


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


def initialization_manifest(
    *,
    patient: str,
    patient_index: int,
    series: Mapping[str, str],
    delta_mm: float,
    n_parameters: int,
) -> dict[str, Any]:
    return provenance.build_manifest(
        repo_root=REPO_ROOT,
        experiment="real-prostate-initialization-ensemble-v1",
        artifact_id=f"{patient}:initialization_delta_mm:{delta_mm:.1f}",
        parameters={
            "mesh_size": MESH_SIZE,
            "max_iterations": MAX_ITERATIONS,
            "center_first": CENTER_FIRST,
            "delta_mm": float(delta_mm),
            "ensemble_n": ENSEMBLE_N,
            "n_parameters": int(n_parameters),
            "base_seed": BASE_SEED,
            "patient_index": int(patient_index),
            "seed_scheme": "SeedSequence([base_seed, patient_index, member_index])",
            "distribution": "independent Uniform(-1, 1) coefficient directions",
            "max_landmarks_per_patient": MAX_LANDMARKS_PER_PATIENT,
            "crop_pad_voxels": CROP_PAD_VOXELS,
            "landmark_seed": BASE_SEED,
            "dce_phase_strategy": "per-slice middle temporal phase",
            "dce_phase_fraction": 0.5,
            "true_displacement_reference": "zero-displacement proxy",
            "member_failure_policy": [
                "registration_exception",
                "nonfinite_displacement",
                "shape_mismatch",
                "mean_displacement_exceeds_crop_physical_diagonal",
            ],
        },
        data_identity={
            "collection": "TCIA Prostate Fused-MRI-Pathology",
            "sensitivity_cohort": list(CASES),
            "patient": patient,
            "t2_series": series["t2_series"],
            "dce_series": series["dce_series"],
            "hecap_mask": f"{patient}-T2-AXIAL-SM-FOV_HECaP.mha",
        },
        source_files=[
            "scripts/17_initialization_ensemble_sensitivity.py",
            PROTOCOL_PATH,
            "src/truemargin/initialization.py",
            "src/truemargin/registration.py",
            "src/truemargin/ensemble.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def _run_patient_strength(
    *,
    patient: str,
    patient_index: int,
    series: Mapping[str, str],
    prepared: Mapping[str, Any],
    delta_mm: float,
    checkpoint_root: str,
) -> Mapping[str, np.ndarray]:
    fixed = np.asarray(prepared["fixed"])
    moving = np.asarray(prepared["moving"])
    idx_crop = np.asarray(prepared["idx_crop"])
    spacing = tuple(float(value) for value in prepared["spacing"])
    diagonal = float(prepared["crop_diagonal_mm"])
    expected_shape = (NDIM, *fixed.shape)
    n_parameters = initialization.bspline_parameter_count(
        fixed,
        mesh_size=MESH_SIZE,
        spacing=spacing,
    )

    checkpoint_dir = os.path.join(checkpoint_root, strength_id(delta_mm))
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"{patient}.npz")
    manifest = initialization_manifest(
        patient=patient,
        patient_index=patient_index,
        series=series,
        delta_mm=delta_mm,
        n_parameters=n_parameters,
    )
    if os.path.exists(checkpoint_path):
        print(f"  {strength_id(delta_mm)}: loading validated checkpoint")
        return provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)

    fields: list[np.ndarray] = []
    member_mean_displacement = np.full(ENSEMBLE_N, np.nan, dtype=np.float64)
    member_proxy_error_median = np.full(ENSEMBLE_N, np.nan, dtype=np.float64)
    member_reasons = np.full(ENSEMBLE_N, "not_run", dtype="U1024")
    member_max_abs_initial = np.full(ENSEMBLE_N, np.nan, dtype=np.float64)

    for member_index in range(ENSEMBLE_N):
        initial_parameters = initialization.initialization_parameters(
            n_parameters,
            delta_mm=delta_mm,
            patient_index=patient_index,
            member_index=member_index,
            base_seed=BASE_SEED,
        )
        member_max_abs_initial[member_index] = float(np.max(np.abs(initial_parameters)))
        try:
            field = initialization.initialized_bspline_registration(
                fixed,
                moving,
                mesh_size=MESH_SIZE,
                max_iterations=MAX_ITERATIONS,
                spacing=spacing,
                center_first=CENTER_FIRST,
                initial_parameters=initial_parameters,
            )
        except Exception as exc:
            member_reasons[member_index] = f"registration_exception:{type(exc).__name__}:{exc}"
            print(f"    member {member_index}: FAILED registration exception")
            continue

        reason = ensemble.validate_member_field(
            field,
            expected_shape=expected_shape,
            crop_diagonal_mm=diagonal,
        )
        if field.shape == expected_shape and np.isfinite(field).all():
            member_mean_displacement[member_index] = mean_displacement_magnitude(field)
        if reason is not None:
            member_reasons[member_index] = reason
            print(f"    member {member_index}: FAILED {reason}")
            continue

        displacement_at = ioutil.sample_field_at_points(field, idx_crop)
        proxy_error = cal.displacement_error(
            displacement_at,
            np.zeros_like(displacement_at),
        )
        member_proxy_error_median[member_index] = float(np.median(proxy_error))
        member_reasons[member_index] = "ok"
        fields.append(field)

    failed_count = int(np.sum(member_reasons != "ok"))
    complete = failed_count == 0 and len(fields) == ENSEMBLE_N
    arrays: dict[str, np.ndarray] = {
        "complete": np.asarray(complete),
        "err": np.asarray([], dtype=np.float64),
        "sigma": np.asarray([], dtype=np.float64),
        "member_mean_displacement_mm": member_mean_displacement,
        "member_proxy_error_median_mm": member_proxy_error_median,
        "member_reasons": member_reasons,
        "member_max_abs_initial_mm": member_max_abs_initial,
        "failed_member_count": np.asarray(failed_count, dtype=np.int64),
        "spacing_xyz_mm": np.asarray(spacing, dtype=np.float64),
        "crop_diagonal_mm": np.asarray(diagonal, dtype=np.float64),
        "n_landmarks": np.asarray(len(idx_crop), dtype=np.int64),
        "n_parameters": np.asarray(n_parameters, dtype=np.int64),
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
    delta_mm: float,
    result: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    complete = bool(np.asarray(result["complete"]).item())
    spacing = np.asarray(result["spacing_xyz_mm"], dtype=float)
    row: dict[str, Any] = {
        "patient": patient,
        "delta_mm": float(delta_mm),
        "setting": strength_id(delta_mm),
        "ensemble_n": ENSEMBLE_N,
        "complete": complete,
        "failed_member_count": int(np.asarray(result["failed_member_count"]).item()),
        "member_reasons": " | ".join(str(value) for value in result["member_reasons"]),
        "spacing_min_mm": float(np.min(spacing)),
        "spacing_max_mm": float(np.max(spacing)),
        "crop_diagonal_mm": float(np.asarray(result["crop_diagonal_mm"]).item()),
        "n_landmarks": int(np.asarray(result["n_landmarks"]).item()),
        "n_parameters": int(np.asarray(result["n_parameters"]).item()),
        "max_abs_initial_mm": float(np.nanmax(result["member_max_abs_initial_mm"])),
    }
    if complete:
        row.update(pointwise_metrics(np.asarray(result["err"]), np.asarray(result["sigma"])))
        if delta_mm == 0.0:
            row["nominal_proxy_error_median_mm"] = float(
                np.asarray(result["member_proxy_error_median_mm"])[0]
            )
    return row


def select_initialization_delta(
    rows: list[dict[str, Any]],
) -> tuple[float | None, int, list[dict[str, Any]]]:
    floor_rows = {str(row["patient"]): row for row in rows if float(row["delta_mm"]) == 0.0}
    floor_complete = sum(bool(row["complete"]) for row in floor_rows.values())
    diagnostics: list[dict[str, Any]] = []
    selected: float | None = None

    for delta_mm in NONZERO_STRENGTHS_MM:
        candidate_rows = {
            str(row["patient"]): row for row in rows if float(row["delta_mm"]) == float(delta_mm)
        }
        shared_patients = [
            patient
            for patient in CASES
            if patient in floor_rows
            and patient in candidate_rows
            and bool(floor_rows[patient]["complete"])
            and bool(candidate_rows[patient]["complete"])
        ]

        non_inert_patients = 0
        for patient in shared_patients:
            floor = floor_rows[patient]
            candidate = candidate_rows[patient]
            required_signal = max(
                3.0 * float(floor["sigma_median_mm"]),
                0.25 * float(floor["spacing_min_mm"]),
            )
            non_inert = float(candidate["sigma_median_mm"]) >= required_signal
            candidate["floor_sigma_median_mm"] = float(floor["sigma_median_mm"])
            candidate["required_signal_mm"] = required_signal
            candidate["non_inert"] = bool(non_inert)
            non_inert_patients += int(non_inert)

        eligible = bool(
            floor_complete >= 4 and len(shared_patients) >= 4 and non_inert_patients >= 4
        )
        diagnostics.append(
            {
                "delta_mm": float(delta_mm),
                "floor_complete_patients": floor_complete,
                "shared_complete_patients": len(shared_patients),
                "non_inert_patients": non_inert_patients,
                "eligible": eligible,
            }
        )
        if selected is None and eligible:
            selected = float(delta_mm)

    if floor_complete < 4:
        selected = None
    return selected, floor_complete, diagnostics


def _write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    preferred = [
        "patient",
        "delta_mm",
        "setting",
        "ensemble_n",
        "complete",
        "failed_member_count",
        "non_inert",
        "required_signal_mm",
        "floor_sigma_median_mm",
        "sigma_median_mm",
        "sigma_iqr_mm",
        "sigma_near_zero_fraction",
        "sigma_cv",
        "error_median_mm",
        "error_mean_mm",
        "error_p90_mm",
        "spearman_sigma_error",
        "pearson_sigma_error",
        "quartile_error_delta_mm",
        "blind_spot_rate",
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
    checkpoint_root = os.path.join(OUT, "checkpoints", "initialization_ensemble_sensitivity")
    os.makedirs(checkpoint_root, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    print("=== TrueMargin prospective initialization-ensemble sensitivity ===")
    print(f"Git SHA: {head}")
    print(f"Protocol main SHA: {PROTOCOL_MAIN_SHA}")
    print(f"Protocol: {PROTOCOL_PATH}")
    print(f"Patients: {list(CASES)}")
    print(f"Initialization strengths (mm): {STRENGTHS_MM}")
    print(
        f"Registration: mesh={MESH_SIZE}, max_iterations={MAX_ITERATIONS}, "
        f"center_first={CENTER_FIRST}, members={ENSEMBLE_N}"
    )
    print("Proxy error and association metrics are descriptive only and cannot select delta_mm.")

    rows: list[dict[str, Any]] = []
    results: dict[tuple[str, float], Mapping[str, np.ndarray]] = {}

    for patient_index, (patient, series) in enumerate(CASES.items()):
        print(f"\n--- {patient}: preparing real-data inputs ---")
        prepared = _prepare_patient(patient, series, seed=BASE_SEED)
        print(
            f"  crop={np.asarray(prepared['fixed']).shape}, "
            f"spacing={prepared['spacing']}, "
            f"diagonal={float(prepared['crop_diagonal_mm']):.3f} mm"
        )

        for delta_mm in STRENGTHS_MM:
            print(f"  delta_mm={delta_mm:.1f}: running/validating {ENSEMBLE_N} members")
            result = _run_patient_strength(
                patient=patient,
                patient_index=patient_index,
                series=series,
                prepared=prepared,
                delta_mm=delta_mm,
                checkpoint_root=checkpoint_root,
            )
            results[(patient, delta_mm)] = result
            row = _base_row(patient=patient, delta_mm=delta_mm, result=result)
            rows.append(row)
            if row["complete"]:
                print(
                    f"    complete=5/5: sigma median={row['sigma_median_mm']:.6g} mm, "
                    f"proxy-error median={row['error_median_mm']:.6g} mm"
                )
            else:
                print(f"    complete=NO: failed_members={row['failed_member_count']}")

    selected, floor_complete, diagnostics = select_initialization_delta(rows)

    metrics_path = os.path.join(OUT, "initialization_ensemble_sensitivity_patient_metrics.csv")
    summary_path = os.path.join(OUT, "initialization_ensemble_sensitivity_summary.json")
    _write_csv(metrics_path, rows)

    summary = {
        "experiment": "real-prostate-initialization-ensemble-v1",
        "git_sha": head,
        "protocol_main_sha": PROTOCOL_MAIN_SHA,
        "protocol_path": PROTOCOL_PATH,
        "patients": list(CASES),
        "strengths_mm": list(STRENGTHS_MM),
        "mesh_size": MESH_SIZE,
        "max_iterations": MAX_ITERATIONS,
        "ensemble_n": ENSEMBLE_N,
        "base_seed": BASE_SEED,
        "seed_scheme": "SeedSequence([base_seed, patient_index, member_index])",
        "ground_truth_status": (
            "zero-displacement proxy/reference assumption; not verified pointwise GT; "
            "proxy error excluded from strength selection"
        ),
        "floor_complete_patients": floor_complete,
        "selected_initialization_delta_mm": selected,
        "selection_diagnostics": diagnostics,
        "selection_rule": (
            "delta=0 complete in >=4/5; smallest nonzero delta with >=4 shared complete "
            "patients and >=4 shared patients satisfying median_sigma >= "
            "max(3*delta0_median_sigma, 0.25*min_spacing)"
        ),
        "rows": rows,
    }
    with open(summary_path, "w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("\n=== Predeclared initialization-strength gate ===")
    print(f"delta=0 repeatability-floor complete: {floor_complete}/5")
    for diagnostic in diagnostics:
        print(
            f"delta_mm={diagnostic['delta_mm']:.1f}: "
            f"shared_complete={diagnostic['shared_complete_patients']}/5, "
            f"non_inert={diagnostic['non_inert_patients']}/5, "
            f"eligible={diagnostic['eligible']}"
        )

    if selected is None:
        print(
            "SELECTED_INITIALIZATION_DELTA_MM=None -- no predeclared strength is "
            "eligible, or the repeatability floor is not assessable. Stop this "
            "mechanism; do not widen or tune the grid post hoc."
        )
    else:
        print(
            f"SELECTED_INITIALIZATION_DELTA_MM={selected:.1f} "
            "(smallest eligible nonzero strength)"
        )
        print("Next stage: run the frozen nested n=5/10/20 size study at this strength.")

    print(f"Patient metrics: {metrics_path}")
    print(f"Machine-readable summary: {summary_path}")


if __name__ == "__main__":
    main()
