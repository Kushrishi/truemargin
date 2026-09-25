# Amendment 2 — geometry-only global deformation-strength calibration

**Status:** frozen after the first complete geometry-only preflight and before any hyperparameter-ensemble known-GT registration result  
**Triggering geometry run:** `36167535578`  
**Triggering source revision:** `bcd7099bca8d37f9f895227c386503610639bd03`  
**Observed result before this amendment:** geometry only; 29/30 valid; no estimator registrations  
**Supersedes:** base protocol Section 6.2 only where this amendment explicitly changes the B-spline coefficient standard deviation

## 1. Reason for amendment

The original geometry-only preflight used the frozen Gaussian B-spline
coefficient standard deviation `4.0`.

Exactly one predeclared case failed the prospectively required topology check:

- anatomy: `aaa0072`
- replicate: `1`
- case seed: `7001`
- minimum Jacobian determinant: `-0.0105857`

The other 29 cases passed geometry.

The base protocol explicitly requires the study to stop before estimator
execution if any case fails geometry and permits a protocol amendment only if
the record states that geometry alone was observed. Those conditions hold:
**zero** promoted-estimator registrations and **zero** sigma/error outcomes have
been observed.

## 2. What remains frozen

This amendment does **not** change:

- the ten held-out anatomies;
- the three replicates per anatomy;
- the 30-case seed schedule;
- the B-spline deformation mesh size `4`;
- the Gaussian coefficient generator family;
- coefficient mean `0.0`;
- the image-construction direction;
- the intensity-noise scale or seed offsets;
- the fixed-domain HECaP ROI rule;
- the 50-landmark rule or landmark seed offsets;
- any geometry validity criterion;
- the promoted nine-member uncertainty estimator;
- any known-error definition;
- any primary/secondary endpoint;
- any inferential rule or threshold; or
- the prohibition on result-bearing execution before a reviewed geometry
  record is separately authorized.

The failed case is not removed and seed `7001` is not replaced.

## 3. Frozen global calibration grid

Evaluate the complete 30-case geometry preflight, with no estimator
registrations, at the following **global** coefficient-standard-deviation
candidates in this exact order:

```text
3.5
3.0
2.5
```

Each candidate is applied to **all 30 cases** using the original anatomy and
seed schedule.

No per-case coefficient strength, seed substitution, rejection sampling, or
case-specific amplitude backoff is permitted.

## 4. Selection rule

Select the **largest** candidate in the frozen grid for which **all 30/30**
predeclared cases pass every original geometry constraint.

A candidate passes only if every case satisfies the complete existing
geometry-only contract, including:

- finite transform parameters;
- finite displacement field;
- strictly positive Jacobian determinant throughout the crop;
- exactly 50 unique eligible landmarks;
- transformed-landmark source-domain containment; and
- finite true landmark displacement.

Selection uses geometry only. The promoted uncertainty estimator must not be
invoked during this calibration.

If `3.5` passes 30/30, do not evaluate lower candidates for selection.
If `3.5` fails, evaluate `3.0`; if that fails, evaluate `2.5`.

If none of the three candidates passes 30/30, record the failure and stop. Do
not extend the grid after observing those outcomes. A different
topology-preserving synthetic generator would then require another explicit
prospective amendment.

## 5. After selection

After a global coefficient standard deviation is selected:

1. commit the selected value and the complete geometry-calibration record;
2. make that value the sole known-GT deformation strength for this study;
3. rerun the complete 30-case geometry preflight under the selected frozen
   value;
4. review and pin the resulting machine-readable geometry artifact;
5. only then may a separate result-bearing run request authorize the 270
   estimator registrations.

No estimator result may be used to revisit the selected deformation strength.

## 6. Interpretation

This amendment responds only to an invalid synthetic topology discovered by the
prospective geometry gate.

It must not be described as tuning the uncertainty estimator, improving its
expected association with error, or selecting a favorable outcome. The
coefficient strength is chosen solely to make the predeclared synthetic
transform set geometrically valid under the study's original topology rule.
