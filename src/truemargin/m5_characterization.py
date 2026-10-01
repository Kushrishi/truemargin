"""Post-primary characterization of frozen TrueMargin M4 outputs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

EXPECTED_CANONICAL_SHA256 = {
    "hyperparameter_known_gt_case_metrics.csv": (
        "16f19a0fcbedfd06145615d17406f4901706a061f755bfbd6dd85e363e38f33c"
    ),
    "hyperparameter_known_gt_anatomy_metrics.csv": (
        "c69143a510db9558336d5395756e5e98e00f21a0910d7f77fd2c87b36898f389"
    ),
    "hyperparameter_known_gt_comparator_anatomy_metrics.csv": (
        "c02f963520a506d781fe09cde35b619d6eb6a6ae42b1fb1d3fca17069ba8f984"
    ),
    "hyperparameter_known_gt_summary.json": (
        "251f3e5545488e3130344a6a59922b6ee6c38fbf1f1fba4342802ddc2bce86f3"
    ),
}
EXPECTED_SHARD_SHA256 = {
    "aaa0044": "c8268a9b1ab5e7e53c3dac7e731bc9fee490f8bb3c0bd4836ad8a63abb166fd7",
    "aaa0051": "04ec0558a76f5be4d2edf0de72ec428bf33d6f38a17ca65cad39d751cf997db8",
    "aaa0053": "24157610525f556e0b7afa97f880909832a2cc087ee802b8e9b69949b866fa2a",
    "aaa0060": "652133d28abbca66c0d21a282d50728504ca2f44b7569924c4a68ac7090a1be7",
    "aaa0064": "555c1589254f4c7a28a656ef7ddf085d61ab1050734b6261ee625c60df00d40e",
    "aaa0069": "139a6f6e44031e3d1cf12207557128abc45b6c09b00ae6482567c1ec73146d1f",
    "aaa0071": "899c75fa65a0fa4680c4ffbf22553cc2a7d6fe84642162947e570262c733012a",
    "aaa0072": "0ea56ccea4bffc0f8fc319ab2c1f3dc533b3320f4bbfd03c2f1e87f8683980f9",
    "aaa0086": "eeaa0caeadb48a24c77d0a1568a2753647c1b62e2f74876e9cf8262517a6ef4b",
    "aaa0087": "9657cce36ea2fa548a168a6a8c4bcc94a131b55a7a24a826d42d877479103be1",
}
M4_WORKFLOW_RUN_ID = 36188222836
M4_CANONICAL_ARTIFACT_ID = 10896650804
M4_CANONICAL_ARTIFACT_DIGEST = (
    "sha256:bd1f76e20c7e4591b5b3113c061c90534ec413bda0a242747625ed6d5f96b728"
)
M4_EXECUTION_GIT_SHA = "9add89e5055ba45eb6c6b93c42da38615891a225"
M4_EXPERIMENT = "hyperparameter-known-gt-v1"
COMPARATORS = ("ice", "residual", "jacdev")
N_REPLICATES = 3
N_POINTS = 50


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str) -> float:
    if value == "" or value.lower() == "nan":
        return float("nan")
    return float(value)


def _as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _npz_scalar(npz: Any, key: str) -> Any:
    value = np.asarray(npz[key])
    if value.size != 1:
        raise ValueError(f"Expected scalar field {key!r}, got shape {value.shape}")
    return value.item()


def _assert_close(label: str, observed: float, expected: float) -> None:
    if not np.isclose(observed, expected, atol=1e-12, rtol=0.0, equal_nan=True):
        raise ValueError(f"Frozen M4 reconstruction mismatch for {label}: {observed} != {expected}")


def _score_metrics(error: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    error_q75 = float(np.percentile(error, 75))
    score_q25, score_q75 = (float(value) for value in np.percentile(score, [25, 75]))
    low_score = score <= score_q25
    high_score = score >= score_q75
    blind_spot = (error >= error_q75) & low_score
    return {
        "spearman": float(spearmanr(score, error).statistic),
        "score_q25": score_q25,
        "error_q75": error_q75,
        "quartile_error_delta_mm": float(
            np.median(error[high_score]) - np.median(error[low_score])
        ),
        "blind_spot": blind_spot,
        "blind_spot_rate": float(np.mean(blind_spot)),
    }


def _verify_inputs(canonical_root: Path, shard_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    canonical_hashes: dict[str, str] = {}
    for name, expected in EXPECTED_CANONICAL_SHA256.items():
        path = canonical_root / name
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Canonical hash mismatch for {name}: {actual}")
        canonical_hashes[name] = actual

    shard_hashes: dict[str, str] = {}
    for patient, expected in EXPECTED_SHARD_SHA256.items():
        path = shard_root / f"{patient}.zip"
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Shard hash mismatch for {patient}: {actual}")
        shard_hashes[patient] = actual
    return canonical_hashes, shard_hashes


def _reconstruct(
    shard_root: Path, canonical_rows: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    canonical = {(row["patient"], int(row["replicate"])): row for row in canonical_rows}
    points: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    for patient in EXPECTED_SHARD_SHA256:
        with zipfile.ZipFile(shard_root / f"{patient}.zip") as archive:
            for replicate in range(N_REPLICATES):
                member = (
                    f"checkpoints/hyperparameter_known_gt/{patient}/" f"replicate_{replicate}.npz"
                )
                with archive.open(member) as handle:
                    npz = np.load(io.BytesIO(handle.read()), allow_pickle=False)

                provenance = json.loads(str(_npz_scalar(npz, "__truemargin_provenance__")))
                if provenance.get("experiment") != M4_EXPERIMENT:
                    raise ValueError(f"Unexpected experiment in {member}")
                if provenance.get("git_sha") != M4_EXECUTION_GIT_SHA:
                    raise ValueError(f"Unexpected execution Git SHA in {member}")
                if provenance.get("data_identity", {}).get("patient") != patient:
                    raise ValueError(f"Patient provenance mismatch in {member}")

                error = np.asarray(npz["error"], dtype=float)
                sigma = np.asarray(npz["sigma"], dtype=float)
                index = np.asarray(npz["idx_zyx"], dtype=np.int64)
                if error.shape != (N_POINTS,) or sigma.shape != (N_POINTS,):
                    raise ValueError(f"Unexpected point-array shape in {member}")
                if index.shape != (N_POINTS, 3):
                    raise ValueError(f"Unexpected coordinate shape in {member}")

                frozen = canonical[(patient, replicate)]
                sigma_metrics = _score_metrics(error, sigma)
                _assert_close(
                    f"{patient}/r{replicate}/sigma Spearman",
                    sigma_metrics["spearman"],
                    _as_float(frozen["spearman_sigma_known_error"]),
                )
                _assert_close(
                    f"{patient}/r{replicate}/sigma blind spot",
                    sigma_metrics["blind_spot_rate"],
                    _as_float(frozen["blind_spot_rate"]),
                )
                _assert_close(
                    f"{patient}/r{replicate}/sigma quartile delta",
                    sigma_metrics["quartile_error_delta_mm"],
                    _as_float(frozen["quartile_known_error_delta_mm"]),
                )

                comparator_data: dict[str, dict[str, Any]] = {}
                for method in COMPARATORS:
                    valid = bool(_npz_scalar(npz, f"{method}_valid"))
                    if valid != _as_bool(frozen[f"{method}_valid"]):
                        raise ValueError(
                            f"Comparator validity mismatch for {patient}/r{replicate}/{method}"
                        )
                    if valid:
                        score = np.asarray(npz[f"{method}_score"], dtype=float)
                        metrics = _score_metrics(error, score)
                        _assert_close(
                            f"{patient}/r{replicate}/{method} Spearman",
                            metrics["spearman"],
                            _as_float(frozen[f"spearman_{method}_known_error"]),
                        )
                        _assert_close(
                            f"{patient}/r{replicate}/{method} blind spot",
                            metrics["blind_spot_rate"],
                            _as_float(frozen[f"{method}_blind_spot_rate"]),
                        )
                        comparator_data[method] = {
                            "valid": True,
                            "score": score,
                            "metrics": metrics,
                        }
                    else:
                        reason = str(_npz_scalar(npz, f"{method}_failure_reason"))
                        if reason != frozen[f"{method}_failure_reason"]:
                            raise ValueError(
                                f"Comparator failure mismatch for {patient}/r{replicate}/{method}"
                            )
                        comparator_data[method] = {
                            "valid": False,
                            "score": None,
                            "metrics": None,
                        }

                cases.append(
                    {
                        "patient": patient,
                        "replicate": replicate,
                        "sigma_case_spearman": sigma_metrics["spearman"],
                        "sigma_blind_spot_count": int(np.sum(sigma_metrics["blind_spot"])),
                        "sigma_blind_spot_rate": sigma_metrics["blind_spot_rate"],
                        "sigma_quartile_error_delta_mm": sigma_metrics["quartile_error_delta_mm"],
                        "known_error_q75_mm": sigma_metrics["error_q75"],
                        "sigma_q25_mm": sigma_metrics["score_q25"],
                        "ice_valid": comparator_data["ice"]["valid"],
                        "ice_case_spearman": (
                            comparator_data["ice"]["metrics"]["spearman"]
                            if comparator_data["ice"]["valid"]
                            else float("nan")
                        ),
                        "ice_blind_spot_count": (
                            int(np.sum(comparator_data["ice"]["metrics"]["blind_spot"]))
                            if comparator_data["ice"]["valid"]
                            else ""
                        ),
                        "invalid_comparators": ",".join(
                            method for method in COMPARATORS if not comparator_data[method]["valid"]
                        ),
                    }
                )

                for point_index in range(N_POINTS):
                    point: dict[str, Any] = {
                        "patient": patient,
                        "replicate": replicate,
                        "point_index": point_index,
                        "z": int(index[point_index, 0]),
                        "y": int(index[point_index, 1]),
                        "x": int(index[point_index, 2]),
                        "known_error_mm": float(error[point_index]),
                        "known_error_q75_mm": sigma_metrics["error_q75"],
                        "sigma_mm": float(sigma[point_index]),
                        "sigma_q25_mm": sigma_metrics["score_q25"],
                        "sigma_blind_spot": bool(sigma_metrics["blind_spot"][point_index]),
                    }
                    for method in COMPARATORS:
                        data = comparator_data[method]
                        point[f"{method}_valid"] = data["valid"]
                        point[f"{method}_blind_spot"] = (
                            bool(data["metrics"]["blind_spot"][point_index])
                            if data["valid"]
                            else ""
                        )
                    points.append(point)

    if len(points) != 1500 or len(cases) != 30:
        raise ValueError("Unexpected M5 reconstruction size")
    return points, cases


def build_failure_table(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in cases
        if row["sigma_blind_spot_count"] > 0
        or row["sigma_case_spearman"] < 0.0
        or row["sigma_quartile_error_delta_mm"] <= 0.0
        or bool(row["invalid_comparators"])
    ]


def _anatomy_table(
    anatomy_rows: list[dict[str, str]], comparator_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    lookup = {(row["patient"], row["method"]): row for row in comparator_rows}
    table: list[dict[str, Any]] = []
    for row in anatomy_rows:
        patient = row["patient"]
        out: dict[str, Any] = {
            "patient": patient,
            "sigma_median_case_spearman": _as_float(row["median_case_spearman"]),
            "sigma_median_blind_spot_rate": _as_float(row["median_blind_spot_rate"]),
        }
        for method in COMPARATORS:
            candidate = lookup[(patient, method)]
            out[f"{method}_median_case_spearman"] = _as_float(candidate["median_case_spearman"])
            out[f"{method}_valid_cases"] = int(candidate["valid_cases"])
        table.append(out)
    return table


def _summary(
    canonical_rows: list[dict[str, str]],
    points: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    anatomy: list[dict[str, Any]],
    frozen: dict[str, Any],
    canonical_hashes: dict[str, str],
    shard_hashes: dict[str, str],
) -> dict[str, Any]:
    sigma_blind = [row for row in points if row["sigma_blind_spot"]]
    ice_valid = [row for row in points if row["ice_valid"]]
    ice_blind = [row for row in ice_valid if row["ice_blind_spot"]]
    joint = [row for row in sigma_blind if row["ice_valid"] and row["ice_blind_spot"]]
    spearman = [float(row["sigma_case_spearman"]) for row in cases]
    deltas = [float(row["sigma_quartile_error_delta_mm"]) for row in cases]
    worst = min(cases, key=lambda row: row["sigma_case_spearman"])
    invalid_counts = {
        method: sum(not _as_bool(row[f"{method}_valid"]) for row in canonical_rows)
        for method in COMPARATORS
    }
    failure_reasons = {
        method: dict(
            sorted(
                Counter(
                    row[f"{method}_failure_reason"]
                    for row in canonical_rows
                    if not _as_bool(row[f"{method}_valid"])
                ).items()
            )
        )
        for method in COMPARATORS
    }

    return {
        "schema_version": 2,
        "analysis_type": "post_primary_descriptive_characterization",
        "inferential_status": (
            "No new confirmatory hypothesis test, winner metric, retuning decision, "
            "or registration execution is introduced by M5."
        ),
        "blind_spot_definition": (
            "Within each case: known error >= case 75th percentile and method score <= "
            "case 25th percentile. This is the frozen M4 definition."
        ),
        "m4_provenance": {
            "workflow_run_id": M4_WORKFLOW_RUN_ID,
            "canonical_artifact_id": M4_CANONICAL_ARTIFACT_ID,
            "canonical_artifact_digest": M4_CANONICAL_ARTIFACT_DIGEST,
            "execution_git_sha": M4_EXECUTION_GIT_SHA,
            "verified_canonical_output_sha256": canonical_hashes,
            "verified_shard_archive_sha256": shard_hashes,
        },
        "frozen_primary_result": {
            "assessable_anatomies": int(frozen["assessable_anatomies"]),
            "complete_cases": int(frozen["complete_cases"]),
            "positive_anatomies": int(frozen["primary_positive_anatomies"]),
            "median_anatomy_spearman": float(frozen["primary_median_anatomy_spearman"]),
            "bootstrap_95_ci": list(frozen["primary_bootstrap_95_ci"]),
            "exact_sign_p": float(frozen["primary_exact_sign_p"]),
        },
        "m5_pointwise_characterization": {
            "points": len(points),
            "sigma_blind_spot_points": len(sigma_blind),
            "sigma_blind_spot_point_rate": len(sigma_blind) / len(points),
            "cases_with_sigma_blind_spots": sum(row["sigma_blind_spot_count"] > 0 for row in cases),
            "anatomies_with_sigma_blind_spots": len({row["patient"] for row in sigma_blind}),
            "ice_valid_points": len(ice_valid),
            "ice_blind_spot_points": len(ice_blind),
            "joint_sigma_ice_blind_spot_points": len(joint),
        },
        "m5_case_characterization": {
            "cases": len(cases),
            "positive_case_rankings": sum(value > 0.0 for value in spearman),
            "negative_case_rankings": sum(value < 0.0 for value in spearman),
            "median_case_spearman": float(np.median(spearman)),
            "cases_with_nonpositive_quartile_error_enrichment": sum(
                value <= 0.0 for value in deltas
            ),
            "worst_case": {
                "patient": worst["patient"],
                "replicate": worst["replicate"],
                "sigma_case_spearman": worst["sigma_case_spearman"],
                "sigma_blind_spot_count": worst["sigma_blind_spot_count"],
            },
        },
        "comparator_operational_failures": {
            "invalid_case_counts": invalid_counts,
            "failure_reasons": failure_reasons,
        },
        "anatomy_order_by_sigma_rank_informativeness": sorted(
            anatomy,
            key=lambda row: row["sigma_median_case_spearman"],
        ),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_figures(
    anatomy: list[dict[str, Any]], cases: list[dict[str, Any]], output_root: Path
) -> None:
    patients = [row["patient"] for row in anatomy]
    x = np.arange(len(patients))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for method, label in (
        ("sigma", "Hyperparameter sigma"),
        ("ice", "Inverse-consistency error"),
        ("residual", "Post-registration residual"),
        ("jacdev", "Jacobian deviation"),
    ):
        values = [row[f"{method}_median_case_spearman"] for row in anatomy]
        ax.plot(x, values, marker="o", linewidth=1.5, label=label)
    ax.axhline(0.0, linewidth=1.0)
    ax.set_xticks(x, patients, rotation=45, ha="right")
    ax.set_ylabel("Median case Spearman association")
    ax.set_title("M4 anatomy-level rank informativeness by method")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(
        output_root / "m5_anatomy_comparator_spearman.svg",
        metadata={"Date": None},
    )
    plt.close(fig)

    lookup = {(row["patient"], int(row["replicate"])): row for row in cases}
    matrix = np.asarray(
        [
            [lookup[(patient, replicate)]["sigma_case_spearman"] for replicate in range(3)]
            for patient in patients
        ]
    )
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    image = ax.imshow(matrix, aspect="auto", vmin=-1.0, vmax=1.0)
    ax.set_yticks(np.arange(len(patients)), patients)
    ax.set_xticks(np.arange(3), [f"rep {index}" for index in range(3)])
    ax.set_title("Case-level sigma vs known-error Spearman association")
    fig.colorbar(image, ax=ax).set_label("Spearman association")
    fig.tight_layout()
    fig.savefig(
        output_root / "m5_sigma_case_spearman.svg",
        metadata={"Date": None},
    )
    plt.close(fig)


def run_characterization(
    canonical_artifact_root: Path,
    shard_zip_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    canonical_root = canonical_artifact_root / "outputs"
    canonical_hashes, shard_hashes = _verify_inputs(canonical_root, shard_zip_root)
    canonical_rows = _read_csv(canonical_root / "hyperparameter_known_gt_case_metrics.csv")
    anatomy_rows = _read_csv(canonical_root / "hyperparameter_known_gt_anatomy_metrics.csv")
    comparator_rows = _read_csv(
        canonical_root / "hyperparameter_known_gt_comparator_anatomy_metrics.csv"
    )
    frozen = json.loads(
        (canonical_root / "hyperparameter_known_gt_summary.json").read_text(encoding="utf-8")
    )
    points, cases = _reconstruct(shard_zip_root, canonical_rows)
    anatomy = _anatomy_table(anatomy_rows, comparator_rows)
    summary = _summary(
        canonical_rows,
        points,
        cases,
        anatomy,
        frozen,
        canonical_hashes,
        shard_hashes,
    )

    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv(output_root / "m5_case_characterization.csv", cases)
    _write_csv(output_root / "m5_case_failure_table.csv", build_failure_table(cases))
    _write_csv(output_root / "m5_anatomy_comparator_table.csv", anatomy)
    _write_csv(
        output_root / "m5_sigma_blind_spots.csv",
        [row for row in points if row["sigma_blind_spot"]],
    )
    (output_root / "m5_characterization.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_figures(anatomy, cases, output_root)
    return summary
