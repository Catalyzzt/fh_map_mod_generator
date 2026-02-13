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

Included `bc7_encoder.cp31*-win_amd64.pyd` binaries will work if you use Python 3.13 or 3.14 on a Windows Machine, otherwise you'll need to build encoder yourself.
BC7 encoder is a compiled C++ extension that provides texture compression into expected pixel format.

- General build requirements:
  - **Cython**: For compiling the Python extension
  - **numpy**: Development headers (included with numpy installation)
- Windows requirements:
  - Microsoft Visual C++ Build Tools
- Linux requirements:
  - `g++` and `python3-dev` (`sudo apt-get install python3-dev build-essential`)

Build with:
```bash
python build_encoder.py
```

## Layer Collection

The `layer_collection` folder contains high-resolution stitched map layers that can be combined to create custom maps. Credit to [Wolfgang-IX/Foxhole-Map-Project](https://github.com/Wolfgang-IX/Foxhole-Map-Project) for making this collection possible, most layers are sourced from there.

### Available Layers

#### Base Layers
- **raws.png** - Raw map data
- **t_devrender.png** - Developer's map renders
- **t_landscape.png** - Landscape ID layer
- **t_heightmap.png** - Complete heightmap
- **t_norm.png** - Normal map
- **t_curvature.png** - Curvature map

#### Enhancement Layers
- **ao.png** - Ambient occlusion (blend mode: multiply)
- **contours.png** - Contour lines (blend mode: multiply)
- **curvature_peaks.png** - Convex points (blend mode: additive)
- **curvature_dips.png** - Concave points (blend mode: difference)
- **heightmap_highs.png** - Terrain above water level (blend mode: additive)
- **heightmap_lows.png** - Terrain below water level (blend mode: difference)
- **rocks.png** - Rocks and mountains tinted blurred mask (blend mode: multiply)

#### Feature Layers
- **bulwark.png** - Bulwark structures
- **glaciers.png** - Glaciers
- **grid.png** - Grid overlay
- **rdz.png** - Rapid decay zone overaly
- **roads.png** - Roads
- **bridges.png** - Bridges
- **beaches.png** - Beaches
- **wells.png** - Water wells

#### Structures Range Overlays
- **ranges_ai.png** - AI structure ranges
- **ranges_cg.png** - Coastal gun ranges
- **ranges_intel.png** - Intel ranges
- **ranges_mh.png** - Mortar house ranges

Combine layers using your preferred image editing software

## Usage

### Basic Usage

This module provides five main functions:

#### 1. `pak` - Package a generic mod

Accepts a dictionary of file paths and their binary data:

```python
from paker import pak

files = {
    "War/Content/Textures/MyTexture.uasset": b"...",
    "War/Content/Data/MyData.uasset": b"..."
}

pak("output", files, compress=True)
```

#### 2. `pak_textures_bc7` - Package Pre-Compressed BC7 Textures

Use this when you already have BC7-compressed texture data (must be exactly 3,637,248 bytes per texture):

```python
from paker import pak_textures_bc7, HEADERS

with open("example/texture", "rb") as f:
    texture_data = f.read()

mappings = {map_name: texture_data for map_name in HEADERS}

pak_textures_bc7("output", compress=True, mappings=mappings)
```

#### 3. `pak_textures_nprgba` - Package numpy array RGBA Images

Compress numpy RGBA images to BC7 format and package them. **Requires the BC7 encoder to be built.**

```python
from paker import pak_textures_nprgba, HEADERS
import numpy as np
from PIL import Image

image = np.array(Image.open("example/texture.png"))

mappings = {map_name: image for map_name in HEADERS}

pak_textures_nprgba("output", compress=True, mappings=mappings)
```

#### 4. `pak_textures_folder` - Package Entire Folder

Process all supported image files in a folder. **Requires the BC7 encoder to be built.**

```python
from paker import pak_textures_folder

pak_textures_folder("output", compress=True, folder="path/to/textures")
```

#### 5. `pak_stitched` - Package Stitched Map Image

Break a full stitched map image into individual regions and package. **Requires the BC7 encoder to be built.**

The stitched image must be in the exact format of the provided layer collection images.

This is particularly useful for creating mods from the provided layer collection:

```python
from paker import pak_stitched

pak_stitched("my_custom_map", compress=True, stitched_image="my_custom_map.png")
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
│   ├── mask.png             # Alpha mask for region extraction
│   └── headers/             # Binary headers for each map region
│       ├── MapAcrithiaHex
│       ├── MapAllodsBightHex
│       └── ... (All 55 map headers)
├── layer_collection/        # Stitched map layers for compositing
│   ├── ao.png
│   ├── contours.png
│   ├── t_norm.png
│   └── ... (All layer files)
└── example/
    ├── texture              # Sample BC7 texture data
    └── texture.png          # Sample PNG texture
```

## Credits

- Layer collection is largerly composed and edited from [Wolfgang-IX/Foxhole-Map-Project](https://github.com/Wolfgang-IX/Foxhole-Map-Project)
