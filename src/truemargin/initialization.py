"""B-spline initialization-sensitivity helpers.

This module implements the mechanism frozen in
``docs/initialization_ensemble_protocol.md``. It deliberately leaves the existing
registration baseline untouched: calls without an explicit parameter vector delegate
straight to :func:`baseline_bspline_registration`, while the initialized path mirrors
that baseline with only the B-spline starting coefficients changed.

The resulting ensemble is an optimization-start sensitivity analysis, not a Bayesian
posterior or a model of scanner noise.
"""

from __future__ import annotations

import numpy as np

from truemargin.registration import _center_moving_on_fixed, baseline_bspline_registration


def initialization_parameters(
    n_parameters: int,
    *,
    delta_mm: float,
    patient_index: int,
    member_index: int,
    base_seed: int = 0,
) -> np.ndarray:
    """Return one deterministic coefficient-perturbation vector.

    The seed depends only on ``base_seed``, patient identity, and member identity,
    never on perturbation strength. Therefore the same patient/member uses the same
    coefficient-space direction for every ``delta_mm`` and later ensemble-size
    studies are prefix nested by member index.
    """
    if n_parameters < 1:
        raise ValueError("n_parameters must be at least 1")
    delta = float(delta_mm)
    if not np.isfinite(delta) or delta < 0:
        raise ValueError("delta_mm must be finite and non-negative")
    if patient_index < 0 or member_index < 0 or base_seed < 0:
        raise ValueError("seed components must be non-negative integers")

    seed_sequence = np.random.SeedSequence([base_seed, patient_index, member_index])
    rng = np.random.default_rng(seed_sequence)
    direction = rng.uniform(-1.0, 1.0, size=n_parameters)
    return direction * delta


def _validated_initial_parameters(
    initial_parameters: np.ndarray,
    *,
    expected_size: int,
) -> np.ndarray:
    params = np.asarray(initial_parameters, dtype=np.float64)
    if params.ndim != 1:
        raise ValueError("initial_parameters must be a one-dimensional vector")
    if len(params) != expected_size:
        raise ValueError(f"initial_parameters has length {len(params)}, expected {expected_size}")
    if not np.isfinite(params).all():
        raise ValueError("initial_parameters must contain only finite values")
    return params


def bspline_parameter_count(
    fixed: np.ndarray,
    *,
    mesh_size: int,
    spacing: tuple[float, ...] | None = None,
) -> int:
    """Return SimpleITK's actual B-spline parameter count for this image/grid."""
    try:
        import SimpleITK as sitk
    except ImportError as exc:
        raise ImportError("SimpleITK is required for B-spline initialization") from exc

    fixed_image = sitk.GetImageFromArray(fixed.astype(np.float32))
    if spacing is not None:
        fixed_image.SetSpacing(spacing)
    mesh = [mesh_size] * fixed_image.GetDimension()
    transform = sitk.BSplineTransformInitializer(fixed_image, mesh)
    return len(transform.GetParameters())


def initialized_bspline_registration(
    fixed: np.ndarray,
    moving: np.ndarray,
    *,
    mesh_size: int = 8,
    max_iterations: int = 100,
    spacing: tuple[float, ...] | None = None,
    center_first: bool = False,
    initial_parameters: np.ndarray | None = None,
) -> np.ndarray:
    """Run the baseline B-spline registration from an optional explicit start.

    ``initial_parameters=None`` delegates directly to the existing baseline so the
    historical zero-initialization path is not reimplemented or silently changed.
    A validated all-zero vector also delegates to that exact path, which makes the
    frozen ``delta_mm=0`` repeatability floor a measurement of the existing baseline.
    Nonzero vectors change only the initial B-spline coefficients before optimization.
    """
    if initial_parameters is None:
        return baseline_bspline_registration(
            fixed,
            moving,
            mesh_size=mesh_size,
            max_iterations=max_iterations,
            spacing=spacing,
            center_first=center_first,
        )

    try:
        import SimpleITK as sitk
    except ImportError as exc:
        raise ImportError("SimpleITK is required for B-spline initialization") from exc

    fixed_image = sitk.GetImageFromArray(fixed.astype(np.float32))
    moving_image = sitk.GetImageFromArray(moving.astype(np.float32))
    if spacing is not None:
        fixed_image.SetSpacing(spacing)
        moving_image.SetSpacing(spacing)

    mesh = [mesh_size] * fixed_image.GetDimension()
    transform = sitk.BSplineTransformInitializer(fixed_image, mesh)
    params = _validated_initial_parameters(
        initial_parameters,
        expected_size=len(transform.GetParameters()),
    )
    if not np.any(params):
        return baseline_bspline_registration(
            fixed,
            moving,
            mesh_size=mesh_size,
            max_iterations=max_iterations,
            spacing=spacing,
            center_first=center_first,
        )

    centering_offset = None
    if center_first:
        moving_image, centering_transform = _center_moving_on_fixed(
            fixed_image,
            moving_image,
            sitk,
        )
        centering_offset = np.asarray(centering_transform.GetOffset(), dtype=np.float64)

    transform.SetParameters(tuple(float(value) for value in params))

    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMattesMutualInformation(50)
    registration.SetOptimizerAsLBFGSB(
        gradientConvergenceTolerance=1e-5,
        numberOfIterations=max_iterations,
    )
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetInitialTransform(transform, inPlace=True)
    registration.Execute(fixed_image, moving_image)

    displacement_filter = sitk.TransformToDisplacementFieldFilter()
    displacement_filter.SetReferenceImage(fixed_image)
    displacement = sitk.GetArrayFromImage(displacement_filter.Execute(transform))
    if centering_offset is not None:
        displacement = displacement + centering_offset
    return np.moveaxis(displacement, -1, 0)
