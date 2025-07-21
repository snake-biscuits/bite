from __future__ import annotations
import enum
from typing import Dict

import numpy as np


class Type(enum.Enum):
    PIXEL = 0
    BLOCK = 1  # BCn etc.
    INDEX = 2  # indexes a palette
    OTHER = 3  # VQ etc.


# TODO: dtype lookup table
# -- match to names & bit sizes
# -- UINT can be used agnostic of bit length


# TODO: generate PixelFormat -> PixelFormat converters
# -- using numpy to do array operations
# -- reordering based on name


class Format:
    channels: Dict[str, int]
    # ^ [("channel", num_bits)]
    # NOTE: order shouldn't change without us noticing
    dtype: np.dtype
    # TODO: also accept a custom class
    # -- e.g. UF16 (5-bit exponent, 11-bit mantissa)
    # TODO: metadata
    # -- colour_space: str  # enum?
    # -- is_hdr: bool

    # TODO: ask for a name, and generate if None
    def __init__(self, dtype=np.uint8, **channels):
        self.channels = channels
        self.dtype = dtype

    def __repr__(self) -> str:
        return f"<PixelFormat {self.name}>"

    @property
    def name(self) -> str:
        channels, bits = zip(self.channels.items())
        return "_".join([
            "".join(channels),
            "".join(map(str, bits))])
        # TODO: dtype name if not uint8
        # -- will need a lookup table
        # TODO: colour_space (e.g. SRGB)
        # -- not relevant for conversion atm, but important info

    @property
    def bits_per_pixel(self) -> int:
        return sum(bits for channel, bits in self.channels.items())

    @property
    def bytes_per_pixel(self) -> float:
        return self.bits_per_pixel / 8

    @classmethod
    def from_name(cls, name: str) -> Format:
        # TODO: optional args for dtype & metadata
        # NOTE: won't handle names like RGBA_32323232_FLOAT correctly
        if name.count("_") == 1:
            channels, bits = name.split("_")
        elif name.count("_") == 2:
            channels, bits, dtype = name.split("_")
        else:
            raise RuntimeError(f"Cannot determine format from name: '{name}'")
        return cls(dict(zip(channels, bits)))

    # TODO: bytes -> pixel array (np.array)
    def array_from_bytes(self, bytes) -> np.array:
        # we can do 1 dtype per pixel, or multiple
        # for twiddling we just want 1 entry per pixel
        # [[r,g,b], ...] vs. [b"rgb", ...]
        # should compare the performance cost
        ...


# copied from `view`: RGB_888 -> RGBA_8888
def rgb_to_rgba(rgb: bytes) -> bytes:
    rgb_array = np.frombuffer(rgb, dtype=np.uint8)
    rgb_pixels = rgb_array.reshape(rgb_array.size // 3, 3)
    rgba = np.insert(rgb_pixels, 3, 0xFF, axis=1).flatten()
    return rgba.tobytes()


# ^ good template for conversion
# - convert to array of dtypes
# -- np.frombuffer
# - reorder channel(s) [optional]
# -- dest[0::4] = source[0::3]
# - array of pixels [add channel(s) prerequisite]
# -- array.reshape
# - add channel(s) [optional]
# -- np.insert
# - convert to bytes
# -- return out.flatten().tobytes()
