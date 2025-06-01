# https://gist.github.com/leon-nn/cd4e3d50eb0fa23d8e197102f49f2cb3
import enum
# import os
from typing import Any, Dict, List, Tuple

import numpy as np
from OpenGL.error import GLError
import OpenGL.GL as gl
import OpenGL.GLUT as glut

from ..base import Size
from .. import dds
from .. import vtf


# NOTE: stored in OpenGL.GL.ARB.texture_compression_bptc
class BPTC(enum.Enum):
    """GL_ARB_texture_compression_bptc format enum"""
    # https://registry.khronos.org/OpenGL/extensions/ARB/ARB_texture_compression_bptc.txt
    RGBA = 0x8E8C  # COMPRESSED_RGBA_BPTC_UNORM_ARB
    SRGB = 0x8E8D  # COMPRESSED_SRGB_ALPHA_BPTC_UNORM_ARB
    SIGNED_FLOAT = 0x8E8E  # COMPRESSED_RGB_BPTC_SIGNED_FLOAT_ARB
    UNSIGNED_FLOAT = 0x8E8F  # COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_ARB


internal_format = {
    ".dds": {
        dds.DXGI.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)},
    ".vtf": {
        vtf.Format.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)}}
# ^ {".ext": {texture.format: (gl_format, is_compressed)}}


