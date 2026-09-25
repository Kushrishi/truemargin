"""Extra geometric checks for the real-data path (context, not the moat)."""

from __future__ import annotations

import numpy as np


def dice(a: np.ndarray, b: np.ndarray) -> float:
    """Overlap of two binary masks (e.g., predicted vs true cancer region). 1 = perfect."""
    a = a.astype(bool)
    b = b.astype(bool)
    denom = a.sum() + b.sum()
    return 1.0 if denom == 0 else float(2 * (a & b).sum() / denom)


def jacobian_determinant(disp: np.ndarray) -> np.ndarray:
    """Jacobian determinant of a 2D/3D displacement field (D, ...).
    Values <= 0 mean the warp folds tissue through itself (physically impossible).

    Found via independent adversarial audit (this function was previously
    unused anywhere in the repo, which is exactly how this went undetected --
    no test or caller ever exercised it): the diagonal/off-diagonal partial
    derivatives were paired up wrong, computing
    (1+dA/dx)(1+dB/dy) - (dA/dy)(dB/dx) instead of the correct
    (1+dA/dy)(1+dB/dx) - (dA/dx)(dB/dy), where A=disp[0] (the row/y
    displacement component, per synthetic.py's warp: `ys + disp[0]`) and
    B=disp[1] (the column/x component). These are NOT algebraically
    equivalent for an anisotropic field -- confirmed with a closed-form
    counterexample: a pure "stretch" field A = 1*y (B=0) has a true Jacobian
    of exactly 2.0 everywhere, but the old formula returned 1.0, completely
    missing the area doubling.
    """
    if disp.shape[0] == 2:
        dA_dy, dA_dx = np.gradient(disp[0])  # A = disp[0], the y/row displacement component
        dB_dy, dB_dx = np.gradient(disp[1])  # B = disp[1], the x/column displacement component
        j = (1 + dA_dy) * (1 + dB_dx) - dA_dx * dB_dy
        return j
    raise NotImplementedError("3D Jacobian: extend as needed.")


def fraction_folded(disp: np.ndarray) -> float:
    """Fraction of the field where the warp folds (a registration-quality red flag)."""
    j = jacobian_determinant(disp)
    return float(np.mean(j <= 0))
