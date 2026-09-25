# Prospective ensemble-baseline repair protocol

**Status:** frozen before implementation or sensitivity results  
**Protocol branch:** `design-ensemble-baseline`  
**Parent scientific baseline:** `main` at `adbf8fe399a31b8335863ead2689a13e8426f8ee`  
**Scope:** repair and falsify the existing registration-ensemble uncertainty baseline without changing the registration objective, cohort, real-data reference assumption, or curvature method.

## 1. Why this protocol exists

TrueMargin's current real-data ensemble uncertainty baseline perturbs the fixed and moving image arrays with independent additive Gaussian noise of absolute standard deviation `0.02`, reruns the same B-spline registration, and uses the spread of the resulting displacement fields as a scalar uncertainty estimate. The real prostate pipeline passes raw/effectively unnormalised T2 and DCE DICOM intensities into that function.

That creates a serious unresolved scale confound: an absolute perturbation of `0.02` may be negligible when image intensities vary on scales of hundreds or thousands. Near-zero ensemble spread could therefore mean either:

1. the registration is genuinely repeatable under a meaningful input perturbation; or
2. the perturbation is effectively inert and the registrations are being asked almost the same question each time.

The synthetic known-ground-truth experiment independently exposed the same units problem: it had to normalise image intensity scale before an absolute `0.02` perturbation became meaningful. That repair was never propagated back to the 15-patient real-data baseline.

This protocol is written **before** changing `ensemble_uncertainty()` and before looking at corrected real-data results. Its purpose is to prevent post-hoc selection of a perturbation magnitude or ensemble size based on whether the historical "repeatability is not correctness" result survives.

## 2. Research question

Primary question:

> After replacing the scale-dependent absolute intensity jitter with a scale-aware perturbation, does ensemble displacement spread contain useful pointwise information about registration error, or can registrations remain mutually consistent while being wrong?

The experiment is explicitly allowed to overturn the historical result.

Possible outcomes are treated symmetrically:

- **Result survives:** corrected perturbations still produce low uncertainty in high-error regions.
- **Result weakens:** corrected perturbations recover some error information but substantial blind spots remain.
- **Result disappears or reverses:** the original blind spot was materially caused by an inert perturbation scale.

None of those outcomes is a failure of the experiment.

## 3. Ground-truth language and scope

### 3.1 Real prostate experiment

The real-data experiment does **not** have independently verified pointwise T2-to-DCE registration ground truth. It uses clinically meaningful HECaP-derived evaluation locations and the existing same-patient/session physical-coordinate-system assumption, under which the correct T2-to-DCE displacement is approximated as zero.

Therefore real-data error in this protocol is always described as:

> error under a zero-displacement proxy/reference assumption

and never as verified registration ground truth.

### 3.2 Synthetic sentinel

A small synthetic known-deformation check will be used only as an implementation and unit-scale sentinel. It does not replace the later planned multi-anatomy known-ground-truth experiment and will not be treated as independent-patient evidence.

## 4. Literature basis

The protocol is informed by the following findings rather than by a requirement that any particular method must win.

### 4.1 Perturbation-based uncertainty is established, but the perturbation must represent a meaningful source of variability

- Hub, Kessler, and Karger (IEEE TMI, 2009; DOI `10.1109/TMI.2009.2021063`) perturbed B-spline coefficients and related local similarity sensitivity to registration error. This supports perturbation/sensitivity analysis in B-spline registration, but it is closer to TrueMargin's local-curvature line of work than to an input-noise rerun ensemble.
- Kybic (IEEE TIP, 2010; DOI `10.1109/TIP.2009.2030955`) used bootstrap resampling of image-derived evidence to estimate registration uncertainty without ground truth. This is a strong precedent for data perturbation, but a faithful 3-D mutual-information bootstrap would be a separate method and is outside the minimal repair.
- The 2023 DIR uncertainty review by Nenoff et al. (Physics in Medicine & Biology; DOI `10.1088/1361-6560/ad0d8a`) identifies algorithm choice and registration parameter settings as important uncertainty sources and stresses geometric validation in physical distance units.
- Meyer et al. (IJROBP, 2025; DOI `10.1016/j.ijrobp.2025.04.004`) construct an ensemble of DVFs from 63 registrations with perturbed hyperparameters, demonstrating that hyperparameter perturbation is a current, literature-aligned way to sample classical DIR variability.

