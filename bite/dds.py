# https://learn.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-file-layout-for-cubic-environment-maps
# https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
from __future__ import annotations
import enum
import io
import math
import os
from typing import Dict, List, Union

from . import base
from .utils import read_struct, write_struct


class DDS(base.Texture):
    extension: str = "dds"
    folder: str
    filename: str
    # header
    flags: int  # TODO: enum.IntFlag
    size: base.Size
    num_mipmaps: int
    # DX10 extended header
    format: DXGI
    dimension: int
    misc_flag: MiscFlag
    alpha_flag: AlphaFlag
    array_size: int
    # pixel data
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): raw_mipmap_data}
    raw_data: Union[bytes, None]  # if mipmaps cannot be split
    # properties
    is_cubemap: bool
    num_frames: int

    def __init__(self):
        # defaults
        self.alpha_flag = AlphaFlag.STRAIGHT
        self.array_size = 1
        self.dimension = Dimension.TEXTURE_2D
        self.flags = Flags(0x000A1007)
        self.format = DXGI.RGBA_8888_UNORM
        self.misc_flag = MiscFlag(0)
        self.num_mipmaps = 0
        # NOTE: misc_flag must be set before num_frames
        super().__init__()

    def __repr__(self) -> str:
        width, height = self.size
        size = f"{width}x{height}"
        return f"<DDS '{self.filename}' {size} {self.format.name}>"

    def split(self) -> List[DDS]:
        """separate a cubemap array into multiple files"""
        # TODO: options for how to split
        # TODO: make header copying universal
        # -- then we could move this method to base.Texture
        out = list()
        base_filename = os.path.splitext(self.filename)[0]
        is_cubemap = self.is_cubemap
        for i in range(self.num_frames):
            child = DDS()
            child.alpha_flag = self.alpha_flag
            child.array_size = 6 if is_cubemap else 1
            child.dimension = self.dimension
            child.filename = f"{base_filename}.{i}.dds"
            child.flags = self.flags
            child.format = self.format
            child.misc_flag = self.misc_flag
            child.num_mipmaps = self.num_mipmaps
            child.size = self.size
            if is_cubemap:
                indices = {
                    (mip, face): base.MipIndex(mip, i, base.Face(face))
                    for mip in range(self.num_mipmaps)
                    for face in range(6)}
            else:
                indices = {
                    (mip, None): base.MipIndex(mip, i, None)
                    for mip in range(self.num_mipmaps)}
            child.mipmaps = {
                base.MipIndex(mip, 0, face): self.mipmaps[index]
                for (mip, face), index in indices.items()}
            out.append(child)
        return out

    @property
    def is_cubemap(self) -> bool:
        # return bool(self.misc_flag & MiscFlag.CUBEMAP)
        return self.dimension == Dimension.TEXTURE_2D

    @property
    def num_frames(self) -> int:
        if self.is_cubemap:
            return self.array_size // 6
        else:
            return self.array_size

    @num_frames.setter
    def num_frames(self, value: int):
        if self.is_cubemap:
            self.array_size = value * 6
        else:
            self.array_size = value

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> DDS:
        out = cls()
        # header
        assert stream.read(4) == b"DDS "
        assert read_struct(stream, "I") == 0x7C  # header size
        out.flags = Flags(read_struct(stream, "I"))
        out.size = read_struct(stream, "2I")
        # pitch / linsize & depth
        assert read_struct(stream, "2I") == (0x00010000, 0x01)  # pitch / linsize?
        out.num_mipmaps = read_struct(stream, "I")
        assert stream.read(44) == b"\0" * 44  # reserved
        assert read_struct(stream, "2I") == (0x20, 0x04)  # pixelformat
        magic = stream.read(4)
        if magic == b"DX10":  # DX10 extended header
            assert stream.read(20) == b"\0" * 20
            assert read_struct(stream, "I") == 0x00401008  # idk, some flags?
            assert stream.read(16) == b"\0" * 16
            out.format = DXGI(read_struct(stream, "I"))
            out.dimension = Dimension(read_struct(stream, "I"))
            out.misc_flag = MiscFlag(read_struct(stream, "I"))
            out.array_size = read_struct(stream, "I")
            out.alpha_flag = AlphaFlag(read_struct(stream, "I"))
        else:
            # TODO: magic -> format
            # -- b"BC4U" -> DXGI.BC4_UNORM
            # TODO: dimension, misc_flag & array_size
            raise NotImplementedError("")
        # calculate mip_sizes
        width, height = out.size
        try:
            bpp = bytes_per_pixel[out.format]
        except KeyError:
            # TODO: UserWarning(f"Unknown bpp for format: {out.format.name}")
            out.raw_data = stream.read()
            return out
        mbs = min_block_size.get(out.format, 0)
        mip_sizes = [
            max(math.ceil((width >> i) * (height >> i) * bpp), mbs)
            for i in range(out.num_mipmaps)]
        # read mipmaps
        if out.is_cubemap:
            assert out.array_size % 6 == 0
            out.mipmaps = {
                base.MipIndex(mip, frame, face): stream.read(mip_size)
                for frame in range(out.num_frames)
                for face in base.Face
                for mip, mip_size in enumerate(mip_sizes)}
        else:
            out.mipmaps = {
                base.MipIndex(mip, frame, None): stream.read(mip_size)
                for frame in range(out.num_faces)
                for mip, mip_size in enumerate(mip_sizes)}
        return out

    def as_bytes(self) -> bytes:
        stream = io.BytesIO()
        # header
        write_struct(stream, "4s", b"DDS ")
        write_struct(stream, "I", 0x7C)
        write_struct(stream, "I", self.flags.value)
        write_struct(stream, "2I", *self.size)
        write_struct(stream, "2I", 0x00010000, 0x01)  # pitch / linsize?
        write_struct(stream, "I", self.num_mipmaps)
        write_struct(stream, "44s", b"\0" * 44)
        write_struct(stream, "2I", 0x20, 0x04)  # don't know, don't care
        # DX10 extended header
        write_struct(stream, "4s", b"DX10")
        write_struct(stream, "20s", b"\0" * 20)
        write_struct(stream, "I", 0x00401008)  # idk, some flags?
        write_struct(stream, "16s", b"\0" * 16)
        write_struct(stream, "I", self.format.value)
        write_struct(stream, "I", self.dimension.value)
        write_struct(stream, "I", self.misc_flag.value)
        write_struct(stream, "I", self.array_size)
        write_struct(stream, "I", self.alpha_flag.value)
        # mip data
        if isinstance(self.raw_data, bytes):
            stream.write(self.raw_data)
        else:
            if self.is_cubemap:
                stream.write(b"".join([
                    self.mipmaps[base.MipIndex(mip, frame, face)]
                    for frame in range(self.num_frames)
                    for face in base.Face
                    for mip in reversed(range(self.num_mipmaps))]))
            else:
                stream.write(b"".join([
                    self.mipmaps[base.MipIndex(mip, frame)]
                    for frame in range(self.num_frames)
                    for mip in reversed(range(self.num_mipmaps))]))
        # stream -> bytes
        stream.seek(0)
        return stream.read()


