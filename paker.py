import os
import hashlib
import zlib
import numpy as np
from struct import pack

try:
    HAS_ENCODER = True
    from bc7_encoder import compress_bc7
except ImportError:
    HAS_ENCODER = False

__all__ = ["pak_textures_bc7", "pak_textures_nprgba", "pak_textures_folder"]


_HEADER_NAMES = [
    "MapAcrithiaHex",
    "MapAllodsBightHex",
    "MapAshFieldsHex",
    "MapBasinSionnachHex",
    "MapCallahansPassageHex",
    "MapCallumsCapeHex",
    "MapClahstraHex",
    "MapClansheadValleyHex",
    "MapDeadlandsHex",
    "MapDrownedValeHex",
    "MapEndlessShoreHex",
    "MapFarranacCoastHex",
    "MapFishermansRowHex",
    "MapGodcroftsHex",
    "MapGreatMarchHex",
    "MapGutterHex",
    "MapHeartlandsHex",
    "MapHomeRegionC",
    "MapHomeRegionW",
    "MapHowlCountyHex",
    "MapKalokaiHex",
    "MapKingsCageHex",
    "MapKuuraStrandHex",
    "MapLinnMercyHex",
    "MapLochMorHex",
    "MapLykosIsleHex",
    "MapMarbanHollowHex",
    "MapMooringCountyHex",
    "MapMorgensCrossingHex",
    "MapNevishLineHex",
    "MapOarbreakerHex",
    "MapOlavisWakeHex",
    "MapOnyxHex",
    "MapOriginHex",
    "MapPalantineBermHex",
    "MapPariPeakHex",
    "MapPipersEnclaveHex",
    "MapReachingTrailHex",
    "MapReaversPassHex",
    "MapRedRiverHex",
    "MapSableportHex",
    "MapShackledChasmHex",
    "MapSpeakingWoodsHex",
    "MapStemaLandingHex",
    "MapStlicanShelfHex",
    "MapStonecradleHex",
    "MapTempestIslandHex",
    "MapTerminusHex",
    "MapTheFingersHex",
    "MapTyrantFoothillsHex",
    "MapUmbralWildwoodHex",
    "MapViperPitHex",
    "MapWeatheredExpanseHex",
    "MapWestgateHex",
    "MapWrestaHex"
]

HEADERS = {}
_HEADERS_LOWER = {}

for name in _HEADER_NAMES:
    with open(f"assets/headers/{name}", "rb") as f:
        data = f.read()
        HEADERS[name] = data
        _HEADERS_LOWER[name.lower()] = (name, data)

BG_PATH = r"War\Content\Textures\UI\WorldMap\WorldMapBG.uasset"

def _get_header(name):
    canonical, header = _HEADERS_LOWER.get(name.lower(), (None, None))
    if canonical is None:
        raise ValueError(f"Unknown texture name: {name}")
    return canonical, header

def _gen_uasset(name, texture):
    canonical, header = _get_header(name)
    footer = (b'\x00\x08\x00\x00\xf0\x06\x00\x00\x01\x00\x00\x00\x00\x00'
              b'\x00\x00\x0f\x00\x00\x00\x00\x00\x00\x00\xc1\x83\x2a\x9e')
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

def pak_textures_bc7(output, compress, mappings):
    """
    Package BC7-compressed textures into a Foxhole .pak file.

    Args:
        output: Output .pak file path
        compress: Use zlib compression for .pak data blocks
        mappings: Dict of {map_name: bc7_bytes}. Each BC7 texture must be
                  exactly 3,637,248 bytes (2048x1776). Map names are
                  case-insensitive.

    Raises:
        ValueError: Invalid texture name or size
    """
    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    files = []
    for name, texture in mappings.items():
        if len(texture) != 3637248:
            raise ValueError("Invalid texture size")
        files.append(_gen_uasset(name, texture))
    files.sort()

    with open(output, "wb") as stream:
        records = []
        for p, b in files:
            record = _write_record(stream, b, compress)
            records.append((p, record))
        with open("assets/WorldMapBG.uasset", "rb") as fh:
            data = fh.read()
            record = _write_record(stream, data, compress)
            records.append((BG_PATH, record))

        _write_index(stream, records)

def pak_textures_nprgba(output, compress, mappings):
    """
    Convert RGBA images to BC7 and package into a Foxhole .pak file.

    Requires BC7 encoder (run build_encoder.py first).

    Args:
        output: Output .pak file path
        compress: Use zlib compression for .pak data blocks
        mappings: Dict of {map_name: numpy_array}. Arrays should be
                  shape [H, W, 4] in RGBA format. Map names are
                  case-insensitive.

    Raises:
        RuntimeError: BC7 encoder not built
    """
    if not HAS_ENCODER:
        raise RuntimeError("Build encoder with build_encoder.py first")

    mappings_bc7 = {k: compress_bc7(v).tobytes() for k, v in mappings.items()}
    pak_textures_bc7(output, compress, mappings_bc7)

def pak_textures_folder(output, compress, folder):
    """
    Package all images from a folder into a Foxhole .pak file.

    Loads PNG, JPG, JPEG, TGA, BMP files, converts to BC7, and packages
    them. Requires BC7 encoder (run build_encoder.py first). Filenames
    (without extension) are used as map names and are case-insensitive.

    Args:
        output: Output .pak file path
        compress: Use zlib compression for .pak data blocks
        folder: Folder containing image files

    Raises:
        RuntimeError: BC7 encoder not built
    """
    if not HAS_ENCODER:
        raise RuntimeError("Build encoder with build_encoder.py first")
    from PIL import Image

    mappings = {}
    for filename in os.listdir(folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tga',
                                       '.bmp')):
            filepath = os.path.join(folder, filename)
            name = os.path.splitext(filename)[0]
            t = np.array(Image.open(filepath))
            mappings[name] = t

    pak_textures_nprgba(output, compress, mappings)
