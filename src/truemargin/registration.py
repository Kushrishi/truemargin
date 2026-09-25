"""
registration.py
---------------
Real-data registration lives here. On synthetic data you don't need this
(synthetic.py already gives you an estimator). For the TCIA prostate step you
plug a real method in and it hands its displacement field to calibration.py.

Requires SimpleITK (pip install SimpleITK) for the baseline. ProsRegNet / RAPHIA /
RAPSODI (Stanford PIMED, on GitHub) are the deep-learning upgrades -- wrap them here.
"""

from __future__ import annotations

import numpy as np


def _center_moving_on_fixed(f, m, sitk):
    """Rigidly translate `m` so its intensity-weighted centroid (center of
    mass of the actual image CONTENT) lines up with `f`'s, before any
    B-spline optimization starts.

    Why this exists: found while debugging a real crash on patient aaa0051
    (scripts/08_curvature_vs_ensemble.py, see docs/roadmap.md) --
    "MattesMutualInformationImageToImageMetricv4: All samples map outside
    moving image buffer. The images do not sufficiently overlap." This error
    was shown (via scripts/_debug_aaa0051_overlap.py) to be STOCHASTIC: the
    exact same registration call, run multiple times on the same patient's
    same crop, sometimes converges fine and sometimes fails. That points to
    the multi-threaded LBFGSB optimizer occasionally wandering far enough
    during its search that the transform pushes sampled points entirely
    outside the moving image's valid region -- more likely when the fixed
    and moving crops aren't well-aligned to begin with, so translation and
    deformation both have to be found from scratch simultaneously.

    ITK's own error message suggests the fix directly: "you can align the
    image centers by translation." That's exactly what this does -- a cheap,
    deterministic rigid pre-alignment step so the B-spline optimizer starts
    much closer to a valid overlap and has a much smaller/easier basin to
    search, rather than being asked to discover a possibly-large translation
    purely through 1500+ free deformation parameters.

    Returns the translated moving image (resampled onto f's grid) plus the
    translation transform used, in case a caller wants to compose it back in.

    Implementation history -- two real bugs found here by actually running
    the test suite, not just reading the code, worth recording:
    1. An earlier version used sitk.CenteredTransformInitializer with a
       TranslationTransform, which THROWS at runtime ("Error converting
       input transform to required transform type with center") --
       CenteredTransformInitializer requires a transform with a
       center-of-rotation parameter (Euler, Similarity, Affine); a pure
       translation has none. Fixed by computing the offset directly instead.
    2. The direct-computation fix that replaced it used each image's
       GEOMETRIC grid center (half the voxel size along each axis) rather
       than its CONTENT. Since every image in this codebase is built via
       sitk.GetImageFromArray with no origin set, fixed and moving always
       get an IDENTICAL default origin and (after cropping/resampling onto
       the same grid) identical size and spacing -- meaning their geometric
       centers are ALWAYS the same point regardless of what the pixel
       content actually looks like. This made "centering" a complete no-op
       whenever the two images share a grid but differ only in content (the
       normal case here), caught by a test asserting the centered and
       uncentered outputs actually differ on a large synthetic offset --
       the test failed because they were bit-identical. Fixed by using each
       image's INTENSITY-WEIGHTED CENTROID (center of mass of the actual
       voxel values, clipped to non-negative first since raw intensities
       are not inherently a physical mass and jittered inputs can go
       slightly negative) instead of the geometric grid center -- this
       actually responds to where the content sits, not just the grid
       definition.
    """
    dim = f.GetDimension()

    def intensity_centroid(img):
        arr = sitk.GetArrayFromImage(img).astype(np.float64)  # numpy (z,y,x,...) order
        weights = np.maximum(arr, 0.0)
        total = weights.sum()
        if total <= 0:
            # Degenerate (all-zero/negative) image -- nothing to weight by,
            # fall back to the geometric grid center rather than dividing by
            # zero.
            centroid_numpy_order = [s / 2.0 for s in arr.shape]
        else:
            idx_grids = np.indices(arr.shape, dtype=np.float64)
            centroid_numpy_order = [float((g * weights).sum() / total) for g in idx_grids]
        # SimpleITK's continuous-index convention is (x, y, z, ...), the
        # reverse of numpy's array-axis order -- same flip used everywhere
        # else in this codebase (e.g. scripts/04's idx_zyx = idx[:, ::-1]).
        center_idx = centroid_numpy_order[::-1]
        return np.array(img.TransformContinuousIndexToPhysicalPoint(center_idx))

    f_center = intensity_centroid(f)
    m_center = intensity_centroid(m)
    # sitk.TranslationTransform's TransformPoint is output = input + offset
    # (ITK convention), and Resample(moving, referenceImage=fixed, transform)
    # samples moving at transform(x) for each physical point x in fixed's
    # grid -- so offset = m_center - f_center makes transform(f_center)
    # land exactly on m_center, aligning the two images' content centroids.
    offset = tuple(float(v) for v in (m_center - f_center))
    centering_tx = sitk.TranslationTransform(dim, offset)
    m_centered = sitk.Resample(m, f, centering_tx, sitk.sitkLinear, 0.0)
    return m_centered, centering_tx


