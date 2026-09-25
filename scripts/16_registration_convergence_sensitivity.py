#!/usr/bin/env python3
"""Run the prospective five-patient registration convergence sensitivity study.

The protocol is frozen in ``docs/registration_convergence_protocol.md``.
This study varies only the LBFGSB maximum iteration budget at the existing
mesh-3 registration regime. It does not tune an uncertainty method.
"""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping
from typing import Any

import numpy as np
import SimpleITK as sitk

from truemargin import calibration as cal
from truemargin import ensemble, provenance
from truemargin import io_utils as ioutil
from truemargin import registration as reg

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(REPO_ROOT, "data")
OUT = os.path.join(REPO_ROOT, "outputs")
MANIFEST_ROOT = os.path.join(DATA, "prostate_fused_manifest", "prostate_fused_mri_pathology")
HECAP_DIR = os.path.join(DATA, "hecap")

DESIGN_BASE_SHA = "052ba816f7ed91f7e8ee32fca5d67914a3c1a29d"
PROTOCOL_PATH = "docs/registration_convergence_protocol.md"
MESH_SIZE = 3
ITERATION_BUDGETS = (15, 30, 60, 100)
REFERENCE_ITERATIONS = 100
REPEATS = 5
MIN_VALID_REPEATS = 4
MAX_LANDMARKS_PER_PATIENT = 75
CROP_PAD_VOXELS = 15
EXPECTED_SEED = 0
CENTER_FIRST = False
NDIM = 3

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


def convergence_manifest(
    *,
    patient: str,
    series: Mapping[str, str],
    max_iterations: int,
) -> dict[str, Any]:
    return provenance.build_manifest(
        repo_root=REPO_ROOT,
        experiment="real-prostate-registration-convergence-v1",
        artifact_id=f"{patient}:iterations:{max_iterations}",
        parameters={
            "mesh_size": MESH_SIZE,
            "max_iterations": int(max_iterations),
            "repeats": REPEATS,
            "min_valid_repeats": MIN_VALID_REPEATS,
            "center_first": CENTER_FIRST,
            "max_landmarks_per_patient": MAX_LANDMARKS_PER_PATIENT,
            "crop_pad_voxels": CROP_PAD_VOXELS,
            "landmark_seed": EXPECTED_SEED,
            "dce_phase_strategy": "per-slice middle temporal phase",
            "dce_phase_fraction": 0.5,
            "true_displacement_reference": "zero-displacement proxy",
            "reference_iterations": REFERENCE_ITERATIONS,
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
            "scripts/16_registration_convergence_sensitivity.py",
            PROTOCOL_PATH,
            "src/truemargin/registration.py",
            "src/truemargin/ensemble.py",
            "src/truemargin/io_utils.py",
            "src/truemargin/calibration.py",
        ],
    )


