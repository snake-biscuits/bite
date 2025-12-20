"""BCn / DXTn / DXTC / S3TC"""
# https://en.wikipedia.org/wiki/S3_Texture_Compression
import functools
import math
import struct
from typing import List

import numpy as np

from ..textures.base import MipIndex, Texture


# NOTE: output should be cropped to (width, height) if oversized
# -- mode = {3: "RGB", 4: "RGBA"}[out.shape[3]]
# -- img = Image.frombytes(mode, out.shape[:2], out.flatten().tobytes())
# -- img = img.crop((0, 0, *texture.mip_size(mip_index)))
def concatenate(tiles: List[np.array], width: int, height: int) -> np.array:
    tile_width, tile_height = tiles[0].shape[:2]
    num_cols = math.ceil(width / tile_width)
    num_rows = math.ceil(height / tile_height)
    assert num_cols * num_rows == len(tiles)
    out = np.concatenate([
        np.concatenate(tiles[i:i + num_cols], axis=0)
        for i in range(0, len(tiles), num_cols)], axis=1)
    assert out.shape[:2] == (num_cols * tile_width, num_rows * tile_height)
    return out


# NOTE: it's easier to calculate the DXT1 palette as rgb888
# -- otherwise we'd assemble a 565 image & convert the whole image to 888
# TODO: scale green intensity better
@functools.cache
def rgb565_as_rgb888(pixel: int) -> (int, int, int):
    r = (pixel >> 0xB) & 0x1F
    g = (pixel >> 0x5) & 0x3F
    b = (pixel >> 0x0) & 0x1F
    r = (r | r << 3) & 0xFF
    g = (g | g << 2) & 0xFF
    b = (b | b << 3) & 0xFF
    return (r, g, b)


