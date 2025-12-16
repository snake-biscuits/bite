# https://gist.github.com/leon-nn/cd4e3d50eb0fa23d8e197102f49f2cb3
# https://learnopengl.com
import os
from typing import Dict, List, Tuple, Union

import numpy as np
from OpenGL.error import GLError
import OpenGL.GL as gl
import OpenGL.GLUT as glut

from ..textures.base import Size


ShaderDict = Dict[str, str]
# ^ {"type": "basename"}
Vertices = List[Union[float, int]]
Attrib = Tuple[int, int, bool]
# ^ (gl.GL_TYPE, count, should_normalise)


class ContextSpec:
    """for checking OpenGL context can provide the features we need"""
    major: int
    minor: int
    version: str  # may contain additional details
    vendor: str
    hardware: str  # GL_RENDERER
    extensions: List[str]
    glsl_versions: List[str]
    # NOTE: GLSL 1.00 uses an empty string for version
    # -- this is because "#version" declarations were added in 1.10
    # -- "100" is used for GLSL ES 1.00; there is no "100 es"

    def __init__(self):
        """must be created in an active OpenGL context"""
        self.major = gl.glGetIntegerv(gl.GL_MAJOR_VERSION)
        self.minor = gl.glGetIntegerv(gl.GL_MINOR_VERSION)
        self.version = gl.glGetString(gl.GL_VERSION).decode()
        self.vendor = gl.glGetString(gl.GL_VENDOR).decode()
        self.hardware = gl.glGetString(gl.GL_RENDERER).decode()
        # TODO: memory limit
        self.extensions = [
            gl.glGetStringi(gl.GL_EXTENSIONS, i).decode()
            for i in range(gl.glGetIntegerv(gl.GL_NUM_EXTENSIONS))]
        # NOTE: ARB_shading_language_100 recommends looping until INVALID_ENUM
        self.glsl_versions = list()
        i = 0
        while True:
            try:
                self.glsl_versions.append(
                    gl.glGetStringi(gl.GL_SHADING_LANGUAGE_VERSION, i).decode())
                i += 1
            except GLError:
                break  # INVALID_ENUM; reached last version

    def __repr__(self) -> str:
        version = f"OpenGL {self.major}.{self.minor}"
        extensions = f"{len(self.extensions)} extensions"
        glsl = f"GLSL {self.glsl_versions[0]}"
        return f"<{self.__class__.__name__} {version} | {extensions} | {glsl}>"

    def has_extension(self, extension: str) -> bool:
        return extension in self.extensions

    def matches_version(self, major, minor) -> bool:
        if self.major == major:
            return self.minor >= minor
        elif self.major > major:
            return True
        return False

    def supports_glsl(self, glsl_version: str) -> bool:
        return glsl_version in self.glsl_versions


class Renderer:
    num_indices: int
    context: ContextSpec
    # glut
    window: int
    # geo
    index_buffer: int
    vertex_buffer: int
    # rendering
    gl_texture: int
    shader: int
    # framebuffer
    depth_buffer: int
    frame_buffer: int
    render_texture: int

    def __init__(self, size, vertices, attribs, indices, shaders):
        # spec: ContextSpec
        # size: Size
        # vertices: Vertices
        # attribs: List[Attrib]
        # indices: List[int]
        # shaders: ShaderDict
        # setup gl context
        glut.glutInit()
        self.window = glut.glutCreateWindow("GLUT")
        glut.glutHideWindow()
        self.context = ContextSpec()
        # TODO: check context has all the features we want
        # basic gl config
        gl.glViewport(0, 0, *size)
        gl.glClearColor(1, 0, 1, 1)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glClearDepth(1)
        gl.glFrontFace(gl.GL_CW)
        # complex gl config
        self.init_framebuffer(size)
        self.init_geo(vertices, attribs, indices)
        self.init_shaders(shaders)

    def init_framebuffer(self, size: Size):
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
        # bind framebuffer so we can draw to it
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)

    def init_geo(self, vertices: Vertices, atrribs: List[Attrib], indices: List[int]):
        # hardcoded fullscreen quad
        vertices = np.array(
            [-1, -1, +1, -1, +1, +1, -1, +1], dtype=np.float32)
        attribs = [(gl.GL_FLOAT, 2, False)]
        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)
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
        # NOTE: don't unbind anything

    def init_shaders(self, shaders: ShaderDict):
        # NOTE: just doing vertex and fragment stages for now
        vertex_base = shaders["vertex"]
        fragment_base = shaders["fragment"]
        filenames = [
            f"vertex/{vertex_base}.glsl",
            f"fragment/{vertex_base}.{fragment_base}.glsl"]
        stages = [
            (type_, filename, gl.glCreateShader(type_))
            for filename, type_ in zip(filenames, (
                gl.GL_VERTEX_SHADER,
                gl.GL_FRAGMENT_SHADER))]
        shader_dir = os.path.join(os.path.dirname(__file__), "shaders")
        # compiling
        self.shader = gl.glCreateProgram()
        for type_, filename, stage in stages:
            path = os.path.join(shader_dir, filename)
            with open(path) as glsl_file:
                gl.glShaderSource(stage, glsl_file.read())
            gl.glCompileShader(stage)
            compiled = gl.glGetShaderiv(stage, gl.GL_COMPILE_STATUS)
            if compiled == gl.GL_FALSE:
                log = gl.glGetShaderInfoLog(stage)
                print(log.decode())
                raise RuntimeError(f"{type_} failed to compile!")
            gl.glAttachShader(self.shader, stage)
        # linking
        gl.glLinkProgram(self.shader)
        linked = gl.glGetProgramiv(self.shader, gl.GL_LINK_STATUS)
        if linked == gl.GL_FALSE:
            log = gl.glGetProgramInfoLog(self.shader)
            print(log.decode())
            raise RuntimeError("Shader Program failed to link")
        # cleanup
        for type_, filename, stage in stages:
            gl.glDetachShader(self.shader, stage)
            gl.glDeleteShader(stage)
        # use shader
        gl.glUseProgram(self.shader)
        # NOTE: it'd be cool to get the ProgramBinary
        # -- haven't been able to pull it off yet though

    def draw(self) -> np.array:
        # draw
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glDrawElements(gl.GL_TRIANGLES, self.num_indices, gl.GL_UNSIGNED_INT, gl.GLvoidp(0))
        # export renderbuffer colour
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
        pixels = gl.glReadPixels(0, 0, *self.texture.max_size, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        return np.frombuffer(pixels, dtype=np.uint8)
