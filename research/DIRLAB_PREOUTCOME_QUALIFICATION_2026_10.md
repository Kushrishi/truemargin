# DIR-Lab 4DCT pre-outcome qualification record

**Date:** 2026-10-06  
**Status:** pre-outcome source/semantics qualification only  
**Held-out landmark contents opened:** **NO**  
**HELD-OUT ACCESS SAFE:** **NO**

This record evaluates whether the authorized Emory DIR-Lab 4DCT collection can replace the unresolved Learn2Reg result-bearing external validation. It does not rewrite the original Learn2Reg protocol and it does not authorize access to any numerical DIR-Lab landmark content.

## Authoritative source boundary

The authoritative public source is the Emory DIR-Lab download/reference site:

- <https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/downloads-and-reference-data/index.html>
- <https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/downloads-and-reference-data/4dct.html>
- coordinate-format document: <https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/_files/format-document.pdf>
- MATLAB Utility Pack 1 summary: <https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/_images/matlab-utility-pack1_aod.pdf>

The site states that each case is distributed as a compressed ZIP, images are Pinnacle raw `*.img`, the image class is 16-bit integer, and coordinate data are text files whose rows identify corresponding landmarks. Access to the protected case packets is password-gated after registration.

The official 4DCT page identifies the original reference publications as Castillo et al. (2009), *A framework for evaluation of deformable image registration spatial accuracy using large landmark point sets*, for 4DCT1-5, and Castillo et al. (2009), *Four-dimensional deformable image registration using trajectory modeling*, for 4DCT6-10.

Public benchmark outcome summaries on the website are not inputs to this qualification and must not be used for case selection, preprocessing, tuning, coordinate choices or acceptance criteria.

## Prospectively recorded non-outcome geometry

All ten cases remain in scope. Dimensions are in voxel units and spacing is in millimetres, exactly as published on the official 4DCT page.

| Case | Size (RL, AP, SI) | Spacing mm (RL, AP, SI) |
| --- | --- | --- |
| 4DCT1 | 256 × 256 × 94 | 0.97 × 0.97 × 2.5 |
| 4DCT2 | 256 × 256 × 112 | 1.16 × 1.16 × 2.5 |
| 4DCT3 | 256 × 256 × 104 | 1.15 × 1.15 × 2.5 |
| 4DCT4 | 256 × 256 × 99 | 1.13 × 1.13 × 2.5 |
| 4DCT5 | 256 × 256 × 106 | 1.10 × 1.10 × 2.5 |
| 4DCT6 | 512 × 512 × 128 | 0.97 × 0.97 × 2.5 |
| 4DCT7 | 512 × 512 × 136 | 0.97 × 0.97 × 2.5 |
| 4DCT8 | 512 × 512 × 128 | 0.97 × 0.97 × 2.5 |
| 4DCT9 | 512 × 512 × 128 | 0.97 × 0.97 × 2.5 |
| 4DCT10 | 512 × 512 × 120 | 0.97 × 0.97 × 2.5 |

`src/truemargin/dirlab.py` records only these public geometry facts and synthetic coordinate-conversion functions. It has no filesystem access and no landmark reader.

## Coordinate convention resolved from official documentation

The official coordinate-format document states:

- T00 is maximum inhale;
- T50 is maximum exhale;
- landmark rows are `(RL, AP, SI)`;
- coordinates are voxel-index units;
- `(1, 1, 1)` is the centroid of the right-anterior-superior corner voxel;
- corresponding rows in the T00/T50 files identify the same landmark.

The diagram shows increasing RL from right to left, AP from anterior to posterior, and SI from superior to inferior. Therefore the purely algebraic conversion from the documented one-based voxel-centroid coordinates to a zero-based native index is:

`index_xyz = (RL, AP, SI) - (1, 1, 1)`

No numerical landmark file is needed to establish or test that rule. Synthetic tests verify the origin, fractional coordinates, bounds, axis order and physical spacing conversion.

For the unchanged TrueMargin array estimator, an origin-zero local physical frame can be constructed as `index_xyz * spacing_xyz_mm`. In this local frame +x is right-to-left, +y anterior-to-posterior and +z superior-to-inferior. This is an estimator-local basis, not a claim that the raw packets encode a standard DICOM LPS/RAS patient frame.

## Registration direction

The original external question fixed expiration and moved inspiration. The official phase documentation establishes T50 as maximum exhale and T00 as maximum inhale. The existing registration implementation calls SimpleITK with the fixed image first and emits a displacement field on the fixed grid whose transform is used to sample the moving image.

Accordingly, the pre-outcome scientific-continuity direction is **T50 fixed / T00 moving**. This choice was made from the original protocol, official phase semantics and existing estimator implementation, not from landmark outcomes or public benchmark errors.

This direction is not yet a DIR-Lab protocol amendment. Dataset suitability still has unresolved image-storage semantics below.

## Raw-image semantics: unresolved gate

The official site establishes raw `*.img` and 16-bit integer class. It does not state on the public pages reviewed here:

- signed versus unsigned 16-bit interpretation for the distributed packets;
- byte order / endianness;
- exact on-disk traversal order for RL/AP/SI;
- any intensity offset or scale applied by the distributed representation.

The MATLAB Utility Pack 1 summary does **not** resolve those choices. It describes a generic importer for which data type, size and byte ordering are supplied by the user, and its implementation is distributed as locked MATLAB `*.p` code.

Therefore no DIR-Lab raw reader is added yet. A reader that guesses endian, signedness or axis traversal and then chooses the visually plausible result would violate the prospective qualification boundary.

The expected raw payload byte count for each phase can be checked without decoding, because the public dimensions and 16-bit class imply `prod(size_xyz) * 2` bytes. That is an identity/integrity check only.

## Protected acquisition and firewall

The authorized case packets still need to be acquired from the official password-gated source. For each archive, record source, acquisition date, exact filename, byte size, SHA-256, case identity, citation and relevant access/use terms while preserving the original bytes unchanged.

Archive member names may be listed to establish identity. Outcome-bearing coordinate members — including the 300-point extreme-phase files and all intermediate 75-point files — must not be opened, parsed, previewed, indexed, summarized or used for debugging before the explicit outcome-unsealing authorization.

Only non-outcome image/data members needed for qualification may be selectively extracted.

## Remaining pre-outcome gates

Before a formal DIR-Lab amendment can be frozen:

1. acquire and hash all ten official protected case packets;
2. preserve/record the official coordinate-format document locally;
3. establish exact packet filenames and safe member inventory without opening coordinate payloads;
4. establish signedness, byte ordering and raw traversal from authoritative packet/source evidence;
5. prove a semantics-preserving image decode for all ten cases;
6. verify the T50/T00 image geometry and one prospectively specified conversion rule across every case;
7. run synthetic/analytical tests for raw decoding, one-based conversion, physical/index conversion, interpolation, displacement sampling and out-of-bounds handling;
8. quantify exact unchanged-estimator runtime/CPU/memory/storage feasibility from image-only bounded probes;
9. only then draft a prospective DIR-Lab amendment preserving the original Learn2Reg history and freezing all analysis details before any real landmark value is accessed.

Until every gate above is satisfied:

**HELD-OUT ACCESS SAFE: NO**
