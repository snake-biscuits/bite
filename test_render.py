import os
import sys

import numpy as np
import OpenGL.GL as gl
from PIL import Image

from bite.base import Face, MipIndex
from bite.dds import DDS
from bite.render import Renderer


shader_dir = "bite/render/shaders"

with open(os.path.join(shader_dir, "basic.vertex.glsl")) as glsl_file:
    vertex_shader = glsl_file.read()

with open(os.path.join(shader_dir, "basic.fragment.glsl")) as glsl_file:
    fragment_shader = glsl_file.read()

renderer = Renderer(
    (512, 512), {
        gl.GL_VERTEX_SHADER: vertex_shader,
        gl.GL_FRAGMENT_SHADER: fragment_shader},
    np.array([-1, -1, +1, -1, +1, +1, -1, +1], dtype=np.float32),
    [(gl.GL_FLOAT, 2, False)],
    np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32))

dds = DDS.from_file(os.path.join(
    "/home/bikkie/drives/ssd1/Mod/",
    "ApexLegends/Projects/Cubemaps/",
    "cubemaps_hdr.dds"))

if len(sys.argv) != 2:
    print(f"USAGE: {sys.argv[0]} cubemap_index")
    sys.exit(0)

i = int(sys.argv[1])

# NOTE: add_texture doesn't take into account mip_level, yet.
texture_bytes = dds.mipmaps[MipIndex(0, i, Face(3))]
renderer.active_texture = renderer.add_texture(dds.size, 0x8E8F, texture_bytes)

pixels = renderer.draw()

result = Image.frombytes("RGB", (512, 512), pixels.tobytes(), "raw")
result.save("test_render.png")
