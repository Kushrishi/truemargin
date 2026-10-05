# Research roadmap

**Updated:** October 5, 2026

## Completed work

- **Known-error study:** 30 synthetic cases across 10 anatomies. All anatomy-level correlations were positive; median Spearman correlation was 0.6841. An advantage over inverse-consistency error was not established.
- **Failure analysis:** 6 of 30 case-level correlations were negative. There were 39 high-error, low-uncertainty observations among 1,500 sampled locations.
- **Held-out calibration:** 30 calibration and 30 evaluation anatomies across two acquisition sources. At nominal 90% coverage, mean anatomy-level coverage was 97.73% and 99.73%, with median radii of 3.93 mm and 4.36 mm. One anatomy reached 70.69 mm. The 95% thresholds were infinite; incomplete inverse-consistency results prevented the full-cohort calibrated comparison.
- **Calibration-only scale analysis:** constant and adaptive scales traded radius size differently across sources. Adaptation did not provide a uniform improvement, and these development folds are not independent confirmation.
- **Technical report:** methods, findings and limits are summarized in [the report](../docs/technical_report.md).

## Next study: external lung CT landmarks

The [external-study protocol](../docs/external_lung_validation_protocol.md) and training-image preflight are implemented. The experiment has not run.

Before execution, reconcile the dataset partition and expected pair count with the protocol, verify image and landmark identities, and confirm that coordinate conventions and eligibility checks are correct. Then test the fixed estimator and comparators on eligible landmark pairs. Report registration failures and missing observations alongside rank associations and error distributions.

This study asks whether the signal remains informative outside the original prostate-image setting. It does not establish clinical usefulness by itself. Any amendment to the external design must be recorded before inspecting estimator outcomes.

## Publication

The existing technical report provides a starting point. An external result could strengthen a comparative paper if it adds a clear finding beyond existing work. The contribution may concern limits or failure patterns rather than a superior uncertainty method. A manuscript or preprint has not been completed.

The original challenge leaderboard and test subjects remain untouched. They come from the same challenge and are not an independent external dataset.

## Research records

Frozen protocols, amendments and numerical result records retain the definitions used in each completed study. They are not changed to improve a later result. The [claims summary](CLAIMS.md) describes what the current evidence supports. The private `truemargin-lab` repository preserves historical work; active research is maintained here.
