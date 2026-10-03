# M6 source-stratified hierarchical calibration protocol

**Status:** prospective freeze before M6 synthetic-deformation preflight, registration, calibration fit, or evaluation  
**Date:** 2026-10-02  
**Milestone:** M6 — calibration  
**Primary signal:** frozen nine-member hyperparameter-ensemble sigma  
**Secondary calibrated comparator:** ensemble-mean inverse-consistency error (ICE)  
**Result-bearing execution authorized by this protocol:** **no**

## 1. Question and claim boundary

M6 asks whether the already-promoted TrueMargin registration-sensitivity signal can be converted into a numerically interpretable upper radius for true local registration error on previously unseen anatomies without:

- reusing M4 outcomes for fitting;
- treating spatial locations as independent patients;
- changing the frozen nine-member estimator after observing calibration results; or
- hiding operational failures, zero-signal cases, or wide/infinite intervals.

Calibration is not a novelty claim. Conformal prediction has already been applied to medical image registration, including CONReg (2026). The methodological role of M6 is to test a frozen signal under a prospectively separated calibration/evaluation design while respecting anatomy-level dependence.

The primary formal target is a **source-specific marginal coverage statement for a randomly sampled eligible ROI location in a new exchangeable anatomy from the same source/acquisition regime**, under the hierarchical-exchangeability assumptions stated below.

Do not describe the guarantee as:

- simultaneous whole-volume coverage;
- guaranteed 90% coverage for every anatomy;
- conditional coverage for an arbitrary fixed voxel;
- external-dataset generalization; or
- clinical validity.

## 2. Frozen evidence entering M6

M6 begins only after the following pre-result gates:

1. the official 80-subject NCI-ISBI challenge identity surface was audited successfully;
2. all 60 official training anatomies passed the prospective geometry/label eligibility gate;
3. exact DICOM identity comparison found zero overlapping SeriesInstanceUIDs and zero overlapping StudyInstanceUIDs between the frozen ten-anatomy M4 confirmatory cohort and the audited M6 challenge surface.

The 10 official leaderboard and 10 official test subjects remain untouched by M6 and are reserved for a separately frozen M7 robustness study. They are part of the same challenge/source collections and must not be called a separate external dataset.

## 3. Frozen M6 cohort roles

M6 uses only the 60 official challenge training anatomies.

Cohort roles are frozen in `research/M6_SPLIT.json`.

Within each source independently:

- 30 `prostate_3t` anatomies -> 15 calibration + 15 evaluation;
- 30 `prostate_diagnosis` anatomies -> 15 calibration + 15 evaluation.

Assignment uses only immutable pre-outcome identity:

```text
digest = SHA256("truemargin-m6-v1|split|" + patient_id)
```

Within each source, sort by ascending hexadecimal digest with lexical `patient_id` as the impossible-tie fallback. The first 15 are calibration and the final 15 are evaluation.

No registration, sigma, ICE, known-error, deformation-effect, or calibration outcome may alter these roles. Failed cases are not replaced and roles are never swapped after outcomes.

## 4. Source-stratified HCP rather than pooled calibration

The two challenge sources reflect materially different acquisition regimes. M6 therefore does not assume that all 30 calibration anatomies are identically distributed across source.

Fit hierarchical conformal thresholds **separately within each source**.

For each source:

- calibration groups `K = 15` anatomies;
- each valid anatomy contributes exactly `n_k = 50` sampled ROI locations;
- each anatomy receives equal total calibration weight;
- evaluation uses the 15 different frozen evaluation anatomies from that source.

This follows the Hierarchical Conformal Prediction (HCP) construction of Lee, Barber, and Willett, *Distribution-free inference with hierarchical data*, ACM Journal of Data Science (2026), DOI `10.1145/3786352`.

The older Dunn-Wasserman-Ramdas two-layer conformal methods remain related background, not the primary M6 procedure.

### 4.1 Hierarchical-exchangeability interpretation

For the formal HCP interpretation, the relevant hierarchy is:

```text
group = anatomy
within-group observation = one uniformly sampled eligible fixed-domain ROI location
```

The assumption is that, within a source/acquisition regime:

1. calibration and future evaluation anatomies are exchangeable at the group level; and
2. the 50 sampled eligible ROI locations are exchangeable under the frozen uniform-without-replacement sampling mechanism.