### 4.2 Transformation spread is not automatically registration-error information

- Luo et al., *Misdirected Registration Uncertainty* (arXiv `1704.08121`) show that transformation uncertainty can be a misleading surrogate for correspondence uncertainty.
- Luo et al., *On the Applicability of Registration Uncertainty* (arXiv `1803.05266`) further distinguish transformation uncertainty from downstream label/correspondence uncertainty and show that using registration uncertainty is not automatically beneficial.
- Luo et al., *Are Registration Uncertainty and Error Monotonically Associated?* (MICCAI 2020; DOI `10.1007/978-3-030-59716-0_26`, arXiv `1908.07709`) directly test pointwise monotonic association and find only weak-to-moderate association for their probabilistic registration setting.

These papers reinforce TrueMargin's central evaluation principle: **calibration or a plausible uncertainty mechanism is not sufficient evidence that uncertainty is informative about pointwise error.**

### 4.3 Newer perturbation ideas are relevant but are not the minimal next experiment

Transformation-equivariance methods perturb inputs spatially and test prediction consistency at inference time (e.g. Tian, Hu, and Iglesias, arXiv `2509.23355`). This is promising, but the current work is framed for pretrained registration networks and would introduce a distinct estimator rather than repair the existing classical B-spline ensemble.

## 5. Candidate perturbation strategies considered prospectively

### A. Legacy absolute intensity perturbation

Definition:

```text
fixed'  = fixed  + Normal(0, 0.02)
moving' = moving + Normal(0, 0.02)
```

Decision: **retain only as a historical control.**

Reason: its physical/effective strength depends entirely on arbitrary image intensity units. It is not an acceptable corrected baseline on raw DICOM-scale data.

### B. Scale-aware intensity perturbation

Definition for perturbation fraction `alpha`:

```text
fixed_scale  = std(fixed)
moving_scale = std(moving)
fixed'  = fixed  + Normal(0, alpha * fixed_scale)
moving' = moving + Normal(0, alpha * moving_scale)
```

The fixed and moving images are **not otherwise normalised or rescaled before registration**.

Decision: **selected as the primary corrected baseline.**

Reasons:

1. It changes only the perturbation scale, not the underlying registration inputs or objective.
2. `alpha` is dimensionless and comparable across patients/modalities.
3. Separate fixed/moving scales avoid making DCE noise magnitude depend on T2 intensity units or vice versa.
4. It directly tests the confound discovered in the existing implementation.
5. It is still honestly described as an **input-intensity perturbation sensitivity ensemble**, not as a posterior distribution or a model of scanner noise.

If either image has a non-finite or effectively zero standard deviation, the run must fail loudly rather than silently substituting an arbitrary scale.

### C. Transform/initialisation perturbation

Decision: **not selected for the repair experiment.**

Reason: there is no currently frozen, physically motivated distribution over initial B-spline coefficients/translations in this repo. Introducing one now would add a second arbitrary scale and would not be a minimal repair. Hub-style control-point perturbation is scientifically relevant but conceptually overlaps the separate local-curvature/sensitivity investigation.

### D. Registration-hyperparameter ensemble

Decision: **deferred until after registration-convergence sensitivity.**

Reason: hyperparameter perturbation is well supported in DIR literature, but TrueMargin's current main real-data mode is `fast_dev` (`mesh_size=3`, `max_iterations=15`). Until a later convergence experiment establishes which registration regime is sufficiently converged, varying mesh/iterations would conflate estimator uncertainty with arbitrary under-convergence/model-capacity choices.

After the convergence gate, a hyperparameter ensemble remains the preferred literature-aligned secondary comparator.

### E. Bootstrap resampling

