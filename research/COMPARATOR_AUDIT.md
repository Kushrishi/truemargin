# Comparator audit

**Updated:** 2026-09-25  
**Status:** prospective comparator selection before any result-bearing known-GT registration

## Scope

This audit determines which contemporary registration-uncertainty or
label-free-quality methods are sufficiently comparable to TrueMargin's frozen
classical B-spline study to justify paper-level evaluation.

At this point:

- the reviewed geometry-only preflight has passed 30 / 30 cases;
- zero result-bearing known-GT estimator registrations have run;
- no sigma/error correlation, comparator outcome, anatomy effect, p-value, or
  model-selection outcome has been observed.

Comparator choices therefore cannot be conditioned on the primary result.

## Direct local comparator set

### 1. Inverse consistency error — include

**Decision:** include as the strongest direct local comparator.

ICE is reference-free, spatially resolved, and can be computed from forward and
reverse registrations. Historical work cautions that inverse consistency is
necessary but not sufficient for accuracy. A 2026 computational-phantom study
reported strong voxelwise association with ground-truth registration error in
anatomical phantoms while also demonstrating an important blind spot under
large homogeneous deformations.

That combination makes ICE especially valuable for TrueMargin: the question is
not merely whether a surrogate sometimes correlates with error, but where it
fails.

For direct comparability to the frozen TrueMargin target, ICE will be computed
from the **forward and reverse nine-member ensemble-mean displacement fields**,
not from an independently chosen registration configuration.

### 2. Same-modality post-registration intensity residual — include

**Decision:** include as a deliberately simple reference-free local baseline.

The current known-GT substrate is same-modality T2-to-synthetic-T2. A local
absolute intensity residual after warping with the frozen forward ensemble mean
is therefore a fair low-complexity baseline.

It is not claimed to generalize to the historical real T2-to-DCE setting. Its
role is to test whether sophisticated uncertainty/consistency signals add
information beyond an obvious same-modality local mismatch cue.

### 3. Jacobian deviation — include

**Decision:** include as a simple deformation-plausibility baseline.

The local score is the absolute deviation of the ensemble-mean deformation
Jacobian from volume preservation, `abs(J - 1)`, sampled at the same 50
fixed-domain landmarks.

This is intentionally not presented as an uncertainty estimator. Jacobian
metrics characterize local deformation behavior and can reveal implausibility,
but the literature explicitly cautions that such consistency/plausibility
signals are not sufficient measures of registration accuracy.

## Secondary case-level comparator

### Contrastive Discrepancy — include only on its native case/model-selection axis

Li et al., *Medical Image Analysis* 113:104210 (2026), introduces Contrastive
Discrepancy (CD) as a label-free DIR evaluation/model-selection metric based on
the discrepancy between deformation fields estimated under transformed
observations of the same anatomy. The authors' publication page links released
code through the snapshot identifier `anonymous.4open.science/r/dbc-B401`.

The paper's principal use is hyperparameter/model selection, not a claim that a
CD scalar is a pointwise local uncertainty map.

**Decision:** do not force CD into the 50-landmark pointwise Spearman table.
Instead, evaluate it on a separate case-level model-selection axis if a
pre-result implementation audit can reproduce the released method without
changing its transformation group, aggregation, or scoring semantics.

If faithful reproduction would require inventing a new classical-registration
variant, record CD as not directly reproducible in this setup and keep it as
related work. Do not substitute a bespoke favorable analogue after seeing
known-GT outcomes.

## Related work not used as a direct comparator

### Transformation-equivariance uncertainty

Tian, Hu & Iglesias propose test-time uncertainty maps for pretrained
registration models using transformation equivariance. As of this audit, the
authors' current publication page still lists the work as an arXiv preprint.
The demonstrated setting uses pretrained deep registration models such as
uniGradICON/SynthMorph.

**Decision:** related-work-only for the confirmatory classical B-spline study.
Adapting the method to an iterative optimizer would introduce a new method whose
equivalence to the published estimator is not established.

### CONReg

CONReg trains a quantile-regression registration network and applies conformal
calibration to predictive displacement intervals.

**Decision:** related-work-only. It changes the registration model, requires a
training/calibration pipeline, and answers a calibrated predictive-interval
question that is not like-for-like with the frozen classical estimator.

### Historical curvature signal

**Decision:** exclude from the confirmatory comparator set unless a separate
pre-result provenance/mathematics audit establishes a complete, stable
definition. The old private-repo curvature experiments are not allowed into the
paper comparator table merely because they are convenient.

## Comparator philosophy

TrueMargin will not publish a single winner score across methods with different
semantics.

The direct local methods are evaluated on the same fixed-domain landmarks
against the same frozen ensemble-mean known-error target.

CD, if faithfully reproduced, is evaluated on model-selection behavior rather
than mislabeled as pointwise uncertainty.

Calibration remains a separate later milestone.

## Current literature anchors

- Bender & Tomé (2009), *Physics in Medicine & Biology* 54:5561-5577,
  DOI 10.1088/0031-9155/54/18/014.
- Loi et al. (2026), *Physics and Imaging in Radiation Oncology* 37:100916,
  DOI 10.1016/j.phro.2026.100916.
- Meyer et al. (2025), *International Journal of Radiation Oncology, Biology,
  Physics* 122(4):818-826, DOI 10.1016/j.ijrobp.2025.04.004.
- Li et al. (2026), *Medical Image Analysis* 113:104210,
  DOI 10.1016/j.media.2026.104210.
- Tian, Hu & Iglesias, arXiv:2509.23355.
- Gheiji et al. (2026), *Journal of Imaging Informatics in Medicine*,
  DOI 10.1007/s10278-026-01878-3.
