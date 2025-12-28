import numpy as np


# TODO: inverse
def ARGB16_to_RGBA32(raw_pixels: bytes) -> bytes:
    argb16 = np.frombuffer(raw_pixels, dtype=np.uint16)
    a = (argb16 >> 0x0) & 0x000F
    r = (argb16 >> 0x4) & 0x000F
    g = (argb16 >> 0x8) & 0x000F
    b = (argb16 >> 0xC) & 0x000F
    rgba32 = np.empty((argb16.size * 4,), dtype=np.uint8)
    rgba32[0::4] = r
    rgba32[1::4] = g
    rgba32[2::4] = b
    rgba32[3::4] = a
    rgba32 = rgba32 | rgba32 << 4  # 4-bit -> 8-bit
    return rgba32.tobytes()


def RGB24_to_RGB565(raw_pixels: bytes) -> bytes:
    rgb24 = np.frombuffer(raw_pixels, dtype=np.uint8)
    r = rgb24[0::3]
    g = rgb24[1::3]
    b = rgb24[2::3]
    rgb565 = np.empty((rgb24.size // 3,), dtype=np.uint16)
    rgb565 = r << 0xB | g << 0x5 | b << 0x0
    return rgb565.tobytes()


def RGB565_to_RGB24(raw_pixels: bytes) -> bytes:
    rgb565 = np.frombuffer(raw_pixels, dtype=np.uint16)
    r = (rgb565 >> 0xB) & 0x1F
    g = (rgb565 >> 0x5) & 0x3F
    b = (rgb565 >> 0x0) & 0x1F
    r = r << 3 | r >> 2
    g = g << 2 | g >> 4
    b = b << 3 | b >> 2
    rgb24 = np.empty((rgb565.size * 3,), dtype=np.uint8)
    rgb24[0::3] = r
    rgb24[1::3] = g
    rgb24[2::3] = b
    return rgb24.tobytes()


# TODO: inverse
def RGB24_to_RGBA32(raw_pixel: bytes) -> bytes:
    rgb24 = np.frombuffer(raw_pixel, dtype=np.uint8)
    rgb24 = rgb24.reshape(rgb24.size // 3, 3)
    rgba32 = np.insert(rgb24, 3, 0xFF, axis=1).flatten()
    return rgba32.tobytes()
