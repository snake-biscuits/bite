# https://github.com/flyinghead/flycast/blob/master/core/ui/boxart/pvrparser.h
# https://registry.khronos.org/OpenGL/extensions/IMG/IMG_texture_compression_pvrtc.txt
# for PowerVR GPUs (Apple | OpenGL ES)
from __future__ import annotations
import enum
import io
import math
from typing import Dict, Union

from . import base
from .utils import read_struct, write_struct


class PixelMode(enum.Enum):
    ARGB_1555 = 0x00
    RGB_565 = 0x01
    ARGB_4444 = 0x02
    YUV_422 = 0x03
    BUMP_MAP = 0x04
    PALETTE_4 = 0x05
    PALETTE_8 = 0x06
    RESERVED = 0x07


bytes_per_pixel = {
    PixelMode.ARGB_1555: 2,
    PixelMode.RGB_565: 2,
    PixelMode.ARGB_4444: 2,
    PixelMode.YUV_422: 2,
    PixelMode.BUMP_MAP: 2,
    PixelMode.PALETTE_4: 0.5,
    PixelMode.PALETTE_8: 1}
# NOTE: no compressed PixelMode, no min_block_size


class TextureMode(enum.Enum):
    TWIDDLED = 0x01
    TWIDDLED_MIPS = 0x02
    VQ = 0x03
    VQ_MIPS = 0x04
    PAL_4 = 0x05
    PAL_4_MIPS = 0x06
    PAL_8 = 0x07
    PAL_8_MIPS = 0x08
    RECTANGLE = 0x09
    STRIDE = 0x0B
    TWIDDLED_RECTANGLE = 0x0D
    SMALL_VQ = 0x10
    SMALL_VQ_MIPS = 0x11
    ALT_TWIDDLED_MIPS = 0x12


class Format:
    pixel: PixelMode
    texture: TextureMode

    def __init__(self, pixel, texture):
        self.pixel = pixel
        self.texture = texture

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, Format):
            return (self.pixel, self.texture) == (other.pixel, other.texture)
        return False

    def __hash__(self):
        return hash((self.pixel, self.texture))

    @property
    def name(self):
        return "_".join([self.pixel.name, self.texture.name])


class PVR(base.Texture):
    extension: str = "pvr"
    folder: str
    filename: str
    # header
    gbix: Union[bytes, None]
    data_size: int
    format: Format
    size: base.Size
    # pixel data
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {(mip_index, cubemap_index, side_index): b"raw_mipmap"}
    raw_data: Union[bytes, None]  # if mipmaps cannot be split
    # properties
    is_cubemap: bool = property(lambda s: False)
    num_mipmaps: int
    num_frames: int

    def __init__(self):
        super().__init__()
        # defaults
        self.gbix = None
        self.version = (0, 0)
        self.data_size = 0
        self.format = Format(PixelMode(0), TextureMode(1))

    def __repr__(self) -> str:
        width, height = self.size
        size = f"{width}x{height}"
        return f"<PVR '{self.filename}' {size} {self.format.name}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> PVR:
        out = cls()
        # header
        magic = stream.read(4)
        if magic == b"GBIX":
            length = read_struct(stream, "I")
            out.gbix = stream.read(length)  # 1 or 2 ints?
            magic = stream.read(4)
        assert magic == b"PVRT"
        out.data_size = read_struct(stream, "I")
        pixel_mode, texture_mode = read_struct(stream, "2B")
        out.format = Format(PixelMode(pixel_mode), TextureMode(texture_mode))
        assert read_struct(stream, "H") == 0  # padding
        out.size = read_struct(stream, "2H")
        # mipmap indexing
        out.num_frames = 1
        if out.format.texture.name.endswith("_MIPS"):
            raise NotImplementedError("PVR w/ mipmaps")
            out.num_mipmaps = ...
        else:
            out.num_mipmaps = 1
        # calculate mip_sizes
        width, height = out.size
        try:
            bpp = bytes_per_pixel[out.format.pixel]
        except KeyError:
            # TODO: UserWarning(f"Unknown bpp for format: {out.format.name}")
            out.raw_data = stream.read()
            return out
        mip_sizes = [
            math.ceil((width >> i) * (height >> i) * bpp)
            for i in range(out.num_mipmaps)]
        # read mipmaps
        out.mipmaps = {
            base.MipIndex(mip, 0, None): stream.read(mip_size)
            for mip, mip_size in enumerate(mip_sizes)}
        return out

    def as_bytes(self) -> bytes:
        raise NotImplementedError()
        stream = io.BytesIO()
        # header
        write_struct(stream, "...", ...)
        ...
        # mip data
        if isinstance(self.raw_data, bytes):
            stream.write(self.raw_data)
        else:
            ...
        # stream -> bytes
        stream.seek(0)
        return stream.read()
