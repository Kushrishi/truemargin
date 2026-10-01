# TrueMargin M5 known-ground-truth analysis plan

**Frozen:** 2026-10-01  
**Evidence source:** completed M4 result-bearing study only  
**Analysis class:** secondary/descriptive; no new registration or model fitting

## 1. Purpose

M4 established a bounded positive result: under the frozen known-deformation study, the promoted nine-member hyperparameter-ensemble sigma contains useful pointwise rank information about true local registration error.

M5 does not rerun that hypothesis with new thresholds. It asks the next predeclared questions:

1. how heterogeneous is informativeness across anatomies and cases;
2. how do the frozen direct comparators behave under the same anatomy-aware summaries;
3. where do high-error / low-reported-score blind spots occur;
4. how severe are those misses when they occur; and
5. which method-specific failures or invalid cases constrain interpretation.

The analysis must preserve weak anatomies, negative cases, and comparator failures.

## 2. Immutable inputs

All M5 numerical inputs come from the completed M4 workflow run `36188222836` at execution source SHA:

`9add89e5055ba45eb6c6b93c42da38615891a225`

The final aggregate artifact is:

- artifact ID `10896650804`;
- digest `sha256:bd1f76e20c7e4591b5b3113c061c90534ec413bda0a242747625ed6d5f96b728`.

The ten anatomy shard artifact IDs and digests are frozen in `research/KNOWN_GT_M5_ANALYSIS_REQUEST.json`.

Each shard contains three immutable per-case NPZ checkpoints. Every checkpoint contains the original 50-point vectors needed for M5, including:

- known registration error;
- target sigma;
- landmark indices;
- true displacement;
- ICE score when valid;
- residual score when valid;
- Jacobian-deviation score when valid;
- method validity/failure metadata; and
- embedded M4 provenance.

M5 must verify the embedded execution SHA and expected cohort/case identity before accepting a checkpoint.

## 3. Durable pointwise evidence table

The expiring workflow shard artifacts are not an acceptable long-term dependency for paper analysis. M5 will therefore derive one compact pointwise table directly from the immutable checkpoints and commit it as research evidence.

Expected structure:

- 10 anatomies;
- 3 cases per anatomy;
- 50 frozen points per case;
- exactly **1,500 rows**.

Per row, preserve at least:

- patient/anatomy identity;
- replicate and case seed;
- point index;
- frozen `z/y/x` voxel index;
- known error in mm;
- target sigma in mm;
- true-displacement magnitude in mm;
- ICE score or missing if method-invalid;
- residual score or missing if method-invalid;
- Jacobian-deviation score or missing if method-invalid.

The table is derived evidence, not a new experimental substrate. A machine-readable provenance record must bind it to the source workflow, shard artifact IDs/digests, M4 execution SHA, and generated table hash.

## 4. Reconciliation requirement

Before any M5 interpretation is accepted, recomputation from the pointwise table must reproduce the frozen M4 case-level metrics within numerical tolerance:

- Spearman score/error association;
- score median and IQR;
- top-minus-bottom quartile known-error delta;
- blind-spot rate;
- comparator validity/failure state.

Recomputed anatomy-level medians must also reproduce the M4 anatomy tables.

A mismatch is a provenance/implementation failure and blocks M5. It must not be resolved by altering the M4 records.

## 5. Frozen M4 metrics reused by M5

For every valid method/case:

### 5.1 Rank informativeness

`Spearman(method_score, known_error)`

### 5.2 Quartile enrichment

Using the case-specific score quartiles already frozen in M4:

`median(error | score >= Q75_score) - median(error | score <= Q25_score)`

### 5.3 Blind spot

A point is a blind spot when both are true:

- `known_error >= Q75_error`; and
- `method_score <= Q25_score`.

The frozen M4 blind-spot rate is:

`blind_spot_count / all_case_points`.

No alternate threshold is introduced in M5.

## 6. M5 descriptive blind-spot severity

M5 adds only descriptive quantities around the already-frozen blind-spot set. For each valid method/case report:

- blind-spot count;
- high-error point count (`known_error >= Q75_error`);
- blind-spot fraction of high-error points;
- median known error among blind-spot points;
- maximum known error among blind-spot points.

If a case has no blind-spot points, blind-spot error severity is missing rather than zero.

These quantities receive no new p-values and do not change the M4 evidence label.

## 7. Aggregation

The anatomy remains the formal unit.

For each method:

1. compute/reuse valid case-level quantities;
2. aggregate valid cases within anatomy using the median;
3. report all anatomy values;
4. summarize across assessable anatomies descriptively.

Comparator anatomy assessability remains governed by the frozen M4 rule: at least two valid cases for the anatomy. The target sigma has three complete cases in every anatomy.

Do not pool all 1,500 landmarks and treat them as independent inferential observations.

## 8. Failure inventory

For ICE, residual, and Jacobian deviation, retain:

- every method-invalid case;
- exact failure reason;
- number of valid cases per anatomy;
- whether each anatomy remains assessable.

No failed comparator value is imputed, repaired, winsorized, or replaced by another metric after observing outcomes.

## 9. Predefined figures

The first M5 figure set is fixed as:

1. anatomy-level Spearman values for sigma, ICE, residual, and Jacobian deviation;
2. anatomy-level top-minus-bottom known-error delta for all four methods;
3. anatomy-level blind-spot rate for all four methods;
4. paired anatomy-level `sigma rho - ICE rho` values.

All assessable anatomies appear. No primary figure may display only favorable anatomies or hand-selected cases.

Any later illustrative pointwise case plot must either show all cases in a supplement or use an explicitly disclosed deterministic selection rule and remain illustrative rather than inferential.

## 10. Interpretation rules

M5 may support statements such as:

- the signal is heterogeneous across anatomies;
- some cases contain high-error / low-score blind spots despite a positive aggregate M4 result;
- one comparator exhibits more/fewer failures or blind spots under the frozen rules;
- residual/Jacobian behavior differs materially from sigma under the already-frozen paired summaries;
- ICE remains a strong comparator and constrains any method-superiority framing.

M5 may **not** establish or imply:

- new superiority over ICE;
- numerical calibration;
- probabilistic coverage;
- clinical usefulness;
- external-dataset generalization;
- universal registration-uncertainty behavior.

## 11. Prohibited post-result changes

Do not:

- add a new superiority p-value;
- change quartile thresholds;
- redefine blind spots after seeing which method looks better;
- pool landmarks for formal inference;
- drop weak anatomies;
- silently omit comparator-invalid cases;
- choose a favorable subset for the primary figure;
- alter M4's primary/comparator conclusions.

## 12. M5 exit criteria

M5 is complete when the repository contains:

- a verified 1,500-row pointwise evidence table and provenance record;
- case-level blind-spot severity/failure table;
- anatomy-level method table;
- method failure inventory;
- machine-readable M5 summary;
- the four predefined figures generated from committed evidence;
- a concise M5 result document reconciling strengths, heterogeneity, blind spots, and the ICE boundary;
- green formatting, typing, tests, and reproducibility checks.

Only after M5 is complete should the project decide whether a separate calibration analysis or a prospectively frozen robustness study is justified.
