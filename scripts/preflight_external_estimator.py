"""Training-only operational probe; no landmark imports or result statistics.

Runs one fixed member/direction per invocation so the supervising shell can
apply a prospective resource budget without changing estimator parameters.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from truemargin.external_lung import discover_training_pairs, inspect_pair
from truemargin.registration import baseline_bspline_registration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_root", type=Path)
    parser.add_argument("--case", choices=tuple(f"{i:03}" for i in range(1, 21)), default="001")
    parser.add_argument("--bins", type=int, choices=(32, 50, 64), default=32)
    parser.add_argument("--tolerance", type=float, choices=(1e-4, 1e-5, 1e-6), default=1e-4)
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()
    pairs = discover_training_pairs(args.training_root)
    if {p.case_id for p in pairs} != {f"{i:03}" for i in range(1, 21)}:
        raise ValueError("operational probe requires the official 001–020 training cohort")
    pair = next(p for p in pairs if p.case_id == args.case)
    geometry = inspect_pair(pair)
    # The historical array estimator preserves spacing but not direction/origin.
    # This probe is not a coordinate-conversion implementation. Refuse noncanonical grids.
    if not np.allclose(geometry.direction, np.eye(3).ravel(), atol=0, rtol=0):
        raise ValueError("array estimator probe requires identity direction")
    fixed = sitk.GetArrayFromImage(sitk.ReadImage(str(pair.fixed_path)))
    moving = sitk.GetArrayFromImage(sitk.ReadImage(str(pair.moving_path)))
    if args.reverse:
        fixed, moving = moving, fixed
    start = time.perf_counter()
    record = {
        "case_id": args.case,
        "landmarks_accessed": False,
        "direction": "reverse" if args.reverse else "forward",
        "metric_bins": args.bins,
        "gradient_tolerance": args.tolerance,
        "mesh_size": 3,
        "max_iterations": 15,
        "center_first": False,
        "sitk_version": sitk.Version_VersionString(),
        "sitk_threads": sitk.ProcessObject.GetGlobalDefaultNumberOfThreads(),
        "input_shape_zyx": list(fixed.shape),
        "spacing_xyz": list(geometry.spacing_xyz),
    }
    try:
        print(json.dumps({**record, "event": "member_start"}), file=sys.stderr, flush=True)

        def progress(iteration, metric):
            print(
                json.dumps(
                    {
                        "event": "optimizer_progress",
                        "case_id": args.case,
                        "iteration": iteration,
                        "metric": metric,
                        "elapsed_seconds": time.perf_counter() - start,
                    }
                ),
                file=sys.stderr,
                flush=True,
            )

        field = baseline_bspline_registration(
            fixed,
            moving,
            mesh_size=3,
            max_iterations=15,
            spacing=geometry.spacing_xyz,
            center_first=False,
            metric_bins=args.bins,
            gradient_convergence_tolerance=args.tolerance,
            progress_callback=progress,
            completion_callback=record.update,
        )
        record.update(
            status="completed",
            output_shape=list(field.shape),
            finite=bool(np.isfinite(field).all()),
            expected_shape=bool(field.shape == (3, *fixed.shape)),
        )
    except Exception as error:
        record.update(status="failed", error_type=type(error).__name__, error=str(error))
    record.update(
        wall_seconds=time.perf_counter() - start,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    )
    print(json.dumps(record, sort_keys=True, indent=2, allow_nan=False))
    if (
        record["status"] != "completed"
        or not record.get("finite")
        or not record.get("expected_shape")
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
