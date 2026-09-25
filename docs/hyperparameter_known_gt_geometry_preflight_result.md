# Hyperparameter known-GT geometry preflight result

**Date:** 2026-09-25  
**Workflow run:** `36167535578`  
**Source revision:** `bcd7099bca8d37f9f895227c386503610639bd03`  
**Mode:** geometry only  
**Estimator registrations run:** **0**  
**Result:** **FAIL — 29/30 cases passed geometry**

## Acquisition

The hosted run successfully acquired the full frozen input set before geometry:

- IDC release: `v24`
- `idc-index`: `0.12.5`
- frozen T2 series resolved/downloaded: `10/10`
- frozen HECaP masks resolved: `10/10`

The run used the ten full DICOM identities frozen in
`research/KNOWN_GT_SERIES_IDENTITY.json`.

## Geometry result

The frozen coefficient standard deviation was `4.0`, with the original
30-case anatomy/replicate seed schedule.

| Anatomy | Replicate | Seed | Minimum Jacobian | Landmark true-displacement median (mm) | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| aaa0044 | 0 | 0 | 0.438255 | 1.67839 | PASS |
| aaa0044 | 1 | 1 | 0.400411 | 2.41449 | PASS |
| aaa0044 | 2 | 2 | 0.471834 | 1.70853 | PASS |
| aaa0051 | 0 | 1000 | 0.486959 | 1.91805 | PASS |
| aaa0051 | 1 | 1001 | 0.350206 | 1.38980 | PASS |
| aaa0051 | 2 | 1002 | 0.499027 | 2.68231 | PASS |
| aaa0053 | 0 | 2000 | 0.375271 | 3.79740 | PASS |
| aaa0053 | 1 | 2001 | 0.373106 | 2.49707 | PASS |
| aaa0053 | 2 | 2002 | 0.446422 | 2.60095 | PASS |
| aaa0060 | 0 | 3000 | 0.308114 | 1.53464 | PASS |
| aaa0060 | 1 | 3001 | 0.125223 | 1.49887 | PASS |
| aaa0060 | 2 | 3002 | 0.364901 | 3.26200 | PASS |
| aaa0064 | 0 | 4000 | 0.519868 | 2.76545 | PASS |
| aaa0064 | 1 | 4001 | 0.413526 | 2.85817 | PASS |
| aaa0064 | 2 | 4002 | 0.490459 | 1.49744 | PASS |
| aaa0069 | 0 | 5000 | 0.415454 | 2.77054 | PASS |
| aaa0069 | 1 | 5001 | 0.446185 | 3.80497 | PASS |
| aaa0069 | 2 | 5002 | 0.489182 | 2.01278 | PASS |
| aaa0071 | 0 | 6000 | 0.464669 | 1.55842 | PASS |
| aaa0071 | 1 | 6001 | 0.371567 | 3.82376 | PASS |
| aaa0071 | 2 | 6002 | 0.407949 | 2.01969 | PASS |
| aaa0072 | 0 | 7000 | 0.233584 | 3.56028 | PASS |
| aaa0072 | 1 | 7001 | **-0.0105857** | — | **FAIL: folding** |
| aaa0072 | 2 | 7002 | 0.135181 | 2.69649 | PASS |
| aaa0086 | 0 | 8000 | 0.419103 | 3.19006 | PASS |
| aaa0086 | 1 | 8001 | 0.360546 | 2.29673 | PASS |
| aaa0086 | 2 | 8002 | 0.547571 | 2.07962 | PASS |
| aaa0087 | 0 | 9000 | 0.486962 | 1.03363 | PASS |
| aaa0087 | 1 | 9001 | 0.617888 | 1.25679 | PASS |
| aaa0087 | 2 | 9002 | 0.437808 | 1.95041 | PASS |

The only failed case was `aaa0072 / replicate 1 / seed 7001`. Its minimum
displacement-field Jacobian determinant was `-0.0105857`, violating the
prospective requirement that the Jacobian remain strictly positive throughout
the evaluated crop grid.

## Interpretation boundary

This is a geometry result, not an uncertainty-estimator result.

The workflow stopped immediately after the geometry preflight and before any of
the planned 270 hyperparameter-ensemble registrations. No sigma/error
association, calibration, blind-spot, or estimator-member outcome existed when
the failure was observed.

The failed seed is not substituted and the anatomy is not dropped. Any change
to the synthetic generator must be made through a prospective amendment that is
frozen before another geometry calibration or any estimator execution.
