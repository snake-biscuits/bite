__all__ = [
    "base", "texture",
    "Renderer", "FrameBuffer2D"]

from . import base
from . import texture

from .base import Renderer
from .texture import FrameBuffer2D
# TODO: FrameBufferCube
# -- gl.GL_TEXTURE_CUBE_MAP_{POSI,NEGA}TIVE_{X,Y,Z}

# will FrameBufferCube need another script?
# is "texture" the best name for the FrameBuffer2D script?
# what's the goal here? defining scope should help focus in on names
