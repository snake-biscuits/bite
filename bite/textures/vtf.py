# https://developer.valvesoftware.com/wiki/VTF_(Valve_Texture_Format)
# https://github.com/NeilJed/VTFLib/blob/main/VTFLib/VTFFormat.h
from __future__ import annotations
import enum
import io
import math
import struct
from typing import Any, Dict, List, Tuple, Union

import breki
from breki.binary import read_struct, write_struct
from breki.files.parsed import parse_first

from . import base


class Format(enum.Enum):
    NONE = -1
    RGBA_8888 = 0
    ABGR_8888 = 1
    RGB_888 = 2
    BGR_888 = 3
    RGB_565 = 4
    I8 = 5
    IA_88 = 6
    P_8 = 7
    A_8 = 8
    RGB_888_BLUESCREEN = 9
    BGR_888_BLUESCREEN = 10
    ARGB_8888 = 11
    BGRA_8888 = 12
    DXT1 = 13
    DXT3 = 14
    DXT5 = 15
    BGRX_8888 = 16
    BGR_565 = 17
    BGRX_5551 = 18
    BGRA_4444 = 19
    DXT1_ONE_BIT_ALPHA = 20
    BGRA_5551 = 21
    UV_88 = 22
    UVWQ_8888 = 23
    RGBA_16161616F = 24
    RGBA_16161616 = 25
    UVLX_8888 = 26
    ...
    BC6H_UF16 = 66  # r2 / r5 cubemaps.hdr.vtf only


bytes_per_pixel = {
    Format.RGBA_8888: 32,
    Format.ABGR_8888: 32,
    Format.RGB_888: 24,
    Format.BGR_888: 24,
    Format.RGB_565: 16,
    Format.I8: 8,
    Format.IA_88: 16,
    Format.P_8: 8,
    Format.A_8: 8,
    Format.RGB_888_BLUESCREEN: 24,
    Format.BGR_888_BLUESCREEN: 24,
    Format.ARGB_8888: 32,
    Format.BGRA_8888: 32,
    Format.DXT1: 0.5,
    Format.DXT3: 1,
    Format.DXT5: 1,
    Format.BGRX_8888: 32,
    Format.BGR_565: 16,
    Format.BGRX_5551: 16,
    Format.BGRA_4444: 16,
    Format.DXT1_ONE_BIT_ALPHA: 0.5,
    # NOTE: same as DXT1, but transparent black appears in the palette
    Format.BGRA_5551: 16,
    Format.UV_88: 16,
    Format.UVWQ_8888: 32,
    Format.RGBA_16161616F: 64,
    Format.RGBA_16161616: 64,
    Format.UVLX_8888: 32,
    Format.BC6H_UF16: 1}


dxt_formats = (
    Format.DXT1,
    Format.DXT3,
    Format.DXT5,
    Format.DXT1_ONE_BIT_ALPHA,
    Format.BC6H_UF16)


def mip_data_size(size, level, format_) -> int:
    if format_ not in bytes_per_pixel:
        return None  # unknown
    width, height = size
    width >>= level
    height >>= level
    if format_ in dxt_formats:
        # round up to nearest full tile
        width = max(math.ceil(width / 4) * 4, 4)
        height = max(math.ceil(height / 4) * 4, 4)
    bpp = bytes_per_pixel[format_]
    return math.ceil(width * height * bpp)


class Flags(enum.IntFlag):
    POINT_SAMPLE = 0x00000001
    TRILINEAR = 0x00000002
    CLAMP_S = 0x00000004
    CLAMP_T = 0x00000008
    ANISOTROPIC = 0x00000010
    HINT_DXT5 = 0x00000020
    PWL_CORRECTED = 0x00000040
    NORMAL = 0x00000080
    NO_MIP = 0x00000100
    NO_LOD = 0x00000200
    ALL_MIPS = 0x00000400
    PROCEDURAL = 0x00000800
    ONE_BIT_ALPHA = 0x00001000
    EIGHT_BIT_ALPHA = 0x00002000
    ENVMAP = 0x00004000
    RENDER_TARGET = 0x00008000
    DEPTH_RENDER_TARGET = 0x00010000
    NO_DEBUG_OVERRIDE = 0x00020000
    SINGLE_COPY = 0x00040000
    PRE_SRGB = 0x00080000
    NO_DEPTH_BUFFER = 0x00800000
    CLAMP_U = 0x02000000
    VERTEX_TEXTURE = 0x04000000
    SSBUMP = 0x08000000
    BORDER = 0x20000000


