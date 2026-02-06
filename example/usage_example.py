import timeit
from paker import HEADERS, pak_textures_bc7, pak_textures_nprgba

def test_bc7():
    with open("texture", "rb") as fh:
        t = fh.read()
    mappings = {k: t for k in HEADERS}
    pak_textures_bc7("War-WindowsNoEditor_MapMod_BC_C.pak", True, mappings)
    pak_textures_bc7("War-WindowsNoEditor_MapMod_BC_UC.pak", False, mappings)

def test_nprgba():
    import numpy as np
    from PIL import Image

    t = np.array(Image.open("texture.png"))

    mappings = {k: t for k in HEADERS}
    pak_textures_nprgba("War-WindowsNoEditor_MapMod_NP_C.pak", True, mappings)
    pak_textures_nprgba("War-WindowsNoEditor_MapMod_NP_UC.pak", False, mappings)

if __name__ == "__main__":
    bc7_time = timeit.timeit(test_bc7, number=1)
    print(f"BC7 test took {bc7_time:.4f} seconds")

    nprgba_time = timeit.timeit(test_nprgba, number=1)
    print(f"NPRGBA test took {nprgba_time:.4f} seconds")