def _run_patient_budget(
    *,
    patient: str,
    series: Mapping[str, str],
    prepared: Mapping[str, Any],
    max_iterations: int,
    checkpoint_root: str,
) -> Mapping[str, np.ndarray]:
    budget_dir = os.path.join(checkpoint_root, f"iter_{max_iterations:03d}")
    os.makedirs(budget_dir, exist_ok=True)
    checkpoint_path = os.path.join(budget_dir, f"{patient}.npz")
    manifest = convergence_manifest(
        patient=patient,
        series=series,
        max_iterations=max_iterations,
    )

    if os.path.exists(checkpoint_path):
        return provenance.load_checkpoint(checkpoint_path, expected_manifest=manifest)

    fixed = np.asarray(prepared["fixed"])
    moving = np.asarray(prepared["moving"])
    idx_crop = np.asarray(prepared["idx_crop"])
    spacing = tuple(float(value) for value in prepared["spacing"])
    diagonal = float(prepared["crop_diagonal_mm"])
    expected_shape = (NDIM, *fixed.shape)

    sampled = np.full((REPEATS, NDIM, len(idx_crop)), np.nan, dtype=np.float64)
    proxy_error = np.full((REPEATS, len(idx_crop)), np.nan, dtype=np.float64)
    valid = np.zeros(REPEATS, dtype=bool)
    mean_displacement = np.full(REPEATS, np.nan, dtype=np.float64)
    reasons = np.full(REPEATS, "not_run", dtype="U1024")

    for repeat in range(REPEATS):
        try:
            field = reg.baseline_bspline_registration(
                fixed,
                moving,
                mesh_size=MESH_SIZE,
                max_iterations=max_iterations,
                spacing=spacing,
                center_first=CENTER_FIRST,
            )
        except Exception as exc:
            reasons[repeat] = f"registration_exception:{type(exc).__name__}:{exc}"
            print(f"    repeat {repeat}: FAILED registration exception")
            continue

        reason = ensemble.validate_member_field(
            field,
            expected_shape=expected_shape,
            crop_diagonal_mm=diagonal,
        )
        if field.shape == expected_shape and np.isfinite(field).all():
            mean_displacement[repeat] = mean_displacement_magnitude(field)
        if reason is not None:
            reasons[repeat] = reason
            print(f"    repeat {repeat}: FAILED {reason}")
            continue

        displacement_at = ioutil.sample_field_at_points(field, idx_crop)
        sampled[repeat] = displacement_at
        proxy_error[repeat] = cal.displacement_error(
            displacement_at,
            np.zeros_like(displacement_at),
        )
        valid[repeat] = True
        reasons[repeat] = "ok"

    arrays: dict[str, np.ndarray] = {
        "valid": valid,
        "sampled_displacement": sampled,
        "proxy_error": proxy_error,
        "member_mean_displacement_mm": mean_displacement,
        "member_reasons": reasons,
        "spacing_xyz_mm": np.asarray(spacing, dtype=np.float64),
        "crop_diagonal_mm": np.asarray(diagonal, dtype=np.float64),
        "n_landmarks": np.asarray(len(idx_crop), dtype=np.int64),
    }
    provenance.save_checkpoint(checkpoint_path, arrays=arrays, manifest=manifest)
    return arrays


def summarize_cell(
    *,
    patient: str,
    max_iterations: int,
    result: Mapping[str, np.ndarray],
) -> tuple[dict[str, Any], np.ndarray | None]:
    valid = np.asarray(result["valid"], dtype=bool)
    valid_count = int(valid.sum())
    assessable = valid_count >= MIN_VALID_REPEATS
    spacing = np.asarray(result["spacing_xyz_mm"], dtype=float)

    row: dict[str, Any] = {
        "patient": patient,
        "max_iterations": int(max_iterations),
        "valid_repeats": valid_count,
        "assessable": bool(assessable),
        "spacing_min_mm": float(np.min(spacing)),
        "spacing_max_mm": float(np.max(spacing)),
        "crop_diagonal_mm": float(np.asarray(result["crop_diagonal_mm"]).item()),
        "n_landmarks": int(np.asarray(result["n_landmarks"]).item()),
        "member_reasons": " | ".join(str(value) for value in result["member_reasons"]),
        "converged_to_reference": False,
    }
    if not assessable:
        return row, None

    sampled = np.asarray(result["sampled_displacement"], dtype=float)[valid]
    representative = np.median(sampled, axis=0)
    repeat_distance = np.sqrt(np.sum((sampled - representative[None, :, :]) ** 2, axis=1))
    representative_proxy_error = cal.displacement_error(
        representative,
        np.zeros_like(representative),
    )
    row.update(
        {
            "repeatability_median_mm": float(np.median(repeat_distance)),
            "repeatability_p90_mm": float(np.percentile(repeat_distance, 90)),
            "proxy_error_median_mm": float(np.median(representative_proxy_error)),
            "proxy_error_p90_mm": float(np.percentile(representative_proxy_error, 90)),
        }
    )
    return row, representative


