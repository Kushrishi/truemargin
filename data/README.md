# Data

Data are intentionally excluded from Git history. The repository contains only
acquisition/identity instructions and code needed to reproduce the research
pipeline.

## Primary collection

The current study uses the public, de-identified TCIA
**Prostate Fused-MRI-Pathology** collection:

- 28 subjects with prostate MRI;
- T1, T2, diffusion-weighted, and DCE MRI;
- accompanying pathology resources;
- fused radiology/pathology MATLAB/MHA resources for 15 annotated subjects;
- CC BY 3.0;
- TCIA data citation required.

Collection DOI:

`10.7937/K9/TCIA.2016.TLPMR1AM`

Current TCIA collection page:

`https://www.cancerimagingarchive.net/collection/prostate-fused-mri-pathology/`

The active experiment does **not** require the ~76.8 GB whole-slide pathology
download. It uses the radiology image download (~4.7 GB) plus the small fused
rad-path MHA/MATLAB resource containing the HECaP cancer-extent masks.

## Expected local layout

```text
data/
  prostate_fused_manifest/
    prostate_fused_mri_pathology/
      <patient>/
        <study>/
          <series>/
            *.dcm

  hecap/
    <patient>-T2-AXIAL-SM-FOV_HECaP.mha
```

Exact local paths remain git-ignored.

## HECaP masks

The HECaP files are expert-checked, histology-derived cancer-extent regions
mapped onto the corresponding T2 MRI grid.

They are useful as **regions of interest**.

They are **not** independently measured T2-to-DCE pointwise displacement
ground truth.

That distinction is central to the current project.

Earlier exploratory scripts sampled HECaP voxels while comparing T2/DCE
registration against a zero-displacement reference assumption. Those analyses
are retained only as historical development evidence.

The current known-ground-truth study instead:

1. loads a real T2 anatomy and its matching HECaP ROI;
2. creates a synthetic fixed image using a known B-spline transform;
3. warps the ROI into the synthetic fixed domain with that same transform;
4. samples deterministic fixed-domain ROI locations; and
5. evaluates estimated displacement against the exact known transform.

## Current cohort split

The registration-hyperparameter mechanism was promoted on five frozen subjects:

```text
aaa0054
aaa0059
aaa0061
aaa0063
aaa0066
```

The known-ground-truth evaluation is frozen on ten different anatomies:

```text
aaa0044
aaa0051
aaa0053
aaa0060
aaa0064
aaa0069
aaa0071
aaa0072
aaa0086
aaa0087
```

Do not substitute subjects after result-bearing outcomes are observed.

Exact T2 series IDs are versioned in the experiment runner and protocol.

## Acquisition

For ordinary local use, TCIA's collection page and current Data Retriever are
the authoritative acquisition surfaces.

For the frozen geometry preflight, `scripts/fetch_known_gt_inputs.py` uses
NCI Imaging Data Commons (IDC) REST v3 to resolve only the ten predeclared T2
series within the public `prostate_fused_mri_pathology` collection. It then
uses pinned `idc-index==0.12.5` to transfer the exact public-series manifest.
Resolution is strict: `research/KNOWN_GT_SERIES_IDENTITY.json` pins the full
`StudyInstanceUID` and `SeriesInstanceUID` for each already-frozen anatomy.
The historical five-digit Data Retriever folder is retained as a compatibility
alias and must equal the final five characters of the pinned full series UID.
Exactly one public MR series must match the full UID, expected study UID,
`T2 AXIAL SM FOV` description, and frozen instance count. Any drift fails
rather than selecting a substitute.

The transport was moved from TCIA's legacy NBIA API after the first hosted
preflight timed out before resolving any anatomy. A subsequent metadata-only
diagnostic established the exact mapping from the historical Data Retriever
folder labels to the current full DICOM UIDs before any geometry result
existed. The scientific data identity did not change: IDC hosts the same public
collection and the workflow records and checks the complete frozen
StudyInstanceUID and SeriesInstanceUID for every selected series.

The same helper retrieves TCIA's small **Fused Rad-Path Matlab Files** archive
and copies only the ten required HECaP MHA files. The acquisition artifact
records the IDC release/API build, pinned acquisition-client version, resolved
full UIDs, exact per-series manifest hashes, and HECaP SHA-256 hashes. The collection page remains
the authoritative citation, version, license, and data-usage source; the
workflow download endpoint is an implementation detail, not a replacement
citation.

## Data identity and provenance

The experiment manifest records:

- collection name;
- patient identifier;
- exact T2 series identifier;
- HECaP mask filename;
- protocol/configuration identity;
- result-defining source hashes.

Generated checkpoints are valid only when their embedded provenance matches the
requested experiment.

## Usage boundary

These are public research data, not private patient records. The project is not
a medical device and makes no clinical-use claim.

Any public release or manuscript must include the TCIA dataset citation and
follow the collection's current data-usage policy.