@functools.cache
def DXT1_block(block: bytes) -> np.array:
    # decode palette
    c0, c1 = [rgb565_as_rgb888(c) for c in struct.unpack("2H", block[:4])]
    if c0 > c1:
        c2 = [a * 2 // 3 + b // 3 for a, b in zip(c0, c1)]
        c3 = [a // 3 + b * 2 // 3 for a, b in zip(c0, c1)]
    else:  # c0 <= c1
        c2 = [a // 2 + b // 2 for a, b in zip(c0, c1)]
        c3 = (0, 0, 0)
    palette = (c0, c1, tuple(c2), tuple(c3))
    # decode indices
    return np.array([[
        palette[(row >> (i * 2)) % 4]
        for row in block[4:]]
        for i in range(4)], dtype=np.uint8)


@functools.cache
def DXT1_block_fast(block: bytes) -> np.array:
    """single palette mode"""
    c0, c1 = [rgb565_as_rgb888(c) for c in struct.unpack("2H", block[:4])]
    c2 = [a * 2 // 3 + b // 3 for a, b in zip(c0, c1)]
    c3 = [a // 3 + b * 2 // 3 for a, b in zip(c0, c1)]
    palette = (c0, c1, tuple(c2), tuple(c3))
    # decode indices
    return np.array([[
        palette[(row >> (i * 2)) % 4]
        for row in block[4:]]
        for i in range(4)], dtype=np.uint8)


# NOTE: also known as BC1
def DXT1(texture: Texture, mip_index: MipIndex = None, fast=True) -> np.array:
    """LDR RGB565 4x4 blocks"""
    if mip_index is None:
        mip_index = texture.default_mip()
    pixel_data = texture.mipmaps[mip_index]
    decode_funcs = {
        True: DXT1_block_fast,
        False: DXT1_block}
    decode_block = decode_funcs[fast]
    tiles = [
        decode_block(pixel_data[i:i + 8])
        for i in range(0, len(pixel_data), 8)]
    return concatenate(tiles, *texture.mip_size(mip_index))


@functools.cache
def DXT3_alpha_block(block: bytes) -> np.array:
    """4x4 4bpp alpha"""
    alpha = np.array([
        block[i // 2] >> 4 if i % 2 == 0 else block[i // 2] & 0xF
        for i in range(16)], dtype=np.uint8)
    return (alpha | alpha << 4).reshape((4, 4, 1))


# NOTE: both DXT2 & DXT3 are BC2
# NOTE: DXT2 = DXT3 + Premultiplied Alpha
def DXT3(texture: Texture, mip_index: MipIndex = None) -> np.array:
    """LDR RGB565 4x4 blocks + 4bpp Alpha"""
    if mip_index is None:
        mip_index = texture.default_mip()
    pixel_data = texture.mipmaps[mip_index]
    a_tiles = list()
    rgb_tiles = list()
    for i in range(0, len(pixel_data), 16):
        a_tiles.append(DXT3_alpha_block(pixel_data[i:i + 8]))
        rgb_tiles.append(DXT1_block_fast(pixel_data[i + 8:i + 16]))
    tiles = [
        np.concatenate((rgb, a), axis=2)
        for rgb, a in zip(rgb_tiles, a_tiles)]
    return concatenate(tiles, *texture.mip_size(mip_index))


@functools.cache
def DXT5_alpha_block(block: bytes) -> np.array:
    # decode palette
    a0, a1 = block[:2]
    if a0 > a1:
        a2 = (a0 * 6 + a1 * 1) // 7
        a3 = (a0 * 5 + a1 * 2) // 7
        a4 = (a0 * 4 + a1 * 3) // 7
        a5 = (a0 * 3 + a1 * 4) // 7
        a6 = (a0 * 2 + a1 * 5) // 7
        a7 = (a0 * 1 + a1 * 6) // 7
    else:  # a0 <= a1
        a2 = (a0 * 4 + a1 * 1) // 5
        a3 = (a0 * 3 + a1 * 2) // 5
        a4 = (a0 * 2 + a1 * 3) // 5
        a5 = (a0 * 1 + a1 * 4) // 5
        a6 = 0
        a7 = 255
    palette = (a0, a1, a2, a3, a4, a5, a6, a7)
    # decode indices
    rows = [  # 4x 3-bit indices per row
        int(block[2:4].hex()[:3], 16),
        int(block[3:5].hex()[1:], 16),
        int(block[5:7].hex()[:3], 16),
        int(block[6:8].hex()[1:], 16)]
    return np.rot90(np.array([[
        [palette[(row >> (i * 3)) & 0b111]]
        for i in range(4)]
        for row in rows], dtype=np.uint8), 3)


# NOTE: Both DXT4 & DXT5 are BC3
# NOTE: DXT4 = DXT5 + Premultiplied Alpha
def DXT5(texture: Texture, mip_index: MipIndex = None) -> np.array:
    """LDR RGB565 + Alpha 4x4 blocks"""
    if mip_index is None:
        mip_index = texture.default_mip()
    pixel_data = texture.mipmaps[mip_index]
    a_tiles = list()
    rgb_tiles = list()
    for i in range(0, len(pixel_data), 16):
        a_tiles.append(DXT5_alpha_block(pixel_data[i:i + 8]))
        rgb_tiles.append(DXT1_block_fast(pixel_data[i + 8:i + 16]))
    tiles = [
        np.concatenate((rgb, a), axis=2)
        for rgb, a in zip(rgb_tiles, a_tiles)]
    return concatenate(tiles, *texture.mip_size(mip_index))


# NOTE: BC6H is quite complex, easier to decode on GPU than CPU
# -- https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc6h-format
def BC6H_block(block: bytes) -> np.array:
    raise NotImplementedError()


# TODO: variants for TYPELESS, UF16 & SF16
def BC6H(texture: Texture, mip_index: MipIndex = None) -> np.array:
    """HDR RGB161616 4x4 blocks"""
    if mip_index is None:
        mip_index = texture.default_mip()
    pixel_data = texture.mipmaps[mip_index]
    tiles = [
        BC6H_block(pixel_data[i:i + 16])
        for i in range(0, len(pixel_data), 16)]
    return concatenate(tiles, *texture.mip_size(mip_index))
