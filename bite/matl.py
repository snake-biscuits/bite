from __future__ import annotations
import enum
import json
from typing import Dict

from . import base


class Slot(enum.Enum):
    ALBEDO = 0
    NORMAL = 1
    GLOSS = 2
    SPECULAR = 3
    ILLUMINATION = 4
    AMBIENT_OCCLUSION = 11
    CAVITY = 12
    OPACITY = 13
    DETAIL_ALBEDO = 14
    DETAIL_NORMAL = 15
    UV_DISTORTION = 18
    UV_DISTORTION_2 = 19
    BLEND = 22
    ALBEDO_2 = 23
    NORMAL_2 = 24
    GLOSS_2 = 25
    SPECULAR_2 = 26


class MATL(base.Material):
    textures: Dict[Slot, str]

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        matl_json = json.load(self.stream)
        matl_textures = matl_json.get("$textures", dict())
        matl_slot_names = matl_json.get("$textureTypes")
        for key, asset_path in matl_textures.items():
            int_key = int(key)
            if int_key in Slot:
                slot = Slot(int_key)
            else:
                slot = (int_key, matl_slot_names.get(key, None))
            self.textures[slot] = asset_path
            # NOTE: asset_path might be a GUID
