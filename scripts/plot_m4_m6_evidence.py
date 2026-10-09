"""Render descriptive evidence panels from retained study outputs (requires matplotlib)."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render(root, output):
    with (root / "results/m5/m5_anatomy_comparator_table.csv").open() as stream:
        anatomies = list(csv.DictReader(stream))
    with (root / "results/m5/m5_case_characterization.csv").open() as stream:
        cases = list(csv.DictReader(stream))
    evaluation = json.loads(
        (root / "results/m6_phase_b/outputs/m6_phase_b/m6_phase_b_evaluation.json").read_text()
    )
    exploration = json.loads(
        (root / "results/m6_exploratory/constant_radius_comparison.json").read_text()
    )
    plt.rcParams.update(
        {
            "font.size": 16,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    methods = [
        ("sigma", "Registration\nspread"),
        ("ice", "Inverse\nconsistency\nerror"),
        ("residual", "Intensity\nresidual"),
        ("jacdev", "Jacobian\ndeviation"),
    ]
    for index, (key, _label) in enumerate(methods):
        values = [float(row[key + "_median_case_spearman"]) for row in anatomies]
        axes[0, 0].scatter([index] * len(values), values, s=24, alpha=0.65)
    axes[0, 0].set(
        xticks=range(4),
        xticklabels=[label for _, label in methods],
        ylim=(-1, 1),
        ylabel="Patient median rank correlation\nwith error",
        title="A  Local error ranking: 10 patients",
    )
    axes[0, 0].axhline(0, color="0.7", linewidth=0.8)
    values = [float(row["sigma_case_spearman"]) for row in cases]
    axes[0, 1].bar(
        range(1, len(values) + 1),
        values,
        color=["#b94848" if value < 0 else "#356b91" for value in values],
    )
    axes[0, 1].set(
        ylim=(-1, 1),
        xlabel="Synthetic deformation case (3 per patient)",
        ylabel="Spread/error rank correlation\n(Spearman)",
        title="B  Six of 30 cases reverse the relationship",
    )
    axes[0, 1].axhline(0, color="0.4", linewidth=0.8)
    colors = {"prostate_3t": "#356b91", "prostate_diagnosis": "#b56e24"}
    labels = {"prostate_3t": "Prostate-3T", "prostate_diagnosis": "Prostate-Diagnosis"}
    for source, color in colors.items():
        level = evaluation["sources"][source]["methods"]["sigma"]["levels"]["0.90"]
        radii = level["radius_efficiency"]["per_anatomy_median_radius_mm"]
        patients = evaluation["sources"][source]["patients"]
        coverages = [100 * level["per_anatomy_coverage"][p] for p in patients]
        axes[1, 0].scatter(radii, coverages, color=color, s=30, alpha=0.7, label=labels[source])
        result = exploration["sources"][source]["0.90"]
        for method, marker in (("sigma", "o"), ("constant", "s")):
            axes[1, 1].scatter(
                result[method + "_equal_anatomy_mean_radius_mm"],
                100 * result[method + "_equal_anatomy_coverage"],
                marker=marker,
                color=color,
                s=65,
            )
            axes[1, 1].annotate(
                ("3T" if source == "prostate_3t" else "Diagnosis")
                + "\n"
                + ("spread-derived" if method == "sigma" else "constant"),
                (
                    result[method + "_equal_anatomy_mean_radius_mm"],
                    100 * result[method + "_equal_anatomy_coverage"],
                ),
                xytext={
                    ("prostate_3t", "sigma"): (10, 15),
                    ("prostate_3t", "constant"): (10, -45),
                    ("prostate_diagnosis", "sigma"): (10, -35),
                    ("prostate_diagnosis", "constant"): (30, 8),
                }[(source, method)],
                textcoords="offset points",
                fontsize=14,
            )
    axes[1, 0].set(
        xscale="log",
        xlabel="Patient median bound radius\n(mm, log scale)",
        ylabel="Sampled errors inside bounds (%)",
        ylim=(85, 102),
        title="C  Calibrated bounds: 30 evaluation patients",
    )
    axes[1, 0].annotate(
        "Prostate-Diagnosis: 70.69 mm",
        (70.69423944096118, 100),
        xytext=(-185, -30),
        textcoords="offset points",
        arrowprops={"arrowstyle": "-", "color": "0.4"},
        fontsize=14,
    )
    axes[1, 0].legend(frameon=False, loc="lower right")
    axes[1, 1].set(
        xlim=(0, 14),
        ylim=(89, 102),
        xlabel="Mean bound radius (mm)\nPatients weighted equally",
        ylabel="Mean coverage (%)\nPatients weighted equally",
        title="D  Exploratory comparison: coverage differs",
    )
    for axis in axes[1]:
        axis.axhline(90, color="0.5", linewidth=0.8, linestyle="--")
        axis.text(
            0.98,
            90.25,
            "Target coverage: 90%",
            transform=axis.get_yaxis_transform(),
            ha="right",
            fontsize=14,
            color="0.4",
        )
    fig.suptitle("Registration variability, known error and calibrated bounds", fontsize=20)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170, bbox_inches="tight", pad_inches=0.15)
    svg_path = output.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.15)
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n"
    )
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()
    render(args.repository_root, args.output_stem)
