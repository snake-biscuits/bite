import io
import struct
from typing import Any, List, Union

import numpy as np


def read_struct(stream: io.BytesIO, format_: str) -> Union[Any, List[Any]]:
    byte_size = struct.calcsize(format_)
    raw_data = stream.read(byte_size)
    assert len(raw_data) == byte_size, "hit EOS"
    out = struct.unpack(format_, raw_data)
    if len(out) == 1:
        out = out[0]
    return out


def write_struct(stream: io.BytesIO, format_: str, *args):
    stream.write(struct.pack(format_, *args))


def rgb_to_rgba(rgb: bytes) -> bytes:
    rgb_array = np.frombuffer(rgb, dtype=np.uint8)
    rgb_pixels = rgb_array.reshape(rgb_array.size // 3, 3)
    rgba = np.insert(rgb_pixels, 3, 0xFF, axis=1).flatten()
    return rgba.tobytes()
