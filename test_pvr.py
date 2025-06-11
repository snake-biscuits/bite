from PIL import Image

import bite


if __name__ == "__main__":
    pvr = bite.PVR.from_file("0GDTEX.PVR")
    # <PVR '0GDTEX.PVR' 256x256 ABGR_4444_TWIDDLED>
    index = bite.MipIndex(0, 0, None)

    pixels = bite.decode.twiddle.TWIDDLED_to_ORDERED(pvr, index)

    tga = Image.frombytes("RGBA", (256, 256), pixels, "raw")
    tga.save("test_pvr.tga")