# formats
class DXGI(enum.Enum):
    UNKNOWN = 0x00
    RGBA_32323232_TYPELESS = 0x01
    RGBA_32323232_FLOAT = 0x02
    RGBA_32323232_UINT = 0x03
    RGBA_32323232_SINT = 0x04
    RGB_323232_TYPELESS = 0x05
    RGB_323232_FLOAT = 0x06
    RGB_323232_UINT = 0x07
    RGB_323232_SINT = 0x08
    RGBA_16161616_TYPELESS = 0x09
    RGBA_16161616_FLOAT = 0x0A
    RGBA_16161616_UNORM = 0x0B
    RGBA_16161616_UINT = 0x0C
    RGBA_16161616_SNORM = 0x0D
    RGBA_16161616_SINT = 0x0E
    RG_3232_TYPELESS = 0x0F
    RG_3232_FLOAT = 0x10
    RG_3232_UINT = 0x11
    RG_3232_SINT = 0x12
    RGX_32824_TYPELESS = 0x13
    DSX_32824_FLOAT_UINT = 0x14
    RXX_32824_FLOAT_TYPELESS = 0x15
    XGX_32824_TYPELESS_UINT = 0x16
    RGBA_1010102_TYPELESS = 0x17
    RGBA_1010102_UNORM = 0x18
    RGBA_1010102_UINT = 0x19
    RGB_111110_FLOAT = 0x1A
    RGBA_8888_TYPELESS = 0x1B
    RGBA_8888_UNORM = 0x1C
    RGBA_8888_UNORM_SRGB = 0x1D
    RGBA_8888_UINT = 0x1E
    RGBA_8888_SNORM = 0x1F
    RGBA_8888_SINT = 0x20
    RG_1616_TYPELESS = 0x21
    RG_1616_FLOAT = 0x22
    RG_1616_UNORM = 0x23
    RG_1616_UINT = 0x24
    RG_1616_SNORM = 0x25
    RG_1616_SINT = 0x26
    R_32_TYPELESS = 0x27
    D_32_FLOAT = 0x28
    R_32_FLOAT = 0x29
    R_32_UINT = 0x2A
    R_32_SINT = 0x2B
    RG_248_TYPELESS = 0x2C
    DS_248_UNORM_UINT = 0x2D
    RX_248_UNORM_TYPLESS = 0x2E
    XG_248_TYPLESS_UINT = 0x2F
    RG_88_TYPELESS = 0x30
    RG_88_UNORM = 0x31
    RG_88_UINT = 0x32
    RG_88_SNORM = 0x33
    RG_88_SINT = 0x34
    R_16_TYPELESS = 0x35
    R_16_FLOAT = 0x36
    D_16_UNORM = 0x37
    R_16_UNORM = 0x38
    R_16_UINT = 0x39
    R_16_SNORM = 0x3A
    R_16_SINT = 0x3B
    R_8_TYPELESS = 0x3C
    R_8_UNORM = 0x3D
    R_8_UINT = 0x3E
    R_8_SNORM = 0x3F
    R_8_SINT = 0x40
    A_8_UNORM = 0x41
    R_1_UNORM = 0x42
    RGBE_9995_SHARED_EXP = 0x43
    RGBG_8888_UNORM = 0x44
    GRGB_8888_UNORM = 0x45
    # S3TC / DXTn / BCn
    BC1_TYPELESS = 0x46
    BC1_UNORM = 0x47
    BC1_UNORM_SRGB = 0x48
    BC2_TYPELESS = 0x49
    BC2_UNORM = 0x4A
    BC2_UNORM_SRGB = 0x4B
    BC3_TYPELESS = 0x4C
    BC3_UNORM = 0x4D
    BC3_UNORM_SRGB = 0x4E
    BC4_TYPELESS = 0x4F
    BC4_UNORM = 0x50
    BC4_SNORM = 0x51
    BC5_TYPELESS = 0x52
    BC5_UNORM = 0x53
    BC5_SNORM = 0x54
    # uncompressed
    BGR_565_UNORM = 0x55
    BGRA_5551_UNORM = 0x56
    BGRA_8888_UNORM = 0x57
    BGRX_8888_UNORM = 0x58
    RGBA_1010102_XR_BIAS_UNORM = 0x59
    BGRA_8888_TYPELESS = 0x5A
    BGRA_8888_UNORM_SRGB = 0x5B
    BGRX_8888_TYPELESS = 0x5C
    BGRX_8888_UNORM_SRGB = 0x5D
    # BC6 & BC7
    BC6H_TYPELESS = 0x5E
    BC6H_UF16 = 0x5F
    BC6H_SF16 = 0x60
    BC7_TYPELESS = 0x61
    BC7_UNORM = 0x62
    BC7_UNORM_SRGB = 0x63
    # ancient formats
    AYUV = 0x64
    Y410 = 0x65
    Y416 = 0x66
    NV12 = 0x67
    P010 = 0x68
    P016 = 0x69
    OPAQUE_420 = 0x6A
    YUY2 = 0x6B
    Y210 = 0x6C
    Y216 = 0x6D
    NV11 = 0x6E
    AI44 = 0x6F
    IA44 = 0x70
    P_8 = 0x71
    AP_88 = 0x72
    BGRA_4444_UNORM = 0x73
    # NOTE: big gap of unofficial formats here
    P208 = 0x82
    V208 = 0x83
    V408 = 0x84
    # special
    SAMPLER_FEEDBACK_MIN_MIP_OPAQUE = 0xBD
    SAMPLER_FEEDBACK_MIP_REGION_USED_OPAQUE = 0xBE
    FORCE_UINT = 0xFFFFFFFF


