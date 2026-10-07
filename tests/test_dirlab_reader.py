from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

import numpy as np
import pytest

from truemargin.dirlab import case_geometry, one_based_rl_ap_si_to_zero_based_index_xyz
from truemargin.dirlab_reader import DirLabDecodeSpec, decode_image_bytes, image_members, read_phase


def spec(case="4DCT1"):
    return DirLabDecodeSpec(
        case,
        case_geometry(case).size_xyz,
        "int16",
        "little",
        "x-fastest-zyx",
        "raw-documented-RL-AP-SI",
    )


def test_asymmetric_words_axes_and_reflection():
    s = spec()
    a = np.zeros(s.size_xyz[::-1], dtype="<i2")
    a[0, 0, 0], a[7, 5, 3], a[-1, -1, -1] = -123, 1234, 32767
    got = decode_image_bytes(a.tobytes(), spec=s)
    assert got.dtype == np.int16 and got.flags.c_contiguous
    np.testing.assert_array_equal(got, a)
    p = one_based_rl_ap_si_to_zero_based_index_xyz(
        np.array([[1, 1, 1], [4, 6, 8], list(s.size_xyz)]), size_xyz=s.size_xyz
    ).astype(int)
    for x, y, z in p:
        assert got[z, y, x] == got[::-1][s.size_xyz[2] - 1 - z, y, x]
    assert got[7, 5, 3] == 1234
    assert got[::-1][7, 5, 3] != 1234  # image-only reflection would be wrong


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "COPD1"),
        ("size_xyz", (1, 2, 3)),
        ("scalar_type", "uint16"),
        ("byte_order", "native"),
        ("byte_order", "big"),
        ("traversal", "xyz"),
        ("orientation", "flipped-z"),
    ],
)
def test_spec_fail_closed(field, value):
    with pytest.raises(ValueError):
        decode_image_bytes(b"", spec=replace(spec(), **{field: value}))


@pytest.mark.parametrize("length_delta", [-1, 1])
def test_size_rejected(length_delta):
    with pytest.raises(ValueError, match="byte count"):
        decode_image_bytes(
            bytes(case_geometry("4DCT1").expected_int16_bytes + length_delta), spec=spec()
        )


def packet(*, omit=None, duplicate=False, bad_case=False):
    stream = BytesIO()
    size = case_geometry("4DCT1").expected_int16_bytes
    with ZipFile(stream, "w", compression=8) as z:
        for i in range(10):
            if i == omit:
                continue
            name = f"Case{2 if bad_case else 1}Pack/Images/case1_T{i}0_s.img"
            z.writestr(name, bytes(size))
        z.writestr("Case1Pack/ExtremePhases/sealed.txt", b"DO NOT OPEN")
        if duplicate:
            z.writestr("Case1Pack/Images/case1_T00-ssm.img", bytes(size))
    stream.seek(0)
    return ZipFile(stream)


def test_selective_read_firewall(monkeypatch):
    with packet() as z:
        original = z.open
        opened = []

        def guarded(name, *args, **kwargs):
            assert str(name).endswith(".img")
            opened.append(name)
            return original(name, *args, **kwargs)

        monkeypatch.setattr(z, "open", guarded)
        assert read_phase(z, phase="T50", spec=spec()).shape == (94, 256, 256)
        assert len(opened) == 1
        with pytest.raises(ValueError):
            read_phase(z, phase="T01", spec=spec())


@pytest.mark.parametrize("kwargs", [{"omit": 5}, {"duplicate": True}, {"bad_case": True}])
def test_bad_inventory(kwargs):
    with packet(**kwargs) as z, pytest.raises(ValueError):
        image_members(z, spec=spec())


def test_case8_root_and_size():
    with ZipFile(BytesIO(), "w") as z:
        z.writestr("Case8Pack/Images/case8_T00.img", b"bad")
        with pytest.raises(ValueError):
            image_members(z, spec=spec("4DCT8"))
