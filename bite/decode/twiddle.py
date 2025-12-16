"""PVR twiddle processing"""
# https://github.com/VincentNLOBJ/pvr2image
from typing import List

import numpy as np

from ..base import Face, MipIndex, Texture
from .. import pvr


# TODO: compare speed of iterate vs detwiddle_lut

def iterate(table: np.array = None) -> np.array:
    # NOTE: table should be a 2D array
    # -- sides should be a power of 2 in length
    # TODO: does table have to be square?
    z = np.array([
        [0, 1],
        [2, 3]], dtype=np.uint32)

    if table is None:
        return z

    big_z = [[
        z + i * z.size
        for i in row]
        for row in table]

    # y0 = np.concatenate((big_z[0][0], big_z[0][1]), axis=1)
    # y1 = np.concatenate((big_z[1][0], big_z[1][1]), axis=1)
    # full = np.concatenate(y0, y1, axis=0)

    return np.concatenate([
        np.concatenate(row, axis=1)
        for row in big_z], axis=0)


# NOTE: the twiddle pattern is a Z-order curve
# -- a fractal space filling curve
# -- handy for finding neighbouring pixels
def detwiddle_lut(width: int, height: int) -> List[int]:
    """adapted from pvr2image"""
    if width != height:
        raise NotImplementedError("Square Images Only")
    # TODO: landscape & portrait rectangles
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


def TWIDDLED_to_ORDERED(texture: Texture, mip_index: MipIndex = None) -> bytes:
    assert isinstance(texture, pvr.PVR)

    if mip_index is None:
        if texture.is_cubemap:
            mip_index = MipIndex(0, 0, Face(0))
        else:
            mip_index = MipIndex(0, 0, None)
    pixel_data = texture.mipmaps[mip_index]

    # ARGB_4444 -> RGBA_8888
    assert texture.format.pixel == pvr.PixelMode.ARGB_4444
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
    raw_bytes = rgba32.tobytes()

    return np.array([
        raw_bytes[i * 4:(i + 1) * 4]  # index whole pixel
        for i in detwiddle_lut(*texture.max_size)]).flatten().tobytes()
