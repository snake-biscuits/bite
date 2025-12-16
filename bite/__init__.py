__all__ = [
    "decode", "materials", "pixels", "textures",
    "Material", "Slot",
    "Face", "MipIndex", "Size", "Texture",
    "Matl", "Vmt",
    "Dds", "Pvr", "Vms", "Vtf"]

# core
from . import decode
from . import materials
from . import pixels
from . import textures
# base classes / utils
from .materials import Material, Slot
from .textures import Face, MipIndex, Size, Texture
# formats
from .materials import Matl, Vmt
from .textures import Dds, Pvr, Vms, Vtf


# extras
import importlib.util

# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "dearpygui")):
    from . import render  # noqa F401
    from . import view  # noqa F401

    __all__.extend(["render", "view"])