def baseline_bspline_registration(
    fixed: np.ndarray,
    moving: np.ndarray,
    mesh_size: int = 8,
    max_iterations: int = 100,
    spacing: tuple[float, ...] | None = None,
    center_first: bool = False,
    metric_bins: int = 50,
    gradient_convergence_tolerance: float = 1e-5,
):
    """Classic deformable (B-spline) registration via SimpleITK.

    Args:
        fixed, moving: image arrays to register.
        mesh_size: control points per dimension for the B-spline grid. Cost
            grows fast with this -- e.g. mesh_size=8 on a 3D volume means
            8*8*8 = 512 control points (1536 free parameters to optimize).
            Use a small value (e.g. 3-4) for quick dev/correctness checks on
            real 3D data, and only raise it once you know the pipeline works.
        max_iterations: cap on optimizer iterations. Also the main real-3D
            runtime lever -- lower this for a fast first pass.
        spacing: real voxel spacing in SimpleITK (x, y, z) order, i.e. exactly
            what `sitk_image.GetSpacing()` returns on the ORIGINAL image
            before it was converted to a numpy array. Defaults to None, which
            SimpleITK then treats as isotropic (1,1,1) -- REAL DICOM SPACING
            IS NOT ISOTROPIC (e.g. prostate MRI is often ~0.3-0.5mm in-plane
            but several mm through-plane). Passing the true spacing here is
            what makes the mesh geometry, optimizer behavior, and returned
            displacement field actually correspond to real millimeters,
            rather than to voxel-index units silently mislabeled as "mm"
            downstream (found via independent code audit; see
            the archived development record).
            If you truly have isotropic 1mm data (e.g. some synthetic tests),
            explicitly pass spacing=(1.0, 1.0, 1.0) rather than relying on
            the default, to make that assumption visible at the call site.
        center_first: if True, rigidly translate the moving image so its
            geometric center lines up with the fixed image's BEFORE running
            the B-spline optimizer (see `_center_moving_on_fixed`). Opt-in
            (default False) so it doesn't silently change results for
            existing checkpoints -- found to fix a stochastic "images do not
            sufficiently overlap" crash on at least one real patient
            (aaa0051); worth turning on generally once verified.

        metric_bins: number of histogram bins used by Mattes mutual
            information. Defaults to the historical/current value of 50.
        gradient_convergence_tolerance: LBFGSB gradient convergence tolerance.
            Defaults to the historical/current value of 1e-5.

    Returns a displacement field shaped (D, ...) matching the image grid.
    This returns the registration estimate used by downstream uncertainty/error studies.
    """
    if metric_bins < 2:
        raise ValueError("metric_bins must be at least 2")
    if not np.isfinite(gradient_convergence_tolerance) or gradient_convergence_tolerance <= 0:
        raise ValueError("gradient_convergence_tolerance must be finite and positive")

    try:
        import SimpleITK as sitk
    except ImportError as e:
        raise ImportError(
            "SimpleITK not installed. `pip install SimpleITK`. "
            "(Not needed for the synthetic week-one plot.)"
        ) from e

    f = sitk.GetImageFromArray(fixed.astype(np.float32))
    m = sitk.GetImageFromArray(moving.astype(np.float32))
    if spacing is not None:
        f.SetSpacing(spacing)
        m.SetSpacing(spacing)

    centering_offset = None
    if center_first:
        m, centering_tx = _center_moving_on_fixed(f, m, sitk)
        centering_offset = np.array(centering_tx.GetOffset())  # (x, y, z, ...) order

    mesh = [mesh_size] * f.GetDimension()
    tx = sitk.BSplineTransformInitializer(f, mesh)

    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(metric_bins)  # multimodal-ready metric
    reg.SetOptimizerAsLBFGSB(
        gradientConvergenceTolerance=gradient_convergence_tolerance,
        numberOfIterations=max_iterations,
    )
    reg.SetInterpolator(sitk.sitkLinear)
    reg.SetInitialTransform(tx, inPlace=True)
    reg.Execute(f, m)

    disp_filter = sitk.TransformToDisplacementFieldFilter()
    disp_filter.SetReferenceImage(f)
    disp = sitk.GetArrayFromImage(disp_filter.Execute(tx))  # (..., D)
    if centering_offset is not None:
        # Found via independent adversarial audit: an earlier version of this
        # function computed the rigid centering translation, used it to steer
        # the optimizer toward a valid overlap, and then DISCARDED it --
        # returning only the B-spline transform's displacement, silently
        # missing the (potentially large) rigid offset from the total
        # fixed->moving displacement. Since centering_tx is a pure
        # translation (constant offset added everywhere, not a per-voxel
        # field), the correct total displacement is simply the B-spline
        # field plus this constant offset -- avoids any ambiguity about
        # sitk.CompositeTransform's composition order by not using it at all.
        disp = disp + centering_offset  # broadcasts over the (..., D) array
    return np.moveaxis(disp, -1, 0)  # -> (D, ...)


