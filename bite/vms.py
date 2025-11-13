# http://mc.pp.se/dc/vms/icondata.html
from __future__ import annotations
import io
from typing import List

from PIL import Image
from PIL import ImageOps

from . import base
from .utils import read_struct


class IconDataVMS(base.Texture):
    extension: str = "vtf"
    folder: str
    filename: str
    # header
    desc: bytes
    # pixels
    monochrome: bytes  # 32x32 1-bit image (inverted)
    colour_palette: List[int]
    colour_indices: bytes  # 32x32 16 colour image (ARGB16)

    def __init__(self):
        super().__init__()
        self.desc = b""

    def __repr__(self) -> str:
        mode = "colour" if len(self.mipmaps) == 2 else "monochrome"
        descriptor = f"32x32 {mode}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> IconDataVMS:
        out = cls()
        out.size = (32, 32)
        out.desc = stream.read(16)
        monochrome_offset = read_struct(stream, "I")
        colour_offset = read_struct(stream, "I")
        # monchrome icon
        stream.seek(monochrome_offset)
        out.mipmaps[base.MipIndex(0, 0)] = stream.read(128)
        out.monochrome = stream.read(128)
        if colour_offset != 0:
            stream.seek(colour_offset)
            palette = read_struct(stream, "16H")
            indices = stream.read(512)
            out.mipmaps[base.MipIndex(0, 1)] = (palette, indices)
        return out

    def save_monochrome(self, filename: str):
        monochrome = self.mipmaps[base.MipIndex(0, 0)]
        img = ImageOps.invert(Image.frombytes("1", (32, 32), monochrome))
        img.save(filename)

    def save_colour(self, filename: str):
        if base.MipIndex(0, 1) not in self.mipmaps:
            raise RuntimeError("no colour icon")
        int_palette, indices = self.mipmaps[base.MipIndex(0, 1)]
        assert len(int_palette) == 16
        assert len(indices) == 512
        palette = list()
        pixels = list()
        for c in int_palette:
            a = c >> 0xC & 0xF
            r = c >> 0x8 & 0xF
            g = c >> 0x4 & 0xF
            b = c >> 0x0 & 0xF
            a = a | a << 4
            r = r | r << 4
            g = g | g << 4
            b = b | b << 4
            rgba = bytes([r, g, b, a])
            palette.append(rgba)
        for index in indices:
            pixels.append(palette[index >> 4])
            pixels.append(palette[index & 15])
        Image.frombytes("RGBA", (32, 32), b"".join(pixels)).save(filename)