class Resource:
    tag: bytes
    flags: int  # 0x2 = NO_DATA
    offset: int

    valid_tags = {
        b"\x01\x00\x00": "Thumbnail",
        b"\x30\x00\x00": "Image Data",
        b"\x10\x00\x00": "Sprite Sheet",
        b"CRC": "Cyclic Redundancy Check",
        b"CMA": "Cubemap Multiply Ambient",
        b"LOD": "Level of Detail Information",
        b"TSO": "Extended Flags",
        b"KVD": "Key Values Data"}

    def __init__(self, tag, flags, offset):
        self.tag = tag
        assert tag in self.valid_tags, tag
        if tag == b"CRC":
            assert flags == 0x02, "CRC Resource should only hold checksum"
            self.checksum = offset
        else:
            self.flags = flags
            self.offset = offset

    def __repr__(self) -> str:
        tag_type = self.valid_tags[self.tag]
        if self.tag == b"CRC":
            args = f"checksum=0x{self.checksum:08X}>"
        else:
            args = f"flags=0x{self.flags:02X} offset={self.offset}>"
        return f"<Resource | {tag_type} {args}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Resource:
        return cls(*read_struct(stream, "3sBI"))

    def as_bytes(self) -> bytes:
        if self.tag == b"CRC":
            flags, offset = 0x02, self.checksum
        else:
            flags, offset = self.flags, self.offset
        return struct.pack("3sBI", self.tag, flags, offset)


class VtfHeader(breki.Struct):
    magic: bytes  # b"VTF\0"
    version: Tuple[int, int]  # major, minor
    header_size: int  # in bytes, includes resources
    size: Tuple[int, int]  # width, height
    flags: Flags
    num_frames: int
    first_frame: int
    reflectivity: Tuple[float, float, float]  # rgb
    bumpmap_scale: int
    format: Format
    __slots__ = [
        "magic", "version", "header_size", "size",
        "flags", "num_frames", "first_frame",
        "padding_1", "reflectivity", "padding_2",
        "bumpmap_scale", "format"]
    _format = "4s3I2HI2H4s3f4sfI"
    _arrays = {
        "version": ["major", "minor"],
        "size": ["width", "height"],
        "reflectivity": [*"rgb"]}
    _classes = {
        "flags": Flags,
        "format": Format}


