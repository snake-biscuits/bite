__all__ = [
    "base", "decode", "pixels", "utils",
    "dds", "pvr", "vtf",
    "Face", "Material", "MipIndex", "Size", "Texture",
    "DDS", "PVR", "VTF"]

# core
from . import base
from . import decode
from . import pixels
from . import utils
# texture formats (includes flag enums etc.)
from . import dds
from . import pvr
from . import vtf
# expose base
from .base import Face, Material, MipIndex, Size, Texture
# texture classes
from .dds import DDS
from .pvr import PVR
from .vtf import VTF

# extras
import importlib.util

# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "dearpygui")):
    from . import render  # noqa F401
    from . import view  # noqa F401

    __all__.extend(["render", "view"])
