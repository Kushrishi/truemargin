"""
io_utils.py
-----------
Loaders for the real TCIA prostate data step. None of this is needed for the
synthetic week-one plot; it's here so the repo is ready when you download data.
"""

from __future__ import annotations

import os

import numpy as np


def load_volume(path: str) -> np.ndarray:
    """Load an MRI/CT volume (DICOM series folder or NIfTI file) as a numpy array.

    Args:
        path: Directory of a DICOM series, or a single NIfTI/.nii.gz file.

    Returns:
        Array shaped (z, y, x) of voxel intensities.
    """
    try:
        import SimpleITK as sitk
    except ImportError as e:
        raise ImportError("pip install SimpleITK to load MRI/CT.") from e
    if os.path.isdir(path):
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames(reader.GetGDCMSeriesFileNames(path))
        img = reader.Execute()
    else:
        img = sitk.ReadImage(path)
    return sitk.GetArrayFromImage(img)  # (z, y, x)


def assert_same_grid(
    img_a, img_b, name_a: str = "image A", name_b: str = "image B", tol: float = 1e-3
) -> None:
    """Raise a clear error if two SimpleITK images do not share the same
    physical grid (size, spacing, origin, direction).

    Found via independent adversarial audit: scripts/04 and scripts/08 both
    convert a mask-image voxel index to a physical point using the MASK
    image, then convert that same physical point to a voxel index using the
    T2 image -- silently assuming both images share an identical physical
    grid, on the strength of a file-naming convention (e.g.
    "<patient>-T2-AXIAL-SM-FOV_HECaP.mha" is assumed to already be aligned to
    that patient's T2 series) rather than a checked fact. A gross mismatch
    (wrong patient, wrong series) would already crash downstream when
    mask_arr.shape has to match t2_arr.shape for cropping -- but a SUBTLE
    mismatch (same size, slightly different origin or spacing, e.g. from a
    resampling step upstream in how the HECaP release was produced) would not
    crash anything; it would silently bias every landmark's assumed physical
    location by a fraction of a voxel, without a single loud error anywhere.
    This makes that assumption explicit and checked rather than assumed.
    """
    size_a, size_b = img_a.GetSize(), img_b.GetSize()
    if size_a != size_b:
        raise ValueError(
            f"{name_a} and {name_b} have different sizes ({size_a} vs {size_b}) -- "
            "they are not on the same grid at all."
        )
    for attr, label in [("GetSpacing", "spacing"), ("GetOrigin", "origin")]:
        val_a = np.array(getattr(img_a, attr)())
        val_b = np.array(getattr(img_b, attr)())
        if not np.allclose(val_a, val_b, atol=tol):
            raise ValueError(
                f"{name_a} and {name_b} have mismatched {label} "
                f"({val_a.tolist()} vs {val_b.tolist()}, tolerance={tol}) -- physical "
                "points computed from one image's grid are not valid on the other's. "
                "This would otherwise silently bias every landmark location instead "
                "of raising an error."
            )
    dir_a = np.array(img_a.GetDirection())
    dir_b = np.array(img_b.GetDirection())
    if not np.allclose(dir_a, dir_b, atol=tol):
        raise ValueError(
            f"{name_a} and {name_b} have mismatched direction cosines "
            f"({dir_a.tolist()} vs {dir_b.tolist()}) -- the two images are not "
            "oriented the same way in physical space."
        )


