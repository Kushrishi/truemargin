# TrueMargin

TrueMargin is a medical-image-computing research project studying a narrow question:

> **When a deformable image-registration method reports local uncertainty, under what conditions does that signal contain useful information about true local spatial registration error?**

The project separates questions that are often conflated: operational variability, pointwise
informativeness, numerical calibration, blind spots, and generalization.

TrueMargin is research software, not a clinical product or medical device.

## Current evidence

The prospective rebuild produced both negative and positive results before the primary
known-ground-truth study:

- a relative-intensity perturbation ensemble failed its frozen promotion gate;
- the mesh-3 / 15-iteration registration regime passed its prospective field-stability gate;
- an initialization-sensitivity ensemble failed its frozen promotion gate;
- a frozen nine-member registration-hyperparameter ensemble passed operational promotion.

Operational promotion did not establish that the resulting uncertainty signal tracked true error,
so the estimator was evaluated prospectively on synthetic known deformations in ten held-out
anatomies.

## Primary known-ground-truth result

The source-pinned M4 result-bearing study completed on 2026-09-26 under the frozen protocol and
comparator specification.

Across **30 / 30 complete cases from 10 held-out anatomies**, the promoted hyperparameter-ensemble
sigma had a median anatomy-level Spearman association with known local error of **0.6841**. All
**10 / 10** anatomy-level associations were positive; the frozen exact one-sided anatomy sign-test
gave **p = 0.0009766**, and the 10,000-replicate anatomy bootstrap interval for the median was
**[0.3048, 0.8284]**.

Under this controlled study, the uncertainty signal therefore contains useful pointwise rank
information about true local spatial error.

The direct-comparator result is deliberately not reduced to a single winner claim:

- inverse-consistency error: median anatomy Spearman **0.7203**;
- same-modality residual: **0.2851**;
- Jacobian deviation: **0.1689**.

Paired anatomy-level bootstrap summaries support stronger rank informativeness for the target sigma
than the residual and Jacobian-deviation comparators in this study. They do **not** establish
superiority over inverse-consistency error: the target-minus-ICE interval crosses zero.

See `docs/hyperparameter_known_gt_result.md` and `research/KNOWN_GT_M4_RESULT.json` for the durable
primary result record.

## M5 failure characterization

M5 reanalyzed the exact frozen M4 outputs without rerunning registration or introducing a new
confirmatory statistic. The ten patient shard archives preserved all 50 sampled locations per
case, so the post-primary characterization covers all **1,500** frozen pointwise observations.

Under the original M4 blind-spot definition — known error at or above the case 75th percentile and
method score at or below the case 25th percentile — target sigma had **39 / 1,500** blind-spot
points across **11 / 30** cases. At the case level, **24 / 30** sigma/error rank associations were
positive and **6 / 30** were negative.

The failure structure matters. `aaa0069` was weak across all three deformations, while `aaa0053`
had one severe inverted replicate despite a strong anatomy-level median. The M4 anatomy-level
result is therefore positive but not uniformly reliable across deformation instances.

ICE remains the strongest direct comparator. Its anatomy-level performance was comparable to
sigma, and only 12 of the 39 sigma blind spots were also ICE blind spots. That overlap is
descriptive post-primary evidence, not a claim that the signals should be combined.

See `docs/m5_informativeness_characterization.md`, `research/M5_CHARACTERIZATION.json`, and
`results/m5/` for the complete M5 evidence.

## Research discipline

Result-defining choices are frozen before the corresponding outcomes are observed. Negative
results are retained. Scientific failures and method-specific invalid comparator cases are
preserved rather than repaired after seeing outcomes.

The current program keeps separate:

- local rank informativeness;
- high-error / low-reported-uncertainty blind spots;
- operational failures;
- numerical calibration;
- robustness and external generalization.

M1-M5 are complete. The next milestone is M6 calibration, which must remain distinct from the
already-completed rank-informativeness result.

See `research/STATE.md` and `research/CLAIMS.md` for the current evidence and claim boundaries, and
`research/ROADMAP.md` for the milestone plan.

## Scope

TrueMargin does **not** currently establish:

- numerical calibration or probabilistic coverage;
- superiority over inverse-consistency error;
- absence of deformation-specific blind spots;
- external-dataset generalization;
- clinical validity or clinical usefulness; or
- a completed manuscript, preprint, or peer-reviewed publication.
