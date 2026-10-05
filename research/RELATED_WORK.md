# Related work

**Updated:** October 5, 2026

Registration uncertainty, perturbation ensembles, inverse consistency and conformal calibration have established precedents. TrueMargin evaluates a fixed ensemble against known spatial error, separates ranking from calibrated bounds, and examines missed errors.

## Closest work

| Work | Signal / method | Ground-truth relationship | Main relevance to TrueMargin |
| --- | --- | --- | --- |
| Meyer et al., *Deformable Image Registration Uncertainty-Encompassing Dose Accumulation for Adaptive Radiation Therapy* (2025) | Hyperparameter-perturbation ensemble of DVFs; voxelwise uncertainty ellipsoids | Clinical cohort lacks true DVF; paper explicitly distinguishes uncertainty from error | Precedent for hyperparameter ensembles; motivates measuring uncertainty against known error. |
| Van der Heyden et al., *Inverse consistency error for validating deformable image registration* (2026) | Voxelwise inverse-consistency error | Computational phantoms with known deformation; reported strong GT error association and a failure mode for large homogeneous deformation | Strong comparator and proof that known-GT spatial validation can reveal both usefulness and blind spots. |
| Gheiji et al., *CONReg* (2026) | Quantile regression + conformal prediction for voxel/case uncertainty | Empirical coverage 0.92-0.98; uncertain groups had higher registration error | Calibration and informativeness are both already active research targets; Both are established research questions. |
| Tian, Hu & Iglesias, *Test-time Uncertainty Estimation ... via Transformation Equivariance* (2025/2026 preprint) | Transformation-equivariance discrepancy for pretrained registration models | Reports uncertainty/error correlation across models/anatomies | Important model-agnostic comparator concept; uncertainty can be estimated from transformation consistency rather than retraining an uncertainty model. |
| Li et al., *Contrastive Discrepancy* (Medical Image Analysis, 2026) | Label-free deformation-field discrepancy based on bias/variance and transformation groups | Performance curve reported to mirror gold-standard TRE across multiple model families/datasets | Very close to the broader question of whether a label-free registration signal tracks true error and supports hyperparameter selection. |
| Chen et al., medical image-registration survey (Medical Image Analysis, 2025) | Survey of modern registration, uncertainty, and evaluation | Review | Confirms uncertainty/evaluation is already a broad field; contribution must be specific and comparative. |
| Le Folgoc et al., sparse Bayesian registration uncertainty (TMI, 2017) | Bayesian posterior uncertainty | Evaluates approximate vs more exact posterior inference | Historical reminder that optimizer/model uncertainty has a substantial pre-deep-learning literature. |

## Comparator choices in the completed study

The direct local comparison used ensemble uncertainty, inverse-consistency error, image residual and Jacobian deviation. Their definitions and failure rules were fixed before outcomes; the [comparator audit](COMPARATOR_AUDIT.md) records those choices.

Contrastive Discrepancy was considered for case-level model selection but excluded before results because its linked code snapshot could not be retrieved reproducibly and the available description did not fix exact scoring semantics. No substitute was invented. Transformation-equivariance uncertainty and CONReg remained related work because they use learned registration models rather than the classical optimizer studied here.

## What remains to establish

The completed studies support a positive but heterogeneous association between ensemble spread and spatial error. They do not establish an advantage over inverse-consistency error, precise calibrated bounds or external generalization. The next planned experiment uses lung CT landmark pairs from a separate dataset. It should test the fixed estimator and comparators rather than retune the completed prostate studies.

See the [technical report](../docs/technical_report.md), [claims summary](CLAIMS.md) and [external-study protocol](../docs/external_lung_validation_protocol.md).

## Sources

Primary/review sources currently driving this boundary:

- Meyer et al. (2025), *Deformable Image Registration
  Uncertainty-Encompassing Dose Accumulation for Adaptive Radiation Therapy*,
  International Journal of Radiation Oncology, Biology, Physics,
  DOI 10.1016/j.ijrobp.2025.04.004.
- *Inverse consistency error for validating deformable image registration: an
  explorative study on computational phantoms* (2026), Physics and Imaging in
  Radiation Oncology, DOI 10.1016/j.phro.2026.100916.
- Gheiji et al. (2026), *CONReg: Uncertainty-Aware Medical Image Registration
  Using Conformal Prediction*, DOI 10.1007/s10278-026-01878-3.
- Tian, Hu & Iglesias (2025/2026), *Test-time Uncertainty Estimation for Medical
  Image Registration via Transformation Equivariance*, arXiv:2509.23355.
- Li et al. (2026), *Contrastive Discrepancy: A label-free metric for deformable
  image registration supporting testing-time hyperparameter selection*,
  Medical Image Analysis 113:104210, DOI 10.1016/j.media.2026.104210.
- Chen et al. (2025), *A survey on deep learning in medical image registration:
  New technologies, uncertainty, evaluation metrics, and beyond*, Medical Image
  Analysis 100:103385.
- Le Folgoc et al. (2017), *Quantifying Registration Uncertainty With Sparse
  Bayesian Modelling*, IEEE Transactions on Medical Imaging 36(2):607-617.