bytes_per_pixel = {
    **{F: 4 for F in (
        DXGI.R_32_TYPELESS, DXGI.D_32_FLOAT, DXGI.R_32_FLOAT,
        DXGI.R_32_UINT, DXGI.R_32_SINT)},
    **{FF: 4 for FF in (
        DXGI.RG_248_TYPELESS, DXGI.DS_248_UNORM_UINT,
        DXGI.RX_248_UNORM_TYPLESS, DXGI.XG_248_TYPLESS_UINT)},
    **{RG: 2 for RG in (
        DXGI.RG_88_TYPELESS, DXGI.RG_88_UNORM, DXGI.RG_88_UINT,
        DXGI.RG_88_SNORM, DXGI.RG_88_SINT)},
    **{F: 2 for F in (
        DXGI.R_16_TYPELESS, DXGI.R_16_FLOAT, DXGI.D_16_UNORM,
        DXGI.R_16_UNORM, DXGI.R_16_UINT, DXGI.R_16_SNORM, DXGI.R_16_SINT)},
    **{F: 1 for F in (
        DXGI.R_8_TYPELESS, DXGI.R_8_UNORM, DXGI.R_8_UINT,
        DXGI.R_8_SNORM, DXGI.R_8_SINT, DXGI.A_8_UNORM)},
    DXGI.R_1_UNORM: 1/8,
    DXGI.RGBE_9995_SHARED_EXP: 4,
    DXGI.RGBG_8888_UNORM: 4,
    DXGI.GRGB_8888_UNORM: 4,
    **{RGBA: 16 for RGBA in (
        DXGI.RGBA_32323232_TYPELESS, DXGI.RGBA_32323232_FLOAT,
        DXGI.RGBA_32323232_UINT, DXGI.RGBA_32323232_SINT)},
    **{RGB: 12 for RGB in (
        DXGI.RGB_323232_TYPELESS, DXGI.RGB_323232_FLOAT,
        DXGI.RGB_323232_UINT, DXGI.RGB_323232_SINT)},
    **{RGBA: 8 for RGBA in (
        DXGI.RGBA_16161616_TYPELESS, DXGI.RGBA_16161616_FLOAT,
        DXGI.RGBA_16161616_UNORM, DXGI.RGBA_16161616_UINT,
        DXGI.RGBA_16161616_SNORM, DXGI.RGBA_16161616_SINT)},
    **{RG: 8 for RG in (
        DXGI.RG_3232_TYPELESS, DXGI.RG_3232_FLOAT,
        DXGI.RG_3232_UINT, DXGI.RG_3232_SINT)},
    **{BC1: 0.5 for BC1 in (
        DXGI.BC1_TYPELESS, DXGI.BC1_UNORM, DXGI.BC1_UNORM_SRGB)},
    # TODO: BC2
    **{BC: 1 for BC in (
        DXGI.BC3_TYPELESS, DXGI.BC3_UNORM, DXGI.BC3_UNORM_SRGB,
        DXGI.BC5_TYPELESS, DXGI.BC5_UNORM, DXGI.BC5_SNORM,
        DXGI.BC6H_TYPELESS, DXGI.BC6H_UF16, DXGI.BC6H_SF16)},
    # TODO: BC4
    # TODO: BC7
    DXGI.BGR_565_UNORM: 2,
    DXGI.BGRA_5551_UNORM: 2,
    **{BGRX: 4 for BGRX in (
        DXGI.BGRA_8888_UNORM, DXGI.BGRX_8888_UNORM,
        DXGI.RGBA_1010102_XR_BIAS_UNORM,
        DXGI.BGRA_8888_TYPELESS, DXGI.BGRA_8888_UNORM_SRGB,
        DXGI.BGRX_8888_TYPELESS, DXGI.BGRX_8888_UNORM_SRGB)},
    # TODO: ancient formats
    }


