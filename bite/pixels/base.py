from __future__ import annotations
import enum
from typing import Dict, List

import numpy as np


class Channel:
    name: str
    char: str
    bits: int
    # assuming 0-limit unsigned int per-channel
    # TODO: floating point
    # -- e.g. UF16 (5-bit exponent, 11-bit mantissa)

    def __init__(self, name, bits, char=None):
        self.name = name
        self.bits = bits
        self.char = name[0].upper() if char is None else char

    def __repr__(self) -> str:
        args = [self.name, self.bits]
        if self.char != self.name[0].upper():
            args.append(self.char)
        args = ", ".join(map(repr, args))
        return f"{self.__class__.__name__}({args})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Channel):
            return hash(self) == hash(other)
        return False

    def __hash__(self):
        return hash((self.name, self.bits, self.char))

    @property
    def mask(self) -> int:
        return (1 << self.bits) - 1

    # TODO: test on np.array
    # TODO: shift up to right & mask to fit a larger destination
    def extract(self, pixel_int, offset=0, out_size=None) -> int:
        out = (pixel_int >> offset) & self.mask
        if out_size is not None:
            mask = (1 << out_size) - 1
            if out_size > self.size:
                # NOTE: assumes out_size <= self.size * 2
                # -- will not expand A_1 -> A_8 etc.
                # -- there's gotta be a smarter way to expand channels
                out = out | out << (out_size - self.size)
            out = out & mask
        return out


class Stride(enum.Enum):
    """Format.dtype stride"""
    PIXEL = 0
    CHANNEL = 1


# NOTE: many Formats will have OpenGL internalformat equivalents
class Format:  # for pixel arrays
    channels: List[Channel]
    stride: Stride
    dtype: np.dtype

    def __init__(self, **channels):
        self.channels = [
            Channel(name, size)
            for name, size in channels.items()]
        self.dtype, self.stride = self.parser_for(self.channels)

    def __repr__(self) -> str:
        return f"<PixelFormat {self.name}>"

    @property
    def is_uniform(self) -> bool:
        return len(set(channel.bits for channel in self.channels)) == 1

    @staticmethod
    def parser_for(channels: List[Channel]) -> (np.dtype, Stride):
        dtypes = {32: np.uint32, 16: np.uint16, 8: np.uint8}
        channel_bits = [channel.bits for channel in channels]
        bpp = sum(channel_bits)
        if bpp in dtypes:
            return (dtypes[bpp], Stride.PIXEL)
        sizes = set(channel_bits)
        if len(sizes) == 1:
            bpc = list(sizes)[0]
            return (dtypes[bpc], Stride.CHANNEL)
        else:
            raise RuntimeError("cannot parse channels as array")

    @property
    def name(self) -> str:
        chars, bits = "", ""
        for channel in self.channels:
            chars += str(channel.char)
            bits += str(channel.bits)
        return f"{chars}_{bits}"

    @property
    def channel(self) -> Dict[str, Channel]:
        out = {
            channel.name: channel
            for channel in self.channels}
        out.update({
            channel.char: channel
            for channel in self.channels})
        return out

    @property
    def bits_per_pixel(self) -> int:
        return sum(channel.bits for channel in self.channels)

    @property
    def bytes_per_pixel(self) -> float:
        return self.bits_per_pixel / 8

    # TODO: pack / unpack channel

    def array_from(self, raw_pixels: bytes) -> np.array:
        """b"rgbrgb" -> [[r, g, b], [r, g, b]]"""
        num_channels = len(self.channels)
        num_pixels = (len(raw_pixels) * 8) // self.bits_per_pixel
        array = np.frombuffer(raw_pixels, self.dtype)
        if self.stride == Stride.PIXEL:
            # split into 1 dtype per channel
            assert array.size == num_pixels
            max_bits = max(channel.bits for channel in self.channels)
            dtypes = {
                0 < max_bits <= 8: (np.uint8, 0xFF),
                8 < max_bits <= 16: (np.uint16, 0xFFFF),
                16 < max_bits <= 32: (np.uint32, 0xFFFFFFFF)}
            dtype, mask = dtypes[True]
            out = np.empty((num_pixels * len(self.channels),), dtype=dtype)
            offset = 0
            i = num_channels
            for channel in reversed(self.channels):
                c = (array >> offset) & ((1 << channel.bits) - 1)
                if channel.bits not in (8, 16, 32):
                    c = (c | c << (max_bits - channel.bits)) & mask
                out[i::num_channels] = c
                offset += channel.bits
                i -= 1
            array = out
        return array.reshape((num_pixels, num_channels))

    def bytes_from(self, array: np.array) -> bytes:
        return array.flatten().tobytes()

    # TODO: add / remove alpha
    # -- assert "alpha" in channel[-1].name.lower()

    # NOTE: faster than matmul & doesn't edit input dtype
    def shuffle(self, pixels: np.array, new: Format) -> bytes:
        assert self.dtype == new.dtype
        assert self.stride == new.stride
        assert set(self.channels) == set(new.channels)
        pixels = pixels.transpose()
        pixels = np.array([
            pixels[self.channels.index(channel)]
            for channel in new.channels])
        return pixels.transpose()


class Layout(enum.Enum):
    PIXEL = 0  # flat pixel array
    TABLE = 1  # a series of flat component arrays
    BLOCK = 2  # blocks of pixels w/ interleaved components
    INDEX = 2  # flat array of indices into a palette


# NOTE: S3TC / DXT/ BCn are all block compression
# NOTE: VQ has a lookup table
# NOTE: YUV420 has a Y table & 1/2 res UV table (12bpp @ 8bpp Y)
# -- IMC2: Y (V,U) per-line [BLOCK]
# -- IMC4: Y (U,V) per-line [BLOCK]
# -- I420: Y U V per-frame [TABLE]
# -- YV12: Y V U per-frame [TABLE]
# -- NV12: Y (U,V) per-frame [TABLE]
# NOTE: YUV422 is made up of 2x1 BLOCKs (YUYV / UYUV)


# TODO: numpy.matmul colour space transforms
class Array:
    array: np.array
    format: Format
    layout = Layout.PIXEL
    # TODO: support more complex layouts
    # -- will probably require width & height
    # NOTE: sampling might be less memory intensive
    # -- uv coords range -> block(s) -> raw_pixels slices

    def __init__(self, fmt, array):
        self.format = fmt
        self.array = array

    def __repr__(self) -> str:
        descriptor = f"{self.format.name} {len(self.array)} pixels"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def as_bytes(self) -> bytes:
        pixels = np.array(
            list(map(self.format.pack, self.array)),
            dtype=self.format.dtype)
        return pixels.flatten().tobytes()

    # e.g. RGB_to_YUV_matrix, YUV_888
    def shift(self, matrix: np.array, out_fmt: Format):
        """linear transformation between colour spaces via matrix"""
        num_channels = len(self.format.channels)
        assert matrix.size == (num_channels, num_channels)
        assert len(out_fmt.channels) == num_channels
        # new_pixel = matrix * old_pixel
        array = np.matmul(matrix, self.array.transpose()).transpose()
        return Array(out_fmt, array)

    def shuffle(self, fmt: Format) -> Array:
        array = self.Format.shuffle(self.array, fmt)
        return Array(fmt, array)

    @classmethod
    def from_bytes(cls, fmt: Format, raw_pixels: bytes) -> Array:
        array = fmt.array_from(raw_pixels)
        return cls(fmt, array)
