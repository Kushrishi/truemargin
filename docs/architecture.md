# Architecture

TrueMargin is organized around a validation problem rather than a product
workflow:

> **Does a registration-derived uncertainty or quality surrogate contain useful
> information about true local spatial registration error?**

The active architecture separates data/geometry, registration, surrogate
construction, validation, and provenance so a change at one layer cannot
silently redefine the scientific question.

## Coordinate convention

The current 3-D pipeline uses the following conventions:

- NumPy image grids: `(z, y, x)`;
- SimpleITK physical coordinates: `(x, y, z)` in millimetres;
- displacement-vector components: `(x, y, z)`;
- stored displacement fields: `(D, z, y, x)`;
- known synthetic transform: **fixed -> moving**.

The conversion between array index order and physical/vector order is explicit
and regression-tested.

For a fixed-domain location `x`, the known deformation is:

```text
u_true(x) = T_known(x) - x
```

and registration error is:

```text
error(x) = ||u_est(x) - u_true(x)||_2
```

## Active research path

```text
public TCIA T2 anatomy
        +
HECaP cancer-extent ROI
        |
        v
crop source anatomy
        |
        v
apply deterministic known B-spline deformation
        |
        +------> fixed synthetic image
        |
        +------> fixed-domain warped HECaP ROI
        |
        v
run frozen registration-surrogate method
        |
        +------> estimated displacement field
        |
        +------> local surrogate spread / score
        |
        v
sample 50 fixed-domain ROI locations
        |
        v
compare surrogate with known local error
        |
        v
case-level rank association
        |
        v
anatomy-level aggregation and inference
```

The real-data zero-displacement analyses that motivated parts of the project are
historical development evidence. They are not the current pointwise
ground-truth validation path.

## Module boundaries

| Layer | Main code | Responsibility |
| --- | --- | --- |
| I/O / geometry | `io_utils.py` | DICOM/mask loading, grid checks, coordinate sampling |
| registration | `registration.py` | B-spline registration and historical uncertainty mechanisms |
| candidate surrogate | `hyperparameter.py`, `ensemble.py` | fixed estimator definitions and member validation |
| error / calibration | `calibration.py` | displacement error, association/calibration primitives |
| geometry helpers | `synthetic.py` | synthetic utilities retained for historical/general tests |
| provenance | `provenance.py` | source/config/data fingerprints for checkpoints |
| experiment runners | `scripts/` | prospective experiment execution and reporting |

## Evidence hierarchy

The project deliberately distinguishes:

1. **mechanism viability** — can an estimator be computed reproducibly and is it
   non-inert?
2. **informativeness** — does a larger surrogate value rank larger known error?
3. **calibration** — does a numerical uncertainty scale have the stated
   coverage?
4. **blind spots** — where is error high despite a low surrogate value?
5. **robustness/generalization** — do conclusions survive deformation regimes,
   anatomies, datasets, and registration families?

Passing one layer does not imply the next.

## Current estimator

The active primary estimator is the prospectively promoted nine-member
registration-hyperparameter sensitivity ensemble:

```text
Mattes-MI bins:            32, 50, 64
LBFGSB gradient tolerance: 1e-4, 1e-5, 1e-6
mesh size:                 3
maximum iterations:        15
members:                   9
```

Its scalar `sigma` is an RMS spread of displacement fields across this
deterministic hyperparameter grid. It is a **sensitivity surrogate**, not a
Bayesian posterior standard deviation.

The current known-ground-truth study tests whether that surrogate is informative
about true local spatial error before any calibration claim is considered.

## Provenance contract

Result checkpoints embed:

- exact result-defining source-file hashes;
- protocol/configuration parameters;
- data identity;
- project version;
- producing Git SHA.

Compatibility is based on the scientific source/configuration fingerprint, so a
documentation-only commit does not invalidate an otherwise identical expensive
checkpoint.

A checkpoint without valid provenance must not be silently reused.

## Data boundary

The project uses the public, de-identified TCIA
**Prostate Fused-MRI-Pathology** collection. Images, masks, and generated
checkpoints are excluded from ordinary Git history.

The HECaP cancer-extent masks are used as spatial ROIs. They do not provide a
measured T2-to-DCE displacement field. In the active known-GT study, exact
correspondence is instead created by a synthetic transform applied to a real T2
anatomy.

## Historical material

Superseded manuscript/product framing and older exploratory narratives are
preserved under `archive/` for provenance. They are not the current
architecture or scientific source of truth.

## Non-goals

TrueMargin is not currently:

- a medical device or clinical decision system;
- a claim of clinical registration accuracy;
- a new registration algorithm;
- a validated probabilistic posterior;
- an externally validated benchmark;
- a finished paper.

The project is an uncertainty/error validation study.
