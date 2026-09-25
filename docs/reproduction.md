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
