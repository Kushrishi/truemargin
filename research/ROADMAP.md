# TrueMargin roadmap

Updated 11 October 2026. [Current evidence](STATE.md) · [Claims](CLAIMS.md)

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
| Recover real-image members | Two Case7 fields independently recovered | The first field passed [cross-host recovery](CASE7_CROSS_HOST_RECOVERY_2026_10_10.md). The matched `1e-4`/`1e-5` tolerance pair differed by only `4.10e-12 mm` vector RMS; both reached the 15-iteration cap. Earlier disconnected outcomes remain unknown. | Preserve the negative diversity result. Two members are not a complete nine-member ensemble, convergence or accuracy validation. |
| Establish an affordable external study | Archive inventory and Mac identity preflight passed; RAM/launcher gate open | The owner verified ten original DIR-Lab archives and paired 300-landmark entry metadata. The prospective cohort is distinct from Learn2Reg. Resource feasibility and the prospective freeze still require review before outcome access. | A single image-only probe requires separate approval after the RAM/launcher gate; no full campaign is authorized. |
| Evaluate external error ranking | Not started | Run the frozen sensitivity signal and declared inverse-consistency, image-residual and Jacobian comparators on the prescribed eligible cases. Retain failures, missingness, patient-level summaries and all denominators. | Assess informativeness, blind spots and comparative cost. Do not select only successful registrations or treat landmarks as independent patients. |
| Deliver the evaluator and research report | Conditional on complete evidence | One documented supported-input workflow, explicit geometry/units, saved numerical outputs, reproducible figures, environment and data-access instructions. Contribution review against related work precedes a submission-ready manuscript. | A useful comparative or failure-analysis result may justify a paper. If novelty is insufficient, release a clearly bounded technical study rather than claiming a new method. |

## Current gate

The latest owner-performed Mac preflight passed original archive, reference field,
candidate configuration and frozen source identities. Review available RAM and
launcher readiness next. Any single image-only `bins32`/`tol1e-5` probe requires a
separate authorization; the roadmap does not authorize execution.

The ten-case archive/entry inventory is complete, while numerical landmarks remain
sealed. Freeze any prospective DIR-Lab external analysis before outcome access,
without relabeling the original Learn2Reg study or changing accepted outcomes.
Full-cohort resources, scientific usefulness and landmark validation remain open.

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

