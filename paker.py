import os
import hashlib
import zlib
import numpy as np
from struct import pack
from time import time

try:
    HAS_ENCODER = True
    from bc7_encoder import compress_bc7
except ImportError:
    HAS_ENCODER = False

__all__ = ["pak",
           "pak_textures_bc7",
           "pak_textures_nprgba",
           "pak_textures_folder",
           "pak_stitched"]


_HEADER_NAMES = {
    "MapAcrithiaHex": [11804, 10792],
    "MapAllodsBightHex": [13344, 8128],
    "MapAshFieldsHex": [7184, 9904],
    "MapBasinSionnachHex": [10264, 1024],
    "MapCallahansPassageHex": [10264, 4576],
    "MapCallumsCapeHex": [7184, 2800],
    "MapClahstraHex": [13344, 6352],
    "MapClansheadValleyHex": [13344, 2800],
    "MapDeadlandsHex": [10264, 6352],
    "MapDrownedValeHex": [11804, 7240],
    "MapEndlessShoreHex": [14884, 7240],
    "MapFarranacCoastHex": [5644, 5464],
    "MapFishermansRowHex": [4104, 6352],
    "MapGodcroftsHex": [16424, 4576],
    "MapGreatMarchHex": [10264, 9904],
    "MapGutterHex": [4104, 4576],
    "MapHeartlandsHex": [8724, 9016],
    "MapHomeRegionC": [19504, 11680],
    "MapHomeRegionW": [1024, 1024],
    "MapHowlCountyHex": [11804, 1912],
    "MapKalokaiHex": [10264, 11680],
    "MapKingsCageHex": [7184, 6352],
    "MapKuuraStrandHex": [4104, 2800],
    "MapLinnMercyHex": [8724, 5464],
    "MapLochMorHex": [8724, 7240],
    "MapLykosIsleHex": [17964, 5464],
    "MapMarbanHollowHex": [11804, 5464],
    "MapMooringCountyHex": [8724, 3688],
    "MapMorgensCrossingHex": [14884, 3688],
    "MapNevishLineHex": [5644, 3688],
    "MapOarbreakerHex": [2564, 7240],
    "MapOlavisWakeHex": [1024, 4576],
    "MapOnyxHex": [16424, 9904],
    "MapOriginHex": [5644, 9016],
    "MapPalantineBermHex": [2564, 5464],
    "MapPariPeakHex": [2564, 3688],
    "MapPipersEnclaveHex": [19504, 8128],
    "MapReachingTrailHex": [10264, 2800],
    "MapReaversPassHex": [14884, 9016],
    "MapRedRiverHex": [8724, 10792],
    "MapSableportHex": [7184, 8128],
    "MapShackledChasmHex": [11804, 9016],
    "MapSpeakingWoodsHex": [8724, 1912],
    "MapStemaLandingHex": [4104, 8128],
    "MapStlicanShelfHex": [14884, 5464],
    "MapStonecradleHex": [7184, 4576],
    "MapTempestIslandHex": [16424, 6352],
    "MapTerminusHex": [13344, 9904],
    "MapTheFingersHex": [17964, 7240],
    "MapTyrantFoothillsHex": [17964, 9016],
    "MapUmbralWildwoodHex": [10264, 8128],
    "MapViperPitHex": [11804, 3688],
    "MapWeatheredExpanseHex": [13344, 4576],
    "MapWestgateHex": [5644, 7240],
    "MapWrestaHex": [16424, 8128],
}

HEADERS = {}
_HEADERS_LOWER = {}

for name in _HEADER_NAMES:
    with open(f"assets/headers/{name}", "rb") as f:
        data = f.read()
        HEADERS[name] = data
        _HEADERS_LOWER[name.lower()] = (name, data)

BG_PATH = r"War\Content\Textures\UI\WorldMap\WorldMapBG.uasset"


def _fix_key(name):
    canonical, _ = _HEADERS_LOWER.get(name.lower(), (None, None))
    if canonical:
        return canonical

    test = "Map" + name
    canonical, _ = _HEADERS_LOWER.get(test.lower(), (None, None))
    if canonical:
        return canonical

    test = name + "Hex"
    canonical, _ = _HEADERS_LOWER.get(test.lower(), (None, None))
    if canonical:
        return canonical

    test = "Map" + name + "Hex"
    canonical, _ = _HEADERS_LOWER.get(test.lower(), (None, None))
    if canonical:
        return canonical

    raise ValueError(f"Unknown texture name: {name}")

def _get_header(name):
    canonical, header = _HEADERS_LOWER.get(name.lower(), (None, None))
    if canonical is None:
        raise ValueError(f"Unknown texture name: {name}")
    return canonical, header

