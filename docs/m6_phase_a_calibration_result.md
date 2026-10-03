# M6 Phase A calibration result

Phase A completed all 30 primary calibration anatomies in [run 37114827455](https://github.com/Kushrishi/truemargin/actions/runs/37114827455). The complete artifact is accepted; its exact thresholds are sealed. The 30 held-out evaluation anatomies remain unopened.

## Fitted multipliers

These dimensionless error/signal multipliers convert the corresponding signal in millimeters into a radius in millimeters. They are calibration fits, not empirical held-out coverage measurements.

| Source | Method | 80% descriptive | 90% primary | 95% sentinel |
| --- | --- | ---: | ---: | --- |
| `prostate_3t` | Sigma | 26.359594160539075 | 41.956170528034775 | Positive infinity |
| `prostate_diagnosis` | Sigma | 21.10737289132953 | 52.08147866494837 | Positive infinity |
| `prostate_3t` | ICE | Unassessable | Unassessable | Unassessable |
| `prostate_diagnosis` | ICE | 1.6803577222086956 | 2.831813657011617 | Positive infinity |

The primary sigma method completed in both sources. ICE completed 29 of 30 anatomies. Three reverse members failed from insufficient overlap in `Prostate3T-01-0013`; all nine forward members completed. The predeclared source-level failure policy makes 3T ICE calibration unassessable. The anatomy is retained, with no rerun, reinitialization, or reduced-cohort calibration.

At 15 calibration groups, the extra infinity atom has mass 1/16. A 95% threshold is therefore positive infinity under the unchanged protocol. This expected sentinel must not be replaced with a finite empirical quantile.

## Verification and retained evidence

The implementation source is `59dddf5c045b75fe9ad3bb84866ae4bdc27ce30c`, with successful source CI run `37114568122`. The request blob is `e300105b98e23b593a7d2044d965f28630b48a34`. The final ZIP SHA-256 is `e3bc6bb2b9985b1dd41777a77315953c6555a6fe2b2596c32db81c1b3ddf0c3e`; the aggregate SHA-256 is `66e926e68912ae2e4fa039f5b78194346f7dd638f32230aad0a629f135087e55`.

Verification covered the ZIP digest, 33 manifest entries, five frozen protocol/input blob pins, exactly 30 calibration records, source and request provenance, all frozen input and geometry identities, all present numeric-vector hashes, and every complete method's error/signal ratios. Zero evaluation accesses are recorded in the aggregate and all calibration shards.

An independent standard-library calculation recovered the exact thresholds: with 15 groups of 50 observations, each finite score has mass 1/800. The 80% and 90% thresholds are order statistics 640 and 720 of 750 scores; order statistic 760 lies in the infinity atom. Replaying the original aggregation helpers also reproduced every threshold and radius summary, yielding a byte-identical aggregate. This replays retained numerical evidence; it does not rerun registration.

Small numerical records, original manifests, transport receipts, and frozen protocol snapshots are retained under `results/m6_phase_a/`. Raw DICOM archives, labels, registration fields, and the large cache ZIPs are excluded from the repository. The original hosted artifact contains those workflow-local inputs and remains identified by its digest.

To verify the retained evidence without acquiring images or running registration:

```bash
python3 scripts/verify_m6_phase_a_result.py results/m6_phase_a
```

See `research/M6_PHASE_A_RESULT.json` for acceptance and provenance, and `research/M6_PHASE_A_THRESHOLD_SEAL.json` for a strict JSON seal. The string `positive_infinity` in that seal preserves the original mathematical value. The untouched aggregate uses Python JSON's `Infinity` representation and must not be silently normalized.

## Next gate and claim boundary

Phase B must consume the exact sealed thresholds, unchanged split, estimator, sampling, score, zero-signal, and failure rules. Its implementation and tests must pass source CI before a separate prospective evaluation request is committed. No further calibration rerun is needed.

Threshold fitting does not establish nominal coverage on held-out anatomies, per-anatomy guarantees, superiority over ICE, external generalization, or clinical usefulness. The M4 and M5 evidence and limitations remain unchanged. All four earlier incomplete Phase A attempts remain ineligible for aggregation.
