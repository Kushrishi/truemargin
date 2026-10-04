"""Inventory Learn2Reg LungCT training images without reading landmarks."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from truemargin.external_lung import discover_training_pairs, preflight_training


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Extracted Learn2Reg LungCT training directory")
    parser.add_argument("--expected-pairs", type=int, default=20)
    args = parser.parse_args()

    if args.expected_pairs < 1:
        parser.error("--expected-pairs must be positive")

    pairs = discover_training_pairs(args.root)
    geometry = preflight_training(args.root, expected_pairs=args.expected_pairs)
    payload = {
        "record": "external-lung-training-preflight",
        "landmarks_accessed": False,
        "pair_count": len(pairs),
        "pairs": [
            {
                **asdict(row),
                "fixed_path": str(pair.fixed_path.relative_to(args.root)),
                "moving_path": str(pair.moving_path.relative_to(args.root)),
                "fixed_mask_present": pair.fixed_mask_path is not None,
                "moving_mask_present": pair.moving_mask_path is not None,
            }
            for pair, row in zip(pairs, geometry, strict=True)
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
