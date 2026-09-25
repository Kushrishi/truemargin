"""
truemargin
==========
Calibrated uncertainty for image registration, applied to mapping a pathology
finding (positive cancer margin) back onto a patient's pre-op scan.

The reusable core is `truemargin.calibration`: given a registration method's
estimated displacement, the true displacement, and a predicted per-point
uncertainty, it answers whether the stated confidence is empirically honest,
and can recalibrate it if not. Everything else in this package (`synthetic`,
`registration`, `io_utils`, `metrics`) exists to feed real or toy data into
that one module -- the calibration harness itself never changes.

Not a medical device. Research use on public/synthetic data only.
"""

__version__ = "0.1.0"
