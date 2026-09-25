# Known-ground-truth protocol amendment 1

**Status:** FROZEN before any known-GT geometry preflight or result-bearing estimator execution  
**Date:** 2026-09-24  
**Base protocol:** `docs/hyperparameter_known_gt_protocol.md`  
**Reason:** pre-execution methodological audit  
**Observed known-GT outcomes at freeze:** none

This amendment changes two parts of the frozen hyperparameter-ensemble
known-ground-truth protocol before any scientific outcome from that evaluation
has been generated.

The original protocol remains in the repository unchanged. Where this amendment
conflicts with the base protocol, this amendment governs.

## Why an amendment is necessary

A pre-execution audit identified two avoidable threats to interpretation:

1. the original landmark sampler drew uniformly from the padded crop, so
   background or non-ROI voxels could dominate the primary pointwise
   association even though an expert-checked cancer-extent mask is available;
2. the original permutation test shuffled individual landmarks within each
   case. Landmarks in an image are spatially correlated, so arbitrary
   landmark-level permutation requires an exchangeability assumption that is
   unnecessarily strong.

Neither problem was discovered from a known-GT result. No geometry preflight,
registration output, case correlation, anatomy summary, p-value, or bootstrap
interval from this evaluation had been observed when this amendment was frozen.

## A1. Fixed-domain ROI landmark sampling

This section supersedes Section 8 of the base protocol.

The known-GT evaluation will still use exactly **50 unique fixed-domain
landmarks per synthetic case**, but they will be sampled from the synthetically
warped HECaP cancer-extent ROI rather than uniformly from the full crop.

For each case:

1. start with the cropped source-domain HECaP binary mask on the same grid as
   `moving_source`;
2. use the same known transform `T_known` and the same fixed reference grid
   used to generate `fixed_synth`;
3. generate a fixed-domain ROI mask with nearest-neighbor resampling:

   ```text
   fixed_roi(x) = moving_roi(T_known(x))
   ```

4. restrict candidate voxels to:
   - `fixed_roi > 0`; and
   - the same 8-voxel boundary margin used by the original protocol;
5. require at least 50 eligible voxels;
6. sample exactly 50 unique eligible voxels without replacement using the
   already-frozen landmark seed for that case.

If any case has fewer than 50 eligible ROI voxels, the geometry preflight fails
before any result-bearing registration is run.

### Direction convention

This does **not** require numerical inversion of the B-spline transform.

SimpleITK resampling evaluates the supplied transform from output/reference
space to input space. Because `T_known` already maps the synthetic fixed
domain to the moving-source domain, applying `T_known` to the source-domain
ROI mask produces the corresponding fixed-domain ROI mask directly.

The analytic translation-direction regression test remains mandatory.

### Interpretation boundary

The primary known-error association now characterizes the HECaP cancer-extent
ROI under the synthetic deformation design, not the whole padded crop.

This is a narrower and more clinically interpretable spatial domain.

It still does not establish real T2-to-DCE correspondence ground truth or
clinical utility.

## A2. Anatomy-level exact sign test

This section supersedes Section 14 and modifies Section 15 of the base protocol.

The per-case statistic remains:

```text
rho_case = Spearman(sigma, known_error)
```

The per-anatomy statistic remains:

```text
rho_anatomy = median(rho_case over complete cases for that anatomy)
```

and the global effect summary remains:

```text
T_observed = median(rho_anatomy over assessable anatomies)
```

The evaluation remains assessable only if at least 8 of 10 anatomies are
assessable.

### Primary inferential test

Do **not** assign a landmark-level permutation p-value.

Instead, use the independent anatomy as the inferential unit.

Let:

```text
n = number of assessable anatomies
k = number of assessable anatomies with rho_anatomy > 0
```

An anatomy with `rho_anatomy == 0` is counted as non-positive.

Use the exact one-sided binomial sign test:

```text
H0: P(rho_anatomy > 0) <= 0.5
H1: P(rho_anatomy > 0) > 0.5
```

with:

```text
p_sign = BinomialSignTest(k positives out of n, p0=0.5, alternative="greater")
```

No within-case spatial-exchangeability assumption is required for this
inferential p-value.

### Primary evidence label

Record:

`KNOWN_GT_POINTWISE_ASSOCIATION_POSITIVE=True`

only if all of the following hold:

1. the evaluation is assessable;
2. `T_observed > 0`; and
3. the exact one-sided anatomy sign-test p-value is `<= 0.05`.

Otherwise record it as false.

Always report:

- `T_observed`;
- `k / n` positive anatomies;
- exact sign-test p-value; and
- all individual anatomy-level `rho_anatomy` values.

The Boolean label is a statistical-evidence label only. It is **not** a
minimum-effect-size or clinical-utility criterion. Paper-level interpretation
must discuss the magnitude and distribution of anatomy-level effects.

## A3. Anatomy bootstrap interval

Section 16 remains operationally unchanged:

- resample assessable anatomies with replacement;
- 10,000 replicates;
- seed 0;
- percentile 95% interval for the median anatomy effect.

Because only 8-10 anatomies can contribute, the interval is explicitly
secondary/descriptive and must not be used as the sole basis for a strong
generalization claim.

The complete vector of anatomy-level effects must be reported alongside it.

## A4. Geometry-preflight additions

For every synthetic case, the geometry record must additionally contain:

- eligible fixed-domain ROI voxel count after the boundary margin;
- sampled ROI landmark count;
- confirmation that every sampled landmark belongs to the fixed-domain ROI.

Any violation is a geometry-preflight failure and stops the study before
result-bearing registration.

## A5. What does not change

This amendment does not alter:

- the ten held-out anatomies;
- the promotion-patient exclusion;
- the three deformation replicates per anatomy;
- the case/noise/landmark seed schedule;
- the known B-spline deformation distribution;
- image-noise scale;
- 9-member hyperparameter estimator;
- mesh size or iteration budget;
- all-member validity requirement;
- per-case Spearman endpoint;
- minimum 2/3 complete cases per anatomy;
- minimum 8/10 assessable anatomies;
- calibration being downstream of informativeness;
- the prohibition on changing the estimator based on known-GT outcomes.

## A6. Scientific rationale

Medical-image registration accuracy is typically evaluated with landmarks
distributed through the region of interest, and multiple observations within a
patient are statistically clustered rather than independent. The amendment
therefore narrows the spatial sampling domain to the available expert-checked
ROI and moves formal inference completely to the patient/anatomy level.

The change is intentionally made before outcomes so it cannot be selected for a
more favorable result.

## Frozen status

`KNOWN_GT_PROTOCOL_AMENDMENT_1=FROZEN`

`KNOWN_GT_GEOMETRY_PREFLIGHT_RUN_AT_FREEZE=NO`

`KNOWN_GT_RESULT_BEARING_REGISTRATION_RUN_AT_FREEZE=NO`

`KNOWN_GT_STATISTICAL_OUTCOME_OBSERVED_AT_FREEZE=NO`
