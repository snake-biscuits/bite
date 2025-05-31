# https://dearpygui.readthedocs.io/en/latest/documentation/
# https://gist.github.com/leon-nn/cd4e3d50eb0fa23d8e197102f49f2cb3
import enum
import os
from typing import Any, Dict, List, Tuple

import dearpygui.dearpygui as imgui
import numpy as np
from OpenGL.error import GLError
import OpenGL.GL as gl
import OpenGL.GLUT as glut

import bite


TextureScope = Tuple[int, int, bool]
# ^ (num_mipmaps, num_frames, is_cubemap)

vertex_shader = """
#version 450 core
layout (location = 0) in vec2 vertexPosition;

out vec2 position;

void main()
{
    position = vertexPosition;
    gl_Position = vec4(vertexPosition, -1.0, 1.0);
}
"""

fragment_shader = """
#version 450 core
layout (location = 0) out vec4 outColour;

in vec2 position;

// TODO: sampler
// TODO: texture

void main()
{
    vec2 uv = (position + 1) / 2;
    outColour = vec4(uv, 0, 1);
}
"""


# NOTE: stored in GL.ARB.texture_compression_bptc
# -- also glInitTextureCompressionBptcARB() -> bool
class BPTC(enum.Enum):
    # https://registry.khronos.org/OpenGL/extensions/ARB/ARB_texture_compression_bptc.txt
    # GL_ARB_texture_compression_bptc
    # RGBA
    RGBA = 0x8E8C  # COMPRESSED_RGBA_BPTC_UNORM_ARB
    SRGB = 0x8E8D  # COMPRESSED_SRGB_ALPHA_BPTC_UNORM_ARB
    # RGB
    SIGNED_FLOAT = 0x8E8E  # COMPRESSED_RGB_BPTC_SIGNED_FLOAT_ARB
    UNSIGNED_FLOAT = 0x8E8F  # COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_ARB


internal_format = {
    ".dds": {
        bite.dds.DXGI.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)},
    ".vtf": {
        bite.vtf.Format.BC6H_UF16: (BPTC.UNSIGNED_FLOAT.value, True)}}
# ^ {".ext": {texture.format: (gl_format, is_compressed)}}


