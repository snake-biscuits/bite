import bite

import numpy as np
from PIL import Image


pvr = bite.PVR.from_file("0GDTEX.PVR")
# <PVR '0GDTEX.PVR' v8.2 256x256 (2, 1)>
# pixel_format 2 -> 4-bits per colour

rgba16 = np.frombuffer(pvr.raw_data, dtype=np.uint8)
rg = np.bitwise_and(rgba16, 0x0F)
ba = np.bitwise_and(rgba16 >> 4, 0x0F)
rgba32 = np.empty((rg.size + ba.size,), dtype=np.uint8)
rgba32[0::2] = np.bitwise_or(rg << 4, rg)
rgba32[1::2] = np.bitwise_or(ba << 4, ba)

png = Image.frombytes("RGBA", (256, 256), rgba32.tobytes(), "raw")
png.save("test_pvr.tga")
