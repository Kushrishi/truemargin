import numpy as np
import pytest

from truemargin.registration import baseline_bspline_registration


def test_observer_preserves_registration_output():
    pytest.importorskip("SimpleITK")
    rng = np.random.default_rng(41)
    fixed = rng.normal(size=(12, 12)).astype(np.float32)
    moving = np.roll(fixed, 1, axis=0)
    events = []
    kwargs = dict(mesh_size=2, max_iterations=2, metric_bins=16)
    plain = baseline_bspline_registration(fixed, moving, **kwargs)
    observed = baseline_bspline_registration(
        fixed, moving, progress_callback=lambda i, m: events.append((i, m)), **kwargs
    )
    # ITK multithreaded reductions need not be byte-identical across calls.
    np.testing.assert_allclose(plain, observed, rtol=1e-12, atol=1e-12)
    assert events and all(np.isfinite(m) for _, m in events)