Decision: **deferred.**

Reason: statistically attractive and literature-supported, but a faithful implementation for 3-D Mattes mutual-information B-spline registration is materially more complex than repairing the current baseline and would create a new estimator rather than fix the identified units bug.

### F. Multiple algorithms / deep probabilistic registration / transformation equivariance

Decision: **deferred.**

Reason: useful future comparators, but they expand model class, dependencies, and interpretation before the current classical baseline is trustworthy.

## 6. Frozen perturbation-strength sensitivity study

### 6.1 Real-data subset

Use exactly five patients selected **before corrected results** by sampling five IDs without replacement from the sorted 15-patient cohort using `numpy.random.default_rng(0)`:

- `aaa0054`
- `aaa0059`
- `aaa0061`
- `aaa0063`
- `aaa0066`

This subset is a compute-saving sensitivity cohort only. It is not an independent clinical cohort and is not used for final paper-level inference.

### 6.2 Registration regime

For this sensitivity phase only, retain the existing real-data baseline registration regime so the experiment isolates the perturbation change:

- mode: `fast_dev`
- B-spline mesh size: `3`
- maximum optimiser iterations: `15`
- similarity metric: Mattes mutual information, as implemented now
- true physical voxel spacing passed through
- DCE phase: existing deterministic middle-phase strategy
- crop: existing HECaP bounding box with 15-voxel padding
- landmarks: existing deterministic HECaP-derived locations, maximum 75/patient
- zero-displacement proxy/reference assumption unchanged

The later convergence-sensitivity experiment may invalidate this regime for publication. This protocol does not pre-judge that result.

### 6.3 Perturbation settings

Evaluate all of the following; do not stop early because a preferred result appears:

1. **repeatability floor:** `relative_std`, `alpha = 0.00`
2. **relative 1%:** `relative_std`, `alpha = 0.01`
3. **relative 2%:** `relative_std`, `alpha = 0.02`
4. **relative 5%:** `relative_std`, `alpha = 0.05`
5. **relative 10%:** `relative_std`, `alpha = 0.10`
6. **historical control:** `absolute_intensity`, `jitter = 0.02` raw intensity units

For this stage, use `n = 5` members for every setting, including `alpha=0`, so the zero-perturbation condition measures any solver/runtime repeatability floor rather than assuming the optimiser is perfectly deterministic.

Use one frozen base RNG seed and generate member perturbations deterministically. The implementation must make the first `n` members identical when the same setting is later evaluated at larger ensemble sizes, enabling nested `n=5`, `n=10`, `n=20` comparisons.

### 6.4 What is *not* allowed

After corrected results are visible, do not:

- add intermediate alpha values because they improve correlation;
- drop an alpha because it makes the historical claim weaker;
- change the five-patient subset;
- change landmark sampling;
- change registration mode or DCE phase;
- redefine the primary informativeness metric;
- select alpha by whichever value maximises Pearson/Spearman correlation, calibration, or blind-spot frequency.

A protocol change after results requires an explicit dated amendment explaining why it was necessary and which observations were already known.

## 7. Divergence and failure rules

Each ensemble member is checked independently.

A member is **failed/unstable** if any of the following occurs:

- registration raises an exception;
- returned displacement contains non-finite values;
- returned shape is inconsistent with the reference grid;
- mean displacement magnitude exceeds the physical diagonal of the registered crop.

The physical-diagonal rule mirrors the existing synthetic known-ground-truth divergence safeguard and is meant to catch obviously non-physical runaway registrations, not merely large local errors.

If any member fails for a patient × perturbation setting:

- mark that patient × setting as unstable;
- report the number of failed members;
- do **not** silently remove failed members and calculate an apparently cleaner uncertainty estimate from survivors;
- preserve diagnostics for that setting;
- exclude the setting from clean sigma-vs-error summaries that require a complete ensemble.

Instability is itself a result of the perturbation sensitivity study.

## 8. Frozen evaluation dimensions

The study must keep **calibration**, **sharpness**, and **informativeness** separate.

