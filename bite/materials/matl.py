from __future__ import annotations
import json
from typing import Dict

import breki

from . import base


# TODO: FriendlyFile "*.msw" & "*.uber"
class Matl(base.Material, breki.TextFile):
    exts = ["*.json"]
    textures: Dict[base.Slot, str]

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        # json -> Matl
        matl_json = json.load(self.stream)
        # TODO: ShaderSet & Subtype
        # textures
        # NOTE: base.Slot uses the indices we need
        matl_textures = matl_json.get("$textures", dict())
        matl_slot_names = matl_json.get("$textureTypes")
        for key, asset_path in matl_textures.items():
            int_key = int(key)
            if int_key in base.Slot:
                slot = base.Slot(int_key)
            else:
                slot = (int_key, matl_slot_names.get(key, None))
            self.textures[slot] = asset_path
            # NOTE: asset_path could be a GUID
