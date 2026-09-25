# Prospective known-ground-truth comparator protocol

**Status:** FROZEN after successful geometry-only preflight and before any result-bearing known-GT estimator execution  
**Date:** 2026-09-25  
**Base scientific protocol:** `docs/hyperparameter_known_gt_protocol.md`  
**Sampling/inference amendment:** `docs/hyperparameter_known_gt_protocol_amendment_1.md`  
**Topology amendment:** `docs/hyperparameter_known_gt_protocol_amendment_2.md`  
**Reviewed geometry result:** `results/hyperparameter_known_gt_geometry_preflight.json`  
**Observed result-bearing known-GT outcomes at freeze:** none

This protocol freezes how contemporary label-free comparators will be evaluated
against the same known-error substrate as the promoted TrueMargin
hyperparameter ensemble.

It does not change the frozen TrueMargin primary endpoint, estimator,
anatomies, seeds, geometry, landmarks, assessability rule, or primary
anatomy-level sign test.

## 1. Comparator questions

The paper-level comparison separates two questions.

### 1.1 Local error informativeness

At the same 50 frozen fixed-domain ROI landmarks used by the primary
TrueMargin endpoint, does a reference-free local signal rank the known spatial
error of the frozen forward ensemble mean?

### 1.2 Case-level model selection

Can a label-free case-level metric choose a useful registration configuration
from the same frozen nine-member grid without access to known error?

Do not combine these questions into one leaderboard.

## 2. Frozen error target

The pointwise known-error target is unchanged from the base protocol.

For each operationally complete case, let the nine forward registrations
produce the frozen ensemble-mean displacement field `u_fwd_mean`.

At fixed-domain landmark `x`:

```text
u_true(x) = T_known(x) - x
known_error(x) = ||u_fwd_mean(x) - u_true(x)||_2
```

Every direct local comparator below is evaluated against this **same**
`known_error(x)` vector.

Do not switch a comparator to member-specific ground truth merely because that
improves its association.

## 3. Target method

The target method is the already-frozen nine-member hyperparameter-ensemble
scalar sigma.

Its primary evidence label, anatomy aggregation, exact one-sided anatomy sign
test, bootstrap interval, degeneracy rule, and assessability rules remain
governed by the base protocol plus Amendment 1.

Comparator testing must not alter or multiplicity-adjust that pre-existing
primary TrueMargin test.

## 4. Direct local comparator A — inverse consistency error

### 4.1 Reverse registrations

For every case that is operationally complete in the frozen forward
nine-member ensemble, run the **same nine hyperparameter configurations** with
the image roles swapped:

```text
reverse fixed  = moving_source
reverse moving = fixed_synth
```

Use the same mesh size, iteration budget, center-first setting, validity rules,
and member ordering as the frozen forward estimator.

No reverse hyperparameter may be added, removed, or tuned.

The reverse comparator is operationally complete only if all nine reverse
members are valid. A reverse failure invalidates ICE for that case but does not
invalidate or remove an otherwise valid primary TrueMargin case.

### 4.2 Reverse ensemble mean

Construct the reverse nine-member ensemble-mean displacement field on the
reverse fixed grid using the same averaging convention as the forward
ensemble.

Let:

- `u_fwd_mean(x)` be the forward ensemble-mean displacement on the synthetic
  fixed grid;
- `u_rev_mean(y)` be the reverse ensemble-mean displacement on the
  moving-source grid.

At frozen fixed-domain landmark `x`:

```text
y = x + u_fwd_mean(x)
x_cycle = y + u_rev_mean(y)
ICE(x) = ||x_cycle - x||_2
```

Evaluate `u_rev_mean(y)` by linear interpolation in physical coordinates.

If interpolation is impossible or non-finite at any frozen landmark, mark ICE
invalid for that case and retain the exact failure reason.

ICE is expressed in millimetres. Higher values mean greater inconsistency.

## 5. Direct local comparator B — absolute post-registration residual

This is a deliberately simple same-modality baseline.

Use the exact normalized/noisy arrays supplied to the frozen forward
registration and the forward ensemble-mean mapping.

At fixed-domain landmark `x`:

```text
y = x + u_fwd_mean(x)
RESIDUAL(x) = |fixed_input(x) - moving_input(y)|
```

Use linear interpolation for continuous image sampling.