### 8.1 Perturbation efficacy / non-inertness

For each patient and setting record:

- `std(fixed)` and `std(moving)`;
- actual fixed/moving noise standard deviation;
- perturbation fraction `alpha` or absolute jitter;
- median and IQR of raw ensemble sigma;
- fraction of landmarks with sigma numerically near zero;
- member failure/divergence count.

The `alpha=0` condition defines the empirical repeatability floor.

### 8.2 Registration accuracy under the existing real-data proxy

For each patient and setting record:

- median error in mm;
- mean error in mm;
- 90th-percentile error in mm.

These are errors under the zero-displacement proxy/reference assumption, not independently verified ground-truth errors.

### 8.3 Pointwise informativeness — primary scientific dimension

Primary statistic:

- **Spearman rank correlation** between raw sigma and pointwise error, computed within each patient.

Rationale: the central question is whether larger predicted uncertainty tends to rank larger errors higher, not whether the raw units already follow an exact linear relation.

Secondary statistics:

- Pearson correlation within each patient;
- error difference between the highest-sigma and lowest-sigma quartiles;
- joint blind-spot rate: proportion of points simultaneously in the patient's highest-error quartile and lowest-sigma quartile;
- sigma coefficient of variation / rank spread to detect near-constant uncertainty maps.

Report patient-wise values and descriptive cohort summaries. Do not treat the approximately 375 landmarks in the five-patient subset as independent subjects and do not run naive point-level inferential tests.

The historical absolute-threshold blind-spot diagnostic (`sigma < 0.01` with appreciable error) may be reproduced for continuity, but it is secondary because raw sigma scale changes by construction across perturbation regimes.

### 8.4 Calibration

For each complete setting, evaluate both raw and recalibrated behavior, but **do not use calibration to choose the perturbation strength**.

Use the project's robust median-matched variance scale terminology. Where feasible on the five-patient subset, use leave-one-patient-out fitting so the patient being evaluated does not calibrate itself.

Record:

- scale factor;
- empirical coverage/reliability curve;
- ECE as a descriptive aggregate calibration metric;
- achieved 90% coverage.

Good ECE does not count as evidence of pointwise informativeness.

### 8.5 Sharpness / usefulness

After the same calibration procedure, report:

- median calibrated 90% radius;
- IQR of calibrated 90% radius;
- patient-level distribution of radius.

A method that achieves coverage only by producing huge regions is not automatically useful.

## 9. Perturbation-strength selection rule for the later full-cohort rerun

The final perturbation fraction is **not** chosen by sigma-error correlation, blind-spot frequency, ECE, or which setting best supports the historical hypothesis.

Selection is based only on whether the perturbation is meaningfully non-inert while remaining a stable sensitivity test.

A nonzero `alpha` is eligible if:

1. its patient-level median raw sigma is clearly above the `alpha=0` repeatability floor (target diagnostic: at least 3× the floor in at least 4 of 5 sensitivity patients); and
2. at least 4 of 5 patients have complete, non-divergent five-member ensembles; and
3. the median registration error across the five patients is not more than 25% worse than the `alpha=0` condition.

If multiple alpha values are eligible, select the **smallest eligible nonzero alpha**.

If no alpha is eligible, do not widen the grid ad hoc. Stop at Gate A and reassess whether additive intensity perturbation is a defensible ensemble mechanism at all.

All alpha settings remain reported regardless of which one is selected.

## 10. Ensemble-size sensitivity after alpha is selected

On the same frozen five-patient subset and selected alpha, evaluate nested ensemble sizes:

- `n = 5`
- `n = 10`
- `n = 20`

Generate a single deterministic 20-member sequence and use prefixes for smaller ensembles.

Choose the smallest `n` that, relative to `n=20`, satisfies both of the following in at least 4 of 5 patients:

- Spearman rank agreement between the sigma maps is at least `0.90`;
- median raw sigma differs by no more than `10%`.

Do **not** use sigma-error correlation, ECE, or blind-spot rate to select `n`.

