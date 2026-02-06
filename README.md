# Foxhole Map Mod Packer

Python tool for creating custom HD map mods for Foxhole (Update 63+) using provided textures

## Requirements

### Texture Requirements
- All textures must be 2048x1776 RGBA

### Python Dependencies

- Python 3.7 or higher
- numpy
- Pillow (PIL)

```bash
pip install numpy pillow
```

### BC7 Encoder

Included `bc7_encoder.cp313-win_amd64.pyd` binary will work if you use Python 3.13 on Windows Machine, otherwise you'll need to build encoder yourself.
BC7 encoder is a compiled C++ extension that provides texture compression into expected pixel format.

- General build requirements:
  - **Cython**: For compiling the Python extension
  - **numpy**: Development headers (included with numpy installation)
- Windows requirements:
  - Microsoft Visual C++ Build Tools
- Linux requirements:
  - `g++` and `python3-dev` (`sudo apt-get install python3-dev build-essential`)

Build with:
`python build_encoder.py`

## Usage

### Basic Usage

The tool provides three main functions for packaging textures:

#### 1. `pak_textures_bc7` - Package Pre-Compressed BC7 Textures

Use this when you already have BC7-compressed texture data (must be exactly 3,637,248 bytes per texture).

```python
from paker import pak_textures_bc7, HEADERS

# Load pre-compressed BC7 texture data
with open("example/texture", "rb") as f:
    texture_data = f.read()

# Create mappings for all maps
mappings = {map_name: texture_data for map_name in HEADERS}

# Package with compression
pak_textures_bc7("output.pak", compress=True, mappings=mappings)

# Or package without compression
pak_textures_bc7("output.pak", compress=False, mappings=mappings)
```

#### 2. `pak_textures_nprgba` - Package numpy array RGBA Images

Use this to compress numpy RGBA images to BC7 format and package them. **Requires the BC7 encoder to be built.**

```python
from paker import pak_textures_nprgba, HEADERS
import numpy as np
from PIL import Image

# Load image as numpy array
image = np.array(Image.open("example/texture.png"))

# Create mappings for all maps
mappings = {map_name: image for map_name in HEADERS}

# Package with compression
pak_textures_nprgba("output.pak", compress=True, mappings=mappings)
```

#### 3. `pak_textures_folder` - Package Entire Folder

Use this to process all supported image files in a folder. **Requires the BC7 encoder to be built.**

```python
from paker import pak_textures_folder

# Package all images in a folder
pak_textures_folder("output.pak", compress=True, folder="path/to/textures")
```

## Project Structure

```
.
├── paker.py                 # Main module with packaging functions
├── build_encoder.py         # Script to build the BC7 encoder extension
├── bc7_encoder*.pyd/.so     # Compiled BC7 encoder
├── bc7_src/                 # BC7 encoder source files
├── assets/
│   ├── WorldMapBG.uasset    # Upscaled background texture
│   └── headers/             # Binary headers for each map region
│       ├── MapAcrithiaHex
│       ├── MapAllodsBightHex
│       └── ... (All 55 map headers)
└── example/
    ├── usage_example.py     # Example usage script
    ├── texture              # Sample BC7 texture data
    └── texture.png          # Sample PNG texture
```