def add_reference_metrics(
    rows: list[dict[str, Any]],
    representatives: Mapping[tuple[str, int], np.ndarray | None],
) -> int:
    reference_assessable = 0
    for patient in CASES:
        reference_row = next(
            row
            for row in rows
            if row["patient"] == patient and row["max_iterations"] == REFERENCE_ITERATIONS
        )
        reference_rep = representatives[(patient, REFERENCE_ITERATIONS)]
        if reference_row["assessable"] and reference_rep is not None:
            reference_assessable += 1

        for budget in ITERATION_BUDGETS:
            if budget == REFERENCE_ITERATIONS:
                continue
            candidate = next(
                row for row in rows if row["patient"] == patient and row["max_iterations"] == budget
            )
            candidate["reference_assessable"] = bool(reference_row["assessable"])
            candidate_rep = representatives[(patient, budget)]
            if (
                not candidate["assessable"]
                or not reference_row["assessable"]
                or candidate_rep is None
                or reference_rep is None
            ):
                continue

            median_tolerance = max(
                float(reference_row["spacing_min_mm"]),
                2.0 * float(reference_row["repeatability_median_mm"]),
            )
            p90_tolerance = max(
                0.5 * float(reference_row["spacing_max_mm"]),
                2.0 * float(reference_row["repeatability_p90_mm"]),
            )
            delta = np.sqrt(np.sum((candidate_rep - reference_rep) ** 2, axis=0))
            delta_median = float(np.median(delta))
            delta_p90 = float(np.percentile(delta, 90))

            candidate.update(
                {
                    "reference_repeatability_median_mm": float(
                        reference_row["repeatability_median_mm"]
                    ),
                    "reference_repeatability_p90_mm": float(reference_row["repeatability_p90_mm"]),
                    "median_tolerance_mm": median_tolerance,
                    "p90_tolerance_mm": p90_tolerance,
                    "reference_delta_median_mm": delta_median,
                    "reference_delta_p90_mm": delta_p90,
                    "converged_to_reference": bool(
                        delta_median <= median_tolerance
                        and delta_p90 <= p90_tolerance
                        and float(candidate["repeatability_median_mm"]) <= median_tolerance
                        and float(candidate["repeatability_p90_mm"]) <= p90_tolerance
                    ),
                }
            )
    return reference_assessable


