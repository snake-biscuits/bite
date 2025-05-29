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


class TextureManager:
    texture: bite.base.Texture
    index: bite.base.MipIndex
    # TODO: if texture is not a cubemap, set face to None
    texture_tag: str
    preview_tag: str

    def __init__(self, texture_tag: str, preview_tag: str):
        self.texture = None
        self.index = bite.base.MipIndex(0, 0, None)
        self.texture_tag = texture_tag
        self.preview_tag = preview_tag

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
            print(f"{self.texture=}")
            print(f"{self.texture.num_mipmaps=}")
            print(f"{self.texture.num_frames=}")
            # TODO: is cubemap
            print(f"{self.texture.format.name=}")
        elif ext == ".dds":
            self.texture = bite.DDS.from_file(path)
            print(f"{self.texture=}")
            print(f"{self.texture.num_mipmaps=}")
            print(f"{self.texture.array_size=}")
            print(f"{self.texture.resource_dimension=}")  # is cubemap
            print(f"{self.texture.format.name=}")
        else:
            raise RuntimeError(f"Unknown Extension: {ext!r}")
        num_mips, num_frames, is_cubemap = self.scope()
        if is_cubemap:
            self.index = bite.base.MipIndex(0, 0, bite.base.Face(0))
        else:
            self.index = bite.base.MipIndex(0, 0, None)
        # TODO: update sliders

    def mip_size(self, mip: int) -> (int, int):
        return [
            axis // (1 << mip)
            for axis in self.texture.size]

    def mip_float32(self, index: bite.base.MipIndex) -> np.array:
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


if __name__ == "__main__":

    imgui.create_context()

    texture_manager = TextureManager("framebuffer_tex", "preview_image")

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

    with imgui.window(tag="Main Window"):
        # ...
        imgui.add_button(
            label="Update",
            callback=texture_manager.update)
        # ...
        imgui.add_button(
            label="Open",
            callback=lambda: imgui.show_item("file_browser"))
        # ...
        imgui.add_image("framebuffer_tex", tag="preview_image")

    imgui.create_viewport(title="bite viewer", width=512, height=512)
    imgui.setup_dearpygui()
    imgui.show_viewport()
    # imgui.set_primary_window("Main Window", True)
    imgui.start_dearpygui()
    imgui.destroy_context()
