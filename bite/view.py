# https://dearpygui.readthedocs.io/en/latest/documentation/
# https://gist.github.com/leon-nn/cd4e3d50eb0fa23d8e197102f49f2cb3
import os
from typing import Any, Dict, List

import dearpygui.dearpygui as imgui
import numpy as np

from .base import Face, MipIndex, Size, Texture
# texture formats
from . import dds
from . import pvr
from . import vtf
# mipmap translation
from . import decode
from . import render


def rgb_to_rgba(rgb: bytes) -> bytes:
    rgb_array = np.frombuffer(rgb, dtype=np.uint8)
    rgb_pixels = rgb_array.reshape(rgb_array.size // 3, 3)
    rgba = np.insert(rgb_pixels, 3, 0xFF, axis=1).flatten()
    return rgba.tobytes()


class Viewer:
    texture: Texture
    index: MipIndex
    # imgui tags
    texture_tags: List[int]
    preview_tag: int
    mip_tag: int
    frame_tag: int
    face_tag: int

    # TODO: delete self & raw textures when closed / on next open
    def __init__(self, sender: str, app_data: Dict[str, Any], parent: str):
        # load texture from file
        name, path = list(app_data["selections"].items())[0]
        base, ext = os.path.splitext(path.lower())
        if ext == ".dds":
            self.texture = dds.DDS.from_file(path)
        elif ext == ".pvr":
            self.texture = pvr.PVR.from_file(path)
        elif ext == ".vtf":
            self.texture = vtf.VTF.from_file(path)
        else:
            raise RuntimeError(f"Unknown Extension: {ext!r}")
        if self.texture.raw_data is not None:
            raise RuntimeError(f"Unsupported Format: {self.texture.format}")
        # set default self.index
        if self.texture.is_cubemap:
            self.index = MipIndex(0, 0, Face(0))
        else:
            self.index = MipIndex(0, 0, None)
        # raw textures
        self.texture_tags = list()
        with imgui.texture_registry(show=False):
            for mip in range(self.texture.num_mipmaps):
                width, height = self.mip_size(mip)
                texture_floats = (np.frombuffer(
                    b"\xFF\x00\xFF\xFF" * width * height,
                    dtype=np.uint8) / 255).astype(np.float32)
                self.texture_tags.append(imgui.add_raw_texture(
                    width=width, height=height,
                    default_value=texture_floats,
                    format=imgui.mvFormat_Float_rgba))
        # create viewer window
        with imgui.child_window(parent=parent):
            with imgui.group(horizontal=True):
                with imgui.group(width=192):
                    self.mip_tag = imgui.add_slider_int(
                        label="Mip Level",
                        min_value=0,
                        max_value=self.texture.num_mipmaps - 1,
                        callback=self.mip_callback)
                    self.frame_tag = imgui.add_slider_int(
                        label="Frame",
                        min_value=0,
                        max_value=self.texture.num_frames - 1,
                        callback=self.frame_callback)
                    if self.texture.is_cubemap:
                        self.face_tag = imgui.add_slider_int(
                            label="Cubemap Face",
                            min_value=0, max_value=5,
                            callback=self.face_callback)
                with imgui.group():
                    width, height = self.texture.max_size
                    self.preview_tag = imgui.add_image(
                        self.texture_tags[0],
                        width=width, height=height)
                    # TODO: zoom
                    # -- on scroll
                    # -- slider
        # load texture
        self.update()

    def mip_size(self, mip: int) -> Size:
        return [axis // (1 << mip) for axis in self.texture.max_size]

    def pixels(self) -> np.array:  # 0..1 float32 RGBA
        # TODO: use a render.FrameBuffer for all textures
        # -- create at initialisation
        if isinstance(self.texture, dds.DDS):
            texture_bytes = self.pixels_dds()
        elif isinstance(self.texture, pvr.PVR):
            texture_bytes = self.pixels_pvr()
        elif isinstance(self.texture, vtf.VTF):
            texture_bytes = self.pixels_vtf()
        else:
            cls = self.texture.__class__.__name__
            raise NotImplementedError(f"Cannot get pixels from '{cls}'")
        return (np.frombuffer(
            texture_bytes,
            dtype=np.uint8) / 255).astype(np.float32)

    def pixels_dds(self) -> bytes:  # RGBA_8888
        texture_bytes = self.texture.mipmaps[self.index]
        # TODO: support more formats
        if self.texture.format == dds.DXGI.RGBA_8888_UINT:
            return texture_bytes
        elif self.texture.format == dds.DXGI.BC6H_UF16:
            # # duplicate uncompressed data to fill texture
            # texture_bytes *= 4
            frame_buffer = render.FrameBuffer2D.from_texture(self.texture)
            # TODO: update frame_buffer MipIndex & viewport size
            texture_bytes = rgb_to_rgba(frame_buffer.draw())
        else:
            fmt = self.texture.format.name
            raise NotImplementedError(f"Cannot convert: '{fmt}'")
        return texture_bytes

    def pixels_pvr(self) -> bytes:  # RGBA_8888
        # TODO: support more formats
        assert self.texture.format.texture == pvr.TextureMode.TWIDDLED
        return decode.twiddle.TWIDDLED_to_ORDERED(self.texture, self.index)
        # NOTE: built for ABGR_4444_TWIDDLED
        # -- need to refactor so pixel and texture translation are separated

    def pixels_vtf(self) -> bytes:  # RGBA_8888
        # TODO: support more formats
        assert self.texture.format == vtf.Format.RGBA_8888
        return self.texture.mipmaps[self.index]

    def update(self):
        """update texture to reflect current index"""
        texture_tag = self.texture_tags[self.index.mip]
        imgui.set_value(texture_tag, self.pixels())
        imgui.configure_item(self.preview_tag, texture_tag=texture_tag)

    # callbacks
    def mip_callback(self):
        mip, frame, face = self.index
        mip = imgui.get_value(self.mip_tag)
        self.index = MipIndex(mip, frame, face)
        self.update()

    def frame_callback(self):
        mip, frame, face = self.index
        frame = imgui.get_value(self.frame_tag)
        self.index = MipIndex(mip, frame, face)
        self.update()

    def face_callback(self):
        mip, frame, face = self.index
        if self.texture.is_cubemap:
            face_index = imgui.get_value(self.face_tag)
            face = Face(face_index)
        else:  # force to None, just in case
            face = None
        self.index = MipIndex(mip, frame, face)
        self.update()


def main():
    """create an imgui loader with a file browser"""
    imgui.create_context()

    # TODO: open a file from argv

    # file browser + callback to create a Viewer
    with imgui.file_dialog(
            directory_selector=False,
            show=False,
            callback=lambda s, a: Viewer(s, a, "main"),
            tag="file_browser",
            width=768, height=320):
        # NOTE: case-sensitive, idk why
        imgui.add_file_extension("Direct Draw Surface (*.dds){.dds}")
        imgui.add_file_extension("PowerVR Texture (*.pvr){.pvr,.PVR}")
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
