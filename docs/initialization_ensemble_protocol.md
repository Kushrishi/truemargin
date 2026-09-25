# Prospective B-spline initialization-ensemble protocol

**Status:** frozen before implementation or initialization-ensemble results  
**Protocol branch:** `design-initialization-ensemble`  
**Parent scientific baseline:** `main` at `96dfa7c3567b51d037f6b7811e7ab717e3d7602b`  
**Scope:** evaluate whether sensitivity to small, physically scaled perturbations of the initial B-spline coefficients provides a stable and non-inert registration-uncertainty signal under the convergence-validated mesh-3 regime.

## 1. Why this protocol exists

The corrected scale-aware input-intensity perturbation ensemble failed its prospectively frozen Gate A: no nonzero perturbation strength satisfied the predeclared promotion rule. That result was recorded without widening or tuning the perturbation grid after seeing results.

A separate prospective registration-convergence study then established that the existing mesh-3, 15-iteration regime is eligible under its frozen field-stability gate in 4/5 frozen patients, with the 100-iteration reference assessable in 5/5 patients. The selected downstream sensitivity regime therefore remains:

- B-spline mesh size: `3`
- maximum LBFGSB iterations: `15`

The next question is whether a different, literature-supported source of registration variability provides a useful uncertainty signal without changing the image intensities or the nominal registration objective.

This protocol is written before implementing the new mechanism and before observing any initialization-ensemble result.

## 2. Prospective sequencing amendment

The earlier frozen ensemble-baseline protocol deferred transform/initialization perturbation because the repository did not then have a physically anchored distribution for initial B-spline coefficients. It identified a registration-hyperparameter ensemble as the preferred literature-aligned comparator after the convergence gate.

That historical protocol is preserved unchanged.

Before any initialization-ensemble result was generated, a targeted literature review identified a directly matching classical-registration construction:

- Sokooti et al., MICCAI 2016, DOI `10.1007/978-3-319-46726-9_13`, generated multiple registrations from randomly perturbed B-spline initializations and used variation in the final transformations as a registration-precision/uncertainty feature.
- Sokooti et al., Medical Image Analysis 2019, DOI `10.1016/j.media.2019.05.005`, extended that work and used independent uniformly distributed offsets in `[-2, 2] mm` on B-spline coefficients. Their interpretation is that sensitivity to the initial state can expose semi-flat or multi-minimum regions of the registration objective.

This resolves the earlier protocol's main reason for deferring initialization perturbation: there is now a published, physically expressed perturbation construction that maps directly onto the current B-spline model.

Initialization perturbation is therefore moved ahead of the broader hyperparameter ensemble for the following prospective reasons:

1. it keeps the convergence-validated `mesh=3`, `max_iterations=15` regime fixed;
2. it does not require introducing new regularization terms, step-size controls, or other registration hyperparameters that are not currently part of TrueMargin's baseline;
3. it isolates one interpretable source of uncertainty: sensitivity to the optimization starting point;
4. it directly tests local-minimum / basin sensitivity suggested by the non-monotonic stability behavior observed in the convergence study; and
5. it is a distinct new estimator, not a post-hoc repair of the failed intensity-perturbation Gate A.

The hyperparameter ensemble remains planned as a later independent comparator. No hyperparameter-ensemble result has been observed or used to justify this sequencing change.

## 3. Research question

Primary question:

> Under the convergence-validated mesh-3 registration regime, does variation in the final deformation field induced by small random perturbations of the initial B-spline coefficients produce a stable, non-inert uncertainty signal that is worth evaluating for calibration and pointwise informativeness?

Secondary scientific question, evaluated only after the perturbation strength and ensemble size are frozen:

> Does initialization sensitivity rank locations with larger real-data proxy error or known synthetic registration error as more uncertain, or can the optimizer be consistently confident around an incorrect solution?

The experiment is allowed to show that initialization sensitivity is uninformative.

## 4. Ground-truth language and scope

### 4.1 Real prostate data

The real-data study does **not** have independently verified pointwise T2-to-DCE registration ground truth.

Real-data error is therefore always described as:

> error under the zero-displacement proxy/reference assumption

and never as verified registration ground truth.

Proxy-error quantities are reported descriptively and are **not used to choose the initialization perturbation strength or ensemble size**.

### 4.2 Synthetic known-deformation work

Synthetic known-deformation experiments provide known registration error and remain the appropriate place to test error association against actual known deformation.

The five-patient real-data sensitivity gate below is only a mechanism-selection and stability study. It is not independent clinical validation.

