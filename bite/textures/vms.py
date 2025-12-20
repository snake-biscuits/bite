# http://mc.pp.se/dc/vms/icondata.html
from __future__ import annotations
from typing import Any, Dict

from PIL import Image
from PIL import ImageOps

import breki
from breki.binary import read_struct
from breki.files.parsed import parse_first

from . import base


class Vms(base.Texture, breki.BinaryFile):
    """Icon Data VMS for Sega Dreamcast VMU"""
    exts = ["*.vms"]
    # header
    desc: bytes
    mipmaps: Dict[str, Any]
    # mipmaps["monochrome"]: bytes  # 1-bit (inverted colour)
    # mipmaps["colour"]: Tuple[List[int], bytes]  # 16 colour ARGB16 palette
    is_cubemap: bool = property(lambda s: False)

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.desc = b""
        self.max_size = (32, 32)

    @parse_first
    def __repr__(self) -> str:
        mode = "colour" if len(self.mipmaps) == 2 else "monochrome"
        descriptor = f"32x32 {mode}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        self.desc = self.stream.read(16)
        monochrome_offset = read_struct(self.stream, "I")
        colour_offset = read_struct(self.stream, "I")
        # monchrome icon
        self.stream.seek(monochrome_offset)
        self.mipmaps["monochrome"] = self.stream.read(128)
        if colour_offset != 0:
            self.stream.seek(colour_offset)
            palette = read_struct(self.stream, "16H")
            indices = self.stream.read(512)
            self.mipmaps["colour"] = (palette, indices)

    def save_monochrome(self, filename: str):
        monochrome = self.mipmaps["monochrome"]
        img = ImageOps.invert(Image.frombytes("1", (32, 32), monochrome))
        img.save(filename)

    def save_colour(self, filename: str):
        if "colour" not in self.mipmaps:
            raise RuntimeError("no colour icon")
        int_palette, indices = self.mipmaps["colour"]
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