def _select_dce_phase_files(
    filenames: list[str],
    positions: list[str],
    times: list[str],
    phase_fraction: float = 0.5,
    max_repeat_ratio: float = 1.25,
) -> list[str]:
    """Pick the files for ONE temporal phase out of a DCE series that stacks
    many repeated scans of the same slice positions over time.

    Real prostate DCE MRI re-images the same set of physical slice locations
    many times (e.g. every ~20 seconds for several minutes) as contrast dye
    moves through tissue -- this project's TCIA DICOM data has no
    TemporalPositionIdentifier tag, so the phase structure has to be
    reconstructed from two tags that ARE present: ImagePositionPatient
    (identical, to many decimal digits, for repeated scans of the same
    physical slice) and AcquisitionTime (differs per repeat, in scan order).

    Before this fix, every script that loaded a DCE series just handed the
    whole folder to sitk.ImageSeriesReader, which stacked ALL phases
    together as if they were consecutive z-slices -- confirmed via direct
    file-count inspection (13 of 15 patients had 480-720 DCE files against
    20-32 for the matching T2 series) and via scripts/_inspect_dce_phases.py
    (aaa0086: exactly 36 real slice positions x 20 time-phases = 720 files,
    a clean grid, each position re-scanned every ~19 seconds for ~6
    minutes). See docs/roadmap.md milestone 3d.

    This groups files by exact position, sorts each position's repeats by
    acquisition time, and returns the filenames for ONE phase per position
    (chosen relative to that position's OWN repeat count, not a single
    global index -- see below), ordered by physical z position so the
    result is a real, anatomically ordered slice stack.

    Real clinical DICOM is not always a perfectly uniform grid: aaa0051's
    DCE series has 32 slice positions, 30 repeated 18 times and 2 repeated
    only 17 times (574 total files), most plausibly because the scanner
    truncated the very last temporal phase for a couple of outer slices --
    a small, benign real-world quirk, not corrupted data. Demanding an
    exactly uniform grid (this function's original, stricter version) would
    make the loader unusable on real data like this. Instead, each
    position's phase is chosen at `phase_fraction` of THAT position's own
    repeat count (so a position with 17 repeats and one with 18 both
    resolve to essentially the same point in time, not off by a whole
    phase), and only a large mismatch in repeat counts across positions
    (controlled by `max_repeat_ratio`) is treated as a sign of real
    structural corruption worth failing loud over, rather than a small,
    plausible truncation.

    Args:
        filenames: DICOM filenames, same order/length as positions/times.
        positions: raw ImagePositionPatient tag string per file ("x\\y\\z").
        times: raw AcquisitionTime tag string per file.
        phase_fraction: which temporal phase to use, as a fraction of each
            position's own repeat count (0.0 = first/earliest -- often a
            low-signal pre-contrast frame; 1.0 = last/latest -- may show
            washout). Default 0.5 picks a phase roughly in the middle of
            the acquisition as a reasonable, reproducible single
            representative frame for structural registration. This is a
            real, disclosed simplifying choice: it does NOT attempt to
            find the clinically "optimal" enhancement phase per patient
            (that would need per-patient enhancement-curve analysis this
            project doesn't do), and different phase choices will shift
            results somewhat -- worth a sensitivity check before treating
            a single phase choice as the final word.
        max_repeat_ratio: maximum allowed ratio between the most-repeated
            and least-repeated slice position's count. Small mismatches
            (e.g. 18 vs 17) are tolerated as real-world DICOM quirks; large
            mismatches (e.g. 20 vs 2) suggest something structurally
            different is going on (a genuinely different series mixed in,
            a badly corrupted acquisition) and should be inspected manually
            rather than silently resolved.

    Returns:
        Filenames for the chosen phase, ordered by increasing z position.

    Raises:
        ValueError: if slice-position repeat counts vary by more than
            `max_repeat_ratio` -- fail loud rather than silently guessing
            at a structure that may not actually be a clean temporal
            series at all.
    """
    by_pos: dict[str, list[tuple[str, str]]] = {}
    for fname, pos, t in zip(filenames, positions, times, strict=True):
        by_pos.setdefault(pos, []).append((fname, t))

    counts = [len(v) for v in by_pos.values()]
    n_max, n_min = max(counts), min(counts)
    if n_min == 0 or (n_max / n_min) > max_repeat_ratio:
        raise ValueError(
            f"DCE series slice-position repeat counts vary too much to "
            f"safely auto-select a phase: min={n_min}, max={n_max} "
            f"(ratio {n_max / max(n_min, 1):.2f} > max_repeat_ratio="
            f"{max_repeat_ratio}) across {len(by_pos)} distinct positions "
            f"and {len(filenames)} total files. Needs manual inspection "
            "(see scripts/_inspect_dce_phases.py) before it's safe to "
            "auto-select a phase."
        )

    def z_of(pos_str: str) -> float:
        return float(pos_str.split("\\")[2])

    sorted_positions = sorted(by_pos.keys(), key=z_of)

    chosen_files = []
    for pos in sorted_positions:
        repeats_sorted = sorted(by_pos[pos], key=lambda ft: ft[1])  # sort by acquisition time
        n_i = len(repeats_sorted)
        phase_idx = min(n_i - 1, max(0, round(phase_fraction * (n_i - 1))))
        chosen_files.append(repeats_sorted[phase_idx][0])

    return chosen_files