def _gen_uasset(name, texture):
    canonical, header = _get_header(name)
    footer = (b"\x00\x08\x00\x00\xf0\x06\x00\x00\x01\x00\x00\x00\x00\x00"
              b"\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\xc1\x83\x2a\x9e")
    path = r"War\Content\Textures\UI\HexMaps\Processed\{}.uasset"
    return path.format(canonical), header + texture + footer

def _pack_path(path):
    encoded_path = path.replace(os.path.sep, "/").encode("utf-8") + b"\0"
    return pack("<I", len(encoded_path)) + encoded_path

def _write_data(stream, data):
    hasher = hashlib.sha1()
    hasher.update(data)
    stream.write(data)
    return len(data), hasher.digest()

def _write_data_zlib(stream, data):
    buf_size = 65536
    size = len(data)
    block_count = (size + buf_size - 1) // buf_size
    base_offset = stream.tell()

    stream.write(pack("<I", block_count))
    stream.seek(block_count * 8 * 2, 1)

    record = pack("<BI", 0, buf_size)
    stream.write(record)

    cur_offset = base_offset + 4 + block_count * 8 * 2 + 5

    compress_blocks = [0] * block_count * 2
    compressed_size = 0
    compress_block_no = 0

    hasher = hashlib.sha1()

    for compress_block_no in range(block_count):
        chunk = data[compress_block_no * buf_size:(compress_block_no + 1) * buf_size]
        compressed_chunk = zlib.compress(chunk)

        compressed_size += len(compressed_chunk)
        compress_blocks[compress_block_no * 2] = cur_offset
        cur_offset += len(compressed_chunk)
        compress_blocks[compress_block_no * 2 + 1] = cur_offset

        hasher.update(compressed_chunk)
        stream.write(compressed_chunk)

    cur_offset = stream.tell()

    stream.seek(base_offset + 4, 0)
    stream.write(pack("<%dQ" % (block_count * 2), *compress_blocks))
    stream.seek(cur_offset, 0)

    return compressed_size, hasher.digest(), block_count, compress_blocks

def _write_record(stream, data, compress):
    record_offset = stream.tell()

    size = len(data)
    record = pack("<16xQI20x", size, int(compress))
    stream.write(record)

    if compress:
        compressed_size, sha1, block_count, blocks = (
            _write_data_zlib(stream, data)
        )
    else:
        record = pack("<BI", 0, 0)
        stream.write(record)
        compressed_size, sha1 = _write_data(stream, data)

    data_end = stream.tell()

    stream.seek(record_offset + 8, 0)
    stream.write(pack("<Q", compressed_size))

    stream.seek(record_offset + 28, 0)
    stream.write(sha1)

    stream.seek(data_end, 0)

    if compress:
        return (pack("<QQQI20s", record_offset, compressed_size, size,
                     1, sha1) +
                pack("<I%dQ" % (block_count * 2), block_count, *blocks) +
                pack("<BI", 0, 65536))
    else:
        return pack("<QQQI20sBI", record_offset, compressed_size, size, 0,
                    sha1, 0, 0)

def _write_index(stream, records):
    hasher = hashlib.sha1()
    index_offset = stream.tell()

    index_header = _pack_path("..\\..\\..\\") + pack("<I", len(records))
    index_size   = len(index_header)
    hasher.update(index_header)
    stream.write(index_header)

    for filename, record in records:
        encoded_filename = _pack_path(filename)
        hasher.update(encoded_filename)
        stream.write(encoded_filename)
        index_size += len(encoded_filename)

        hasher.update(record)
        stream.write(record)
        index_size += len(record)

    index_sha1 = hasher.digest()
    stream.write(pack("<IIQQ20s", 0x5A6F12E1, 3, index_offset, index_size,
                      index_sha1))

def _image_into_mapping(filename):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    print(f"Breaking {filename}...")

    stitched = Image.open(filename).convert("RGBA")
    mask = Image.open("assets/mask.png").convert("L")

    stitched_array = np.array(stitched)
    mask_array = np.array(mask)

    total = len(_HEADER_NAMES)

    mapping = {}

    for i, (region_name, (x, y)) in enumerate(_HEADER_NAMES.items(), 1):
        y1, y2 = y - 1024, y + 1024
        x1, x2 = x - 1024, x + 1024

        region_img = stitched_array[y1:y2, x1:x2].copy()
        region_img[:, :, 3] = np.minimum(region_img[:, :, 3], mask_array)

        mapping[region_name] = region_img[136:-136,:,:]
        print(f"  {i}/{total}", end="\r")
    print()
    return mapping

