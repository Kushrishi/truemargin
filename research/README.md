# Research evidence guide

Start with the [technical report](../docs/technical_report.md),
[current status](STATE.md) and [roadmap](ROADMAP.md). The roadmap is the current
plan. Dated protocols, decisions and execution records describe their original
studies and do not supersede it.

| Question | Evidence and interpretation |
| --- | --- |
| Does registration spread track known spatial error? | [Controlled ranking result](../docs/hyperparameter_known_gt_result.md), [comparator audit](COMPARATOR_AUDIT.md) |
| Where does that relationship fail? | [Case-level failures and blind spots](../docs/m5_informativeness_characterization.md) |
| Do calibrated bounds cover held-out errors, and how wide are they? | [Calibration result](../docs/m6_phase_a_calibration_result.md), [evaluation result](../docs/m6_phase_b_evaluation_result.md), [failure diagnostics](../docs/m6_failure_diagnostics.md) |
| What do these results contribute? | [Contribution review](../docs/m4_m6_contribution_review.md), [claims ledger](CLAIMS.md), [related work](RELATED_WORK.md) |
| What is required for a real lung-image study? | [Decoder audit](DIRLAB_DECODER_AUDIT_2026_10.md), [resource feasibility](DIRLAB_RUNTIME_FEASIBILITY_2026_10.md), [current roadmap](ROADMAP.md) |
| How can I check retained evidence? | [Reproduction](../docs/reproduction.md), [results index](../results/README.md) |

## Historical identifiers

These identifiers remain in filenames, hashes and protocols to preserve links
and reproduction. They are study labels, not method names or quality levels.

| Identifier | Study |
| --- | --- |
| M4 | Known-deformation ranking: ten anatomies, three deformation cases each |
| M5 | Descriptive failure and blind-spot analysis of those saved results |
| M6 Phase A | Source-stratified calibration on 30 anatomies |
| M6 Phase B | Evaluation on 30 separate anatomies with sealed thresholds |

The [decision log](DECISION_LOG.md) records estimator selection and amendments.
The [older status snapshot](STATUS.md) is explicitly pre-result. Copies of frozen
protocols within result bundles are deliberate provenance records; keep their
bytes and paths intact.
