# Prospective registration-hyperparameter ensemble protocol

**Status:** frozen before implementation or hyperparameter-ensemble results  
**Protocol branch:** `design-hyperparameter-ensemble`  
**Parent scientific baseline:** `main` at `b364dedfe4f6bfa97f3ca89f93423ce363b5180b`  
**Scope:** test whether modest variation in existing registration metric/optimizer settings produces a stable, non-inert deformation-field uncertainty signal while preserving the convergence-validated mesh-3, 15-iteration regime.

## 1. Why this protocol exists

TrueMargin has now prospectively tested two classical registration-uncertainty ensemble mechanisms under frozen rules:

1. a scale-aware input-intensity perturbation ensemble; and
2. a B-spline initialization-sensitivity ensemble.

Neither mechanism produced a nonzero operating point that passed its predeclared promotion gate.

A separate registration-convergence experiment established that the current mesh-3, 15-iteration regime is eligible under its frozen field-stability criterion in 4/5 sensitivity patients, with the 100-iteration reference assessable in 5/5 patients.

The next planned independent comparator is therefore a registration-hyperparameter ensemble. This was already identified prospectively in `docs/ensemble_baseline_protocol.md` as a literature-aligned mechanism to revisit after convergence had been characterized.

This protocol is written before adding hyperparameter hooks, before running the new ensemble, and before observing any hyperparameter-ensemble uncertainty result.

## 2. Literature basis and bounded interpretation

Classical deformable-registration uncertainty has been estimated by repeating registration across different but reasonable algorithm settings and treating the spread of resulting deformation vector fields as an uncertainty signal.

Meyer et al. (International Journal of Radiation Oncology, Biology, Physics, 2025; DOI `10.1016/j.ijrobp.2025.04.004`) generated an ensemble of deformation fields by perturbing registration hyperparameters. Their implementation varied parameters from the transformation model, regularization, and optimizer and produced 63 registrations per image pair.

TrueMargin does **not** copy that grid directly because its current B-spline registration implementation is materially different:

- there is no explicit bending-energy regularization term;
- there is no exposed optimizer step-size parameter analogous to the one in that study; and
- only the current mesh-3, 15-iteration regime has been prospectively checked for convergence.

The present experiment therefore uses a deliberately smaller, implementation-native hyperparameter grid around two controls that already exist in the current registration method:

1. Mattes mutual-information histogram resolution; and
2. LBFGSB gradient-convergence tolerance.

SimpleITK exposes `SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)` and `SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, ...)`; these values match TrueMargin's current hard-coded baseline settings.

The mechanism is called a:

> **registration-hyperparameter sensitivity ensemble**

It measures variation in the fitted deformation field induced by modest changes to algorithm settings.

It is **not** described as:

- a Bayesian posterior;
- scanner-noise uncertainty;
- biological variability;
- a calibrated probability of registration error; or
- verified correspondence uncertainty.

## 3. Research question

Primary question:

> Under the convergence-validated mesh-3, 15-iteration registration regime, does modest variation of the Mattes-MI histogram resolution and LBFGSB gradient-convergence tolerance produce a stable, non-inert deformation-field spread across the frozen sensitivity cohort?

Secondary question, evaluated only if this mechanism passes its promotion gate:

> Does the resulting hyperparameter-sensitivity uncertainty contain useful pointwise information about registration error under synthetic known deformation and, descriptively, under the real-data zero-displacement proxy/reference assumption?

The experiment is allowed to show that the hyperparameter ensemble is unstable, inert, or uninformative.

## 4. Ground-truth language and scope

### 4.1 Real prostate data

The real-data study does **not** have independently verified pointwise T2-to-DCE registration ground truth.

Any real-data error quantity is therefore described as:

> error under the zero-displacement proxy/reference assumption

and never as verified registration ground truth.

Proxy-error, calibration, correlation, and blind-spot quantities are descriptive during the mechanism-promotion gate and cannot determine whether the hyperparameter ensemble is promoted.

