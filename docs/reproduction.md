# Reproduction

The controlled studies are complete. [Current status](../research/STATE.md) links
the result reports. Historical execution instructions below describe the original
runs, not new experiments.

## Environment

Use Python 3.12 and a Git checkout. Tests that verify source provenance need the
checkout's Git metadata; a downloaded source archive is not equivalent.

Install the OpenSlide system library before the Python dependencies. CI tests
Ubuntu and macOS:

```bash
# Ubuntu
sudo apt-get update
sudo apt-get install -y libopenslide0

# macOS, using Homebrew
brew install openslide
```

Run only the command for your operating system. From the repository root, create
an isolated Python environment and install both dependency groups:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[realdata,dev]"
```

The `realdata` group supplies SimpleITK and the Python OpenSlide interface; the
`dev` group supplies the test and code-checking tools. Installing `dev` alone is
not sufficient for the full test suite.

## Software verification

Run:

```bash
ruff check src tests scripts
black --check src tests scripts
mypy
pytest
```

These checks do not require the TCIA imaging dataset. They test the software;
they do not rerun the completed imaging studies.

## Verify completed results without registration

From the repository root, using Python 3.12:

```bash
python scripts/verify_m6_phase_a_result.py results/m6_phase_a
python scripts/verify_m6_phase_b_result.py results/m6_phase_b
```

These standard-library verifiers check saved records, hashes, cohort identities
and numerical summaries. They do not download images, execute registration,
refit thresholds or access external landmarks. The first command checks the
30-anatomy calibration record; the second checks the separate 30-anatomy
evaluation record against the saved thresholds. A mismatch exits nonzero.

To redraw the descriptive figure from committed outputs:

```bash
python scripts/plot_m4_m6_evidence.py . /tmp/truemargin-evidence
```

This writes PNG and SVG files using the package's plotting dependencies. See the
[research guide](../research/README.md) and [results index](../results/README.md)
for the study names and saved files.

## Historical execution instructions

The remaining commands describe the original controlled-study execution. Use
its pinned source and protocol when reproducing it; editing a run request is not
an installation step. The external study has a separate design.

## Data

See [data/README.md](../data/README.md) for the TCIA collection, expected local
layout, HECaP ROI role and original anatomy split. Imaging data remain outside Git.

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
