import io
import struct
from typing import Any, List, Union


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
