# Reproduction

## Environment

TrueMargin currently targets Python 3.12.

For a development environment with the real-data registration dependencies:

```bash
python -m pip install -e ".[realdata,dev]"
```

On Linux, OpenSlide also requires the system OpenSlide library. The public CI
workflow installs it explicitly before the Python package.

## Software verification

Run:

```bash
ruff check src tests scripts
black --check src tests scripts
mypy
pytest
```

These checks do not require the TCIA imaging dataset.

## Data

See `data/README.md` for the public TCIA collection, expected local layout,
HECaP ROI role, and the frozen promotion/held-out anatomy split. Imaging data
remain outside Git.

## Known-ground-truth execution

Before either execution mode starts, the runner verifies the frozen protocol
files against their public Git blob identities:

- base protocol: `98a747c502a4aca6d8e65f8373bc4e62a8f1b7a0`;
- Amendment 1: `1eafe77bb847b1a77229e267ef32e6bbedd27bc2`.

These blobs are byte-identical to the original private freeze commits recorded
in `research/DECISION_LOG.md`.

The first permitted scientific execution is geometry only:

```bash
python scripts/19_hyperparameter_known_gt_validation.py --geometry-only
```

This validates all 30 predeclared synthetic cases and exits before the
nine-member estimator is run.

Result-bearing execution is intentionally locked. After the geometry record is
reviewed and preserved, a separate research milestone must create
`research/KNOWN_GT_RUN_REQUEST.json` that pins the reviewed record and frozen
study contract. Only then may:

```bash
python scripts/19_hyperparameter_known_gt_validation.py --run-result-bearing
```

proceed.

Do not create the run request merely to bypass the gate.