def load_dce_single_phase(series_dir: str, phase_fraction: float = 0.5):
    """Load ONE temporal phase of a DCE MRI series as a proper 3D SimpleITK image.

    See `_select_dce_phase_files`'s docstring for why this exists: naively
    reading a DCE series folder with sitk.ImageSeriesReader silently stacks
    ALL repeated time-phases together as if they were consecutive z-slices,
    producing an anatomically meaningless pseudo-volume for any series with
    more than one phase (13 of 15 patients in this project's real-data
    cohort, found via independent review + direct verification -- see
    docs/roadmap.md milestone 3d).

    This reuses SimpleITK's own geometry inference (the same
    ImageSeriesReader code path already used successfully for T2 and for
    the 2 patients whose DCE series happened to be single-phase already) --
    it is only fed a corrected, phase-filtered, z-ordered file list instead
    of every file in the folder. This is deliberately safer than manually
    reconstructing spacing/origin/direction by hand.

    Args:
        series_dir: Directory of DCE DICOM files (all phases mixed together).
        phase_fraction: passed to `_select_dce_phase_files`.

    Returns:
        A SimpleITK Image: a real, single-phase, correctly ordered 3D volume.
    """
    import SimpleITK as sitk

    filenames = sorted(
        f for f in os.listdir(series_dir) if os.path.isfile(os.path.join(series_dir, f))
    )
    reader = sitk.ImageFileReader()
    reader.LoadPrivateTagsOn()
    positions, times = [], []
    for f in filenames:
        reader.SetFileName(os.path.join(series_dir, f))
        reader.ReadImageInformation()
        positions.append(reader.GetMetaData("0020|0032").strip())
        times.append(reader.GetMetaData("0008|0032").strip())

    chosen = _select_dce_phase_files(filenames, positions, times, phase_fraction=phase_fraction)
    chosen_paths = [os.path.join(series_dir, f) for f in chosen]

    series_reader = sitk.ImageSeriesReader()
    series_reader.SetFileNames(chosen_paths)
    return series_reader.Execute()


def load_wsi_thumbnail(path: str, level: int = 2) -> np.ndarray:
    """Load a whole-slide image at a downsampled level (full WSI is gigapixels).

    Args:
        path: Path to a whole-slide image file (e.g. .svs).
        level: OpenSlide pyramid level to read; clamped to the slide's max level.

    Returns:
        RGB array shaped (H, W, 3).
    """
    try:
        import openslide
    except ImportError as e:
        raise ImportError("pip install openslide-python (+ system openslide) for WSIs.") from e
    slide = openslide.OpenSlide(path)
    level = min(level, slide.level_count - 1)
    img = slide.read_region((0, 0), level, slide.level_dimensions[level])
    return np.array(img.convert("RGB"))


def load_landmarks(path: str) -> np.ndarray:
    """Load a single set of point coordinates (N, D). Adapt to the dataset's format.

    Prefer `load_landmark_pairs` when the file contains fixed/moving
    correspondences (the usual TCIA prostate landmark format) -- that is what
    the calibration harness needs to compute true displacement.
    """
    return np.loadtxt(path, delimiter=",")


