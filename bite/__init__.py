__all__ = [
    "base", "utils",
    "dds", "vtf",
    "Face", "MipIndex", "Size", "Texture",
    "DDS", "VTF"]

# core
from . import base
from . import utils
# texture formats (includes flag enums etc.)
from . import dds
from . import vtf
# expose base
from .base import Face, MipIndex, Size, Texture
# texture classes
from .dds import DDS
from .vtf import VTF

# extras
import importlib
# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "numpy", "dearpygui")):
    from . import render
    from . import view

    __all__ = [*__all__, "render", "view"]
