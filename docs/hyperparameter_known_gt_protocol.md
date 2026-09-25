# Prospective hyperparameter-ensemble known-ground-truth evaluation protocol

**Status:** frozen before implementation or any hyperparameter-ensemble synthetic known-GT result  
**Protocol branch:** `design-hyperparameter-known-gt-evaluation`  
**Parent scientific baseline:** `main` at `e26c4cc8b8b3a09626e68a760f36e6a99cdfaae2`  
**Scope:** independently test whether the promoted nine-member registration-hyperparameter sensitivity ensemble contains pointwise information about actual registration error under a known synthetic deformation.

## 1. Why this protocol exists

The prospective real-data mechanism gate recorded in `docs/hyperparameter_ensemble_result.md` returned:

`HYPERPARAMETER_ENSEMBLE_ELIGIBLE=True`

The exact nine-member estimator was operationally complete in 5/5 frozen sensitivity patients and non-inert in 4/5. That result promotes the mechanism for evaluation; it does **not** establish that its uncertainty is useful.

The next question is deliberately harder:

> When the true fixed-to-moving deformation is known by construction, does larger hyperparameter-ensemble sigma actually correspond to larger registration error at the same spatial locations?

This protocol freezes that evaluation before the promoted estimator is run on the new synthetic known-deformation cases.

No configuration may be removed, added, reweighted, or selected based on the results of this stage.

## 2. Frozen promoted estimator

The estimator is exactly the mechanism that passed the prior gate:

```text
Mattes-MI bins:             32, 50, 64
LBFGSB gradient tolerance:  1e-4, 1e-5, 1e-6
Cartesian members:          9
B-spline mesh size:         3
maximum iterations:         15
center_first:               False
```

The nine deformation fields are summarized using the same ensemble mean and scalar sigma convention used by the promotion runner.

Do not:

- drop a member because it behaves poorly;
- add another histogram-bin or tolerance setting;
- vary mesh size or iteration count;
- tune the scalarization;
- recalibrate sigma before the primary association test; or
- use downstream known-GT results to redefine the estimator.

## 3. Important correction to the legacy synthetic harness

The existing `scripts/13_synthetic_ground_truth_validation.py` is useful historical machinery, but its transform direction must **not** be copied blindly into this evaluation.

The legacy script constructs a B-spline transform `tx_true`, then calls conceptually:

```text
moving = Resample(fixed, reference=fixed, transform=tx_true)
```

and later compares the registration's returned fixed-to-moving field directly with `tx_true`.

SimpleITK's `ResampleImageFilter` defines its supplied transform as **output/reference -> input-image**. SimpleITK registration's optimized transform maps the virtual/fixed domain toward the moving domain.

Therefore, when the same transform is passed to `Resample` while the original image is treated as the fixed image afterward, the transform direction used for image generation is not automatically the same fixed-to-moving direction returned by registration.

This is a material convention issue, not a cosmetic naming issue.

The present protocol avoids numerical inversion entirely by defining the synthetic pair in the direction SimpleITK actually uses:

1. begin with a real T2 crop called `moving_source`;
2. construct the known B-spline transform `T_known` on the crop domain;
3. generate

```text
fixed_synth = Resample(
    moving_source,
    reference=moving_source,
    transform=T_known,
)
```

4. call registration as

```text
registration(fixed=fixed_synth, moving=moving_source)
```

Under these definitions, `T_known` is intentionally the mapping from the synthetic fixed/reference domain into the moving-source domain, matching the transform direction optimized by `ImageRegistrationMethod`.

The exact true displacement at fixed-domain point `x` is therefore:

```text
u_true(x) = T_known(x) - x
```

No B-spline inverse is needed.

### 3.1 Required convention test

Before the scientific runner is accepted, add a small analytic regression test using a known translation. The test must demonstrate that the synthetic-generation convention and the registration/displacement convention use the same fixed-to-moving sign/direction.

A direction test failure is a stop condition.

### 3.2 Status of legacy synthetic numbers

Previous numbers from `scripts/13_synthetic_ground_truth_validation.py` are historical and must not be used as authoritative evidence for this new estimator until the transform-direction issue is reconciled.

This protocol does not retroactively change those old files or selectively reinterpret their favorable/unfavorable results. The new evaluation is a clean prospective replacement for the promoted hyperparameter estimator.

## 4. Independent anatomy cohort

The five patients used to promote the hyperparameter mechanism were:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

They are excluded from the primary known-GT cohort.