class Vtf(base.Texture, breki.BinaryFile):
    exts = ["*.vtf"]
    # header
    header: VtfHeader
    resources: List[Resource]
    cma: Union[None, CMA]
    # essentials
    size: base.Size
    num_frames: int
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): b"raw_mipmap"}
    raw_data: Union[None, bytes]
    # properties
    as_json: Dict[str, Any]
    is_cubemap: bool

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        # TODO: default header
        self.cma = None
        self.header = None
        self.resources = list()

    @parse_first
    def __repr__(self) -> str:
        major, minor = self.header.version
        version = f"v{major}.{minor}"
        width, height = self.max_size
        size = f"{width}x{height}"
        format_ = self.header.format
        flags = self.header.flags
        return f"<VTF {version} '{self.filename}' {size} {format_.name} flags={flags.name}>"

    @parse_first
    def mip_size(self, mip_index: base.MipIndex) -> base.Size:
        if mip_index == "thumbnail":
            return self.thumbnail_size
        else:
            return super().mip_size(mip_index)

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        assert self.stream.read(4) == b"VTF\0"
        major, minor = read_struct(self.stream, "2I")  # format version
        if major != 7 or minor > 5:
            raise NotImplementedError(f"Vtf v{major}.{minor} is not supported!")
        self.stream.seek(-12, 1)
        self.header = VtfHeader.from_stream(self.stream)
        assert self.header.padding_1 == b"\0" * 4
        assert self.header.padding_2 == b"\0" * 4
        # expose the essentials
        self.max_size = tuple(self.header.size)
        self.num_frames = self.header.num_frames
        # funky alignment
        self.num_mipmaps = read_struct(self.stream, "B")
        self.thumbnail_format = Format(read_struct(self.stream, "i"))
        self.thumbnail_size = read_struct(self.stream, "2B")
        if minor == 1:  # v7.1
            assert self.stream.read(1) == b"\0"  # padding
        if minor >= 2:  # v7.2+
            self.mipmap_depth = read_struct(self.stream, "H")
        if minor >= 3:  # v7.3+
            assert self.stream.read(3) == b"\0" * 3
            num_resources = read_struct(self.stream, "I")
            assert self.stream.read(8) == b"\0" * 8
            resources = [
                Resource.from_stream(self.stream)
                for i in range(num_resources)]
            self.resources = {
                Resource.valid_tags[resource.tag]: resource
                for resource in resources}
        assert self.stream.tell() == self.header.header_size
        # CMA
        if "Cubemap Multiply Ambient" in self.resources:
            self.cma = CMA.from_vtf_stream(self, self.stream)
            self.stream.seek(self.header.header_size)
        # check assumptions
        assert self.header.first_frame == 0
        # thumbnail
        if "Thumbnail" in self.resources:
            self.stream.seek(self.resources["Thumbnail"].offset)
        if self.thumbnail_format == Format.NONE:
            assert self.thumbnail_size == (0, 0)
        elif self.thumbnail_format in bytes_per_pixel:
            assert self.thumbnail_size != (0, 0)
            self.mipmaps["thumbnail"] = self.stream.read(mip_data_size(
                self.thumbnail_size, 0, self.thumbnail_format))
        else:  # thumbnail w/ unknown bpp & mbs
            # TODO: compare mip_sizes against total filesize
            # -- whatever is left must be the thumbnail size
            # TODO: UserWarning(f"Unknown bpp for format: {self.thumbnail_format}")
            self.raw_data = self.stream.read()
            return
        # seek to start of mipmaps
        if "Image Data" in self.resources:
            self.stream.seek(self.resources["Image Data"].offset)
        # use raw_data if bytes_per_pixel is unknown
        if self.header.format not in bytes_per_pixel:
            # TODO: UserWarning(f"Unknown bpp for format: {self.header.format}")
            self.raw_data = self.stream.read()
            return
        # calculate mip_sizes
        mip_sizes = [
            mip_data_size(self.max_size, i, self.header.format)
            for i in range(self.num_mipmaps)]
        # read mipmaps
        if self.is_cubemap:
            self.mipmaps.update({
                base.MipIndex(mip, frame, face): self.stream.read(mip_size)
                for mip, mip_size in reversed([*enumerate(mip_sizes)])
                for frame in range(self.num_frames)
                for face in base.Face})
        else:
            self.mipmaps.update({
                base.MipIndex(mip, frame, None): self.stream.read(mip_size)
                for mip, mip_size in reversed([*enumerate(mip_sizes)])
                for frame in range(self.num_frames)})

    @property
    @parse_first
    def as_json(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "max_size": self.max_size,
            "flags": self.flags.name,
            "num_frames": self.num_frames,
            "first_frame": self.first_frame,
            "reflectivity": self.reflectivity,
            "bumpmap_scale": self.bumpmap_scale,
            "format": self.format.name,
            "num_mipmaps": self.num_mipmaps,
            "low_res_format": self.low_res_format.name,
            "low_res_size": self.low_res_size,
            "mipmap_depth": self.mipmap_depth,
            "resources": {k: str(v) for k, v in self.resources.items()},
            "cma": self.cma.as_json if self.cma is not None else None}

    @property
    @parse_first
    def is_cubemap(self) -> bool:
        return Flags.ENVMAP in self.header.flags

    @parse_first
    def as_bytes(self) -> bytes:
        stream = io.BytesIO()
        # header
        header_size = 80 + len(self.resources) * 8
        self.header.header_size = header_size
        stream.write(self.header.as_bytes())
        write_struct(stream, "B", self.num_mipmaps)
        write_struct(stream, "i", self.low_res_format.value)
        write_struct(stream, "2B", *self.low_res_size)
        # v7.2+
        write_struct(stream, "H", self.mipmap_depth)
        # v7.3+
        stream.write(b"\0" * 3)
        write_struct(stream, "I", len(self.resources))
        stream.write(b"\0" * 8)
        # resources
        # TODO: verify / calculate resource offsets
        offset = header_size  # vtf_header + 8 bytes per resource
        if "Cyclic Redundancy Check" in self.resources:
            # TODO: save crc32 in self.resources["Cyclic Redundany Check"].offset
            raise NotImplementedError("idk how to generate CRC")
        if "Cubemap Multiply Ambient" in self.resources:
            assert self.cma is not None
            assert len(self.cma.data) == self.num_frames
            if self.num_frames == 1:
                self.resources["Cubemap Multiply Ambient"].flags = 0x02
                cma_0 = struct.pack("f", self.cma.data[0])
                self.resources["Cubemap Multiply Ambient"].offset = cma_0
            else:
                self.resources["Cubemap Multiply Ambient"].flags = 0x00
                self.resources["Cubemap Multiply Ambient"].offset = offset
                offset += (self.num_frames + 1) * 4
        # NOTE: Image Data is always last!
        if "Image Data" in self.resources:
            self.resources["Image Data"].offset = offset
        stream.write(b"".join(r.as_bytes() for r in self.resources.values()))
        assert stream.tell() == header_size
        # cma
        if self.cma is not None:
            stream.write(self.cma.as_bytes())
        # mip data
        assert "Image Data" in self.resources
        assert self.resources["Image Data"].offset == stream.tell()
        # TODO: check .is_cubemap & use alternate packing
        assert Flags.ENVMAP in self.header.flags
        if isinstance(self.raw_data, bytes):
            stream.write(self.raw_data)
        else:
            stream.write(b"".join([
                self.mipmaps[base.MipIndex(mip, frame, face)]
                for mip in range(self.num_mipmaps)
                for frame in range(self.num_frames)
                for face in range(6)]))
        # stream -> bytes
        stream.seek(0)
        return stream.read()


class CMA:
    """same data as rBSP v48 CUBEMAPS_AMBIENT_RCP"""
    data: List[float]

    def __repr__(self) -> str:
        return f"<CMA with {len(self.data)} entries at 0x{id(self):012X}>"

    def as_bytes(self) -> bytes:
        if len(self.data) == 1:
            return b""  # CMA will be stored in Resource.offset
        return struct.pack(
            f"I{len(self.data)}f",
            len(self.data) * 4,
            *self.data)

    @classmethod
    def from_data(cls, *data: List[float]):
        out = cls()
        out.data = data
        return out

    @classmethod
    def from_vtf_stream(cls, vtf: Vtf, stream: io.BytesIO):
        resource = vtf.resources["Cubemap Multiply Ambient"]
        out = cls()
        if resource.flags == 0x02:  # single entry saved in offset
            raw_cma = struct.pack("I", resource.offset)
            out.data = struct.unpack("f", raw_cma)
        else:
            stream.seek(resource.offset)
            size, *out.data = read_struct(stream, f"I{vtf.num_frames}f")
            assert size == vtf.num_frames * 4
        return out

    @property
    def as_json(self) -> List[str]:
        return list(self.data)
