__all__ = [
    "base", "utils",
    "dds", "pvr", "vtf",
    "Face", "MipIndex", "Size", "Texture",
    "DDS", "PVR", "VTF"]

# core
from . import base
from . import utils
# texture formats (includes flag enums etc.)
from . import dds
from . import pvr
from . import vtf
# expose base
from .base import Face, MipIndex, Size, Texture
# texture classes
from .dds import DDS
from .pvr import PVR
from .vtf import VTF

# extras
import importlib.util

# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "numpy", "dearpygui")):
    from . import render  # noqa F401
    from . import view  # noqa F401

    __all__.extend(["render", "view"])

# decode
if importlib.util.find_spec("numpy") is not None:
    from . import decode  # noqa F401

    __all__.append("decode")