def curvature_uncertainty(
    fixed: np.ndarray,
    moving: np.ndarray,
    mesh_size: int = 8,
    max_iterations: int = 100,
    perturb_eps: float = 0.5,
    spacing: tuple[float, ...] | None = None,
    center_first: bool = False,
    return_curvature: bool = False,
    mc_samples: int = 30,
    mc_seed: int = 0,
):
    """A second, more principled uncertainty estimate: instead of asking "how
    much do several perturbed registration attempts disagree" (see
    ensemble_uncertainty), ask "if I nudge the found answer slightly, how much
    worse does the alignment get?"

    Why this exists: docs/real_data_findings.md (results 3-4) found real
    evidence that ensemble_uncertainty conflates REPEATABILITY with
    CORRECTNESS -- an optimizer that converges to the same weak, shallow
    answer every time looks maximally confident (zero disagreement) even
    though a weak/shallow alignment score is itself evidence the answer
    shouldn't be trusted. Curvature-based uncertainty measures the thing
    ensemble disagreement misses directly: how sharply defined the found
    optimum actually is.

    This is the same idea as the Fisher information matrix / Laplace
    approximation in classical statistics: the curvature (second derivative)
    of a likelihood/objective function at its optimum is inversely related to
    how confident you should be in that optimum -- steep curvature (small
    nudges cost a lot) means a precise, well-supported answer; flat curvature
    (small nudges cost almost nothing) means an imprecise, poorly-supported
    one. Concretely here: sigma^2 is set proportional to 1/curvature at each
    B-spline control point.

    How the spatial variation comes for free: a B-spline transform is built
    from a grid of control points, each of which only influences a small
    local region of the image (local support). Measuring curvature per
    control point gives one standard-deviation estimate per B-spline
    parameter; PROPAGATING those parameter-level uncertainties into a smooth
    per-voxel sigma map (rather than a re-run per landmark or an
    externally-imposed binning scheme) is done via Monte Carlo sampling of
    the actual transform -- see the implementation below and the note on
    why this replaced an earlier, mathematically incorrect approach that
    directly interpolated raw sigma values through the B-spline basis
    (found via independent adversarial review; docs/paper.tex Appendix D).

    Args:
        spacing: real voxel spacing in SimpleITK (x, y, z) order -- see
            baseline_bspline_registration's docstring for why this matters.
            Without it, curvature is measured against an assumed-isotropic
            1mm grid, and the resulting sigma is not in real physical units.
        mc_samples: number of Monte Carlo parameter draws used to propagate
            per-parameter sigma into the per-voxel sigma field (see the
            implementation below). More samples reduce Monte Carlo noise in
            the resulting field at the cost of one extra displacement-field
            evaluation (cheap relative to the curvature finite-difference
            loop's metric evaluations) per sample.
        mc_seed: seed for the Monte Carlo parameter sampling, for
            reproducibility.

    Returns:
        u_mean: the registration's displacement field, same shape as
            baseline_bspline_registration's return, (D, ...).
        sigma: per-voxel scalar uncertainty, shape matching u_mean's spatial
            dims, derived from local curvature (propagated via Monte Carlo
            sampling of the real transform, then combined across axes via
            root-mean-square to match calibration.py's isotropic
            chi-squared(ndim) coverage model) rather than ensemble spread.
    """
    try:
        import SimpleITK as sitk
    except ImportError as e:
        raise ImportError(
            "SimpleITK not installed. `pip install SimpleITK`. "
            "(Not needed for the synthetic week-one plot.)"
        ) from e

    f = sitk.GetImageFromArray(fixed.astype(np.float32))
    m = sitk.GetImageFromArray(moving.astype(np.float32))
    if spacing is not None:
        f.SetSpacing(spacing)
        m.SetSpacing(spacing)

    centering_offset = None
    if center_first:
        m, centering_tx = _center_moving_on_fixed(f, m, sitk)
        centering_offset = np.array(centering_tx.GetOffset())

    mesh = [mesh_size] * f.GetDimension()
    tx = sitk.BSplineTransformInitializer(f, mesh)

    reg = sitk.ImageRegistrationMethod()
    reg.SetMetricAsMattesMutualInformation(50)
    reg.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=max_iterations)
    reg.SetInterpolator(sitk.sitkLinear)
    reg.SetInitialTransform(tx, inPlace=True)
    reg.Execute(f, m)

    disp_filter = sitk.TransformToDisplacementFieldFilter()
    disp_filter.SetReferenceImage(f)
    disp = sitk.GetArrayFromImage(disp_filter.Execute(tx))
    if centering_offset is not None:
        # See baseline_bspline_registration's identical fix/comment -- the
        # rigid centering translation must be added back into the total
        # displacement, not discarded (found via independent audit).
        disp = disp + centering_offset
    u_mean = np.moveaxis(disp, -1, 0)

    # Curvature per control point: for each transform parameter, perturb it
    # +eps and -eps (holding everything else fixed) and see how much the
    # alignment metric degrades in each direction. A second-derivative
    # (curvature) estimate from three points: metric(+eps), metric(0),
    # metric(-eps).
    params0 = np.array(tx.GetParameters())
    metric_eval = sitk.ImageRegistrationMethod()
    metric_eval.SetMetricAsMattesMutualInformation(50)
    metric_eval.SetInterpolator(sitk.sitkLinear)
    # Force dense (non-random) sampling for these evaluations. Mattes MI can
    # default to evaluating a random SUBSET of voxels for speed, which would
    # make metric_at() noisy even at the exact same parameters -- and that
    # noise could swamp the tiny true signal we're measuring here (how much
    # a SMALL nudge changes the metric), producing junk curvature regardless
    # of how well-converged the registration is.
    metric_eval.SetMetricSamplingStrategy(metric_eval.NONE)

    def metric_at(params):
        tx.SetParameters(tuple(params))
        metric_eval.SetInitialTransform(tx, inPlace=True)
        return metric_eval.MetricEvaluate(f, m)

    metric0 = metric_at(params0)
    curvature = np.zeros_like(params0)
    for i in range(len(params0)):
        p_plus = params0.copy()
        p_plus[i] += perturb_eps
        p_minus = params0.copy()
        p_minus[i] -= perturb_eps
        m_plus = metric_at(p_plus)
        m_minus = metric_at(p_minus)
        # Mattes MI is minimized (lower=better), so a genuine local minimum
        # has metric INCREASE in both directions -- that's positive curvature
        # in the usual (loss-is-minimized) sense.
        curvature[i] = (m_plus + m_minus - 2 * metric0) / (perturb_eps**2)
    tx.SetParameters(tuple(params0))  # restore the actual optimized answer

    # Diagnostics: two earlier hypotheses (sampling noise, non-convergence)
    # were both tested and neither alone explained the nonsensical sigma
    # values seen in practice -- print what's actually happening to curvature
    # itself instead of guessing again from the final sigma number alone.
    n_floored = int((curvature <= 1e-6).sum())
    print(
        f"  [curvature diag] eps={perturb_eps}  n_params={len(params0)}  "
        f"n_at_floor={n_floored} ({100 * n_floored / len(params0):.1f}%)  "
        f"curvature: min={curvature.min():.6g} median={np.median(curvature):.6g} "
        f"max={curvature.max():.6g}"
    )

    # sigma^2 ~ 1/curvature (Laplace approximation). Curvature can come out
    # negative or near-zero for a poorly-supported point (not a true local
    # minimum) -- clip to a small positive floor so sigma stays finite and
    # large (very uncertain) rather than blowing up or going undefined.
    curvature_floor = 1e-6
    param_sigma = 1.0 / np.sqrt(np.maximum(curvature, curvature_floor))

    # Turn the per-parameter sigma values into a smooth per-voxel sigma map.
    #
    # HISTORY (found via independent adversarial review, not caught by any
    # prior audit in this project -- see docs/paper.tex Appendix D): an
    # earlier version of this step built a "sigma transform" on the same
    # mesh, loaded param_sigma directly as ITS parameters, and read off the
    # resulting field -- i.e. it computed, at each voxel x with B-spline
    # basis weights B_j(x), the quantity sum_j B_j(x) * sigma_j. That is
    # WRONG: a B-spline displacement is d(x) = sum_j B_j(x) * theta_j, and if
    # the theta_j are independent random variables with std sigma_j, the
    # correctly propagated std of d(x) is sqrt(sum_j B_j(x)^2 * sigma_j^2),
    # not sum_j B_j(x) * sigma_j. Those two quantities are not the same and
    # do not differ by a constant factor across voxels (confirmed by direct
    # numerical comparison against a Monte Carlo ground truth on a toy
    # example: analytic-correct 3.551 vs the old formula's 4.100, a ~15%
    # error that would NOT be removed by the global recalibration scale
    # fitted later, since the error's size depends on the local basis
    # weights and per-parameter sigmas, which vary across voxels and
    # patients). The old approach reused displacement-field machinery on
    # inputs (standard deviations) it was never designed to combine that way.
    #
    # FIX: Monte Carlo propagation using the REAL transform. Since d(x) is
    # an exactly linear function of the parameters theta, and the parameters
    # are modeled as independent Gaussians theta_j ~ N(theta0_j, sigma_j^2)
    # (the same Laplace-approximation assumption already used to get
    # param_sigma from curvature), drawing many theta samples, evaluating
    # the ACTUAL transform's displacement field for each (via the same
    # disp_filter used for u_mean, which is already exercised and tested
    # elsewhere in this codebase), and taking the per-voxel standard
    # deviation across samples is an unbiased, exact-in-expectation estimate
    # of the correctly propagated per-axis sigma field -- no hand-derivation
    # of individual B-spline basis weights is needed, because the real
    # interpolation machinery is doing the (correct) linear combination on
    # each sampled draw, and only the SUMMARY STATISTIC across draws (a
    # standard deviation, not a weighted sum) differs from the old approach.
    mc_rng = np.random.default_rng(mc_seed)
    mc_field_list = []
    for _ in range(mc_samples):
        theta_sample = params0 + mc_rng.standard_normal(len(params0)) * param_sigma
        tx.SetParameters(tuple(theta_sample))
        mc_field_list.append(sitk.GetArrayFromImage(disp_filter.Execute(tx)))  # (..., D)
    tx.SetParameters(tuple(params0))  # restore the actual optimized answer
    mc_fields = np.stack(mc_field_list, axis=0)  # (K, ..., D)
    sigma_per_axis = mc_fields.std(axis=0)  # (..., D) -- per-voxel, per-axis std

    # Combine the D per-axis sigma values into ONE scalar per voxel. As with
    # ensemble_uncertainty (see that function's identical fix), the correct
    # summary consistent with calibration.py's isotropic chi-squared(ndim)
    # coverage model is the root-mean-square across axes, not the vector
    # magnitude (plain sum of squares) used by the old code -- the old
    # combination step had BOTH bugs stacked on top of each other.
    sigma = np.sqrt((sigma_per_axis**2).mean(axis=-1))

    if return_curvature:
        # Exposes the raw per-parameter curvature array for direct testing
        # of the curvature->sigma relationship (see
        # tests/test_registration.py's
        # test_sigma_is_monotonically_related_to_curvature), without relying
        # on an indirect proxy like "this synthetic image looks textured" --
        # an earlier test used exactly that kind of proxy and it turned out
        # to encode a false assumption about which synthetic case would
        # produce sharper curvature (found by actually running the test
        # suite; see docs/roadmap.md). Default False so existing call sites
        # unpacking exactly (u_mean, sigma) are unaffected.
        return u_mean, sigma, curvature
    return u_mean, sigma


