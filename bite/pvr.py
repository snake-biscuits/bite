# https://github.com/flyinghead/flycast/blob/master/core/ui/boxart/pvrparser.h
# https://registry.khronos.org/OpenGL/extensions/IMG/IMG_texture_compression_pvrtc.txt
# for PowerVR GPUs (Apple | OpenGL ES)
from __future__ import annotations
import enum
import io
import math
from typing import Union

import breki
from breki.binary import read_struct, write_struct
from breki.files.parsed import parse_first

from . import base


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
    VQ = 0x03  # Vector Quantization
    VQ_MIPS = 0x04
    PAL_4 = 0x05
    PAL_4_MIPS = 0x06
    PAL_8 = 0x07
    PAL_8_MIPS = 0x08
    RECTANGLE = 0x09
    RECTANGLE_MIPS = 0x0A
    STRIDE = 0x0B
    STRIDE_MIPS = 0x0C
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


class Pvr(base.Texture, breki.BinaryFile):
    exts = ["*.pvr"]
    # essentials
    is_cubemap: bool = property(lambda s: False)
    # header
    gbix: Union[bytes, None]
    data_size: int  # preserved for debugging
    format: Format

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        # defaults
        self.gbix = None
        self.data_size = 8
        self.format = Format(PixelMode(0), TextureMode(1))
        self.num_frames = 1
        self.num_mipmaps = 1

    @parse_first
    def __repr__(self) -> str:
        width, height = self.max_size
        size = f"{width}x{height}"
        return f"<PVR '{self.filename}' {size} {self.format.name}>"

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        # header
        magic = self.stream.read(4)
        if magic == b"GBIX":
            length = read_struct(self.stream, "I")
            self.gbix = self.stream.read(length)  # 1 or 2 ints?
            magic = self.stream.read(4)
        assert magic == b"PVRT"
        self.data_size = read_struct(self.stream, "I")
        pixel_mode, texture_mode = read_struct(self.stream, "2B")
        self.format = Format(PixelMode(pixel_mode), TextureMode(texture_mode))
        assert read_struct(self.stream, "H") == 0  # padding
        self.max_size = read_struct(self.stream, "2H")
        # mipmap indexing
        # if out.format.texture.name.endswith("_MIPS"):
        #     raise NotImplementedError("PVR w/ mipmaps")
        #     out.num_mipmaps = ...
        if self.format.pixel not in bytes_per_pixel:
            # TODO: UserWarning / log
            self.raw_data = self.stream.read()
            return
        # calculate mip_sizes
        width, height = self.max_size
        bpp = bytes_per_pixel[self.format.pixel]
        mip_sizes = [
            math.ceil((width >> i) * (height >> i) * bpp)
            for i in range(self.num_mipmaps)]
        # NOTE: should catch VQ & _MIPS TextureModes
        if sum(mip_sizes) + 8 != self.data_size:
            # TODO: UserWarning / log
            self.raw_data = self.stream.read()
            return  # invalid mip_sizes
        # read mipmaps
        self.mipmaps = {
            base.MipIndex(mip, 0, None): self.stream.read(mip_size)
            for mip, mip_size in enumerate(mip_sizes)}

    @parse_first
    def as_bytes(self) -> bytes:
        stream = io.BytesIO()
        if isinstance(self.raw_data, bytes):
            data_size = len(self.raw_data)
        else:
            # NOTE: will be incorrect for some TextureModes
            data_size = sum(
                len(mipmap)
                for mipmap in self.mipmaps.values())
        data_size += 8
        # gbix
        if isinstance(self.gbix, bytes):
            stream.write(b"GBIX")
            write_struct(stream, "I", len(self.gbix))
            stream.write(self.gbix)
        # header
        stream.write(b"PVRT")
        write_struct(stream, "I", data_size)
        write_struct(stream, "B", self.format.pixel.value)
        write_struct(stream, "B", self.format.texture.value)
        write_struct(stream, "H", 0)  # padding
        write_struct(stream, "2H", *self.max_size)
        # mip data
        if isinstance(self.raw_data, bytes):
            stream.write(self.raw_data)
        else:
            stream.write(b"".join([
                self.mipmaps[base.MipIndex(mip, 0, None)]
                for mip in range(self.num_mipmaps)]))
        # stream -> bytes
        stream.seek(0)
        return stream.read()
