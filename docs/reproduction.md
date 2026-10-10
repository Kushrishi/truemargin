# Reproduction

The controlled studies are complete. [Current status](../research/STATE.md) links
the accepted result reports. Historical execution gates below describe those
original runs; they are not a request to rerun completed experiments or open new
held-out data.

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

## Verify completed results without registration

From the repository root, using Python 3.12:

```bash
python scripts/verify_m6_phase_a_result.py results/m6_phase_a
python scripts/verify_m6_phase_b_result.py results/m6_phase_b
```

These standard-library verifiers check retained calibration and evaluation
records, hashes, cohort identities and numerical summaries. They do not download
images, execute registration, refit thresholds or access external landmarks.
The first command checks the 30-anatomy calibration record; the second checks the
30-anatomy evaluation record against sealed thresholds. A mismatch exits nonzero.
This verifies the saved evidence, not a fresh reproduction of image registration.

To redraw the descriptive figure from committed outputs:

```bash
python scripts/plot_m4_m6_evidence.py . /tmp/truemargin-evidence
```

This writes PNG and SVG files. It requires the package's plotting dependencies
and does not run an experiment. See the [evidence guide](../research/README.md)
for study names and the [results index](../results/README.md) for retained files.

## Historical execution instructions

The remaining commands describe the original controlled-study execution. Use
its pinned source and protocol when reproducing it; editing a run request is not
an installation step. The current external study has a separate design.

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