The deterministic PRNG seed is fixed from patient identity before registration outcomes. Conditional on an anatomy, the 50 locations are sampled uniformly without replacement from the prospectively defined eligible ROI population.

If these assumptions are judged scientifically implausible after results, narrow the coverage claim. Do not change the sampling scheme or source pooling after seeing evaluation coverage.

## 5. Anatomy preparation

For every M6 training anatomy:

1. load the exact frozen T2 source series identified by the completed identity audit;
2. load the exact official challenge NRRD label;
3. nearest-neighbour resample the label onto the DICOM image grid using physical geometry;
4. define the source prostate ROI as the union of label values `1` and `2`;
5. require the completed M6 geometry-eligibility criteria to remain satisfied;
6. crop to the resampled prostate-ROI bounding box with the same **15-voxel padding** used by M4;
7. preserve voxel spacing;
8. rebuild the cropped SimpleITK image with origin `(0, 0, 0)` and identity direction before synthetic deformation, matching the coordinate convention used by the TrueMargin array-based registrar.

No intensity, scanner, source, or anatomy-specific tuning is permitted.

## 6. One frozen synthetic deformation per anatomy

M6 uses exactly one synthetic known-deformation realization per anatomy to retain a two-level hierarchy:

```text
anatomy -> sampled ROI locations
```

Do not add deformation replicates after observing calibration or evaluation behavior.

### 6.1 Deterministic random streams

Random streams are role-independent and patient-identity based.

For stream name `stream` and `patient_id`:

```text
digest = SHA256("truemargin-m6-v1|" + stream + "|" + patient_id)
seed = unsigned big-endian integer represented by digest[0:8]
```

Use NumPy `default_rng(seed)`.

Freeze distinct stream names:

- `deformation`
- `noise`
- `points`

The same patient receives the same synthetic geometry regardless of calibration/evaluation role.

### 6.2 Raw deformation

Retain the M4 generator:

- random 3-D B-spline transform;
- deformation mesh size `4`;
- independent Gaussian coefficients;
- coefficient mean `0.0`;
- coefficient standard deviation `4.0`.

Generate the raw coefficient vector once. Never redraw an inconvenient case.

### 6.3 Deterministic topology backtracking

Apply the M4 Amendment-2 scale sequence to every anatomy:

```text
1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50
```

Choose the first/largest scale for which:

- transform parameters are finite;
- displacement field is finite;
- evaluated Jacobian determinant is finite everywhere; and
- the minimum evaluated-grid Jacobian determinant is strictly greater than `0.0`.

If no scale passes, the deformation-only preflight fails. Do not extend the scale grid, redraw coefficients, replace the anatomy, or inspect estimator outcomes to repair it.

The positive evaluated-grid Jacobian criterion is not a proof of continuous-domain diffeomorphism.

## 7. Synthetic image and fixed-domain ROI construction

For each anatomy:

1. call the normalized cropped real T2 image `moving_source`;
2. construct topology-safe `T_known`;
3. generate

```text
fixed_synth = Resample(
    moving_source,
    reference=moving_source,
    transform=T_known,
)
```

with linear interpolation and zero default fill;
4. use `T_known` as the fixed-to-moving known map;
5. compute the intensity standard deviation from the original moving-source array once;
6. divide both arrays by that same standard deviation;
7. add independent Gaussian noise with standard deviation `0.03` to `fixed_synth` only using the frozen `noise` stream.

True displacement at fixed-domain point `x` is:

```text
u_true(x) = T_known(x) - x
```

No numerical B-spline inversion is used.

Warp the source prostate ROI into the synthetic fixed domain using `T_known` and nearest-neighbour interpolation, exactly matching the M4 fixed-domain ROI convention.

## 8. Frozen spatial sampling

For every anatomy:

1. candidate voxels satisfy `fixed_roi > 0`;
2. candidate voxels must also satisfy the same **8-voxel boundary margin** used in M4;
3. require at least 50 eligible candidates;
4. sample exactly **50 unique candidates uniformly without replacement** using the frozen `points` stream;
5. require every transformed sampled point `T_known(x)` to remain inside the moving-source physical domain.

These 50 points are frozen by the deformation preflight before any estimator registration.

No point may be removed because sigma is small, known error is large, ICE is invalid, or the eventual interval is inconvenient.

## 9. Deformation-only preflight