Do not denoise, locally normalize, smooth, window, or tune the residual after
known-GT outcomes are visible.

This baseline is specific to the same-modality synthetic T2 task and must not
be generalized to the historical real T2-to-DCE setting.

## 6. Direct local comparator C — Jacobian deviation

Compute the displacement-field Jacobian determinant `J(x)` of the forward
ensemble-mean displacement field on the frozen fixed grid.

At each frozen landmark:

```text
JACDEV(x) = |J(x) - 1|
```

Use the same evaluated physical/grid convention throughout the study.

Jacobian deviation is a deformation-plausibility signal, not a probabilistic
uncertainty estimate.

If the Jacobian or sampled score is non-finite, mark this comparator invalid for
that case and retain the failure reason.

## 7. Local comparator statistics

For each direct local comparator `m in {ICE, RESIDUAL, JACDEV}` and each
method-valid case:

```text
rho_case_m = Spearman(score_m, known_error)
```

Higher comparator score is always defined to mean more suspected error, so a
positive rho has the same interpretation for all methods.

If the comparator score or known-error vector is rank-degenerate such that
Spearman is undefined, set `rho_case_m = 0` and flag the degeneracy. Do not
drop the case because it weakens the comparator.

### 7.1 Anatomy aggregation

A comparator-specific anatomy is assessable if at least 2 of its 3 frozen
cases are valid for that comparator.

For each assessable anatomy:

```text
rho_anatomy_m = median(rho_case_m over valid cases)
```

For each comparator:

```text
T_m = median(rho_anatomy_m over assessable anatomies)
```

A comparator-level result is assessable only if at least 8 of 10 anatomies are
assessable.

### 7.2 Comparator sign tests

For each assessable direct comparator, use the same exact one-sided anatomy
sign-test construction as Amendment 1:

```text
H0: P(rho_anatomy_m > 0) <= 0.5
H1: P(rho_anatomy_m > 0) > 0.5
```

Anatomy effects equal to zero count as non-positive.

The three comparator p-values form one secondary family and are corrected with
Holm's method at family-wise alpha `0.05`.

These secondary tests do not alter the frozen primary TrueMargin evidence
label.

### 7.3 Paired effect summaries

For every local comparator with at least 8 anatomies jointly assessable with
the target method, compute paired anatomy differences:

```text
delta_anatomy_m = rho_anatomy_target - rho_anatomy_m
```

Report:

- all paired anatomy differences;
- median paired difference;
- 95% percentile bootstrap interval for the median paired difference;
- 10,000 anatomy bootstrap replicates;
- random seed `0`.

Do not add a post-hoc superiority p-value.

## 8. Local blind-spot and enrichment summaries

For each direct local method, including the TrueMargin sigma target, reuse the
frozen case-level known-error quartiles.

For each valid case record:

- median known error in the top score quartile;
- median known error in the bottom score quartile;
- top-minus-bottom median known-error difference;
- blind-spot rate: points simultaneously in the top known-error quartile and
  bottom method-score quartile.

Aggregate cases within anatomy first, then summarize across anatomies.

Do not pool landmarks across patients for formal inference.

## 9. Contrastive Discrepancy — separate case-level axis

Li et al. (Medical Image Analysis 113:104210, 2026) define Contrastive
Discrepancy (CD) as a label-free model-selection metric based on deformation
field disagreement under transformed observations.

The authors' publication page links released code at the snapshot:

```text
anonymous.4open.science/r/dbc-B401
```

CD is **not** inserted into the local 50-landmark uncertainty table unless the
released method itself yields an explicitly local score with documented
semantics. The paper-level protocol treats its primary role as case-level
configuration selection.

### 9.1 Mandatory pre-result feasibility audit

Before any result-bearing known-GT run that includes CD:

1. inspect the released code and paper together;
2. record the exact source snapshot/archive identity available at audit time;
3. record the transformation family and all perturbation parameters;
4. record the aggregation/scoring equation;
5. demonstrate the implementation on toy/non-result-bearing inputs;
6. verify that wrapping the frozen TrueMargin registrar does not change CD's
   published scoring semantics.

If faithful application to the frozen 3-D classical registrar would require
inventing a new perturbation family, training a new model, changing the CD
aggregation, or otherwise producing a new method, record
`CD_FEASIBLE=False` before known-GT estimator outcomes are observed.

