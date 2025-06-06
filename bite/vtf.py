# https://developer.valvesoftware.com/wiki/VTF_(Valve_Texture_Format)
# https://github.com/NeilJed/VTFLib/blob/main/VTFLib/VTFFormat.h
from __future__ import annotations
import enum
import io
import struct
from typing import Any, Dict, List, Tuple, Union

from . import base
from .utils import read_struct, write_struct


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
    Format.DXT1: 0.5,  # 8 bytes, 4x4 pixels
    Format.DXT3: ...,
    Format.DXT5: ...,
    Format.BGRX_8888: 32,
    Format.BGR_565: 16,
    Format.BGRX_5551: 16,
    Format.BGRA_4444: 16,
    Format.DXT1_ONE_BIT_ALPHA: ...,
    Format.BGRA_5551: 16,
    Format.UV_88: 16,
    Format.UVWQ_8888: 32,
    Format.RGBA_16161616F: 64,
    Format.RGBA_16161616: 64,
    Format.UVLX_8888: 32,
    Format.BC6H_UF16: 1}


min_block_size = {
    Format.DXT1: 8,  # 4 byte palette + 4 byte indices
    Format.DXT3: ...,
    Format.DXT5: ...,
    Format.DXT1_ONE_BIT_ALPHA: ...,
    Format.BC6H_UF16: 16}


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
            return f"<Resource | {tag_type} checksum=0x{self.checksum:08X}>"
        else:
            return f"<Resource | {tag_type} flags=0x{self.flags:02X} offset={self.offset}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Resource:
        return cls(*read_struct(stream, "3sBI"))

    def as_bytes(self) -> bytes:
        return struct.pack("3sBI", self.tag, self.flags, self.offset)


class VTF(base.Texture):
    extension: str = "vtf"
    folder: str
    filename: str
    # header
    version: Tuple[int, int]  # major, minor
    size: base.Size
    flags: Flags
    num_frames: int
    first_frame: int
    reflectivity: Tuple[float, float, float]  # rgb
    bumpmap_scale: int
    format: Format
    num_mipmaps: int
    low_res_format: Format
    low_res_size: base.Size
    resources: List[Resource]
    cma: Union[None, CMA]
    # pixel data
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): b"raw_mipmap"}
    raw_data: Union[None, bytes]
    # properties
    as_json: Dict[str, Any]
    is_cubemap: bool

    def __init__(self):
        super().__init__()
        # defaults
        self.version = (7, 5)
        self.format = Format.NONE
        self.flags = Flags(0x00)  # self.flags.name will be a blank string
        self.cma = None

    def __repr__(self) -> str:
        major, minor = self.version
        version = f"v{major}.{minor}"
        width, height = self.size
        size = f"{width}x{height}"
        return f"<VTF {version} '{self.filename}' {size} {self.format.name} flags={self.flags.name}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> VTF:
        out = cls()
        assert stream.read(4) == b"VTF\0"
        out.version = read_struct(stream, "2I")
        if out.version != (7, 5):
            raise NotImplementedError(f"v{out.version[0]}.{out.version[1]} is not supported!")
        header_size = read_struct(stream, "I")
        out.size = read_struct(stream, "2H")
        out.flags = Flags(read_struct(stream, "I"))
        out.num_frames, out.first_frame = read_struct(stream, "2H")
        assert stream.read(4) == b"\0" * 4
        out.reflectivity = read_struct(stream, "3f")
        assert stream.read(4) == b"\0" * 4
        out.bumpmap_scale = read_struct(stream, "f")
        out.format = Format(read_struct(stream, "I"))
        out.num_mipmaps = read_struct(stream, "B")
        out.low_res_format = Format(read_struct(stream, "i"))
        out.low_res_size = read_struct(stream, "2B")
        # v7.2+
        out.mipmap_depth = read_struct(stream, "H")
        # v7.3+
        assert stream.read(3) == b"\0" * 3
        num_resources = read_struct(stream, "I")
        assert stream.read(8) == b"\0" * 8
        resources = [
            Resource.from_stream(stream)
            for i in range(num_resources)]
        out.resources = {
            Resource.valid_tags[resource.tag]: resource
            for resource in resources}
        assert stream.tell() == header_size
        # CMA
        if "Cubemap Multiply Ambient" in out.resources:
            out.cma = CMA.from_vtf_stream(out, stream)
            stream.seek(header_size)
        # mipmaps
        assert Flags.ENVMAP in out.flags
        assert out.low_res_format == Format.NONE
        assert out.low_res_size == (0, 0)
        assert out.first_frame == 0
        assert "Image Data" in out.resources
        stream.seek(out.resources["Image Data"].offset)
        # TODO: r1o 32x32 Format.DXT5 "cubemapdefault.vtf" (LDR)
        # TODO: r1o 32x32 Format.RGBA_16161616F "cubemapdefault.hdr.vtf" (HDR)
        # -- mip bytes are all zero afaik
        # Titanfall
        if out.format == Format.RGBA_8888 and out.size == (64, 64):
            mip_sizes = [
                (1 << i) ** 2 * 4
                for i in reversed(range(out.num_mipmaps))]
        # Titanfall 2 / Apex Legends
        elif out.format == Format.BC6H_UF16 and out.size == (256, 256):
            mip_sizes = [
                max(1 << i, 4) ** 2
                for i in reversed(range(out.num_mipmaps))]
        else:
            # TODO: UserWarning("unknown pixel format, could not parse mips")
            out.raw_data = stream.read()
            return out
        # parse mipmaps
        # mip.X-side.0-cubemap.0 ... mip.0-side.5-cubemap.X
        out.mipmaps = {
            base.MipIndex(mip, frame, face): stream.read(mip_size)
            for mip, mip_size in reversed([*enumerate(mip_sizes)])
            for frame in range(out.num_frames)
            for face in base.Face}
        return out

    @property
    def as_json(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "size": self.size,
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
    def is_cubemap(self) -> bool:
        return Flags.ENVMAP in self.flags

    def as_bytes(self) -> bytes:
        stream = io.BytesIO()
        # header
        stream.write(b"VTF\0")
        write_struct(stream, "2I", *self.version)
        header_size = 80 + len(self.resources) * 8
        write_struct(stream, "I", header_size)
        write_struct(stream, "2H", *self.size)
        write_struct(stream, "I", self.flags.value)
        write_struct(stream, "2H", self.num_frames, self.first_frame)
        stream.write(b"\0" * 4)
        write_struct(stream, "3f", *self.reflectivity)
        stream.write(b"\0" * 4)
        write_struct(stream, "f", self.bumpmap_scale)
        write_struct(stream, "I", self.format.value)
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
        assert Flags.ENVMAP in self.flags
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
    def from_vtf_stream(cls, vtf: VTF, vtf_file: io.BytesIO):
        resource = vtf.resources["Cubemap Multiply Ambient"]
        out = cls()
        if resource.flags == 0x02:  # single entry saved in offset
            raw_cma = struct.pack("I", resource.offset)
            out.data = struct.unpack("f", raw_cma)
        else:
            vtf_file.seek(resource.offset)
            size, *out.data = read_struct(vtf_file, f"I{vtf.num_frames}f")
            assert size == vtf.num_frames * 4
        return out

    @property
    def as_json(self) -> List[str]:
        return list(self.data)