Use **all ten remaining anatomies** from the 15-patient dataset, so there is no held-out-patient cherry-picking:

| Patient | T2 series |
| --- | --- |
| `aaa0044` | `13614` |
| `aaa0051` | `36207` |
| `aaa0053` | `45314` |
| `aaa0060` | `12400` |
| `aaa0064` | `40733` |
| `aaa0069` | `58343` |
| `aaa0071` | `27783` |
| `aaa0072` | `64767` |
| `aaa0086` | `42255` |
| `aaa0087` | `30095` |

These are held out from mechanism promotion, but they come from the same TCIA collection. Claims must therefore be framed as held-out-anatomy validation within this dataset, not external-dataset validation.

Do not replace an anatomy because its registration is difficult or its result is unfavorable.

## 5. Anatomy preparation

For each held-out patient:

1. load the frozen T2 series;
2. load the patient's HECaP mask;
3. require `assert_same_grid(mask, T2)`;
4. make the same deterministic mask-bounding-box crop used by the real-data pipeline with 15-voxel padding;
5. use the T2 crop only as real anatomical texture for the synthetic task; DCE is not used;
6. preserve true voxel spacing;
7. rebuild the cropped SimpleITK image with origin `(0, 0, 0)` and identity direction before creating the synthetic deformation, while retaining voxel spacing.

The origin/direction normalization is deliberate: TrueMargin's numpy-based registration API reconstructs SimpleITK images from arrays and propagates spacing but not the original DICOM origin/direction. The synthetic ground-truth transform must therefore be defined in the same coordinate convention used by the estimator being evaluated.

If any anatomy cannot be prepared under these exact rules, stop before scientific registration results are generated. Do not substitute another anatomy.

## 6. Frozen synthetic deformation design

For each of the ten anatomies, generate exactly three independent deformation/noise cases.

Total synthetic cases:

```text
10 anatomies x 3 deformation replicates = 30 cases
```

### 6.1 Seed schedule

Use fixed anatomy order exactly as listed in Section 4.

For zero-based `anatomy_index` and replicate `r in {0,1,2}`:

```text
case_seed = 1000 * anatomy_index + r
```

Use deterministic offsets from `case_seed` for any separate random streams needed for image noise and landmark sampling. Those offsets must be frozen in the implementation and tested.

### 6.2 Known transform

Use a random 3-D B-spline transform with:

- deformation mesh size: `4`;
- coefficient distribution: independent Gaussian;
- coefficient standard deviation: `4.0`;
- coefficient mean: `0.0`.

The `4.0` value is the existing legacy synthetic harness setting. It is retained rather than tuned against the promoted hyperparameter estimator.

It is a B-spline coefficient scale, not a direct statement that every voxel moves 4 mm.

Record the realized true-displacement distribution for every case.

### 6.3 Image construction

For each case:

1. call the normalized real T2 crop `moving_source`;
2. construct `T_known` using the frozen seed and deformation settings;
3. generate `fixed_synth = Resample(moving_source, reference=moving_source, T_known)` with linear interpolation and zero default fill;
4. convert both images to float arrays;
5. compute the intensity standard deviation from the original moving-source array once;
6. divide both arrays by that same standard deviation;
7. add independent Gaussian intensity noise with standard deviation `0.03` to `fixed_synth` only.

The `0.03` normalized noise scale is carried forward from the existing synthetic harness and is not tuned using the hyperparameter estimator's result.

This is a same-modality synthetic registration task. It tests error informativeness under a known answer; it does not reproduce real T2-to-DCE intensity ambiguity.

## 7. Geometry-only preflight before any estimator result

Before running any of the 270 estimator registrations, generate and validate the geometry for all 30 synthetic cases.

For each case require:

- finite B-spline parameters;
- finite displacement field;
- strictly positive displacement-field Jacobian determinant throughout the evaluated crop grid;
- exactly 50 unique evaluation landmarks can be sampled from the interior region;
- every evaluation landmark is at least 8 voxels from each crop boundary;
- every transformed landmark `T_known(x)` remains inside the moving-source physical domain; and
- finite true displacement at every landmark.

If any predeclared case fails geometry-only validation:

- stop before running the promoted uncertainty estimator;
- record the exact failure;
- do not silently substitute another seed, patient, or deformation;
- any protocol amendment must explicitly state that only geometry was observed and that no hyperparameter-ensemble known-GT result existed yet.