### 4.2 Synthetic known-deformation work

Known-deformation synthetic experiments remain the appropriate place to test whether uncertainty tracks actual registration error.

Passing the real-data mechanism gate below only establishes that the hyperparameter ensemble is operationally stable and non-inert enough to justify further evaluation.

## 5. Frozen real-data sensitivity cohort

Use exactly the same five patients used in the prior prospective ensemble and convergence studies:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

Use the already frozen T2/DCE series identities and HECaP masks for those patients.

Do not replace a patient because a hyperparameter configuration fails or produces an inconvenient result.

## 6. Frozen nominal registration regime

Hold the following settings fixed for every registration in this experiment unless explicitly listed in the hyperparameter grid:

- B-spline mesh size: `3`
- maximum LBFGSB iterations: `15`
- `center_first=False`
- linear interpolation
- true physical voxel spacing propagated from source data
- deterministic middle DCE phase
- existing HECaP bounding-box crop with 15-voxel padding
- existing deterministic HECaP-derived evaluation locations, maximum 75 per patient
- zero-displacement real-data proxy/reference assumption unchanged

Do **not** vary mesh size or iteration budget in this experiment.

Reason: only the mesh-3 regime has been prospectively checked by the completed convergence study. Varying mesh size or iteration count here would reintroduce model-capacity/under-convergence ambiguity into an experiment intended to isolate hyperparameter sensitivity.

Do not vary centering strategy, interpolation, DCE phase, crop, landmark selection, or metric sampling strategy.

## 7. Frozen hyperparameter grid

### 7.1 Mattes mutual-information histogram bins

Evaluate exactly:

- `32`
- `50` — current TrueMargin / SimpleITK default setting
- `64`

Rationale:

- `50` is the current nominal configuration;
- `32` is a commonly used lower-resolution Mattes-MI histogram setting in medical-registration work; and
- `64` is a modest higher-resolution counterpart that changes metric discretization without changing the similarity metric itself.

Do not add other histogram-bin values after seeing results.

### 7.2 LBFGSB gradient-convergence tolerance

Evaluate exactly:

- `1e-4`
- `1e-5` — current TrueMargin / SimpleITK default setting
- `1e-6`

This is a one-decade sensitivity range on either side of the current nominal tolerance.

The maximum iteration cap remains fixed at `15` for all configurations.

Do not add intermediate or more extreme tolerances after seeing results.

### 7.3 Cartesian ensemble

Use the complete Cartesian product:

```text
3 histogram-bin settings × 3 gradient-tolerance settings = 9 configurations
```

The nominal configuration `(50 bins, 1e-5 tolerance)` is one of the nine ensemble members.

Each configuration is run once per patient for the hyperparameter ensemble.

The configuration order must be deterministic and fixed before execution.

## 8. Empirical repeatability floor

Because repeated registrations under identical settings can show numerical/optimizer variability, measure a separate nominal repeatability floor rather than assuming the nominal registration is deterministic.

For every patient, run exactly five registrations using:

- histogram bins: `50`
- gradient-convergence tolerance: `1e-5`
- mesh size: `3`
- maximum iterations: `15`
- all other frozen nominal settings unchanged

Use the spread of these five nominal registrations as the empirical repeatability-floor sigma field.

The repeatability-floor registrations are separate from the nine-member hyperparameter grid. Do not substitute a single nominal grid member for the five-member floor.

## 9. Planned registration count

Per patient:

```text
5 nominal repeatability-floor registrations
+ 9 hyperparameter-grid registrations
= 14 registrations
```

Across five patients:

```text
5 patients × 14 registrations = 70 registrations
```

Run the full predeclared grid. Do not stop early because one setting appears promising or poor.

## 10. Member validity and failure rules

Apply the existing operational member-validity rules to every registration:

