from __future__ import annotations
import enum
from typing import Dict

import breki


# TODO: FriendlyFile for linking shader & textures
class Material(breki.ParsedFile):
    is_transparent: bool
    shader: str
    textures: Dict[Slot, str]
    # ^ {Slot: "local/path"}

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.shader = None
        self.is_transparent = False
        self.textures = dict()

    def __repr__(self) -> str:
        descriptor = " ".join([
            f"'{self.filename}'",
            f"{self.shader}",
            f"{len(self.textures)} textures"])
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"


# NOTE: starting from MATL (WLD) slot indices
class Slot(enum.Enum):
    ALBEDO = 0
    NORMAL = 1
    GLOSS = 2
    SPECULAR = 3
    ILLUMINATION = 4
    ...
    AMBIENT_OCCLUSION = 11
    CAVITY = 12
    OPACITY = 13
    DETAIL_ALBEDO = 14
    DETAIL_NORMAL = 15
    ...
    UV_DISTORTION = 18
    UV_DISTORTION_2 = 19
    ...
    BLEND = 22
    ALBEDO_2 = 23
    NORMAL_2 = 24
    GLOSS_2 = 25
    SPECULAR_2 = 26