The next authorized scientific operation after this protocol freeze is a geometry-only synthetic-deformation preflight across **all 60** M6 training anatomies.

It may compute and record:

- source/input identity;
- seeds;
- raw and selected topology scale;
- displacement/Jacobian geometry;
- fixed-domain ROI size;
- the 50 sampled point coordinates;
- transformed-point containment;
- realized true-displacement summaries.

It must not run:

- any of the nine forward registration members;
- any reverse registration;
- sigma;
- ICE;
- known registration error from an estimated field;
- calibration scores or thresholds.

Result-bearing M6 remains unauthorized until the complete 60-anatomy preflight is reviewed and pinned by a separate calibration-run request.

## 10. Frozen forward estimator and error target

For each result-bearing anatomy, retain the exact M4 estimator:

```text
Mattes-MI bins:             32, 50, 64
LBFGSB gradient tolerance:  1e-4, 1e-5, 1e-6
Cartesian members:          9
B-spline mesh size:         3
maximum iterations:         15
center_first:               False
```

All nine forward members must be valid. Do not summarize a survivor ensemble.

Let the nine-member forward ensemble mean be `u_fwd_mean` and the frozen scalar ensemble spread be `sigma_mm`.

At each frozen fixed-domain ROI point:

```text
known_error_mm = ||u_fwd_mean(x) - u_true(x)||_2
```

The numerical calibration target is this nonnegative local error magnitude in millimetres.

## 11. Secondary calibrated comparator: ICE

For every forward-complete anatomy, run the same nine configurations with image roles reversed, preserving the M4 comparator semantics.

Construct the reverse ensemble mean `u_rev_mean`. At frozen point `x`:

```text
y = x + u_fwd_mean(x)
x_cycle = y + u_rev_mean(y)
ICE_mm(x) = ||x_cycle - x||_2
```

Use linear physical-coordinate interpolation of the reverse ensemble mean.

No reverse hyperparameter may be added, removed, or tuned.

ICE is secondary. A reverse failure does not invalidate the primary sigma result, but it is preserved as an ICE method failure.

A formal ICE HCP coverage result for a source is assessable only if all predeclared calibration and evaluation anatomies required for that source produce valid ICE at all 50 frozen points. Otherwise report the ICE failure rate and any complete-case coverage only as descriptive, with no distribution-free ICE coverage claim.

## 12. Nonconformity scores

For method signal `S_mm` in `{sigma_mm, ICE_mm}`:

```text
score = known_error_mm / S_mm
```

with exact zero handling:

```text
if S_mm > 0:
    score = known_error_mm / S_mm
elif S_mm == 0 and known_error_mm == 0:
    score = 0
elif S_mm == 0 and known_error_mm > 0:
    score = +infinity
```

Negative or non-finite finite-valued signals are method-invalid and must be reported.

Do not epsilon-floor, clip, winsorize, log-transform, discard, or abstain on zero/near-zero signals after outcomes.

M6 v1 has **no primary abstention rule**.

## 13. HCP threshold construction

Fit thresholds separately for each source, method, and nominal level.

For one source with `K = 15` calibration anatomies and anatomy `k` containing `n_k = 50` scores `s_ki`, form the weighted empirical measure:

```text
mu =
    (1 / (K + 1)) * delta_(+infinity)
    + sum_k [
        (1 / (K + 1)) * (1 / n_k) * sum_i delta_(s_ki)
      ]
```

Each anatomy therefore has equal total mass `1 / (K + 1)` regardless of its number of spatial samples.

For miscoverage `alpha`, define:

```text
q_alpha = lower (1 - alpha) quantile of mu
radius_mm(x) = q_alpha * S_mm(x)
```

Coverage at an evaluation point is:

```text
known_error_mm(x) <= radius_mm(x)
```

When `q_alpha = +infinity`, the interval is recorded as infinite rather than replaced by the largest finite score.

### 13.1 Frozen nominal levels

- primary: `90%` (`alpha = 0.10`);
- secondary descriptive: `80%` (`alpha = 0.20`);
- finite-sample sentinel: `95%` (`alpha = 0.05`).

With `K = 15`, the HCP `+infinity` atom has mass `1/16 = 0.0625`. Therefore the exact source-specific 95% HCP threshold is prospectively expected to be `+infinity`. This is a finite-sample limitation, not a failure to be tuned away.

