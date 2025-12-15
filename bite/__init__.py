__all__ = [
    "base", "decode", "pixel",
    "vmt",
    "dds", "pvr", "vms", "vtf",
    "Face", "Material", "MipIndex", "Size", "Texture",
    "VMT",
    "Dds", "PVR", "IconDataVMS", "Vtf"]

# core
from . import base
from . import decode
from . import pixel
# material formats
# from . import matl
from . import vmt
# texture formats (includes flag enums etc.)
from . import dds
from . import pvr
from . import vms
from . import vtf
# expose base
from .base import Face, Material, MipIndex, Size, Texture
# material classes
# from .matl import MATL
from .vmt import VMT
# texture classes
from .dds import Dds
from .pvr import PVR
from .vms import IconDataVMS
from .vtf import Vtf

# extras
import importlib.util

# viewer
if all(importlib.util.find_spec(dependency) is not None
       for dependency in ("OpenGL", "dearpygui")):
    from . import render  # noqa F401
    from . import view  # noqa F401

    __all__.extend(["render", "view"])
