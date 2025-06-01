import os

from PIL import Image

from bite.dds import DDS
from bite.render.texture import TextureRenderer


dds = DDS.from_file(os.path.join(
    "/home/bikkie/drives/ssd1/Mod/",
    "ApexLegends/Projects/Cubemaps/",
    "cubemaps_hdr.dds"))
renderer = TextureRenderer.from_texture(dds)
pixels = renderer.draw()
png = Image.frombytes("RGB", dds.size, pixels.tobytes(), "raw")
png.save("test_render.png")
