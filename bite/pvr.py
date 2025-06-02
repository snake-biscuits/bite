from __future__ import annotations
import io
from typing import Dict, Tuple, Union

from . import base
from .utils import read_struct, write_struct


class PVR(base.Texture):
    extension: str = "pvr"
    folder: str
    filename: str
    # header
    gbix: Union[bytes, None]
    flags: int
    format: Tuple[int, int]
    # ^ (pixel_format, texture_format)
    size: base.Size
    # pixel data
    mipmaps: Dict[base.MipIndex, bytes]
    # ^ {(mip_index, cubemap_index, side_index): b"raw_mipmap"}
    raw_data: Union[bytes, None]  # if mipmaps cannot be split
    # properties
    # is_cubemap: bool

    def __init__(self):
        super().__init__()
        # defaults
        self.gbix = None
        self.version = (0, 0)
        self.format = (0, 0)

    def __repr__(self) -> str:
        major, minor = self.version
        version = f"v{major}.{minor}"
        width, height = self.size
        size = f"{width}x{height}"
        return f"<PVR '{self.filename}' {version} {size} {self.format}>"

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
        out.version = read_struct(stream, "2H")
        out.format = read_struct(stream, "2B")  # pixel_format, texture_format
        assert read_struct(stream, "H") == 0  # padding
        out.size = read_struct(stream, "2H")
        # pixel data
        # if out.format == ...:
        #     mip_sizes = [
        #         max(1 << i, 4) ** 2
        #         for i in reversed(range(out.num_mipmaps))]
        #     if out.is_cubemap:
        #         assert out.array_size % 6 == 0
        #         out.mipmaps = {
        #             base.MipIndex(mip, frame, face): stream.read(mip_size)
        #             for frame in range(out.num_frames)
        #             for face in base.Face
        #             for mip, mip_size in enumerate(mip_sizes)}
        #     else:
        #         out.mipmaps = {
        #             base.MipIndex(mip, frame): stream.read(mip_size)
        #             for frame in out.array_size
        #             for mip, mip_size in enumerate(mip_sizes)}
        # else:
        # TODO: UserWarning("unknown pixel format, could not parse mips")
        out.raw_data = stream.read()
        return out
        # return out

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
