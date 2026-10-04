# External lung CT validation protocol

## Purpose

This study tests whether the local rank-information result observed in TrueMargin's
prostate experiments transfers to a different anatomy, acquisition source, and
registration problem.

The question is:

> Does the unchanged nine-member registration-hyperparameter ensemble produce
> local spread that ranks true landmark registration error on an external lung
> CT dataset?

This is an external replication of informativeness and failure behavior. It is
not a new estimator and is not a clinical validation study.

## Dataset

Use the Learn2Reg Lung CT inspiration-expiration registration task.

Official sources:

- training archive: https://doi.org/10.5281/zenodo.3835682
- test archive: https://doi.org/10.5281/zenodo.4048761
- challenge description: https://learn2reg.grand-challenge.org/Datasets/

Published archive identities:

- `training.zip`: MD5 `cd4ef606641b915603a8a0f6a4664a6c`
- `testData.zip`: MD5 `573c7f936e9af111fa536559238af172`

The challenge provides 30 3-D lung CT volumes (20 training, 10 test). The
registration direction is expiration as fixed image and inspiration as moving
image. The held-out test cases have manual landmarks.

The challenge-preprocessed images are the analysis inputs. The original-resolution
8.1 GB archive is not required for this study.

## Frozen estimator

Do not tune the estimator on lung landmark outcomes.

Use the existing `truemargin.hyperparameter` configuration unchanged:

- 3-D B-spline registration;
- mesh size 3;
- maximum 15 optimizer iterations;
- `center_first = False`;
- Mattes mutual-information bins: 32, 50, 64;
- LBFGSB gradient convergence tolerances: 1e-4, 1e-5, 1e-6;
- all nine members required for a complete target estimate.

Use physical voxel spacing from the NIfTI image metadata. No outcome-driven
intensity normalization, crop selection, member filtering, or optimizer changes
are allowed after manual test landmarks are inspected.

## Comparators

For every target-complete test pair, evaluate the existing direct comparators:

1. inverse-consistency error (ICE), using the same nine-member ensemble in the
   reverse direction;
2. same-modality absolute residual;
3. Jacobian deviation.

Comparator failure remains method-specific and must not change target
completeness.

## Landmark error

For each fixed-image landmark, sample the ensemble-mean forward displacement in
physical space and predict its corresponding moving-image location.

True local registration error is the Euclidean distance in millimetres between
that predicted location and the provided moving-image manual landmark.

The target uncertainty score is ensemble spread sampled at the same fixed-image
landmark.

Coordinate conversion, interpolation, and axis-order logic must be covered by
synthetic tests before test landmark values are read.

## Primary analysis

The inferential unit is the test case, not the individual landmark.

For each of the 10 held-out test pairs:

- compute Spearman association between target spread and landmark error;
- record whether the association is positive;
- retain all complete cases without selecting by result.

Primary aggregate:

- median case-level Spearman association;
- number of positive case-level associations out of 10;
- exact one-sided sign test against 0.5;
- 10,000-replicate case bootstrap interval for the median.

The primary claim is limited to local rank informativeness on this external
dataset.

## Comparator analysis

For each assessable comparator, compute the same case-level Spearman statistic.

Report paired case-level target-minus-comparator differences. ICE is the
principal comparator. A superiority claim requires the predeclared paired
interval to exclude zero; otherwise report no established superiority.

Comparator failures are retained and reported.

## Failure characterization

Reuse the existing within-case descriptive blind-spot rule:

- high error: landmark error at or above the case 75th percentile;
- low score: uncertainty/comparator score at or below the case 25th percentile.

Report blind-spot counts and the number of affected cases. This is secondary
failure characterization, not a second confirmatory endpoint.

## What is not tested here

This external study does **not** estimate or validate new numerical error-radius
calibration. Ten manual-landmark test pairs are too small to create a credible
new calibration/evaluation split while preserving an independent external
assessment.

The previously observed M6 calibration results remain separate.

The study also does not establish:

- clinical usefulness;
- universal registration-error prediction;
- superiority over ICE unless the paired external result supports it;
- performance of a learned/deep registration model;
- generalization beyond this lung CT task.

## Execution order

Before accessing manual test landmark values:

1. verify archive identity;
2. inventory filenames and image geometry;
3. implement and test NIfTI loading plus landmark coordinate conversion;
4. run estimator-only operational preflight on training image pairs;
5. freeze exact test-pair identities and analysis code;
6. only then read manual test landmarks and execute the result-bearing study.

If the unchanged estimator is operationally infeasible on the training images,
stop and report that result. Do not redesign it using test landmark outcomes.

## Related work boundary

Recent work already establishes that registration uncertainty and conformal
prediction are active research areas, including CONReg (2026), and recent
phantom work reports strong association between ICE and ground-truth
registration error.

The contribution sought here is therefore not "uncertainty for registration."
It is a controlled external test of when a simple operational variability signal
contains local error information, how often it fails, and whether it adds
anything beyond simpler quality signals.

References:

- Gheiji et al., *CONReg: Uncertainty-Aware Medical Image Registration Using
  Conformal Prediction*, Journal of Imaging Informatics in Medicine, 2026.
  https://doi.org/10.1007/s10278-026-01878-3
- Learn2Reg Lung CT dataset and challenge:
  https://learn2reg.grand-challenge.org/Datasets/