## 5. Frozen real-data sensitivity cohort

Use exactly the same five patients used in the prior prospective Gate A and convergence studies:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

Use the already frozen series identities for those patients.

Do not replace a patient because its result is inconvenient.

## 6. Frozen registration regime

Hold the nominal registration configuration fixed:

- B-spline mesh size: `3`
- maximum LBFGSB iterations: `15`
- `center_first=False`
- Mattes mutual information histogram bins: `50`
- LBFGSB gradient convergence tolerance: `1e-5`
- linear interpolation
- true physical voxel spacing propagated from the source data
- deterministic middle DCE phase
- existing HECaP bounding-box crop with 15-voxel padding
- existing deterministic HECaP-derived evaluation locations, maximum 75 per patient
- zero-displacement real-data proxy/reference assumption unchanged

Do not vary mesh size, iteration budget, metric bins, interpolation, centering strategy, DCE phase, crop, or landmark selection in this experiment.

The purpose is to isolate initialization sensitivity.

## 7. Initialization perturbation definition

### 7.1 Where the perturbation is applied

Construct the usual zero-initialized B-spline transform with `BSplineTransformInitializer`.

Before `reg.Execute(...)`, replace the initial coefficient vector with a perturbed coefficient vector.

For half-range `delta_mm` and coefficient index `j`:

```text
z_j ~ Uniform(-1, 1)
initial_parameter_j = delta_mm * z_j
```

All B-spline coefficients are perturbed independently.

The perturbation is applied to the **initial transform only**. The optimizer then runs normally using the unchanged registration objective and settings.

Do not add perturbations to the final fitted transformation.

Do not perturb the image intensities.

### 7.2 Interpretation

This mechanism is called an:

> **initialization-sensitivity ensemble**

It measures sensitivity of the fitted deformation to small changes in the optimization starting point.

It is **not** described as:

- a Bayesian posterior;
- scanner-noise uncertainty;
- biological variability;
- calibrated probability of error; or
- verified registration-error uncertainty.

### 7.3 Physical scale

The perturbation half-range is expressed in millimetres in the transform's physical coordinate system.

The largest predeclared value, `2.0 mm`, is anchored to the published Sokooti initialization construction, which used independent uniform B-spline coefficient offsets in `[-2, 2] mm`.

Smaller strengths are included prospectively to determine whether a lower perturbation is already distinguishable from the zero-perturbation repeatability floor.

## 8. Frozen perturbation-strength grid

Evaluate all strengths below before applying the selection rule:

1. `delta_mm = 0.0` — empirical optimizer/runtime repeatability floor
2. `delta_mm = 0.5`
3. `delta_mm = 1.0`
4. `delta_mm = 2.0` — published-range anchor

Use `n = 5` registrations per patient × strength during this sensitivity stage.

Total planned registrations:

```text
5 patients × 4 strengths × 5 members = 100 registrations
```

Do not add `0.25`, `1.5`, values above `2.0`, or any other intermediate values after seeing results.

If none of the three nonzero strengths passes the frozen gate, stop this mechanism at the strength gate.

## 9. Frozen RNG and nesting rule

Use NumPy's modern generator machinery with base seed `0`.

The random direction vector for a patient/member must be independent of perturbation strength so that strengths differ only by scale.

A reproducible implementation is:

```text
SeedSequence([0, patient_index, member_index])
z = Uniform(-1, 1, size=n_parameters)
initial_parameters(delta) = delta * z
```

Consequences:

- the same patient/member uses the same coefficient-space direction at `0.5`, `1.0`, and `2.0 mm`;
- the first five members remain identical if the later ensemble-size study expands to 10 or 20 members; and
- checkpoint/resume order cannot change the perturbations.

Do not use wall-clock seeds.

## 10. Member validity and failure rules

Each registration member is failed/unstable if any of the following occurs:

- registration raises an exception;
- the returned displacement contains non-finite values;
- the returned displacement has the wrong shape;
- mean displacement magnitude exceeds the physical diagonal of the registered crop.

These are operational validity rules, not accuracy criteria.

For the strength-sensitivity stage, if any of the five members fails for a patient × strength cell:

- mark the cell unstable/incomplete;
- retain the member-level failure reasons;
- do not calculate a clean uncertainty summary from survivors only; and
- count the cell as incomplete for the promotion gate.

Instability is itself a result.

## 11. Uncertainty construction

