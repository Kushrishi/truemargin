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

All ten authorized case packets have now been acquired from the official password-gated source (see the complete acquisition record below). For each archive, record source, acquisition date, exact filename, byte size, SHA-256, case identity, citation and relevant access/use terms while preserving the original bytes unchanged.

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

## 7 October initial authorized acquisition checkpoint

One original official packet, `Case1Pack.zip`, was acquired through the password-gated link reached from the Emory 4DCT source. Its unchanged archive is 77,006,951 bytes, SHA-256 `5589732668c3694e46a3c0eda4ccaceb4e634de08c633bcfb0362644caf1287a`. Member-name/size inventory establishes the extreme T00/T50 image members, both 300-landmark files and the intermediate 75-landmark files. All ten phase image members have 12,320,768 uncompressed bytes, consistent with the public case-1 dimensions and 16-bit class. **No coordinate member was opened, parsed or extracted.** Images also remain undecoded pending storage semantics.

The official coordinate-format PDF was preserved: 1,108,791 bytes, SHA-256 `8e022f4856d29b20c8d863146cef6726f56f8fdca97025f5ae4c1c5d37269b7b`. The official [MATLAB Utility Pack 1 PDF](https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/_files/matlab-utility-pack1.pdf) was consulted specifically for raw reading semantics. It states that the user supplies datatype, size and byte ordering and that implementation is locked `.p` code. This does not establish the distributed packets' signedness, endianness, traversal or intensity scaling. No utility software was acquired or run.

The other nine packets remain unacquired; the case-2 link presents a separate password gate. Registration authorization is established by the user, but exact applicable access/use restrictions must remain recorded locally with the packets before qualification closes. Archives and protected payloads stay outside public Git. Transient Work storage is not an established persistent raw-data repository; retain the originals and local acquisition records in an authorized stable local data directory.

No image decoding, runtime probe, prospective replacement amendment or outcome execution follows from this acquisition checkpoint. No public benchmark outcome statistics were used. **HELD-OUT ACCESS SAFE: NO.**

## 7 October complete ten-case acquisition

All ten original ZIP packets were acquired through the official Emory-linked password-gated pages on 2026-10-07 UTC, superseding the initial acquisition count above. Original bytes remain unchanged and local outside public Git. The following hashes identify the archives; no protected payload is redistributed.

| Case | Original archive | Archive bytes | SHA-256 | Each phase image bytes |
| --- | --- | --- | --- | --- |
| 4DCT1 | `Case1Pack.zip` | 77,006,951 | `5589732668c3694e46a3c0eda4ccaceb4e634de08c633bcfb0362644caf1287a` | 12,320,768 |
| 4DCT2 | `Case2Pack.zip` | 93,396,266 | `237b9cf423967f86149c3680029b7c6afae5c3e9b315c91a00d43953362717c8` | 14,680,064 |
| 4DCT3 | `Case3Pack.zip` | 85,769,449 | `824d9cb93891a5fd73835aae28cd3b21cdb22c81f552f5fb958a06c63b6c76fc` | 13,631,488 |
| 4DCT4 | `Case4Pack.zip` | 84,395,602 | `cd5603cb2611911f04b188dd1f26f988d6740fe077dba02734b7f50b344bda0e` | 12,976,128 |
| 4DCT5 | `Case5Pack.zip` | 87,097,616 | `6bf6afffcc01b0039f84c4f4ab4dd9aae9807d35b217196430697865a8dbddc2` | 13,893,632 |
| 4DCT6 | `Case6Pack.zip` | 322,431,318 | `a48a87ff5feee9decd8f7e27e2053de904977406e1f74e21b1247de4c40de916` | 67,108,864 |
| 4DCT7 | `Case7Pack.zip` | 333,591,361 | `8154f7f84ad927a135df11e6c10d5db8d2f7a92d346cf17978ed8069a569389a` | 71,303,168 |
| 4DCT8 | `Case8Pack.zip` | 341,488,519 | `29b5f777a5798e72a1ec1a089e0f3d4ee690bcdc4b62a78b8f83882037a35743` | 67,108,864 |
| 4DCT9 | `Case9Pack.zip` | 300,347,734 | `138282e9ce4ab55093611456776a7ef7baa042d2a53a8da0d37f2579a1611a57` | 67,108,864 |
| 4DCT10 | `Case10Pack.zip` | 289,284,277 | `c402b0d3f99a1fe470e758816a3f4d1f07248ac8f34bc0cf83cea239c6e410f0` | 62,914,560 |

Each packet contains ten phase image members whose uncompressed sizes match the prospectively recorded geometry and two-byte scalar class. The case-8 ZIP uses the internal root name `Case8Deploy`; its official archive name remains `Case8Pack.zip`. That naming difference does not establish a decoding convention or change inclusion. ZIP inventories contain no additional non-image/non-coordinate format documentation. All coordinate payloads, including intermediate-phase references, remain unopened and unextracted. No raw image has been decoded.

The original reference publications remain assigned prospectively: the landmark-framework paper for cases 1–5 and the trajectory-modeling paper for cases 6–10. Local records retain canonical official links, acquisition UTC dates, sizes, hashes, case identities, citation context and the user-established authorization. Exact applicable accepted-use restrictions still need to be retained locally before qualification closes. Protected archives require stable access-controlled local retention; Work scratch storage is transient.

Acquisition closes the first three listed gates only. Signedness, endianness, traversal, intensity representation, validated decoding and image-only feasibility remain unresolved. A targeted raw-format clarification draft is prepared locally and has not been sent. No source convention may be selected from landmark values, visually plausible outcomes or published benchmark results. No replacement amendment, full compute campaign or outcome unsealing is authorized. **HELD-OUT ACCESS SAFE: NO.**
