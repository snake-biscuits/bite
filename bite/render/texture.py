from __future__ import annotations
import enum

import numpy as np
import OpenGL.GL as gl

from ..base import Face, MipIndex, Size, Texture
from .. import dds
from .. import vtf
from . import base


# NOTE: stored in OpenGL.GL.ARB.texture_compression_bptc
class BPTC(enum.Enum):
    """GL_ARB_texture_compression_bptc format enum"""
    # https://registry.khronos.org/OpenGL/extensions/ARB/ARB_texture_compression_bptc.txt
    RGBA = 0x8E8C  # COMPRESSED_RGBA_BPTC_UNORM_ARB
    SRGB = 0x8E8D  # COMPRESSED_SRGB_ALPHA_BPTC_UNORM_ARB
    SIGNED_FLOAT = 0x8E8E  # COMPRESSED_RGB_BPTC_SIGNED_FLOAT_ARB
    UNSIGNED_FLOAT = 0x8E8F  # COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_ARB


def internal_format(texture: Texture) -> (int, bool):
    format_for = {
        "dds": {
            dds.DXGI.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)},
        "vtf": {
            vtf.Format.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)}}
    # ^ {"ext": {texture.format: (gl_format, is_compressed)}}
    return format_for[texture.extension][texture.format]


class FrameBuffer2D(base.Renderer):
    """render a single texture, filling the viewport"""
    texture0: int

    # TODO: update texture mips

    def init_texture_2d(self, size: Size, fmt: int, is_compressed: bool, data: bytes):
        self.texture0 = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture0)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        if is_compressed:
            gl.glCompressedTexImage2D(gl.GL_TEXTURE_2D, 0, fmt, *size, 0, data)
        else:
            # NOTE: using GL_RGB because RGBA is hard
            # -- difficult, but not impossible
            fmt2 = gl.GL_RGB
            type_ = gl.GL_UNSIGNED_BYTE
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, fmt, *size, 0, fmt2, type_, data)
        # NOTE: don't unbind texture

    @classmethod
    def from_texture(cls, texture: Texture) -> FrameBuffer2D:
        # TODO: get texture.is_compressed & internal_format first
        # -- that will help us pick shaders & extensions
        out = cls(
            texture.max_size,
            np.array([
                -1, -1,
                +1, -1,
                +1, +1,
                -1, +1], dtype=np.float32),
            [(gl.GL_FLOAT, 2, False)],
            np.array([
                0, 1, 2,
                0, 2, 3], dtype=np.uint32),
            {"vertex": "basic_2d", "fragment": "hdr"})
        # TODO: methods for adding the texture & binding it for rendering
        assert out.context.matches_version(4, 5)
        assert out.context.has_extension("GL_ARB_texture_compression_bptc")
        assert out.context.supports_glsl("450")
        out.texture = texture  # keep a copy
        # add data
        size = texture.max_size
        format_, is_compressed = internal_format(texture)
        data = texture.mipmaps[MipIndex(0, 0, Face(0))]
        out.init_texture_2d(size, format_, is_compressed, data)
        return out