- registration exception;
- non-finite displacement values;
- wrong displacement-field shape;
- mean displacement magnitude exceeding the physical diagonal of the registered crop.

### 10.1 Repeatability-floor cell

If any of the five nominal repeatability-floor registrations fails for a patient:

- mark that patient's floor cell incomplete;
- retain member-level failure reasons; and
- do not calculate a clean floor uncertainty summary from survivors only.

### 10.2 Hyperparameter ensemble cell

A patient's nine-member hyperparameter ensemble is complete only if all nine predeclared configurations are valid.

If any configuration fails:

- mark the patient's hyperparameter ensemble incomplete;
- retain the exact failing configuration and reason;
- do not silently drop failed configurations; and
- do not calculate a clean nine-member uncertainty summary from survivors only.

Instability is itself a result of the hyperparameter-sensitivity mechanism.

## 11. Uncertainty construction

For a complete five-member repeatability-floor cell, compute the mean displacement field and scalar sigma field using the repository's existing ensemble scalarization convention.

For a complete nine-member hyperparameter ensemble, compute the mean displacement field and scalar sigma field using that same convention.

Do not introduce a new anisotropic/PCA uncertainty representation in this experiment. Although the Meyer et al. study used PCA ellipsoids, changing TrueMargin's scalarization at the same time as changing the ensemble mechanism would confound the comparison with the existing calibration pipeline.

The scalar sigma must remain compatible with the repository's existing isotropic chi-square calibration model.

## 12. Frozen promotion gate

This gate decides whether the hyperparameter-sensitivity ensemble is sufficiently stable and non-inert to justify downstream evaluation. It does **not** select the setting that best predicts error.

### 12.1 Floor assessability

The five-member nominal repeatability-floor cell must be complete in at least 4/5 patients.

If fewer than four floor cells are complete:

- record `HYPERPARAMETER_ENSEMBLE_ELIGIBLE=False`;
- record the gate as not assessable; and
- stop without tuning the grid.

### 12.2 Per-patient non-inertness

For a patient with complete floor and hyperparameter cells, define:

```text
floor_p = median_sigma(nominal five-repeat floor)
resolution_floor_p = 0.25 * min(spacing_xyz_p)
required_signal_p = max(3 * floor_p, resolution_floor_p)
```

The hyperparameter ensemble is non-inert for patient `p` if:

```text
median_sigma(hyperparameter grid) >= required_signal_p
```

This mirrors the already frozen initialization-strength logic and prevents a numerically tiny hyperparameter spread from being promoted merely because the nominal repeatability floor is approximately zero.

### 12.3 Global eligibility

The hyperparameter mechanism is eligible only if:

1. at least 4/5 patients have complete nominal repeatability-floor cells;
2. at least 4/5 patients have both complete floor and complete nine-member hyperparameter cells; and
3. the non-inertness criterion is satisfied in at least four of those shared complete patients.

If all conditions pass, record:

`HYPERPARAMETER_ENSEMBLE_ELIGIBLE=True`

Otherwise record:

`HYPERPARAMETER_ENSEMBLE_ELIGIBLE=False`

There is no post-hoc choice among subsets of the 3×3 grid.

Do not delete a configuration because it reduces correlation, increases proxy error, or causes the central TrueMargin thesis to look weaker.

## 13. Metrics excluded from promotion

The following may be recorded descriptively but cannot determine mechanism eligibility:

- real-data proxy-error median/mean/p90;
- Spearman sigma-error correlation;
- Pearson sigma-error correlation;
- quartile error separation;
- blind-spot rate;
- ECE;
- marginal coverage;
- conformal coverage;
- calibration scale factor;
- calibrated uncertainty radius;
- sharpness; and
- whether the resulting evidence supports or weakens the central TrueMargin thesis.

## 14. Frozen descriptive outputs

For each patient, record at minimum:

### Repeatability floor

- complete/failed status;
- member failure reasons;
- raw sigma median and IQR;
- near-zero sigma fraction;
- sigma coefficient of variation.