If neither `n=5` nor `n=10` satisfies the stability rule, use `n=20` for the later cohort rerun.

## 11. Synthetic known-ground-truth sentinel

After implementation, but before the full real-cohort rerun, run a small sentinel using the existing synthetic known-deformation setup for cases/seeds `0`, `1`, and `2`.

Purpose:

- verify the new relative-scale implementation behaves sensibly in a setting with known true deformation/error;
- detect another intensity-units mistake before spending compute on 15 real patients;
- compare the new implementation against the existing synthetic code path that previously normalised intensity scale.

This three-case sentinel is descriptive only. It is **not** a replacement for the later multi-anatomy synthetic study, and the three deformations are not treated as three independent patients.

## 12. Gate A: interpretation rule

After perturbation-strength and ensemble-size sensitivity are complete, pause before the 15-patient rerun and classify the evidence into one of three predeclared outcomes.

### A. Historical mechanism survives strongly

Scale-aware perturbations are demonstrably non-inert, yet sigma remains weakly informative or shows persistent high-error/low-uncertainty regions across patients.

Interpretation: stronger evidence that ensemble repeatability can fail to imply correctness under this registration setup.

### B. Historical mechanism survives only partially

Scale-aware perturbation improves sigma-error ranking materially, but blind spots or weak discrimination remain.

Interpretation: narrow the claim. The historical finding was partly a perturbation-scale artifact and partly a genuine limitation of ensemble spread.

### C. Historical mechanism disappears or reverses

Once perturbations are meaningful, ensemble sigma becomes materially informative about error and the former blind spots largely disappear.

Interpretation: explicitly invalidate the old strong blind-spot conclusion. The corrected ensemble becomes the baseline against which curvature and later methods are judged.

No threshold is defined for making a favored category occur; the classification must be justified from the complete patient-wise diagnostics and reported sensitivity plots.

## 13. Implementation requirements for the next branch

The next branch should be named `fix-ensemble-perturbation-scaling` and should make the smallest code change required to implement this protocol.

Expected API direction (exact spelling may change before merge if tests expose a cleaner minimal interface):

```python
ensemble_uncertainty(
    ...,
    perturbation="relative_std",   # or "absolute_intensity"
    perturbation_scale=0.02,
)
```

Requirements:

- legacy absolute-intensity behavior remains reproducible and explicitly named;
- corrected relative-std behavior uses each image's own standard deviation;
- raw registration images are not normalised as part of this repair;
- zero/invalid scale fails loudly;
- deterministic member generation supports nested ensemble-size experiments;
- divergence diagnostics are explicit;
- tests verify scale invariance of the **perturbation behavior** under multiplicative intensity rescaling;
- tests verify legacy mode exactly preserves the old additive-noise semantics;
- checkpoint provenance records perturbation strategy and scale so legacy and corrected artifacts cannot be mixed;
- no curvature, calibration, cohort, DCE-phase, manuscript, or documentation redesign is bundled into the implementation branch.

## 14. What this phase will not conclude

Even a successful corrected ensemble study will not establish that:

- Gaussian intensity perturbation is a calibrated physical model of MRI acquisition noise;
- ensemble spread is a Bayesian posterior standard deviation;
- the zero-displacement real-data proxy is verified pointwise ground truth;
- `fast_dev` is a publication-quality converged registration regime;
- aggregate coverage implies useful pointwise uncertainty;
- five sensitivity patients establish population-level clinical validity.

Those questions belong to later convergence, synthetic-ground-truth, and external-validation gates.

## 15. Protocol amendment policy

This document is frozen before corrected sensitivity results.

After any result from `fix-ensemble-perturbation-scaling` or `ensemble-jitter-sensitivity` has been inspected, substantive changes to patient selection, alpha grid, primary metric, divergence rules, or selection criteria require a dated amendment appended to this file. The amendment must state:

1. what changed;
2. why the original rule was inadequate;
3. which results were already visible when the change was proposed; and
4. which prior outputs are invalidated or must be rerun.

Do not silently rewrite the prospective protocol to match observed results.
