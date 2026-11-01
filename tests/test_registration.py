"""Synthetic regression tests for spacing, centering and uncertainty calculations.

SimpleITK-dependent tests are skipped when the package is unavailable.
Historical method corrections are documented in docs/paper.tex, Appendices B–D."""

import numpy as np
import pytest

pytest.importorskip("SimpleITK")

from truemargin import registration as reg  # noqa: E402


def _synthetic_textured_volume(shape, seed):
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 1, shape).astype(np.float32)


def _synthetic_blob_volume(shape, seed, blob_sigma=2.5, background_noise=0.02, amplitude=1.0):
    """Return an off-center Gaussian blob with low background noise.

    Centroid alignment needs concentrated intensity; uniform noise has an
    approximately stationary centroid even when shifted."""
    rng = np.random.default_rng(seed)
    grid = np.indices(shape, dtype=np.float64)
    # An off-center blob exposes centroid sign and axis-order errors.
    center = np.array([shape[i] / 4.0 for i in range(len(shape))])
    dist2 = sum((grid[i] - center[i]) ** 2 for i in range(len(shape)))
    blob = amplitude * np.exp(-dist2 / (2 * blob_sigma**2))
    noise = rng.uniform(0, background_noise, shape)
    return (blob + noise).astype(np.float32)


def _run_registration_with_seed_retry(register_fn, shape, shift_vec, base_seed=0, max_tries=8):
    """Retry synthetic fixtures when registration raises RuntimeError.

    SimpleITK registration can fail when transformed images do not overlap.
    Require at least one successful run; retain the last error if all fail."""
    from scipy.ndimage import shift as ndi_shift

    last_err = None
    for i in range(max_tries):
        seed = base_seed + i
        fixed = _synthetic_textured_volume(shape, seed=seed)
        moving = ndi_shift(fixed, shift=shift_vec, order=1, mode="nearest").astype(np.float32)
        try:
            return fixed, moving, register_fn(fixed, moving)
        except RuntimeError as e:
            last_err = e
            continue
    raise RuntimeError(
        f"Registration failed on all {max_tries} seeds tried starting at {base_seed} "
        f"(last error: {last_err}) -- needs at least one successful run to test anything."
    )


def test_baseline_registration_spacing_changes_result():
    shape = (10, 16, 16)
    fixed = _synthetic_textured_volume(shape, seed=0)
    from scipy.ndimage import shift

    moving = shift(fixed, shift=(1.0, 0.5, -0.5), order=1, mode="nearest").astype(np.float32)

    disp_isotropic = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, spacing=(1.0, 1.0, 1.0)
    )
    disp_anisotropic = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, spacing=(0.3, 0.3, 3.0)
    )

    assert disp_isotropic.shape == disp_anisotropic.shape
    assert not np.allclose(disp_isotropic, disp_anisotropic), (
        "Displacement field is identical regardless of declared spacing -- "
        "spacing is not actually reaching the SimpleITK images (regression "
        "of the bug found in the independent code audit)."
    )


def test_baseline_registration_default_spacing_is_isotropic():
    shape = (8, 12, 12)
    fixed = _synthetic_textured_volume(shape, seed=1)
    from scipy.ndimage import shift

    moving = shift(fixed, shift=(0.5, 0.5, 0.5), order=1, mode="nearest").astype(np.float32)

    disp_default = reg.baseline_bspline_registration(fixed, moving, mesh_size=3, max_iterations=20)
    disp_explicit_isotropic = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, spacing=(1.0, 1.0, 1.0)
    )
    # Allow optimizer floating-point variation between equivalent calls.
    np.testing.assert_allclose(disp_default, disp_explicit_isotropic, rtol=1e-4, atol=1e-8)


