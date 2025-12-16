import numpy as np

from bite.pixels import base


def test_Format():
    # pixel array from bytes
    rgb_888 = base.Format(red=8, green=8, blue=8)
    rgb_array = rgb_888.array_from(
        b"\x00\x01\x02\x03\x04\x05")
    expected_rgb = np.array([
        [0, 1, 2],
        [3, 4, 5]], dtype=np.uint8)
    assert np.array_equal(rgb_array, expected_rgb)

    # shuffle rgb -> bgr
    bgr_888 = base.Format(blue=8, green=8, red=8)
    bgr_array = rgb_888.shuffle(rgb_array, bgr_888)
    expected_bgr = np.array([
        [2, 1, 0],
        [5, 4, 3]], dtype=np.uint8)
    assert np.array_equal(bgr_array, expected_bgr)
