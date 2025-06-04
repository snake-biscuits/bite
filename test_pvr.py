# https://github.com/VincentNLOBJ/pvr2image
import numpy as np
from PIL import Image

import bite


def detwiddle(width: int, height: int):
    """adapted from pvr2image"""
    if width != height:
        raise NotImplementedError("Square Images Only")
    # lookup table
    sequence = [2, 6, 2, 22, 2, 6, 2]
    pattern_a = [
        *sequence, 86,
        *sequence, 342,
        *sequence, 86,
        *sequence]
    pattern_b = [
        1366, 5462, 1366, 21846,
        1366, 5462, 1366, 87382,
        1366, 5462, 1366, 21846,
        1366, 5462, 1366, 349526,
        1366, 5462, 1366, 21846,
        1366, 5462, 1366, 87382,
        1366, 5462, 1366, 21846,
        1366, 5462, 1366, 349526]
    row_increments = list()
    for b in pattern_b:
        row_increments.extend(pattern_a)
        row_increments.append(b)
    row_increments.extend(pattern_a)
    # square lut
    slice_ = [*row_increments[0:width - 1], 2]
    row = list()
    index = 0
    for increment in slice_:
        row.append(index)
        index += increment
    column = [
        x // 2
        for x in row]
    return [
        x + y
        for x in row
        for y in column]


if __name__ == "__main__":
    pvr = bite.PVR.from_file("0GDTEX.PVR")
    # <PVR '0GDTEX.PVR' 256x256 ABGR_4444_TWIDDLED>
    pixel_data = pvr.mipmaps[bite.MipIndex(0, 0, None)]

    # ABGR_4444 -> RGBA_8888
    argb16 = np.frombuffer(pixel_data, dtype=np.uint16)
    # NOTE: 1 entry per pixel
    a = (argb16 >> 0x0) & 0x000F
    r = (argb16 >> 0x4) & 0x000F
    g = (argb16 >> 0x8) & 0x000F
    b = (argb16 >> 0xC) & 0x000F
    rgba32 = np.empty((argb16.size * 4,), dtype=np.uint8)
    # NOTE: 1 entry per channel
    rgba32[0::4] = r
    rgba32[1::4] = g
    rgba32[2::4] = b
    rgba32[3::4] = a
    rgba32 = rgba32 | rgba32 << 4  # 4-bit -> 8-bit

    # TWIDDLED -> standard order
    lut = detwiddle(*pvr.size)
    raw_bytes = rgba32.tobytes()
    remix = np.array(
        [raw_bytes[i * 4:(i + 1) * 4]
         for i in lut]).flatten()

    tga = Image.frombytes("RGBA", (256, 256), remix.tobytes(), "raw")
    tga.save("test_pvr.tga")