min_block_size = {
    DXGI.R_1_UNORM: 1,
    **{BC1: 8 for BC1 in (  # DXT1
        DXGI.BC1_TYPELESS, DXGI.BC1_UNORM, DXGI.BC1_UNORM_SRGB)},
    # TODO: BC2, 4 & 7
    **{BC: 16 for BC in (
        DXGI.BC3_TYPELESS, DXGI.BC3_UNORM, DXGI.BC3_UNORM_SRGB,
        DXGI.BC5_TYPELESS, DXGI.BC5_UNORM, DXGI.BC5_SNORM,
        DXGI.BC6H_TYPELESS, DXGI.BC6H_UF16, DXGI.BC6H_SF16)}}


# flag enums
class AlphaFlag(enum.IntFlag):
    UNKNOWN = 0x00
    STRAIGHT = 0x01
    PREMULTIPLIED = 0x02
    OPAQUE = 0x03
    CUSTOM = 0x04  # not used for transparency


class Dimension(enum.Enum):
    TEXTURE_1D = 0x02  # width
    TEXTURE_2D = 0x03  # width x height
    TEXTURE_3D = 0x04  # width x height x depth


class Flags(enum.IntFlag):
    CAPS = 0x00000001
    HEIGHT = 0x00000002
    WIDTH = 0x00000004
    PITCH = 0x00000008
    PIXEL_FORMAT = 0x00001000
    MIPMAPS = 0x00020000
    LINEAR_SIZE = 0x00080000
    DEPTH = 0x00800000


class MiscFlag(enum.IntFlag):
    CUBEMAP = 0x04