Do not inspect sigma/error association while deciding whether the synthetic geometry is valid.

## 8. Evaluation landmarks

Use exactly **50 unique landmarks per synthetic case**.

Landmarks are sampled uniformly without replacement from interior crop voxels satisfying the 8-voxel boundary margin.

They are not HECaP lesion voxels, because after nonlinear synthetic warping the original lesion mask would require inverse mapping to identify the corresponding fixed-domain lesion location. The purpose of this stage is spatial error informativeness under exact known correspondence, not lesion localization.

Landmark sampling must be deterministic from the frozen case seed schedule.

## 9. Planned registration count

Every synthetic case is evaluated with the complete frozen nine-member estimator:

```text
30 synthetic cases x 9 registrations = 270 registrations
```

There is no repeatability-floor stage and no member-count tuning stage here. The estimator definition has already been frozen by the promotion experiment.

## 10. Registration member validity

Apply the existing member validity rules to every one of the nine registrations in every synthetic case:

- registration exception;
- non-finite displacement;
- wrong displacement-field shape; or
- mean displacement magnitude exceeding the physical diagonal of the crop.

A synthetic case is operationally complete only if **all nine** configurations are valid.

If any member fails:

- mark the case incomplete;
- retain configuration identity and failure reason;
- do not summarize an eight-member or smaller survivor ensemble; and
- do not replace the failed hyperparameter configuration.

Failure is part of the estimator's robustness evidence.

## 11. Known true error

For every operationally complete case:

1. compute the nine-member ensemble mean displacement field `u_mean`;
2. compute the frozen scalar sigma field `sigma`;
3. sample both at the 50 fixed-domain landmarks;
4. query `T_known` at those same fixed-domain physical points;
5. compute

```text
u_true(x) = T_known(x) - x
error(x) = ||u_mean(x) - u_true(x)||_2
```

This error is known by construction and does not use the real-data zero-displacement proxy/reference assumption.

## 12. Primary pointwise-informativeness endpoint

For every operationally complete synthetic case, compute the within-case Spearman rank correlation:

```text
rho_case = Spearman(sigma, known_error)
```

Spearman is primary because the question is whether uncertainty ranks risk correctly; no linear relationship is assumed.

If sigma or known error is constant enough that Spearman is undefined, set `rho_case = 0` for the primary summary and separately flag the case as rank-degenerate. Do not drop a degenerate case from the primary result merely because it weakens association.

Do **not** use a naive correlation after pooling all landmarks from all cases/anatomies as the primary inferential statistic.

A pooled correlation may be shown descriptively only and must be labeled as clustered/non-independent.

## 13. Anatomy-level aggregation

The inferential unit is anatomy, not landmark.

An anatomy is assessable if at least **2 of its 3** predeclared synthetic cases are operationally complete.

For each assessable anatomy define:

```text
rho_anatomy = median(rho_case over complete cases for that anatomy)
```

Primary global effect:

```text
T_observed = median(rho_anatomy over assessable anatomies)
```

The primary evaluation is assessable only if at least **8 of 10 anatomies** are assessable.

If fewer than eight anatomies are assessable:

- record `KNOWN_GT_EVALUATION_ASSESSABLE=False`;
- report operational failures;
- do not replace patients/seeds/configurations; and
- do not tune the estimator.

## 14. Cluster-aware permutation test

If the primary evaluation is assessable, test the null hypothesis that sigma has no positive within-case association with known error.

Use exactly `20,000` permutations with random seed `0`.

For each permutation:

1. within every operationally complete case, independently permute sigma across that case's 50 landmarks while leaving known error fixed;
2. recompute the case Spearman statistic using the same degeneracy rule;
3. recompute each anatomy's median case statistic;
4. recompute the global median anatomy statistic `T_perm`.

Use the one-sided p-value:

```text
p = (1 + count(T_perm >= T_observed)) / (20000 + 1)
```

This preserves case/anatomy structure instead of pretending that hundreds of landmarks are independent patients.

## 15. Primary evidence label

If the evaluation is assessable, record:

`KNOWN_GT_POINTWISE_ASSOCIATION_POSITIVE=True`

only if both:

1. `T_observed > 0`; and
2. the frozen one-sided permutation p-value is `<= 0.05`.

Otherwise record:

`KNOWN_GT_POINTWISE_ASSOCIATION_POSITIVE=False`

This label means evidence of a positive rank association under this synthetic design. It does **not** by itself mean that the uncertainty estimator is clinically useful, well calibrated, or free of important blind spots.

