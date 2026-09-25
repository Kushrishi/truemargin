# Known-ground-truth protocol amendment 2

**Status:** FROZEN after geometry-only preflight and before any known-GT estimator execution  
**Date:** 2026-09-25  
**Base protocol:** `docs/hyperparameter_known_gt_protocol.md`  
**Prior amendment:** `docs/hyperparameter_known_gt_protocol_amendment_1.md`  
**Triggering geometry run:** GitHub Actions `36167535578` at source `bcd7099bca8d37f9f895227c386503610639bd03`  
**Observed known-GT estimator outcomes at freeze:** none

This amendment changes only construction of the synthetic known deformation
after the first complete 30-case geometry-only preflight exposed one folding
case.

The base protocol and Amendment 1 remain unchanged in the repository. Where
this amendment conflicts with their synthetic-transform construction rule, this
amendment governs.

## Why an amendment is necessary

The geometry-only preflight completed public-data acquisition for all ten frozen
held-out anatomies and generated all 30 predeclared synthetic cases.

The result was:

- 29 / 30 geometry cases passed;
- `aaa0072`, replicate `1`, case seed `7001` failed;
- the failure was a folding deformation with minimum evaluated Jacobian
  determinant `-0.0105857`;
- zero hyperparameter-ensemble registrations were run;
- no sigma field, registration-error field, case correlation, anatomy effect,
  p-value, calibration quantity, or estimator comparison was observed.

The exact preflight outcome is preserved in
`research/KNOWN_GT_GEOMETRY_PREFLIGHT_RESULT_1.json`.

The base protocol explicitly requires strictly positive Jacobian determinant
throughout the evaluated crop grid and requires a prospective amendment rather
than silent seed or anatomy substitution when geometry fails.

## A2.1 Raw random deformation is unchanged

For every anatomy/replicate pair, continue to generate the exact same raw
B-spline coefficient vector using:

- the same case seed;
- deformation mesh size `4`;
- independent Gaussian coefficients;
- raw coefficient mean `0.0`;
- raw coefficient standard deviation `4.0`.

The raw coefficient vector is generated once.

Do **not** redraw coefficients and do not substitute another seed when topology
fails.

## A2.2 Deterministic topology backtracking

For every case, construct candidate transforms by multiplying the frozen raw
coefficient vector by each scale in this exact order:

```text
1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50
```

For each candidate, compute the displacement field and Jacobian determinant on
the same evaluated crop grid used by the existing geometry preflight.

Select the **first** candidate in the ordered list whose:

- transform parameters are finite;
- displacement field is finite;
- Jacobian determinant is finite everywhere; and
- minimum evaluated Jacobian determinant is strictly greater than `0.0`.

Because the scales are ordered from largest to smallest, this selects the
largest predeclared amplitude that satisfies the original topology criterion.

If no candidate through scale `0.50` passes, the geometry preflight fails and
the study stops again. Do not extend the scale grid after seeing that outcome
without another explicit prospective amendment.

This rule is applied to **all 30 cases**, not only to the previously failed
case.

## A2.3 What must be recorded

For every case, the geometry record must additionally contain:

- minimum Jacobian determinant of the raw scale-`1.00` transform;
- selected topology scale;
- minimum Jacobian determinant of the selected transform;
- whether attenuation was required.

The realized true-displacement summaries remain mandatory and are computed from
the selected transform.

The final transform used for fixed-image synthesis, ROI warping, landmark
mapping, known true displacement, and any later estimator evaluation must be
the same selected transform.

## A2.4 Seed and sampling invariants

This amendment does not change:

- anatomy order;
- case seed;
- noise seed;
- landmark seed;
- number of replicates;
- number of landmarks;
- fixed-domain ROI rule;
- landmark boundary margin;
- image-noise distribution.

Landmarks and the fixed-domain ROI are generated from the selected topology-safe
transform using the already-frozen seeds.

## A2.5 Required repeat of the whole geometry preflight

Do not validate only the previously failed case.

After implementation, rerun the complete 30-case geometry-only preflight under
this amendment.

Result-bearing execution remains unauthorized unless all 30 amended geometry
cases pass and the complete reviewed geometry record is pinned by a separate
run authorization.

## A2.6 Interpretation boundary

The raw stochastic deformation draw still has coefficient standard deviation
`4.0`, but a case may have a smaller realized amplitude after deterministic
topology backtracking.

Therefore future reporting must distinguish:

- raw coefficient distribution;
- selected topology scale; and
- realized displacement distribution.

The positive-Jacobian check is the protocol's discrete evaluated-grid topology
criterion. It must not be described as a proof of continuous-domain
diffeomorphism.

## A2.7 What does not change

This amendment does not alter:

- the ten held-out anatomies;
- any frozen DICOM series identity;
- the 30 case seeds;
- the promoted nine-member estimator;
- registration mesh size or iteration budget;
- the pointwise Spearman endpoint;
- anatomy-level aggregation;
- exact sign test;
- bootstrap rule;
- assessability thresholds;
- calibration sequencing;
- any claim boundary.

No estimator output existed when this amendment was frozen.

## Scientific rationale

Local invertibility/topology preservation in B-spline deformation models is
commonly expressed through positivity of the transformation Jacobian. The
amendment uses that same criterion only as a pre-estimator geometry constraint.
Amplitude backtracking preserves each frozen random coefficient direction and
seed rather than replacing an inconvenient deformation.

Relevant background includes topology-preserving and Jacobian-constrained
B-spline registration work by Noblet et al. (IEEE TIP, 2005), Rueckert et al.
(MICCAI, 2006), and Chun & Fessler (IEEE TMI, 2009/2011 archive).

## Frozen status

`KNOWN_GT_PROTOCOL_AMENDMENT_2=FROZEN`

`KNOWN_GT_GEOMETRY_PREFLIGHT_OBSERVED_AT_FREEZE=YES`

`KNOWN_GT_GEOMETRY_PREFLIGHT_RESULT_AT_FREEZE=29_PASS_1_FOLD`

`KNOWN_GT_RESULT_BEARING_REGISTRATION_RUN_AT_FREEZE=NO`

`KNOWN_GT_ESTIMATOR_OUTCOME_OBSERVED_AT_FREEZE=NO`
