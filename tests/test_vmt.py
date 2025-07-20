import os

from bite.vmt import VMT


# TODO: pytest parametrise
# TODO: utils for collecting test files
def test_vmt():
    materials_dir = "tests/files"
    material = "tv.vmt"
    vmt = VMT.from_file(os.path.join(materials_dir, material))
    assert vmt.shader == "UnlitTwoTexture"
    assert vmt.textures["colour"] == "dev/test_pattern"
    assert vmt.textures["multiply"] == "models/tv/scanline"
    # TODO: assert vmt._raw caught texture proxies
