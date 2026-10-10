# TrueMargin roadmap

Updated 10 October 2026. [Current evidence](STATE.md) · [Claims](CLAIMS.md)

## Purpose

Build a reproducible evaluation toolkit and empirical study of local registration
quality: when does disagreement among registrations identify spatial error, when
does it miss that error, and how does it compare with cheaper signals?

The intended user is a registration researcher evaluating a quality signal.
A publishable comparative study is the research goal. A clinical product,
a new registration model and a claim that spread is calibrated probability are
outside the present scope.

## Milestones and decisions

| Milestone | Status | Work and completion evidence | Decision afterward |
| --- | --- | --- | --- |
| Controlled studies | Complete | Known-deformation ranking, failure analysis and separate calibration/evaluation results are retained in the [technical report](../docs/technical_report.md). | Preserve the positive associations, case reversals, conservative bounds and failed comparator runs together. |
| Recover one real-image registration | In progress | Obtain terminal wall time, CPU, peak RSS, optimizer stop and a complete field; copy it to persistent storage and verify its hashes from an independent runtime. | If the field or terminal evidence is missing, report the attempt as incomplete or unverified. Diagnose the specific failure before proposing another attempt. |
| Establish an affordable external study | Blocked by real-member recovery | Budget all prescribed forward members, reverse comparators, temporary arrays, retained fields and transfer time. State both measured inputs and uncertainty in the estimate. Finalize the DIR-Lab replacement amendment and coordinate/eligibility rules before outcome access. | Proceed only when the complete study fits an explicit resource budget. If it does not, document a prospective redesign or stop; do not silently weaken the fixed estimator. |
| Evaluate external error ranking | Not started | Run the frozen sensitivity signal and declared inverse-consistency, image-residual and Jacobian comparators on the prescribed eligible cases. Retain failures, missingness, patient-level summaries and all denominators. | Assess informativeness, blind spots and comparative cost. Do not select only successful registrations or treat landmarks as independent patients. |
| Deliver the evaluator and research report | Conditional on complete evidence | One documented supported-input workflow, explicit geometry/units, saved numerical outputs, reproducible figures, environment and data-access instructions. Contribution review against related work precedes a submission-ready manuscript. | A useful comparative or failure-analysis result may justify a paper. If novelty is insufficient, release a clearly bounded technical study rather than claiming a new method. |

## Immediate order

1. Read the existing registration attempt's saved terminal evidence when available.
2. Verify field retention independently and calculate the full-study resource estimate.
3. Settle the replacement protocol before any external landmark-based evaluation.
4. Execute and analyze that study only within its approved design and budget.
5. Decide manuscript scope from the comparative findings; prepare LaTeX and archival
   reproduction materials for that scope rather than drafting unsupported conclusions.

Image decoding is qualified. Field-size copy and remount readback have passed,
but those storage checks are not a completed real registration or independent
runtime recovery. The current attempt is a feasibility prerequisite, not the
external accuracy experiment. No additional worker is implied by this roadmap.

## What would change the direction?

- **Compute or retention failure:** repair the execution/storage problem first;
  another full run is not the default response.
- **No advantage over inverse consistency:** retain that finding. Investigate
  whether the study establishes useful limits or complementary failure behavior;
  do not tune against the evaluated external outcomes to obtain a win.
- **Conservative or uninformative bounds:** keep coverage and radius together.
  External calibration would need a separate adequately justified design; ten
  lung cases do not automatically supply it.
- **Insufficient novelty:** maintain the toolkit and publish the bounded technical
  record. A manuscript is an outcome to earn, not a required label for the project.

## Relevant standards

Reviewed 10 October 2026:

- [RegUn](https://github.com/hsokooti/RegUn) predicts local registration error in
  chest CT. It is relevant prior work for the target, not the same estimator.
- [CONReg](https://doi.org/10.1007/s10278-026-01878-3), published 11 March 2026,
  combines quantile regression and conformal prediction for registration.
  Registration uncertainty and conformalization alone are not a novelty claim.
- [uniGradICON](https://github.com/uncbiag/uniGradICON) provides installation,
  executable registration commands, models and examples. Adopt its direct path
  from input to output; its registration performance does not validate TrueMargin.

## Evidence boundaries

Frozen protocols, archived results and numerical definitions remain unchanged.
The immediate external question is ranking and failure behavior. Clinical
validity, external calibration and broad population guarantees are not established.
Numerical external landmarks remain sealed: **HELD-OUT ACCESS SAFE: NO**.
The existing package metadata restricts reuse to research; distribution licensing
must be settled explicitly before presenting a generally reusable release.