For a complete ensemble, compute the mean displacement field and the spread of member displacement fields using the same scalar RMS convention already used by the existing ensemble/calibration pipeline.

The scalar sigma field must remain compatible with the repository's isotropic chi-square calibration model.

Do not change the scalarization formula specifically for this mechanism after seeing results.

For real-data pointwise evaluation, the corresponding ensemble-mean displacement field is the point estimate whose proxy error is summarized.

Also retain the unperturbed nominal registration as a descriptive reference.

## 12. Frozen strength-promotion gate

The perturbation-strength gate chooses a **mechanism operating scale**, not the scale with the best scientific result.

The `delta_mm=0` repeatability-floor reference must first have a complete five-member cell in at least 4/5 patients. If fewer than four zero-perturbation cells are complete, record the strength gate as not assessable and stop without selecting a nonzero strength.

### 12.1 Per-patient non-inertness criterion

For a patient with complete `delta_mm=0` and candidate cells, define:

```text
floor_p = median_sigma(delta=0)
resolution_floor_p = 0.25 * min(spacing_xyz_p)
required_signal_p = max(3 * floor_p, resolution_floor_p)
```

A nonzero strength is non-inert for patient `p` if:

```text
median_sigma(delta) >= required_signal_p
```

The resolution-linked floor prevents tiny floating-point/numerical differences from being promoted merely because the `delta=0` repeatability floor is effectively zero.

### 12.2 Strength eligibility

A nonzero `delta_mm` is eligible only if:

1. at least 4/5 patients have complete five-member cells for both `delta=0` and the candidate strength; and
2. the per-patient non-inertness criterion is satisfied in at least four of those shared complete patients.

Choose the **smallest** eligible nonzero strength in ascending order:

```text
0.5 -> 1.0 -> 2.0 mm
```

Do not use any of the following to select the strength:

- proxy-error median/mean/p90;
- Spearman correlation with error;
- Pearson correlation with error;
- quartile separation;
- blind-spot rate;
- calibration error;
- coverage;
- conformal results;
- sharpness after recalibration; or
- whether the central TrueMargin thesis appears stronger or weaker.

### 12.3 No eligible strength

If no nonzero strength is eligible:

- record `SELECTED_INITIALIZATION_DELTA_MM=None`;
- stop this mechanism;
- do not widen the range beyond `2.0 mm`;
- do not add intermediate strengths post hoc; and
- do not proceed to ensemble-size tuning for this mechanism.

## 13. Frozen descriptive metrics during strength sensitivity

These metrics are recorded but are not used to select `delta_mm`.

### 13.1 Perturbation efficacy

For each patient × strength:

- valid/failed member count;
- member failure reasons;
- raw sigma median and IQR;
- near-zero sigma fraction;
- sigma coefficient of variation;
- crop physical diagonal;
- physical spacing.

### 13.2 Real-data proxy error

For each patient × strength, under the zero-displacement proxy/reference assumption:

- median error;
- mean error;
- p90 error.

These are descriptive only.

### 13.3 Pointwise informativeness

Record within-patient:

- Spearman rank correlation between raw sigma and proxy error — primary association statistic;
- Pearson correlation — secondary;
- top-vs-bottom sigma quartile error difference;
- high-error / low-sigma blind-spot rate.

Do not pool landmarks across patients for naive inferential testing.

## 14. Frozen ensemble-size study

Run this stage only if a nonzero initialization strength is selected.

At the selected `delta_mm`, evaluate nested:

- `n = 5`
- `n = 10`
- `n = 20`

Because the RNG is member-index based, the first 5 members of the 10- and 20-member ensembles must be identical to the original five, and the first 10 of the 20-member ensemble must match the 10-member run.

Use `n=20` as the size-stability reference.

A patient × size cell is valid only if all members required for that nested size are valid under the member rules above. Do not compute a clean size-comparison sigma vector from survivor-only members.

The `n=20` reference must have valid complete cells in at least 4/5 patients. If fewer than four `n=20` cells are valid, record `SELECTED_ENSEMBLE_SIZE=None` and stop this mechanism because the size-stability reference is not assessable.

For each candidate `n` in `{5, 10}`, evaluate only patients with valid complete cells for both that candidate and `n=20`. At least four shared valid patients are required for the candidate to be eligible.

For each shared valid patient, compare sigma values at the frozen evaluation locations. A candidate size passes for a patient only if both are true:

1. Spearman agreement between `sigma_n` and `sigma_20` is at least `0.90`; and
2. median sigma differs from the `n=20` median by no more than `10%`.

