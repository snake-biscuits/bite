# https://dearpygui.readthedocs.io/en/latest/documentation/
# https://gist.github.com/leon-nn/cd4e3d50eb0fa23d8e197102f49f2cb3
import os
from typing import Any, Dict, Tuple

import dearpygui.dearpygui as imgui
import numpy as np

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
    gl_Position = vec4(vertexPosition, 0.0, 1.0);
}
"""

fragment_shader = """
#version 450 core
out vec4 outColour;

in vec2 position;  // also uv

void main()
{
    outColour = vec4(position, 0.0, 1.0);
}
"""


# NOTE: having texture manager spawn a viewer window might be better
class TextureManager:
    texture: bite.Texture
    index: bite.MipIndex
    # imgui item tags
    texture_tag: str
    preview_tag: str
    # sliders
    mip_tag: str
    frame_tag: str
    face_tag: str

    def __init__(self, texture, preview, mip, frame, face):
        self.texture = None
        self.index = bite.MipIndex(0, 0, None)
        self.texture_tag = texture
        self.preview_tag = preview
        self.mip_tag = mip
        self.frame_tag = frame
        self.face_tag = face

    def load_callback(self, sender: str, app_data: Dict[str, Any]):
        for name, path in app_data["selections"].items():
            try:
                self.load(path)
            except Exception as exc:
                # TODO: show an error dialog / popup
                print(f"!!! {exc!r}")
        # NOTE: self.load will reset self.index to the first mipmap
        self.update()

    def load(self, path: str):
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
        # set slider ranges
        # NOTE: setting slider value to zero doesn't update it visually
        imgui.configure_item(self.mip_tag, max_value=num_mips - 1)
        imgui.configure_item(self.frame_tag, max_value=num_frames - 1)
        imgui.configure_item(self.face_tag, enabled=is_cubemap)

    def mip_size(self, mip: int) -> (int, int):
        return [
            axis // (1 << mip)
            for axis in self.texture.size]

    def mip_float32(self, index: bite.MipIndex) -> np.array:
        texture_bytes = self.texture.mipmaps[index] * 4
        # NOTE: x4 for BC6 compression factor
        # TODO: use OpenGL framebuffer to convert texture on the GPU
        return (np.array(
            list(texture_bytes),
            dtype=np.uint8) / 255).astype(np.float32)

    def update(self):
        imgui.set_value(self.texture_tag, self.mip_float32(self.index))
        width, height = self.mip_size(self.index.mip)
        imgui.set_item_width(self.texture_tag, width)
        imgui.set_item_height(self.texture_tag, height)
        # TODO: zoom slider for viewer
        imgui.set_item_width(self.preview_tag, width)
        imgui.set_item_height(self.preview_tag, height)

    def scope(self) -> TextureScope:
        if self.texture is None:
            return (0, 0, None)
        elif isinstance(self.texture, bite.DDS):
            return self.scope_dds(self.texture)
        elif isinstance(self.texture, bite.VTF):
            return self.scope_vtf(self.texture)
        else:
            raise NotImplementedError(
                "Unsupported Texture class: {type(self.texture)}")

    @staticmethod
    def scope_dds(dds) -> TextureScope:
        if dds.resource_dimension == 3:
            return (dds.num_mipmaps, dds.array_size // 6, True)
        else:
            return (dds.num_mipmaps, dds.array_size, False)

    @staticmethod
    def scope_vtf(vtf) -> TextureScope:
        is_cubemap = bite.vtf.Flags.ENVMAP in vtf.flags
        return (vtf.num_mipmaps, vtf.num_frames, is_cubemap)

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

    imgui.create_context()

    texture_manager = TextureManager(
        "framebuffer_tex",
        "preview_image",
        "mip_level",
        "frame",
        "cubemap_face")

    # default texture
    texture_floats = (np.array(
        list(b"\xFF\x00\xFF\xFF" * 32 * 32),
        dtype=np.uint8) / 255).astype(np.float32)

    with imgui.texture_registry(show=False):
        imgui.add_raw_texture(
            width=32, height=32,
            default_value=texture_floats,
            format=imgui.mvFormat_Float_rgba,
            tag="framebuffer_tex")

    # ui
    with imgui.file_dialog(
            directory_selector=False,
            show=False,
            callback=texture_manager.load_callback,
            tag="file_browser",
            cancel_callback=lambda sender, app_data: None,
            width=768, height=320):
        imgui.add_file_extension("Direct Draw Surface (*.dds){.dds}")
        imgui.add_file_extension("Valve Texture Format (*.vtf){.vtf}")

    # NOTE: forcing 4k min size to ensure we fill the viewport
    with imgui.window(tag="main", min_size=(4096, 4096)):
        with imgui.menu_bar():
            imgui.add_menu_item(
                label="Open",
                callback=lambda: imgui.show_item("file_browser"))

        with imgui.group(horizontal=True):
            with imgui.group(width=192):
                imgui.add_slider_int(
                    label="Mip Level",
                    min_value=0, max_value=0,
                    callback=texture_manager.mip_callback,
                    tag="mip_level")
                imgui.add_slider_int(
                    label="Frame",
                    min_value=0, max_value=0,
                    callback=texture_manager.frame_callback,
                    tag="frame")
                imgui.add_slider_int(
                    label="Cubemap Face",
                    min_value=0, max_value=5,
                    enabled=False,
                    callback=texture_manager.face_callback,
                    tag="cubemap_face")
            with imgui.group():
                imgui.add_image("framebuffer_tex", tag="preview_image")
                # TODO: viewer controls
                # -- mip
                # -- frame
                # -- face
                # -- render mode (single mip, 3D cubemap, equilateral)
                # TODO: zoom
                # -- on scroll
                # -- slider

    imgui.create_viewport(title="bite viewer", width=512, height=512)
    imgui.setup_dearpygui()
    imgui.show_viewport()
    imgui.set_primary_window("main", True)
    imgui.start_dearpygui()
    imgui.destroy_context()