Do not change the p-value threshold or association statistic after results are visible.

## 16. Anatomy-bootstrap interval

Report a 95% percentile bootstrap interval for `T_observed` by resampling assessable anatomies with replacement.

Use exactly:

- 10,000 bootstrap replicates;
- random seed `0`.

This interval is secondary to the frozen permutation test but helps quantify effect-size uncertainty.

## 17. Frozen secondary metrics

For every operationally complete case also record:

- Pearson correlation between sigma and known error;
- median known error;
- mean known error;
- p90 known error;
- median sigma;
- sigma IQR;
- top-vs-bottom sigma-quartile difference in median known error;
- blind-spot rate, defined as points simultaneously in the case's top known-error quartile and bottom sigma quartile;
- realized true-displacement min/median/p90/max; and
- all member validity/failure information.

Aggregate secondary metrics first within anatomy, then across anatomies. Do not perform naive point-level inferential tests.

## 18. Calibration is deliberately not the primary question here

Do **not** fit a variance-calibration scale before the primary known-error association test.

A global scale factor can improve marginal coverage without creating pointwise information. Mixing calibration fitting into the first promoted-estimator known-GT test would blur the exact distinction TrueMargin is designed to study.

Calibration/coverage will be evaluated as a separate frozen stage after the present pointwise-informativeness result, regardless of whether association is strong or weak.

## 19. Interpretation rules

### 19.1 If positive association evidence is found

The allowed conclusion is bounded to:

> The frozen nine-member hyperparameter-sensitivity uncertainty shows positive pointwise rank association with known registration error across the held-out multi-anatomy synthetic evaluation.

Still do not claim:

- calibrated probability;
- clinical validity;
- external-dataset generalization;
- real T2-to-DCE correspondence ground truth; or
- absence of blind spots.

Proceed to separate calibration, blind-spot, robustness, and curvature-comparison stages without changing the estimator.

### 19.2 If positive association evidence is not found

Do not tune the nine-member grid, remove configurations, change scalarization, change deformation seeds, or choose a favorable anatomy subset.

The result is evidence that passing a real-data operational/non-inertness gate did not automatically establish useful pointwise known-error information.

Proceed to the planned calibration-vs-informativeness analysis and other comparators with the negative association result preserved.

## 20. Relationship to prior ensemble failures

The prior input-intensity and initialization ensembles remain separate prospective negative mechanism results.

This known-GT stage must not be used to retrospectively retune those mechanisms.

Likewise, the positive real-data promotion result for the hyperparameter ensemble remains an operational result even if this independent known-GT informativeness test is negative.

That separation is scientifically important:

```text
operational variability != pointwise error information != calibration
```

## 21. Implementation constraints

The implementation PR should remain narrow.

Preferred structure:

1. reuse the frozen hyperparameter configuration definition rather than duplicate a second editable grid;
2. factor only the minimum helper needed to produce the exact nine-member ensemble mean/sigma on arbitrary fixed/moving arrays;
3. add a dedicated synthetic known-GT runner rather than rewriting the historical script in place;
4. add the required translation-direction regression test;
5. add tests pinning all ten held-out anatomies and T2 series IDs;
6. add tests pinning the 30-case seed schedule;
7. add tests for geometry-only stop behavior;
8. add tests that a failed member invalidates the full nine-member case;
9. add tests for rank-degenerate cases mapping to primary rho `0`;
10. add tests for anatomy assessability, global assessability, permutation p-value calculation, and the positive-association label; and
11. add strict provenance covering estimator definition, anatomy, deformation seed, deformation settings, landmark seed, noise seed, and source files.

Do not modify curvature behavior in this PR.

## 22. Stop conditions

Stop before scientific interpretation if:

- the synthetic transform direction is not pinned by an analytic test;
- any geometry-only preflight case fails before estimator execution;
- the actual anatomy list differs from the ten frozen held-out patients;
- the actual seed schedule differs from the frozen 30 cases;
- the promoted estimator differs from the exact nine-member grid;
- a failed member is silently omitted;
- the registration regime differs from mesh `3` / iterations `15` / `center_first=False`;
- known-error calculation uses the zero-displacement real-data proxy;
- pooled landmark correlation is substituted for anatomy-aware inference; or
- the primary statistic, permutation scheme, threshold, or estimator is changed after results are visible.

Any amendment after synthetic geometry or estimator results exist must state exactly what had already been observed.