If Spearman agreement is undefined because either sigma vector is constant or otherwise degenerate, that patient does not pass the candidate-size criterion.

Select the smallest candidate size with at least four shared valid patients and at least four patient-level passes.

If neither 5 nor 10 is eligible but `n=20` is valid in at least 4/5 patients, select 20.

Do not use error association, calibration, or blind-spot metrics to select ensemble size.

## 15. Calibration and informativeness after mechanism freeze

Only after both perturbation strength and ensemble size are frozen should the mechanism proceed to broader evaluation.

Keep the following dimensions separate:

### Calibration

- raw calibration/reliability summaries;
- patient-level split calibration;
- LOPO recalibration where feasible;
- marginal 90% coverage;
- conformal coverage where applicable.

### Sharpness

- raw sigma distribution;
- post-calibration uncertainty radius median/IQR;
- 90% radius summaries.

### Informativeness

- within-patient Spearman;
- within-patient Pearson;
- high-vs-low uncertainty error separation;
- blind-spot frequency;
- known-error association in synthetic experiments.

Good calibration does not establish pointwise informativeness.

## 16. Implementation constraints

The implementation PR must remain narrowly scoped.

Preferred design:

1. add an optional initial B-spline parameter vector or equivalent initialization hook to the baseline registration path;
2. preserve the current zero-initialization behavior exactly when the new argument is absent;
3. implement deterministic coefficient perturbation in a dedicated small helper rather than embedding RNG logic throughout registration code;
4. reuse existing displacement validation and ensemble scalarization where possible;
5. add checkpoint/provenance fields for `delta_mm`, seed scheme, patient/member identity, and protocol hash; and
6. leave curvature behavior unchanged.

Required tests should include at least:

- existing baseline output path unchanged when no initialization perturbation is supplied;
- `delta_mm=0` produces a zero coefficient offset;
- sampled offsets remain within `[-delta_mm, +delta_mm]`;
- deterministic reruns reproduce identical coefficient vectors;
- the same patient/member direction scales consistently across perturbation strengths;
- member nesting is preserved for later `n=5/10/20` studies; and
- malformed initialization vectors fail loudly.

Do not refactor unrelated registration code in the implementation PR.

## 17. What is not allowed after results are visible

Do not:

- alter the three nonzero perturbation strengths;
- change the five-patient sensitivity cohort;
- change the member count for the strength gate;
- replace the uniform distribution with Gaussian noise because one looks better;
- change the non-inertness threshold;
- add a proxy-error performance criterion after seeing results;
- choose the perturbation strength from correlation/calibration results;
- remove difficult patients;
- change `mesh=3` or `max_iterations=15` within this mechanism;
- reinterpret the real-data proxy as verified ground truth; or
- describe the ensemble spread as a posterior probability distribution.

A scientifically necessary protocol amendment must be dated, explicit about which results were already known, and committed before generating results under the amended design.

## 18. Possible outcomes

### Outcome A — a nonzero strength is promoted

Proceed to the frozen ensemble-size study, then broader real/synthetic evaluation after size selection.

### Outcome B — all strengths remain effectively inert

Record the mechanism-specific negative result and stop. Do not widen the perturbation range post hoc.

### Outcome C — perturbations frequently destabilize registration

Record the instability as the result. Do not estimate clean uncertainty from survivor-only members.

### Outcome D — uncertainty is stable but poorly associated with error

That is a valid scientific result and directly informs TrueMargin's calibration-versus-informativeness question.

### Outcome E — uncertainty is informative

That is also a valid result. TrueMargin does not require every uncertainty estimator to fail; a useful contrast between informative and uninformative mechanisms would strengthen the broader evaluation framework.

## 19. Relationship to later hyperparameter ensemble

This protocol does not cancel the previously planned registration-hyperparameter comparator.

A later protocol should separately define perturbations of reasonable registration settings and must address convergence comparability when changing transformation-model capacity or optimizer behavior.

Initialization sensitivity and hyperparameter sensitivity represent different uncertainty sources and should not be combined into one ensemble unless a future prospective protocol explicitly defines such a mixture.

## 20. Stop/go summary

The next implementation is allowed only after this protocol is merged.

The implementation must then run the frozen 100-registration strength sensitivity study exactly as specified.

The first scientific decision after that run is only:

```text
SELECTED_INITIALIZATION_DELTA_MM = 0.5, 1.0, 2.0, or None
```

No pointwise error-association or calibration result is allowed to alter that selection.
