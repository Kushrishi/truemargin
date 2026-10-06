# External landmark provenance decision — 2026-10-06

**Classification C: access/terms/conventions unresolved.** Learn2Reg outcome
execution is stopped. No manual landmark coordinates or external outcome values
have been opened. This is an access limitation, not a negative scientific result.
The original external protocol and unchanged estimator remain preserved.

## Authoritative sources inspected

- [Challenge paper](https://mediatum.ub.tum.de/doc/1696292/document.pdf),
  DOI 10.1109/TMI.2022.3213983: 20 training/10 test pairs, affinely pre-aligned
  192×192×208 images, 100 manual landmarks per test case.
- [Official 2020 task](https://learn2reg.grand-challenge.org/Learn2Reg2020/)
  and [2021 task](https://learn2reg.grand-challenge.org/Learn2Reg2021/): fixed
  expiration, moving inspiration; public image acquisition and challenge evaluation.
  Some live pages return HTTP 403; indexed organizer text and public source code
  are available. A blocked page is not proof that annotations do not exist.
- Official Zenodo records 3835682, 4048761 and 4279348: previously hashed archive
  identities/name inventories contain no ten-case landmark files. These inspections
  are not repeated; test member payloads remain unopened.
- Official `MDL-UzL/L2R` revision
  `88475095e35442087a24439ff34ec09f54bc7dac`: public tree has validation
  landmark names 0001–0003, not the ten test correspondences 0021–0030.
  Code/configuration alone were read. No annotation CSV was opened.

## Exact endpoint checklist

| Requirement | Established / missing |
| --- | --- |
| Direct official download of ten manual test pairs | Not established in inspected sources; no unofficial copy used |
| Annotation-specific use/access terms | Not established; open image download does not establish annotation permission |
| Landmark artifact checksum | Unavailable without an authoritative artifact |
| Case mapping | Image IDs 0021–0030 frozen; matching landmark filenames are expected by evaluator but artifacts not acquired |
| Count | Paper reports 100/case; exact files not inspected |
| Coordinate order | Evaluator samples displacement components in array-axis order, but authoritative exported-file conventions remain unverified |
| Units/indexing | Code operates in continuous voxel indices and scales error by moving spacing; exact annotation indexing convention remains unresolved |
| Origin/direction/spacing | Image geometry measured on training data; coordinate conversion must preserve actual external representation |
| Image representation | Challenge images are affinely pre-aligned/resampled; original-resolution coordinates cannot be silently substituted |
| Transform direction | Frozen TrueMargin fixed expiration→moving inspiration sampling transform; must match annotation semantics |

## Evaluator-only route: do not overstate the limitation

Both `evaluation/evaluation.py` and `evaluation/L2RTest/evaluation.py` compute
TRE vectors and write `mean` **and `detailed`** fields. It is incorrect to assert
that the official implementation intrinsically returns only aggregate TRE.
Whether a hosted service currently exposes those detailed fields to participants
was not established; no submission was made.

Even a TRE vector without its corresponding fixed-coordinate locations cannot
sample ensemble spread or the three comparator signals at those locations.
An organizer-authorized service that evaluates all signals jointly might answer
the endpoint, but that interface/access is not documented here. A leaderboard
average cannot substitute for case-level local association. The evaluator's
interpolation convention is not silently adopted as TrueMargin's trilinear
scientific definition.

Pinned code SHA-256:

- `evaluation/evaluation.py`: `ed14b7b2fc2b1a52c1bccc102a3182720d6b49ddc260de1cee5c5a2bc34c6dc6`
- `evaluation/utils.py`: `fd924ef31a10d9c47ee24f255a9415abc6e784ee788d62b94be08ba997a34a05`
- `evaluation/L2RTest/evaluation.py`: `3ce2cec7e405e82f4d30cbbc0b1777e1b23bd490313c0daa6d6c4a84b8abd50d`

## Prospective fallback assessment (not an amendment)

| Criterion | Learn2Reg LungCT | DIR-Lab 4DCT |
| --- | --- | --- |
| Independent cases | Ten frozen test pairs | Ten official 4DCT cases |
| Expert local truth | Paper: 100/case | Official download description: 300 paired samples/case; complete larger point sets not downloadable |
| Direct endpoint access | Unresolved | Request form provides password-protected case packets; human acquisition required |
| Coordinate documentation | Test export conventions unresolved | Official format PDF documents voxel XYZ=(RL,AP,SI), one-based corner-voxel centroid, corresponding rows, T00 inhale/T50 exhale |
| Image format / resources | Preprocessed NIfTI; training timing measured | Raw 16-bit `.img`; variable 256/512 grids, larger runtime/memory likely; image read order/intensity handling must be prospectively specified |
| Terms / artifact hashes | Annotation permission unresolved | Request/packet terms and exact identities not obtained yet |
| Current decision | Park result-bearing execution | Strong candidate for acquisition assessment, not approved/frozen replacement |

DIR-Lab primary sources:
[download description](https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/downloads-and-reference-data/index.html),
[4DCT cases/access](https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/downloads-and-reference-data/4dct.html),
[coordinate format PDF](https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/_files/format-document.pdf).

The user must request access themselves; no form/email/contact was submitted.
Request image/format/use documentation with correspondence files kept sealed.
Record archive hashes without reading landmark values. Verify terms and raw
image layout before deciding a formal amendment. No favorable preliminary
registration result is used to select the dataset. Do not transpose/reindex
coordinates to maximize correlation.

## Stop / next gate

No further expensive Learn2Reg runtime work is launched while the endpoint source
is unresolved. Seven forward members and one reverse returned finite fields;
two forward members remain censored. Full-study feasibility is not asserted.
Obtain authorized exact-ten Learn2Reg correspondence access, or complete DIR-Lab
access/terms/geometry assessment and a prospective amendment before outcomes.
Only after all existing pre-outcome gates pass may a committed machine-readable
freeze authorize landmark access. **HELD-OUT ACCESS SAFE: NO.**
