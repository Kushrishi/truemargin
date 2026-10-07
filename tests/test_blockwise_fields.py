import numpy as np
import pytest

from truemargin.ensemble import summarize_fields, summarize_fields_blockwise


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
@pytest.mark.parametrize("block", [2, 7, 13, 1000])
@pytest.mark.parametrize("layout", ["contiguous", "sitk-vector-last", "memmap"])
def test_exact_unchanged_formula(tmp_path, dtype, block, layout):
    rng = np.random.default_rng(17)
    fields = []
    for i in range(9):
        vector_last = rng.normal(size=(2, 4, 5, 3)).astype(dtype)
        field = np.moveaxis(vector_last, -1, 0)
        if layout != "sitk-vector-last":
            field = np.ascontiguousarray(field)
        if layout == "memmap":
            path = tmp_path / f"synthetic-{i}.npy"
            np.save(path, field)
            field = np.load(path, mmap_mode="r")
        fields.append(field)
    expected = summarize_fields(fields)
    actual = summarize_fields_blockwise(fields, block_voxels=block)
    for left, right in zip(expected, actual, strict=True):
        np.testing.assert_array_equal(left, right)


@pytest.mark.parametrize("block", [0, 1, -1, True, 1.5])
def test_invalid_block(block):
    with pytest.raises(ValueError):
        summarize_fields_blockwise([np.zeros((3, 2, 4, 5))] * 9, block_voxels=block)


def test_bad_fields():
    a = np.zeros((3, 2, 4, 5))
    for fields in [
        [a],
        [a, a[:, :, :, :4]],
        [a, a.astype(np.float32)],
        [a, np.full_like(a, np.nan)],
        [np.zeros((4, 2, 4, 5))] * 2,
    ]:
        with pytest.raises(ValueError):
            summarize_fields_blockwise(fields)


def test_reject_copy_producing_layout():
    a = np.zeros((3, 2, 4, 5)).transpose(0, 2, 1, 3)
    with pytest.raises(ValueError, match="contiguous"):
        summarize_fields_blockwise([a, a])
