# Pre-outcome analysis record validation

This is input-validation hardening, not an external result or protocol amendment.
No manual landmark values were opened. The frozen estimator, endpoints, case
denominator, bootstrap count/seed and comparator definitions are unchanged.

Case aggregation now rejects nonfinite/out-of-range/non-numerical correlations,
inconsistent failure statuses, malformed blind-spot counts and missing comparator
records. Explicit comparator failure remains retained rather than dropped. Zero
correlations still count as nonpositive in the ten-case one-sided sign test.
An undefined target still prevents the primary summary rather than silently
shrinking the case denominator.

Coordinate direction validation uses an absolute 1e-8 orthonormality tolerance,
without NumPy's implicit relative tolerance admitting scaled axes. Reflected
orthogonal medical-image directions remain valid; these are not confused with
proper SE(3) rotations. Existing valid coordinate conversions and trilinear
sampling calculations are unchanged.

Only synthetic arrays/records are used in tests. Authorized endpoint provenance,
operational feasibility and a complete pre-outcome freeze remain required before
external landmark access. **HELD-OUT ACCESS SAFE: NO.**