### Hyperparameter ensemble

- all nine configuration identities;
- per-configuration validity/failure reason;
- raw sigma median and IQR;
- near-zero sigma fraction;
- sigma coefficient of variation;
- crop physical diagonal;
- physical spacing.

### Real-data proxy error

Under the zero-displacement proxy/reference assumption, report descriptively:

- median error;
- mean error;
- p90 error.

### Pointwise informativeness

Report descriptively within patient:

- Spearman rank correlation between raw sigma and proxy error;
- Pearson correlation;
- top-vs-bottom sigma quartile error difference; and
- high-error / low-sigma blind-spot rate.

Do not pool landmarks across patients for naive inferential testing.

## 15. No ensemble-size tuning stage

This mechanism is defined by the complete predeclared 3×3 Cartesian grid.

There is therefore no `n=5/10/20` size-selection stage for this experiment.

Do not retrospectively choose a smaller subset of configurations because it yields a cleaner uncertainty map or stronger error association.

If the full grid is operationally unstable or inert, the mechanism fails its gate.

## 16. Downstream path if the mechanism passes

If `HYPERPARAMETER_ENSEMBLE_ELIGIBLE=True`, freeze the nine-member mechanism exactly as tested and proceed to independent evaluation, including:

1. synthetic known-deformation error association;
2. comparison with curvature uncertainty;
3. calibration vs pointwise informativeness separation;
4. blind-spot behavior;
5. robustness/sensitivity analysis; and
6. later full-cohort real-data evaluation only after the estimator definition remains frozen.

Passing this gate does not establish that the estimator is useful; it only allows that question to be tested.

## 17. Downstream path if the mechanism fails

If `HYPERPARAMETER_ENSEMBLE_ELIGIBLE=False`:

- record the negative result;
- do not widen the bin/tolerance ranges post hoc;
- do not add mesh-size or iteration-budget variation to rescue the mechanism;
- do not select a favorable subset of the nine configurations; and
- move to the next independently specified uncertainty comparator or to the existing curvature line of work.

Potential later comparators remain bootstrap/evidence-resampling and transformation-equivariance approaches, but neither is part of this protocol.

## 18. Implementation constraints

The implementation PR must remain narrowly scoped.

Preferred design:

1. expose optional `metric_bins` and `gradient_convergence_tolerance` arguments on the baseline B-spline registration path;
2. preserve current behavior exactly when those arguments are omitted or left at defaults (`50`, `1e-5`);
3. leave mesh size, iteration cap, centering, spacing, interpolation, and DCE handling unchanged;
4. implement the frozen 3×3 grid in a dedicated sensitivity runner;
5. reuse existing member validation and ensemble scalarization;
6. add strict checkpoint/provenance fields for both hyperparameters and configuration identity; and
7. leave curvature and initialization-sensitivity behavior unchanged.

Required tests should include at least:

- baseline registration defaults remain `50` bins and `1e-5` gradient tolerance;
- explicit nominal arguments reproduce the default code path;
- the exact 3×3 configuration set is generated once each and in deterministic order;
- invalid/failed configurations make a patient hyperparameter cell incomplete;
- no survivor-only summary is promoted;
- floor assessability is enforced;
- non-inertness threshold calculation is pinned;
- global eligibility requires at least four shared complete/non-inert patients; and
- descriptive proxy-error/correlation fields cannot change promotion.

## 19. Stop conditions

Stop and investigate before scientific interpretation if:

- the implementation changes nominal registration behavior at default settings;
- checkpoint provenance cannot prove exact configuration identity;
- the actual run differs from the frozen 3×3 grid;
- a failed configuration is silently omitted from the ensemble;
- the run uses a mesh or iteration budget other than `3` and `15`; or
- promotion criteria are changed after results are visible.

Any protocol amendment after results exist must explicitly state what results were already known and why the amendment is necessary.