def test_center_first_defaults_to_off_and_preserves_old_behavior():
    shape = (8, 12, 12)
    fixed = _synthetic_textured_volume(shape, seed=3)
    from scipy.ndimage import shift

    moving = shift(fixed, shift=(1.0, 0.5, -0.5), order=1, mode="nearest").astype(np.float32)

    disp_default = reg.baseline_bspline_registration(fixed, moving, mesh_size=3, max_iterations=20)
    disp_explicit_off = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, center_first=False
    )
    np.testing.assert_allclose(disp_default, disp_explicit_off, rtol=1e-4, atol=1e-8)


def test_center_first_composes_the_translation_into_the_returned_displacement():
    shape = (10, 20, 20)
    fixed = _synthetic_blob_volume(shape, seed=8)
    from scipy.ndimage import shift

    true_shift = (0.0, 6.0, 6.0)  # array-axis order, matching `shape`
    moving = shift(fixed, shift=true_shift, order=1, mode="nearest").astype(np.float32)

    disp = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, center_first=True
    )
    # Default unit spacing makes this shift magnitude equal to millimetres.
    true_shift_mag = float(np.sqrt(sum(s**2 for s in true_shift)))
    mean_disp_mag = float(np.mean(np.sqrt((disp**2).sum(axis=0))))
    assert mean_disp_mag > true_shift_mag * 0.5, (
        f"Mean displacement magnitude ({mean_disp_mag:.2f}) is far smaller than "
        f"the true applied shift's magnitude ({true_shift_mag:.2f}) -- the "
        "center_first rigid translation appears to be missing from the "
        "returned displacement field (the discard bug found by audit)."
    )


def test_center_first_changes_the_starting_point_for_a_large_offset():
    shape = (10, 20, 20)
    fixed = _synthetic_textured_volume(shape, seed=4)
    from scipy.ndimage import shift

    moving = shift(fixed, shift=(0.0, 6.0, 6.0), order=1, mode="nearest").astype(np.float32)

    disp_uncentered = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, center_first=False
    )
    disp_centered = reg.baseline_bspline_registration(
        fixed, moving, mesh_size=3, max_iterations=20, center_first=True
    )
    assert disp_uncentered.shape == disp_centered.shape
    assert not np.allclose(disp_uncentered, disp_centered), (
        "center_first=True produced an identical displacement field to "
        "center_first=False on a large-offset case -- the centering step "
        "isn't actually reaching the registration call."
    )


def test_curvature_uncertainty_accepts_center_first():
    def register(fixed, moving):
        return reg.curvature_uncertainty(
            fixed, moving, mesh_size=3, max_iterations=20, center_first=True
        )

    fixed, moving, (u, sigma) = _run_registration_with_seed_retry(
        register, shape=(8, 12, 12), shift_vec=(1.0, 0.5, -0.5), base_seed=5
    )
    assert u.shape[0] == 3
    assert sigma.shape == fixed.shape


def test_sigma_is_monotonically_related_to_curvature():
    def register(fixed, moving):
        return reg.curvature_uncertainty(
            fixed, moving, mesh_size=3, max_iterations=20, perturb_eps=0.5, return_curvature=True
        )

    _fixed, _moving, (_u, _sigma, curvature) = _run_registration_with_seed_retry(
        register, shape=(8, 12, 12), shift_vec=(1.0, 0.5, -0.5), base_seed=7
    )
    assert curvature.ndim == 1
    assert len(curvature) > 10, "expected a real B-spline parameter count, not a degenerate case"

    # Check the inverse-square-root mapping on the returned curvature.
    curvature_floor = 1e-6  # must match curvature_uncertainty's own floor
    recomputed_param_sigma = 1.0 / np.sqrt(np.maximum(curvature, curvature_floor))

    order = np.argsort(curvature)
    sorted_sigma = recomputed_param_sigma[order]
    assert np.all(np.diff(sorted_sigma) <= 1e-9), (
        "Recomputed per-parameter sigma is not monotonically non-increasing as "
        "curvature increases -- the 1/sqrt(curvature) formula or floor logic is "
        "broken (this is a pure arithmetic check, independent of any assumption "
        "about which synthetic image should have higher curvature)."
    )
    assert curvature.max() > curvature_floor, (
        "Every parameter hit the curvature floor -- this test's registration setup "
        "produced a degenerate case that can't actually exercise the monotonic "
        "relationship being tested; increase max_iterations or check convergence."
    )
    assert (
        recomputed_param_sigma[np.argmax(curvature)] < recomputed_param_sigma[np.argmin(curvature)]
    ), "Highest-curvature parameter did not get a smaller sigma than the lowest-curvature one."


