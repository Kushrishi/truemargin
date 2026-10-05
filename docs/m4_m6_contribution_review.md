# Contribution review after M4–M6

**Date:** 2026-10-03
**Decision:** prepare a bounded technical report; do not start M7 or a method-superiority manuscript yet. This is an internal scientific assessment, not independent peer review or a publication prediction.

## What the completed work establishes

| Evidence | Supported conclusion | Important limit |
| --- | --- | --- |
| M4, 10 anatomies and 30 deformation cases | Frozen ensemble spread has positive anatomy-level rank association with known local error; median Spearman 0.6841 | ICE performs comparably; paired target-minus-ICE interval crosses zero |
| M5, reconstruction of the same M4 outputs | Positive aggregate association coexists with six negative case associations and 39 low-sigma/high-error sampled locations | Post-primary characterization, not an independent replication; the blind-spot definition is study-specific |
| M6, 30 calibration and 30 evaluation anatomies | Sealed 80%/90% multipliers produce conservative held-out empirical coverage in the frozen synthetic design | Large multipliers, a retained 70.69 mm anatomy median radius, infinite 95% radii, and incomplete ICE comparisons |

The useful finding is the separation of operational variability, local ranking, numerical radius size and failure behavior. None of those axes alone establishes a dependable clinical error estimate. The estimator and scientific boundaries remain unchanged.

## Related work

Meyer et al. already use hyperparameter perturbations to construct registration ensembles and voxelwise uncertainty ellipsoids for dose accumulation. Our nine-member perturbation mechanism is not itself new. Their clinical application and our synthetic error audit answer different questions; we have not reproduced their pipeline and cannot rank the methods across studies. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/40239820/), DOI 10.1016/j.ijrobp.2025.04.004.

CONReg already combines learned quantile registration with conformal calibration. TrueMargin cannot claim to introduce conformal prediction to registration. Its classical optimizer, scalar error magnitude and anatomy-aware hierarchy differ, but those differences are not by themselves enough to establish a publishable contribution. [Primary paper](https://link.springer.com/article/10.1007/s10278-026-01878-3).

The uncertainty/error monotonic-association question was directly studied by Luo et al.; it is not an unexplored premise. Recent ICE computational-phantom work also studies known-error association and a deformation-dependent failure. TrueMargin adds a specific retained comparison and failure record, not a universal discovery that uncertainty can be misleading. [Luo et al.](https://arxiv.org/abs/1908.07709); [ICE paper](https://doi.org/10.1016/j.phro.2026.100916).

Contrastive Discrepancy addresses label-free evaluation and hyperparameter selection across multiple registration families. That creates pressure on a broad quality-estimation headline. It is not the same sampled pointwise-radius estimand; the prospective comparator audit explains why no invented adaptation was inserted into M4. [Author publication page](https://medapt.cn/publication/media26-contrastive-discrepancy/), DOI 10.1016/j.media.2026.104210.

Hierarchical conformal prediction is inherited methodology, not a new theorem here. Its interpretation depends on anatomy-level and within-anatomy exchangeability. A deterministic, synthetic study with fixed patient-derived seeds and one deformation per anatomy does not establish validity across arbitrary acquisition, deformation or clinical populations. [Lee, Barber and Willett](https://arxiv.org/abs/2306.06342).

These sources were rechecked on October 3. The Meyer record and HCP abstract were retrieved; CONReg full text and the CD author description were reviewed. ICE full-text retrieval was unavailable in this recheck; its previously recorded comparator boundary remains unchanged. This is a focused closest-work review, not an exhaustive systematic literature review.

## One missing efficiency check

Coverage can be high because radii are large. M6 did not prospectively include a constant-radius baseline, so its primary results cannot establish that spatial adaptation improves numerical efficiency. To clarify this limit, a separately labeled exploratory analysis uses only the accepted numerical records.

The comparison was chosen **after evaluation outcomes were observed**. It is not a new confirmatory M6 endpoint. Each source's constant radius is fitted only to its 15 calibration anatomies' known errors, using the same equal-group HCP weights. With 50 locations per anatomy, finite scores have weight 1/800 and the new-group infinity atom has weight 1/16. The finite 80%/90% thresholds are exact ranks 640/720; at 95%, both constant and sigma constructions give infinity. Sigma retains its original sealed multipliers. No images are acquired, registrations rerun, cases excluded or accepted thresholds refitted.

| Source, nominal level | Sigma coverage | Constant coverage | Sigma mean radius, mm | Constant radius, mm |
| --- | ---: | ---: | ---: | ---: |
| 3T, 80% | 88.13% | 81.20% | 2.93 | 1.68 |
| Diagnosis, 80% | 86.67% | 87.60% | 4.16 | 1.99 |
| 3T, 90% | 97.73% | 93.73% | 4.66 | 2.21 |
| Diagnosis, 90% | 99.73% | 95.20% | 10.26 | 2.84 |

Mean radius here is the equal-anatomy average of each anatomy's mean radius. It differs from M6's median-of-anatomy-medians summary and retains large-radius tails. At nominal 90%, sigma has a smaller anatomy mean radius in only 1/15 3T and 2/15 Diagnosis anatomies. Its source mean radius is 2.11 and 3.62 times the respective constant radius. This does **not** establish statistical dominance: achieved coverage differs, the comparison is post-outcome, and no clinical radius tolerance has been justified. It establishes a limitation: adaptive efficiency has not been demonstrated, and high coverage alone does not resolve that question.

The exploration has no tuned intercept, clipping, epsilon floor, source pooling, threshold sweep or evaluation-selected mapping. These exploratory results leave the accepted primary study unchanged and do not establish coverage-matched superiority. [Retained exploratory record](../results/m6_exploratory/constant_radius_comparison.json).

Reproduce it from the repository root:

```sh
python scripts/m6_exploratory_efficiency.py .
```

## Publication assessment

A new-uncertainty-method or improved-calibration paper is not currently justified. M4 does not show superiority to ICE, M6 cannot complete its planned calibrated ICE comparison, and the new exploratory check does not establish adaptive efficiency. A generic conformal wrapper would face close prior work. Additional results should not be purchased merely to enlarge the manuscript.

A focused technical report is justified now: a reproducible case study of one classical ensemble, with anatomy-aware rank evidence, deformation-specific inversions, blind spots, conservative radii and retained operational failures. Its scientific value is transparency and a bounded empirical finding. Peer-reviewed workshop or short-paper suitability remains unresolved; no acceptance probability or venue recommendation is asserted.

The resulting [technical report](technical_report.md) includes four evidence panels: M4 comparator associations, M5 case-level inversions and blind spots, M6 held-out coverage with radius tails, and the explicitly exploratory constant-radius comparison. Include exact protocol/result provenance, failure denominators and reproduction commands. Describe the synthetic target accurately and keep clinical claims out.

The completed report can form the basis of a manuscript, subject to an assessment of its contribution and venue suitability. It reports evidence about one ensemble rather than introducing a new uncertainty method.

Subsequent calibration-only development is documented in [the validation analysis](m6_calibration_only_scale_validation.md). The [external lung-CT protocol](external_lung_validation_protocol.md) proposes a separate study on new data. That extension has not produced results, and none of its future findings would change the completed study's methods or outcomes.
