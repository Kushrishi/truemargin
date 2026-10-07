"""Image-only DIR-Lab decoder; never reads a coordinate member.

The canonical array retains raw slice order. Its local +z is documented SI;
this is not ITK's patient LPS +z. See the dated source audit before changing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from zipfile import ZipFile

import numpy as np

from truemargin.dirlab import case_geometry


@dataclass(frozen=True)
class DirLabDecodeSpec:
    case_id: str
    size_xyz: tuple[int, int, int]
    scalar_type: str
    byte_order: str
    traversal: str
    orientation: str

    def validate(self) -> None:
        geometry = case_geometry(self.case_id)
        if self.size_xyz != geometry.size_xyz:
            raise ValueError("dimensions must match the declared official case")
        if (self.scalar_type, self.byte_order, self.traversal, self.orientation) != (
            "int16",
            "little",
            "x-fastest-zyx",
            "raw-documented-RL-AP-SI",
        ):
            raise ValueError("unsupported DIR-Lab decode convention")


def decode_image_bytes(payload: bytes, *, spec: DirLabDecodeSpec) -> np.ndarray:
    """Decode exactly one phase into contiguous native int16 (z,y,x), no offset.

    Little endian is explicit even on a big-endian host. No clipping, reordering,
    centering or intensity normalization is performed. Landmark conversion is
    xyz-1 in this representation; physically reversing z requires Nz-SI instead.
    """
    spec.validate()
    expected = case_geometry(spec.case_id).expected_int16_bytes
    if len(payload) != expected:
        raise ValueError("raw image byte count does not match declared case geometry")
    words = np.frombuffer(payload, dtype="<i2")
    return words.reshape(spec.size_xyz[::-1]).astype(np.int16, copy=True)


def image_members(archive: ZipFile, *, spec: DirLabDecodeSpec) -> dict[str, str]:
    """Validate names/sizes only, including case-8's official internal root."""
    spec.validate()
    number = int(spec.case_id[4:])
    root = f"Case{number}{'Deploy' if number == 8 else 'Pack'}"
    pattern = re.compile(rf"{root}/Images/case{number}_(T[0-9]0)(?:_s|-ssm)?\.img")
    found = {}
    for info in archive.infolist():
        if not info.filename.lower().endswith(".img"):
            continue
        match = pattern.fullmatch(info.filename)
        if match is None or match[1] in found:
            raise ValueError("unexpected or duplicate DIR-Lab image member")
        if info.file_size != case_geometry(spec.case_id).expected_int16_bytes:
            raise ValueError("archive image size does not match declared case geometry")
        found[match[1]] = info.filename
    if set(found) != {f"T{i}0" for i in range(10)}:
        raise ValueError("archive must contain all ten unique phases of declared case")
    return found


def read_phase(archive: ZipFile, *, phase: str, spec: DirLabDecodeSpec) -> np.ndarray:
    """Select one validated image from an already source-identified local ZIP.

    No extractall, generic file reader or landmark parser is exposed. The caller
    must verify the original archive identity against its acquisition manifest.
    ZIP CRC verification is performed by ZipFile when the bounded read completes.
    """
    members = image_members(archive, spec=spec)
    if phase not in members:
        raise ValueError("phase must be T00 through T90 in ten-percent steps")
    expected = case_geometry(spec.case_id).expected_int16_bytes
    with archive.open(members[phase]) as stream:
        payload = stream.read(expected + 1)
    return decode_image_bytes(payload, spec=spec)
