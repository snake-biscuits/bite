from __future__ import annotations
import enum
import io
import os
from typing import Dict, Tuple, Union


Size = Tuple[int, int]
# ^ (width, height)


class Face(enum.Enum):
    """Cubemap Face Index; follows DirectX order"""
    # see: Microsoft Learn - Cubic Environment Mapping (Direct3D 9)
    RIGHT = 0  # X+
    LEFT = 1  # X-
    UP = 2  # Y+
    DOWN = 3  # Y-
    FRONT = 4  # Z+
    BACK = 5  # Z-


class MipIndex:
    mip: int  # 0 = largest
    frame: int
    face: Union[None, Face]

    def __init__(self, mip, frame=0, face=None):
        self.mip = mip
        self.frame = frame
        self.face = face

    def __repr__(self) -> str:
        args = [
            f"mip={self.mip!r}",
            f"frame={self.frame!r}"]
        if self.face is not None:
            args.append(f"face=Face.{self.face.name}")
        return f"{self.__class__.__name__}({', '.join(args)})"

    def __eq__(self, other) -> bool:
        if isinstance(other, MipIndex):
            return hash(self) == hash(other)
        return False

    def __hash__(self):
        return hash((self.mip, self.frame, self.face))

    def __iter__(self):
        return iter((self.mip, self.frame, self.face))


class Texture:
    extension: str = "ext"
    folder: str
    filename: str
    # header
    size: Tuple[int, int]  # dimensions of largest mipmap
    # data
    mipmaps: Dict[MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): b"raw_mipmap"}
    raw_data: Union[None, bytes]  # for when mips cannot be split
    # NOTE: texture should have (num_mipmaps, num_frames, is_cubemap)
    # -- this defines the full range of possible mipmaps keys

    def __init__(self):
        self.folder = ""
        self.filename = f"untitled.{self.extension}"
        self.mipmaps = dict()
        self.raw_data = None
        self.size = (0, 0)

    def __repr__(self) -> str:
        width, height = self.size
        size = "{width}x{height}"
        descriptor = f"'{self.filename}' {size} {len(self.mipmaps)} mipmaps"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    # read
    @classmethod
    def from_bytes(cls, raw_data: bytes) -> Texture:
        return cls.from_stream(io.BytesIO(raw_data))

    @classmethod
    def from_file(cls, path: str) -> Texture:
        with open(path, "rb") as texture_file:
            out = cls.from_stream(texture_file)
        out.folder, out.filename = os.path.split(path)
        return out

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Texture:
        raise NotImplementedError()

    # write
    def as_bytes(self) -> bytes:
        raise NotImplementedError()

    def save(self):
        path = os.path.join(self.folder, self.filename)
        self.save_as(path)

    def save_as(self, path: str):
        out = self.as_bytes()
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        with open(path, "wb") as texture_file:
            texture_file.write(out)
