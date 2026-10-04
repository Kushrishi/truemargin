# Calibration-only scale development validation

This analysis asks whether the post-study affine error scale is worth carrying
into a fresh validation study. It uses only the original 30 Phase-A calibration
anatomies. The previously observed Phase-B evaluation records are not read.

For each source, every calibration anatomy is held out once. Of the remaining
14 anatomies, the first four in the predeclared SHA-256 patient-ID order fit the
nonnegative affine scale; the remaining ten fit the nominal-90% multiplier.
The held-out anatomy is then evaluated. Constant, spread-only, affine, and
feasible inverse-consistency-error (ICE) scales use the same held-out fold.

The 15 folds overlap heavily, so these are development summaries rather than
independent confirmatory estimates.

## Result

| Source | Scale | Mean coverage | Mean radius |
| --- | --- | ---: | ---: |
| Prostate-3T | constant | 96.8% | 2.31 mm |
| Prostate-3T | spread | 99.1% | 5.45 mm |
| Prostate-3T | affine | 98.0% | 2.66 mm |
| Prostate-Diagnosis | constant | 98.9% | 4.01 mm |
| Prostate-Diagnosis | spread | 93.1% | 9.00 mm |
| Prostate-Diagnosis | affine | 95.5% | 3.15 mm |
| Prostate-Diagnosis | ICE | 98.7% | 5.81 mm |

ICE is not fully assessable for the Prostate-3T folds because the retained
incomplete ICE anatomy is always present in either the held-out or multiplier
set under this fixed design.

## Interpretation

The affine scale does not show a uniform advantage.

For Prostate-3T, a simple constant radius is smaller on average than the affine
radius while both exceed nominal coverage in these overlapping development
folds. For Prostate-Diagnosis, the affine scale is smaller than the constant
radius and still exceeds 90% mean coverage, but the difference is source-specific.

Spread-only scaling is inefficient in both sources and particularly unstable in
the Diagnosis cohort.

This result does not change M6. It argues against a paper claim that adaptive
scaling is already superior. A fresh study, if pursued, should instead test the
source-dependent question prospectively: under what conditions does an adaptive
scale improve the coverage/radius tradeoff over a constant radius and ICE?

Run the retained-data analysis with:

```bash
python scripts/m6_calibration_only_scale_validation.py .
```