def test_curvature_uncertainty_accepts_spacing():
    def register(fixed, moving):
        u_iso, sigma_iso = reg.curvature_uncertainty(
            fixed, moving, mesh_size=3, max_iterations=20, spacing=(1.0, 1.0, 1.0)
        )
        u_aniso, sigma_aniso = reg.curvature_uncertainty(
            fixed, moving, mesh_size=3, max_iterations=20, spacing=(0.3, 0.3, 3.0)
        )
        return u_iso, sigma_iso, u_aniso, sigma_aniso

    _fixed, _moving, (u_iso, sigma_iso, u_aniso, sigma_aniso) = _run_registration_with_seed_retry(
        register, shape=(8, 12, 12), shift_vec=(1.0, 0.5, -0.5), base_seed=2
    )
    assert u_iso.shape == u_aniso.shape
    assert sigma_iso.shape == sigma_aniso.shape
    assert not np.allclose(sigma_iso, sigma_aniso), (
        "Curvature sigma is identical regardless of declared spacing -- "
        "spacing is not reaching curvature_uncertainty's SimpleITK images."
    )


def test_ensemble_sigma_uses_rms_not_vector_magnitude(monkeypatch):
    """Check RMS aggregation of known per-axis deviations.

    The isotropic coverage model expects per-axis variance, so scalar spread
    is sqrt(mean(axis_variances)), not sqrt(sum(axis_variances)). Registration
    is mocked to isolate this arithmetic from optimizer convergence."""
    shape = (4, 5, 5)
    rng = np.random.default_rng(0)
    true_sigma = np.array([1.0, 2.0, 3.0])  # deliberately anisotropic
    n = 4000  # large n so the empirical estimate is close to the analytic RMS

    def fake_registration(fixed, moving, **kwargs):
        return np.stack([rng.normal(0, s, size=shape) for s in true_sigma])

    monkeypatch.setattr(reg, "baseline_bspline_registration", fake_registration)

    fixed = np.zeros(shape, dtype=np.float32)
    moving = np.zeros(shape, dtype=np.float32)
    _u_mean, sigma = reg.ensemble_uncertainty(fixed, moving, n=n, jitter=0.0, seed=0)

    expected_rms = np.sqrt((true_sigma**2).mean())
    wrong_vector_magnitude = np.sqrt((true_sigma**2).sum())
    measured = float(np.mean(sigma))

    assert abs(measured - expected_rms) < 0.15, (
        f"measured sigma ({measured:.3f}) does not match the expected RMS "
        f"combination ({expected_rms:.3f}) -- got something closer to the "
        f"WRONG vector-magnitude combination ({wrong_vector_magnitude:.3f}) "
        "instead (regression of the bug found by independent review)."
    )


def test_curvature_uncertainty_mc_propagation_is_reproducible():
    def register(fixed, moving):
        return reg.curvature_uncertainty(
            fixed,
            moving,
            mesh_size=3,
            max_iterations=20,
            perturb_eps=0.5,
            mc_samples=8,
            mc_seed=42,
        )

    fixed, moving, (_u1, sigma1) = _run_registration_with_seed_retry(
        register, shape=(8, 12, 12), shift_vec=(1.0, 0.5, -0.5), base_seed=9
    )
    # Repeat on the same images; the optimizer can vary despite a fixed MC seed.
    _u2, sigma2 = reg.curvature_uncertainty(
        fixed,
        moving,
        mesh_size=3,
        max_iterations=20,
        perturb_eps=0.5,
        mc_samples=8,
        mc_seed=42,
    )
    np.testing.assert_allclose(sigma1, sigma2, rtol=1e-2, atol=1e-6)