class Renderer:
    # core handles
    window: int
    vertex_buffer: int
    index_buffer: int
    shader: int
    # metadata
    size: bite.Size
    # texture handles
    active_texture: int
    textures: Dict[Tuple[bite.Size, int], int]
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
        # gl.glClearDepth(1)
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

    def add_texture(self, size: bite.Size, format_: int, data: bytes):
        raise NotImplementedError("WIP")
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
        gl.glCompressedTexImage2D(gl.GL_TEXTURE_2D, 0, format_, *size, 0, len(data), data)
        # pixelated filtering:
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        # TODO: GL_TEXTURE_WRAP_S, GL_MIRROR_CLAMP_TO_EDGE
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # unbind

    def init_framebuffer(self, size):
        # texture to save render colour
        self.render_texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.render_texture)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0, gl.GL_RGB, *size, 0, gl.GL_RGB,
            gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # unbind
        # depth buffer
        self.depth_buffer = gl.glGenRenderbuffers(1)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depth_buffer)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT, *size)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)  # unbind
        # colour buffer
        self.frame_buffer = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER,
            gl.GL_COLOR_ATTACHMENT0,
            gl.GL_TEXTURE_2D,
            self.render_texture,
            0)
        # link it all together
        gl.glFramebufferRenderbuffer(
            gl.GL_FRAMEBUFFER,
            gl.GL_DEPTH_ATTACHMENT,
            gl.GL_RENDERBUFFER,
            self.depth_buffer)
        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            # NOTE: this is bad, the GPU can't handle this config!
            raise RuntimeError(f"init_framebuffer failed: {status}")

    def init_geo(self, vertices: np.array, attribs: List[Any], indices: np.array):
        self.num_indices = indices.size
        # buffer data
        self.vertex_buffer, self.index_buffer = gl.glGenBuffers(2)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferData(
            gl.GL_ARRAY_BUFFER,
            len(vertices.tobytes()),
            vertices,
            gl.GL_STATIC_DRAW)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        gl.glBufferData(
            gl.GL_ELEMENT_ARRAY_BUFFER,
            len(indices.tobytes()),
            indices,
            gl.GL_STATIC_DRAW)
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
            gl.glVertexAttribPointer(i, size, type_, normalise, span, offset)
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
        # TODO: can't always see triangles, only get clearcolour
        # -- I HAVE NO IDEA WHY THIS IS HAPPENING
        # -- need more explicit state? matricies?
        # NOTE: can't we just copy the compressed texture to uncompressed RGBA?
        # setup
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
        # draw
        gl.glUseProgram(self.shader)
        gl.glDrawElements(gl.GL_TRIANGLES, self.num_indices, gl.GL_UNSIGNED_INT, None)
        gl.glUseProgram(0)
        # read pixels
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
        pixels = gl.glReadPixels(0, 0, *self.size, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        # return 1D array
        return np.frombuffer(pixels, dtype=np.uint8)
        # NOTE: we could do mvFormat_Float_rgb
        # -- since we're copying into a raw texture
        # -- this doesn't work on mac, but then iirc neither does OpenGL
        # -- RGB uint8 feeds into PIL.Image.frombytes nicely though


class Viewer:
    texture: bite.Texture
    index: bite.MipIndex
    # imgui tags
    texture_tags: List[int]
    preview_tag: int
    mip_tag: int
    frame_tag: int
    face_tag: int

    # TODO: delete self & raw textures when closed / on next open
    def __init__(self, sender: str, app_data: Dict[str, Any]):
        # load texture from file
        name, path = list(app_data["selections"].items())[0]
        base, ext = os.path.splitext(path.lower())
        if ext == ".vtf":
            self.texture = bite.VTF.from_file(path)
        elif ext == ".dds":
            self.texture = bite.DDS.from_file(path)
        else:
            raise RuntimeError(f"Unknown Extension: {ext!r}")
        # reset self.index
        num_mips, num_frames, is_cubemap = self.scope()
        if is_cubemap:
            self.index = bite.MipIndex(0, 0, bite.Face(0))
        else:
            self.index = bite.MipIndex(0, 0, None)
        # raw textures
        self.texture_tags = list()
        with imgui.texture_registry(show=False):
            for mip in range(num_mips):
                width, height = self.mip_size(mip)
                texture_floats = (np.array(
                    list(b"\xFF\x00\xFF\xFF" * width * height),
                    dtype=np.uint8) / 255).astype(np.float32)
                self.texture_tags.append(imgui.add_raw_texture(
                    width=width, height=height,
                    default_value=texture_floats,
                    format=imgui.mvFormat_Float_rgba))
        # create viewer window
        num_mipmaps, num_frames, is_cubemap = self.scope()
        with imgui.child_window(parent="main"):
            with imgui.group(horizontal=True):
                with imgui.group(width=192):
                    self.mip_tag = imgui.add_slider_int(
                        label="Mip Level",
                        min_value=0, max_value=num_mipmaps - 1,
                        callback=self.mip_callback)
                    self.frame_tag = imgui.add_slider_int(
                        label="Frame",
                        min_value=0, max_value=num_frames - 1,
                        callback=self.frame_callback)
                    if is_cubemap:
                        self.face_tag = imgui.add_slider_int(
                            label="Cubemap Face",
                            min_value=0, max_value=5,
                            callback=self.face_callback)
                with imgui.group():
                    width, height = self.texture.size
                    self.preview_tag = imgui.add_image(
                        self.texture_tags[0],
                        width=width, height=height)
                    # TODO: zoom
                    # -- on scroll
                    # -- slider
        # load texture
        self.update()

    def mip_size(self, mip: int) -> bite.Size:
        return [axis // (1 << mip) for axis in self.texture.size]

    def update(self):
        mip = self.index.mip
        texture_bytes = self.texture.mipmaps[self.index] * 4
        # NOTE: x4 for BC6 compression factor
        # TODO: use OpenGL framebuffer to convert texture on the GPU
        mip_float32 = (np.array(
            list(texture_bytes),
            dtype=np.uint8) / 255).astype(np.float32)
        # update raw texture of correct mip scale
        imgui.set_value(self.texture_tags[mip], mip_float32)
        imgui.configure_item(
            self.preview_tag,
            texture_tag=self.texture_tags[mip])

    def scope(self) -> TextureScope:
        if self.texture is None:
            return (0, 0, None)
        elif isinstance(self.texture, bite.DDS):
            dds = self.texture
            if dds.resource_dimension == 3:
                return (dds.num_mipmaps, dds.array_size // 6, True)
            else:
                return (dds.num_mipmaps, dds.array_size, False)
        elif isinstance(self.texture, bite.VTF):
            vtf = self.texture
            is_cubemap = bite.vtf.Flags.ENVMAP in vtf.flags
            return (vtf.num_mipmaps, vtf.num_frames, is_cubemap)
        else:
            raise NotImplementedError(
                "Unsupported Texture class: {type(self.texture)}")

    # callbacks
    def mip_callback(self):
        mip, frame, face = self.index
        mip = imgui.get_value(self.mip_tag)
        self.index = bite.MipIndex(mip, frame, face)
        self.update()

    def frame_callback(self):
        mip, frame, face = self.index
        frame = imgui.get_value(self.frame_tag)
        self.index = bite.MipIndex(mip, frame, face)
        self.update()

    def face_callback(self):
        mip, frame, face = self.index
        if self.scope()[-1]:  # is_cubemap
            face_index = imgui.get_value(self.face_tag)
            face = bite.Face(face_index)
        else:  # force to None, just in case
            face = None
        self.index = bite.MipIndex(mip, frame, face)
        self.update()


if __name__ == "__main__":
    # Renderer test
    renderer = Renderer(
        (512, 512), {
            gl.GL_VERTEX_SHADER: vertex_shader,
            gl.GL_FRAGMENT_SHADER: fragment_shader},
        np.array([-1, -1, +1, -1, +1, +1, -1, +1], dtype=np.float32),
        [(gl.GL_FLOAT, 2, False)],
        np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32))

    pixels = renderer.draw()

    from PIL import Image
    result = Image.frombytes("RGB", (512, 512), pixels.tobytes(), "raw")
    result.save("test_render.png")

    import sys
    sys.exit(0)

    # main
    imgui.create_context()
    # imgui.configure_app(manual_callback_management=True)

    # ui
    with imgui.file_dialog(
            directory_selector=False,
            show=False,
            # callback=lambda s, a: print(Viewer(s, a)),
            callback=lambda s, a: Viewer(s, a),
            # callback=lambda s, a: imgui.add_window(label="Test"),
            tag="file_browser",
            width=768, height=320):
        imgui.add_file_extension("Direct Draw Surface (*.dds){.dds}")
        imgui.add_file_extension("Valve Texture Format (*.vtf){.vtf}")

    # NOTE: forcing 4k min size to ensure we fill the viewport
    with imgui.window(tag="main", min_size=(4096, 4096)):
        with imgui.menu_bar():
            imgui.add_menu_item(
                label="Open",
                callback=lambda: imgui.show_item("file_browser"))

    imgui.create_viewport(title="bite viewer", width=512, height=512)
    imgui.setup_dearpygui()
    imgui.show_viewport()
    imgui.set_primary_window("main", True)
    imgui.start_dearpygui()
    imgui.destroy_context()
