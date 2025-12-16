from __future__ import annotations
import enum
from typing import Dict, Tuple, Union

import breki


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


class Texture(breki.ParsedFile):
    # header
    max_size: Size  # dimensions of largest mipmap
    num_mipmaps: int
    num_frames: int
    # data
    mipmaps: Dict[MipIndex, bytes]
    # ^ {MipIndex(mip, frame, face): b"raw_mipmap"}
    raw_data: Union[None, bytes]  # for when mips cannot be split
    # NOTE: texture should have (num_mipmaps, num_frames, is_cubemap)
    # -- this defines the full range of possible mipmaps keys
    # properties
    is_cubemap: bool

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.mipmaps = dict()
        self.raw_data = None
        self.max_size = (0, 0)
        self.num_mipmaps = 0
        self.num_frames = 0

    def __repr__(self) -> str:
        width, height = self.max_size
        size = f"{width}x{height}"
        descriptor = f"'{self.filename}' {size} {len(self.mipmaps)} mipmaps"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    # utilities
    def default_index(self) -> MipIndex:
        face = Face(0) if self.is_cubemap else None
        return MipIndex(0, 0, face)

    def mip_size(self, index: MipIndex) -> Size:
        width, height = self.max_size
        width >>= index.mip
        height >>= index.mip
        return (width, height)

    # properties
    @property
    def is_cubemap(self):
        raise NotImplementedError()
