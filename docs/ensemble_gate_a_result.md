# Prospective ensemble perturbation Gate A result

Date: 2026-09-13

## Status

**Gate A failed prospectively. No corrected relative-STD perturbation alpha was promoted.**

The experiment was executed from Git commit
`4c1b72fb336eb09a61d39c4094990c5dd7a8592f`, using the protocol frozen on
main at `fe90dac687b1f847e7f98cb7d9d3a13c172c9f96`.

The predeclared five-patient sensitivity cohort was:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

The registration regime remained the frozen `fast_dev` configuration:
mesh size 3, maximum 15 iterations, seed 0, five ensemble members per
patient-setting, deterministic middle DCE phase, and up to 75 HECaP-derived
evaluation points per patient.

Real-data error used the existing zero-displacement proxy/reference assumption.
It is **not** independently verified pointwise T2-to-DCE registration ground
truth.

## Predeclared decision rule

For each nonzero `relative_std` alpha in `{0.01, 0.02, 0.05, 0.10}`, promotion
required all of the following:

1. at least 4/5 patients complete without an unstable ensemble member;
2. at least 4/5 patients with median sigma above the predeclared repeatability
   floor criterion relative to `alpha=0`;
3. at least four patients shared between the candidate and `alpha=0` for the
   proxy-error comparison; and
4. patient-median proxy-error ratio no greater than 1.25 versus `alpha=0`.

The smallest eligible nonzero alpha would have been selected. Pointwise
Spearman/Pearson correlation, calibration metrics, blind-spot metrics, and
other informativeness diagnostics were explicitly excluded from alpha
selection.

## Gate A outcome

| Relative-STD alpha | Complete | Above repeatability floor | Shared error | Proxy-error ratio vs alpha=0 | Eligible |
| ---: | ---: | ---: | ---: | ---: | :---: |
| 0.01 | 4/5 | 3/5 | 4/5 | 1.110 | No |
| 0.02 | 1/5 | 0/5 | 1/5 | 0.410 | No |
| 0.05 | 2/5 | 1/5 | 2/5 | 2.069 | No |
| 0.10 | 4/5 | 3/5 | 4/5 | 2.359 | No |

`SELECTED_ALPHA=None`.

Therefore the predeclared action is:

> Stop at Gate A. Do not widen or tune the perturbation grid post hoc, and do
> not proceed to ensemble-size sensitivity for this mechanism.

## Interpretation

The scale-aware additive input-intensity perturbation repair did not produce a
candidate that was simultaneously non-inert across enough patients, stable
across enough patients, and acceptably non-destructive to proxy registration
error.

The nearest candidate was `alpha=0.01`: it met the completion requirement
(4/5) and stayed within the proxy-error degradation limit (ratio 1.110), but
only 3/5 patients exceeded the repeatability-floor criterion, below the frozen
4/5 requirement.

Larger perturbations did not rescue the mechanism. `alpha=0.02` and
`alpha=0.05` were frequently unstable. `alpha=0.10` completed in 4/5 patients
and exceeded the repeatability floor in 3/5, but its patient-median proxy error
was approximately 2.36 times the `alpha=0` reference, well outside the
predeclared 1.25 limit.

This result does **not** establish that all registration-uncertainty ensembles
are uninformative. It establishes only that this prospectively defined
relative-STD additive input-intensity perturbation mechanism did not earn
promotion under the frozen Gate A criteria.

It also means the historical absolute-intensity ensemble should not be treated
as repaired merely by rescaling its input noise. A scientifically justified
replacement mechanism requires a new prospective design rather than post-hoc
expansion of the observed alpha grid.

## Descriptive observations not used for selection

Some patient-setting results continued to show large discrepancies between
repeatability-style uncertainty and proxy registration error. For example,
`aaa0066` at `alpha=0` had essentially zero median sigma while retaining
nonzero median proxy error, and `aaa0063` likewise showed a very small
repeatability sigma despite much larger proxy error. These observations are
scientifically relevant to the broader TrueMargin question, but they were not
used to select or reject an alpha.

Conversely, some stronger perturbations produced high within-patient
sigma-error correlations while also causing unstable registrations or large
proxy-error degradation. Favorable pointwise correlation therefore did not
override the predeclared stability and degradation gate.

## Execution and provenance notes

The sensitivity run completed all 30 patient-setting combinations
(5 patients x 6 settings), corresponding to 150 attempted registrations.
Patient-setting checkpoints were written with dedicated sensitivity provenance
under `outputs/checkpoints/ensemble_jitter_sensitivity/`.

The TCIA data were re-downloaded on the execution machine and the exact frozen
T2/DCE series identities were verified before the run. The current TCIA Data
Retriever placed `md5hashes.csv` metadata files inside series directories;
these non-DICOM checksum files were removed only from the derived canonical
TrueMargin data copy before execution because the frozen DCE loader expects
series directories to contain image files. The raw TCIA download was left
unchanged. No tracked scientific code was modified for this operational repair.

## Next step

Do **not** run the planned `n=5/10/20` ensemble-size sensitivity because Gate A
did not select an alpha.

Before defining a replacement uncertainty ensemble, characterize registration
convergence/stability prospectively on the same frozen five-patient cohort.
This will determine whether the 15-iteration `fast_dev` regime is itself stable
enough for perturbation-based uncertainty experiments and will separate
registration non-convergence from uncertainty-mechanism failure.

Only after that convergence gate should a new uncertainty mechanism be frozen
prospectively (for example, a scientifically justified optimization- or
hyperparameter-perturbation ensemble).