# DIR-Lab decoder source audit — 7 October 2026

Pre-outcome qualification. Numerical landmark contents remain unopened.
**HELD-OUT ACCESS SAFE: NO.** No provider correspondence was sent.

Exact repository revisions, code blobs and all 100 committed MONAI header blob
identities are in [the source manifest](DIRLAB_DECODER_SOURCES_2026_10.json).
The immutable revisions specified by the owner were inspected, rather than
unversioned copies. MONAI's ten T00 headers were checked against every official
case geometry; its generator specifies the same fields for all phases.
Current [ITK MetaIO documentation](https://docs.itk.org/en/latest/learn/metaio.html)
was checked at ITK commit `812c951739e6103b1a7dd8d6a6670f71a721b6d7`.

| Field | Official provider evidence | Independent implementation evidence | Direct non-outcome invariant / decision |
| --- | --- | --- | --- |
| Width / dimensions / spacing | 16-bit integer, published ten-case geometry | MONAI and RegNet reproduce geometry | All 100 image sizes equal product(dimensions) × 2; 4,030,464,000 bytes total. |
| Signedness | Integer, signedness not specified | MONAI MET_SHORT; RegNet/dual int16; SuperElastix MET_USHORT | Bit 15 is unset in every word of all 100 images under explicit little endian. Signed/unsigned numbers are identical for these actual payloads. This is not provider-authoritative signedness. Select explicit int16. |
| Byte order | Not specified in reviewed provider documents | MONAI explicitly MSB=False; other NumPy readers use host-native int16 | Choose explicit little endian; native-endian readers alone are not portable evidence. All images agree voxel-for-voxel with the independent SimpleITK 2.5.6 MetaImage path. |
| Traversal | Not explicitly specified | RegNet/dual reshape reversed XYZ to ZYX; MONAI MetaImage dimensions XYZ | x fastest, NumPy (z,y,x). Independent native-buffer and MetaImage decoding agree on every voxel. |
| Raw slice versus documented SI | Provider defines coordinate 1 at superior voxel centroid; increasing SI toward inferior | RegNet and dual reverse BOTH image z AND landmark z. MONAI retains stored order with direction diag(1,1,-1). SuperElastix retains raw array. | Retain raw order in the estimator-local RL/AP/SI frame and use xyz−1. A physical z reversal requires a matching Nz−SI landmark index. An image-only reversal is unsupported by the inspected readers. |
| Intensity offset / scale | No binary rescale specified | MONAI says stored HU+1024 and clips after subtraction; dual subtracts/clips at a different range; RegNet notes uncertainty about slope/intercept | Retain stored words without offset, clipping or scale. HU calibration is unnecessary for the unchanged estimator and is not claimed. |

## Transparent SI correction to the proposed source-convergence hypothesis

The hypothesis that independent readers reverse raw z **while retaining**
`landmark = xyz−1` is contradicted by their exact source. RegNet explicitly uses
`(RL−1, AP−1, Nz−SI)` after image reversal, and states that the reversal makes its
representation more similar to another study. Dual uses `Nz−SI` too. These are
representational choices, not evidence that image-only reversal establishes the
provider's superior-origin index system. MONAI's negative physical direction
changes geometry, not voxel order. Its conversion copies geometry after intensity
processing; it does not reverse the pixel array.

Let raw array R have ZYX shape. Representation A used here is C=R with index
p=(RL−1,AP−1,SI−1) and local physical coordinate p×spacing. Representation B is
C'=R[::-1] with p'=(RL−1,AP−1,Nz−SI). Then C[p]=C'[p'] exactly. To express B in
A's physical frame use origin_z=(Nz−1)×spacing_z and direction_z=−1. Alternatively
B can define its own reflected physical frame, provided images, points and vector
components all transform consistently. It cannot silently discard that reflection.

TrueMargin constructs origin-zero identity-direction images from arrays. Thus
A deliberately uses a **local +z superior-to-inferior frame**, not standard ITK
patient LPS. Array semantics survive downstream code. The existing coordinate
helper remains correct for A; its documentation now explicitly names this basis.
Synthetic asymmetric word/point tests detect an image-only or double reversal.
No anatomical visual preview, registration score, published benchmark errors or
landmark content was used to select A. Embedded benchmark statistics in converter
source are excluded from decisions; only image metadata/reader code was used.

## Intensity reasoning and controlled numerical check

For valid linear interpolation, subtracting a common constant from fixed and
moving intensities cancels exactly in their absolute residual. Outside-volume
padding must be masked consistently; changing a constant without changing padding
is not a general whole-grid residual-invariance proof. ICE and Jacobian are
functions of displacement fields, not directly of CT intensity offset.

Mattes MI normalizes intensities against each image's histogram range. A common
additive offset shifts values and extrema together and leaves normalized histogram
locations and intensity derivatives unchanged in exact arithmetic. Floating-point
optimizer trajectories need not be bitwise identical. An asymmetric synthetic 3D
mesh-3, 15-iteration, bins-50, tolerance-1e-5, no-centering experiment compared
stored-like arrays with the same arrays minus 1024. The maximum returned-field
difference was 0.0000055164 mm; both reached the 15-iteration cap. This is a
controlled implementation check, not real-image or scientific result evidence.
Retaining stored values avoids even that numerical perturbation. No clipping is
introduced; MONAI/dual clipping is information-changing and is not imported.

## Scope and acceptance

A bounded image-only reader requires explicit case, dimensions, int16, little
endian, x-fastest ZYX traversal and raw documented RL/AP/SI orientation. It
validates all ten phase names/sizes, rejects aliases/duplicates/missing phases,
and opens only the requested `.img` member. The caller must verify source archive
SHA-256 before use. No landmark reader is added.

All 100 images were decoded through explicit little-endian NumPy and independently
through the pinned MONAI-style MetaImage header convention using SimpleITK 2.5.6.
Every voxel and size/spacing/direction check agreed. Synthetic opposite-endian,
asymmetric-axis, reflected-index, bounds, malformed specification and selective
archive-access tests accompany the reader. Existing interpolation/displacement
and reflected-geometry tests remain part of the full suite.

The binary/coordinate representation is qualified without provider contact.
Operational feasibility, final prospective analysis identity and outcome-unsealing
remain separate gates. No full registration ensemble has been launched.