class Renderer:
    # core handles
    window: int
    vertex_buffer: int
    index_buffer: int
    shader: int
    # metadata
    size: Size
    # texture handles
    active_texture: int
    textures: Dict[Tuple[Size, int], int]
    # ^ {((width, height), format_): handle}

    def __init__(self, size, shaders, vertices, attribs, indices):
        # size: bite.Size
        # shaders: Dict[int, str]
        # ^ {gl.GL_VERTEX_SHADER: "vertex shader text"}
        # vertices: np.array(..., dtype=np.float32)
        # attribs: [(gl.GL_FLOAT, 3, False)]
        # indices: np.array(..., dtype=np.uint32)
        self.size = size
        glut.glutInit()
        self.window = glut.glutCreateWindow("GLUT")
        glut.glutHideWindow()
        self.print_metadata()
        # gl state
        gl.glViewport(0, 0, *size)
        gl.glClearColor(1, 0, 1, 1)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glClearDepth(1)
        gl.glFrontFace(gl.GL_CW)
        # gl objects
        self.init_framebuffer(size)
        self.init_geo(vertices, attribs, indices)
        self.init_shaders(shaders)
        # NOTE: user should add textures & set active texture before rendering
        self.textures = dict()
        self.active_texture = 0  # unbind

    def print_metadata(self):
        major = gl.glGetIntegerv(gl.GL_MAJOR_VERSION)
        minor = gl.glGetIntegerv(gl.GL_MINOR_VERSION)
        version = gl.glGetString(gl.GL_VERSION).decode()
        print(f"version: {major}.{minor} | {version}")
        assert major == 4 and minor >= 5, "not OpenGL 4.5 or later"
        vendor = gl.glGetString(gl.GL_VENDOR).decode()
        print(f"vendor: {vendor}")
        hardware = gl.glGetString(gl.GL_RENDERER).decode()
        print(f"hardware: {hardware}")
        extensions = [
            gl.glGetStringi(gl.GL_EXTENSIONS, i).decode()
            for i in range(gl.glGetIntegerv(gl.GL_NUM_EXTENSIONS))]
        print(f"{len(extensions)} extensions available")
        assert "GL_ARB_texture_compression_bptc" in extensions, "BC6 unsupported"
        # NOTE: ARB_shading_language_100 recommends looping until INVALID_ENUM
        glsl_versions = list()
        i = 0
        while True:
            try:
                glsl_versions.append(gl.glGetStringi(
                    gl.GL_SHADING_LANGUAGE_VERSION, i).decode())
                i += 1
            except GLError:
                break  # INVALID_ENUM; reached last version
        # NOTE: GLSL 1.00 uses an empty string for version
        # -- this is because "#version" declarations were added in 1.10
        # -- "100" is used for GLSL ES 1.00; there is no "100 es"
        print(f"{len(glsl_versions)} GLSL versions available")
        if len(glsl_versions) > 0:
            print(f"latest GLSL version: {glsl_versions[0]}")

    def add_texture(self, size, format_, data) -> int:
        # create texture
        if (size, format_) in self.textures:
            width, height = size
            # NOTE: format will be an int, we can't preserve the name here
            raise RuntimeError(f"already have a {width}x{height} ({format_}) texture")
        self.textures[(size, format_)] = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.textures[(size, format_)])
        # add data
        # TODO: cubemap faces
        # -- gl.GL_TEXTURE_CUBE_MAP_{POSI,NEGA}TIVE_{X,Y,Z}
        # TODO: force mip level when rendering
        # -- gl.glTextureParameteri(target, gl.GL_TEXTURE_{MIN,MAX}_LOD, mip)
        # TODO: identify if format is compressed or uncompressed
        gl.glCompressedTexImage2D(gl.GL_TEXTURE_2D, 0, format_, *size, 0, data)
        # pixelated filtering:
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        # TODO: GL_TEXTURE_WRAP_S, GL_MIRROR_CLAMP_TO_EDGE
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # unbind
        return self.textures[(size, format_)]

    def init_framebuffer(self, size):
        # create & bind frame buffer
        self.frame_buffer = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
        # colour texture
        self.render_texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.render_texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, *size, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # unbind
        # link to framebuffer
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.render_texture, 0)
        # depth buffer
        self.depth_buffer = gl.glGenRenderbuffers(1)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depth_buffer)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT, *size)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)  # unbind
        # link to framebuffer
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self.depth_buffer)
        # confirm framebuffer is complete
        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            # NOTE: this is bad, the GPU can't handle this config!
            raise RuntimeError(f"init_framebuffer failed: {status}")

    def init_geo(self, vertices: np.array, attribs: List[Any], indices: np.array):
        self.num_indices = indices.size
        # buffer data
        vertex_buffer, index_buffer = gl.glGenBuffers(2)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(vertices.tobytes()), vertices, gl.GL_STATIC_DRAW)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, len(indices.tobytes()), indices, gl.GL_STATIC_DRAW)
        # vertex attribs
        type_size = {
            gl.GL_FLOAT: 4}
        span = sum(
            type_size[type_] * size
            for type_, size, normalise in attribs)
        offset = 0
        for i, spec in enumerate(attribs):
            type_, size, normalise = spec
            normalise = (gl.GL_FALSE, gl.GL_TRUE)[normalise]
            gl.glEnableVertexAttribArray(i)
            # NOTE: PyOpenGL fails: "no valid context"
            # -- https://github.com/pygame/pygame/issues/3110
            # -- context can be 0 on wayland
            # -- editted PyOpenGL manually to fix this for now
            # -- might need to make a fork / PR
            gl.glVertexAttribPointer(i, size, type_, normalise, span, gl.GLvoidp(offset))
            offset += type_size[type_] * size

    def init_shaders(self, shaders: Dict[int, str]):
        self.shader = gl.glCreateProgram()
        stages = [
            (type_, source, gl.glCreateShader(type_))
            for type_, source in shaders.items()]
        for type_, source, stage in stages:
            gl.glShaderSource(stage, source)
            gl.glCompileShader(stage)
            compiled = gl.glGetShaderiv(stage, gl.GL_COMPILE_STATUS)
            if compiled == gl.GL_FALSE:
                log = gl.glGetShaderInfoLog(stage)
                print(log.decode())
                raise RuntimeError(f"{type_} failed to compile!")
            gl.glAttachShader(self.shader, stage)
        gl.glLinkProgram(self.shader)
        linked = gl.glGetProgramiv(self.shader, gl.GL_LINK_STATUS)
        if linked == gl.GL_FALSE:
            log = gl.glGetProgramInfoLog(self.shader)
            print(log.decode())
            raise RuntimeError("Shader Program failed to link")
        for type_, source, stage in stages:
            gl.glDetachShader(self.shader, stage)
            gl.glDeleteShader(stage)
        # NOTE: tried gl.GetProgramBinary
        # -- typical PyOpenGL schenanigans ensued

    def draw(self) -> np.array:
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glUseProgram(self.shader)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.active_texture)
        gl.glDrawElements(gl.GL_TRIANGLES, self.num_indices, gl.GL_UNSIGNED_INT, gl.GLvoidp(0))
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glUseProgram(0)
        # read pixels
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
        pixels = gl.glReadPixels(0, 0, *self.size, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        # return 1D array
        return np.frombuffer(pixels, dtype=np.uint8)
