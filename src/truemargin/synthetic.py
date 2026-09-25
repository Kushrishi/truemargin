"""
synthetic.py
------------
Generate a controlled toy world where we KNOW the true deformation, so we can test
the calibration harness before touching any real data (no TCIA download needed).

Pipeline mirrors the real one in miniature:
  fixed image  --(known smooth deformation)-->  moving image
  an 'estimator' recovers the deformation imperfectly, and ALSO emits a predicted
  per-pixel uncertainty sigma. We then ask whether that sigma is honest (calibrated).

Swap this module out for real SimpleITK/elastix/ProsRegNet output later; everything
downstream (calibration.py) stays identical.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter


def make_phantom(shape=(256, 256), n_blobs=40, seed=0) -> np.ndarray:
    """A smooth random 'tissue-like' intensity image."""
    rng = np.random.default_rng(seed)
    img = np.zeros(shape, dtype=np.float64)
    ys, xs = np.mgrid[0 : shape[0], 0 : shape[1]]
    for _ in range(n_blobs):
        cy, cx = rng.uniform(0, shape[0]), rng.uniform(0, shape[1])
        r = rng.uniform(8, 40)
        amp = rng.uniform(0.3, 1.0)
        img += amp * np.exp(-((ys - cy) ** 2 + (xs - cx) ** 2) / (2 * r**2))
    img = (img - img.min()) / (np.ptp(img) + 1e-9)
    return img


def make_true_deformation(shape=(256, 256), max_disp=12.0, smoothness=30.0, seed=1):
    """A smooth, spatially-varying ground-truth displacement field, shape (2, H, W) in pixels.

    Larger displacement toward one region -> mimics tissue that deforms unevenly,
    which is exactly where uncertainty SHOULD grow.
    """
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((2,) + shape)
    field = np.stack([gaussian_filter(raw[i], smoothness) for i in range(2)])
    field /= np.abs(field).max() + 1e-9
    # make the deformation stronger on the right half (a controllable 'hard region')
    ramp = np.linspace(0.3, 1.0, shape[1])[None, None, :]
    field = field * ramp * max_disp
    return field  # (2, H, W)


def warp(image: np.ndarray, disp: np.ndarray) -> np.ndarray:
    """Apply displacement field (2, H, W) to an image via linear interpolation."""
    from scipy.ndimage import map_coordinates

    ys, xs = np.mgrid[0 : image.shape[0], 0 : image.shape[1]].astype(np.float64)
    coords = np.stack([ys + disp[0], xs + disp[1]])
    return map_coordinates(image, coords, order=1, mode="reflect")


def fake_estimator(u_true: np.ndarray, seed=2, overconfidence=2.2):
    """Simulate a registration method that is (a) imperfect and (b) OVERCONFIDENT.

    Returns:
        u_est : estimated displacement (2, H, W)
        sigma : predicted per-pixel uncertainty (H, W)  -- deliberately too small

    The true error grows where deformation is large; the predicted sigma only
    partly tracks it AND is scaled down by `overconfidence`. This reproduces the
    real-world finding: registration uncertainty is systematically overconfident.
    """
    rng = np.random.default_rng(seed)
    disp_mag = np.sqrt(u_true[0] ** 2 + u_true[1] ** 2)
    # actual error scales with local deformation magnitude (+ a floor)
    true_err_scale = 0.10 * disp_mag + 0.4
    err = rng.standard_normal(u_true.shape) * true_err_scale[None]
    u_est = u_true + err
    # the model's PREDICTED sigma: correlated with, but not equal to, reality,
    # and shrunk by `overconfidence` -> miscalibrated on purpose.
    sigma_pred = (true_err_scale * (0.7 + 0.3 * rng.random(true_err_scale.shape))) / overconfidence
    return u_est, sigma_pred
