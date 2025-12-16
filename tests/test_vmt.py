import os

from bite.materials.vmt import Vmt


# TODO: pytest parametrise
# TODO: utils for collecting test files
def test_vmt():
    materials_dir = "tests/files"
    material = "tv.vmt"
    vmt = Vmt.from_file(os.path.join(materials_dir, material))
    vmt.parse()
    assert vmt.shader == "UnlitTwoTexture"
    assert vmt.textures["colour"] == "dev/test_pattern"
    assert vmt.textures["multiply"] == "models/tv/scanline"
    # TODO: assert vmt._raw caught texture proxies