def ensemble_uncertainty(
    fixed,
    moving,
    n=5,
    jitter=0.02,
    seed=0,
    mesh_size=8,
    max_iterations=100,
    spacing=None,
    center_first=False,
):
    """A first, cheap uncertainty estimate: register several perturbed inputs and
    take the per-voxel spread of the resulting displacement fields as sigma.

    This is the crude baseline you IMPROVE in the thesis (correlation-aware models,
    proper probabilistic registration, conformal prediction).

    mesh_size / max_iterations / spacing pass straight through to
    baseline_bspline_registration -- see there for why these matter a lot on
    real 3D volumes (spacing in particular: without it, results are computed
    against an assumed-isotropic grid, not real millimeters).

    IMPORTANT CAVEAT on `jitter`: this perturbs raw voxel INTENSITY values
    (fixed/moving + N(0, jitter)), not the registration's initial transform
    parameters, despite "perturbed starting point" language used loosely
    elsewhere in this project's write-ups -- that's an intensity perturbation,
    not a starting-position perturbation. Its default (0.02) is calibrated
    for roughly-normalized intensities; if `fixed`/`moving` are raw,
    unnormalized DICOM values (which commonly range into the hundreds or
    thousands), a jitter of 0.02 is negligible relative to the signal and may
    not meaningfully perturb anything, which would make ensemble spread
    trivially near-zero for reasons having nothing to do with a genuinely
    weak/shallow registration optimum -- an unresolved confound flagged by
    independent code audit (see docs/roadmap.md milestone 3c). If your
    images are not normalized to a comparable intensity range, consider
    scaling jitter relative to each image's own intensity std rather than
    using the raw default.
    """
    rng = np.random.default_rng(seed)
    fields = []
    for _ in range(n):
        fj = fixed + rng.normal(0, jitter, fixed.shape)
        mj = moving + rng.normal(0, jitter, moving.shape)
        fields.append(
            baseline_bspline_registration(
                fj,
                mj,
                mesh_size=mesh_size,
                max_iterations=max_iterations,
                spacing=spacing,
                center_first=center_first,
            )
        )
    fields = np.stack(fields)  # (n, D, ...)
    u_mean = fields.mean(0)  # (D, ...)
    ndim = fields.shape[1]
    # sigma combines the D per-axis deviations into one scalar. calibration.py's
    # coverage model (coverage_radius, fit_variance_scale) assumes ||e||^2/sigma^2
    # ~ chi-squared(ndim), i.e. each of the ndim axes independently has the SAME
    # variance sigma^2 -- so the correct single-number summary of D possibly
    # unequal per-axis variances is the ROOT-MEAN-SQUARE across axes,
    # sqrt(mean_d sigma_d(x)^2), not the plain sum sqrt(sum_d sigma_d(x)^2)
    # (a vector magnitude) used by an earlier version of this line. Found via
    # independent adversarial review (see docs/paper.tex Appendix D): if the
    # true per-axis sigmas are all equal to s, the vector-magnitude sum equals
    # s*sqrt(ndim), which is too large by exactly that factor relative to what
    # the chi-squared(ndim) model expects -- confirmed by direct simulation. A
    # single global recalibration scale can absorb a CONSTANT bias like this,
    # but not one that varies across points/patients as real anisotropy does,
    # so this is fixed at the source rather than left for calibration to paper
    # over. Dividing by ndim inside the sqrt is the fix.
    sigma = np.sqrt(((fields - u_mean) ** 2).sum(1).mean(0) / ndim)  # per-voxel scalar
    return u_mean, sigma