If infeasible, do not replace CD with a bespoke analogue after seeing results.

### 9.2 Frozen CD outcome if feasible

For each frozen synthetic case and each of the nine frozen registration
configurations, compute the faithful CD score without access to known error.

Let `E_c` be that configuration's median known landmark error and
`CD_c` its label-free discrepancy.

Record:

```text
rho_CD_case = Spearman(CD_c, E_c across the 9 configurations)
c_CD = argmin_c CD_c
c_oracle = argmin_c E_c
regret_CD = E_(c_CD) - E_(c_oracle)
```

Tie-breaking uses the existing frozen configuration order.

Also record the median known error of the central grid member
`(50 bins, gradient tolerance 1e-5)` as a simple fixed-choice reference.

Aggregate CD case statistics within anatomy before cross-anatomy summaries.

CD results remain case/model-selection evidence and are not relabeled as
pointwise local uncertainty.

## 10. Excluded direct comparators

### 10.1 Transformation-equivariance uncertainty

Do not include as a confirmatory direct comparator in this classical B-spline
study.

The current published/preprint evidence evaluates pretrained deep registration
models. A classical-optimizer adaptation would be a new estimator whose
equivalence to the source method has not been established.

### 10.2 CONReg

Do not include as a direct comparator.

CONReg requires a learned quantile-registration model and conformal calibration
pipeline, changing both the registration model and uncertainty semantics.

### 10.3 Historical curvature signal

Do not include unless a separate pre-result audit freezes a mathematically
complete implementation and provenance before the result-bearing run request.

Absence from the confirmatory suite is preferable to importing an unstable
historical signal.

## 11. Registration budget

The frozen forward TrueMargin primary study remains:

```text
30 cases x 9 forward registrations = 270 registrations
```

ICE adds at most:

```text
30 cases x 9 reverse registrations = 270 registrations
```

Therefore the direct local target + ICE registration budget is at most:

```text
540 registrations
```

Residual and Jacobian-deviation comparators reuse the forward ensemble mean and
add no registration members.

Any additional registrations required by a faithful CD implementation must be
counted and pinned separately in the final result-bearing run request before
execution.

## 12. Failure discipline

Comparator failure never authorizes modification of the frozen target method.

For each method:

- retain exact member/configuration identity;
- retain exact failure reason;
- do not replace failed cases, anatomies, seeds, or hyperparameters;
- do not silently compute a reduced-member ensemble;
- report method-specific assessability.

Infrastructure reruns are permitted only with unchanged scientific
configuration and recorded provenance.

## 13. Multiplicity and claim boundary

The frozen TrueMargin sigma test remains the sole pre-existing primary
hypothesis test.

Comparator sign tests are secondary and Holm-corrected as one family.

Paired target-versus-comparator effects are reported as effect sizes and
bootstrap intervals, not as a post-hoc winner test.

A favorable comparator result cannot be used to retune TrueMargin, and an
unfavorable comparator result cannot be omitted from the paper-level evidence.

## 14. Required implementation preflight

Before a result-bearing authorization is created, tests must pin:

- the forward/reverse transform-direction convention for ICE;
- physical-coordinate interpolation of reverse displacement;
- ICE = zero for an analytic perfectly inverse transform pair;
- residual sampling on a known analytic translation;
- Jacobian deviation on identity and known affine fields;
- comparator degeneracy mapping to rho `0`;
- comparator-specific anatomy assessability;
- Holm correction;
- paired-anatomy bootstrap seed/count;
- exact central-grid configuration identity;
- any CD feasibility decision and source identity.

No known-GT estimator outcome may be inspected while choosing these
implementation details.

## 15. Frozen status

`KNOWN_GT_COMPARATOR_PROTOCOL=FROZEN`

`KNOWN_GT_GEOMETRY_PREFLIGHT_STATUS_AT_FREEZE=30_PASS_0_FAIL`

`KNOWN_GT_RESULT_BEARING_REGISTRATION_RUN_AT_FREEZE=NO`

`KNOWN_GT_ESTIMATOR_OUTCOME_OBSERVED_AT_FREEZE=NO`

`KNOWN_GT_COMPARATOR_OUTCOME_OBSERVED_AT_FREEZE=NO`
