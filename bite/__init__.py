__all__ = [
    "base", "decode", "pixel", "utils",
    "vmt",
    "dds", "pvr", "vms", "vtf",
    "Face", "Material", "MipIndex", "Size", "Texture",
    "VMT",
    "DDS", "PVR", "IconDataVMS", "VTF"]

# core
from . import base
from . import decode
from . import pixel
from . import utils
# material formats
from . import vmt
# texture formats (includes flag enums etc.)
from . import dds
from . import pvr
from . import vms
from . import vtf
# expose base
from .base import Face, Material, MipIndex, Size, Texture
# material classes
from .vmt import VMT
# texture classes
from .dds import DDS
from .pvr import PVR
from .vms import IconDataVMS
from .vtf import VTF

# extras
import importlib.util

# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "dearpygui")):
    from . import render  # noqa F401
    from . import view  # noqa F401

    __all__.extend(["render", "view"])