Do not pool the two sources merely to obtain a finite 95% radius.

## 14. Calibration/evaluation execution separation

### Phase A — calibration

Only the 30 frozen calibration anatomies may run.

Planned registrations:

```text
30 anatomies x 9 forward members = 270 forward registrations
30 anatomies x 9 reverse members = 270 reverse registrations
```

Fit the source-specific sigma thresholds and, if ICE is fully valid, source-specific ICE thresholds.

The calibration artifact must pin:

- all anatomy identities;
- all deformation/point seeds and preflight hashes;
- all method validity outcomes;
- all score hashes;
- all `q_alpha` values;
- radius-efficiency summaries;
- zero/infinite-score behavior.

Evaluation anatomies must not be run in this phase.

A separate committed evaluation authorization must seal the reviewed calibration artifact and exact thresholds before any evaluation registration.

### Phase B — confirmatory evaluation

Only after the calibration artifact is sealed may the 30 frozen evaluation anatomies run.

Planned registrations are another 270 forward + 270 reverse.

No threshold, split, ROI rule, deformation rule, score rule, or failure rule may change after Phase A.

## 15. Evaluation outputs

For each method/source/nominal level, report:

- coverage at each of the 15 evaluation anatomies;
- equal-anatomy mean coverage within source;
- all 15 per-anatomy coverage values;
- overall balanced mean across the 30 evaluation anatomies;
- per-anatomy median radius in millimetres;
- median and interquartile range of the per-anatomy median radii;
- fraction of zero, near-zero, and infinite signals/scores/radii as applicable;
- all method failures;
- uncalibrated descriptive reference `radius_mm = S_mm`;
- source/acquisition composition.

The primary HCP claim is tied to the 90% source-specific construction.

Per-anatomy coverage distributions are empirical diagnostics. They are not guaranteed to exceed 90% anatomy by anatomy.

Do not use a pooled count of 1,500 evaluation points as if they were 1,500 independent trials.

### 15.1 No post-hoc acceptance tolerance

There is no post-hoc pass/fail tolerance chosen from evaluation coverage.

Report:

```text
coverage_gap = empirical_equal_anatomy_coverage - nominal_coverage
```

continuously for each source and method.

If held-out empirical behavior materially conflicts with the nominal HCP interpretation, narrow the claim and investigate assumptions in M7 or future work. Do not retune M6.

## 16. Failure discipline

### Primary sigma

A source-specific primary calibration/evaluation claim requires all 15 predeclared calibration anatomies and all 15 predeclared evaluation anatomies for that source to be operationally complete under the frozen nine-member estimator and 50-point sampling rule.

A failed primary anatomy is not replaced or silently excluded. Preserve the failure and mark the corresponding source-specific confirmatory calibration claim unsupported/incomplete.

### ICE

ICE follows the stricter secondary-comparator validity rule in Section 11. ICE failure never changes the primary sigma cohort or threshold.

### Infrastructure

A network/runner/storage failure may be retried only with the same source-pinned request and scientific inputs.

Scientific failures are not infrastructure failures.

## 17. Interpretation rules

M6 can support a bounded statement about numerical error radii under the frozen synthetic known-deformation and hierarchical-sampling design.

It cannot establish:

- clinical safety;
- calibration on real unknown correspondence;
- arbitrary-voxel or whole-volume coverage;
- superiority over ICE merely from narrower intervals;
- independence/generalization to the M7 leaderboard/test reserve;
- universal registration-uncertainty calibration.

If sigma HCP is very wide or infinite, preserve that result. Strong M4 rank informativeness and weak M6 numerical efficiency can both be true.

If ICE calibrates better than sigma, preserve that result. M6 is not designed to force a TrueMargin win.

## 18. Frozen next-step authorization boundary

After this protocol is merged and CI-reviewed, only the **60-anatomy deformation-only preflight** is authorized.

The following remain unauthorized until separate, source-pinned requests:

- forward estimator registration;
- reverse/ICE registration;
- HCP fitting;
- calibration-threshold publication as a result;
- evaluation registration;
- evaluation coverage calculation.

`M6_CALIBRATION_PROTOCOL=FROZEN_PRE_RESULT`

`M6_RESULT_BEARING_REGISTRATION_AUTHORIZED=NO`

`M6_DEFORMATION_ONLY_PREFLIGHT_AUTHORIZED=YES`
