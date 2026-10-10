# Results

Only compact, reviewed scientific evidence belongs here.

Raw images and transient registration state remain outside Git. Durable result records identify
their protocol, source revision, configuration, provenance, and interpretation boundary.

## Known-ground-truth geometry preflight

The reviewed Amendment-2 geometry-only preflight passed **30 / 30** cases.

Permanent evidence:

- `hyperparameter_known_gt_geometry_preflight.md` — concise reviewed result and interpretation
  boundary;
- `hyperparameter_known_gt_geometry_preflight.json` — complete 30-case geometry record recovered
  from the successful hosted run;
- `known_gt_data_acquisition.json` — frozen-series and HECaP acquisition provenance.

These files contain no result-bearing uncertainty-vs-error outcome.

## M5 frozen-output characterization

`m5/` contains the post-primary descriptive characterization of the completed M4 study.

Permanent evidence:

- `m5_sigma_blind_spots.csv` — the 39 target-sigma blind-spot locations reconstructed from the ten
  verified patient shard artifacts;
- `m5_case_characterization.csv` — all 30 deformation-specific cases;
- `m5_case_failure_table.csv` — cases with a target blind spot, negative target rank association,
  non-positive quartile enrichment, or method-invalid comparator;
- `m5_anatomy_comparator_table.csv` — target/comparator anatomy summaries.

The analysis uses only frozen M4 outputs. Its CLI reconstructs the complete 1,500-location
pointwise state in memory and generates anatomy-comparator and case-heterogeneity SVG figures in
the requested output directory. Those larger derived outputs are intentionally not versioned. The
analysis does not rerun registration, retune the estimator, change the ROI, or add a new
confirmatory hypothesis test.

## Calibration and evaluation

- `m6_phase_a/`: calibration bundle, frozen input/geometry identities, protocol
  copies, patient shards and aggregate thresholds.
- `m6_phase_b/`: sealed-threshold evaluation bundle, numeric point records,
  identities, protocol copies and aggregate coverage/radius summaries.
- `m6_exploratory/`: explicitly post-primary comparisons and failure analysis.
  These are not additional confirmatory studies.

Use the [saved-evidence verification commands](../docs/reproduction.md) before
relying on the bundles. M4–M6 are historical study identifiers, explained in the
[research guide](../research/README.md).
