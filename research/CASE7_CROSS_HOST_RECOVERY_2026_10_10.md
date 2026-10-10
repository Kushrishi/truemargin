# Case7 cross-host recovery evidence

October 10, 2026. File recovery only; no registration or numerical landmark access.

The independently supplied producer manifest hash is
`5565bbf06f131d2936b801c17da2bf70ec8ca3d26b17b40e8c22e2b4c66807af`;
the original retention-receipt hash is
`fefa8015271b46842db643b2e0cbd53709d20284bab460bfb9d192e3f4bdbb8d`.
These trust anchors predate the transfer and were not inferred from its contents.
Four transfer parts reconstructed a 677,229,524-byte packet with SHA-256
`1e82c24030c33b84ef69a4301354528bf898b713588e55e13e22c99e01e04a78`.
Every part, both pinned records and all five producer files passed size/hash checks.

Producer source remains `fdaa8ae7b5aefa02e58c4f4acf4496835f7eaa3e`.
The producer was the owner's Mac, as established by the separate execution/audit
records and handoff. The consumer observed Linux 6.18.44 x86_64, glibc 2.39,
Python 3.12.14, NumPy 2.3.5 and SimpleITK 2.5.6. This is a distinct operating
host context, with owner-reported producer provenance rather than hardware attestation.
The packet itself does not authenticate host origin.

Strict extraction and verified copying recovered a fresh Linux destination.
Workspace synchronization recreated a renamed staging path in the initial attempt;
that observation is preserved. An isolated local-directory recovery then verified
the destination after staging was renamed, with the original staging path absent.
A new Python process independently verified the restored five files and scanned
all 35,651,584 vectors (106,954,752 components), in 544 blocks of 65,536 vectors.
The field is contiguous little-endian float64 with shape `[3,136,512,512]`;
file size is 855,638,144 bytes, including its NPY header. SHA-256 is
`076f1b42fa89f56a6aed7a19513b2f1589eaeaa87bbabb6392f39b63a4c46640`.
All values are finite. Mean displacement 0.7362613238858077 mm and maximum
2.250949983938718 mm match the producer audit exactly. Private transfer payloads,
consumer reports and readback script are retained separately; no clinical files
are redistributed here.

This establishes exact byte recovery and full-field validity for one completed
member. It does not establish correct alignment, optimizer convergence, numerical
diversity of nine configurations, external ranking/calibration performance, or
180-slot campaign credit. Numerical landmarks remain sealed; HELD-OUT ACCESS
SAFE remains NO. Earlier disconnected runs retain their unknown outcomes.
