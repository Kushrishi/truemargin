# M6 held-out evaluation

Phase B completed on 2026-10-03 in [run 37122716790](https://github.com/Kushrishi/truemargin/actions/runs/37122716790). All 30 frozen evaluation anatomies produced complete primary sigma results. The unchanged Phase A thresholds were applied without refitting. This is a synthetic known-deformation study, not clinical validation.

## Held-out coverage and radius size

Each source contains 15 evaluation anatomies with 50 frozen ROI points per anatomy. Coverage is averaged equally across anatomies. Radius size below is the median of the 15 per-anatomy median radii; it is not a pooled-point median.

| Source | Nominal level | Empirical coverage | Coverage minus nominal | Median radius, mm |
| --- | ---: | ---: | ---: | ---: |
| Prostate-3T | 80% | 88.13% | +8.13 percentage points | 2.47 |
| Prostate-Diagnosis | 80% | 86.67% | +6.67 percentage points | 1.77 |
| Prostate-3T | 90% | 97.73% | +7.73 percentage points | 3.93 |
| Prostate-Diagnosis | 90% | 99.73% | +9.73 percentage points | 4.36 |
| Both sources, separately | 95% | 100% | +5.00 percentage points | Infinite |

The equal-source, equal-anatomy mean is 87.40% at nominal 80% and 98.73% at nominal 90%. These are empirical study summaries, not independent trials across 1,500 spatial points. Coverage above nominal does not establish precise calibration or clinical usefulness.

The raw sigma reference, radius equal to sigma without calibration, covers only 0.13% and 0.40% of the respective source points under equal-anatomy averaging. Ensemble variability is therefore not itself a numerical error bound. The sealed 90% multipliers are approximately 41.96 and 52.08; their magnitude and the conservative coverage need to remain visible.

At nominal 90%, anatomy-level coverage ranges from 88% to 100% in 3T and from 98% to 100% in Prostate-Diagnosis. The protocol does not guarantee coverage for every anatomy. Most importantly, `ProstateDx-01-0043` has a median calibrated radius of **70.69 mm**, despite a source median of 4.36 mm. Its primary result is retained. This outlier limits an efficiency or broadly useful precision claim and must not be excluded to improve summaries.

The 95% result is a finite-sample sentinel: with 15 calibration groups, the frozen HCP construction places mass 1/16 at positive infinity. The 95% quantile is therefore infinite. The resulting 100% empirical coverage is vacuous for finite-radius usefulness; no thresholds were clipped or pooled to hide this limitation.

## ICE failures remain part of the result

All nine reverse registrations completed for `ProstateDx-01-0043`, but comparator evaluation failed because a sample point lay outside the image domain. ICE is thus complete for 29 of 30 evaluation anatomies. Its Prostate-Diagnosis calibrated result is unassessable under the frozen full-cohort policy. No complete-case calibrated comparison is substituted.

3T ICE evaluation is complete, but its calibration was already unavailable after the retained Phase A failure at `Prostate3T-01-0013`. Its raw descriptive reference has 62.67% coverage and a 1.40 mm median anatomy radius. This reference is not a calibrated comparison. Neither source supports the planned full-cohort calibrated sigma-versus-ICE comparison, and no superiority claim follows.

## Evidence verification

The final ZIP is 275,266 bytes; SHA-256 is `70d7a6e7bff7f8f631de7dd85b6acba76f64fa990a3133a9be9ecedf7a8448ec`. The evaluation aggregate digest is `75680f4eaf829a7f8415025e5781fd87d405205407ab863712e47a398863ba63`.

An independent standard-library verifier checks six request-pinned blobs, 31 original manifest entries, exact frozen cohort membership, shard-reported input and geometry identities, runtime versions, every numeric vector hash and ratio score, all 30 NPZ numerical checkpoints, unchanged thresholds, coverage, radius quartiles and zero/infinite/near-zero diagnostics. It imports no experiment implementation. The original manifest covers the aggregate and JSON shards; NPZ vectors are checked separately against their JSON values, and the downloaded ZIP digest covers the whole archive.

The source-pinned aggregation implementation also reproduced the final aggregate byte for byte. This verifies aggregation and retained evidence, not an independent rerun of image decoding or registration. Raw images are not retained in this result release. Historical staging and hosted run provenance remain necessary for acquisition claims.

Reproduce the independent audit from the repository root:

```sh
python scripts/verify_m6_phase_b_result.py results/m6_phase_b
```

See [the result record](../research/M6_PHASE_B_RESULT.json) and [retained verification](../results/m6_phase_b/independent_verification.json).

## Decision after M6

M6 supports reporting conservative finite 80%/90% radii on the frozen held-out synthetic study. It does not establish accurate nominal calibration, clinical precision, finite 95% bounds, comparator superiority or external generalization. Formal HCP interpretation remains conditional on the protocol's hierarchical exchangeability and eligible-location assumptions.

Do not launch M7 or change the estimator to improve these observed results. First assemble the M4–M6 claims ledger and contribution review around the evidence actually obtained: rank informativeness, deformation-specific blind spots, and conservative or inefficient numerical bounds. A manuscript decision requires a separate novelty and scientific-value review. If that review identifies one decisive robustness question, freeze a limited M7 protocol prospectively; the 20 challenge leaderboard/test subjects remain untouched until then.