def pak(output, files, compress):
    """
    Create a pak archive from a dictionary of files.

    Args:
        output: Output filename (without "War-WindowsNoEditor_" prefix)
        files: Dict mapping file paths to binary data
        compress: Whether to use zlib compression
    """

    print(f"Packing {len(files)} files...")

    files = {k: v for k, v in sorted(files.items())}
    if output.endswith(".pak"):
        output = output[:-4]
    output_full = f"War-WindowsNoEditor_{output}.pak"
    with open(output_full, "wb") as stream:
        records = []
        total = len(files)
        for i, (p, b) in enumerate(files.items(), 1):
            record = _write_record(stream, b, compress)
            records.append((p, record))
            print(f"  {i}/{total}", end="\r")
        _write_index(stream, records)
    print()

def pak_textures_bc7(output, compress, mappings, _print_time=True):
    """
    Package BC7-compressed textures into a pak archive.

    Args:
        output: Output filename (without "War-WindowsNoEditor_" prefix)
        compress: Whether to use zlib compression
        mappings: Dict mapping texture names to BC7-compressed bytes
        _print_time: Internal flag to control time printing
    """

    t1 = time()
    print(f"Packaging {len(mappings)} BC7 textures...")

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fixed_mappings = {_fix_key(k): v for k, v in mappings.items()}

    files = {}
    total = len(fixed_mappings)
    for i, (name, texture) in enumerate(fixed_mappings.items(), 1):
        if len(texture) != 3637248:
            raise ValueError("Invalid texture size")
        p, b = _gen_uasset(name, texture)
        files[p] = b
        print(f"  {i}/{total}", end="\r")
    print()

    with open("assets/WorldMapBG.uasset", "rb") as fh:
        data = fh.read()
        files[BG_PATH] = data

    pak(output, files, compress)

    if _print_time:
        print(f"Completed in {time() - t1:.2f}s")

def pak_textures_nprgba(output, compress, mappings, _print_time=True):
    """
    Convert numpy RGBA arrays to BC7 and package into a pak archive.

    Args:
        output: Output filename (without "War-WindowsNoEditor_" prefix)
        compress: Whether to use zlib compression
        mappings: Dict mapping texture names to numpy RGBA arrays
        _print_time: Internal flag to control time printing

    Raises:
        RuntimeError: If BC7 encoder is not built
    """

    if not HAS_ENCODER:
        raise RuntimeError("Build encoder with build_encoder.py first")

    t1 = time()
    print(f"Converting {len(mappings)} textures to BC7...")

    fixed_mappings = {_fix_key(k): v for k, v in mappings.items()}

    mappings_bc7 = {}
    total = len(fixed_mappings)
    for i, (k, v) in enumerate(fixed_mappings.items(), 1):
        mappings_bc7[k] = compress_bc7(v).tobytes()
        print(f"  {i}/{total}", end="\r")
    print()

    pak_textures_bc7(output, compress, mappings_bc7, _print_time=False)

    if _print_time:
        print(f"Completed in {time() - t1:.2f}s")

def pak_textures_folder(output, compress, folder):
    """
    Load images from a folder and package them into a pak archive.

    Args:
        output: Output filename (without "War-WindowsNoEditor_" prefix)
        compress: Whether to use zlib compression
        folder: Path to folder containing image files

    Raises:
        RuntimeError: If BC7 encoder is not built
    """

    if not HAS_ENCODER:
        raise RuntimeError("Build encoder with build_encoder.py first")
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    t1 = time()
    print(f"Loading images from {folder}...")

    image_files = [f for f in os.listdir(folder)
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".tga", ".bmp"))]

    mappings = {}
    total = len(image_files)
    for i, filename in enumerate(image_files, 1):
        name = os.path.splitext(filename)[0]
        fixed_name = _fix_key(name)
        filepath = os.path.join(folder, filename)
        t = np.array(Image.open(filepath))
        mappings[fixed_name] = t
        print(f"  {i}/{total}", end="\r")
    print()

    pak_textures_nprgba(output, compress, mappings, _print_time=False)
    print(f"Completed in {time() - t1:.2f}s")

def pak_stitched(output, compress, stitched_image):
    """
    Break a stitched map image into regions and package into a pak archive.

    Args:
        output: Output filename (without "War-WindowsNoEditor_" prefix)
        compress: Whether to use zlib compression
        stitched_image: Path to stitched image file

    Raises:
        RuntimeError: If BC7 encoder is not built
    """

    if not HAS_ENCODER:
        raise RuntimeError("Build encoder with build_encoder.py first")

    t1 = time()
    mappings = _image_into_mapping(stitched_image)
    pak_textures_nprgba(output, compress, mappings, _print_time=False)
    print(f"Completed in {time() - t1:.2f}s")