def load_landmark_pairs(path: str, ndim: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Load paired fixed/moving landmark correspondences for real-data calibration.

    Expects a CSV with no header and 2*ndim columns per row:
        fx, fy[, fz], mx, my[, mz]
    i.e. the point's coordinates in the fixed (MRI) volume, followed by its
    corresponding coordinates in the moving (histology) volume. This is the
    standard shape for registration landmark ground truth (ANHIR/ACROBAT-style).

    Args:
        path: CSV path.
        ndim: Spatial dimensionality (2 for slice-wise, 3 for full volumes).

    Returns:
        (fixed_pts, moving_pts), each shaped (N, ndim). The true displacement
        at each landmark is `moving_pts - fixed_pts`.
    """
    arr = np.loadtxt(path, delimiter=",")
    if arr.ndim == 1:
        arr = arr[None, :]
    if arr.shape[1] != 2 * ndim:
        raise ValueError(
            f"Expected {2 * ndim} columns (fixed + moving coords) for ndim={ndim}, "
            f"got {arr.shape[1]}. Adjust ndim or the CSV layout."
        )
    return arr[:, :ndim], arr[:, ndim:]


def crop_to_mask_bbox(
    fixed: np.ndarray,
    moving: np.ndarray,
    mask: np.ndarray,
    points_idx: np.ndarray,
    pad: int = 10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Crop fixed/moving volumes down to a padded bounding box around the mask,
    and shift landmark indices to match the cropped array.

    Why: registration.ensemble_uncertainty runs a full B-spline optimization
    over the ENTIRE volume (e.g. 320x320x28 voxels), even though real cases
    typically only care about a small tumor region with a handful of
    landmarks in it. Registration cost scales with volume size, so cropping
    down to just the region of interest (plus a safety margin) before
    registering is the single biggest speedup available without changing the
    registration algorithm or losing accuracy where it matters.

    Args:
        fixed, moving: arrays shaped (z, y, x), same shape.
        mask: array shaped (z, y, x), same shape, >0 marks the region of interest.
        points_idx: array shaped (N, 3) of landmark voxel indices in (z, y, x)
            order, in the ORIGINAL (uncropped) array's coordinate space.
        pad: extra voxels of margin around the mask's bounding box on every
            side, so the crop isn't so tight it clips useful context.

    Returns:
        (fixed_cropped, moving_cropped, points_idx_cropped) -- the cropped
        arrays, and landmark indices re-expressed in the cropped array's own
        coordinate space (subtract this same offset from any other index you
        need to look up in the cropped arrays).
    """
    voxel_idx = np.argwhere(mask > 0)
    if len(voxel_idx) == 0:
        raise ValueError("Mask is empty -- nothing to crop to.")
    lo = np.maximum(voxel_idx.min(axis=0) - pad, 0)
    hi = np.minimum(voxel_idx.max(axis=0) + pad + 1, np.array(mask.shape))

    fixed_cropped = fixed[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
    moving_cropped = moving[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
    points_idx_cropped = points_idx - lo[None, :]

    return fixed_cropped, moving_cropped, points_idx_cropped


def sample_field_at_points(field: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Sample a per-voxel field (e.g. a displacement or sigma map) at landmark
    coordinates, via nearest-neighbor lookup.

    Args:
        field: Array shaped (D, ...) for vector fields (e.g. displacement) or
            (...) for scalar fields (e.g. sigma), where `...` is the spatial
            grid (ndim dims, row-major to match `points` ordering).
        points: Array shaped (N, ndim) of coordinates in the same grid/index
            space as `field`'s spatial dims.

    Returns:
        Array shaped (D, N) for vector fields or (N,) for scalar fields.
    """
    idx = tuple(np.round(points[:, d]).astype(int) for d in range(points.shape[1]))
    is_vector = field.ndim == points.shape[1] + 1
    if is_vector:
        vector_idx: tuple[slice | np.ndarray, ...] = (slice(None), *idx)
        return field[vector_idx]
    return field[idx]
