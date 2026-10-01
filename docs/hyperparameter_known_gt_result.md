# Hyperparameter known-ground-truth result

**Result date:** 2026-09-26  
**Status:** completed prospective M4 result-bearing study

## Outcome

The source-pinned known-ground-truth study completed under the frozen protocol, amendments, comparator specification, execution-control amendment, cohort, seeds, ROI rule, estimator definition, and result-bearing budget.

The primary result supports pointwise rank informativeness of the promoted nine-member hyperparameter-ensemble uncertainty signal in this frozen synthetic known-deformation study.

| Primary quantity | Result |
| --- | ---: |
| Held-out anatomies | 10 |
| Complete synthetic cases | 30 / 30 |
| Positive anatomy-level associations | 10 / 10 |
| Median anatomy-level Spearman | **0.6841** |
| 95% anatomy-bootstrap interval | **[0.3048, 0.8284]** |
| Exact one-sided anatomy sign-test | **p = 0.0009766** |
| Median anatomy blind-spot rate | **0.000** |
| Median high-vs-low uncertainty known-error delta | **1.712 mm** |

The conclusion is deliberately bounded: under the frozen registration regime, synthetic deformation process, held-out anatomy cohort, and spatial sampling rule, larger reported ensemble spread tended to rank locations with larger known spatial registration error.

This result does not establish numerical calibration, external-dataset generalization, clinical validity, or universal behavior of registration uncertainty.

## Direct comparator context

The prospectively frozen direct local comparator suite remained unchanged during result-bearing execution.

| Method | Median anatomy Spearman | Paired target-minus-comparator median | Paired bootstrap 95% interval |
| --- | ---: | ---: | ---: |
| Hyperparameter ensemble sigma | **0.6841** | — | — |
| Inverse-consistency error | **0.7203** | -0.0339 | [-0.0903, 0.0736] |
| Same-modality residual | **0.2851** | +0.2389 | [0.0188, 0.4757] |
| Jacobian deviation | **0.1689** | +0.2703 | [0.1695, 0.7144] |

The paired evidence supports stronger rank informativeness for the target sigma than the residual and Jacobian-deviation comparators in this study. It does **not** support superiority over inverse-consistency error: the target-minus-ICE interval crosses zero and the ICE median is numerically slightly higher.

Method-specific invalid comparator cases were retained under the frozen failure rules rather than repaired or replaced after observing outcomes. All four methods remained assessable at the anatomy level across all ten anatomies.

## Provenance

- GitHub Actions workflow run: `36188222836`
- Successful attempt: `3`
- Result-bearing execution Git SHA: `9add89e5055ba45eb6c6b93c42da38615891a225`
- Final artifact: `truemargin-known-gt-result-bearing`
- Artifact ID: `10896650804`
- Artifact digest: `sha256:bd1f76e20c7e4591b5b3113c061c90534ec413bda0a242747625ed6d5f96b728`
- Frozen result-bearing budget: 270 forward + 270 reverse = 540 registrations
- Primary summary SHA-256: `251f3e5545488e3130344a6a59922b6ee6c38fb1f1fba4342802ddc2bce86f3`

The workflow artifact also records protocol and input identities. The machine-readable durable result record is `research/KNOWN_GT_M4_RESULT.json`.

## Interpretation

M4 resolves the project's first central known-ground-truth question positively but narrowly: the promoted hyperparameter ensemble is not merely operationally variable; in this controlled study, its local variation contains useful information about true local spatial error.

The result also narrows the contribution boundary. The evidence does not justify presenting the hyperparameter ensemble as uniformly better than simpler registration-quality measures because inverse-consistency error performed comparably. A publication should therefore center on controlled evaluation of local uncertainty/quality signals, anatomy-aware failure behavior, and the distinction between informativeness and calibration rather than a universal method-superiority claim.

## Next stage

Proceed to M5 without modifying the completed M4 design or result:

1. preserve and analyze method-specific failures and blind spots;
2. produce anatomy-aware comparator and failure-case figures;
3. characterize high-error / low-reported-uncertainty cases rather than relying only on aggregate rank association;
4. keep calibration as a separate downstream question;
5. freeze any robustness study before observing its outcomes.

No estimator member, comparator definition, anatomy, seed, case, ROI rule, or primary statistic may be changed to improve the completed M4 result.
