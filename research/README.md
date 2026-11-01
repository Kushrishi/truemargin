# Research guide

Start with the [technical report](../docs/technical_report.md) and [current status](STATE.md).
The controlled studies are complete; external validation is deferred. The older
[roadmap](ROADMAP.md) and dated execution records describe past plans, not active work.

| Question | Where to look |
| --- | --- |
| Does registration spread track known spatial error? | [Ranking results](../docs/hyperparameter_known_gt_result.md), [comparator analysis](COMPARATOR_AUDIT.md) |
| Where does the relationship fail? | [Failure analysis](../docs/m5_informativeness_characterization.md) |
| Do error bounds cover held-out errors, and how wide are they? | [Calibration](../docs/m6_phase_a_calibration_result.md), [evaluation](../docs/m6_phase_b_evaluation_result.md), [failure diagnostics](../docs/m6_failure_diagnostics.md) |
| What do the results contribute? | [Contribution review](../docs/m4_m6_contribution_review.md), [claims summary](CLAIMS.md), [related work](RELATED_WORK.md) |
| Where did the external study stop? | [Source and decoder checks](DIRLAB_DECODER_AUDIT_2026_10.md), [runtime investigation](DIRLAB_RUNTIME_FEASIBILITY_2026_10.md), [current status](STATE.md) |
| How can I check the results? | [Reproduction instructions](../docs/reproduction.md), [results index](../results/README.md) |

## Study identifiers

These labels remain in filenames and result records so existing links and verification commands continue to work.

| Identifier | Study |
| --- | --- |
| M4 | Known-deformation ranking: ten anatomies, three deformation cases each |
| M5 | Failure analysis of those saved results |
| M6 Phase A | Calibration on 30 anatomies |
| M6 Phase B | Evaluation on 30 separate anatomies with fixed thresholds |

The [decision log](DECISION_LOG.md) records method selection and amendments. The
[older status snapshot](STATUS.md) predates the completed results. Frozen protocols
and copies within result bundles remain unchanged.
