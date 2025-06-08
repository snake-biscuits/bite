# https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-file-layout-for-cubic-environment-maps
from __future__ import annotations
import enum
import io
import os
from typing import Dict, List, Union

from . import base
from .utils import read_struct, write_struct


class DXGI(enum.Enum):
    BC6H_UF16 = 0x5F  # the only format we care about


class DDS(base.Texture):
    extension: str = "dds"
    folder: str
    filename: str
    # header
    size: base.Size
    num_mipmaps: int
    # DX10 extended header
    format: DXGI
    resource_dimension: int  # always 3?
    misc_flag: int  # TODO: enum
    array_size: int
    # pixel data
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): raw_mipmap_data}
    raw_data: Union[bytes, None]  # if mipmaps cannot be split
    # properties
    is_cubemap: bool
    num_frames: int

    def __init__(self):
        super().__init__()
        # defaults
        self.array_size = 1
        self.format = DXGI.BC6H_UF16
        self.misc_flag = 0
        self.num_mipmaps = 0
        self.resource_dimension = 3

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
            child.array_size = 6 if is_cubemap else 1
            child.filename = f"{base_filename}.{i}.dds"
            child.format = self.format
            child.misc_flag = self.misc_flag
            child.num_mipmaps = self.num_mipmaps
            child.resource_dimension = self.resource_dimension
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
        return self.resource_dimension == 3

    @property
    def num_frames(self) -> int:
        if self.is_cubemap:
            return self.array_size // 6
        else:
            return self.array_size

    @num_frames.setter
    def num_frames(self, value: int):
        pass

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> DDS:
        out = cls()
        # header
        assert stream.read(4) == b"DDS "
        assert read_struct(stream, "2I") == (0x7C, 0x000A1007)  # version?
        out.size = read_struct(stream, "2I")
        assert read_struct(stream, "2I") == (0x00010000, 0x01)  # pitch / linsize?
        out.num_mipmaps = read_struct(stream, "I")
        assert stream.read(44) == b"\0" * 44
        assert read_struct(stream, "2I") == (0x20, 0x04)  # don't know, don't care
        # DX10 extended header
        assert stream.read(4) == b"DX10"
        assert stream.read(20) == b"\0" * 20
        assert read_struct(stream, "I") == 0x00401008  # idk, some flags?
        assert stream.read(16) == b"\0" * 16
        out.format = DXGI(read_struct(stream, "I"))
        out.resource_dimension = read_struct(stream, "I")
        out.misc_flag = read_struct(stream, "I")
        out.array_size = read_struct(stream, "I")
        assert stream.read(4) == b"\0" * 4  # reserved
        # pixel data
        if out.format == DXGI.BC6H_UF16:
            mip_sizes = [
                max(1 << i, 4) ** 2
                for i in reversed(range(out.num_mipmaps))]
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
                    for frame in out.array_size
                    for mip, mip_size in enumerate(mip_sizes)}
        else:
            # TODO: UserWarning("unknown pixel format, could not parse mips")
            out.raw_data = stream.read()
        return out

    def as_bytes(self) -> bytes:
        stream = io.BytesIO()
        # header
        write_struct(stream, "4s", b"DDS ")
        write_struct(stream, "2I", 0x7C, 0x000A1007)  # version?
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
        write_struct(stream, "I", self.resource_dimension)
        write_struct(stream, "I", self.misc_flag)
        write_struct(stream, "I", self.array_size)
        write_struct(stream, "4s", b"\0" * 4)  # reserved
        # mip data
        if isinstance(self.raw_data, bytes):
            stream.write(self.raw_data)
        else:
            if self.resource_dimension == 3:  # cubemap
                stream.write(b"".join([
                    self.mipmaps[base.MipIndex(mip, frame, face)]
                    for frame in range(self.array_size)
                    for face in base.Face
                    for mip in reversed(range(self.num_mipmaps))]))
            else:
                stream.write(b"".join([
                    self.mipmaps[base.MipIndex(mip, frame)]
                    for frame in range(self.array_size)
                    for mip in reversed(range(self.num_mipmaps))]))
        # stream -> bytes
        stream.seek(0)
        return stream.read()
