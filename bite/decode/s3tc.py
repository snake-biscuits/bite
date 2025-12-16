"""BCn / DXTn / DXTC / S3TC"""
# https://en.wikipedia.org/wiki/S3_Texture_Compression
import numpy as np

from ..textures.base import MipIndex, Texture


# TODO: compressed blocks to numpy pixel array


# LDR RGB565 4x4 blocks
def DXT1(texture: Texture, mip_index: MipIndex = None) -> np.array:
    if mip_index is None:
        mip_index = texture.default_index()
    width, height = texture.mip_size(mip_index)
    ...
    pixel_data = texture.mipmaps[mip_index]
    # np.frombuffer(pixel_data, dtype=...)
    # TODO: loop over each tile and place it in as regular pixels
    # -- decode.detwiddle would be handy for this actually
    # -- each tile is a Z, so 1 iteration would suffice
    raise NotImplementedError()


# NOTE: DXT3 & DXT5 consist of Alpha blocks followed by DXT1 RGB blocks


# should handle TYPELESS, UF16 & SF16
def BC6H(texture, mip_index: MipIndex = None) -> np.array:
    # https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc6h-format
    if mip_index is None:
        mip_index = texture.default_index()
    width, height = texture.mip_size(mip_index)
    # ...
    pixel_data = texture.mipmaps[mip_index]
    # np.frombuffer(pixel_data, dtype=...)
    raise NotImplementedError()
