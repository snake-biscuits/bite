# https://en.wikipedia.org/wiki/S3_Texture_Compression
# https://github.com/snake-biscuits/minecraft_tf2_converter/blob/master/minecraft_assets/materials/vtf_converter.py#L82
from ..base import Face, MipIndex, Texture


def DXT1_to_RGB24(texture: Texture, mip_index: MipIndex = None) -> bytes:
    if mip_index is None:
        if texture.is_cubemap:
            mip_index = MipIndex(0, 0, Face(0))
        else:
            mip_index = MipIndex(0, 0, None)
    pixel_data = texture.mipmaps[mip_index]
    width, height = texture.size
    width >>= mip_index.mip
    height >>= mip_index.mip
    # TODO: loop over each tile and place it in as regular pixels
    # -- decode.detwiddle would be handy for this actually
    # -- each tile is a Z, so 1 iteration would suffice
    raise NotImplementedError()