def select_iterations(
    rows: list[dict[str, Any]],
    *,
    reference_assessable_patients: int,
) -> tuple[int | None, list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    for budget in (15, 30, 60):
        candidate_rows = [row for row in rows if row["max_iterations"] == budget]
        shared_assessable = sum(
            bool(row["assessable"] and row.get("reference_assessable", False))
            for row in candidate_rows
        )
        converged_patients = sum(bool(row["converged_to_reference"]) for row in candidate_rows)
        eligible = (
            reference_assessable_patients >= 4
            and shared_assessable >= 4
            and converged_patients >= 4
        )
        diagnostics.append(
            {
                "max_iterations": budget,
                "reference_assessable_patients": reference_assessable_patients,
                "shared_assessable_patients": shared_assessable,
                "converged_patients": converged_patients,
                "eligible": bool(eligible),
            }
        )

    eligible = [item["max_iterations"] for item in diagnostics if item["eligible"]]
    return (min(eligible) if eligible else None), diagnostics


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
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _json_safe(row.get(key)) for key in fieldnames})


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    checkpoint_root = os.path.join(OUT, "checkpoints", "registration_convergence")
    os.makedirs(checkpoint_root, exist_ok=True)

    print("=== TrueMargin prospective registration convergence sensitivity ===")
    print(f"Git SHA: {provenance.current_git_sha(REPO_ROOT)}")
    print(f"Design base SHA: {DESIGN_BASE_SHA}")
    print(f"Protocol: {PROTOCOL_PATH}")
    print(f"Patients: {list(CASES)}")
    print(f"Iteration budgets: {ITERATION_BUDGETS}")
    print(f"Registration: mesh={MESH_SIZE}, center_first={CENTER_FIRST}, repeats={REPEATS}")
    print("Proxy error is descriptive only and is not used for iteration selection.\n")

    results: dict[tuple[str, int], Mapping[str, np.ndarray]] = {}
    rows: list[dict[str, Any]] = []
    representatives: dict[tuple[str, int], np.ndarray | None] = {}

    for patient, series in CASES.items():
        print(f"--- {patient}: preparing real-data inputs ---")
        prepared = _prepare_patient(patient, series, seed=EXPECTED_SEED)
        print(
            f"  crop={np.asarray(prepared['fixed']).shape}, "
            f"spacing={prepared['spacing']}, "
            f"diagonal={prepared['crop_diagonal_mm']:.3f} mm"
        )
        for budget in ITERATION_BUDGETS:
            print(f"  iterations={budget}: running/validating {REPEATS} repeats")
            result = _run_patient_budget(
                patient=patient,
                series=series,
                prepared=prepared,
                max_iterations=budget,
                checkpoint_root=checkpoint_root,
            )
            results[(patient, budget)] = result
            row, representative = summarize_cell(
                patient=patient,
                max_iterations=budget,
                result=result,
            )
            rows.append(row)
            representatives[(patient, budget)] = representative
            if row["assessable"]:
                print(
                    f"    assessable={row['valid_repeats']}/{REPEATS}: "
                    f"repeat median={row['repeatability_median_mm']:.6g} mm, "
                    f"p90={row['repeatability_p90_mm']:.6g} mm, "
                    f"proxy-error median={row['proxy_error_median_mm']:.6g} mm"
                )
            else:
                print(f"    UNASSESSABLE: valid repeats={row['valid_repeats']}/{REPEATS}")
        print()

    reference_assessable_patients = add_reference_metrics(rows, representatives)
    selected_iterations, selection_diagnostics = select_iterations(
        rows,
        reference_assessable_patients=reference_assessable_patients,
    )

    summary = {
        "experiment": "real-prostate-registration-convergence-v1",
        "git_sha": provenance.current_git_sha(REPO_ROOT),
        "design_base_sha": DESIGN_BASE_SHA,
        "protocol_path": PROTOCOL_PATH,
        "ground_truth_status": (
            "zero-displacement proxy/reference assumption; "
            "not verified pointwise GT; proxy error excluded from selection"
        ),
        "patients": list(CASES),
        "mesh_size": MESH_SIZE,
        "iteration_budgets": list(ITERATION_BUDGETS),
        "reference_iterations": REFERENCE_ITERATIONS,
        "repeats": REPEATS,
        "min_valid_repeats": MIN_VALID_REPEATS,
        "reference_assessable_patients": reference_assessable_patients,
        "selection_rule": (
            "smallest of 15/30/60 with >=4 shared assessable patients and >=4/5 patients "
            "passing candidate-to-100 and within-budget median/p90 field-stability tolerances; "
            "100-iteration reference must itself be assessable in >=4/5 patients"
        ),
        "selected_iterations": selected_iterations,
        "selection_diagnostics": selection_diagnostics,
        "rows": rows,
    }

    csv_path = os.path.join(OUT, "registration_convergence_patient_metrics.csv")
    json_path = os.path.join(OUT, "registration_convergence_summary.json")
    _write_csv(csv_path, rows)
    with open(json_path, "w") as handle:
        json.dump(_json_safe(summary), handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("=== Predeclared registration convergence gate ===")
    print(f"100-iteration reference assessable: {reference_assessable_patients}/5")
    for item in selection_diagnostics:
        print(
            f"iterations={item['max_iterations']}: "
            f"shared_assessable={item['shared_assessable_patients']}/5, "
            f"converged={item['converged_patients']}/5, "
            f"eligible={item['eligible']}"
        )
    if reference_assessable_patients < 4:
        print(
            "SELECTED_ITERATIONS=None -- 100-iteration reference is not stable enough. "
            "Stop and investigate registration design before uncertainty work continues."
        )
    elif selected_iterations is None:
        print(
            "SELECTED_ITERATIONS=None -- no lower iteration budget met the frozen "
            "convergence gate. Do not tune the gate post hoc."
        )
    else:
        print(f"SELECTED_ITERATIONS={selected_iterations} (smallest eligible lower budget)")
    print(f"Patient metrics: {csv_path}")
    print(f"Machine-readable summary: {json_path}")


if __name__ == "__main__":
    main()
