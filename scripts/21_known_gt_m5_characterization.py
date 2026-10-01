#!/usr/bin/env python3
"""Characterize frozen TrueMargin M4 outputs without rerunning registration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from truemargin.m5_characterization import run_characterization  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical-artifact-root",
        type=Path,
        required=True,
        help="Extracted canonical M4 result artifact containing outputs/.",
    )
    parser.add_argument(
        "--shard-zip-root",
        type=Path,
        required=True,
        help="Directory containing the ten preserved M4 patient shard ZIP archives.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "outputs" / "m5_characterization",
        help="Directory for descriptive M5 tables, JSON, and figures.",
    )
    args = parser.parse_args()

    summary = run_characterization(
        args.canonical_artifact_root,
        args.shard_zip_root,
        args.output_root,
    )
    pointwise = summary["m5_pointwise_characterization"]
    cases = summary["m5_case_characterization"]
    print(f"M5_OUTPUT_ROOT={args.output_root}")
    print(f"M5_SIGMA_BLIND_SPOT_POINTS={pointwise['sigma_blind_spot_points']}")
    print(f"M5_CASES_WITH_SIGMA_BLIND_SPOTS={pointwise['cases_with_sigma_blind_spots']}")
    print(f"M5_NEGATIVE_CASE_RANKINGS={cases['negative_case_rankings']}")
    print("M5_CHARACTERIZATION=COMPLETE")


if __name__ == "__main__":
    main()
